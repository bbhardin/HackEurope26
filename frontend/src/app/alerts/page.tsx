"use client";

import { useEffect, useState, useCallback } from "react";
import { getAlerts, acknowledgeAlert } from "@/lib/api";
import type { Alert } from "@/lib/types";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [showAcknowledged, setShowAcknowledged] = useState(false);

  const loadAlerts = useCallback(async () => {
    try {
      const data = await getAlerts(showAcknowledged);
      setAlerts(data);
    } catch (e) {
      console.error("Failed to load alerts:", e);
    }
  }, [showAcknowledged]);

  useEffect(() => {
    loadAlerts();
    const interval = setInterval(loadAlerts, 5000);
    return () => clearInterval(interval);
  }, [loadAlerts]);

  const handleAcknowledge = async (alertId: string) => {
    try {
      await acknowledgeAlert(alertId);
      loadAlerts();
    } catch (e) {
      console.error("Failed to acknowledge:", e);
    }
  };

  const typeColor = (type: string) => {
    switch (type) {
      case "churn_risk": return { bg: "rgba(239,68,68,0.15)", text: "var(--color-red)" };
      case "anomaly": return { bg: "rgba(245,158,11,0.15)", text: "var(--color-amber)" };
      case "unknown_customer": return { bg: "rgba(79,140,255,0.15)", text: "var(--color-accent)" };
      case "order_modified": return { bg: "rgba(34,197,94,0.15)", text: "var(--color-green)" };
      default: return { bg: "rgba(139,143,163,0.15)", text: "var(--color-text-muted)" };
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Alerts</h2>
        <button
          onClick={() => setShowAcknowledged(!showAcknowledged)}
          className="px-3 py-1.5 rounded text-sm font-medium border cursor-pointer"
          style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}
        >
          {showAcknowledged ? "Show Active" : "Show Acknowledged"}
        </button>
      </div>

      <div className="space-y-3">
        {alerts.map((alert) => {
          const colors = typeColor(alert.type);
          return (
            <div
              key={alert.id}
              className="rounded-lg border px-5 py-4 flex items-start justify-between"
              style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-semibold px-2 py-0.5 rounded" style={{ background: colors.bg, color: colors.text }}>
                    {alert.type}
                  </span>
                  {alert.customer_name && (
                    <span className="text-sm font-medium">{alert.customer_name}</span>
                  )}
                  <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                    {alert.created_at.slice(0, 16).replace("T", " ")}
                  </span>
                </div>
                <p className="text-sm" style={{ color: "var(--color-text)" }}>{alert.detail}</p>
              </div>
              {!alert.acknowledged && (
                <button
                  onClick={() => handleAcknowledge(alert.id)}
                  className="ml-4 px-3 py-1.5 rounded text-xs font-medium border cursor-pointer shrink-0"
                  style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}
                >
                  Dismiss
                </button>
              )}
            </div>
          );
        })}
        {alerts.length === 0 && (
          <div className="rounded-lg border p-8 text-center" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
            <p style={{ color: "var(--color-text-muted)" }}>
              {showAcknowledged ? "No acknowledged alerts" : "No active alerts"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
