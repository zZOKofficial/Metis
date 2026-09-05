import json
import operator
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from ..core.clock import as_utc, utcnow
from ..core.config import settings

# Lazy database client
_db = None

_DATETIME_MARKER = '__dt__'


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return {_DATETIME_MARKER: obj.isoformat()}
    raise TypeError(f'Object of type {type(obj).__name__} is not JSON serializable')


def _revive(value: Any) -> Any:
    if isinstance(value, list):
        return [_revive(v) for v in value]
    if isinstance(value, dict):
        if _DATETIME_MARKER in value and len(value) == 1:
            try:
                # Rows written before datetimes were made aware come back
                # naive; normalize here so the rest of the app never has to
                # care which build wrote a given document.
                return as_utc(datetime.fromisoformat(value[_DATETIME_MARKER]))
            except (ValueError, TypeError):
                return value
        return {k: _revive(v) for k, v in value.items()}
    return value


def _dump(data: dict) -> str:
    return json.dumps(data, default=_json_default)


def _load(raw: str) -> dict:
    try:
        return _revive(json.loads(raw))
    except (json.JSONDecodeError, TypeError):
        return {}


# --- Query filters -----------------------------------------------------------
# Filters are (field, op, value) triples. Whenever the backing store can
# evaluate one itself we push it down; anything left over is applied in Python
# by _matches(). Pushing down matters most on Firestore, where an unfiltered
# stream() reads (and bills for) every document in the collection, including
# every other tenant's.

_PUSHDOWN_OPS = {'==': '=', '>': '>', '<': '<', '>=': '>=', '<=': '<='}

# '!=' is deliberately unsupported: SQLite and Firestore both exclude documents
# where the field is absent, while a naive Python comparison would include them.
_COMPARATORS = {
    '==': operator.eq,
    '>': operator.gt,
    '<': operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
}

# Field names are interpolated into a JSON path, so only allow plain identifiers.
_FIELD_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _can_push(field: str, op: str, value: Any) -> bool:
    '''True when the store can evaluate this filter natively.

    Only scalars are pushed down: datetimes are stored as {__dt__: ...} wrappers
    and would not compare correctly inside the store.
    '''
    return (
        op in _PUSHDOWN_OPS
        and isinstance(field, str)
        and _FIELD_RE.match(field) is not None
        and isinstance(value, (str, int, float, bool))
    )


def _matches(data: dict, filters: list[tuple]) -> bool:
    '''Evaluate filters in Python, matching how the stores behave.

    A missing field satisfies no comparison, which is what both SQLite (NULL
    propagates through the comparison) and Firestore (absent fields are not
    returned) already do. An unknown operator raises rather than being skipped
    -- a filter that silently matches everything is how one tenant ends up
    seeing another tenant's rows.
    '''
    for field, op, value in filters:
        compare = _COMPARATORS.get(op)
        if compare is None:
            raise ValueError(f'unsupported filter operator: {op!r}')
        field_val = data.get(field)
        if field_val is None:
            return False
        try:
            if not compare(field_val, value):
                return False
        except TypeError:
            return False  # mismatched types never match
    return True


def _default_db_path() -> str:
    if settings.METIS_DB_PATH:
        return settings.METIS_DB_PATH
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(backend_root, 'data', 'metis.db')


def get_db():
    '''Get database client instance (lazy initialization).

    Uses Firestore when GOOGLE_CLOUD_PROJECT is configured, otherwise a
    local SQLite database so all data survives restarts.

    Falling back to SQLite is the right answer on a laptop and the wrong one
    on a hosted deployment, where the container filesystem is discarded on
    every restart: the app would keep serving, look healthy, and quietly lose
    every product and order it was given. METIS_REQUIRE_FIRESTORE turns that
    fallback into a startup failure instead.
    '''
    global _db
    if _db is None:
        if settings.GOOGLE_CLOUD_PROJECT:
            try:
                from google.cloud import firestore
                client = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)
                if settings.METIS_REQUIRE_FIRESTORE:
                    _verify_firestore(client)
                _db = client
            except Exception as e:
                if settings.METIS_REQUIRE_FIRESTORE:
                    raise RuntimeError(
                        f'Firestore is unreachable ({e}) and '
                        f'METIS_REQUIRE_FIRESTORE is set, so falling back to '
                        f'local SQLite would silently discard all data on the '
                        f'next restart. Check GOOGLE_CLOUD_PROJECT and the '
                        f'service-account credentials.'
                    ) from e
                print(f'WARNING: Firestore client failed to initialize ({e}); switching to local SQLite database.')
                _db = SqliteDB(_default_db_path())
        elif settings.METIS_REQUIRE_FIRESTORE:
            raise RuntimeError(
                'METIS_REQUIRE_FIRESTORE is set but GOOGLE_CLOUD_PROJECT is '
                'blank, so there is no Firestore to require.'
            )
        else:
            print('INFO: GOOGLE_CLOUD_PROJECT not set; using local SQLite database. Data persists across restarts.')
            _db = SqliteDB(_default_db_path())
    return _db


