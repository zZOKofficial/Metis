from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
import json
from ..models.schemas import (
    BusinessCreate,
    ProductCreate,
    CustomerCreate,
    OrderCreate,
    ChatRequest, ChatResponse, ChatMessage,
    StorefrontChatRequest,
    ApprovalStatus,
    OrderStatus,
    AgentType,
    RiskLevel,
    AiConfigRequest,
    REVENUE_STATUSES,
)
from ..services.firestore import (
    business_service,
    product_service,
    customer_service,
    order_service,
    agent_log_service,
    approval_service,
    chat_service,
    storefront_chat_service,
    app_state_service,
)
from ..core.currency import currency_symbol
from ..core.auth import (
    require_business_access,
    get_business_or_404,
    get_current_uid,
    strip_protected_fields,
)

router = APIRouter()


# === Currencies ===

@router.get('/currencies')
def list_currencies():
    from ..core.currency import CURRENCIES, DEFAULT_CURRENCY
    return {'currencies': CURRENCIES, 'default': DEFAULT_CURRENCY}


# === Business ===

@router.post('/business', response_model=dict)
def create_business(data: BusinessCreate, uid: Optional[str] = Depends(get_current_uid)):
    payload = data.model_dump()
    payload['owner_uid'] = uid or ''
    business_id = business_service.create(payload)
    return {'id': business_id, 'message': 'Business created successfully.'}


@router.get('/business/{business_id}')
def get_business(business_id: str, business: dict = Depends(require_business_access)):
    return business


@router.put('/business/{business_id}')
def update_business(business_id: str, data: dict, _business: dict = Depends(require_business_access)):
    business_service.update(business_id, strip_protected_fields(data))
    return {'message': 'Business updated.'}


# === Demo ===

@router.post('/demo/seed')
def seed_demo(uid: Optional[str] = Depends(get_current_uid)):
    from ..services.demo import seed_demo_business
    business = seed_demo_business(owner_uid=uid or '')
    return {
        'business_id': business['id'],
        'business': business,
        'message': 'Demo store created — five products, three customers, three orders.',
    }


# === Products ===

def _product_key_taken(business_id: str, product_key: str, exclude_id: str = '') -> bool:
    '''True if another product in this business already has the given key.'''
    if not product_key:
        return False
    existing = product_service.list_all([
        ('business_id', '==', business_id),
        ('product_key', '==', product_key),
    ])
    return any(p['id'] != exclude_id for p in existing)


def _get_owned_product(business_id: str, product_id: str) -> dict:
    product = product_service.get(product_id)
    if not product or product.get('business_id') != business_id:
        raise HTTPException(status_code=404, detail='Product not found.')
    return product


@router.post('/products/{business_id}')
def create_product(business_id: str, data: ProductCreate, _business: dict = Depends(require_business_access)):
    product_data = data.model_dump()
    product_key = (product_data.get('product_key') or '').strip()
    if _product_key_taken(business_id, product_key):
        raise HTTPException(status_code=409, detail=f'A product with key "{product_key}" already exists.')
    product_data['product_key'] = product_key
    product_data['business_id'] = business_id
    product_id = product_service.create(product_data)
    return {'id': product_id, 'message': 'Product created.'}


@router.post('/products/{business_id}/from-photo')
async def draft_product_from_photo(business_id: str, file: UploadFile = File(...), _business: dict = Depends(require_business_access)):
    from ..services.gemini import gemini_service
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail='Uploaded file is empty.')
    draft = gemini_service.draft_product_from_image(image_bytes, file.content_type or 'image/jpeg')
    return draft


@router.get('/products/{business_id}')
def list_products(business_id: str, category: str = '', in_stock: bool = False, _business: dict = Depends(require_business_access)):
    filters = [('business_id', '==', business_id)]
    if category:
        filters.append(('category', '==', category))
    if in_stock:
        filters.append(('stock', '>', 0))
    return product_service.list_all(filters)


