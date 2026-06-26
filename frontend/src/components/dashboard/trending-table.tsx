"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  TrendingUp, ArrowUpRight, ArrowDownRight,
  ChevronUp, ChevronDown, ChevronsUpDown, Search,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SentimentGauge } from "./sentiment-gauge";
import { formatNumber, formatPrice, formatPercent } from "@/lib/utils";
import type { TrendingStock } from "@/lib/mock-data";

type SortKey =
  | "ticker"
  | "price"
  | "change_pct"
  | "mention_count"
  | "mention_velocity"
  | "sentiment_score"
  | "volume_ratio"
  | "trend_score";

type SortDir = "asc" | "desc";

interface TrendingTableProps {
  stocks: TrendingStock[];
  compact?: boolean;
}

interface SortHeaderProps {
  label: string;
  col: SortKey;
  active: SortKey;
  dir: SortDir;
  onSort: (k: SortKey) => void;
}

function SortHeader({ label, col, active, dir, onSort }: SortHeaderProps) {
  const isActive = active === col;
  return (
    <th className="pb-3 font-medium">
      <button
        onClick={() => onSort(col)}
        className={`flex items-center gap-1 hover:text-foreground transition-colors select-none whitespace-nowrap ${
          isActive ? "text-foreground" : ""
        }`}
      >
        {label}
        {isActive ? (
          dir === "asc" ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )
        ) : (
          <ChevronsUpDown className="h-3 w-3 opacity-40" />
        )}
      </button>
    </th>
  );
}

export function TrendingTable({ stocks, compact = false }: TrendingTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("trend_score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [query, setQuery] = useState("");

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const displayed = useMemo(() => {
    if (compact) return stocks.slice(0, 5);

    let list = stocks;

    if (query.trim()) {
      const q = query.trim().toLowerCase();
      list = list.filter(
        (s) =>
          s.ticker.toLowerCase().includes(q) ||
          (s.name ?? "").toLowerCase().includes(q)
      );
    }

    return [...list].sort((a, b) => {
      const av = a[sortKey as keyof TrendingStock];
      const bv = b[sortKey as keyof TrendingStock];
      if (typeof av === "string" && typeof bv === "string") {
        return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      const an = Number(av ?? 0);
      const bn = Number(bv ?? 0);
      return sortDir === "asc" ? an - bn : bn - an;
    });
  }, [stocks, compact, query, sortKey, sortDir]);

  const sortProps = { active: sortKey, dir: sortDir, onSort: handleSort };

  return (
    <Card className="h-full flex flex-col overflow-hidden">
      <CardHeader className="flex flex-col gap-2 shrink-0 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle className="flex items-center gap-2 shrink-0">
          <TrendingUp className="h-5 w-5 text-primary" />
          Trending Stocks
        </CardTitle>
        {compact ? (
          <Link href="/trending" className="text-sm text-primary hover:underline">
            View all
          </Link>
        ) : (
          <div className="relative max-w-xs w-full">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter by ticker or name…"
              className="w-full rounded-md border border-input bg-background pl-8 pr-3 py-1.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
        )}
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto min-h-0 pt-0">
        <div className="overflow-x-auto">
          <table className="w-full text-xs sm:text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-3 pr-3 font-medium w-8">#</th>
                {compact ? (
                  <>
                    <th className="pb-3 font-medium">Ticker</th>
                    <th className="pb-3 font-medium">Price</th>
                    <th className="pb-3 font-medium">Change</th>
                    <th className="pb-3 font-medium">Mentions</th>
                    <th className="pb-3 font-medium">Sentiment</th>
                    <th className="pb-3 font-medium">Score</th>
                  </>
                ) : (
                  <>
                    <SortHeader label="Ticker" col="ticker" {...sortProps} />
                    <SortHeader label="Price" col="price" {...sortProps} />
                    <SortHeader label="Change" col="change_pct" {...sortProps} />
                    <SortHeader label="Mentions" col="mention_count" {...sortProps} />
                    <SortHeader label="Velocity" col="mention_velocity" {...sortProps} />
                    <SortHeader label="Sentiment" col="sentiment_score" {...sortProps} />
                    <SortHeader label="Vol Ratio" col="volume_ratio" {...sortProps} />
                    <th className="pb-3 font-medium">Sources</th>
                    <SortHeader label="Score" col="trend_score" {...sortProps} />
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {displayed.length === 0 ? (
                <tr>
                  <td
                    colSpan={compact ? 7 : 10}
                    className="py-10 text-center text-sm text-muted-foreground"
                  >
                    {stocks.length === 0
                      ? "No trending stocks yet — scrapers will populate this once they run."
                      : `No stocks match “${query}”`}
                  </td>
                </tr>
              ) : (
                displayed.map((stock, i) => (
                  <tr
                    key={stock.ticker}
                    className="border-b last:border-0 hover:bg-accent/50 transition-colors"
                  >
                    <td className="py-3 pr-3 text-muted-foreground">{i + 1}</td>
                    <td className="py-3 pr-3">
                      <Link href={`/watchlist/${stock.ticker}/analysis`} className="group">
                        <span className="font-semibold text-foreground group-hover:text-primary transition-colors">
                          {stock.ticker}
                        </span>
                        {!compact && (
                          <span className="ml-2 text-xs text-muted-foreground">
                            {stock.name}
                          </span>
                        )}
                      </Link>
                    </td>
                    <td className="py-3 pr-3 font-mono">{formatPrice(stock.price)}</td>
                    <td className="py-3 pr-3">
                      <span
                        className={`inline-flex items-center gap-0.5 font-mono ${
                          stock.change_pct >= 0 ? "text-bullish" : "text-bearish"
                        }`}
                      >
                        {stock.change_pct >= 0 ? (
                          <ArrowUpRight className="h-3 w-3" />
                        ) : (
                          <ArrowDownRight className="h-3 w-3" />
                        )}
                        {formatPercent(stock.change_pct)}
                      </span>
                    </td>
                    <td className="py-3 pr-3 font-mono">{formatNumber(stock.mention_count)}</td>
                    {!compact && (
                      <td className="py-3 pr-3 font-mono text-muted-foreground">
                        {stock.mention_velocity.toFixed(1)}/hr
                      </td>
                    )}
                    <td className="py-3 pr-3">
                      <SentimentGauge score={stock.sentiment_score} size="sm" />
                    </td>
                    {!compact && (
                      <td className="py-3 pr-3 font-mono">
                        <span
                          className={
                            stock.volume_ratio >= 1.5
                              ? "text-bullish font-semibold"
                              : "text-muted-foreground"
                          }
                        >
                          {stock.volume_ratio.toFixed(1)}x
                        </span>
                      </td>
                    )}
                    {!compact && (
                      <td className="py-3 pr-3">
                        <div className="flex gap-1">
                          {stock.sources.map((s) => (
                            <Badge key={s} variant="secondary" className="text-[10px]">
                              {s}
                            </Badge>
                          ))}
                        </div>
                      </td>
                    )}
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-16 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-primary transition-all"
                            style={{ width: `${stock.trend_score * 100}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono">
                          {(stock.trend_score * 100).toFixed(0)}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
