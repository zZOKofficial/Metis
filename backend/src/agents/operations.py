from typing import Any

from .base import BaseAgent
from ..models.schemas import (
    AgentType,
    AgentMessage,
    AgentResponse,
    OrderStatus,
    ORDER_RELEASED_STATUSES,
)
from ..services.firestore import (
    order_service,
    product_service,
    customer_service,
)


class OperationsAgent(BaseAgent):
    '''Operations Agent - manages orders, inventory tracking, and operational issues.'''

    def __init__(self, business_id: str):
        super().__init__(AgentType.OPERATIONS, business_id)

    @property
    def agent_name(self) -> str:
        return 'Operations Agent'

    @property
    def system_prompt(self) -> str:
        return '''You are the Operations Agent of METIS.

Your role:
- Track and manage orders through their lifecycle
- Monitor inventory levels
- Detect and alert on low-stock products
- Generate operational summaries

Rules:
- Always use actual order and inventory data
- Never fabricate order status or inventory numbers
- Alert proactively when stock is low (5 or fewer items)
- Be precise with numbers and dates

Communication style: Organized, precise, proactive.'''

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        order = order_service.get(order_id)
        if not order or order.get('business_id') != self.business_id:
            return {'success': False, 'error': 'Order not found.'}
        self.log_action(action='check_order_status', details={'order_id': order_id, 'status': order.get('status')})
        return {'success': True, 'order_id': order_id, 'status': order.get('status'), 'total': order.get('total_amount'), 'items': order.get('items', []), 'created_at': str(order.get('created_at', ''))}

    def update_order_status(self, order_id: str, new_status: OrderStatus) -> dict[str, Any]:
        order = order_service.get(order_id)
        if not order or order.get('business_id') != self.business_id:
            return {'success': False, 'error': 'Order not found.'}
        old_status = order.get('status')
        if old_status == new_status.value:
            return {
                'success': True,
                'order_id': order_id,
                'old_status': old_status,
                'new_status': new_status.value,
            }

        # An order holds stock and counts toward customer spend from creation
        # until it reaches a released status (cancelled / returned). Moving
        # into a released status reverses those bookings; coming back out of
        # one re-applies them.
        was_released = old_status in ORDER_RELEASED_STATUSES
        is_released = new_status.value in ORDER_RELEASED_STATUSES
        if not was_released and is_released:
            self._release_order_bookings(order)
        elif was_released and not is_released:
            self._reapply_order_bookings(order)

        order_service.update(order_id, {'status': new_status.value})
        self.log_action(
            action='update_order_status',
            details={
                'order_id': order_id,
                'old_status': old_status,
                'new_status': new_status.value,
                'released': is_released and not was_released,
            },
            result=f'Order status: {old_status} -> {new_status.value}',
        )
        return {
            'success': True,
            'order_id': order_id,
            'old_status': old_status,
            'new_status': new_status.value,
        }

    def _release_order_bookings(self, order: dict[str, Any]) -> None:
        """Restore inventory and undo the customer spend booked at creation."""
        for item in order.get('items', []):
            product = product_service.get(item.get('product_id', ''))
            if product and product.get('business_id') == self.business_id:
                new_stock = product.get('stock', 0) + int(item.get('quantity', 0))
                update = {'stock': new_stock}
                if product.get('status') == 'out_of_stock' and new_stock > 0:
                    update['status'] = 'active'
                product_service.update(product['id'], update)
        customer = customer_service.get(order.get('customer_id', ''))
        if customer and customer.get('business_id') == self.business_id:
            customer_service.update(customer['id'], {
                'total_orders': max(0, customer.get('total_orders', 0) - 1),
                'total_spent': max(0.0, float(customer.get('total_spent', 0)) - float(order.get('total_amount', 0))),
            })

    def _reapply_order_bookings(self, order: dict[str, Any]) -> None:
        """Re-deduct inventory and re-book customer spend for a revived order."""
        for item in order.get('items', []):
            product = product_service.get(item.get('product_id', ''))
            if product and product.get('business_id') == self.business_id:
                product_service.update(product['id'], {
                    'stock': max(0, product.get('stock', 0) - int(item.get('quantity', 0))),
                })
        customer = customer_service.get(order.get('customer_id', ''))
        if customer and customer.get('business_id') == self.business_id:
            customer_service.update(customer['id'], {
                'total_orders': customer.get('total_orders', 0) + 1,
                'total_spent': customer.get('total_spent', 0) + float(order.get('total_amount', 0)),
            })

    def get_all_orders(self, status_filter: str = '') -> list[dict[str, Any]]:
        filters = [('business_id', '==', self.business_id)]
        if status_filter:
            filters.append(('status', '==', status_filter))
        return order_service.list_all(filters)

    def restock_product(self, product_ref: str, quantity: int) -> dict[str, Any]:
        '''Add stock to a product (restock). Resolves by ID or name.'''
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return {'success': False, 'error': 'Quantity must be a whole number.'}
        if quantity <= 0:
            return {'success': False, 'error': 'Quantity must be greater than zero.'}

        from ..agents.sales import SalesAgent
        product = SalesAgent(self.business_id).resolve_product(product_ref)
        if not product:
            return {'success': False, 'error': f'Product {product_ref} not found.'}

        old_stock = product.get('stock', 0)
        new_stock = old_stock + quantity
        update = {'stock': new_stock}
        if product.get('status') == 'out_of_stock' and new_stock > 0:
            update['status'] = 'active'
        product_service.update(product['id'], update)

        self.log_action(
            action='restock_product',
            details={'product_id': product['id'], 'quantity': quantity, 'old_stock': old_stock, 'new_stock': new_stock},
            result=f'Restocked {product["name"]}: {old_stock} -> {new_stock}',
        )
        return {
            'success': True,
            'product_id': product['id'],
            'name': product['name'],
            'old_stock': old_stock,
            'quantity_added': quantity,
            'new_stock': new_stock,
        }

    def check_inventory_levels(self) -> dict[str, Any]:
        products = product_service.list_all([('business_id', '==', self.business_id)])
        low_stock = []
        out_of_stock = []
        healthy = []
        for p in products:
            stock = p.get('stock', 0)
            if stock == 0:
                out_of_stock.append(p)
            elif stock <= 5:
                low_stock.append(p)
            else:
                healthy.append(p)
        alert_needed = len(low_stock) > 0 or len(out_of_stock) > 0
        if alert_needed:
            self.log_action(action='inventory_alert', details={'low_stock_count': len(low_stock), 'out_of_stock_count': len(out_of_stock)}, status='alert')
        return {'total_products': len(products), 'healthy': healthy, 'low_stock': low_stock, 'out_of_stock': out_of_stock, 'alert_needed': alert_needed}

    def generate_operations_summary(self) -> str:
        orders = self.get_all_orders()
        inventory = self.check_inventory_levels()
        pending_orders = [o for o in orders if o.get('status') == 'pending']
        processing = [o for o in orders if o.get('status') == 'processing']
        low_stock_names = chr(10).join(f'  - {p["name"]}: {p["stock"]} left' for p in inventory['low_stock'][:5])
        prompt = f'''Generate a brief operations summary based on this data:

Orders:
- Total: {len(orders)}
- Pending: {len(pending_orders)}
- Processing: {len(processing)}
- Completed: {len([o for o in orders if o.get("status") == "delivered"])}

Inventory:
- Total products: {inventory["total_products"]}
- Healthy stock: {len(inventory["healthy"])}
- Low stock: {len(inventory["low_stock"])}
- Out of stock: {len(inventory["out_of_stock"])}

Low stock items:
{low_stock_names}

Provide a 3-4 sentence operational summary with any urgent alerts.'''
        summary = self.think(prompt, temperature=0.4)
        self.log_action(action='operations_summary', details={'orders': len(orders), 'low_stock': len(inventory['low_stock'])}, result=summary[:200])
        return summary

    async def handle_message(self, message: AgentMessage) -> AgentResponse:
        task = message.task.lower()
        if 'order' in task and 'status' in task:
            order_id = message.context.get('order_id', '')
            if order_id:
                result = self.get_order_status(order_id)
            else:
                orders = self.get_all_orders()
                result = {'orders': orders, 'count': len(orders)}
            return AgentResponse(success=True, agent=self.agent_type, task=message.task, result=str(result), data=result)
        if 'inventory' in task or 'stock' in task:
            result = self.check_inventory_levels()
            summary = f'Inventory check: {result["total_products"]} products, {len(result["low_stock"])} low stock, {len(result["out_of_stock"])} out of stock.'
            return AgentResponse(success=True, agent=self.agent_type, task=message.task, result=summary, data=result)
        if 'update' in task and 'order' in task:
            order_id = message.context.get('order_id', '')
            status = message.context.get('status', 'confirmed')
            try:
                new_status = OrderStatus(status)
            except ValueError:
                new_status = OrderStatus.CONFIRMED
            result = self.update_order_status(order_id, new_status)
            return AgentResponse(success=result.get('success', False), agent=self.agent_type, task=message.task, result=f'Order {order_id} updated to {status}' if result.get('success') else result.get('error', 'Update failed'), data=result)
        summary = self.generate_operations_summary()
        return AgentResponse(success=True, agent=self.agent_type, task=message.task, result=summary)
