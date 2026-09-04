"""Business CRUD."""


def test_create_and_get_business(client):
    resp = client.post('/api/business', json={'name': 'Deadpool\'s Den', 'category': 'comics'})
    assert resp.status_code == 200
    business_id = resp.json()['id']
    assert business_id

    resp = client.get(f'/api/business/{business_id}')
    assert resp.status_code == 200
    assert resp.json()['name'] == "Deadpool's Den"


def test_get_business_not_found(client):
    resp = client.get('/api/business/does-not-exist')
    assert resp.status_code == 404


def test_update_business(client, business):
    resp = client.put(f'/api/business/{business["id"]}', json={'name': 'Renamed Shop'})
    assert resp.status_code == 200

    resp = client.get(f'/api/business/{business["id"]}')
    assert resp.json()['name'] == 'Renamed Shop'
