"""Order creation, inventory/customer booking, status lifecycle, revenue."""
import pytest


@pytest.fixture()
def catalog(client, business):
    """A business with one product and one customer."""
    product_id = client.post(f'/api/products/{business["id"]}', json={
        'name': 'Sky Blue Summer Shirt', 'price': 1499.0, 'stock': 12,
    }).json()['id']
    customer_id = client.post(f'/api/customers/{business["id"]}', json={
        'name': 'Nadia Rahman',
    }).json()['id']
    return {'business_id': business['id'], 'product_id': product_id, 'customer_id': customer_id}


def _place_order(client, catalog, quantity=2):
    return client.post(f'/api/orders/{catalog["business_id"]}', json={
        'customer_id': catalog['customer_id'],
        'items': [{'product_id': catalog['product_id'], 'quantity': quantity}],
    })


def test_create_order_computes_total_server_side(client, catalog):
    resp = _place_order(client, catalog, quantity=2)
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['total_amount'] == pytest.approx(1499.0 * 2)


def test_create_order_decrements_inventory(client, catalog):
    _place_order(client, catalog, quantity=2)
    product = client.get(f'/api/products/{catalog["business_id"]}/{catalog["product_id"]}').json()
    assert product['stock'] == 10


def test_create_order_books_customer_stats_immediately(client, catalog):
    _place_order(client, catalog, quantity=2)
    customer = client.get(f'/api/customers/{catalog["business_id"]}/{catalog["customer_id"]}').json()
    assert customer['total_orders'] == 1
    assert customer['total_spent'] == pytest.approx(2998.0)


def test_create_order_insufficient_stock_rejected(client, catalog):
    resp = _place_order(client, catalog, quantity=999)
    assert resp.status_code == 400

    # Stock must be untouched by the rejected order.
    product = client.get(f'/api/products/{catalog["business_id"]}/{catalog["product_id"]}').json()
    assert product['stock'] == 12


def test_create_order_unknown_customer_rejected(client, catalog):
    resp = client.post(f'/api/orders/{catalog["business_id"]}', json={
        'customer_id': 'does-not-exist',
        'items': [{'product_id': catalog['product_id'], 'quantity': 1}],
    })
    assert resp.status_code == 400


def test_create_order_unknown_product_rejected(client, catalog):
    resp = client.post(f'/api/orders/{catalog["business_id"]}', json={
        'customer_id': catalog['customer_id'],
        'items': [{'product_id': 'does-not-exist', 'quantity': 1}],
    })
    assert resp.status_code == 400


def test_order_status_invalid_value_rejected(client, catalog):
    order_id = _place_order(client, catalog).json()['order_id']
    resp = client.put(f'/api/orders/{catalog["business_id"]}/{order_id}/status?status=teleported')
    assert resp.status_code == 400


def test_order_status_unknown_order_rejected(client, catalog):
    resp = client.put(f'/api/orders/{catalog["business_id"]}/does-not-exist/status?status=confirmed')
    assert resp.status_code == 400


def test_revenue_booked_only_when_confirmed(client, catalog):
    order_id = _place_order(client, catalog, quantity=2).json()['order_id']

    # Pending orders don't count toward recognized revenue yet.
    revenue = client.get(f'/api/analytics/{catalog["business_id"]}/revenue').json()
    assert revenue['total_revenue'] == 0.0

    resp = client.put(f'/api/orders/{catalog["business_id"]}/{order_id}/status?status=confirmed')
    assert resp.status_code == 200

    revenue = client.get(f'/api/analytics/{catalog["business_id"]}/revenue').json()
    assert revenue['total_revenue'] == pytest.approx(2998.0)


def test_cancelling_an_order_releases_stock_and_customer_spend(client, catalog):
    order_id = _place_order(client, catalog, quantity=2).json()['order_id']

    resp = client.put(f'/api/orders/{catalog["business_id"]}/{order_id}/status?status=cancelled')
    assert resp.status_code == 200

    product = client.get(f'/api/products/{catalog["business_id"]}/{catalog["product_id"]}').json()
    assert product['stock'] == 12

    customer = client.get(f'/api/customers/{catalog["business_id"]}/{catalog["customer_id"]}').json()
    assert customer['total_orders'] == 0
    assert customer['total_spent'] == pytest.approx(0.0)


def test_reviving_a_cancelled_order_reapplies_bookings(client, catalog):
    order_id = _place_order(client, catalog, quantity=2).json()['order_id']
    client.put(f'/api/orders/{catalog["business_id"]}/{order_id}/status?status=cancelled')

    resp = client.put(f'/api/orders/{catalog["business_id"]}/{order_id}/status?status=confirmed')
    assert resp.status_code == 200

    product = client.get(f'/api/products/{catalog["business_id"]}/{catalog["product_id"]}').json()
    assert product['stock'] == 10

    customer = client.get(f'/api/customers/{catalog["business_id"]}/{catalog["customer_id"]}').json()
    assert customer['total_orders'] == 1
    assert customer['total_spent'] == pytest.approx(2998.0)
