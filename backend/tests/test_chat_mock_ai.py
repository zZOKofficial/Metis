"""Owner chat under mock AI mode (METIS_MOCK_AI=1, no Gemini key needed).

Mock AI pattern-matches the raw message and dispatches straight to the same
tool the real model would call (`backend/src/services/gemini.py::_mock_run_with_tools`),
so these exercise the full chat -> tool -> approval/execution path
deterministically.
"""


def _chat(client, business_id, message):
    return client.post(f'/api/chat/{business_id}', json={'business_id': business_id, 'message': message})


def test_add_product_is_staged_for_approval(client, business):
    resp = _chat(client, business['id'], 'Add a product called "Red Cap" for 450')
    assert resp.status_code == 200
    body = resp.json()
    staged = [a for a in body['agent_actions'] if a.get('approval_id')]
    assert len(staged) == 1
    assert staged[0]['action'] == 'create_product'
    assert staged[0]['status'] == 'staged'

    # Not in the catalog until the owner approves.
    products = client.get(f'/api/products/{business["id"]}').json()
    assert not any(p['name'] == 'Red Cap' for p in products)

    resp = client.post(f'/api/approvals/{business["id"]}/{staged[0]["approval_id"]}/approve')
    assert resp.status_code == 200
    products = client.get(f'/api/products/{business["id"]}').json()
    assert any(p['name'] == 'Red Cap' for p in products)


def test_restock_executes_immediately_no_approval(client, business):
    product_id = client.post(f'/api/products/{business["id"]}', json={
        'name': 'Blue Shirt', 'price': 999.0, 'stock': 2,
    }).json()['id']

    resp = _chat(client, business['id'], 'restock Blue Shirt by 10')
    assert resp.status_code == 200
    body = resp.json()
    assert body['agent_actions'][0]['status'] == 'executed'
    assert body['agent_actions'][0]['approval_id'] is None

    product = client.get(f'/api/products/{business["id"]}/{product_id}').json()
    assert product['stock'] == 12


def test_mark_out_of_stock_executes_immediately(client, business):
    product_id = client.post(f'/api/products/{business["id"]}', json={
        'name': 'Golden Glock', 'price': 999.0, 'stock': 3,
    }).json()['id']

    resp = _chat(client, business['id'], 'mark Golden Glock as out of stock')
    assert resp.status_code == 200

    product = client.get(f'/api/products/{business["id"]}/{product_id}').json()
    assert product['stock'] == 0
    assert product['status'] == 'out_of_stock'


def test_set_stock_to_exact_level(client, business):
    product_id = client.post(f'/api/products/{business["id"]}', json={
        'name': 'Golden Glock', 'price': 999.0, 'stock': 3,
    }).json()['id']

    resp = _chat(client, business['id'], 'set stock of Golden Glock to 25')
    assert resp.status_code == 200

    product = client.get(f'/api/products/{business["id"]}/{product_id}').json()
    assert product['stock'] == 25


def test_delete_product_is_staged_for_approval(client, business):
    client.post(f'/api/products/{business["id"]}', json={'name': 'Red Cap', 'price': 450.0})

    resp = _chat(client, business['id'], 'delete product Red Cap')
    assert resp.status_code == 200
    staged = [a for a in resp.json()['agent_actions'] if a.get('approval_id')]
    assert len(staged) == 1
    assert staged[0]['action'] == 'delete_product'

    products = client.get(f'/api/products/{business["id"]}').json()
    assert any(p['name'] == 'Red Cap' for p in products)

    client.post(f'/api/approvals/{business["id"]}/{staged[0]["approval_id"]}/approve')
    products = client.get(f'/api/products/{business["id"]}').json()
    assert not any(p['name'] == 'Red Cap' for p in products)


def test_move_order_status_via_chat(client, business):
    product_id = client.post(f'/api/products/{business["id"]}', json={
        'name': 'Blue Shirt', 'price': 999.0, 'stock': 5,
    }).json()['id']
    customer_id = client.post(f'/api/customers/{business["id"]}', json={'name': 'Nadia'}).json()['id']
    order_id = client.post(f'/api/orders/{business["id"]}', json={
        'customer_id': customer_id,
        'items': [{'product_id': product_id, 'quantity': 1}],
    }).json()['order_id']

    resp = _chat(client, business['id'], f'move order {order_id} to shipped')
    assert resp.status_code == 200
    assert resp.json()['agent_actions'][0]['status'] == 'executed'

    order = client.get(f'/api/orders/{business["id"]}/{order_id}').json()
    assert order['status'] == 'shipped'


def test_unrecognized_message_gets_help_text_and_no_actions(client, business):
    resp = _chat(client, business['id'], 'How is the weather today?')
    assert resp.status_code == 200
    body = resp.json()
    assert body['agent_actions'] == []
    assert 'Mock AI mode' in body['message']


def test_chat_history_persists_across_turns(client, business):
    _chat(client, business['id'], 'How is the weather today?')
    _chat(client, business['id'], 'And now?')

    resp = client.get(f'/api/chat/{business["id"]}/history')
    assert resp.status_code == 200
    roles = [m['role'] for m in resp.json()]
    assert roles == ['user', 'assistant', 'user', 'assistant']
