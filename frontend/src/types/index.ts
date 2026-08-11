export interface Business {
  id: string;
  name: string;
  category: string;
  description: string;
  contact_email: string;
  phone: string;
  operating_hours: string;
  policies: Record<string, string>;
  goals: string[];
  created_at: string;
}

export interface Product {
  id: string;
  business_id: string;
  name: string;
  description: string;
  price: number;
  stock: number;
  category: string;
  status: string;
  created_at: string;
}

export interface Customer {
  id: string;
  business_id: string;
  name: string;
  email: string;
  phone: string;
  total_orders: number;
  total_spent: number;
  created_at: string;
}

export interface OrderItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface Order {
  id: string;
  business_id: string;
  customer_id: string;
  items: OrderItem[];
  total_amount: number;
  status: string;
  notes: string;
  created_at: string;
}

export interface AgentLog {
  id: string;
  business_id: string;
  agent_type: string;
  action: string;
  details: Record<string, any>;
  status: string;
  result: string;
  created_at: string;
}

export interface Approval {
  id: string;
  business_id: string;
  agent_type: string;
  action: string;
  reason: string;
  risk_level: string;
  status: string;
  details: Record<string, any>;
  created_at: string;
}

export interface DashboardMetrics {
  total_revenue: number;
  total_orders: number;
  total_customers: number;
  conversion_rate: number;
  top_products: any[];
  low_stock_products: any[];
  agent_activity_count: Record<string, number>;
  average_order_value: number;
  recommendations: string[];
}

export interface AgentStatus {
  type: string;
  name: string;
  status: string;
  tasks_completed: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}
