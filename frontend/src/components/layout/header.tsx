"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, Bell, Moon, Sun, TrendingUp, DollarSign, X } from "lucide-react";
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

export function Header() {
  const [query, setQuery] = useState("");
  const [darkMode, setDarkMode] = useState(true);
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { notifications, unreadCount, markAllRead } = useNotifications();

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

  // Close on outside click
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
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-card/80 px-4 pl-16 backdrop-blur-sm lg:px-6 lg:pl-6">
      <form onSubmit={handleSearch} className="relative w-full max-w-[180px] sm:max-w-sm lg:max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search ticker..."
          className="h-10 w-full rounded-md border bg-background pl-10 pr-4 text-sm outline-none ring-ring focus:ring-2"
        />
      </form>

      <div className="flex items-center gap-2 ml-2">
        {/* Bell with dropdown */}
        <div className="relative" ref={dropdownRef}>
          <Button variant="ghost" size="icon" className="relative" onClick={toggleDropdown}>
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] text-primary-foreground font-bold">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </Button>

          {open && (
            <div className="absolute right-0 top-10 z-50 w-80 max-w-[calc(100vw-1rem)] rounded-lg border bg-card shadow-xl">
              {/* Header */}
              <div className="flex items-center justify-between border-b px-4 py-2.5">
                <span className="text-sm font-semibold">Notifications</span>
                <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground">
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* List */}
              <div className="max-h-96 overflow-y-auto divide-y">
                {notifications.length === 0 ? (
                  <p className="px-4 py-6 text-center text-sm text-muted-foreground">
                    No recent activity
                  </p>
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

        <Button variant="ghost" size="icon" onClick={toggleTheme}>
          {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  );
}
