"""Tool layer that bridges Gemini function calls to the METIS agents.

Read-only tools execute immediately. Direct write tools (low risk) execute
immediately. Staged write tools (medium/high risk) create an approval request
that the owner resolves in the Approval Center; the approval endpoint executes
the staged action via `execute_staged_action`.
"""

from typing import Any

from ..models.schemas import AgentType, OrderStatus, RiskLevel
from ..services.firestore import order_service
from ..agents.registry import get_agent


ORDER_STATUS_VALUES = [s.value for s in OrderStatus]

TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "get_dashboard",
        "description": "Get current business metrics (total revenue, order count, customer count, conversion rate, top products, low stock alerts) and AI recommendations.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "list_orders",
        "description": "List orders, optionally filtered by status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "status": {
                    "type": "STRING",
                    "enum": ORDER_STATUS_VALUES,
                    "description": "Filter by order status. Optional.",
                }
            },
        },
    },
    {
        "name": "get_order",
        "description": "Get a single order by its ID.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "order_id": {"type": "STRING", "description": "The order ID."}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "check_inventory",
        "description": "Check inventory levels across all products. Returns healthy, low stock and out of stock products.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "search_products",
        "description": "Search the product catalog by keyword, category or maximum price.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Free-text search across product name, description and category.",
                },
                "category": {
                    "type": "STRING",
                    "description": "Filter by exact category.",
                },
                "max_price": {
                    "type": "NUMBER",
                    "description": "Maximum product price.",
                },
            },
        },
    },
    {
        "name": "recommend_products",
        "description": "Recommend products that match a customer's needs. Read-only; no order is created.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "customer_query": {
                    "type": "STRING",
                    "description": "What the customer is looking for.",
                }
            },
            "required": ["customer_query"],
        },
    },
    {
        "name": "create_order",
        "description": "Create a new order for a customer. Requires the customer ID and at least one item (product ID and quantity). Creating an order needs owner approval, so an approval request is created instead of executing immediately.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "customer_id": {
                    "type": "STRING",
                    "description": "The ID of the customer placing the order.",
                },
                "items": {
                    "type": "ARRAY",
                    "description": "Order line items.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "product_id": {
                                "type": "STRING",
                                "description": "Product ID.",
                            },
                            "quantity": {
                                "type": "INTEGER",
                                "description": "Quantity to order.",
                            },
                        },
                        "required": ["product_id", "quantity"],
                    },
                },
            },
            "required": ["customer_id", "items"],
        },
    },
    {
        "name": "update_order_status",
        "description": "Move an order through its lifecycle by changing its status (confirmed, processing, shipped, delivered, cancelled).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "order_id": {"type": "STRING", "description": "The order ID."},
                "status": {
                    "type": "STRING",
                    "enum": ORDER_STATUS_VALUES,
                    "description": "New order status.",
                },
            },
            "required": ["order_id", "status"],
        },
    },
    {
        "name": "create_campaign",
        "description": "Create a marketing campaign for a product. Requires owner approval, so an approval request is created instead of executing immediately.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal": {
                    "type": "STRING",
                    "description": "Campaign goal, e.g. increase_sales or brand_awareness.",
                },
                "platform": {
                    "type": "STRING",
                    "description": "Target platform, e.g. facebook or instagram.",
                },
                "product_id": {
                    "type": "STRING",
                    "description": "Product to promote (optional; defaults to top products).",
                },
            },
        },
    },
]

TOOL_NAMES = {t["name"] for t in TOOL_DECLARATIONS}

STAGED_TOOLS: set[str] = {"create_order", "create_campaign"}

STAGED_RISK: dict[str, RiskLevel] = {
    "create_order": RiskLevel.MEDIUM,
    "create_campaign": RiskLevel.HIGH,
}


