"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getCustomers } from "@/lib/api";
import type { Customer } from "@/lib/types";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);

  useEffect(() => {
    getCustomers().then(setCustomers).catch(console.error);
  }, []);

  const healthColor = (score: number) => {
    if (score >= 0.9) return "var(--color-green)";
    if (score >= 0.8) return "var(--color-amber)";
    return "var(--color-red)";
  };

  const healthLabel = (score: number) => {
    if (score >= 0.9) return "Healthy";
    if (score >= 0.8) return "Watch";
    return "At Risk";
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Customer Health</h2>

      <div className="grid grid-cols-3 gap-4">
        {customers.map((customer) => (
          <Link
            key={customer.id}
            href={`/customers/${customer.id}`}
            className="rounded-lg border p-4 transition-colors block"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="font-semibold text-sm">{customer.name}</p>
                <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>{customer.type}</p>
              </div>
              <span
                className="text-xs font-semibold px-2 py-0.5 rounded"
                style={{
                  background: `${healthColor(customer.health_score)}20`,
                  color: healthColor(customer.health_score),
                }}
              >
                {healthLabel(customer.health_score)}
              </span>
            </div>

            <div className="flex items-center gap-4">
              <div>
                <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>Health Score</p>
                <p className="text-lg font-bold" style={{ color: healthColor(customer.health_score) }}>
                  {(customer.health_score * 100).toFixed(0)}%
                </p>
              </div>
              <div>
                <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>Phone</p>
                <p className="text-xs font-mono">{customer.contact_phone}</p>
              </div>
            </div>

            <p className="text-xs mt-2" style={{ color: "var(--color-text-muted)" }}>
              {customer.delivery_address}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
