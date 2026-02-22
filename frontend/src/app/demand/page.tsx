"use client";

import { useEffect, useState, useCallback } from "react";
import { getAggregatedItems } from "@/lib/api";
import type { AggregatedItem } from "@/lib/types";

function formatQty(qty: number, unitType: string) {
  return unitType === "discrete" ? String(Math.round(qty)) : qty.toFixed(1);
}

export default function DemandPage() {
  const [items, setItems] = useState<AggregatedItem[]>([]);
  const [statusFilter, setStatusFilter] = useState("confirmed");

  const loadItems = useCallback(async () => {
    try {
      const data = await getAggregatedItems(statusFilter);
      setItems(data);
    } catch (e) {
      console.error("Failed to load aggregated items:", e);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadItems();
    const interval = setInterval(loadItems, 5000);
    return () => clearInterval(interval);
  }, [loadItems]);

  const filters = [
    { value: "confirmed", label: "Confirmed" },
    { value: "pending_confirmation", label: "Pending" },
    { value: "confirmed,pending_confirmation", label: "All Active" },
  ];

  const totalValue = items.reduce((sum, item) => sum + item.total_quantity * (item.total_quantity / item.order_count), 0);

  return (
    <div>
      <h2 className="text-2xl font-bold mb-2">Demand Overview</h2>
      <p className="text-sm mb-6" style={{ color: "var(--color-text-muted)" }}>
        Aggregated product demand across {statusFilter === "confirmed,pending_confirmation" ? "all active" : statusFilter} orders
      </p>

      <div className="flex gap-2 mb-6">
        {filters.map((f) => (
          <button key={f.value} onClick={() => setStatusFilter(f.value)} className="px-3 py-1.5 rounded text-sm font-medium transition-colors cursor-pointer"
            style={{ background: statusFilter === f.value ? "var(--color-accent)" : "var(--color-surface)", color: statusFilter === f.value ? "#fff" : "var(--color-text-muted)", border: `1px solid ${statusFilter === f.value ? "var(--color-accent)" : "var(--color-border)"}` }}>
            {f.label}
          </button>
        ))}
        <span className="ml-auto text-sm self-center" style={{ color: "var(--color-text-muted)" }}>
          {items.length} products across orders
        </span>
      </div>

      <div className="rounded-lg border overflow-hidden" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
        <table className="w-full text-sm">
          <thead>
            <tr style={{ color: "var(--color-text-muted)" }}>
              <th className="text-left text-xs font-medium px-4 py-3">Product</th>
              <th className="text-left text-xs font-medium px-4 py-3">SKU</th>
              <th className="text-left text-xs font-medium px-4 py-3">Category</th>
              <th className="text-right text-xs font-medium px-4 py-3">Total Qty</th>
              <th className="text-left text-xs font-medium px-4 py-3">Unit</th>
              <th className="text-right text-xs font-medium px-4 py-3">Orders</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.product_id} className="border-t" style={{ borderColor: "var(--color-border)" }}>
                <td className="px-4 py-2.5 font-medium">{item.product_name}</td>
                <td className="px-4 py-2.5 font-mono text-xs" style={{ color: "var(--color-text-muted)" }}>{item.sku}</td>
                <td className="px-4 py-2.5 text-xs">
                  <span className="px-2 py-0.5 rounded" style={{ background: "rgba(79,140,255,0.1)", color: "var(--color-accent)" }}>{item.category}</span>
                </td>
                <td className="px-4 py-2.5 text-right font-bold">{formatQty(item.total_quantity, item.unit_type)}</td>
                <td className="px-4 py-2.5">{item.unit}</td>
                <td className="px-4 py-2.5 text-right" style={{ color: "var(--color-text-muted)" }}>{item.order_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && (
          <p className="p-8 text-sm text-center" style={{ color: "var(--color-text-muted)" }}>No items for the selected status filter</p>
        )}
      </div>
    </div>
  );
}
