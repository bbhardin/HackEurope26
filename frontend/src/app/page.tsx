"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { getOrdersOverview, getOrders, getAlerts, simulateMessage, triggerNudgeScan, getActivity } from "@/lib/api";
import type { OrdersOverview, Order, Alert, AgentAction } from "@/lib/types";

function KpiCard({ label, value, sub, color, href, icon }: { label: string; value: string; sub?: string; color: string; href?: string; icon?: React.ReactNode }) {
  const content = (
    <div className="rounded-lg p-5 border transition-colors" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
      <div className="flex items-center gap-2 mb-2">
        {icon && <span style={{ color }}>{icon}</span>}
        <p className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>{label}</p>
      </div>
      <p className="text-2xl font-bold" style={{ color }}>{value}</p>
      {sub && <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>{sub}</p>}
    </div>
  );
  if (href) return <Link href={href}>{content}</Link>;
  return content;
}

function SmallKpiCard({ label, value, sub, color, href }: { label: string; value: string; sub?: string; color: string; href?: string }) {
  const content = (
    <div className="rounded-lg px-4 py-2 border transition-colors" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
      <p className="text-xs font-medium uppercase tracking-wider mb-0.0" style={{ color: "var(--color-text-muted)" }}>{label}</p>
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-base font-bold" style={{ color }}>{value}</p>
        {sub && <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>{sub}</p>}
      </div>
    </div>
  );
  if (href) return <Link href={href}>{content}</Link>;
  return content;
}

function alertActionHref(alert: Alert): string | null {
  switch (alert.type) {
    case "anomaly":
    case "agent_note":
    case "order_modified":
      return "/orders";
    case "churn_risk":
    case "incoming_message":
      return alert.customer_id ? `/customers/${alert.customer_id}` : null;
    default:
      return null;
  }
}

function alertActionLabel(type: string): string {
  switch (type) {
    case "anomaly":
    case "agent_note":
    case "order_modified":
      return "Review";
    case "churn_risk":
      return "View Customer";
    case "incoming_message":
      return "Reply";
    default:
      return "View";
  }
}