@router.get('/products/{business_id}/{product_id}')
def get_product(business_id: str, product_id: str, _business: dict = Depends(require_business_access)):
    return _get_owned_product(business_id, product_id)


@router.put('/products/{business_id}/{product_id}')
def update_product(business_id: str, product_id: str, data: dict, _business: dict = Depends(require_business_access)):
    _get_owned_product(business_id, product_id)
    if 'product_key' in data:
        product_key = (data.get('product_key') or '').strip()
        if _product_key_taken(business_id, product_key, exclude_id=product_id):
            raise HTTPException(status_code=409, detail=f'A product with key "{product_key}" already exists.')
        data['product_key'] = product_key
    product_service.update(product_id, data)
    return {'message': 'Product updated.'}


@router.delete('/products/{business_id}/{product_id}')
def delete_product(business_id: str, product_id: str, _business: dict = Depends(require_business_access)):
    _get_owned_product(business_id, product_id)
    product_service.delete(product_id)
    return {'message': 'Product deleted.'}


# === Customers ===

@router.post('/customers/{business_id}')
def create_customer(business_id: str, data: CustomerCreate, _business: dict = Depends(require_business_access)):
    customer_data = data.model_dump()
    customer_data['business_id'] = business_id
    customer_id = customer_service.create(customer_data)
    return {'id': customer_id, 'message': 'Customer created.'}


@router.get('/customers/{business_id}')
def list_customers(business_id: str, _business: dict = Depends(require_business_access)):
    return customer_service.list_all([('business_id', '==', business_id)])


@router.get('/customers/{business_id}/{customer_id}')
def get_customer(business_id: str, customer_id: str, _business: dict = Depends(require_business_access)):
    customer = customer_service.get(customer_id)
    if not customer or customer.get('business_id') != business_id:
        raise HTTPException(status_code=404, detail='Customer not found.')
    return customer


# === Orders ===

@router.post('/orders/{business_id}')
def create_order(business_id: str, data: OrderCreate, _business: dict = Depends(require_business_access)):
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
def list_orders(business_id: str, status: str = '', _business: dict = Depends(require_business_access)):
    filters = [('business_id', '==', business_id)]
    if status:
        filters.append(('status', '==', status))
    return order_service.list_all(filters)


@router.get('/orders/{business_id}/{order_id}')
def get_order(business_id: str, order_id: str, _business: dict = Depends(require_business_access)):
    order = order_service.get(order_id)
    if not order or order.get('business_id') != business_id:
        raise HTTPException(status_code=404, detail='Order not found.')
    return order


@router.put('/orders/{business_id}/{order_id}/status')
def update_order_status(business_id: str, order_id: str, status: str, _business: dict = Depends(require_business_access)):
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
def get_agent_status(business_id: str, _business: dict = Depends(require_business_access)):
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
def get_agent_activity(business_id: str, agent_type: str = '', limit: int = 50, _business: dict = Depends(require_business_access)):
    filters = [('business_id', '==', business_id)]
    if agent_type:
        filters.append(('agent_type', '==', agent_type))
    logs = agent_log_service.list_all(filters)
    return logs[:limit]


@router.get('/agents/{business_id}/briefing')
def get_voice_briefing(business_id: str, _business: dict = Depends(require_business_access)):
    '''A short spoken-style summary of the business, for the Dashboard's voice briefing button.'''
    from ..agents.registry import get_agent
    manager = get_agent(AgentType.MANAGER, business_id)
    summary = manager.produce_summary()
    return {'summary': summary}


# === Chat ===

MAX_CHAT_HISTORY = 100
CHAT_CONTEXT_TURNS = 20


# === AI Config ===

@router.post('/ai/config')
def save_ai_config(data: AiConfigRequest):
    from ..services.gemini import gemini_service
    key = data.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail='API key cannot be empty.')
    app_state_service.create({'api_key': key}, doc_id='ai_config')
    gemini_service.configure(key)
    return {'configured': True, 'key_source': 'user'}


@router.post('/ai/config/test')
def test_ai_config(data: AiConfigRequest):
    from ..services.gemini import gemini_service
    key = data.api_key.strip()
    return gemini_service.test_key(key or None)


