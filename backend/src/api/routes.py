from fastapi import APIRouter, HTTPException
from typing import Optional
from ..models.schemas import (
    BusinessCreate,
    ProductCreate,
    CustomerCreate,
    OrderCreate,
    ChatRequest, ChatResponse,
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

@router.post('/chat/{business_id}', response_model=ChatResponse)
def chat_with_manager(business_id: str, data: ChatRequest):
    from ..agents.registry import get_agent
    manager = get_agent(AgentType.MANAGER, business_id)
    context = manager.get_business_context()

    business = context.get('business', {})
    products = context.get('products', [])
    orders = context.get('orders', [])
    customers = context.get('customers', [])
    total_revenue = sum(o.get('total_amount', 0) for o in orders)
    low_stock = [p for p in products if p.get('stock', 0) <= 5]

    recent_orders = '\n'.join(f'  - Order {o["id"][:8]}: ৳{o["total_amount"]:,.2f} ({o["status"]})' for o in orders[:5])
    product_list = '\n'.join(f'  - {p["name"]}: ৳{p["price"]:,.2f} (Stock: {p.get("stock", 0)})' for p in products[:10])

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

The owner says: "{data.message}"

Respond helpfully using ONLY the data above. Be concise and specific. If they ask for something requiring action (like creating a campaign), explain what you can do and ask for confirmation.'''

    response = manager.think(prompt, temperature=0.6)
    manager.log_action(action='chat_response', details={'message': data.message}, result=response[:200])

    return ChatResponse(message=response)


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
    from datetime import datetime
    approval_service.update(approval_id, {
        'status': ApprovalStatus.APPROVED.value,
        'resolved_at': datetime.utcnow(),
    })
    return {'message': 'Action approved.', 'approval_id': approval_id}


@router.post('/approvals/{business_id}/{approval_id}/reject')
def reject_action(business_id: str, approval_id: str):
    approval = approval_service.get(approval_id)
    if not approval or approval.get('business_id') != business_id:
        raise HTTPException(status_code=404, detail='Approval not found.')
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