export default function OverviewPage() {
  const [overview, setOverview] = useState<OrdersOverview | null>(null);
  const [recentOrders, setRecentOrders] = useState<Order[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [simPhone, setSimPhone] = useState("+4917612345002");
  const [simMessage, setSimMessage] = useState("Hi, I need 20kg chicken breast, 10kg potatoes, and the usual olive oil please");
  const [simStatus, setSimStatus] = useState("");
  const [lastActivity, setLastActivity] = useState<AgentAction | null>(null);
  const [recentActionCount, setRecentActionCount] = useState(0);

  const loadData = useCallback(async () => {
    try {
      const [ov, orders, al] = await Promise.all([
        getOrdersOverview(),
        getOrders(),
        getAlerts(),
      ]);
      setOverview(ov);
      setRecentOrders(orders.slice(0, 8));
      setAlerts(al.slice(0, 5));
      const activity = await getActivity(20);
      if (activity.length > 0) {
        setLastActivity(activity[0]);
        const oneHourAgo = new Date(Date.now() - 3600000).toISOString();
        setRecentActionCount(activity.filter((a) => a.created_at >= oneHourAgo).length);
      }
    } catch (e) {
      console.error("Failed to load overview:", e);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleSimulate = async () => {
    setSimStatus("Sending...");
    try {
      await simulateMessage(simPhone, simMessage);
      setSimStatus("Message processed!");
      loadData();
    } catch (e) {
      setSimStatus(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const handleNudge = async () => {
    setSimStatus("Running nudge scan...");
    try {
      const result = await triggerNudgeScan();
      setSimStatus(`Nudge scan complete: ${result.nudges_sent} nudges sent, ${result.alerts_created} alerts`);
      loadData();
    } catch (e) {
      setSimStatus(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "fulfilled": return "var(--color-green)";
      case "confirmed": return "#22d3ee";
      case "pending_confirmation": return "var(--color-amber)";
      case "flagged": return "var(--color-red)";
      case "rejected": return "var(--color-red)";
      default: return "var(--color-text-muted)";
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Order Overview</h2>

      {lastActivity && (
        <Link href="/activity" className="flex items-center gap-3 mb-6 px-4 py-2.5 rounded-lg border transition-opacity hover:opacity-80" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
          <span className="w-2 h-2 rounded-full shrink-0" style={{ background: "var(--color-green)" }} />
          <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
            Agent is active — {recentActionCount} action{recentActionCount !== 1 ? "s" : ""} in the last hour.
            Last: <span style={{ color: "var(--color-text)" }}>{lastActivity.action}</span> at {lastActivity.created_at.slice(11, 16)}
          </p>
        </Link>
      )}

      {overview && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <KpiCard label="Pending" value={String(overview.pending_count)} sub={`EUR ${overview.pending_value.toLocaleString()}`} color="var(--color-amber)" href="/orders?filter=pending_confirmation"
            icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>} />
          <KpiCard label="Confirmed" value={String(overview.confirmed_all_count)} sub={`EUR ${overview.confirmed_all_value.toLocaleString()}`} color="#22d3ee" href="/orders?filter=confirmed"
            icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="9 12 11 14 15 10"/></svg>} />
          <KpiCard label="Fulfilled Today" value={String(overview.fulfilled_today_count)} sub={`EUR ${overview.fulfilled_today_value.toLocaleString()}`} color="var(--color-green)" href="/orders?filter=fulfilled"
            icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>} />
          <div className="flex flex-col gap-1.5">
            <SmallKpiCard label="Total Fulfilled" value={String(overview.fulfilled_all_count)} sub={`EUR ${overview.fulfilled_all_value.toLocaleString()}`} color="var(--color-accent)" href="/orders?filter=fulfilled" />
            <SmallKpiCard label="Flagged / Rejected" value={`${overview.flagged_count} / ${overview.rejected_count}`} color="var(--color-red)" href="/orders?filter=flagged" />
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6 mb-8">
        <div>
          <h3 className="text-lg font-semibold mb-3">Recent Orders</h3>
          <div className="rounded-lg border overflow-hidden" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            {recentOrders.map((order) => (
              <Link key={order.id} href="/orders" className="flex items-center justify-between px-4 py-3 border-b last:border-b-0 transition-colors" style={{ borderColor: "var(--color-border)" }}>
                <div>
                  <p className="text-sm font-medium">{order.customer_name}</p>
                  <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>{order.created_at.slice(0, 16).replace("T", " ")}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">EUR {order.total_value.toFixed(2)}</p>
                  <p className="text-xs font-medium" style={{ color: statusColor(order.status) }}>{order.status}</p>
                </div>
              </Link>
            ))}
            {recentOrders.length === 0 && (
              <p className="p-4 text-sm" style={{ color: "var(--color-text-muted)" }}>No recent orders</p>
            )}
          </div>
        </div>

        <div>
          <h3 className="text-lg font-semibold mb-3">Active Alerts</h3>
          <div className="rounded-lg border overflow-hidden" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            {alerts.map((alert) => {
              const actionHref = alertActionHref(alert);
              return (
                <div key={alert.id} className="px-4 py-3 border-b last:border-b-0" style={{ borderColor: "var(--color-border)" }}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium px-2 py-0.5 rounded" style={{
                      background: alert.type === "churn_risk" ? "rgba(239,68,68,0.15)" : "rgba(245,158,11,0.15)",
                      color: alert.type === "churn_risk" ? "var(--color-red)" : "var(--color-amber)",
                    }}>
                      {alert.type}
                    </span>
                    {alert.customer_name && <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>{alert.customer_name}</span>}
                  </div>
                  <div className="flex items-center justify-between">
                    <p className="text-xs flex-1" style={{ color: "var(--color-text-muted)" }}>{alert.detail.slice(0, 120)}</p>
                    {actionHref && (
                      <Link href={actionHref} className="ml-2 text-xs font-medium px-2 py-1 rounded shrink-0" style={{ color: "var(--color-accent)" }}>
                        {alertActionLabel(alert.type)}
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
            {alerts.length === 0 && (
              <p className="p-4 text-sm" style={{ color: "var(--color-text-muted)" }}>No active alerts</p>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-lg border p-5" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
        <h3 className="text-lg font-semibold mb-3">Demo Controls</h3>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-xs font-medium mb-1 block" style={{ color: "var(--color-text-muted)" }}>Phone Number</label>
            <input className="w-full px-3 py-2 rounded border text-sm" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} value={simPhone} onChange={(e) => setSimPhone(e.target.value)} />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block" style={{ color: "var(--color-text-muted)" }}>Message</label>
            <input className="w-full px-3 py-2 rounded border text-sm" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} value={simMessage} onChange={(e) => setSimMessage(e.target.value)} />
          </div>
        </div>
        <div className="flex gap-3">
          <button onClick={handleSimulate} className="px-4 py-2 rounded text-sm font-medium transition-colors cursor-pointer" style={{ background: "var(--color-accent)", color: "#fff" }}>Send Simulated Message</button>
          <button onClick={handleNudge} className="px-4 py-2 rounded text-sm font-medium border transition-colors cursor-pointer" style={{ borderColor: "var(--color-border)", color: "var(--color-text)" }}>Trigger Nudge Scan</button>
        </div>
        {simStatus && <p className="text-xs mt-2" style={{ color: "var(--color-text-muted)" }}>{simStatus}</p>}
      </div>
    </div>
  );
}
