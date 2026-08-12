from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime
from ..models.schemas import (
    BusinessCreate,
    ProductCreate,
    CustomerCreate,
    OrderCreate,
    ChatRequest, ChatResponse, ChatMessage,
    ApprovalStatus,
    OrderStatus,
    AgentType,
    RiskLevel,
)
from ..services.firestore import (
    business_service,
    product_service,
    customer_service,
    order_service,
    agent_log_service,
    approval_service,
    chat_service,
)

router = APIRouter()


# === Business ===

@router.post('/business', response_model=dict)
def create_business(data: BusinessCreate):
    business_id = business_service.create(data.model_dump())
    return {'id': business_id, 'message': 'Business created successfully.'}


@router.get('/business/{business_id}')
def get_business(business_id: str):
    business = business_service.get(business_id)
    if not business:
        raise HTTPException(status_code=404, detail='Business not found.')
    return business


@router.put('/business/{business_id}')
def update_business(business_id: str, data: dict):
    business_service.update(business_id, data)
    return {'message': 'Business updated.'}


# === Products ===

@router.post('/products/{business_id}')
def create_product(business_id: str, data: ProductCreate):
    product_data = data.model_dump()
    product_data['business_id'] = business_id
    product_id = product_service.create(product_data)
    return {'id': product_id, 'message': 'Product created.'}


@router.get('/products/{business_id}')
def list_products(business_id: str, category: str = '', in_stock: bool = False):
    filters = [('business_id', '==', business_id)]
    if category:
        filters.append(('category', '==', category))
    if in_stock:
        filters.append(('stock', '>', 0))
    return product_service.list_all(filters)


@router.get('/products/{business_id}/{product_id}')
def get_product(business_id: str, product_id: str):
    product = product_service.get(product_id)
    if not product or product.get('business_id') != business_id:
        raise HTTPException(status_code=404, detail='Product not found.')
    return product


@router.put('/products/{business_id}/{product_id}')
def update_product(business_id: str, product_id: str, data: dict):
    product_service.update(product_id, data)
    return {'message': 'Product updated.'}


@router.delete('/products/{business_id}/{product_id}')
def delete_product(business_id: str, product_id: str):
    product_service.delete(product_id)
    return {'message': 'Product deleted.'}


# === Customers ===

@router.post('/customers/{business_id}')
def create_customer(business_id: str, data: CustomerCreate):
    customer_data = data.model_dump()
    customer_data['business_id'] = business_id
    customer_id = customer_service.create(customer_data)
    return {'id': customer_id, 'message': 'Customer created.'}


@router.get('/customers/{business_id}')
def list_customers(business_id: str):
    return customer_service.list_all([('business_id', '==', business_id)])


@router.get('/customers/{business_id}/{customer_id}')
def get_customer(business_id: str, customer_id: str):
    customer = customer_service.get(customer_id)
    if not customer or customer.get('business_id') != business_id:
        raise HTTPException(status_code=404, detail='Customer not found.')
    return customer


# === Orders ===

@router.post('/orders/{business_id}')
def create_order(business_id: str, data: OrderCreate):
    from ..agents.registry import get_agent
    sales_agent = get_agent(AgentType.SALES, business_id)
    result = sales_agent.create_order(
        customer_id=data.customer_id,
        items=[item.model_dump() for item in data.items],
    )
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Order creation failed.'))
    return result


@router.get('/orders/{business_id}')
def list_orders(business_id: str, status: str = ''):
    filters = [('business_id', '==', business_id)]
    if status:
        filters.append(('status', '==', status))
    return order_service.list_all(filters)


@router.get('/orders/{business_id}/{order_id}')
def get_order(business_id: str, order_id: str):
    order = order_service.get(order_id)
    if not order or order.get('business_id') != business_id:
        raise HTTPException(status_code=404, detail='Order not found.')
    return order


@router.put('/orders/{business_id}/{order_id}/status')
def update_order_status(business_id: str, order_id: str, status: str):
    from ..agents.registry import get_agent
    operations_agent = get_agent(AgentType.OPERATIONS, business_id)
    try:
        new_status = OrderStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid status.')
    result = operations_agent.update_order_status(order_id, new_status)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result


# === Agents ===

@router.get('/agents/{business_id}')
def get_agent_status(business_id: str):
    agents = []
    for agent_type in AgentType:
        from ..agents.registry import get_agent
        agent = get_agent(agent_type, business_id)
        logs = agent_log_service.list_all([
            ('business_id', '==', business_id),
            ('agent_type', '==', agent_type.value),
        ])
        agents.append({
            'type': agent_type.value,
            'name': agent.agent_name,
            'status': 'active',
            'tasks_completed': len(logs),
        })
    return agents


