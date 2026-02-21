export interface OrderItem {
  id: string;
  order_id: string;
  product_id: string;
  product_name: string;
  sku: string;
  unit: string;
  category?: string;
  quantity: number;
  unit_price: number;
  matched_confidence: number;
  original_text: string;
  substitution_for: string | null;
}

export interface Order {
  id: string;
  customer_id: string;
  customer_name?: string;
  customer_whatsapp?: string;
  channel: string;
  raw_message: string;
  status: string;
  total_value: number;
  created_at: string;
  confirmed_at: string | null;
  confirmed_by: string | null;
  items: OrderItem[];
}

export interface Customer {
  id: string;
  name: string;
  type: string;
  contact_phone: string;
  contact_whatsapp: string;
  delivery_address: string;
  health_score: number;
  created_at: string;
}

export interface CustomerContext {
  typical_basket: BasketItem[];
  order_frequency: string;
  preferred_order_day: string;
  delivery_preferences: string;
  notes: string;
}

export interface BasketItem {
  product_id: string;
  sku: string;
  name: string;
  usual_quantity: number;
  unit: string;
  price: number;
}

export interface Alert {
  id: string;
  type: string;
  customer_id: string | null;
  customer_name: string | null;
  detail: string;
  acknowledged: number;
  created_at: string;
}

export interface AgentAction {
  id: string;
  agent_type: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details_json: string;
  confidence: number | null;
  human_reviewed: number;
  created_at: string;
}

export interface OrdersOverview {
  pending_count: number;
  pending_value: number;
  confirmed_today_count: number;
  confirmed_today_value: number;
  confirmed_all_count: number;
  confirmed_all_value: number;
  rejected_count: number;
  flagged_count: number;
}

export interface Conversation {
  id: string;
  customer_id: string;
  channel: string;
  direction: string;
  message_text: string;
  parsed_intent: string | null;
  created_at: string;
}
