"""Customer CRUD."""


def test_create_and_list_customer(client, business):
    resp = client.post(f'/api/customers/{business["id"]}', json={
        'name': 'Nadia Rahman', 'email': 'nadia@example.com', 'phone': '+88017000000',
    })
    assert resp.status_code == 200
    customer_id = resp.json()['id']

    resp = client.get(f'/api/customers/{business["id"]}')
    assert resp.status_code == 200
    assert any(c['id'] == customer_id for c in resp.json())


def test_get_customer_not_found(client, business):
    resp = client.get(f'/api/customers/{business["id"]}/does-not-exist')
    assert resp.status_code == 404


def test_get_customer_wrong_business_is_404(client, business):
    customer_id = client.post(f'/api/customers/{business["id"]}', json={'name': 'Nadia'}).json()['id']
    other_id = client.post('/api/business', json={'name': 'Other Shop'}).json()['id']

    resp = client.get(f'/api/customers/{other_id}/{customer_id}')
    assert resp.status_code == 404
