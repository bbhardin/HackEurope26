"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { getCustomers, getNudgeSuggestions, sendNudge, createCustomer } from "@/lib/api";
import type { Customer, NudgeSuggestion } from "@/lib/types";

type SortOption = "name_asc" | "name_desc" | "health_asc" | "health_desc";
type FilterOption = "all" | "pending" | "confirmed" | "at_risk";
type ViewMode = "tile" | "list";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [nudges, setNudges] = useState<NudgeSuggestion[]>([]);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortOption>("name_asc");
  const [filter, setFilter] = useState<FilterOption>("all");
  const [view, setView] = useState<ViewMode>("tile");
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [newType, setNewType] = useState("restaurant");
  const [newAddress, setNewAddress] = useState("");

  const loadData = () => {
    getCustomers().then(setCustomers).catch(console.error);
    getNudgeSuggestions().then(setNudges).catch(console.error);
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const customerNudge = (customerId: string) => nudges.find((n) => n.customer_id === customerId);

  const handleSendNudge = async (nudgeId: string) => {
    try {
      await sendNudge(nudgeId);
      loadData();
    } catch (e) {
      console.error("Failed to send nudge:", e);
    }
  };

  const filtered = useMemo(() => {
    let result = customers;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter((c) => c.name.toLowerCase().includes(q));
    }
    switch (filter) {
      case "pending": result = result.filter((c) => c.pending_order_count > 0); break;
      case "confirmed": result = result.filter((c) => c.confirmed_order_count > 0); break;
      case "at_risk": result = result.filter((c) => c.health_score < 0.8); break;
    }
    switch (sort) {
      case "name_asc": result = [...result].sort((a, b) => a.name.localeCompare(b.name)); break;
      case "name_desc": result = [...result].sort((a, b) => b.name.localeCompare(a.name)); break;
      case "health_asc": result = [...result].sort((a, b) => a.health_score - b.health_score); break;
      case "health_desc": result = [...result].sort((a, b) => b.health_score - a.health_score); break;
    }
    return result;
  }, [customers, search, sort, filter]);

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

  const severityColor = (severity: string | null) => {
    switch (severity) {
      case "critical": return "var(--color-red)";
      case "warning": return "var(--color-amber)";
      case "info": return "var(--color-green)";
      default: return "var(--color-text-muted)";
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Customer Health</h2>
        <button onClick={() => setShowAdd(!showAdd)} className="px-4 py-2 rounded text-sm font-medium cursor-pointer" style={{ background: "var(--color-accent)", color: "#fff" }}>
          {showAdd ? "Cancel" : "Add Customer"}
        </button>
      </div>

      {showAdd && (
        <div className="rounded-lg border p-4 mb-6" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <input placeholder="Customer name" value={newName} onChange={(e) => setNewName(e.target.value)} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
            <input placeholder="Phone (+49...)" value={newPhone} onChange={(e) => setNewPhone(e.target.value)} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
          </div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <select value={newType} onChange={(e) => setNewType(e.target.value)} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)", color: "var(--color-text)" }}>
              {["restaurant", "hotel", "caterer", "canteen", "small_retail"].map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <input placeholder="Delivery address" value={newAddress} onChange={(e) => setNewAddress(e.target.value)} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }} />
          </div>
          <button onClick={async () => {
            if (!newName || !newPhone) return;
            await createCustomer({ name: newName, phone: newPhone, customer_type: newType, address: newAddress || "Not provided" });
            setNewName(""); setNewPhone(""); setNewAddress(""); setShowAdd(false);
            loadData();
          }} className="px-4 py-2 rounded text-sm font-medium cursor-pointer" style={{ background: "var(--color-green)", color: "#fff" }}>Create Customer</button>
        </div>
      )}

      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <input
          placeholder="Search customers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-2 rounded border text-sm w-64"
          style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }}
        />
        <select value={sort} onChange={(e) => setSort(e.target.value as SortOption)} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)", color: "var(--color-text)" }}>
          <option value="name_asc">Name A–Z</option>
          <option value="name_desc">Name Z–A</option>
          <option value="health_asc">Health: Low first</option>
          <option value="health_desc">Health: High first</option>
        </select>
        <select value={filter} onChange={(e) => setFilter(e.target.value as FilterOption)} className="px-3 py-2 rounded border text-sm" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)", color: "var(--color-text)" }}>
          <option value="all">All</option>
          <option value="pending">Has pending orders</option>
          <option value="confirmed">Has confirmed orders</option>
          <option value="at_risk">At risk</option>
        </select>
        <div className="flex gap-1 ml-auto">
          <button onClick={() => setView("tile")} className="px-2 py-1.5 rounded text-sm cursor-pointer" style={{ background: view === "tile" ? "var(--color-accent)" : "var(--color-surface)", color: view === "tile" ? "#fff" : "var(--color-text-muted)", border: `1px solid ${view === "tile" ? "var(--color-accent)" : "var(--color-border)"}` }}>▦</button>
          <button onClick={() => setView("list")} className="px-2 py-1.5 rounded text-sm cursor-pointer" style={{ background: view === "list" ? "var(--color-accent)" : "var(--color-surface)", color: view === "list" ? "#fff" : "var(--color-text-muted)", border: `1px solid ${view === "list" ? "var(--color-accent)" : "var(--color-border)"}` }}>☰</button>
        </div>
      </div>

      {view === "tile" ? (
        <div className="grid grid-cols-3 gap-4">
          {filtered.map((customer) => {
            const nudge = customerNudge(customer.id);
            return (
              <div key={customer.id} className="rounded-lg border p-4 transition-colors" style={{ background: "var(--color-surface)", borderColor: nudge ? "var(--color-amber)" : "var(--color-border)" }}>
                <Link href={`/customers/${customer.id}`} className="block">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="font-semibold text-sm">{customer.name}</p>
                      <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>{customer.type}</p>
                    </div>
                    <span className="text-xs font-semibold px-2 py-0.5 rounded" style={{ background: `${healthColor(customer.health_score)}20`, color: healthColor(customer.health_score) }}>
                      {healthLabel(customer.health_score)}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 mb-2">
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
                  {customer.latest_health_event && (
                    <p className="text-xs mt-1" style={{ color: severityColor(customer.latest_health_severity) }}>
                      {customer.latest_health_event.slice(0, 60)}
                      {customer.latest_health_date && (
                        <span style={{ color: "var(--color-text-muted)" }}> · {customer.latest_health_date.slice(0, 10)}</span>
                      )}
                    </p>
                  )}
                  <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>{customer.delivery_address}</p>
                </Link>
                {nudge && (
                  <div className="mt-3 pt-3 border-t" style={{ borderColor: "var(--color-border)" }}>
                    <p className="text-xs font-medium mb-1" style={{ color: "var(--color-amber)" }}>Nudge: {nudge.reason}</p>
                    <button onClick={() => handleSendNudge(nudge.id)} className="px-3 py-1.5 rounded text-xs font-medium cursor-pointer" style={{ background: "var(--color-amber)", color: "#fff" }}>Send Nudge</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ color: "var(--color-text-muted)" }}>
                <th className="text-left text-xs font-medium px-4 py-3">Name</th>
                <th className="text-left text-xs font-medium px-4 py-3">Type</th>
                <th className="text-right text-xs font-medium px-4 py-3">Health</th>
                <th className="text-left text-xs font-medium px-4 py-3">Phone</th>
                <th className="text-right text-xs font-medium px-4 py-3">Pending</th>
                <th className="text-left text-xs font-medium px-4 py-3">Latest Event</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((customer) => (
                <tr key={customer.id} className="border-t" style={{ borderColor: "var(--color-border)" }}>
                  <td className="px-4 py-2.5">
                    <Link href={`/customers/${customer.id}`} style={{ color: "var(--color-accent)" }} className="font-medium">{customer.name}</Link>
                  </td>
                  <td className="px-4 py-2.5 text-xs" style={{ color: "var(--color-text-muted)" }}>{customer.type}</td>
                  <td className="px-4 py-2.5 text-right font-bold" style={{ color: healthColor(customer.health_score) }}>
                    {(customer.health_score * 100).toFixed(0)}%
                  </td>
                  <td className="px-4 py-2.5 text-xs font-mono">{customer.contact_phone}</td>
                  <td className="px-4 py-2.5 text-right">{customer.pending_order_count > 0 ? customer.pending_order_count : "—"}</td>
                  <td className="px-4 py-2.5 text-xs" style={{ color: severityColor(customer.latest_health_severity) }}>
                    {customer.latest_health_event ? customer.latest_health_event.slice(0, 50) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {filtered.length === 0 && (
        <div className="rounded-lg border p-8 text-center" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
          <p style={{ color: "var(--color-text-muted)" }}>No customers match your filters</p>
        </div>
      )}
    </div>
  );
}
