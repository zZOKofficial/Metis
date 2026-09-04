"""Identity resolution and the routes that mint ownership.

The suite never touches Firebase: `verify_token` is the single seam the app
uses (`src/core/firebase.py`), so patching it stands in for a real ID token.
That keeps these tests offline and free of any project configuration.
"""
import pytest

from src.core import firebase
from src.core.config import settings


@pytest.fixture()
def tokens(monkeypatch):
    """Map fake bearer tokens to uids, the way verified ID tokens would."""
    table = {'alice-token': 'alice', 'mallory-token': 'mallory'}
    monkeypatch.setattr(firebase, 'verify_token', lambda t: table.get(t))
    return table


def auth(token):
    return {'Authorization': f'Bearer {token}'}


# --- middleware --------------------------------------------------------------

def test_valid_bearer_token_becomes_the_caller_uid(client, tokens, monkeypatch):
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)
    business_id = client.post(
        '/api/business', json={'name': "Alice's Shop"}, headers=auth('alice-token')
    ).json()['id']
    stored = client.get(f'/api/business/{business_id}', headers=auth('alice-token')).json()
    assert stored['owner_uid'] == 'alice'


@pytest.mark.parametrize('header', [
    {},                                        # no header at all
    {'Authorization': 'Bearer garbage'},       # forged / expired
    {'Authorization': 'Basic alice-token'},    # wrong scheme
    {'Authorization': 'Bearer'},               # malformed, no token
    {'Authorization': ''},                     # empty
])
def test_unusable_credentials_are_anonymous_not_errors(client, tokens, header):
    """A bad token must degrade to 'not signed in', never a 500."""
    resp = client.get('/api/businesses', headers=header)
    assert resp.status_code == 200
    assert resp.json() == []  # auth off -> all businesses, and there are none yet


def test_verification_failure_does_not_break_public_routes(client, tokens, monkeypatch):
    """Storefront shoppers carry no token; the middleware must not reject them."""
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)
    business_id = client.post(
        '/api/business', json={'name': 'Open Shop'}, headers=auth('alice-token')
    ).json()['id']

    resp = client.get(f'/api/storefront/{business_id}/history?session_id=s1')
    assert resp.status_code == 200


def test_verify_token_returns_none_when_firebase_is_unavailable(monkeypatch):
    """No firebase-admin, no credentials, no project: still no exception."""
    firebase.reset_for_tests()
    monkeypatch.setattr(firebase, '_get_app', lambda: None)
    assert firebase.verify_token('anything') is None
    assert firebase.verify_token('') is None


# --- routes that mint ownership ---------------------------------------------

def test_creating_a_business_requires_a_caller_when_auth_is_on(client, tokens, monkeypatch):
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)
    assert client.post('/api/business', json={'name': 'Anon Shop'}).status_code == 401
    assert client.post('/api/demo/seed').status_code == 401


def test_creating_a_business_stays_open_when_auth_is_off(client, tokens):
    assert client.post('/api/business', json={'name': 'Local Shop'}).status_code == 200
    assert client.post('/api/demo/seed').status_code == 200


def test_demo_seed_is_owned_by_its_creator(client, tokens, monkeypatch):
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)
    business_id = client.post('/api/demo/seed', headers=auth('alice-token')).json()['business_id']
    stored = client.get(f'/api/business/{business_id}', headers=auth('alice-token')).json()
    assert stored['owner_uid'] == 'alice'


# --- GET /api/businesses -----------------------------------------------------

def test_businesses_lists_only_your_own(client, tokens, monkeypatch):
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)
    client.post('/api/business', json={'name': "Alice's Shop"}, headers=auth('alice-token'))
    client.post('/api/business', json={'name': "Mallory's Shop"}, headers=auth('mallory-token'))

    mine = client.get('/api/businesses', headers=auth('alice-token')).json()
    assert [b['name'] for b in mine] == ["Alice's Shop"]

    theirs = client.get('/api/businesses', headers=auth('mallory-token')).json()
    assert [b['name'] for b in theirs] == ["Mallory's Shop"]


def test_businesses_is_empty_for_an_anonymous_caller_when_auth_is_on(client, tokens, monkeypatch):
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)
    client.post('/api/business', json={'name': "Alice's Shop"}, headers=auth('alice-token'))
    assert client.get('/api/businesses').json() == []


def test_businesses_returns_everything_on_a_single_user_local_install(client, tokens):
    """With auth off there is no identity to filter by, so every shop is yours."""
    client.post('/api/business', json={'name': 'Shop One'})
    client.post('/api/business', json={'name': 'Shop Two'})
    assert len(client.get('/api/businesses').json()) == 2
