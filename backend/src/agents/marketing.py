from typing import Any, Optional

from .base import BaseAgent
from ..models.schemas import AgentType, AgentMessage, AgentResponse, RiskLevel
from ..services.firestore import product_service, order_service


class MarketingAgent(BaseAgent):
    """Marketing Agent — creates campaigns, generates promotional content."""

    def __init__(self, business_id: str):
        super().__init__(AgentType.MARKETING, business_id)

    @property
    def agent_name(self) -> str:
        return "Marketing Agent"

    @property
    def system_prompt(self) -> str:
        return """You are the Marketing Agent of METIS, an AI workforce for small businesses.

Your role:
- Analyze products and identify promotional opportunities
- Generate social media content (Facebook, Instagram, etc.)
- Create marketing campaigns
- Write promotional copy
- Suggest target audiences
- Analyze campaign potential

Rules:
- Use actual product data, never fabricate
- Keep content appropriate for small business audiences
- Focus on practical, cost-effective marketing strategies
- All campaign suggestions must be actionable
- Consider the business type and target market
- Content should be ready-to-post with minimal editing

Communication style: Creative, enthusiastic, practical."""

    def analyze_promotion_opportunity(self) -> dict[str, Any]:
        """Analyze products to find promotion opportunities."""
        products = product_service.list_all(
            [("business_id", "==", self.business_id)]
        )

        if not products:
            return {"opportunities": [], "message": "No products to analyze."}

        # Find high-inventory, potentially slow-moving products
        opportunities = []
        for p in products:
            stock = p.get("stock", 0)
            price = p.get("price", 0)
            if stock > 10:
                opportunities.append({
                    "product": p,
                    "reason": "High inventory — good candidate for promotion",
                    "suggested_discount": "10-15%",
                })

        prompt = f"""Analyze these products for promotion opportunities:

{chr(10).join(f"- {p['name']}: ৳{p['price']:,.2f}, Stock: {p.get('stock', 0)}, Category: {p.get('category', 'N/A')}" for p in products)}

Which products would benefit most from a promotional campaign? Consider:
1. High stock levels
2. Seasonal relevance
3. Price point attractiveness
4. Category popularity

Provide 2-3 specific promotion ideas with reasoning."""

        analysis = self.think(prompt)

        self.log_action(
            action="analyze_promotions",
            details={"products_analyzed": len(products)},
            result=analysis[:200],
        )

        return {
            "opportunities": opportunities,
            "analysis": analysis,
        }

    def create_campaign(
        self,
        product_id: str = "",
        goal: str = "increase_sales",
        platform: str = "facebook",
    ) -> dict[str, Any]:
        """Create a marketing campaign for a product."""
        products = product_service.list_all(
            [("business_id", "==", self.business_id)]
        )

        if product_id:
            ref = (product_id or "").strip().lower()
            target_products = [
                p
                for p in products
                if p.get("id", "").lower() == ref
                or p.get("id", "").lower().startswith(ref)
                or p.get("name", "").lower() == ref
            ]
        else:
            target_products = products[:3]  # Top 3 products

        if not target_products:
            return {"success": False, "error": "No products found for campaign."}

        product_info = "\n".join(
            f"- {p['name']}: ৳{p['price']:,.2f} — {p.get('description', 'No description')}"
            for p in target_products
        )

        prompt = f"""Create a marketing campaign with these details:

Goal: {goal}
Platform: {platform}

Products to promote:
{product_info}

Create a complete campaign with:
1. Campaign name
2. Primary message/hook
3. Full post content (ready to publish)
4. Call-to-action
5. Suggested hashtags (5-8)
6. Visual suggestion (what image/video to use)

Format the response clearly with sections."""

        campaign_content = self.think(prompt, temperature=0.8)

        campaign = {
            "success": True,
            "goal": goal,
            "platform": platform,
            "products": [p["name"] for p in target_products],
            "content": campaign_content,
            "requires_approval": True,
            "status": "pending_approval",
        }

        self.log_action(
            action="create_campaign",
            details={
                "goal": goal,
                "platform": platform,
                "products": [p["id"] for p in target_products],
            },
            result=campaign_content[:200],
        )

        return campaign

    def generate_social_post(
        self,
        product_name: str = "",
        occasion: str = "",
        tone: str = "friendly",
    ) -> str:
        """Generate a social media post."""
        products = product_service.list_all(
            [("business_id", "==", self.business_id)]
        )

        product_context = ""
        if product_name:
            matching = [p for p in products if product_name.lower() in p.get("name", "").lower()]
            if matching:
                p = matching[0]
                product_context = f"Product: {p['name']}, Price: ৳{p['price']:,.2f}, Description: {p.get('description', '')}"

        prompt = f"""Write a social media post for our business.

{product_context}
Occasion/Topic: {occasion or 'General promotion'}
Tone: {tone}

Requirements:
- Keep it concise (2-3 short paragraphs max)
- Include a clear call-to-action
- Use engaging language appropriate for social media
- Add relevant hashtags
- Make it feel personal, not corporate

The post should be ready to copy and paste."""

        return self.think(prompt, temperature=0.8)

    async def handle_message(self, message: AgentMessage) -> AgentResponse:
        """Handle a delegated task."""
        task = message.task.lower()
        context = message.context

        if "campaign" in task:
            result = self.create_campaign(
                product_id=context.get("product_id", ""),
                goal=context.get("goal", "increase_sales"),
                platform=context.get("platform", "facebook"),
            )
            return AgentResponse(
                success=result.get("success", False),
                agent=self.agent_type,
                task=message.task,
                result=result.get("content", result.get("error", "")),
                data=result,
                requires_approval=True,
            )

        if "post" in task or "content" in task:
            content = self.generate_social_post(
                product_name=context.get("product_name", ""),
                occasion=context.get("occasion", ""),
            )
            return AgentResponse(
                success=True,
                agent=self.agent_type,
                task=message.task,
                result=content,
                requires_approval=True,
            )

        if "analyze" in task or "opportunity" in task:
            result = self.analyze_promotion_opportunity()
            return AgentResponse(
                success=True,
                agent=self.agent_type,
                task=message.task,
                result=result.get("analysis", ""),
                data=result,
            )

        # Default: analyze and create campaign
        result = self.create_campaign()
        return AgentResponse(
            success=result.get("success", False),
            agent=self.agent_type,
            task=message.task,
            result=result.get("content", result.get("error", "")),
            data=result,
            requires_approval=True,
        )
