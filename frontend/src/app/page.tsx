"use client";

import { useEffect, useState, useCallback } from "react";
import { getOrdersOverview, getOrders, getAlerts, simulateMessage, triggerNudgeScan } from "@/lib/api";
import type { OrdersOverview, Order, Alert } from "@/lib/types";

function KpiCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color: string }) {
  return (
    <div className="rounded-lg p-5 border" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
      <p className="text-xs font-medium uppercase tracking-wider mb-2" style={{ color: "var(--color-text-muted)" }}>{label}</p>
      <p className="text-2xl font-bold" style={{ color }}>{value}</p>
      {sub && <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>{sub}</p>}
    </div>
  );
}

export default function OverviewPage() {
  const [overview, setOverview] = useState<OrdersOverview | null>(null);
  const [recentOrders, setRecentOrders] = useState<Order[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [simPhone, setSimPhone] = useState("+4917612345002");
  const [simMessage, setSimMessage] = useState("Hi, I need 20kg chicken breast, 10kg potatoes, and the usual olive oil please");
  const [simStatus, setSimStatus] = useState("");

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
      case "confirmed": return "var(--color-green)";
      case "pending_confirmation": return "var(--color-amber)";
      case "flagged": return "var(--color-red)";
      case "rejected": return "var(--color-red)";
      default: return "var(--color-text-muted)";
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Order Overview</h2>

      {overview && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <KpiCard label="Pending Orders" value={String(overview.pending_count)} sub={`EUR ${overview.pending_value.toLocaleString()}`} color="var(--color-amber)" />
          <KpiCard label="Confirmed Today" value={String(overview.confirmed_today_count)} sub={`EUR ${overview.confirmed_today_value.toLocaleString()}`} color="var(--color-green)" />
          <KpiCard label="Total Confirmed" value={String(overview.confirmed_all_count)} sub={`EUR ${overview.confirmed_all_value.toLocaleString()}`} color="var(--color-accent)" />
          <KpiCard label="Flagged / Rejected" value={`${overview.flagged_count} / ${overview.rejected_count}`} color="var(--color-red)" />
        </div>
      )}

      <div className="grid grid-cols-2 gap-6 mb-8">
        <div>
          <h3 className="text-lg font-semibold mb-3">Recent Orders</h3>
          <div className="rounded-lg border overflow-hidden" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            {recentOrders.map((order) => (
              <div key={order.id} className="flex items-center justify-between px-4 py-3 border-b last:border-b-0" style={{ borderColor: "var(--color-border)" }}>
                <div>
                  <p className="text-sm font-medium">{order.customer_name}</p>
                  <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>{order.created_at.slice(0, 16).replace("T", " ")}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">EUR {order.total_value.toFixed(2)}</p>
                  <p className="text-xs font-medium" style={{ color: statusColor(order.status) }}>{order.status}</p>
                </div>
              </div>
            ))}
            {recentOrders.length === 0 && (
              <p className="p-4 text-sm" style={{ color: "var(--color-text-muted)" }}>No recent orders</p>
            )}
          </div>
        </div>

        <div>
          <h3 className="text-lg font-semibold mb-3">Active Alerts</h3>
          <div className="rounded-lg border overflow-hidden" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            {alerts.map((alert) => (
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
                <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>{alert.detail.slice(0, 120)}</p>
              </div>
            ))}
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
            <input
              className="w-full px-3 py-2 rounded border text-sm"
              style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }}
              value={simPhone}
              onChange={(e) => setSimPhone(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block" style={{ color: "var(--color-text-muted)" }}>Message</label>
            <input
              className="w-full px-3 py-2 rounded border text-sm"
              style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }}
              value={simMessage}
              onChange={(e) => setSimMessage(e.target.value)}
            />
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleSimulate}
            className="px-4 py-2 rounded text-sm font-medium transition-colors cursor-pointer"
            style={{ background: "var(--color-accent)", color: "#fff" }}
          >
            Send Simulated Message
          </button>
          <button
            onClick={handleNudge}
            className="px-4 py-2 rounded text-sm font-medium border transition-colors cursor-pointer"
            style={{ borderColor: "var(--color-border)", color: "var(--color-text)" }}
          >
            Trigger Nudge Scan
          </button>
        </div>
        {simStatus && (
          <p className="text-xs mt-2" style={{ color: "var(--color-text-muted)" }}>{simStatus}</p>
        )}
      </div>
    </div>
  );
}
