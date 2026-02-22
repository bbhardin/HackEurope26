"use client";

import { useEffect, useState, useCallback } from "react";
import { getOrders, approveOrder, rejectOrder, fulfilOrder, sendOrderMessage, clarifyOrder, updateOrderItems, searchProducts } from "@/lib/api";
import type { Order, Product, DetectedOrderChange } from "@/lib/types";

function formatQty(qty: number, unitType: string) {
  return unitType === "discrete" ? String(Math.round(qty)) : qty.toFixed(1);
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [filter, setFilter] = useState("pending_confirmation");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [processing, setProcessing] = useState<string | null>(null);
  const [msgInputs, setMsgInputs] = useState<Record<string, string>>({});
  const [msgStatus, setMsgStatus] = useState<Record<string, string>>({});
  const [editingOrder, setEditingOrder] = useState<string | null>(null);
  const [editItems, setEditItems] = useState<{ product_id: string; quantity: number; unit_price: number; product_name: string; unit: string; unit_type: string }[]>([]);
  const [productSearch, setProductSearch] = useState("");
  const [productResults, setProductResults] = useState<Product[]>([]);
  const [detectedChanges, setDetectedChanges] = useState<DetectedOrderChange[]>([]);
  const [changeOrderId, setChangeOrderId] = useState("");

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
    try { await approveOrder(orderId); loadOrders(); } catch (e) { console.error(e); }
    setProcessing(null);
  };

  const handleReject = async (orderId: string) => {
    setProcessing(orderId);
    try { await rejectOrder(orderId); loadOrders(); } catch (e) { console.error(e); }
    setProcessing(null);
  };

  const handleFulfil = async (orderId: string) => {
    setProcessing(orderId);
    try { await fulfilOrder(orderId); loadOrders(); } catch (e) { console.error(e); }
    setProcessing(null);
  };

  const handleSendMessage = async (orderId: string) => {
    const msg = msgInputs[orderId];
    if (!msg?.trim()) return;
    setMsgStatus({ ...msgStatus, [orderId]: "Sending..." });
    try {
      const result = await sendOrderMessage(orderId, msg);
      setMsgInputs({ ...msgInputs, [orderId]: "" });
      if (result.detected_changes && result.detected_changes.length > 0) {
        setDetectedChanges(result.detected_changes);
        setChangeOrderId(orderId);
        setMsgStatus({ ...msgStatus, [orderId]: "Sent! Order changes detected — see prompt below." });
      } else {
        setMsgStatus({ ...msgStatus, [orderId]: "Sent!" });
      }
    } catch (e) {
      setMsgStatus({ ...msgStatus, [orderId]: `Error: ${e instanceof Error ? e.message : String(e)}` });
    }
  };

  const handleClarify = async (orderId: string) => {
    const msg = msgInputs[orderId];
    if (!msg?.trim()) return;
    setMsgStatus({ ...msgStatus, [orderId]: "Sending clarification..." });
    try {
      await clarifyOrder(orderId, msg);
      setMsgInputs({ ...msgInputs, [orderId]: "" });
      setMsgStatus({ ...msgStatus, [orderId]: "Clarification sent!" });
    } catch (e) {
      setMsgStatus({ ...msgStatus, [orderId]: `Error: ${e instanceof Error ? e.message : String(e)}` });
    }
  };

  const startEdit = (order: Order) => {
    setEditingOrder(order.id);
    setEditItems(order.items.map(i => ({
      product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price,
      product_name: i.product_name, unit: i.unit, unit_type: i.unit_type,
    })));
  };

  const handleSaveEdit = async (orderId: string) => {
    setProcessing(orderId);
    try {
      await updateOrderItems(orderId, editItems.map(i => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price })));
      setEditingOrder(null);
      loadOrders();
    } catch (e) { console.error(e); }
    setProcessing(null);
  };

  const handleProductSearch = async (q: string) => {
    setProductSearch(q);
    if (q.length >= 2) {
      const results = await searchProducts(q);
      setProductResults(results);
    } else {
      setProductResults([]);
    }
  };

  const addProduct = (p: Product) => {
    setEditItems([...editItems, { product_id: p.id, quantity: 1, unit_price: p.price_default, product_name: p.name, unit: p.unit, unit_type: p.unit_type }]);
    setProductSearch("");
    setProductResults([]);
  };

  const applyDetectedChanges = async () => {
    if (!changeOrderId || detectedChanges.length === 0) return;
    const order = orders.find(o => o.id === changeOrderId);
    if (!order) return;
    const currentItems = order.items.map(i => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price }));
    for (const change of detectedChanges) {
      if (change.action === "remove_item") {
        const idx = currentItems.findIndex(i => i.product_id === change.product_id);
        if (idx >= 0) currentItems.splice(idx, 1);
      } else if (change.action === "change_quantity") {
        const item = currentItems.find(i => i.product_id === change.product_id);
        if (item) item.quantity = Math.max(0, item.quantity + change.quantity_change);
      }
    }
    try {
      await updateOrderItems(changeOrderId, currentItems.filter(i => i.quantity > 0));
      setDetectedChanges([]);
      setChangeOrderId("");
      loadOrders();
    } catch (e) { console.error(e); }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "fulfilled": return "var(--color-green)";
      case "confirmed": return "#22d3ee";
      case "pending_confirmation": return "var(--color-amber)";
      case "flagged": return "var(--color-red)";
      case "rejected": return "var(--color-red)";
      case "needs_clarification": return "var(--color-amber)";
      default: return "var(--color-text-muted)";
    }
  };

  const filters = [
    { value: "pending_confirmation", label: "Pending" },
    { value: "flagged", label: "Flagged" },
    { value: "needs_clarification", label: "Clarification" },
    { value: "confirmed", label: "Confirmed" },
    { value: "fulfilled", label: "Fulfilled" },
    { value: "rejected", label: "Rejected" },
    { value: "all", label: "All" },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Order Queue</h2>

      <div className="flex gap-2 mb-6">
        {filters.map((f) => (
          <button key={f.value} onClick={() => setFilter(f.value)} className="px-3 py-1.5 rounded text-sm font-medium transition-colors cursor-pointer"
            style={{ background: filter === f.value ? "var(--color-accent)" : "var(--color-surface)", color: filter === f.value ? "#fff" : "var(--color-text-muted)", border: `1px solid ${filter === f.value ? "var(--color-accent)" : "var(--color-border)"}` }}>
            {f.label}
          </button>
        ))}
      </div>

      {detectedChanges.length > 0 && (
        <div className="mb-4 p-4 rounded-lg border" style={{ background: "rgba(79,140,255,0.1)", borderColor: "var(--color-accent)" }}>
          <p className="text-sm font-semibold mb-2" style={{ color: "var(--color-accent)" }}>Detected order changes from your message:</p>
          {detectedChanges.map((c, i) => (
            <p key={i} className="text-sm">{c.action}: {c.product_name} (qty change: {c.quantity_change})</p>
          ))}
          <div className="flex gap-2 mt-3">
            <button onClick={applyDetectedChanges} className="px-3 py-1.5 rounded text-xs font-semibold cursor-pointer" style={{ background: "var(--color-accent)", color: "#fff" }}>Apply Changes</button>
            <button onClick={() => { setDetectedChanges([]); setChangeOrderId(""); }} className="px-3 py-1.5 rounded text-xs font-semibold cursor-pointer border" style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}>Dismiss</button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {orders.map((order) => {
          const isEditing = editingOrder === order.id;
          return (
            <div key={order.id} className="rounded-lg border transition-colors" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
              <div className="flex items-center justify-between px-5 py-4 cursor-pointer" onClick={() => setExpanded(expanded === order.id ? null : order.id)}>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold">{order.customer_name}</p>
                    {order.flags && order.flags.length > 0 && order.flags.map((flag, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded" style={{ background: "rgba(239,68,68,0.15)", color: "var(--color-red)" }}>{flag.slice(0, 60)}</span>
                    ))}
                  </div>
                  <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>{order.created_at.slice(0, 16).replace("T", " ")} · {order.items.length} items</p>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm font-bold">EUR {order.total_value.toFixed(2)}</p>
                    <p className="text-xs font-medium" style={{ color: statusColor(order.status) }}>{order.status}</p>
                  </div>
                  {(order.status === "pending_confirmation" || order.status === "flagged") && (
                    <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                      <button onClick={() => handleApprove(order.id)} disabled={processing === order.id} className="px-3 py-1.5 rounded text-xs font-semibold cursor-pointer disabled:opacity-50" style={{ background: "var(--color-green)", color: "#fff" }}>{processing === order.id ? "..." : "Approve"}</button>
                      <button onClick={() => handleReject(order.id)} disabled={processing === order.id} className="px-3 py-1.5 rounded text-xs font-semibold cursor-pointer disabled:opacity-50" style={{ background: "var(--color-red)", color: "#fff" }}>Reject</button>
                    </div>
                  )}
                  {order.status === "confirmed" && (
                    <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                      <button onClick={() => handleFulfil(order.id)} disabled={processing === order.id} className="px-3 py-1.5 rounded text-xs font-semibold cursor-pointer disabled:opacity-50" style={{ background: "var(--color-accent)", color: "#fff" }}>Mark Fulfilled</button>
                    </div>
                  )}
                  {order.status === "needs_clarification" && (
                    <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                      <button onClick={() => handleApprove(order.id)} disabled={processing === order.id} className="px-3 py-1.5 rounded text-xs font-semibold cursor-pointer disabled:opacity-50" style={{ background: "var(--color-green)", color: "#fff" }}>Approve Anyway</button>
                      <button onClick={() => handleReject(order.id)} disabled={processing === order.id} className="px-3 py-1.5 rounded text-xs font-semibold cursor-pointer disabled:opacity-50" style={{ background: "var(--color-red)", color: "#fff" }}>Reject</button>
                    </div>
                  )}
                </div>
              </div>

              {expanded === order.id && (
                <div className="px-5 pb-4 border-t" style={{ borderColor: "var(--color-border)" }}>
                  <div className="pt-3 flex justify-between items-center mb-2">
                    <p className="text-xs font-medium" style={{ color: "var(--color-text-muted)" }}>Order Items</p>
                    {!isEditing && (order.status === "pending_confirmation" || order.status === "confirmed" || order.status === "flagged") && (
                      <button onClick={() => startEdit(order)} className="text-xs px-2 py-1 rounded border cursor-pointer" style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}>Edit</button>
                    )}
                    {isEditing && (
                      <div className="flex gap-2">
                        <button onClick={() => handleSaveEdit(order.id)} className="text-xs px-2 py-1 rounded cursor-pointer" style={{ background: "var(--color-green)", color: "#fff" }}>Save</button>
                        <button onClick={() => setEditingOrder(null)} className="text-xs px-2 py-1 rounded border cursor-pointer" style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}>Cancel</button>
                      </div>
                    )}
                  </div>

                  {!isEditing ? (
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
                              <p className="font-medium" style={{ color: item.matched_confidence < 0.7 ? "var(--color-amber)" : undefined }}>{item.product_name}</p>
                              {item.original_text && <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>&quot;{item.original_text.slice(0, 60)}&quot;</p>}
                            </td>
                            <td className="text-right py-2">{formatQty(item.quantity, item.unit_type)} {item.unit}</td>
                            <td className="text-right py-2">EUR {item.unit_price.toFixed(2)}</td>
                            <td className="text-right py-2 font-medium">EUR {(item.quantity * item.unit_price).toFixed(2)}</td>
                            <td className="text-right py-2">
                              <span style={{ color: item.matched_confidence >= 0.9 ? "var(--color-green)" : item.matched_confidence >= 0.7 ? "var(--color-amber)" : "var(--color-red)" }}>
                                {(item.matched_confidence * 100).toFixed(0)}%
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="space-y-2">
                      {editItems.map((item, idx) => (
                        <div key={idx} className="flex items-center gap-3 py-1">
                          <span className="text-sm flex-1">{item.product_name} ({item.unit})</span>
                          <input type="number" value={item.quantity} min={item.unit_type === "discrete" ? 1 : 0.1} step={item.unit_type === "discrete" ? 1 : 0.1}
                            onChange={(e) => { const nv = [...editItems]; nv[idx] = { ...nv[idx], quantity: parseFloat(e.target.value) || 0 }; setEditItems(nv); }}
                            className="w-20 px-2 py-1 rounded border text-sm text-right" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
                          <span className="text-xs w-20 text-right">EUR {item.unit_price.toFixed(2)}</span>
                          <button onClick={() => setEditItems(editItems.filter((_, i) => i !== idx))} className="text-xs cursor-pointer" style={{ color: "var(--color-red)" }}>✕</button>
                        </div>
                      ))}
                      <div className="relative mt-2">
                        <input placeholder="Search products to add..." value={productSearch} onChange={(e) => handleProductSearch(e.target.value)}
                          className="w-full px-3 py-2 rounded border text-sm" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
                        {productResults.length > 0 && (
                          <div className="absolute top-full left-0 right-0 rounded border mt-1 max-h-40 overflow-y-auto z-10" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
                            {productResults.map(p => (
                              <button key={p.id} onClick={() => addProduct(p)} className="w-full text-left px-3 py-2 text-sm cursor-pointer hover:opacity-80" style={{ color: "var(--color-text)" }}>
                                {p.name} ({p.unit}) — EUR {p.price_default.toFixed(2)}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {order.raw_message && (
                    <div className="mt-3 pt-3 border-t" style={{ borderColor: "var(--color-border)" }}>
                      <p className="text-xs font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>Raw Message</p>
                      <p className="text-sm p-2 rounded" style={{ background: "var(--color-bg)" }}>{order.raw_message}</p>
                    </div>
                  )}

                  <div className="mt-3 pt-3 border-t" style={{ borderColor: "var(--color-border)" }}>
                    <p className="text-xs font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>Send Message to Customer</p>
                    <div className="flex gap-2">
                      <input value={msgInputs[order.id] || ""} onChange={(e) => setMsgInputs({ ...msgInputs, [order.id]: e.target.value })} placeholder="Type a message..."
                        className="flex-1 px-3 py-2 rounded border text-sm" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
                      <button onClick={() => handleSendMessage(order.id)} className="px-3 py-2 rounded text-xs font-medium cursor-pointer" style={{ background: "var(--color-accent)", color: "#fff" }}>Send</button>
                      {order.status === "needs_clarification" && (
                        <button onClick={() => handleClarify(order.id)} className="px-3 py-2 rounded text-xs font-medium cursor-pointer border" style={{ borderColor: "var(--color-amber)", color: "var(--color-amber)" }}>Clarify</button>
                      )}
                    </div>
                    {msgStatus[order.id] && <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>{msgStatus[order.id]}</p>}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {orders.length === 0 && (
          <div className="rounded-lg border p-8 text-center" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            <p style={{ color: "var(--color-text-muted)" }}>No orders matching filter &quot;{filter}&quot;</p>
          </div>
        )}
      </div>
    </div>
  );
}