def _verify_firestore(client) -> None:
    '''Prove the client can actually talk to Firestore.

    `firestore.Client(...)` is lazy -- it constructs happily with absent,
    expired or wrong credentials and only fails on the first real query. So
    catching construction errors proves nothing; a deployment with a bad key
    would still report itself healthy and fail later, one request at a time.
    One cheap read settles it at startup.
    '''
    next(client.collection('businesses').limit(1).stream(), None)


def backend_name() -> str:
    '''Which store is actually serving reads, for /health.

    Resolves the lazy client, so a misconfigured deployment fails the health
    check rather than the first shopper.
    '''
    return 'sqlite' if isinstance(get_db(), SqliteDB) else 'firestore'


def generate_id() -> str:
    '''Generate a unique ID.'''
    return str(uuid.uuid4())


class FakeDoc:
    '''Fake document that mimics Firestore DocumentSnapshot.'''
    def __init__(self, doc_id: str, data: dict):
        self.id = doc_id
        self._data = data
        self.exists = data is not None and len(data) > 0

    def to_dict(self):
        return self._data


class InMemoryDB:
    '''In-memory database for local development without Google Cloud credentials.'''

    def __init__(self):
        self._collections: dict[str, dict[str, dict]] = {}

    def collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = {}
        return CollectionRef(self._collections[name])


class CollectionRef:
    def __init__(self, data: dict):
        self._data = data

    def document(self, doc_id: str):
        return DocumentRef(self._data, doc_id)

    def stream(self, filters: Optional[list[tuple]] = None):
        results = []
        for doc_id, doc_data in self._data.items():
            if filters and not _matches(doc_data, filters):
                continue
            results.append(FakeDoc(doc_id, doc_data))
        return iter(results)


class DocumentRef:
    def __init__(self, collection_data: dict, doc_id: str):
        self._collection = collection_data
        self._id = doc_id

    def get(self):
        data = self._collection.get(self._id, {})
        return FakeDoc(self._id, data)

    def set(self, data: dict):
        self._collection[self._id] = data

    def update(self, data: dict):
        if self._id not in self._collection:
            self._collection[self._id] = {}
        self._collection[self._id].update(data)

    def delete(self):
        self._collection.pop(self._id, None)


class SqliteDB:
    '''SQLite-backed document store implementing the same API as InMemoryDB.

    One table with a (collection, doc_id) primary key; document data is
    stored as a JSON blob. All operations are serialized through a module
    write lock, so concurrent FastAPI worker threads are safe.
    '''

    def __init__(self, path: str):
        self.path = path
        data_dir = os.path.dirname(path)
        if data_dir:
            os.makedirs(data_dir, exist_ok=True)
        self._lock = threading.Lock()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, check_same_thread=False)

    def _init(self):
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    'CREATE TABLE IF NOT EXISTS metis_store ('
                    'collection TEXT NOT NULL, '
                    'doc_id TEXT NOT NULL, '
                    'data TEXT NOT NULL, '
                    'PRIMARY KEY (collection, doc_id))'
                )
                # Every list query filters on business_id; without this the
                # json_extract predicate degrades to a per-collection scan.
                conn.execute(
                    'CREATE INDEX IF NOT EXISTS idx_metis_store_business '
                    "ON metis_store (collection, json_extract(data, '$.business_id'))"
                )
                conn.commit()
            finally:
                conn.close()

    def collection(self, name: str):
        return SqliteCollectionRef(self, name)


class SqliteCollectionRef:
    def __init__(self, db: SqliteDB, name: str):
        self._db = db
        self._name = name

    def document(self, doc_id: str):
        return SqliteDocumentRef(self._db, self._name, doc_id)

    def stream(self, filters: Optional[list[tuple]] = None):
        sql = 'SELECT doc_id, data FROM metis_store WHERE collection = ?'
        params: list[Any] = [self._name]
        for field, op, value in (filters or []):
            # Guarded by _can_push before it reaches here; assert the invariant
            # rather than risk interpolating an arbitrary field into the path.
            if not _can_push(field, op, value):
                raise ValueError(f'filter not pushable to SQLite: {field!r} {op!r}')
            sql += f" AND json_extract(data, '$.{field}') {_PUSHDOWN_OPS[op]} ?"
            params.append(value)
        with self._db._lock:
            conn = self._db._connect()
            try:
                rows = conn.execute(sql, params).fetchall()
            finally:
                conn.close()
        results = []
        for doc_id, raw in rows:
            results.append(FakeDoc(doc_id, _load(raw)))
        return iter(results)


