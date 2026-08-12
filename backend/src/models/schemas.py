from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


# === Enums ===

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


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
    policies: dict[str, str] = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)


class BusinessCreate(BusinessBase):
    pass


class Business(BusinessBase):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
    category: str = ""
    variants: list[ProductVariant] = Field(default_factory=list)
    status: ProductStatus = ProductStatus.ACTIVE


class ProductCreate(ProductBase):
    pass


class Product(ProductBase):
    id: str
    business_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# === Agent Log ===

class AgentLog(BaseModel):
    id: str = ""
    business_id: str
    agent_type: AgentType
    action: str
    details: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"
    result: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
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
    timestamp: datetime = Field(default_factory=datetime.utcnow)


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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
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
