from typing import Any, Optional
from datetime import datetime

from .base import BaseAgent, can_request
from ..models.schemas import (
    AgentType,
    AgentMessage,
    AgentResponse,
    RiskLevel,
)
from ..services.firestore import (
    product_service,
    customer_service,
    order_service,
    approval_service,
    business_service,
    generate_id,
)


class ManagerAgent(BaseAgent):
    """Manager Agent — the central orchestrator of the METIS workforce."""

    def __init__(self, business_id: str):
        super().__init__(AgentType.MANAGER, business_id)
        self._pending_tasks: list[dict[str, Any]] = []

    @property
    def agent_name(self) -> str:
        return "Manager Agent"

    @property
    def system_prompt(self) -> str:
        return """You are the Manager Agent of METIS, an AI workforce for small businesses.

Your role:
- Understand the business owner's objectives
- Delegate tasks to specialized agents (Sales, Support, Marketing, Operations, Analytics)
- Coordinate between agents
- Monitor results and combine them into coherent summaries
- Request human approval for medium and high-risk actions
- Produce clear business summaries for the owner

Rules:
- Always delegate to the appropriate specialist agent
- Never do a specialist's job yourself
- Always verify results before reporting to the owner
- Be concise and actionable in your responses
- Use real data from the business, never fabricate numbers
- When uncertain, say so clearly

Communication style: Professional, direct, helpful."""

    def get_business_context(self) -> dict[str, Any]:
        """Gather current business context from all sources."""
        business = business_service.get(self.business_id)
        products = product_service.list_all(
            [("business_id", "==", self.business_id)]
        )
        orders = order_service.list_all(
            [("business_id", "==", self.business_id)]
        )
        customers = customer_service.list_all(
            [("business_id", "==", self.business_id)]
        )

        return {
            "business": business,
            "products": products,
            "orders": orders,
            "customers": customers,
            "product_count": len(products),
            "order_count": len(orders),
            "customer_count": len(customers),
        }

    def delegate_task(
        self, target: AgentType, task: str, context: dict[str, Any]
    ) -> AgentResponse:
        """Delegate a task to a specialized agent."""
        if not can_request(self.agent_type, target):
            return AgentResponse(
                success=False,
                agent=self.agent_type,
                task=task,
                result=f"Cannot delegate to {target.value}: permission denied.",
            )

        message = AgentMessage(
            requester=self.agent_type,
            target=target,
            task=task,
            context=context,
        )

        # Import here to avoid circular imports
        from .registry import get_agent

        agent = get_agent(target, self.business_id)
        import asyncio
        response = asyncio.get_event_loop().run_until_complete(
            agent.handle_message(message)
        )

        self.log_action(
            action="delegate_task",
            details={
                "target": target.value,
                "task": task,
                "context": context,
            },
            result=response.result,
        )

        return response

    def request_approval(
        self,
        agent_type: AgentType,
        action: str,
        reason: str,
        risk_level: RiskLevel,
        details: dict[str, Any],
    ) -> str:
        """Create an approval request for the business owner."""
        from ..models.schemas import ApprovalCreate

        approval = ApprovalCreate(
            agent_type=agent_type,
            action=action,
            reason=reason,
            risk_level=risk_level,
            details=details,
        )
        data = approval.model_dump()
        data["business_id"] = self.business_id
        data["status"] = "pending"
        approval_id = approval_service.create(data)

        self.log_action(
            action="request_approval",
            details={
                "approval_id": approval_id,
                "agent": agent_type.value,
                "action": action,
                "risk": risk_level.value,
            },
        )

        return approval_id

    def produce_summary(self) -> str:
        """Produce a business summary for the owner."""
        context = self.get_business_context()
        business = context.get("business", {})
        products = context.get("products", [])
        orders = context.get("orders", [])
        customers = context.get("customers", [])

        total_revenue = sum(o.get("total_amount", 0) for o in orders)
        low_stock = [p for p in products if p.get("stock", 0) <= 5]

        prompt = f"""Based on the following business data, produce a concise summary for the business owner.

Business: {business.get('name', 'Unknown')}
Category: {business.get('category', 'N/A')}

Key Metrics:
- Total Revenue: ৳{total_revenue:,.2f}
- Total Orders: {len(orders)}
- Total Customers: {len(customers)}
- Total Products: {len(products)}

Low Stock Products ({len(low_stock)}):
{chr(10).join(f"  - {p['name']}: {p['stock']} remaining" for p in low_stock[:5])}

Recent Orders:
{chr(10).join(f"  - Order {o['id'][:8]}: ৳{o['total_amount']:,.2f} ({o['status']})" for o in orders[:5])}

Provide a 3-4 sentence summary with one actionable recommendation."""

        return self.think(prompt, temperature=0.5)

    async def handle_message(self, message: AgentMessage) -> AgentResponse:
        """Handle incoming messages (usually from the owner via chat)."""
        self.memory.add_context(
            {"role": "requester", "content": message.task, "from": message.requester.value}
        )

        # Determine what the owner wants
        prompt = f"""The business owner said: "{message.task}"

Based on this request, determine which agent(s) should handle this and what specific task they should perform.

Available agents:
- sales: product inquiries, recommendations, order creation
- support: customer questions, FAQs, complaints
- marketing: campaigns, promotions, content
- operations: order management, inventory tracking
- analytics: business metrics, insights, reports

Respond in this format:
AGENT: <agent_type>
TASK: <specific task description>
REASON: <why this agent>"""

        response = self.think_structured(prompt)

        self.log_action(
            action="handle_owner_request",
            details={"message": message.task, "routing": response},
        )

        return AgentResponse(
            success=True,
            agent=self.agent_type,
            task=message.task,
            result=response,
        )
