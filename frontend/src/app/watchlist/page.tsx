"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/layout/page-header";
import {
  Star, ArrowUpRight, ArrowDownRight,
  Trash2, Plus, Search, ChevronUp, ChevronDown,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SentimentGauge } from "@/components/dashboard/sentiment-gauge";
import { formatPrice, formatPercent } from "@/lib/utils";
import { useWatchlist } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { WatchlistItem } from "@/lib/mock-data";

type SortKey = "ticker" | "price" | "change_pct" | "sentiment_score";
type SortDir = "asc" | "desc";

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "ticker", label: "Ticker" },
  { key: "price", label: "Price" },
  { key: "change_pct", label: "Change" },
  { key: "sentiment_score", label: "Sentiment" },
];

const DEFAULT_DIR: Record<SortKey, SortDir> = {
  ticker: "asc",
  price: "desc",
  change_pct: "desc",
  sentiment_score: "desc",
};

function WatchlistCard({
  stock,
  onRemove,
}: {
  stock: WatchlistItem;
  onRemove: (ticker: string) => void;
}) {
  return (
    <Card className="relative overflow-hidden group">
      {stock.has_active_signal && (
        <div className="absolute right-3 top-3 z-10">
          <Badge variant="bullish" className="text-[10px]">SIGNAL</Badge>
        </div>
      )}

      <Link href={`/watchlist/${stock.ticker}/analysis`} className="block">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 group-hover:text-primary transition-colors">
            {stock.ticker}
            <span className="text-sm font-normal text-muted-foreground">{stock.name}</span>
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-3">
          {/* Price + change */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-2xl font-bold font-mono">{formatPrice(stock.price)}</p>
              <p className={`flex items-center gap-0.5 text-sm font-mono ${
                stock.change_pct >= 0 ? "text-bullish" : "text-bearish"
              }`}>
                {stock.change_pct >= 0
                  ? <ArrowUpRight className="h-3 w-3" />
                  : <ArrowDownRight className="h-3 w-3" />}
                {formatPercent(stock.change_pct)}
              </p>
            </div>
            <SentimentGauge score={stock.sentiment_score} size="sm" />
          </div>
        </CardContent>
      </Link>

      {/* Remove button sits outside the Link to avoid nested interaction */}
      <div className="px-6 pb-4">
        <Button
          variant="ghost"
          size="sm"
          className="text-xs text-muted-foreground hover:text-bearish w-full"
          onClick={() => onRemove(stock.ticker)}
        >
          <Trash2 className="mr-1 h-3 w-3" />
          Remove
        </Button>
      </div>
    </Card>
  );
}

export default function WatchlistPage() {
  const { data, refetch } = useWatchlist();

  const [adding, setAdding] = useState(false);
  const [tickerInput, setTickerInput] = useState("");
  const [addError, setAddError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("ticker");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const handleSortClick = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(DEFAULT_DIR[key]);
    }
  };

  const displayed = useMemo(() => {
    let list: WatchlistItem[] = data.stocks;

    if (query.trim()) {
      const q = query.trim().toLowerCase();
      list = list.filter(
        (s) =>
          s.ticker.toLowerCase().includes(q) ||
          (s.name ?? "").toLowerCase().includes(q)
      );
    }

    return [...list].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === "string" && typeof bv === "string") {
        return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      const an = Number(av ?? 0);
      const bn = Number(bv ?? 0);
      return sortDir === "asc" ? an - bn : bn - an;
    });
  }, [data.stocks, query, sortKey, sortDir]);

  const handleAdd = async () => {
    const ticker = tickerInput.trim().toUpperCase();
    if (!ticker) return;
    setAddError(null);
    try {
      const res = await api.watchlist.add(ticker);
      if (!res.ok) {
        const body = await res.json();
        setAddError(body.detail || "Failed to add ticker");
        return;
      }
      setTickerInput("");
      setAdding(false);
      refetch();
    } catch {
      setAddError("Network error — is the backend running?");
    }
  };

  const handleRemove = async (ticker: string) => {
    await api.watchlist.remove(ticker);
    refetch();
  };

  return (
    <div className="mx-auto max-w-[1180px] space-y-[18px]">
      <div className="flex items-end justify-between gap-4">
        <PageHeader
          kicker="Markets"
          title="Watchlist"
          description="Sentiment blends Reddit, StockTwits & news mentions into a single −1 to +1 mood reading."
        />
        <Button size="sm" onClick={() => { setAdding(true); setAddError(null); }}>
          <Star className="mr-2 h-4 w-4" />
          Add Ticker
        </Button>
      </div>

      {/* Add ticker form */}
      {adding && (
        <Card>
          <CardContent className="flex items-center gap-3 pt-4">
            <input
              autoFocus
              className="flex-1 rounded-md border bg-background px-3 py-2 text-sm uppercase placeholder:normal-case placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="e.g. NVDA"
              value={tickerInput}
              onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleAdd();
                if (e.key === "Escape") setAdding(false);
              }}
            />
            <Button size="sm" onClick={handleAdd}>
              <Plus className="mr-1 h-4 w-4" /> Add
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setAdding(false)}>
              Cancel
            </Button>
            {addError && <p className="text-xs text-destructive">{addError}</p>}
          </CardContent>
        </Card>
      )}

      {/* Filter + sort controls — only shown when there are stocks */}
      {data.stocks.length > 0 && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          {/* Filter input */}
          <div className="relative max-w-xs w-full">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter by ticker or name…"
              className="w-full rounded-md border border-input bg-background pl-8 pr-3 py-1.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>

          {/* Sort picker */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-muted-foreground shrink-0">Sort by</span>
            <div className="flex flex-wrap gap-1 rounded-lg border p-0.5">
              {SORT_OPTIONS.map(({ key, label }) => {
                const active = sortKey === key;
                return (
                  <button
                    key={key}
                    onClick={() => handleSortClick(key)}
                    className={`flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                      active
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    }`}
                  >
                    {label}
                    {active && (
                      sortDir === "asc"
                        ? <ChevronUp className="h-3 w-3" />
                        : <ChevronDown className="h-3 w-3" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Empty watchlist */}
      {data.stocks.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Star className="mb-4 h-12 w-12 text-muted-foreground/50" />
            <p className="text-lg font-medium">Your watchlist is empty</p>
            <p className="text-sm text-muted-foreground">
              Click &ldquo;Add Ticker&rdquo; to start tracking stocks
            </p>
          </CardContent>
        </Card>
      ) : displayed.length === 0 ? (
        /* No results after filtering */
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-10">
            <p className="text-sm text-muted-foreground">
              No stocks match &ldquo;{query}&rdquo;
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {displayed.map((stock) => (
            <WatchlistCard key={stock.ticker} stock={stock} onRemove={handleRemove} />
          ))}
        </div>
      )}
    </div>
  );
}
