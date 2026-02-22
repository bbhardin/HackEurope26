"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getCustomer, getCustomerContext, getCustomerOrders, getCustomerConversations, getHealthEvents, sendCustomerMessage, logCommunication, getNudgeSuggestions, sendNudge, dismissNudge, getCustomerSuggestions } from "@/lib/api";
import { useToast } from "@/components/Toast";
import type { Customer, CustomerContext, Order, Conversation, HealthEvent, DetectedOrderChange, NudgeSuggestion } from "@/lib/types";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function CustomerDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [customer, setCustomer] = useState<Customer | null>(null);
  const [context, setContext] = useState<CustomerContext | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [healthEvts, setHealthEvts] = useState<HealthEvent[]>([]);
  const [msgInput, setMsgInput] = useState("");
  const [msgStatus, setMsgStatus] = useState("");
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteChannel, setNoteChannel] = useState("phone");
  const [noteText, setNoteText] = useState("");
  const [noteStatus, setNoteStatus] = useState("");
  const [detectedChanges, setDetectedChanges] = useState<DetectedOrderChange[]>([]);
  const [nudges, setNudges] = useState<NudgeSuggestion[]>([]);
  const [nudgeMsg, setNudgeMsg] = useState("");
  const [msgSuggestions, setMsgSuggestions] = useState<string[]>([]);
  const [chartPeriod, setChartPeriod] = useState<"week" | "month">("week");
  const { showToast } = useToast();

  const loadData = () => {
    if (!id) return;
    Promise.all([
      getCustomer(id),
      getCustomerContext(id),
      getCustomerOrders(id),
      getCustomerConversations(id),
      getHealthEvents(id),
      getNudgeSuggestions(),
    ]).then(([c, ctx, o, conv, he, allNudges]) => {
      setCustomer(c);
      setContext(ctx);
      setOrders(o);
      setConversations(conv);
      setHealthEvts(he);
      setNudges(allNudges.filter((n) => n.customer_id === id));
    }).catch(console.error);
    getCustomerSuggestions(id).then(setMsgSuggestions).catch(() => {});
  };

  useEffect(() => { loadData(); }, [id]);

  const handleSendMessage = async () => {
    if (!msgInput.trim()) return;
    setMsgStatus("Sending...");
    try {
      const result = await sendCustomerMessage(id, msgInput);
      setMsgInput("");
      if (result.detected_changes && result.detected_changes.length > 0) {
        setDetectedChanges(result.detected_changes);
        showToast("Sent via WhatsApp — order changes detected", "info");
      } else {
        showToast("Sent via WhatsApp");
      }
      setMsgStatus("");
      loadData();
    } catch (e) {
      showToast("Failed to send message", "error");
      setMsgStatus(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const handleLogNote = async () => {
    if (!noteText.trim()) return;
    setNoteStatus("Logging...");
    try {
      await logCommunication(id, noteChannel, noteText);
      setNoteText("");
      setNoteOpen(false);
      setNoteStatus("");
      showToast("Note logged");
      loadData();
    } catch (e) {
      showToast("Failed to log note", "error");
      setNoteStatus(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  if (!customer) {
    return <p style={{ color: "var(--color-text-muted)" }}>Loading...</p>;
  }

  const channelColor = (channel: string) => {
    switch (channel) {
      case "whatsapp": return "var(--color-green)";
      case "phone": return "var(--color-accent)";
      case "email": return "var(--color-amber)";
      default: return "var(--color-text-muted)";
    }
  };

  const severityColor = (severity: string) => {
    switch (severity) {
      case "critical": return "var(--color-red)";
      case "warning": return "var(--color-amber)";
      case "info": return "var(--color-green)";
      default: return "var(--color-text-muted)";
    }
  };

  return (
    <div>
      <Link href="/customers" className="text-sm mb-4 inline-block" style={{ color: "var(--color-accent)" }}>← Back to Customers</Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">{customer.name}</h2>
          <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
            {customer.type} · {customer.contact_phone} · {customer.delivery_address}
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

      {healthEvts.length > 0 && (
        <div className="rounded-lg border p-4 mb-6" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
          <h3 className="text-sm font-semibold mb-3">Health Timeline</h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {healthEvts.map((evt) => (
              <div key={evt.id} className="flex items-start gap-2">
                <span className="text-xs font-semibold px-1.5 py-0.5 rounded shrink-0" style={{
                  background: `${severityColor(evt.severity)}20`,
                  color: severityColor(evt.severity),
                }}>
                  {evt.severity}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs">{evt.detail}</p>
                  <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>{evt.event_type} · {evt.created_at.slice(0, 16).replace("T", " ")}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {nudges.length > 0 && (
        <div className="rounded-lg border p-4 mb-6" style={{ background: "rgba(245,158,11,0.05)", borderColor: "var(--color-amber)" }}>
          <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--color-amber)" }}>Nudge Suggestions</h3>
          {nudges.map((nudge) => (
            <div key={nudge.id} className="mb-3 last:mb-0">
              <p className="text-xs mb-1" style={{ color: "var(--color-text-muted)" }}>{nudge.reason}</p>
              <textarea
                defaultValue={nudge.suggested_message}
                onChange={(e) => setNudgeMsg(e.target.value)}
                className="w-full px-3 py-2 rounded border text-sm mb-2"
                rows={3}
                style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }}
              />
              <div className="flex gap-2">
                <button onClick={async () => { await sendNudge(nudge.id, nudgeMsg || undefined); loadData(); }} className="px-3 py-1.5 rounded text-xs font-medium cursor-pointer" style={{ background: "var(--color-amber)", color: "#fff" }}>Send Nudge</button>
                <button onClick={async () => { await dismissNudge(nudge.id); loadData(); }} className="px-3 py-1.5 rounded text-xs font-medium cursor-pointer border" style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}>Dismiss</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {detectedChanges.length > 0 && (
        <div className="mb-4 p-4 rounded-lg border" style={{ background: "rgba(79,140,255,0.1)", borderColor: "var(--color-accent)" }}>
          <p className="text-sm font-semibold mb-2" style={{ color: "var(--color-accent)" }}>Detected order changes from your message:</p>
          {detectedChanges.map((c, i) => (
            <p key={i} className="text-sm">{c.action}: {c.product_name} (qty change: {c.quantity_change})</p>
          ))}
          <button onClick={() => setDetectedChanges([])} className="mt-2 px-3 py-1.5 rounded text-xs font-semibold cursor-pointer border" style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}>Dismiss</button>
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
                      color: order.status === "fulfilled" ? "var(--color-green)" : order.status === "confirmed" ? "#22d3ee" : "var(--color-amber)",
                    }}>{order.status}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {order.items.map((item, idx) => (
                    <span key={item.id} className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                      {item.quantity}{item.unit} {item.product_name}{idx < order.items.length - 1 ? "," : ""}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold">Conversation History</h3>
            <button onClick={() => setNoteOpen(!noteOpen)} className="text-xs px-2 py-1 rounded border cursor-pointer"
              style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}>
              {noteOpen ? "Cancel" : "Log Communication"}
            </button>
          </div>

          {noteOpen && (
            <div className="rounded-lg border p-3 mb-3" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
              <div className="flex gap-2 mb-2">
                {["phone", "email", "in-person", "other"].map(ch => (
                  <button key={ch} onClick={() => setNoteChannel(ch)} className="text-xs px-2 py-1 rounded cursor-pointer"
                    style={{ background: noteChannel === ch ? "var(--color-accent)" : "transparent", color: noteChannel === ch ? "#fff" : "var(--color-text-muted)", border: `1px solid ${noteChannel === ch ? "var(--color-accent)" : "var(--color-border)"}` }}>
                    {ch}
                  </button>
                ))}
              </div>
              <textarea value={noteText} onChange={(e) => setNoteText(e.target.value)} placeholder="Describe the communication..."
                className="w-full px-3 py-2 rounded border text-sm mb-2" rows={2} style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
              <button onClick={handleLogNote} className="px-3 py-1.5 rounded text-xs font-medium cursor-pointer" style={{ background: "var(--color-accent)", color: "#fff" }}>Log Note</button>
              {noteStatus && <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>{noteStatus}</p>}
            </div>
          )}

          {conversations.length > 0 && conversations[0].direction === "outbound" && orders.some(o => o.status === "flagged" || o.status === "pending_confirmation") && (
            <p className="text-xs italic mb-2 px-1" style={{ color: "var(--color-amber)" }}>Awaiting customer response</p>
          )}
          {conversations.length > 0 && conversations[0].direction === "inbound" && orders.some(o => o.status === "flagged" || o.status === "pending_confirmation") && (
            <p className="text-xs italic mb-2 px-1" style={{ color: "var(--color-accent)" }}>Customer responded — review needed</p>
          )}

          <div className="rounded-lg border overflow-hidden max-h-96 overflow-y-auto" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            {conversations.slice(0, 30).map((conv) => (
              <div key={conv.id} className="px-4 py-3 border-b last:border-b-0" style={{ borderColor: "var(--color-border)" }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium px-1.5 py-0.5 rounded" style={{
                    background: conv.direction === "inbound" ? `${channelColor(conv.channel)}20` : "rgba(34,197,94,0.15)",
                    color: conv.direction === "inbound" ? channelColor(conv.channel) : "var(--color-green)",
                  }}>
                    {conv.direction === "inbound" ? conv.channel.toUpperCase() : "OUT"}
                  </span>
                  {conv.source === "manual" && (
                    <span className="text-xs px-1 py-0.5 rounded" style={{ background: "rgba(79,140,255,0.15)", color: "var(--color-accent)" }}>manual</span>
                  )}
                  {conv.source === "system" && conv.direction === "outbound" && (
                    <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>auto</span>
                  )}
                  <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>{conv.created_at.slice(0, 16).replace("T", " ")}</span>
                  {conv.parsed_intent && (
                    <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>[{conv.parsed_intent}]</span>
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

          <div className="mt-3">
            {msgSuggestions.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {msgSuggestions.map((s, i) => (
                  <button key={i} onClick={() => setMsgInput(s)} className="text-xs px-2 py-1 rounded border cursor-pointer transition-colors" style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}>
                    {s.slice(0, 60)}{s.length > 60 ? "..." : ""}
                  </button>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <input value={msgInput} onChange={(e) => setMsgInput(e.target.value)} placeholder="Send a WhatsApp message..."
                className="flex-1 px-3 py-2 rounded border text-sm" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
              <button onClick={handleSendMessage} className="px-3 py-2 rounded text-xs font-medium cursor-pointer" style={{ background: "var(--color-accent)", color: "#fff" }}>Send via WhatsApp</button>
            </div>
            {msgStatus && <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>{msgStatus}</p>}
          </div>
        </div>
      </div>

      {(() => {
        const threeMonthsAgo = new Date();
        threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);

        const buckets: Record<string, { label: string; value: number }> = {};
        orders
          .filter(o => o.status === "fulfilled" && new Date(o.created_at) >= threeMonthsAgo)
          .forEach(o => {
            const d = new Date(o.created_at);
            let key: string, label: string;
            if (chartPeriod === "month") {
              key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
              label = d.toLocaleDateString("en-GB", { month: "short", year: "2-digit" });
            } else {
              const mon = new Date(d);
              mon.setDate(d.getDate() - ((d.getDay() + 6) % 7));
              key = mon.toISOString().slice(0, 10);
              label = mon.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
            }
            if (!buckets[key]) buckets[key] = { label, value: 0 };
            buckets[key].value += o.total_value;
          });

        const chartData = Object.entries(buckets)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([, { label, value }]) => ({ date: label, value: Math.round(value) }));

        if (chartData.length === 0) return null;
        return (
          <div className="mt-6 rounded-lg border p-5" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Order Value — Last 3 Months</h3>
              <div className="flex gap-1">
                {(["week", "month"] as const).map(p => (
                  <button key={p} onClick={() => setChartPeriod(p)}
                    className="text-xs px-3 py-1 rounded cursor-pointer capitalize"
                    style={{
                      background: chartPeriod === p ? "var(--color-accent)" : "var(--color-bg)",
                      color: chartPeriod === p ? "#fff" : "var(--color-text-muted)",
                      border: `1px solid ${chartPeriod === p ? "var(--color-accent)" : "var(--color-border)"}`,
                    }}>
                    {p}
                  </button>
                ))}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData} margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
                <defs>
                  <linearGradient id="orderValueGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f8cff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#4f8cff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--color-text-muted)" }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "var(--color-text-muted)" }} tickLine={false} axisLine={false}
                  tickFormatter={v => `€${Number(v).toLocaleString()}`} width={70} />
                <Tooltip
                  contentStyle={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "6px", fontSize: "12px" }}
                  labelStyle={{ color: "var(--color-text-muted)" }}
                  formatter={(v: number) => [`EUR ${v.toLocaleString()}`, "Total Value"]}
                />
                <Area type="monotone" dataKey="value" stroke="#4f8cff" strokeWidth={2} fill="url(#orderValueGradient)" dot={{ r: 3, fill: "#4f8cff" }} activeDot={{ r: 5 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        );
      })()}
    </div>
  );
}
