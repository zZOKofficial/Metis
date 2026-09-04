"""Whose Gemini key gets spent.

Until 0.8.2 there was exactly one: a single `app_state/ai_config` document and
a process-wide cache, so on a shared backend the first owner to save a key paid
for everyone else's agents. These tests pin the boundary -- an owner's key is
theirs, another owner never reaches it, and the deployment's own env key stays
the shared fallback it was always meant to be.

No network: `test_key` is the only method that would make a request, and the
resolution being tested happens before any call.
"""
import pytest

from src.core import firebase
from src.core.config import settings
from src.services.firestore import app_state_service
from src.services.gemini import gemini_service


@pytest.fixture(autouse=True)
def clean_gemini(client, monkeypatch):
    """Every test starts with nothing resolved and no env key.

    Depends on `client` so it runs after it: the shared fixture turns mock AI
    mode on for the rest of the suite, and mock mode reports every caller as
    configured no matter whose key is set, which is the one thing these tests
    exist to observe.
    """
    monkeypatch.setattr(settings, 'GEMINI_API_KEY', '')
    monkeypatch.setattr(settings, 'METIS_MOCK_AI', False)
    gemini_service.reset_cache()
    yield
    gemini_service.reset_cache()


@pytest.fixture()
def tokens(monkeypatch):
    table = {'alice-token': 'alice', 'bob-token': 'bob'}
    monkeypatch.setattr(firebase, 'verify_token', lambda t: table.get(t))
    return table


def auth(token):
    return {'Authorization': f'Bearer {token}'}


# --- storage scoping ---------------------------------------------------------

def test_each_owner_gets_their_own_document():
    assert gemini_service.scope_doc_id('alice') == 'ai_config:alice'
    assert gemini_service.scope_doc_id('bob') == 'ai_config:bob'


def test_no_identity_uses_the_single_global_document():
    """A local install has always had one key; that must keep working."""
    assert gemini_service.scope_doc_id(None) == 'ai_config'
    assert gemini_service.scope_doc_id('') == 'ai_config'


# --- resolution --------------------------------------------------------------

def test_an_owner_never_inherits_another_owners_key(client):
    """The bug this change exists to fix."""
    app_state_service.create({'api_key': 'alice-secret'}, doc_id='ai_config:alice')
    gemini_service.reset_cache()

    assert gemini_service._effective_key('alice') == 'alice-secret'
    assert gemini_service._effective_key('bob') == ''
    assert gemini_service.is_configured('bob') is False


def test_an_owner_does_not_inherit_the_unscoped_key(client):
    """A key saved with auth off must not become everyone's key once auth is on."""
    app_state_service.create({'api_key': 'legacy-global'}, doc_id='ai_config')
    gemini_service.reset_cache()

    assert gemini_service._effective_key(None) == 'legacy-global'
    assert gemini_service._effective_key('alice') == ''


def test_the_env_key_is_the_shared_fallback(client, monkeypatch):
    """GEMINI_API_KEY belongs to whoever runs the deployment, so it is shared."""
    monkeypatch.setattr(settings, 'GEMINI_API_KEY', 'deployment-key')
    gemini_service.reset_cache()

    assert gemini_service._effective_key('alice') == 'deployment-key'
    assert gemini_service.key_source('alice') == 'env'


def test_a_saved_key_outranks_the_env_key(client, monkeypatch):
    monkeypatch.setattr(settings, 'GEMINI_API_KEY', 'deployment-key')
    app_state_service.create({'api_key': 'alice-secret'}, doc_id='ai_config:alice')
    gemini_service.reset_cache()

    assert gemini_service._effective_key('alice') == 'alice-secret'
    assert gemini_service.key_source('alice') == 'user'


def test_clients_are_not_shared_between_keys(client):
    """One owner's client must never serve another owner's request."""
    app_state_service.create({'api_key': 'alice-secret'}, doc_id='ai_config:alice')
    app_state_service.create({'api_key': 'bob-secret'}, doc_id='ai_config:bob')
    gemini_service.reset_cache()

    a = gemini_service._ensure_client('alice')
    b = gemini_service._ensure_client('bob')
    assert a is not b
    assert gemini_service._ensure_client('alice') is a, 'should be cached, not rebuilt'


# --- the routes --------------------------------------------------------------

def test_saving_a_key_scopes_it_to_the_caller(client, tokens, monkeypatch):
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)

    resp = client.post('/api/ai/config', json={'api_key': 'alice-secret'}, headers=auth('alice-token'))
    assert resp.status_code == 200
    assert app_state_service.get('ai_config:alice')['api_key'] == 'alice-secret'
    assert app_state_service.get('ai_config') is None, 'must not write the shared document'

    gemini_service.reset_cache()
    assert gemini_service._effective_key('bob') == ''


def test_models_reports_per_caller_configuration(client, tokens, monkeypatch):
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)
    client.post('/api/ai/config', json={'api_key': 'alice-secret'}, headers=auth('alice-token'))
    gemini_service.reset_cache()

    assert client.get('/api/models', headers=auth('alice-token')).json()['configured'] is True
    assert client.get('/api/models', headers=auth('bob-token')).json()['configured'] is False


def test_clearing_a_key_leaves_other_owners_alone(client, tokens, monkeypatch):
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)
    client.post('/api/ai/config', json={'api_key': 'alice-secret'}, headers=auth('alice-token'))
    client.post('/api/ai/config', json={'api_key': 'bob-secret'}, headers=auth('bob-token'))

    client.post('/api/ai/config/clear', headers=auth('alice-token'))
    gemini_service.reset_cache()

    assert gemini_service._effective_key('alice') == ''
    assert gemini_service._effective_key('bob') == 'bob-secret'


def test_anonymous_callers_cannot_set_a_key_when_auth_is_on(client, tokens, monkeypatch):
    """Otherwise anyone passing by could write the key every agent then spends."""
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)
    assert client.post('/api/ai/config', json={'api_key': 'x'}).status_code == 401
    assert client.post('/api/ai/config/clear').status_code == 401


def test_a_local_install_still_saves_one_key(client):
    """Auth off: unchanged behaviour, one key, no identity involved."""
    resp = client.post('/api/ai/config', json={'api_key': 'local-key'})
    assert resp.status_code == 200
    assert app_state_service.get('ai_config')['api_key'] == 'local-key'
    gemini_service.reset_cache()
    assert gemini_service._effective_key(None) == 'local-key'


# --- the agents --------------------------------------------------------------

def test_an_agent_spends_its_business_owners_key(client, tokens, monkeypatch):
    """The storefront matters most here: the shopper has no account and no key."""
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)
    business_id = client.post(
        '/api/business', json={'name': "Alice's Shop"}, headers=auth('alice-token')
    ).json()['id']

    from src.agents.registry import get_agent
    from src.models.schemas import AgentType
    agent = get_agent(AgentType.SALES, business_id)
    assert agent.owner_uid == 'alice'


def test_an_unowned_business_falls_back_to_the_global_key(client):
    """Businesses created before ownership existed keep working."""
    business_id = client.post('/api/business', json={'name': 'Legacy Shop'}).json()['id']

    from src.agents.registry import get_agent
    from src.models.schemas import AgentType
    agent = get_agent(AgentType.SALES, business_id)
    assert agent.owner_uid is None
