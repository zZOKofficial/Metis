"""Shared pytest fixtures for the METIS backend test suite.

Every test gets a fresh, isolated SQLite database (a temp file per test) and
mock AI mode turned on, so the suite never touches the dev database
(`backend/data/metis.db`) and never needs a live Gemini key.
"""
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

# Allow `from src...` imports regardless of the directory pytest is invoked from.
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from src.core.config import settings  # noqa: E402
from src.services import firestore as firestore_module  # noqa: E402
from src.services.gemini import gemini_service  # noqa: E402

# Every FirestoreService singleton caches its own `_db` handle on first use,
# independently of the module-level `_db` global — all of them need to be
# reset alongside the module global for a test to actually get a clean slate.
_SERVICE_ATTRS = [
    'business_service',
    'product_service',
    'customer_service',
    'order_service',
    'agent_log_service',
    'approval_service',
    'chat_service',
    'storefront_chat_service',
    'app_state_service',
]


def _reset_db_handles():
    firestore_module._db = None
    for name in _SERVICE_ATTRS:
        getattr(firestore_module, name)._db = None


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """FastAPI TestClient wired to a fresh temp SQLite DB, mock AI mode on."""
    db_path = tmp_path / f'metis_test_{uuid.uuid4().hex}.db'
    monkeypatch.setattr(settings, 'METIS_DB_PATH', str(db_path))
    monkeypatch.setattr(settings, 'GOOGLE_CLOUD_PROJECT', '')
    monkeypatch.setattr(settings, 'GEMINI_API_KEY', '')
    monkeypatch.setattr(settings, 'METIS_MOCK_AI', True)
    _reset_db_handles()
    gemini_service.reset_cache()

    from src.main import app
    with TestClient(app) as test_client:
        yield test_client

    _reset_db_handles()


@pytest.fixture()
def business(client):
    """A created business, returned as {id, ...request payload}."""
    payload = {
        'name': 'Aurum Comics & Collectibles',
        'category': 'comic book store',
        'description': 'Local comic shop (test fixture)',
        'contact_email': 'owner@aurum.example',
        'phone': '+8801XXXXXX',
    }
    resp = client.post('/api/business', json=payload)
    assert resp.status_code == 200
    return {'id': resp.json()['id'], **payload}
