#!/usr/bin/env python3
"""METIS end-to-end demo verification.

Tier A (deterministic, no AI): business -> products -> customers -> orders ->
inventory -> status -> analytics, plus product_key 409, ownership 404 and
approval reject paths.

Tier B (live Gemini, skipped without a key): owner chat stages create_product,
storefront chat stages create_order, both approved and verified.

Usage:
    METIS_API_URL=http://127.0.0.1:8001 python scripts/e2e_demo.py

Exit code 1 on any Tier A failure; Tier B problems are reported as warnings
(they depend on a live Gemini model).
"""
import json
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import httpx

API = os.environ.get('METIS_API_URL', 'http://127.0.0.1:8001').rstrip('/') + '/api'
HAS_GEMINI = bool(os.environ.get('GEMINI_API_KEY')) or os.environ.get('E2E_LIVE_AI', '1') == '1'

passed = 0
failed = 0
warnings = 0


def ok(step: str, detail: str = ''):
    global passed
    passed += 1
    print(f'  PASS  {step}' + (f'  [{detail}]' if detail else ''))


def fail(step: str, detail: str = ''):
    global failed
    failed += 1
    print(f'  FAIL  {step}' + (f'  [{detail}]' if detail else ''))


def warn(step: str, detail: str = ''):
    global warnings
    warnings += 1
    print(f'  WARN  {step}' + (f'  [{detail}]' if detail else ''))


def req(client, method, path, **kw):
    r = client.request(method, API + path, **kw)
    return r.status_code, (r.json() if r.content else None)


