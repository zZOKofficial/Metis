"""Approval Center: staging, approve/reject, and execution-failure handling.

Approvals are staged directly through the Manager agent (bypassing chat/NLU,
which isn't the concern here) so these tests focus purely on the approve/
reject API and `execute_staged_action` dispatch.
"""
import pytest

from src.agents.registry import get_agent
from src.models.schemas import AgentType, RiskLevel


def _stage(business_id, agent_type, action, tool, params, risk=RiskLevel.MEDIUM):
    manager = get_agent(AgentType.MANAGER, business_id)
    return manager.request_approval(
        agent_type=agent_type,
        action=action,
        reason='test',
        risk_level=risk,
        details={'tool': tool, 'params': params},
    )


def test_approve_create_product_adds_to_catalog(client, business):
    approval_id = _stage(
        business['id'], AgentType.OPERATIONS, 'Create product "Red Cap"',
        'create_product', {'name': 'Red Cap', 'price': 450.0, 'stock': 10},
    )

    resp = client.post(f'/api/approvals/{business["id"]}/{approval_id}/approve')
    assert resp.status_code == 200

    products = client.get(f'/api/products/{business["id"]}').json()
    assert any(p['name'] == 'Red Cap' for p in products)


def test_approve_create_order_decrements_stock(client, business):
    product_id = client.post(f'/api/products/{business["id"]}', json={
        'name': 'Crimson Summer Shirt', 'price': 1799.0, 'stock': 8,
    }).json()['id']
    customer_id = client.post(f'/api/customers/{business["id"]}', json={'name': 'Nadia'}).json()['id']

    approval_id = _stage(
        business['id'], AgentType.SALES, 'Create order',
        'create_order', {'customer_id': customer_id, 'items': [{'product_id': product_id, 'quantity': 2}]},
    )

    resp = client.post(f'/api/approvals/{business["id"]}/{approval_id}/approve')
    assert resp.status_code == 200

    product = client.get(f'/api/products/{business["id"]}/{product_id}').json()
    assert product['stock'] == 6


def test_reject_leaves_catalog_unchanged(client, business):
    approval_id = _stage(
        business['id'], AgentType.OPERATIONS, 'Create product "Red Cap"',
        'create_product', {'name': 'Red Cap', 'price': 450.0},
    )

    resp = client.post(f'/api/approvals/{business["id"]}/{approval_id}/reject')
    assert resp.status_code == 200

    products = client.get(f'/api/products/{business["id"]}').json()
    assert not any(p['name'] == 'Red Cap' for p in products)

    pending = client.get(f'/api/approvals/{business["id"]}?status=pending').json()
    assert pending == []


def test_approve_unknown_id_is_404(client, business):
    resp = client.post(f'/api/approvals/{business["id"]}/does-not-exist/approve')
    assert resp.status_code == 404


def test_reject_unknown_id_is_404(client, business):
    resp = client.post(f'/api/approvals/{business["id"]}/does-not-exist/reject')
    assert resp.status_code == 404


def test_approve_already_resolved_is_400(client, business):
    approval_id = _stage(
        business['id'], AgentType.OPERATIONS, 'Create product "Red Cap"',
        'create_product', {'name': 'Red Cap', 'price': 450.0},
    )
    resp = client.post(f'/api/approvals/{business["id"]}/{approval_id}/approve')
    assert resp.status_code == 200

    resp = client.post(f'/api/approvals/{business["id"]}/{approval_id}/approve')
    assert resp.status_code == 400


def test_approve_failing_action_marks_failed_not_approved(client, business):
    product_id = client.post(f'/api/products/{business["id"]}', json={
        'name': 'Crimson Summer Shirt', 'price': 1799.0, 'stock': 1,
    }).json()['id']
    customer_id = client.post(f'/api/customers/{business["id"]}', json={'name': 'Nadia'}).json()['id']

    # Stage an order for more units than are in stock.
    approval_id = _stage(
        business['id'], AgentType.SALES, 'Create order',
        'create_order', {'customer_id': customer_id, 'items': [{'product_id': product_id, 'quantity': 99}]},
    )

    resp = client.post(f'/api/approvals/{business["id"]}/{approval_id}/approve')
    assert resp.status_code == 400
    assert 'execution' in resp.json()['detail']

    failed = client.get(f'/api/approvals/{business["id"]}?status=failed').json()
    assert any(a['id'] == approval_id for a in failed)

    # Stock must be untouched by the failed execution.
    product = client.get(f'/api/products/{business["id"]}/{product_id}').json()
    assert product['stock'] == 1


def test_approval_cross_business_is_404(client, business):
    approval_id = _stage(
        business['id'], AgentType.OPERATIONS, 'Create product "Red Cap"',
        'create_product', {'name': 'Red Cap', 'price': 450.0},
    )
    other_id = client.post('/api/business', json={'name': 'Other Shop'}).json()['id']

    resp = client.post(f'/api/approvals/{other_id}/{approval_id}/approve')
    assert resp.status_code == 404
