export interface OrderItem {
  id: string;
  order_id: string;
  product_id: string;
  product_name: string;
  sku: string;
  unit: string;
  unit_type: string;
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
  fulfilled_at: string | null;
  flags_json: string | null;
  flags: string[];
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
  latest_health_event: string | null;
  latest_health_severity: string | null;
  latest_health_date: string | null;
  pending_order_count: number;
  confirmed_order_count: number;
  fulfilled_order_count: number;
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
  customer_name: string | null;
  resolved_customer_id: string | null;
  related_order_id: string | null;
}

export interface OrdersOverview {
  pending_count: number;
  pending_value: number;
  confirmed_today_count: number;
  confirmed_today_value: number;
  confirmed_all_count: number;
  confirmed_all_value: number;
  fulfilled_today_count: number;
  fulfilled_today_value: number;
  fulfilled_all_count: number;
  fulfilled_all_value: number;
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
  source: string;
  created_at: string;
  image_url: string | null;
}

export interface AggregatedItem {
  product_id: string;
  product_name: string;
  sku: string;
  category: string;
  unit: string;
  unit_type: string;
  total_quantity: number;
  order_count: number;
}

export interface HealthEvent {
  id: string;
  customer_id: string;
  event_type: string;
  severity: string;
  detail: string;
  created_at: string;
}

export interface DetectedOrderChange {
  order_id: string;
  action: string;
  product_name: string;
  product_id: string;
  quantity_change: number;
  confidence: number;
}

export interface ManualMessageResponse {
  status: string;
  detected_changes: DetectedOrderChange[];
}

export interface Product {
  id: string;
  name: string;
  sku: string;
  category: string;
  unit: string;
  unit_type: string;
  price_default: number;
}

export interface NudgeSuggestion {
  id: string;
  customer_id: string;
  customer_name: string;
  contact_whatsapp: string;
  suggested_message: string;
  reason: string;
  status: string;
  created_at: string;
}

export interface CreateProductInput {
  name: string;
  sku: string;
  category: string;
  unit: string;
  unit_type: string;
  price_default: number;
}

export interface EditableItem {
  product_id: string;
  quantity: number;
  unit_price: number;
}
