from typing import Any

from .base import BaseAgent
from ..models.schemas import AgentType, AgentMessage, AgentResponse, REVENUE_STATUSES
from ..services.firestore import order_service, product_service, customer_service, agent_log_service


class AnalyticsAgent(BaseAgent):
    '''Analytics Agent - converts business data into decisions and insights.'''

    def __init__(self, business_id: str):
        super().__init__(AgentType.ANALYTICS, business_id)

    @property
    def agent_name(self) -> str:
        return 'Analytics Agent'

    @property
    def system_prompt(self) -> str:
        return '''You are the Analytics Agent of METIS.

Your role:
- Analyze business performance data
- Identify trends and patterns
- Answer quantitative business questions
- Provide actionable recommendations
- Detect anomalies and opportunities

Rules:
- ALL numerical answers must come from actual stored business data
- Never fabricate or estimate numbers
- Be specific with figures and percentages
- When data is insufficient, say so clearly
- Always provide context with numbers

Communication style: Data-driven, precise, insightful.'''

    def get_revenue(self, period: str = 'all') -> dict[str, Any]:
        orders = order_service.list_all([('business_id', '==', self.business_id)])
        if period != 'all':
            from datetime import datetime, timedelta
            if period == 'today':
                cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == '7d':
                cutoff = datetime.utcnow() - timedelta(days=7)
            elif period == '30d':
                cutoff = datetime.utcnow() - timedelta(days=30)
            else:
                cutoff = None
            if cutoff is not None:
                orders = [
                    o for o in orders
                    if isinstance(o.get('created_at'), datetime) and o['created_at'] >= cutoff
                ]
        # Only confirmed/processing/shipped/delivered orders count as revenue.
        recognized = [o for o in orders if o.get('status') in REVENUE_STATUSES]
        total = sum(float(o.get('total_amount') or 0) for o in recognized)
        return {
            'total_revenue': total,
            'order_count': len(orders),
            'recognized_order_count': len(recognized),
            'average_order_value': total / len(recognized) if recognized else 0,
        }

    def get_top_products(self, limit: int = 5) -> list[dict[str, Any]]:
        orders = [o for o in order_service.list_all([('business_id', '==', self.business_id)]) if o.get('status') in REVENUE_STATUSES]
        product_sales = {}
        for order in orders:
            for item in order.get('items', []):
                pid = item.get('product_id', '')
                if pid not in product_sales:
                    product_sales[pid] = {'product_id': pid, 'name': item.get('product_name', ''), 'units_sold': 0, 'revenue': 0.0}
                product_sales[pid]['units_sold'] += item.get('quantity', 1)
                product_sales[pid]['revenue'] += item.get('total_price', 0)
        sorted_products = sorted(product_sales.values(), key=lambda x: x['revenue'], reverse=True)
        return sorted_products[:limit]

    def get_low_stock_products(self) -> list[dict[str, Any]]:
        products = product_service.list_all([('business_id', '==', self.business_id)])
        return [p for p in products if p.get('stock', 0) <= 5]

    def get_agent_activity(self) -> dict[str, int]:
        logs = agent_log_service.list_all([('business_id', '==', self.business_id)])
        activity = {}
        for log in logs:
            agent = log.get('agent_type', 'unknown')
            activity[agent] = activity.get(agent, 0) + 1
        return activity

    def get_dashboard_metrics(self) -> dict[str, Any]:
        revenue_data = self.get_revenue()
        top_products = self.get_top_products()
        low_stock = self.get_low_stock_products()
        agent_activity = self.get_agent_activity()
        customers = customer_service.list_all([('business_id', '==', self.business_id)])
        orders = order_service.list_all([('business_id', '==', self.business_id)])
        conversion_rate = (len(orders) / len(customers) * 100) if customers else 0
        return {
            'total_revenue': revenue_data['total_revenue'],
            'total_orders': revenue_data['order_count'],
            'total_customers': len(customers),
            'conversion_rate': round(conversion_rate, 1),
            'top_products': top_products,
            'low_stock_products': low_stock,
            'agent_activity_count': agent_activity,
            'average_order_value': revenue_data['average_order_value'],
        }

    def generate_recommendations(self) -> list[str]:
        metrics = self.get_dashboard_metrics()
        recommendations = []
        if metrics['low_stock_products']:
            names = ', '.join(p['name'] for p in metrics['low_stock_products'][:3])
            recommendations.append(f'Restock soon: {names} is running low on inventory.')
        if metrics['top_products']:
            top = metrics['top_products'][0]
            recommendations.append(f'Your best-seller is {top["name"]} - consider featuring it in marketing.')
        if metrics['conversion_rate'] < 50:
            recommendations.append('Conversion rate is below 50% - consider improving product descriptions or pricing.')
        if metrics['total_orders'] == 0:
            recommendations.append('No orders yet - start by promoting your products on social media.')
        if not recommendations:
            recommendations.append('Business is running smoothly! Consider expanding your product catalog.')
        return recommendations

    def answer_question(self, question: str) -> str:
        metrics = self.get_dashboard_metrics()
        prompt = f'''The business owner asked: "{question}"

Current Business Metrics:
- Total Revenue: ৳{metrics['total_revenue']:,.2f}
- Total Orders: {metrics['total_orders']}
- Total Customers: {metrics['total_customers']}
- Conversion Rate: {metrics['conversion_rate']}%
- Average Order Value: ৳{metrics['average_order_value']:,.2f}

Top Products:
{chr(10).join(f'  {i+1}. {p["name"]}: {p["units_sold"]} units, ৳{p["revenue"]:,.2f}' for i, p in enumerate(metrics['top_products']))}

Low Stock:
{chr(10).join(f'  - {p["name"]}: {p["stock"]} left' for p in metrics['low_stock_products'][:5]) if metrics['low_stock_products'] else '  None'}

Answer the question using ONLY the data above. Be specific with numbers.'''

        response = self.think(prompt, temperature=0.3)
        self.log_action(action='answer_analytics', details={'question': question}, result=response[:200])
        return response

    async def handle_message(self, message: AgentMessage) -> AgentResponse:
        task = message.task.lower()
        if 'dashboard' in task or 'metrics' in task or 'overview' in task:
            metrics = self.get_dashboard_metrics()
            recommendations = self.generate_recommendations()
            return AgentResponse(success=True, agent=self.agent_type, task=message.task, result=str(metrics), data={'metrics': metrics, 'recommendations': recommendations})
        if 'recommend' in task or 'suggest' in task or 'what should' in task:
            recommendations = self.generate_recommendations()
            return AgentResponse(success=True, agent=self.agent_type, task=message.task, result=chr(10).join(f'- {r}' for r in recommendations), data={'recommendations': recommendations})
        if 'revenue' in task or 'sales' in task:
            revenue = self.get_revenue()
            return AgentResponse(success=True, agent=self.agent_type, task=message.task, result=f'Total revenue: ৳{revenue["total_revenue"]:,.2f} from {revenue["order_count"]} orders.', data=revenue)
        if 'top' in task or 'best' in task or 'popular' in task:
            top = self.get_top_products()
            return AgentResponse(success=True, agent=self.agent_type, task=message.task, result=str(top), data={'top_products': top})
        response = self.answer_question(message.task)
        return AgentResponse(success=True, agent=self.agent_type, task=message.task, result=response)