@router.post('/ai/config/clear')
def clear_ai_config():
    from ..services.gemini import gemini_service
    app_state_service.delete('ai_config')
    gemini_service.configure('')
    return {
        'configured': gemini_service.is_configured(),
        'key_source': gemini_service.key_source(),
    }


@router.get('/models')
def list_models():
    from ..services.gemini import gemini_service
    return {
        'models': gemini_service.AVAILABLE_MODELS,
        'default': gemini_service.MODEL,
        'configured': gemini_service.is_configured(),
        'key_source': gemini_service.key_source(),
    }


def _sorted_chat_history(business_id: str) -> list[dict]:
    """All stored chat messages for a business, oldest first."""
    messages = chat_service.list_all([('business_id', '==', business_id)])
    messages.sort(key=lambda m: m.get('created_at') or datetime.min)
    return messages


@router.get('/chat/{business_id}/history')
def get_chat_history(business_id: str, limit: int = 100, _business: dict = Depends(require_business_access)):
    return _sorted_chat_history(business_id)[-limit:]


def _sse_event(payload: dict) -> str:
    return f'data: {json.dumps(payload, default=str)}\n\n'


def _sse_stream(response: ChatResponse):
    """Replay an already-computed ChatResponse as an SSE stream.

    Chunks `message` word-by-word so the client can render it
    progressively, then emits a final `done` event carrying the full
    response (agent_actions, synced history) so the client stays in sync
    exactly like the non-streaming endpoint.
    """
    import time

    words = response.message.split(' ') if response.message else []
    for i, word in enumerate(words):
        chunk = word if i == 0 else ' ' + word
        yield _sse_event({'type': 'delta', 'text': chunk})
        time.sleep(0.02)
    yield _sse_event({'type': 'done', 'response': json.loads(response.model_dump_json())})


