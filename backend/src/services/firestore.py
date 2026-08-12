import uuid
from datetime import datetime
from typing import Optional, Any
from ..core.config import settings

# Lazy database client
_db = None


def get_db():
    '''Get Firestore client instance (lazy initialization).'''
    global _db
    if _db is None:
        if settings.GOOGLE_CLOUD_PROJECT:
            try:
                from google.cloud import firestore
                _db = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)
            except Exception as e:
                print(f'WARNING: Firestore client failed to initialize ({e}); falling back to in-memory DB. Data will NOT persist.')
                _db = InMemoryDB()
        else:
            print('WARNING: GOOGLE_CLOUD_PROJECT not set; using in-memory DB. Data will NOT persist.')
            _db = InMemoryDB()
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
