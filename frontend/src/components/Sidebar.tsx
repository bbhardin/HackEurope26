"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: "◈" },
  { href: "/orders", label: "Order Queue", icon: "☰" },
  { href: "/demand", label: "Demand Overview", icon: "▤" },
  { href: "/customers", label: "Customers", icon: "◉" },
  { href: "/catalog", label: "Product Catalog", icon: "▦" },
  { href: "/alerts", label: "Alerts", icon: "△" },
  { href: "/activity", label: "Activity Log", icon: "◇" },
];

export function Sidebar() {
  const pathname = usePathname();
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const saved = localStorage.getItem("theme") as "dark" | "light" | null;
    if (saved) {
      setTheme(saved);
      document.documentElement.dataset.theme = saved === "light" ? "light" : "";
    }
  }, []);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next === "light" ? "light" : "";
    localStorage.setItem("theme", next);
  };

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 flex flex-col border-r"
      style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
      <div className="p-6 border-b" style={{ borderColor: "var(--color-border)" }}>
        <h1 className="text-lg font-bold tracking-tight" style={{ color: "var(--color-accent)" }}>
          ◆ Wholesaler AI
        </h1>
        <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>
          Order Management Dashboard
        </p>
      </div>

      <nav className="flex-1 py-4">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-6 py-3 text-sm font-medium transition-colors"
              style={{
                color: isActive ? "var(--color-accent)" : "var(--color-text-muted)",
                background: isActive ? "rgba(79, 140, 255, 0.08)" : "transparent",
                borderRight: isActive ? "2px solid var(--color-accent)" : "2px solid transparent",
              }}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-6 border-t" style={{ borderColor: "var(--color-border)" }}>
        <button
          onClick={toggleTheme}
          className="flex items-center gap-2 text-xs cursor-pointer mb-3"
          style={{ color: "var(--color-text-muted)" }}
        >
          <span>{theme === "dark" ? "☀" : "☽"}</span>
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </button>
        <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
          Rheinfood Demo
        </p>
      </div>
    </aside>
  );
}