@router.get('/agents/{business_id}/activity')
def get_agent_activity(business_id: str, agent_type: str = '', limit: int = 50):
    filters = [('business_id', '==', business_id)]
    if agent_type:
        filters.append(('agent_type', '==', agent_type))
    logs = agent_log_service.list_all(filters)
    return logs[:limit]


# === Chat ===

MAX_CHAT_HISTORY = 100
CHAT_CONTEXT_TURNS = 20


@router.get('/models')
def list_models():
    from ..services.gemini import gemini_service
    return {
        'models': gemini_service.AVAILABLE_MODELS,
        'default': gemini_service.MODEL,
    }


def _sorted_chat_history(business_id: str) -> list[dict]:
    """All stored chat messages for a business, oldest first."""
    messages = chat_service.list_all([('business_id', '==', business_id)])
    messages.sort(key=lambda m: m.get('created_at') or datetime.min)
    return messages


@router.get('/chat/{business_id}/history')
def get_chat_history(business_id: str, limit: int = 100):
    return _sorted_chat_history(business_id)[-limit:]


@router.post('/chat/{business_id}', response_model=ChatResponse)
def chat_with_manager(business_id: str, data: ChatRequest):
    from ..agents.registry import get_agent
    from ..services.actions import TOOL_DECLARATIONS, handle_tool_call
    from ..services.gemini import gemini_service

    model = data.model.strip()
    if model and not gemini_service.is_valid_model(model):
        raise HTTPException(status_code=400, detail=f"Unknown model '{model}'.")

    manager = get_agent(AgentType.MANAGER, business_id)
    context = manager.get_business_context()

    stored = _sorted_chat_history(business_id)

    # Seed server-side history from the client (e.g. pre-persistence conversations)
    if not stored and data.history:
        for msg in data.history:
            record = msg.model_dump()
            record['business_id'] = business_id
            chat_service.create(record)
        stored = _sorted_chat_history(business_id)

    # Persist the new user turn
    chat_service.create({
        'business_id': business_id,
        'role': 'user',
        'content': data.message,
        'timestamp': datetime.utcnow(),
    })

    # Exclude the turn just persisted: it is included in the prompt below
    history = _sorted_chat_history(business_id)[-CHAT_CONTEXT_TURNS:-1]

    business = context.get('business') or {}
    products = context.get('products') or []
    orders = context.get('orders') or []
    customers = context.get('customers') or []
    total_revenue = sum(float(o.get('total_amount') or 0) for o in orders)
    low_stock = [p for p in products if p.get('stock', 0) <= 5]

    recent_orders = '\n'.join(
        f'  - Order {str(o.get("id", ""))[:8]}: ৳{float(o.get("total_amount") or 0):,.2f} ({o.get("status", "unknown")})'
        for o in orders[:5]
    )
    product_list = '\n'.join(
        f'  - {p.get("name", "Unknown")}: ৳{float(p.get("price") or 0):,.2f} (Stock: {p.get("stock", 0)})'
        for p in products[:10]
    )
    customer_list = '\n'.join(
        f'  - {c.get("name", "Unknown")} (ID: {str(c.get("id", ""))[:8]})'
        for c in customers[:10]
    )

    prompt = f'''You are the Manager Agent for {business.get('name', 'this business')}.

Current Business Status:
- Revenue: ৳{total_revenue:,.2f}
- Orders: {len(orders)}
- Customers: {len(customers)}
- Products: {len(products)}
- Low stock items: {len(low_stock)}

Recent orders:
{recent_orders}

Products:
{product_list}

Customers:
{customer_list}

The owner says: "{data.message}"

You have tools available. Prefer calling a tool over guessing:
- For questions about performance, orders, inventory or products, call the matching read-only tool.
- If the owner asks to create an order or a marketing campaign, call the matching tool - it will create an approval request for the owner to review.
- If the owner asks to change an order's status, call update_order_status.

After the tools run, summarize concisely what you did or what is awaiting approval.'''

    agent_actions: list[dict] = []

    def _run_tool(name: str, args: dict) -> dict:
        outcome = handle_tool_call(business_id, name, args)
        agent_actions.append({
            'action': name,
            'status': outcome.get('status', 'failed'),
            'approval_id': outcome.get('approval_id'),
            'error': outcome.get('error'),
            'result': outcome.get('result'),
        })
        return outcome

    result = manager.gemini.run_with_tools(
        prompt,
        tools=TOOL_DECLARATIONS,
        on_call=_run_tool,
        system_instruction=manager.system_prompt,
        temperature=0.6,
        history=[{'role': m['role'], 'content': m['content']} for m in history],
        model=model or None,
    )
    response = result.get('text') or ''

    manager.log_action(
        action='chat_response',
        details={
            'message': data.message,
            'agent_actions': [a['action'] for a in agent_actions],
        },
        result=response[:200],
    )

    # Persist the assistant turn
    chat_service.create({
        'business_id': business_id,
        'role': 'assistant',
        'content': response,
        'timestamp': datetime.utcnow(),
    })

    # Trim history to the cap
    stored = _sorted_chat_history(business_id)
    if len(stored) > MAX_CHAT_HISTORY:
        for old in stored[:-MAX_CHAT_HISTORY]:
            chat_service.delete(old['id'])

    # Return full stored history so the client stays in sync
    final = _sorted_chat_history(business_id)[-50:]
    return ChatResponse(
        message=response,
        agent_actions=agent_actions,
        history=[
            ChatMessage(
                role=m['role'],
                content=m['content'],
                timestamp=m.get('timestamp') or m['created_at'],
            )
            for m in final
        ],
    )


