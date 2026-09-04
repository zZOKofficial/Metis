"""Business-scoped routes verify the business in the URL.

Before this, every owner route took `business_id` from the path and trusted
it: an unknown id returned an empty list (or silently created a document),
and once the API is hosted, one tenant's id in another tenant's URL would have
returned that tenant's data.
"""
import pytest

from src.core import auth
from src.core.config import settings
from src.main import app


# --- existence, with auth off (current default) ------------------------------

BOGUS = 'no-such-business'

OWNER_GETS = [
    f'/api/business/{BOGUS}',
    f'/api/products/{BOGUS}',
    f'/api/customers/{BOGUS}',
    f'/api/orders/{BOGUS}',
    f'/api/agents/{BOGUS}',
    f'/api/agents/{BOGUS}/activity',
    f'/api/agents/{BOGUS}/briefing',
    f'/api/chat/{BOGUS}/history',
    f'/api/approvals/{BOGUS}',
    f'/api/analytics/{BOGUS}/dashboard',
    f'/api/analytics/{BOGUS}/revenue',
    f'/api/analytics/{BOGUS}/top-products',
    f'/api/analytics/{BOGUS}/low-stock',
]


@pytest.mark.parametrize('path', OWNER_GETS)
def test_unknown_business_is_404_not_empty(client, path):
    assert client.get(path).status_code == 404


def test_unknown_business_rejected_on_writes(client):
    assert client.post(f'/api/products/{BOGUS}', json={'name': 'X', 'price': 1}).status_code == 404
    assert client.post(f'/api/customers/{BOGUS}', json={'name': 'X'}).status_code == 404
    assert client.post(f'/api/chat/{BOGUS}', json={'message': 'hi'}).status_code == 404


def test_update_to_unknown_business_no_longer_creates_it(client):
    """PUT used to write blindly, conjuring a business at an arbitrary id."""
    assert client.put(f'/api/business/{BOGUS}', json={'name': 'Ghost'}).status_code == 404
    assert client.get(f'/api/business/{BOGUS}').status_code == 404


def test_storefront_is_public_but_still_validates_the_business(client):
    assert client.get(f'/api/storefront/{BOGUS}/history').status_code == 404


def test_storefront_stays_reachable_for_a_real_business(client, business):
    assert client.get(f"/api/storefront/{business['id']}/history?session_id=s1").status_code == 200


def test_protected_fields_cannot_be_set_through_update(client, business):
    resp = client.put(f"/api/business/{business['id']}", json={
        'name': 'Renamed',
        'owner_uid': 'attacker',
        'id': 'hijacked',
    })
    assert resp.status_code == 200
    stored = client.get(f"/api/business/{business['id']}").json()
    assert stored['name'] == 'Renamed'
    assert stored.get('owner_uid', '') != 'attacker'
    assert stored['id'] == business['id']


# --- ownership, with auth on -------------------------------------------------

@pytest.fixture()
def as_user(client, monkeypatch):
    """Enable auth and let a test choose which uid is calling."""
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)
    state = {'uid': None}
    app.dependency_overrides[auth.get_current_uid] = lambda: state['uid']

    def _login(uid):
        state['uid'] = uid
        return client

    yield _login
    app.dependency_overrides.pop(auth.get_current_uid, None)


def test_creator_becomes_the_owner(as_user):
    client = as_user('alice')
    business_id = client.post('/api/business', json={'name': "Alice's Shop"}).json()['id']
    assert client.get(f'/api/business/{business_id}').json()['owner_uid'] == 'alice'


def test_another_user_cannot_read_or_write_the_business(as_user):
    client = as_user('alice')
    business_id = client.post('/api/business', json={'name': "Alice's Shop"}).json()['id']
    client.post(f'/api/products/{business_id}', json={'name': 'Rare Comic', 'price': 500})
    assert len(client.get(f'/api/products/{business_id}').json()) == 1

    client = as_user('mallory')
    # 404, not 403 -- a 403 would confirm the business id exists.
    assert client.get(f'/api/business/{business_id}').status_code == 404
    assert client.get(f'/api/products/{business_id}').status_code == 404
    assert client.get(f'/api/orders/{business_id}').status_code == 404
    assert client.get(f'/api/analytics/{business_id}/dashboard').status_code == 404
    assert client.post(f'/api/chat/{business_id}', json={'message': 'hi'}).status_code == 404
    assert client.put(f'/api/business/{business_id}', json={'name': 'Owned'}).status_code == 404


def test_owner_still_has_full_access(as_user):
    client = as_user('alice')
    business_id = client.post('/api/business', json={'name': "Alice's Shop"}).json()['id']
    assert client.get(f'/api/business/{business_id}').status_code == 200
    assert client.get(f'/api/products/{business_id}').status_code == 200
    assert client.get(f'/api/analytics/{business_id}/dashboard').status_code == 200


def test_storefront_stays_open_to_anonymous_shoppers(as_user):
    """Customers have no account, so ownership must not apply to the storefront."""
    client = as_user('alice')
    business_id = client.post('/api/business', json={'name': "Alice's Shop"}).json()['id']

    client = as_user(None)  # a shopper, signed in to nothing
    assert client.get(f'/api/storefront/{business_id}/history?session_id=s1').status_code == 200


def test_businesses_created_before_auth_are_not_locked_out(as_user):
    """Pre-auth rows have no owner_uid; they must stay reachable, not 404."""
    from src.services.firestore import business_service
    legacy_id = business_service.create({'name': 'Legacy Shop', 'currency': 'BDT'})

    client = as_user('alice')
    assert client.get(f'/api/business/{legacy_id}').status_code == 200