class SqliteDocumentRef:
    def __init__(self, db: SqliteDB, collection: str, doc_id: str):
        self._db = db
        self._collection = collection
        self._id = doc_id

    def get(self):
        with self._db._lock:
            conn = self._db._connect()
            try:
                row = conn.execute(
                    'SELECT data FROM metis_store WHERE collection = ? AND doc_id = ?',
                    (self._collection, self._id),
                ).fetchone()
            finally:
                conn.close()
        if row is None:
            return FakeDoc(self._id, {})
        return FakeDoc(self._id, _load(row[0]))

    def set(self, data: dict):
        with self._db._lock:
            conn = self._db._connect()
            try:
                conn.execute(
                    'INSERT OR REPLACE INTO metis_store (collection, doc_id, data) VALUES (?, ?, ?)',
                    (self._collection, self._id, _dump(data)),
                )
                conn.commit()
            finally:
                conn.close()

    def update(self, data: dict):
        existing = self.get().to_dict()
        if not existing:
            existing = {}
        existing.update(data)
        self.set(existing)

    def delete(self):
        with self._db._lock:
            conn = self._db._connect()
            try:
                conn.execute(
                    'DELETE FROM metis_store WHERE collection = ? AND doc_id = ?',
                    (self._collection, self._id),
                )
                conn.commit()
            finally:
                conn.close()


class FirestoreService:
    '''Generic Firestore CRUD service with in-memory fallback.'''

    def __init__(self, collection: str):
        self.collection = collection
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_db()
        return self._db

    def create(self, data: dict, doc_id: Optional[str] = None) -> str:
        doc_id = doc_id or generate_id()
        data['created_at'] = utcnow()
        data['updated_at'] = utcnow()
        self.db.collection(self.collection).document(doc_id).set(data)
        return doc_id

    def get(self, doc_id: str) -> Optional[dict]:
        doc = self.db.collection(self.collection).document(doc_id).get()
        if doc.exists:
            result = doc.to_dict()
            if result:
                result['id'] = doc.id
            return result
        return None

    def update(self, doc_id: str, data: dict) -> bool:
        data['updated_at'] = utcnow()
        doc_ref = self.db.collection(self.collection).document(doc_id)
        doc_ref.update(data)
        return True

    def delete(self, doc_id: str) -> bool:
        self.db.collection(self.collection).document(doc_id).delete()
        return True

    def _stream(self, filters: list[tuple]):
        '''Stream the collection with as many filters applied by the store as possible.'''
        coll = self.db.collection(self.collection)

        # Local backends take the filters directly.
        if isinstance(coll, (CollectionRef, SqliteCollectionRef)):
            return coll.stream(filters)

        # Real Firestore CollectionReference.
        if not filters:
            return coll.stream()
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = coll
        for field, op, value in filters:
            query = query.where(filter=FieldFilter(field, op, value))
        try:
            # Materialised inside the try: Firestore reports a missing index
            # lazily, on first iteration, not when stream() is called.
            return list(query.stream())
        except Exception as e:
            # Firestore raises FailedPrecondition (with a link to create the
            # index) for compound queries it has no composite index for. Keep
            # serving rather than 500ing, but make the cost loudly visible.
            print(
                f'WARNING: MISSING FIRESTORE INDEX for {self.collection} '
                f'{filters} ({e}); falling back to a full collection scan. '
                f'Add the index to deployment/firestore.indexes.json.'
            )
            return coll.stream()

    def list_all(self, filters: Optional[list[tuple]] = None) -> list[dict]:
        filters = list(filters or [])
        pushable: list[tuple] = []
        residual: list[tuple] = []
        for f in filters:
            (pushable if _can_push(*f) else residual).append(f)

        results = []
        for doc in self._stream(pushable):
            data = doc.to_dict()
            data['id'] = doc.id
            if residual and not _matches(data, residual):
                continue
            results.append(data)
        return results


# Collection-specific services (lazy initialization)
business_service = FirestoreService('businesses')
product_service = FirestoreService('products')
customer_service = FirestoreService('customers')
order_service = FirestoreService('orders')
agent_log_service = FirestoreService('agent_logs')
approval_service = FirestoreService('approvals')
chat_service = FirestoreService('chat_messages')
storefront_chat_service = FirestoreService('storefront_chat_messages')
app_state_service = FirestoreService('app_state')