def handle_tool_call(business_id: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a tool call to the right agent and execution mode.

    Returns {"status": "executed" | "staged" | "failed", ...}.
    """
    if name not in TOOL_NAMES:
        return {"status": "failed", "error": f"Unknown tool '{name}'."}

    if name in STAGED_TOOLS:
        return _stage_action(business_id, name, args)

    if name == "update_order_status":
        return _update_order_status(business_id, args)

    return _read_only(business_id, name, args)


def _read_only(business_id: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        if name == "get_dashboard":
            analytics = get_agent(AgentType.ANALYTICS, business_id)
            metrics = analytics.get_dashboard_metrics()
            recommendations = analytics.generate_recommendations()
            return {"status": "executed", "result": {**metrics, "recommendations": recommendations}}

        if name == "list_orders":
            operations = get_agent(AgentType.OPERATIONS, business_id)
            orders = operations.get_all_orders(args.get("status", ""))
            return {"status": "executed", "result": {"orders": orders, "count": len(orders)}}

        if name == "get_order":
            order = order_service.get(args.get("order_id", ""))
            if not order or order.get("business_id") != business_id:
                return {"status": "failed", "error": "Order not found."}
            return {"status": "executed", "result": order}

        if name == "check_inventory":
            operations = get_agent(AgentType.OPERATIONS, business_id)
            return {"status": "executed", "result": operations.check_inventory_levels()}

        if name == "search_products":
            sales = get_agent(AgentType.SALES, business_id)
            products = sales.search_products(
                query=args.get("query", ""),
                category=args.get("category", ""),
                max_price=args.get("max_price"),
            )
            return {"status": "executed", "result": {"products": products, "count": len(products)}}

        if name == "recommend_products":
            sales = get_agent(AgentType.SALES, business_id)
            products = sales.recommend_products(customer_query=args.get("customer_query", ""))
            return {"status": "executed", "result": {"products": products, "count": len(products)}}

        return {"status": "failed", "error": f"Tool '{name}' is not executable."}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def _update_order_status(business_id: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        new_status = OrderStatus(args.get("status", ""))
    except ValueError:
        return {"status": "failed", "error": "Invalid order status."}

    operations = get_agent(AgentType.OPERATIONS, business_id)
    result = operations.update_order_status(args.get("order_id", ""), new_status)
    if not result.get("success"):
        return {"status": "failed", "error": result.get("error", "Order status update failed.")}
    return {"status": "executed", "result": result}


def _stage_action(business_id: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    manager = get_agent(AgentType.MANAGER, business_id)

    if name == "create_order":
        items = args.get("items") or []
        customer_id = args.get("customer_id") or ""
        if not customer_id or not items:
            return {
                "status": "failed",
                "error": "create_order requires customer_id and at least one item.",
            }
        approval_id = manager.request_approval(
            agent_type=AgentType.SALES,
            action=f"Create order for customer {customer_id}",
            reason="New order requested via chat. Your approval is required before the order is created and inventory is updated.",
            risk_level=STAGED_RISK["create_order"],
            details={"tool": "create_order", "params": {"customer_id": customer_id, "items": items}},
        )
        return {
            "status": "staged",
            "approval_id": approval_id,
            "result": {"message": "Approval request created.", "approval_id": approval_id},
        }

    if name == "create_campaign":
        approval_id = manager.request_approval(
            agent_type=AgentType.MARKETING,
            action="Launch marketing campaign",
            reason="Marketing campaign requested via chat. Your approval is required before publishing.",
            risk_level=STAGED_RISK["create_campaign"],
            details={
                "tool": "create_campaign",
                "params": {k: args.get(k) for k in ("goal", "platform", "product_id")},
            },
        )
        return {
            "status": "staged",
            "approval_id": approval_id,
            "result": {"message": "Approval request created.", "approval_id": approval_id},
        }

    return {"status": "failed", "error": f"Tool '{name}' cannot be staged."}


def execute_staged_action(business_id: str, approval: dict[str, Any]) -> dict[str, Any]:
    """Execute the action that was staged when the approval was created."""
    details = approval.get("details") or {}
    tool = details.get("tool", "")
    params = details.get("params") or {}

    try:
        if tool == "create_order":
            sales = get_agent(AgentType.SALES, business_id)
            return sales.create_order(
                customer_id=params.get("customer_id", ""),
                items=params.get("items", []),
            )

        if tool == "create_campaign":
            marketing = get_agent(AgentType.MARKETING, business_id)
            result = marketing.create_campaign(
                product_id=params.get("product_id", ""),
                goal=params.get("goal", "increase_sales"),
                platform=params.get("platform", "facebook"),
            )
            result.pop("requires_approval", None)
            return result
    except Exception as e:
        return {"success": False, "error": str(e)}

    return {"success": False, "error": f"Unknown staged action '{tool}'."}
