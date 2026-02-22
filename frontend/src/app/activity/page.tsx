"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { getActivity } from "@/lib/api";
import type { AgentAction } from "@/lib/types";

export default function ActivityPage() {
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [agentFilter, setAgentFilter] = useState<string>("");

  const loadActions = useCallback(async () => {
    try {
      const data = await getActivity(100, agentFilter || undefined);
      setActions(data);
    } catch (e) {
      console.error("Failed to load activity:", e);
    }
  }, [agentFilter]);

  useEffect(() => {
    loadActions();
    const interval = setInterval(loadActions, 5000);
    return () => clearInterval(interval);
  }, [loadActions]);

  const agentColor = (type: string) => {
    switch (type) {
      case "customer_agent": return "var(--color-accent)";
      case "orchestrator": return "var(--color-green)";
      case "nudge_scheduler": return "var(--color-amber)";
      default: return "var(--color-text-muted)";
    }
  };

  const filters = [
    { value: "", label: "All" },
    { value: "customer_agent", label: "Customer Agent" },
    { value: "orchestrator", label: "Orchestrator" },
    { value: "nudge_scheduler", label: "Nudge Scheduler" },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Activity Log</h2>

      <div className="flex gap-2 mb-6">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => setAgentFilter(f.value)}
            className="px-3 py-1.5 rounded text-sm font-medium transition-colors cursor-pointer"
            style={{
              background: agentFilter === f.value ? "var(--color-accent)" : "var(--color-surface)",
              color: agentFilter === f.value ? "#fff" : "var(--color-text-muted)",
              border: `1px solid ${agentFilter === f.value ? "var(--color-accent)" : "var(--color-border)"}`,
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="rounded-lg border overflow-hidden" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
        <table className="w-full text-sm">
          <thead>
            <tr style={{ color: "var(--color-text-muted)" }}>
              <th className="text-left text-xs font-medium px-4 py-3">Timestamp</th>
              <th className="text-left text-xs font-medium px-4 py-3">Agent</th>
              <th className="text-left text-xs font-medium px-4 py-3">Action</th>
              <th className="text-left text-xs font-medium px-4 py-3">Customer</th>
              <th className="text-left text-xs font-medium px-4 py-3">Order</th>
              <th className="text-right text-xs font-medium px-4 py-3">Confidence</th>
              <th className="text-left text-xs font-medium px-4 py-3">Details</th>
            </tr>
          </thead>
          <tbody>
            {actions.map((action) => {
              let details = "";
              try {
                const parsed = JSON.parse(action.details_json);
                details = Object.entries(parsed)
                  .slice(0, 3)
                  .map(([k, v]) => `${k}: ${typeof v === "string" ? v.slice(0, 40) : String(v)}`)
                  .join(", ");
              } catch {
                details = action.details_json.slice(0, 80);
              }

              return (
                <tr key={action.id} className="border-t" style={{ borderColor: "var(--color-border)" }}>
                  <td className="px-4 py-2.5 text-xs font-mono" style={{ color: "var(--color-text-muted)" }}>
                    {action.created_at.slice(0, 19).replace("T", " ")}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs font-semibold" style={{ color: agentColor(action.agent_type) }}>
                      {action.agent_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs">{action.action}</td>
                  <td className="px-4 py-2.5 text-xs">
                    {action.customer_name ? (
                      <Link href={`/customers/${action.resolved_customer_id}`} style={{ color: "var(--color-accent)" }}>
                        {action.customer_name}
                      </Link>
                    ) : action.entity_type === "phone" ? (
                      <span style={{ color: "var(--color-text-muted)" }}>{action.entity_id}</span>
                    ) : (
                      <span style={{ color: "var(--color-text-muted)" }}>—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-xs font-mono" style={{ color: "var(--color-text-muted)" }}>
                    {action.related_order_id || "—"}
                  </td>
                  <td className="px-4 py-2.5 text-right text-xs">
                    {action.confidence !== null ? `${(action.confidence * 100).toFixed(0)}%` : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-xs" style={{ color: "var(--color-text-muted)", maxWidth: "300px" }}>
                    {details}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {actions.length === 0 && (
          <p className="p-4 text-sm text-center" style={{ color: "var(--color-text-muted)" }}>No activity recorded</p>
        )}
      </div>
    </div>
  );
}
