"use client";

import { useRouter } from "next/navigation";
import { useWatchlist } from "@/lib/hooks";

interface WatchlistSwitcherProps {
  currentTicker: string;
}

export function WatchlistSwitcher({ currentTicker }: WatchlistSwitcherProps) {
  const { data } = useWatchlist();
  const router = useRouter();

  if (!data.stocks.length) return null;

  return (
    <select
      value={currentTicker}
      onChange={(e) => router.push(`/watchlist/${e.target.value}/volume`)}
      className="rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
    >
      {data.stocks.map((s) => (
        <option key={s.ticker} value={s.ticker}>
          {s.ticker} — {s.name}
        </option>
      ))}
    </select>
  );
}