def _process_manager_turn(business_id: str, data: ChatRequest) -> ChatResponse:
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
    total_revenue = sum(float(o.get('total_amount') or 0) for o in orders if o.get('status') in REVENUE_STATUSES)
    low_stock = [p for p in products if p.get('stock', 0) <= 5]
    currency = currency_symbol(business.get('currency', ''))

    recent_orders = '\n'.join(
        f'  - Order {str(o.get("id", ""))}: {currency}{float(o.get("total_amount") or 0):,.2f} ({o.get("status", "unknown")})'
        for o in orders[:5]
    )
    product_list = '\n'.join(
        f'  - {p.get("name", "Unknown")}: {currency}{float(p.get("price") or 0):,.2f} (ID: {str(p.get("id", ""))}, Stock: {p.get("stock", 0)})'
        for p in products[:10]
    )
    customer_list = '\n'.join(
        f'  - {c.get("name", "Unknown")} (ID: {str(c.get("id", ""))})'
        for c in customers[:10]
    )

    prompt = f'''You are the Manager Agent for {business.get('name', 'this business')}.

Current Business Status:
- Revenue: {currency}{total_revenue:,.2f}
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
- If the owner asks to restock a product (add stock / top up a product that is low or out of stock), call restock_product with the product ID and the quantity to add - it executes immediately.
- If the owner asks to set a product's stock to a specific level or mark a product out of stock (stock to zero), call set_stock with the product ID or name and the new quantity - it executes immediately.
- If the owner asks to add a new product to the catalog (with optional starting stock and product key), call create_product with the name, price and any other known details - it will create an approval request for the owner to review.
- If the owner asks to remove a product from the catalog, call delete_product with the product ID or name - it will create an approval request for the owner to review.

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
        raw_message=data.message,
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


@router.post('/chat/{business_id}', response_model=ChatResponse)
def chat_with_manager(business_id: str, data: ChatRequest, _business: dict = Depends(require_business_access)):
    return _process_manager_turn(business_id, data)


@router.post('/chat/{business_id}/stream')
def chat_with_manager_stream(business_id: str, data: ChatRequest, _business: dict = Depends(require_business_access)):
    response = _process_manager_turn(business_id, data)
    return StreamingResponse(_sse_stream(response), media_type='text/event-stream')


# === Storefront (public customer chat) ===

MAX_STOREFRONT_HISTORY = 100
STOREFRONT_CONTEXT_TURNS = 20


def _sorted_storefront_history(business_id: str, session_id: str) -> list[dict]:
    """All stored storefront chat messages for a business + session, oldest first."""
    messages = storefront_chat_service.list_all([
        ('business_id', '==', business_id),
        ('session_id', '==', session_id),
    ])
    messages.sort(key=lambda m: m.get('created_at') or datetime.min)
    return messages


@router.get('/storefront/{business_id}/history')
def get_storefront_history(business_id: str, session_id: str = '', limit: int = 100, _business: dict = Depends(get_business_or_404)):
    if not session_id:
        raise HTTPException(status_code=400, detail='session_id is required.')
    return _sorted_storefront_history(business_id, session_id)[-limit:]


def _process_storefront_turn(business_id: str, data: StorefrontChatRequest) -> ChatResponse:
    from ..services.actions import (
        STOREFRONT_TOOL_DECLARATIONS,
        handle_storefront_tool_call,
    )
    from ..services.gemini import gemini_service

    if not business_id or not business_service.get(business_id):
        raise HTTPException(status_code=404, detail='Store not found.')

    customer = None
    if data.customer_id:
        customer = customer_service.get(data.customer_id)
        if not customer or customer.get('business_id') != business_id:
            raise HTTPException(status_code=400, detail='Unknown customer for this store.')

    model = data.model.strip()
    if model and not gemini_service.is_valid_model(model):
        raise HTTPException(status_code=400, detail=f"Unknown model '{model}'.")

    business = business_service.get(business_id)
    session_id = data.session_id.strip() or 'public'

    stored = _sorted_storefront_history(business_id, session_id)

    # Seed server-side history from the client (e.g. pre-persistence conversations)
    if not stored and data.history:
        for msg in data.history:
            record = msg.model_dump()
            record['business_id'] = business_id
            record['session_id'] = session_id
            storefront_chat_service.create(record)
        stored = _sorted_storefront_history(business_id, session_id)

    # Persist the new user turn
    storefront_chat_service.create({
        'business_id': business_id,
        'session_id': session_id,
        'role': 'user',
        'content': data.message,
        'timestamp': datetime.utcnow(),
    })

    # Exclude the turn just persisted: it is included in the prompt below
    history = _sorted_storefront_history(business_id, session_id)[-STOREFRONT_CONTEXT_TURNS:-1]

    products = product_service.list_all([('business_id', '==', business_id)])
    currency = currency_symbol(business.get('currency', ''))
    product_list = '\n'.join(
        f'  - {p.get("name", "Unknown")}: {currency}{float(p.get("price") or 0):,.2f} (ID: {str(p.get("id", ""))}, Stock: {p.get("stock", 0)})'
        for p in products[:12]
    )

    prompt = f'''You are a shop assistant for {business.get('name', 'this store')} ({business.get('category', 'general store')}).

Catalog:
{product_list or '  - (the catalog is currently empty)'}

Customer: {customer['name'] if customer else 'a guest'} (customer ID: {customer['id'] if customer else 'unknown'})

A customer says: "{data.message}"

