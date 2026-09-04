"""POST /api/demo/seed — one-click demo store."""


def test_seed_demo_creates_full_store(client):
    resp = client.post('/api/demo/seed')
    assert resp.status_code == 200
    business_id = resp.json()['business_id']
    assert business_id

    products = client.get(f'/api/products/{business_id}').json()
    assert len(products) == 5

    customers = client.get(f'/api/customers/{business_id}').json()
    assert len(customers) == 3

    orders = client.get(f'/api/orders/{business_id}').json()
    assert len(orders) == 3
    statuses = {o['status'] for o in orders}
    assert statuses == {'delivered', 'shipped', 'confirmed'}


def test_seed_demo_is_isolated_per_call(client):
    """Each call seeds a brand new business — no collisions between demo runs."""
    first = client.post('/api/demo/seed').json()['business_id']
    second = client.post('/api/demo/seed').json()['business_id']
    assert first != second

    resp = client.get(f'/api/business/{second}')
    assert resp.status_code == 200
