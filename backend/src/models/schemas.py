from datetime import datetime
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field

from ..core.clock import utcnow


# === Enums ===

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


# Statuses whose order amount counts toward recognized revenue.
# Pending orders are not booked as revenue until confirmed; cancelled and
# returned orders never count.
REVENUE_STATUSES = frozenset({
    OrderStatus.CONFIRMED.value,
    OrderStatus.PROCESSING.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
})

# Statuses in which the order no longer holds inventory or customer spend;
# reaching one releases the stock and spend that were booked on creation.
ORDER_RELEASED_STATUSES = frozenset({
    OrderStatus.CANCELLED.value,
    OrderStatus.RETURNED.value,
})


class ProductStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentType(str, Enum):
    MANAGER = "manager"
    SALES = "sales"
    SUPPORT = "support"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    ANALYTICS = "analytics"


# === Business ===

class BusinessBase(BaseModel):
    name: str
    category: str = ""
    description: str = ""
    contact_email: str = ""
    phone: str = ""
    operating_hours: str = ""
    currency: str = "BDT"
    policies: dict[str, str] = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)


class BusinessCreate(BusinessBase):
    pass


class Business(BusinessBase):
    id: str
    # Set from the authenticated caller at creation time, never from the
    # request body. Empty on businesses created before auth existed, which
    # require_business_access treats as unowned.
    owner_uid: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# === Product ===

class ProductVariant(BaseModel):
    name: str
    sku: str = ""
    price_override: Optional[float] = None
    stock: int = 0


class ProductBase(BaseModel):
    name: str
    description: str = ""
    price: float
    stock: int = 0
    product_key: str = ""
    category: str = ""
    variants: list[ProductVariant] = Field(default_factory=list)
    status: ProductStatus = ProductStatus.ACTIVE


class ProductCreate(ProductBase):
    pass


class Product(ProductBase):
    id: str
    business_id: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# === Customer ===

class CustomerBase(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    notes: str = ""


class CustomerCreate(CustomerBase):
    pass


class Customer(CustomerBase):
    id: str
    business_id: str
    total_orders: int = 0
    total_spent: float = 0.0
    created_at: datetime = Field(default_factory=utcnow)


# === Order ===

class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float


class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int = 1


class OrderBase(BaseModel):
    customer_id: str
    items: list[OrderItemCreate]
    total_amount: float = 0.0
    notes: str = ""


class OrderCreate(OrderBase):
    pass


class Order(OrderBase):
    id: str
    business_id: str
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# === Agent Log ===

class AgentLog(BaseModel):
    id: str = ""
    business_id: str
    agent_type: AgentType
    action: str
    details: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"
    result: str = ""
    created_at: datetime = Field(default_factory=utcnow)


# === Approval ===

class ApprovalBase(BaseModel):
    agent_type: AgentType
    action: str
    reason: str
    risk_level: RiskLevel
    details: dict[str, Any] = Field(default_factory=dict)


class ApprovalCreate(ApprovalBase):
    pass


class Approval(ApprovalBase):
    id: str
    business_id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: Optional[datetime] = None


# === Agent Communication ===

class AgentMessage(BaseModel):
    requester: AgentType
    target: AgentType
    task: str
    context: dict[str, Any] = Field(default_factory=dict)
    priority: str = "normal"
    requires_approval: bool = False


class AgentResponse(BaseModel):
    success: bool
    agent: AgentType
    task: str
    result: str
    data: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    approval_id: Optional[str] = None


# === Chat ===

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=utcnow)


class ChatRequest(BaseModel):
    business_id: str
    message: str
    model: str = ""
    history: list[ChatMessage] = Field(default_factory=list)


class StorefrontChatRequest(ChatRequest):
    """Public customer chat with the Sales Agent.

    `session_id` scopes the stored conversation per browser; `customer_id`
    binds the shopper so staged orders carry a real customer reference.
    """
    session_id: str = ""
    customer_id: str = ""


class ChatResponse(BaseModel):
    message: str
    agent_actions: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utcnow)
    history: list[ChatMessage] = Field(default_factory=list)


# === AI Config ===

class AiConfigRequest(BaseModel):
    api_key: str = ""


# === Analytics ===

class DashboardMetrics(BaseModel):
    total_revenue: float
    total_orders: int
    total_customers: int
    conversion_rate: float
    top_products: list[dict[str, Any]]
    low_stock_products: list[dict[str, Any]]
    recent_orders: list[Order]
    agent_activity_count: dict[str, int]
    recommendations: list[str]
