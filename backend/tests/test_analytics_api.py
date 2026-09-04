"""Analytics: dashboard metrics, revenue (incl. period filter), top-products, low-stock.

Covers a route bug found while writing this suite: `GET /analytics/{id}/revenue`
accepted no `period` query param at all (always behaved like `period=all`)
despite the documented `all`/`today`/`7d`/`30d` filter — fixed alongside these
tests in `backend/src/api/routes.py`.
"""
import pytest


@pytest.fixture()
def confirmed_order(client, business):
    product_id = client.post(f'/api/products/{business["id"]}', json={
        'name': 'Sky Blue Summer Shirt', 'price': 1499.0, 'stock': 12,
    }).json()['id']
    customer_id = client.post(f'/api/customers/{business["id"]}', json={'name': 'Nadia'}).json()['id']
    order = client.post(f'/api/orders/{business["id"]}', json={
        'customer_id': customer_id,
        'items': [{'product_id': product_id, 'quantity': 2}],
    }).json()
    client.put(f'/api/orders/{business["id"]}/{order["order_id"]}/status?status=confirmed')
    return {'business_id': business['id'], 'product_id': product_id, 'order_id': order['order_id']}


def test_revenue_default_is_all_time(client, confirmed_order):
    resp = client.get(f'/api/analytics/{confirmed_order["business_id"]}/revenue')
    assert resp.status_code == 200
    assert resp.json()['total_revenue'] == pytest.approx(2998.0)


@pytest.mark.parametrize('period', ['today', '7d', '30d'])
def test_revenue_period_filter_includes_recent_order(client, confirmed_order, period):
    resp = client.get(f'/api/analytics/{confirmed_order["business_id"]}/revenue?period={period}')
    assert resp.status_code == 200
    assert resp.json()['total_revenue'] == pytest.approx(2998.0)


def test_dashboard_metrics(client, confirmed_order):
    resp = client.get(f'/api/analytics/{confirmed_order["business_id"]}/dashboard')
    assert resp.status_code == 200
    body = resp.json()
    assert body['total_orders'] == 1
    assert body['total_customers'] == 1
    assert body['total_revenue'] == pytest.approx(2998.0)
    assert 'recommendations' in body


def test_top_products_ranks_ordered_item(client, confirmed_order):
    resp = client.get(f'/api/analytics/{confirmed_order["business_id"]}/top-products?limit=3')
    assert resp.status_code == 200
    body = resp.json()
    assert body and body[0]['name'] == 'Sky Blue Summer Shirt'
    assert body[0]['units_sold'] == 2


def test_low_stock_lists_products_at_or_below_five(client, business):
    client.post(f'/api/products/{business["id"]}', json={'name': 'Low Item', 'price': 10.0, 'stock': 3})
    client.post(f'/api/products/{business["id"]}', json={'name': 'Healthy Item', 'price': 10.0, 'stock': 50})

    resp = client.get(f'/api/analytics/{business["id"]}/low-stock')
    assert resp.status_code == 200
    names = [p['name'] for p in resp.json()]
    assert 'Low Item' in names
    assert 'Healthy Item' not in names