# === Approvals ===

@router.get('/approvals/{business_id}')
def list_approvals(business_id: str, status: str = 'pending'):
    filters = [('business_id', '==', business_id)]
    if status:
        filters.append(('status', '==', status))
    return approval_service.list_all(filters)


@router.post('/approvals/{business_id}/{approval_id}/approve')
def approve_action(business_id: str, approval_id: str):
    approval = approval_service.get(approval_id)
    if not approval or approval.get('business_id') != business_id:
        raise HTTPException(status_code=404, detail='Approval not found.')
    if approval.get('status') != ApprovalStatus.PENDING.value:
        raise HTTPException(status_code=400, detail='Approval already resolved.')

    from datetime import datetime
    from ..services.actions import execute_staged_action

    result = execute_staged_action(business_id, approval)
    success = result.get('success', False)
    approval_service.update(approval_id, {
        'status': ApprovalStatus.APPROVED.value if success else ApprovalStatus.FAILED.value,
        'resolved_at': datetime.utcnow(),
        'execution': result,
    })
    if not success:
        raise HTTPException(status_code=400, detail={
            'message': 'Action could not be executed.',
            'approval_id': approval_id,
            'execution': result,
        })
    return {
        'message': 'Action approved and executed.',
        'approval_id': approval_id,
        'execution': result,
    }


@router.post('/approvals/{business_id}/{approval_id}/reject')
def reject_action(business_id: str, approval_id: str):
    approval = approval_service.get(approval_id)
    if not approval or approval.get('business_id') != business_id:
        raise HTTPException(status_code=404, detail='Approval not found.')
    if approval.get('status') != ApprovalStatus.PENDING.value:
        raise HTTPException(status_code=400, detail='Approval already resolved.')
    from datetime import datetime
    approval_service.update(approval_id, {
        'status': ApprovalStatus.REJECTED.value,
        'resolved_at': datetime.utcnow(),
    })
    return {'message': 'Action rejected.', 'approval_id': approval_id}


# === Analytics ===

@router.get('/analytics/{business_id}/dashboard')
def get_dashboard(business_id: str):
    from ..agents.registry import get_agent
    analytics = get_agent(AgentType.ANALYTICS, business_id)
    metrics = analytics.get_dashboard_metrics()
    recommendations = analytics.generate_recommendations()
    return {**metrics, 'recommendations': recommendations}


@router.get('/analytics/{business_id}/revenue')
def get_revenue(business_id: str):
    from ..agents.registry import get_agent
    analytics = get_agent(AgentType.ANALYTICS, business_id)
    return analytics.get_revenue()


@router.get('/analytics/{business_id}/top-products')
def get_top_products(business_id: str, limit: int = 5):
    from ..agents.registry import get_agent
    analytics = get_agent(AgentType.ANALYTICS, business_id)
    return analytics.get_top_products(limit)


@router.get('/analytics/{business_id}/low-stock')
def get_low_stock(business_id: str):
    from ..agents.registry import get_agent
    analytics = get_agent(AgentType.ANALYTICS, business_id)
    return analytics.get_low_stock_products()
