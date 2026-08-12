import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime
from typing import Optional, Any
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
                return datetime.fromisoformat(value[_DATETIME_MARKER])
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


def _default_db_path() -> str:
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(backend_root, 'data', 'metis.db')


def get_db():
    '''Get database client instance (lazy initialization).

    Uses Firestore when GOOGLE_CLOUD_PROJECT is configured, otherwise a
    local SQLite database so all data survives restarts.
    '''
    global _db
    if _db is None:
        if settings.GOOGLE_CLOUD_PROJECT:
            try:
                from google.cloud import firestore
                _db = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)
            except Exception as e:
                print(f'WARNING: Firestore client failed to initialize ({e}); switching to local SQLite database.')
                _db = SqliteDB(_default_db_path())
        else:
            print('INFO: GOOGLE_CLOUD_PROJECT not set; using local SQLite database. Data persists across restarts.')
            _db = SqliteDB(_default_db_path())
    return _db


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

    def stream(self):
        results = []
        for doc_id, doc_data in self._data.items():
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

    def stream(self):
        with self._db._lock:
            conn = self._db._connect()
            try:
                rows = conn.execute(
                    'SELECT doc_id, data FROM metis_store WHERE collection = ?',
                    (self._name,),
                ).fetchall()
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
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
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
        data['updated_at'] = datetime.utcnow()
        doc_ref = self.db.collection(self.collection).document(doc_id)
        doc_ref.update(data)
        return True

    def delete(self, doc_id: str) -> bool:
        self.db.collection(self.collection).document(doc_id).delete()
        return True

    def list_all(self, filters: Optional[list[tuple]] = None) -> list[dict]:
        docs = self.db.collection(self.collection).stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            if filters:
                match = True
                for field, op, value in filters:
                    field_val = data.get(field)
                    if op == '==' and field_val != value:
                        match = False
                        break
                    elif op == '>' and (field_val is None or field_val <= value):
                        match = False
                        break
                    elif op == '<' and (field_val is None or field_val >= value):
                        match = False
                        break
                if not match:
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
app_state_service = FirestoreService('app_state')
