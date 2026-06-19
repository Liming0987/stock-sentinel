"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useWatchlist, useSignals } from "@/lib/hooks";

const NAV_SECTIONS = [
  {
    label: "Overview",
    items: [{ href: "/", label: "Dashboard" }],
  },
  {
    label: "Markets",
    items: [
      { href: "/watchlist", label: "Watchlist", badgeKey: "watchlist" },
      { href: "/signals", label: "Signals", badgeKey: "signals" },
      { href: "/trending", label: "Trending" },
    ],
  },
  {
    label: "Research",
    items: [
      { href: "/strategies", label: "Strategies" },
      { href: "/strategy-signals", label: "Signal Log" },
      { href: "/backtest", label: "Backtest" },
      { href: "/reports", label: "Reports" },
      { href: "/youtube-digest", label: "YouTube Digest" },
    ],
  },
  {
    label: "Grow",
    items: [
      { href: "/learn", label: "Learn" },
      { href: "/settings", label: "Settings" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { data: watchlistData } = useWatchlist();
  const { data: signalsData } = useSignals();

  const badges: Record<string, string> = {
    watchlist: watchlistData.stocks.length > 0 ? String(watchlistData.stocks.length) : "",
    signals: signalsData.signals.length > 0 ? String(signalsData.signals.length) : "",
  };

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/");

  return (
    <>
      {/* Mobile hamburger */}
      <button
        onClick={() => setOpen(true)}
        className="fixed left-4 top-4 z-50 flex h-10 w-10 items-center justify-center rounded-xl border bg-card shadow-sm lg:hidden"
        aria-label="Open menu"
      >
        <Menu className="h-4 w-4" />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-40 bg-background/70 backdrop-blur-sm lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        style={{ background: "var(--sentinel-sidebar)", width: 248 }}
        className={cn(
          "fixed left-0 top-0 z-50 flex h-screen flex-col border-r transition-transform duration-200",
          "lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between border-b px-6 py-[26px]">
          <div className="flex items-center gap-2.5">
            <span
              className="h-[11px] w-[11px] rounded-full bg-primary"
              style={{ boxShadow: "0 0 0 4px var(--sentinel-accent-soft)" }}
            />
            <span className="font-serif text-[23px] font-semibold tracking-tight leading-none">
              Sentinel
            </span>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="flex h-7 w-7 items-center justify-center rounded-lg hover:bg-accent lg:hidden"
            aria-label="Close menu"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="px-6 pt-2 pb-0 text-[11.5px] text-muted-foreground tracking-wide">
          Social-signal market monitor
        </p>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3.5 py-[18px] space-y-5">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label}>
              <p className="mb-1.5 px-2.5 text-[10px] font-semibold uppercase tracking-[0.13em] text-muted-foreground/60">
                {section.label}
              </p>
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const active = isActive(item.href);
                  const badge = item.badgeKey ? badges[item.badgeKey] : "";
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setOpen(false)}
                      className={cn(
                        "flex items-center gap-2.5 rounded-[9px] px-2.5 py-[9px] text-[13.5px] transition-colors",
                        active
                          ? "bg-[var(--sentinel-accent-soft)] text-primary font-semibold"
                          : "text-muted-foreground font-medium hover:bg-accent hover:text-foreground"
                      )}
                    >
                      <span
                        className="h-4 w-1 rounded-full flex-shrink-0 transition-colors"
                        style={{ background: active ? "var(--primary)" : "transparent" }}
                      />
                      <span className="flex-1">{item.label}</span>
                      {badge && (
                        <span className="font-mono text-[10.5px] font-medium px-1.5 py-0.5 rounded-full bg-[var(--sentinel-accent-soft)] text-primary">
                          {badge}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t px-[22px] py-4">
          <p className="text-[10.5px] leading-relaxed text-muted-foreground">
            Educational use only. Not financial advice.
          </p>
        </div>
      </aside>
    </>
  );
}
