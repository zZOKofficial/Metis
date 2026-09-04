"""Demo seeding — one click builds a fully stocked comic store so judges and
owners see a living dashboard instead of an empty one."""
from typing import Optional

from .firestore import (
    business_service,
    product_service,
    customer_service,
    order_service,
)

DEMO_BUSINESS = {
    'name': "Deadpool's Den",
    'category': 'comics & collectibles',
    'description': 'Premium comics, shirts and collectibles — run by an AI workforce.',
    'contact_email': 'pool@deadpools-den.example',
    'phone': '+8801700000000',
    'operating_hours': '10AM - 10PM',
    'currency': 'BDT',
    'policies': {
        'returns': '14-day returns on sealed items',
        'shipping': 'Same-day delivery in Dhaka',
    },
    'goals': ['Grow summer shirt sales', 'Clear low-stock collectibles'],
}

DEMO_PRODUCTS = [
    {'name': 'Sky Blue Summer Shirt', 'description': 'Lightweight cotton shirt, summer fit.', 'price': 1499.0, 'stock': 12, 'product_key': 'SHIRT-SKY', 'category': 'apparel'},
    {'name': 'Crimson Summer Shirt', 'description': 'Bold red shirt, breathable fabric.', 'price': 1799.0, 'stock': 8, 'product_key': 'SHIRT-CRM', 'category': 'apparel'},
    {'name': "Deadpool's Golden Glock", 'description': 'Rare collectible replica — almost gone.', 'price': 999.0, 'stock': 3, 'product_key': 'GLOCK-DP', 'category': 'collectibles'},
    {'name': 'Bat-Mobile Scale Model', 'description': 'Die-cast 1:24 scale model, display case.', 'price': 4999.0, 'stock': 5, 'product_key': 'BATMOB-24', 'category': 'collectibles'},
    {'name': 'Deadpool Comics Bundle', 'description': 'Issues 1-10 in a slipcase.', 'price': 799.0, 'stock': 20, 'product_key': 'DP-BUNDLE', 'category': 'comics'},
]

DEMO_CUSTOMERS = [
    {'name': 'Nadia Rahman', 'email': 'nadia@example.com', 'phone': '+8801711111111'},
    {'name': 'Arif Chowdhury', 'email': 'arif@example.com', 'phone': '+8801722222222'},
    {'name': 'Tanvir Ahmed', 'email': 'tanvir@example.com', 'phone': '+8801733333333'},
]

DEMO_ORDERS = [
    # (customer_index, [(product_key, qty)], status)
    (0, [('SHIRT-SKY', 2)], 'delivered'),
    (1, [('DP-BUNDLE', 1), ('GLOCK-DP', 1)], 'shipped'),
    (2, [('BATMOB-24', 1)], 'confirmed'),
]


def seed_demo_business() -> dict:
    """Create a demo business with products, customers and orders.

    Returns the stored business document (with id).
    """
    business_id = business_service.create(dict(DEMO_BUSINESS))
    business = business_service.get(business_id)
    business['id'] = business_id

    product_ids: dict[str, str] = {}
    for p in DEMO_PRODUCTS:
        data = dict(p)
        data['business_id'] = business_id
        product_ids[p['product_key']] = product_service.create(data)

    customer_ids: list[str] = []
    for c in DEMO_CUSTOMERS:
        data = dict(c)
        data['business_id'] = business_id
        customer_ids.append(customer_service.create(data))

    from ..agents.registry import get_agent
    from ..models.schemas import AgentType, OrderStatus
    sales_agent = get_agent(AgentType.SALES, business_id)
    operations_agent = get_agent(AgentType.OPERATIONS, business_id)

    for customer_idx, items, status in DEMO_ORDERS:
        result = sales_agent.create_order(
            customer_id=customer_ids[customer_idx],
            items=[{'product_id': product_ids[key], 'quantity': qty} for key, qty in items],
        )
        if result.get('success'):
            order_id = result.get('order_id')
            if order_id and status != 'pending':
                operations_agent.update_order_status(order_id, OrderStatus(status))

    return business