Be a helpful, honest shop assistant:
- Recommend only products from the catalog above — never invent products, prices, or stock.
- Mention what is in stock; note items with low stock.
- If the customer wants to buy one or more items, call create_order with the customer ID above and the exact product ID and quantity.
- Keep answers friendly and concise.'''

    agent_actions: list[dict] = []

    def _run_tool(name: str, args: dict) -> dict:
        # The storefront knows the shopper; never trust the model's customer id.
        if name == 'create_order' and customer:
            args = dict(args)
            args['customer_id'] = customer['id']
        outcome = handle_storefront_tool_call(business_id, name, args)
        agent_actions.append({
            'action': name,
            'status': outcome.get('status', 'failed'),
            'approval_id': outcome.get('approval_id'),
            'error': outcome.get('error'),
            'result': outcome.get('result'),
        })
        return outcome

    from ..agents.registry import get_agent
    sales_agent = get_agent(AgentType.SALES, business_id)

    result = gemini_service.run_with_tools(
        prompt,
        tools=STOREFRONT_TOOL_DECLARATIONS,
        on_call=_run_tool,
        system_instruction=sales_agent.system_prompt,
        temperature=0.6,
        history=[{'role': m['role'], 'content': m['content']} for m in history],
        model=model or None,
        raw_message=data.message,
    )
    response = result.get('text') or ''

    agent_log_service.create({
        'business_id': business_id,
        'agent_type': AgentType.SALES.value,
        'action': 'storefront_chat_response',
        'details': {
            'message': data.message,
            'session_id': session_id,
            'customer_id': customer['id'] if customer else '',
            'agent_actions': [a['action'] for a in agent_actions],
        },
        'status': 'completed',
        'result': response[:200],
    })

    # Persist the assistant turn
    storefront_chat_service.create({
        'business_id': business_id,
        'session_id': session_id,
        'role': 'assistant',
        'content': response,
        'timestamp': datetime.utcnow(),
    })

    # Trim history to the cap
    stored = _sorted_storefront_history(business_id, session_id)
    if len(stored) > MAX_STOREFRONT_HISTORY:
        for old in stored[:-MAX_STOREFRONT_HISTORY]:
            storefront_chat_service.delete(old['id'])

    # Return full stored history so the client stays in sync
    final = _sorted_storefront_history(business_id, session_id)[-50:]
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


@router.post('/storefront/{business_id}/chat', response_model=ChatResponse)
def storefront_chat(business_id: str, data: StorefrontChatRequest, _business: dict = Depends(get_business_or_404)):
    return _process_storefront_turn(business_id, data)


@router.post('/storefront/{business_id}/chat/stream')
def storefront_chat_stream(business_id: str, data: StorefrontChatRequest, _business: dict = Depends(get_business_or_404)):
    response = _process_storefront_turn(business_id, data)
    return StreamingResponse(_sse_stream(response), media_type='text/event-stream')


# === Approvals ===

@router.get('/approvals/{business_id}')
def list_approvals(business_id: str, status: str = 'pending', _business: dict = Depends(require_business_access)):
    filters = [('business_id', '==', business_id)]
    if status:
        filters.append(('status', '==', status))
    return approval_service.list_all(filters)


@router.post('/approvals/{business_id}/{approval_id}/approve')
def approve_action(business_id: str, approval_id: str, _business: dict = Depends(require_business_access)):
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
def reject_action(business_id: str, approval_id: str, _business: dict = Depends(require_business_access)):
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
def get_dashboard(business_id: str, _business: dict = Depends(require_business_access)):
    from ..agents.registry import get_agent
    analytics = get_agent(AgentType.ANALYTICS, business_id)
    metrics = analytics.get_dashboard_metrics()
    recommendations = analytics.generate_recommendations()
    return {**metrics, 'recommendations': recommendations}


@router.get('/analytics/{business_id}/revenue')
def get_revenue(business_id: str, period: str = 'all', _business: dict = Depends(require_business_access)):
    from ..agents.registry import get_agent
    analytics = get_agent(AgentType.ANALYTICS, business_id)
    return analytics.get_revenue(period)


@router.get('/analytics/{business_id}/top-products')
def get_top_products(business_id: str, limit: int = 5, _business: dict = Depends(require_business_access)):
    from ..agents.registry import get_agent
    analytics = get_agent(AgentType.ANALYTICS, business_id)
    return analytics.get_top_products(limit)


@router.get('/analytics/{business_id}/low-stock')
def get_low_stock(business_id: str, _business: dict = Depends(require_business_access)):
    from ..agents.registry import get_agent
    analytics = get_agent(AgentType.ANALYTICS, business_id)
    return analytics.get_low_stock_products()