def main() -> int:
    client = httpx.Client(timeout=60)

    print('=== TIER A: deterministic REST flow ===')

    # 1. Business
    s, body = req(client, 'POST', '/business', json={
        'name': 'Aurum Comics & Collectibles',
        'category': 'comic book store',
        'description': 'Local comic shop (E2E demo)',
        'contact_email': 'owner@aurum.example',
        'phone': '+8801XXXXXX',
    })
    if s == 200 and body.get('id'):
        business_id = body['id']
        ok('create business', business_id[:8])
    else:
        fail('create business', f'{s} {body}')
        print(f'Aborting: cannot continue without a business.')
        return 1

    # 2. Products (summer collection)
    summer = [
        {'name': 'Sky Blue Summer Shirt', 'price': 1499.0, 'stock': 12,
         'product_key': 'SHIRT-SKY', 'category': 'apparel'},
        {'name': 'Crimson Summer Shirt', 'price': 1799.0, 'stock': 8,
         'product_key': 'SHIRT-CRM', 'category': 'apparel'},
        {'name': "Deadpool's Golden Glock", 'price': 999.0, 'stock': 3,
         'product_key': 'GLOCK-DP', 'category': 'collectibles'},
    ]
    product_ids = {}
    for p in summer:
        s, body = req(client, 'POST', f'/products/{business_id}', json=p)
        if s == 200 and body.get('id'):
            product_ids[p['name']] = body['id']
        else:
            fail('create product', f'{p["name"]}: {s} {body}')
    if len(product_ids) == 3:
        ok('create 3 products')

    # 3. Duplicate product_key -> 409
    s, _ = req(client, 'POST', f'/products/{business_id}',
               json={'name': 'Dup Shirt', 'price': 1.0, 'product_key': 'SHIRT-SKY'})
    ok('duplicate product_key -> 409', f'status {s}') if s == 409 else fail('duplicate product_key -> 409', f'status {s}')

    # 4. Ownership check -> 404 (fetch another business's product)
    s2, b2 = req(client, 'POST', '/business', json={'name': 'Other Shop'})
    other_bid = b2.get('id', '') if s2 == 200 and b2 else ''
    s, _ = req(client, 'GET', f'/products/{other_bid}/{product_ids["Sky Blue Summer Shirt"]}')
    if s == 404:
        ok('cross-business product fetch -> 404')
    else:
        fail('cross-business product fetch -> 404', f'status {s}')
    s, body = req(client, 'GET', f'/products/{business_id}/{product_ids["Sky Blue Summer Shirt"]}')
    if s == 200:
        ok('owned product fetch', '200')
    else:
        fail('owned product fetch', f'{s}')

    # 5. Customer
    s, body = req(client, 'POST', f'/customers/{business_id}', json={
        'name': 'Nadia Rahman', 'email': 'nadia@example.com', 'phone': '+88017...',
    })
    if s == 200 and body.get('id'):
        customer_id = body['id']
        ok('create customer', customer_id[:8])
    else:
        fail('create customer', f'{s} {body}')
        customer_id = ''

    # 6. Order with {product_id, quantity} contract
    shirt_id = product_ids['Sky Blue Summer Shirt']
    s, body = req(client, 'POST', f'/orders/{business_id}', json={
        'customer_id': customer_id,
        'items': [{'product_id': shirt_id, 'quantity': 2}],
    })
    if s == 200 and body.get('order_id'):
        order_id = body['order_id']
        ok('create order (qty contract)', body.get('order_id', '')[:8])
        order = body
        expected_total = 1499.0 * 2
        if abs(float(order.get('total_amount', 0)) - expected_total) < 0.01:
            ok('total computed server-side', f'৳{order["total_amount"]}')
        else:
            fail('total computed server-side', f'{order.get("total_amount")}')
    else:
        fail('create order', f'{s} {body}')
        order_id = ''

    # 7. Inventory decremented on order
    s, body = req(client, 'GET', f'/products/{business_id}/{shirt_id}')
    stock_after = body.get('stock') if s == 200 else None
    if stock_after == 10:
        ok('inventory decremented on order', f'12 -> {stock_after}')
    else:
        fail('inventory decremented on order', f'expected 10, got {stock_after}')

    # 8. Status -> confirmed -> revenue booked
    s, body = req(client, 'PUT', f'/orders/{business_id}/{order_id}/status?status=confirmed')
    ok('order status -> confirmed', f'{s}') if s == 200 else fail('order status -> confirmed', f'{s} {body}')

    s, body = req(client, 'GET', f'/analytics/{business_id}/revenue')
    if s == 200 and abs(float(body.get('total_revenue', 0)) - 2998.0) < 0.01:
        ok('revenue reflects confirmed order', f'৳{body["total_revenue"]}')
    else:
        fail('revenue reflects confirmed order', f'{s} {body}')

    s, body = req(client, 'GET', f'/analytics/{business_id}/dashboard')
    if s == 200 and body.get('total_orders') == 1 and body.get('total_customers') == 1:
        ok('dashboard metrics', f'{body.get("total_orders")} order, {body.get("total_customers")} customer')
    else:
        fail('dashboard metrics', f'{s} {body}')

    s, body = req(client, 'GET', f'/analytics/{business_id}/top-products?limit=3')
    if s == 200 and body and body[0].get('name') == 'Sky Blue Summer Shirt':
        ok('top-products ranks ordered item')
    else:
        fail('top-products ranks ordered item', f'{s} {body}')

    s, body = req(client, 'GET', f'/analytics/{business_id}/low-stock')
    if s == 200 and any(p.get('name') == "Deadpool's Golden Glock" for p in body):
        ok('low-stock lists Glock (stock 3 <= 5)')
    else:
        fail('low-stock lists Glock', f'{s} {body}')

    # 9. Approval reject path (stage via direct POST is not exposed; use list + reject of a bogus id)
    s, _ = req(client, 'POST', f'/approvals/{business_id}/bogus-id/reject')
    if s == 404:
        ok('approval reject guards unknown id -> 404')
    else:
        fail('approval reject guards unknown id', f'{s}')

    s, body = req(client, 'GET', f'/approvals/{business_id}?status=pending')
    if s == 200 and body == []:
        ok('no pending approvals yet')
    else:
        fail('no pending approvals yet', f'{s} {body}')

    # 10. Chat history endpoints respond
    s, body = req(client, 'GET', f'/chat/{business_id}/history')
    if s == 200 and body == []:
        ok('chat history endpoint (empty)')
    else:
        fail('chat history endpoint', f'{s} {body}')

    s, _ = req(client, 'GET', f'/storefront/{business_id}/history?session_id=e2e-session')
    ok('storefront history endpoint') if s == 200 else fail('storefront history endpoint', f'{s}')

    # 11. Agents endpoint
    s, body = req(client, 'GET', f'/agents/{business_id}')
    if s == 200 and len(body) == 6:
        ok('agent status lists 6 agents')
    else:
        fail('agent status lists 6 agents', f'{s} {body}')

    print()
    print('=== TIER B: live Gemini chat flow ===')

    # 12. Owner chat: stage create_product
    s, body = req(client, 'POST', f'/chat/{business_id}', json={
        'business_id': business_id,
        'message': 'Add a product called "E2E Test T-Shirt" priced at 550 taka with 20 in stock and product key E2E-TSHIRT.',
    })
    if s != 200:
        warn('owner chat reply', f'{s} {body}')
    else:
        ok('owner chat replied')
        staged = [a for a in body.get('agent_actions', []) if a.get('approval_id')]
        if staged:
            approval_id = staged[0]['approval_id']
            ok('create_product staged for approval', approval_id[:8])
            s2, b2 = req(client, 'POST', f'/approvals/{business_id}/{approval_id}/approve')
            if s2 == 200:
                ok('approval executed', b2.get('message', ''))
                s3, b3 = req(client, 'GET', f'/products/{business_id}')
                if any(p.get('name') == 'E2E Test T-Shirt' for p in b3):
                    ok('staged product now in catalog')
                else:
                    fail('staged product now in catalog')
            else:
                fail('approval executed', f'{s2} {b2}')
        else:
            warn('create_product staged', 'no approval_id in agent_actions')

    # 13. Storefront chat: stage create_order
    s, body = req(client, 'POST', f'/storefront/{business_id}/chat', json={
        'business_id': business_id,
        'session_id': 'e2e-session',
        'customer_id': customer_id,
        'message': 'I would like to buy 2 Crimson Summer Shirts please.',
    })
    if s != 200:
        warn('storefront chat reply', f'{s} {body}')
    else:
        ok('storefront chat replied')
        staged = [a for a in body.get('agent_actions', []) if a.get('approval_id')]
        if staged:
            approval_id = staged[0]['approval_id']
            ok('create_order staged from storefront', approval_id[:8])
            s2, b2 = req(client, 'POST', f'/approvals/{business_id}/{approval_id}/approve')
            if s2 == 200:
                ok('storefront order approved & executed')
                s3, b3 = req(client, 'GET', f'/products/{business_id}/{product_ids["Crimson Summer Shirt"]}')
                if b3 and b3.get('stock') == 6:
                    ok('storefront order decremented stock', '8 -> 6')
                else:
                    fail('storefront order decremented stock', f'{s3} {b3}')
            else:
                fail('storefront order approved & executed', f'{s2} {b2}')
        else:
            warn('create_order staged from storefront', 'no approval_id in agent_actions')

    print()
    print(f'RESULT: {passed} passed, {failed} failed, {warnings} warnings')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())