"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Moon, Sun, TrendingUp, DollarSign, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNotifications } from "@/lib/hooks";
import type { AppNotification } from "@/lib/hooks";

function notifIcon(type: AppNotification["type"]) {
  if (type === "signal") return <TrendingUp className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" />;
  if (type === "trade_open") return <DollarSign className="h-3.5 w-3.5 text-bullish shrink-0 mt-0.5" />;
  return <DollarSign className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />;
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function isMarketOpen() {
  const now = new Date();
  const et = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
  const h = et.getHours(), m = et.getMinutes(), day = et.getDay();
  const mins = h * 60 + m;
  return day >= 1 && day <= 5 && mins >= 570 && mins < 960;
}

export function Header() {
  const [query, setQuery] = useState("");
  const [darkMode, setDarkMode] = useState(true);
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { notifications, unreadCount, markAllRead } = useNotifications();
  const marketOpen = isMarketOpen();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/stock/${query.trim().toUpperCase()}`);
      setQuery("");
    }
  };

  const toggleTheme = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle("dark");
  };

  const toggleDropdown = () => {
    if (!open) markAllRead();
    setOpen((v) => !v);
  };

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <header className="sticky top-0 z-30 flex h-[68px] items-center gap-4 border-b bg-background px-8 pl-16 lg:pl-8">
      {/* Search */}
      <form onSubmit={handleSearch} className="relative w-full max-w-[380px]">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-[13px]">⌕</span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search a ticker — NVDA, GME, SOFI…"
          className="h-[38px] w-full rounded-[9px] border bg-card pl-8 pr-4 text-[13px] outline-none focus:ring-2 ring-primary/30"
        />
      </form>

      <div className="flex-1" />

      {/* Market status pill */}
      <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 border rounded-[20px] bg-card">
        <span
          className="h-[7px] w-[7px] rounded-full"
          style={{
            background: marketOpen ? "var(--sentinel-up)" : "var(--sentinel-down)",
            boxShadow: marketOpen ? "0 0 8px var(--sentinel-up)" : "none",
          }}
        />
        <span className="text-[12px] font-medium text-muted-foreground">
          {marketOpen ? "Market open" : "Market closed"}
        </span>
      </div>

      {/* Notifications */}
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={toggleDropdown}
          className="relative flex h-[38px] w-[38px] items-center justify-center rounded-[9px] border bg-card text-muted-foreground hover:text-foreground transition-colors"
        >
          <span className="text-[15px]">🔔</span>
          {unreadCount > 0 && (
            <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold"
              style={{ color: "var(--sentinel-accent-ink)" }}>
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </button>

        {open && (
          <div className="absolute right-0 top-12 z-50 w-80 rounded-xl border bg-card shadow-xl">
            <div className="flex items-center justify-between border-b px-4 py-2.5">
              <span className="text-sm font-semibold">Notifications</span>
              <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-96 overflow-y-auto divide-y">
              {notifications.length === 0 ? (
                <p className="px-4 py-6 text-center text-sm text-muted-foreground">No recent activity</p>
              ) : (
                notifications.map((n) => (
                  <div key={n.id} className="flex gap-2.5 px-4 py-3 hover:bg-accent/40 transition-colors">
                    {notifIcon(n.type)}
                    <div className="min-w-0">
                      <p className="text-xs leading-snug">{n.message}</p>
                      <p className="mt-0.5 text-[10px] text-muted-foreground">{timeAgo(n.timestamp)}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        className="flex h-[38px] w-[38px] items-center justify-center rounded-[9px] border bg-card text-foreground hover:bg-accent transition-colors"
        title="Toggle theme"
      >
        {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>

      {/* Avatar */}
      <div
        className="flex h-[38px] w-[38px] items-center justify-center rounded-full border font-serif text-[15px] font-semibold text-primary"
        style={{ background: "var(--sentinel-accent-soft)" }}
      >
        A
      </div>
    </header>
  );
}
