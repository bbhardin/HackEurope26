import type {
  Order,
  Customer,
  CustomerContext,
  Alert,
  AgentAction,
  OrdersOverview,
  Conversation,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function getOrdersOverview(): Promise<OrdersOverview> {
  return fetchJson<OrdersOverview>("/api/orders/overview");
}

export async function getOrders(status?: string): Promise<Order[]> {
  const query = status ? `?status=${status}` : "";
  return fetchJson<Order[]>(`/api/orders${query}`);
}

export async function getOrder(id: string): Promise<Order> {
  return fetchJson<Order>(`/api/orders/${id}`);
}

export async function approveOrder(id: string): Promise<Order> {
  return fetchJson<Order>(`/api/orders/${id}/approve`, { method: "POST" });
}

export async function rejectOrder(id: string): Promise<Order> {
  return fetchJson<Order>(`/api/orders/${id}/reject`, { method: "POST" });
}

export async function getCustomers(): Promise<Customer[]> {
  return fetchJson<Customer[]>("/api/customers");
}

export async function getCustomer(id: string): Promise<Customer> {
  return fetchJson<Customer>(`/api/customers/${id}`);
}

export async function getCustomerContext(id: string): Promise<CustomerContext> {
  return fetchJson<CustomerContext>(`/api/customers/${id}/context`);
}

export async function getCustomerOrders(id: string): Promise<Order[]> {
  return fetchJson<Order[]>(`/api/customers/${id}/orders`);
}

export async function getCustomerConversations(id: string): Promise<Conversation[]> {
  return fetchJson<Conversation[]>(`/api/customers/${id}/conversations`);
}

export async function getAlerts(acknowledged = false): Promise<Alert[]> {
  return fetchJson<Alert[]>(`/api/alerts?acknowledged=${acknowledged}`);
}

export async function acknowledgeAlert(id: string): Promise<void> {
  await fetchJson<Record<string, string>>(`/api/alerts/${id}/acknowledge`, { method: "POST" });
}

export async function getActivity(limit = 50, agentType?: string): Promise<AgentAction[]> {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (agentType) params.set("agent_type", agentType);
  return fetchJson<AgentAction[]>(`/api/activity?${params}`);
}

export async function triggerNudgeScan(): Promise<Record<string, number | string>> {
  return fetchJson<Record<string, number | string>>("/api/nudge/run", { method: "POST" });
}

export async function simulateMessage(phone: string, message: string): Promise<void> {
  await fetchJson<Record<string, string>>("/api/simulate/message", {
    method: "POST",
    body: JSON.stringify({ phone, message, message_type: "text" }),
  });
}
