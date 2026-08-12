from typing import Any, Optional
from datetime import datetime

from .base import BaseAgent
from ..models.schemas import (
    AgentType,
    AgentMessage,
    AgentResponse,
    OrderCreate,
    OrderItem,
    OrderStatus,
)
from ..services.firestore import (
    product_service,
    customer_service,
    order_service,
    generate_id,
)


class SalesAgent(BaseAgent):
    """Sales Agent — handles product inquiries, recommendations, and order creation."""

    def __init__(self, business_id: str):
        super().__init__(AgentType.SALES, business_id)

    @property
    def agent_name(self) -> str:
        return "Sales Agent"

    @property
    def system_prompt(self) -> str:
        return """You are the Sales Agent of METIS, an AI workforce for small businesses.

Your role:
- Answer product questions accurately using ONLY the provided product data
- Search and recommend products based on customer needs
- Check inventory availability
- Calculate order totals including any applicable discounts
- Suggest relevant upsells based on customer interest
- Create orders when customers decide to purchase

Rules:
- NEVER invent product prices, availability, or details
- ALWAYS verify product information against the actual product database
- If a product is not found, clearly say so
- Always check stock before recommending
- Be helpful but honest about what's available
- Suggest alternatives when exact matches aren't available
- All prices must come from actual product data, never guessed

Communication style: Friendly, helpful, knowledgeable about the products."""

    def search_products(
        self,
        query: str = "",
        category: str = "",
        max_price: Optional[float] = None,
        in_stock_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Search products with optional filters."""
        filters = [("business_id", "==", self.business_id)]
        if category:
            filters.append(("category", "==", category))
        if in_stock_only:
            filters.append(("stock", ">", 0))

        products = product_service.list_all(filters)

        if max_price is not None:
            products = [p for p in products if p.get("price", 0) <= max_price]

        if query:
            query_lower = query.lower()
            products = [
                p
                for p in products
                if query_lower in p.get("name", "").lower()
                or query_lower in p.get("description", "").lower()
                or query_lower in p.get("category", "").lower()
            ]

        return products

    def get_product(self, product_id: str) -> Optional[dict[str, Any]]:
        """Get a specific product by ID and verify it belongs to this business."""
        product = product_service.get(product_id)
        if product and product.get("business_id") == self.business_id:
            return product
        return None

    def _normalize_ref(self, ref: str) -> str:
        import re
        return re.sub(r'[^a-z0-9]', '', ref.lower())

    def resolve_customer(self, customer_ref: str) -> Optional[dict[str, Any]]:
        """Resolve a customer by full ID, ID prefix, or name (case-insensitive)."""
        ref = (customer_ref or "").strip()
        if not ref:
            return None
        customer = customer_service.get(ref)
        if customer and customer.get("business_id") == self.business_id:
            return customer
        ref_lower = ref.lower()
        customers = customer_service.list_all(
            [("business_id", "==", self.business_id)]
        )
        for c in customers:
            if c.get("id", "").lower().startswith(ref_lower) or c.get("name", "").lower() == ref_lower:
                return c
        return None

    def resolve_product(self, product_ref: str) -> Optional[dict[str, Any]]:
        """Resolve a product by full ID, ID prefix, or name (case-insensitive)."""
        ref = (product_ref or "").strip()
        if not ref:
            return None
        product = self.get_product(ref)
        if product:
            return product
        ref_lower = ref.lower()
        products = product_service.list_all(
            [("business_id", "==", self.business_id)]
        )
        for p in products:
            if p.get("id", "").lower().startswith(ref_lower) or p.get("name", "").lower() == ref_lower:
                return p
        # Fuzzy fallback: strip punctuation/prefixes, e.g. "prod_batmobile" -> "Bat-Mobile"
        ref_norm = self._normalize_ref(ref)
        if len(ref_norm) >= 4:
            for p in products:
                name_norm = self._normalize_ref(p.get("name", ""))
                if name_norm and (name_norm in ref_norm or ref_norm in name_norm):
                    return p
        return None

    def check_inventory(self, product_id: str) -> dict[str, Any]:
        """Check inventory for a specific product."""
        product = self.get_product(product_id)
        if not product:
            return {"available": False, "error": "Product not found."}

        stock = product.get("stock", 0)
        return {
            "available": stock > 0,
            "stock": stock,
            "product_name": product.get("name"),
            "low_stock": stock <= 5,
        }

    def recommend_products(
        self,
        customer_query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Recommend products based on customer query."""
        prompt = f"""Based on the customer query: "{customer_query}"

And the following available products:
{self._format_products_for_ai(self.search_products(in_stock_only=True))}

Select the top {limit} most relevant products for this customer.
Consider: price relevance, category match, and product features.

Respond with ONLY a JSON array of product IDs, like: ["id1", "id2", "id3"]"""

        response = self.think_structured(prompt)
        import json
        try:
            product_ids = json.loads(response)
            products = []
            for pid in product_ids:
                product = self.get_product(pid)
                if product:
                    products.append(product)
            return products
        except (json.JSONDecodeError, TypeError):
            return self.search_products(query=customer_query)[:limit]

    def create_order(
        self,
        customer_id: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create a new order after verifying stock."""
        customer = self.resolve_customer(customer_id)
        if not customer:
            return {
                "success": False,
                "error": f"Customer {customer_id} not found.",
            }
        customer_id = customer["id"]

        order_items = []
        total_amount = 0.0

        for item in items:
            if not isinstance(item, dict) or not item.get("product_id"):
                return {
                    "success": False,
                    "error": "Each order item must include a product_id.",
                }
            product = self.resolve_product(item["product_id"])
            if not product:
                return {
                    "success": False,
                    "error": f"Product {item['product_id']} not found.",
                }

            requested_qty = item.get("quantity", 1)
            if product.get("stock", 0) < requested_qty:
                return {
                    "success": False,
                    "error": f"Insufficient stock for {product['name']}. Available: {product['stock']}",
                }

            unit_price = product.get("price", 0)
            total_price = unit_price * requested_qty
            order_items.append(
                OrderItem(
                    product_id=product["id"],
                    product_name=product["name"],
                    quantity=requested_qty,
                    unit_price=unit_price,
                    total_price=total_price,
                ).model_dump()
            )
            total_amount += total_price

        order_data = {
            "business_id": self.business_id,
            "customer_id": customer_id,
            "items": order_items,
            "total_amount": total_amount,
            "status": OrderStatus.PENDING.value,
            "notes": "",
        }

        order_id = order_service.create(order_data)

        # Update inventory
        for item in order_items:
            product = self.resolve_product(item["product_id"])
            if product:
                new_stock = product.get("stock", 0) - item["quantity"]
                product_service.update(product["id"], {"stock": max(0, new_stock)})

        # Update customer stats
        customer_service.update(
            customer_id,
            {
                "total_orders": customer.get("total_orders", 0) + 1,
                "total_spent": customer.get("total_spent", 0) + total_amount,
            },
        )

        self.log_action(
            action="create_order",
            details={
                "order_id": order_id,
                "customer_id": customer_id,
                "total": total_amount,
                "items": len(order_items),
            },
            result=f"Order created: ৳{total_amount:,.2f}",
        )

        return {
            "success": True,
            "order_id": order_id,
            "total_amount": total_amount,
            "items": order_items,
        }

    def handle_inquiry(self, message: str) -> str:
        """Handle a customer product inquiry."""
        products = self.search_products(in_stock_only=True)

        prompt = f"""A customer asked: "{message}"

Available products:
{self._format_products_for_ai(products)}

Respond helpfully to the customer. If they're looking for something specific, show matching products with prices and availability. If no exact match exists, suggest alternatives.

Important: Only mention products from the list above. Use their exact names and prices."""

        response = self.think(prompt)

        self.log_action(
            action="handle_inquiry",
            details={"customer_message": message},
            result=response[:200],
        )

        return response

    def _format_products_for_ai(self, products: list[dict[str, Any]]) -> str:
        """Format product list for AI prompt."""
        if not products:
            return "No products available."

        lines = []
        for p in products:
            lines.append(
                f"- ID: {p['id']} | {p['name']} | "
                f"৳{p['price']:,.2f} | Stock: {p.get('stock', 0)} | "
                f"Category: {p.get('category', 'N/A')}"
            )
        return "\n".join(lines)

    async def handle_message(self, message: AgentMessage) -> AgentResponse:
        """Handle a delegated task from Manager Agent."""
        task = message.task.lower()

        if "search" in task or "find" in task or "product" in task:
            products = self.search_products(query=message.context.get("query", ""))
            return AgentResponse(
                success=True,
                agent=self.agent_type,
                task=message.task,
                result=f"Found {len(products)} products.",
                data={"products": products},
            )

        if "recommend" in task:
            products = self.recommend_products(
                message.context.get("query", task)
            )
            return AgentResponse(
                success=True,
                agent=self.agent_type,
                task=message.task,
                result=f"Recommended {len(products)} products.",
                data={"products": products},
            )

        if "inquiry" in task or "question" in task:
            response = self.handle_inquiry(message.task)
            return AgentResponse(
                success=True,
                agent=self.agent_type,
                task=message.task,
                result=response,
            )

        if "order" in task:
            result = self.create_order(
                customer_id=message.context.get("customer_id", ""),
                items=message.context.get("items", []),
            )
            return AgentResponse(
                success=result.get("success", False),
                agent=self.agent_type,
                task=message.task,
                result=result.get("error") or f"Order created: {result.get('order_id', '')}",
                data=result,
                requires_approval=True,
            )

        # Default: handle as general inquiry
        response = self.handle_inquiry(message.task)
        return AgentResponse(
            success=True,
            agent=self.agent_type,
            task=message.task,
            result=response,
        )
