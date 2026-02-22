"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getCustomer, getCustomerContext, getCustomerOrders, getCustomerConversations } from "@/lib/api";
import type { Customer, CustomerContext, Order, Conversation } from "@/lib/types";

export default function CustomerDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [customer, setCustomer] = useState<Customer | null>(null);
  const [context, setContext] = useState<CustomerContext | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      getCustomer(id),
      getCustomerContext(id),
      getCustomerOrders(id),
      getCustomerConversations(id),
    ]).then(([c, ctx, o, conv]) => {
      setCustomer(c);
      setContext(ctx);
      setOrders(o);
      setConversations(conv);
    }).catch(console.error);
  }, [id]);

  if (!customer) {
    return <p style={{ color: "var(--color-text-muted)" }}>Loading...</p>;
  }

  return (
    <div>
      <Link href="/customers" className="text-sm mb-4 inline-block" style={{ color: "var(--color-accent)" }}>
        ← Back to Customers
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">{customer.name}</h2>
          <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
            {customer.type} &middot; {customer.contact_phone} &middot; {customer.delivery_address}
          </p>
        </div>
        <span className="text-xl font-bold" style={{
          color: customer.health_score >= 0.9 ? "var(--color-green)" : customer.health_score >= 0.8 ? "var(--color-amber)" : "var(--color-red)",
        }}>
          {(customer.health_score * 100).toFixed(0)}% Health
        </span>
      </div>

      {context && (
        <div className="rounded-lg border p-4 mb-6" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
          <h3 className="text-sm font-semibold mb-3">Customer Context</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs mb-1" style={{ color: "var(--color-text-muted)" }}>Order Frequency</p>
              <p>{context.order_frequency} (Preferred: {context.preferred_order_day})</p>
            </div>
            <div>
              <p className="text-xs mb-1" style={{ color: "var(--color-text-muted)" }}>Delivery</p>
              <p>{context.delivery_preferences}</p>
            </div>
          </div>
          <div className="mt-3">
            <p className="text-xs mb-1" style={{ color: "var(--color-text-muted)" }}>Typical Basket</p>
            <div className="flex flex-wrap gap-2">
              {context.typical_basket.map((item) => (
                <span key={item.product_id} className="text-xs px-2 py-1 rounded border" style={{ borderColor: "var(--color-border)" }}>
                  {item.usual_quantity}{item.unit} {item.name}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold mb-3">Recent Orders</h3>
          <div className="rounded-lg border overflow-hidden" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            {orders.slice(0, 10).map((order) => (
              <div key={order.id} className="px-4 py-3 border-b last:border-b-0" style={{ borderColor: "var(--color-border)" }}>
                <div className="flex items-center justify-between">
                  <p className="text-sm">{order.created_at.slice(0, 10)}</p>
                  <div className="text-right">
                    <p className="text-sm font-semibold">EUR {order.total_value.toFixed(2)}</p>
                    <p className="text-xs" style={{
                      color: order.status === "confirmed" ? "var(--color-green)" : "var(--color-amber)",
                    }}>{order.status}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {order.items.map((item) => (
                    <span key={item.id} className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                      {item.quantity}{item.unit} {item.product_name}
                      {order.items.indexOf(item) < order.items.length - 1 ? "," : ""}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-lg font-semibold mb-3">Conversation History</h3>
          <div className="rounded-lg border overflow-hidden max-h-96 overflow-y-auto" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            {conversations.slice(0, 20).map((conv) => (
              <div key={conv.id} className="px-4 py-3 border-b last:border-b-0" style={{ borderColor: "var(--color-border)" }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium px-1.5 py-0.5 rounded" style={{
                    background: conv.direction === "inbound" ? "rgba(79,140,255,0.15)" : "rgba(34,197,94,0.15)",
                    color: conv.direction === "inbound" ? "var(--color-accent)" : "var(--color-green)",
                  }}>
                    {conv.direction === "inbound" ? "IN" : "OUT"}
                  </span>
                  <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                    {conv.created_at.slice(0, 16).replace("T", " ")}
                  </span>
                  {conv.parsed_intent && (
                    <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                      [{conv.parsed_intent}]
                    </span>
                  )}
                </div>
                {conv.message_text.startsWith("[IMAGE:") ? (
                  <img
                    src={`data:image/jpeg;base64,${conv.message_text.slice(7, -1)}`}
                    alt="Customer image"
                    className="max-w-xs rounded mt-1"
                    style={{ maxHeight: "200px", objectFit: "contain" }}
                  />
                ) : (
                  <p className="text-sm">{conv.message_text.slice(0, 150)}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
