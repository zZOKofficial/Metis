"""GET /api/agents/{business_id}/briefing — the Dashboard's voice briefing text.

Under mock AI mode (the fixture default) `ManagerAgent.produce_summary()`
builds the sentence directly from metrics instead of calling Gemini, so the
briefing always has real numbers with no key configured.
"""
import pytest


def test_briefing_mentions_revenue_orders_and_customers(client, business):
    product_id = client.post(f'/api/products/{business["id"]}', json={
        'name': 'Sky Blue Summer Shirt', 'price': 1499.0, 'stock': 12,
    }).json()['id']
    customer_id = client.post(f'/api/customers/{business["id"]}', json={'name': 'Nadia'}).json()['id']
    order = client.post(f'/api/orders/{business["id"]}', json={
        'customer_id': customer_id,
        'items': [{'product_id': product_id, 'quantity': 2}],
    }).json()
    client.put(f'/api/orders/{business["id"]}/{order["order_id"]}/status?status=confirmed')

    resp = client.get(f'/api/agents/{business["id"]}/briefing')
    assert resp.status_code == 200
    summary = resp.json()['summary']
    assert business['name'] in summary
    assert '৳2,998.00' in summary
    assert '1 order' in summary
    assert '1 customer' in summary


def test_briefing_flags_low_stock(client, business):
    client.post(f'/api/products/{business["id"]}', json={'name': 'Low Item', 'price': 10.0, 'stock': 2})

    resp = client.get(f'/api/agents/{business["id"]}/briefing')
    assert resp.status_code == 200
    summary = resp.json()['summary']
    assert 'Low Item' in summary
    assert 'restocking' in summary.lower()


def test_briefing_no_orders_yet(client, business):
    resp = client.get(f'/api/agents/{business["id"]}/briefing')
    assert resp.status_code == 200
    assert 'No orders yet' in resp.json()['summary']


def test_briefing_uses_business_currency(client):
    business_id = client.post('/api/business', json={'name': 'US Shop', 'currency': 'USD'}).json()['id']
    resp = client.get(f'/api/agents/{business_id}/briefing')
    assert resp.status_code == 200
    assert '$0.00' in resp.json()['summary']
