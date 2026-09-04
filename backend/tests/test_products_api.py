"""Product CRUD, product_key uniqueness (409), and cross-business ownership (404)."""


def _create_product(client, business_id, **overrides):
    payload = {
        'name': 'Sky Blue Summer Shirt',
        'price': 1499.0,
        'stock': 12,
        'product_key': 'SHIRT-SKY',
        'category': 'apparel',
    }
    payload.update(overrides)
    return client.post(f'/api/products/{business_id}', json=payload)


def test_create_and_list_product(client, business):
    resp = _create_product(client, business['id'])
    assert resp.status_code == 200
    product_id = resp.json()['id']
    assert product_id

    resp = client.get(f'/api/products/{business["id"]}')
    assert resp.status_code == 200
    names = [p['name'] for p in resp.json()]
    assert 'Sky Blue Summer Shirt' in names


def test_duplicate_product_key_rejected(client, business):
    resp = _create_product(client, business['id'])
    assert resp.status_code == 200

    resp = _create_product(client, business['id'], name='Dup Shirt', product_key='SHIRT-SKY')
    assert resp.status_code == 409


def test_product_key_unique_per_business_not_global(client, business):
    resp = _create_product(client, business['id'])
    assert resp.status_code == 200

    other = client.post('/api/business', json={'name': 'Other Shop'})
    other_id = other.json()['id']
    resp = _create_product(client, other_id)
    assert resp.status_code == 200


def test_cross_business_product_fetch_is_404(client, business):
    product_id = _create_product(client, business['id']).json()['id']

    other = client.post('/api/business', json={'name': 'Other Shop'})
    other_id = other.json()['id']

    resp = client.get(f'/api/products/{other_id}/{product_id}')
    assert resp.status_code == 404

    resp = client.get(f'/api/products/{business["id"]}/{product_id}')
    assert resp.status_code == 200


def test_update_product(client, business):
    product_id = _create_product(client, business['id']).json()['id']

    resp = client.put(f'/api/products/{business["id"]}/{product_id}', json={'price': 1600.0})
    assert resp.status_code == 200

    resp = client.get(f'/api/products/{business["id"]}/{product_id}')
    assert resp.json()['price'] == 1600.0


def test_update_product_not_found(client, business):
    resp = client.put(f'/api/products/{business["id"]}/does-not-exist', json={'price': 1.0})
    assert resp.status_code == 404


def test_update_product_to_taken_key_is_409(client, business):
    p1 = _create_product(client, business['id']).json()['id']
    p2 = _create_product(client, business['id'], name='Crimson Shirt', product_key='SHIRT-CRM').json()['id']

    resp = client.put(f'/api/products/{business["id"]}/{p2}', json={'product_key': 'SHIRT-SKY'})
    assert resp.status_code == 409

    # A product may keep its own existing key without tripping the uniqueness check.
    resp = client.put(f'/api/products/{business["id"]}/{p1}', json={'product_key': 'SHIRT-SKY'})
    assert resp.status_code == 200


def test_delete_product(client, business):
    product_id = _create_product(client, business['id']).json()['id']

    resp = client.delete(f'/api/products/{business["id"]}/{product_id}')
    assert resp.status_code == 200

    resp = client.get(f'/api/products/{business["id"]}/{product_id}')
    assert resp.status_code == 404


def test_delete_product_wrong_business_is_404(client, business):
    product_id = _create_product(client, business['id']).json()['id']
    other_id = client.post('/api/business', json={'name': 'Other Shop'}).json()['id']

    resp = client.delete(f'/api/products/{other_id}/{product_id}')
    assert resp.status_code == 404

    # The product must survive an attempted cross-business delete.
    resp = client.get(f'/api/products/{business["id"]}/{product_id}')
    assert resp.status_code == 200
