from typing import Any

from .base import BaseAgent
from ..models.schemas import AgentType, AgentMessage, AgentResponse
from ..services.firestore import product_service, business_service, customer_service


class SupportAgent(BaseAgent):
    """Support Agent — handles customer questions, FAQs, and complaints."""

    @property
    def agent_name(self) -> str:
        return "Support Agent"

    @property
    def system_prompt(self) -> str:
        return """You are the Support Agent of METIS, an AI workforce for small businesses.

Your role:
- Answer customer questions about business policies and products
- Handle common complaints professionally
- Explain shipping, return, refund, and exchange policies
- Track customer issues
- Escalate complex issues to the business owner

Rules:
- NEVER invent policies, prices, or procedures
- ALWAYS use the provided business knowledge base
- If information is unavailable, escalate or ask for clarification
- Be empathetic and professional
- Never promise what the business doesn't offer
- When uncertain, say "Let me check with the owner" rather than guessing

Communication style: Empathetic, professional, patient."""

    def get_business_knowledge(self) -> dict[str, Any]:
        """Get business knowledge base for answering questions."""
        business = business_service.get(self.business_id)
        products = product_service.list_all(
            [("business_id", "==", self.business_id)]
        )
        return {
            "business": business,
            "products": products,
            "policies": business.get("policies", {}) if business else {},
            "operating_hours": business.get("operating_hours", "") if business else "",
        }

    def answer_question(self, question: str) -> str:
        """Answer a customer question using business knowledge."""
        knowledge = self.get_business_knowledge()
        business = knowledge.get("business", {})
        policies = knowledge.get("policies", {})
        products = knowledge.get("products", [])

        prompt = f"""A customer asked: "{question}"

Business Information:
- Name: {business.get('name', 'Our Store')}
- Category: {business.get('category', 'General')}
- Operating Hours: {knowledge.get('operating_hours', 'N/A')}

Policies:
{chr(10).join(f"- {k}: {v}" for k, v in policies.items()) if policies else "No specific policies listed."}

Available Products (for reference):
{chr(10).join(f"- {p['name']}: ৳{p['price']:,.2f}" for p in products[:10])}

Rules:
1. Only use the information provided above
2. If the answer isn't in the provided info, say you'll need to check with the owner
3. Never invent policies or prices
4. Be helpful and suggest alternatives when you don't have exact info

Provide a helpful, accurate response:"""

        response = self.think(prompt)

        self.log_action(
            action="answer_question",
            details={"question": question},
            result=response[:200],
        )

        return response

    def handle_complaint(self, complaint: str, customer_id: str = "") -> str:
        """Handle a customer complaint."""
        knowledge = self.get_business_knowledge()
        policies = knowledge.get("policies", {})

        prompt = f"""A customer complaint was received: "{complaint}"

Our Return/Refund Policy: {policies.get('return_policy', 'Not specified')}
Our General Policies: {chr(10).join(f"- {k}: {v}" for k, v in policies.items())}

Respond professionally:
1. Acknowledge their concern
2. Explain what can be done based on our policies
3. If the issue requires owner intervention, indicate escalation
4. Never promise something our policies don't support"""

        response = self.think(prompt)

        self.log_action(
            action="handle_complaint",
            details={"complaint": complaint, "customer_id": customer_id},
            result=response[:200],
        )

        return response

    def escalate_issue(self, issue: str, reason: str) -> dict[str, Any]:
        """Escalate an issue to the business owner."""
        self.log_action(
            action="escalate_issue",
            details={"issue": issue, "reason": reason},
            status="escalated",
        )

        return {
            "escalated": True,
            "issue": issue,
            "reason": reason,
            "message": "This issue has been escalated to the business owner.",
        }

    async def handle_message(self, message: AgentMessage) -> AgentResponse:
        """Handle a delegated task."""
        task = message.task.lower()

        if "complaint" in task:
            response = self.handle_complaint(
                message.task,
                message.context.get("customer_id", ""),
            )
        else:
            response = self.answer_question(message.task)

        return AgentResponse(
            success=True,
            agent=self.agent_type,
            task=message.task,
            result=response,
        )
