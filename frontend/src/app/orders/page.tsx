"use client";

import { useEffect, useState, useCallback } from "react";
import { getOrders, approveOrder, rejectOrder } from "@/lib/api";
import type { Order } from "@/lib/types";

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [filter, setFilter] = useState("pending_confirmation");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [processing, setProcessing] = useState<string | null>(null);

  const loadOrders = useCallback(async () => {
    try {
      const data = filter === "all" ? await getOrders() : await getOrders(filter);
      setOrders(data);
    } catch (e) {
      console.error("Failed to load orders:", e);
    }
  }, [filter]);

  useEffect(() => {
    loadOrders();
    const interval = setInterval(loadOrders, 5000);
    return () => clearInterval(interval);
  }, [loadOrders]);

  const handleApprove = async (orderId: string) => {
    setProcessing(orderId);
    try {
      await approveOrder(orderId);
      loadOrders();
    } catch (e) {
      console.error("Approve failed:", e);
    }
    setProcessing(null);
  };

  const handleReject = async (orderId: string) => {
    setProcessing(orderId);
    try {
      await rejectOrder(orderId);
      loadOrders();
    } catch (e) {
      console.error("Reject failed:", e);
    }
    setProcessing(null);
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "confirmed": return "var(--color-green)";
      case "pending_confirmation": return "var(--color-amber)";
      case "flagged": return "var(--color-red)";
      case "rejected": return "var(--color-red)";
      default: return "var(--color-text-muted)";
    }
  };

  const filters = [
    { value: "pending_confirmation", label: "Pending" },
    { value: "flagged", label: "Flagged" },
    { value: "confirmed", label: "Confirmed" },
    { value: "rejected", label: "Rejected" },
    { value: "all", label: "All" },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Order Queue</h2>

      <div className="flex gap-2 mb-6">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className="px-3 py-1.5 rounded text-sm font-medium transition-colors cursor-pointer"
            style={{
              background: filter === f.value ? "var(--color-accent)" : "var(--color-surface)",
              color: filter === f.value ? "#fff" : "var(--color-text-muted)",
              border: `1px solid ${filter === f.value ? "var(--color-accent)" : "var(--color-border)"}`,
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {orders.map((order) => (
          <div
            key={order.id}
            className="rounded-lg border transition-colors"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
          >
            <div
              className="flex items-center justify-between px-5 py-4 cursor-pointer"
              onClick={() => setExpanded(expanded === order.id ? null : order.id)}
            >
              <div className="flex items-center gap-4">
                <div>
                  <p className="text-sm font-semibold">{order.customer_name}</p>
                  <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                    {order.created_at.slice(0, 16).replace("T", " ")} &middot; {order.items.length} items
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-sm font-bold">EUR {order.total_value.toFixed(2)}</p>
                  <p className="text-xs font-medium" style={{ color: statusColor(order.status) }}>{order.status}</p>
                </div>
                {(order.status === "pending_confirmation" || order.status === "flagged") && (
                  <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => handleApprove(order.id)}
                      disabled={processing === order.id}
                      className="px-3 py-1.5 rounded text-xs font-semibold cursor-pointer disabled:opacity-50"
                      style={{ background: "var(--color-green)", color: "#fff" }}
                    >
                      {processing === order.id ? "..." : "Approve"}
                    </button>
                    <button
                      onClick={() => handleReject(order.id)}
                      disabled={processing === order.id}
                      className="px-3 py-1.5 rounded text-xs font-semibold cursor-pointer disabled:opacity-50"
                      style={{ background: "var(--color-red)", color: "#fff" }}
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            </div>

            {expanded === order.id && (
              <div className="px-5 pb-4 border-t" style={{ borderColor: "var(--color-border)" }}>
                <div className="pt-3">
                  <p className="text-xs font-medium mb-2" style={{ color: "var(--color-text-muted)" }}>Order Items</p>
                  <table className="w-full text-sm">
                    <thead>
                      <tr style={{ color: "var(--color-text-muted)" }}>
                        <th className="text-left text-xs font-medium pb-2">Product</th>
                        <th className="text-right text-xs font-medium pb-2">Qty</th>
                        <th className="text-right text-xs font-medium pb-2">Unit Price</th>
                        <th className="text-right text-xs font-medium pb-2">Line Total</th>
                        <th className="text-right text-xs font-medium pb-2">Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {order.items.map((item) => (
                        <tr key={item.id} className="border-t" style={{ borderColor: "var(--color-border)" }}>
                          <td className="py-2">
                            <p className="font-medium">{item.product_name}</p>
                            {item.original_text && (
                              <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                                &quot;{item.original_text.slice(0, 60)}&quot;
                              </p>
                            )}
                          </td>
                          <td className="text-right py-2">{item.quantity} {item.unit}</td>
                          <td className="text-right py-2">EUR {item.unit_price.toFixed(2)}</td>
                          <td className="text-right py-2 font-medium">EUR {(item.quantity * item.unit_price).toFixed(2)}</td>
                          <td className="text-right py-2">
                            <span style={{ color: item.matched_confidence >= 0.9 ? "var(--color-green)" : "var(--color-amber)" }}>
                              {(item.matched_confidence * 100).toFixed(0)}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {order.raw_message && (
                  <div className="mt-3 pt-3 border-t" style={{ borderColor: "var(--color-border)" }}>
                    <p className="text-xs font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>Raw Message</p>
                    <p className="text-sm p-2 rounded" style={{ background: "var(--color-bg)" }}>{order.raw_message}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {orders.length === 0 && (
          <div className="rounded-lg border p-8 text-center" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            <p style={{ color: "var(--color-text-muted)" }}>No orders matching filter &quot;{filter}&quot;</p>
          </div>
        )}
      </div>
    </div>
  );
}
