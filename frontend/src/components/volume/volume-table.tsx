"use client";

import { useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { VolumeHistoryPoint } from "@/lib/hooks";

type SortKey = "date" | "close" | "high" | "low" | "volume" | "vol_ratio" | "price_change_pct";
type SortDir = "asc" | "desc";
type Filter = "all" | "spikes" | "notable";

// ── Wyckoff event metadata ────────────────────────────────────────────────────

const WY_ACC = new Set(["SC", "AR", "ST", "SOS", "LPS"]);
const WY_LABEL: Record<string, string> = {
  SC: "Selling Climax", AR: "Auto Rally", ST: "Secondary Test",
  SOS: "Sign of Strength", LPS: "Last Point of Support",
  BC: "Buying Climax", AR2: "Auto Reaction", UT: "Upthrust",
  SOW: "Sign of Weakness", LPSY: "Last Point of Supply",
};

function WyckoffTag({ label }: { label: string }) {
  const isAcc = WY_ACC.has(label);
  return (
    <span
      title={WY_LABEL[label] ?? label}
      className={`inline-block rounded px-1 py-0 text-[9px] font-bold leading-4 ${
        isAcc
          ? "bg-bullish/20 text-bullish border border-bullish/30"
          : "bg-bearish/20 text-bearish border border-bearish/30"
      }`}
    >
      {label}
    </span>
  );
}

// ── Candle glyph ──────────────────────────────────────────────────────────────

function CandleGlyph({ open, close, high, low }: { open: number; close: number; high: number; low: number }) {
  const range = high - low;
  const bullish = close >= open;
  const doji = range > 0 && Math.abs(close - open) / range < 0.1;

  if (doji) {
    return <span className="text-muted-foreground text-xs font-bold">—</span>;
  }
  // Hammer: small body in upper 30%, long lower wick
  const bodyTop = Math.max(open, close);
  const bodyBot = Math.min(open, close);
  const lowerWick = bodyBot - low;
  const upperWick = high - bodyTop;
  const bodySize = bodyTop - bodyBot;
  const hammer = range > 0 && lowerWick > bodySize * 2 && upperWick < bodySize;
  const shootingStar = range > 0 && upperWick > bodySize * 2 && lowerWick < bodySize;

  if (hammer)      return <span className="text-bullish text-xs" title="Hammer">🔨</span>;
  if (shootingStar) return <span className="text-bearish text-xs" title="Shooting Star">⭐</span>;
  return bullish
    ? <span className="text-bullish font-bold text-xs">▲</span>
    : <span className="text-bearish font-bold text-xs">▼</span>;
}

// ── Formatters ────────────────────────────────────────────────────────────────

function fmtVol(v: number | null): string {
  if (v == null) return "—";
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
  return `${v}`;
}

function volRatioColor(r: number | null): string {
  if (r == null) return "text-muted-foreground";
  if (r >= 2.5) return "text-red-400 font-bold";
  if (r >= 1.5) return "text-amber-400 font-semibold";
  return "text-slate-400";
}

function rowBg(row: VolumeHistoryPoint): string {
  if (row.wyckoff_events?.length) {
    const hasAcc = row.wyckoff_events.some(e => WY_ACC.has(e));
    const hasDist = row.wyckoff_events.some(e => !WY_ACC.has(e));
    if (hasAcc && hasDist) return "bg-yellow-900/20";
    if (hasAcc)  return "bg-bullish/10";
    if (hasDist) return "bg-bearish/10";
  }
  if (row.is_spike) return "bg-amber-950/20";
  return "";
}

// ── Main component ────────────────────────────────────────────────────────────

interface VolumeTableProps {
  data: VolumeHistoryPoint[];
}

const FILTER_LABELS: Record<Filter, string> = {
  all:     "All",
  spikes:  "Spikes ≥1.5×",
  notable: "Notable (spike or ≥2%)",
};

export function VolumeTable({ data }: VolumeTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [showAll, setShowAll] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const filtered = data.filter(row => {
    if (filter === "spikes")  return (row.vol_ratio ?? 0) >= 1.5;
    if (filter === "notable") return (row.vol_ratio ?? 0) >= 1.5 || Math.abs(row.price_change_pct ?? 0) >= 2;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = typeof av === "string" ? av.localeCompare(bv as string) : (av as number) - (bv as number);
    return sortDir === "asc" ? cmp : -cmp;
  });

  const displayed = showAll ? sorted : sorted.slice(0, 30);

  const SortIcon = ({ col }: { col: SortKey }) =>
    sortKey === col
      ? sortDir === "asc" ? <ChevronUp className="inline h-3 w-3" /> : <ChevronDown className="inline h-3 w-3" />
      : null;

  const th = (label: string, col: SortKey, cls = "") => (
    <th
      className={`cursor-pointer select-none whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:text-foreground ${cls}`}
      onClick={() => handleSort(col)}
    >
      {label} <SortIcon col={col} />
    </th>
  );

  return (
    <div className="space-y-3">
      {/* Filter pills */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">{filtered.length} rows</span>
        <div className="flex gap-1.5 ml-auto">
          {(["all", "spikes", "notable"] as Filter[]).map(f => (
            <button
              key={f}
              onClick={() => { setFilter(f); setShowAll(false); }}
              className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-colors ${
                filter === f
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-accent"
              }`}
            >
              {FILTER_LABELS[f]}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/30">
              {th("Date", "date")}
              <th className="px-2 py-2 text-xs font-medium text-muted-foreground w-6" />
              {th("High", "high", "hidden sm:table-cell")}
              {th("Low", "low", "hidden sm:table-cell")}
              {th("Close", "close")}
              <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground hidden sm:table-cell">
                Range%
              </th>
              {th("Volume", "volume")}
              {th("Vol ×", "vol_ratio")}
              {th("Chg%", "price_change_pct")}
              <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">
                Wyckoff
              </th>
            </tr>
          </thead>
          <tbody>
            {displayed.map((row, i) => {
              const rangePct = row.high != null && row.low != null && row.close != null && row.close > 0
                ? ((row.high - row.low) / row.close * 100)
                : null;
              return (
                <tr
                  key={i}
                  className={`border-b border-border/50 transition-colors hover:bg-muted/30 ${rowBg(row)}`}
                >
                  <td className="px-3 py-1.5 font-mono text-xs whitespace-nowrap">{row.date}</td>

                  {/* Candle glyph */}
                  <td className="px-2 py-1.5 text-center">
                    {row.open != null && row.close != null && row.high != null && row.low != null && (
                      <CandleGlyph open={row.open} close={row.close} high={row.high} low={row.low} />
                    )}
                  </td>

                  {/* High */}
                  <td className="px-3 py-1.5 font-mono text-xs text-muted-foreground hidden sm:table-cell">
                    {row.high != null ? `$${row.high.toFixed(2)}` : "—"}
                  </td>

                  {/* Low */}
                  <td className="px-3 py-1.5 font-mono text-xs text-muted-foreground hidden sm:table-cell">
                    {row.low != null ? `$${row.low.toFixed(2)}` : "—"}
                  </td>

                  {/* Close */}
                  <td className="px-3 py-1.5 font-mono font-medium">
                    {row.close != null ? `$${row.close.toFixed(2)}` : "—"}
                  </td>

                  {/* Range% */}
                  <td className="px-3 py-1.5 font-mono text-xs text-muted-foreground hidden sm:table-cell">
                    {rangePct != null ? `${rangePct.toFixed(1)}%` : "—"}
                  </td>

                  {/* Volume */}
                  <td className="px-3 py-1.5 font-mono text-xs">{fmtVol(row.volume)}</td>

                  {/* Vol ratio */}
                  <td className={`px-3 py-1.5 font-mono text-xs ${volRatioColor(row.vol_ratio)}`}>
                    {row.vol_ratio != null ? `${row.vol_ratio.toFixed(2)}×` : "—"}
                  </td>

                  {/* Price change */}
                  <td className={`px-3 py-1.5 font-mono text-xs ${
                    (row.price_change_pct ?? 0) >= 0 ? "text-bullish" : "text-bearish"
                  }`}>
                    {row.price_change_pct != null
                      ? `${row.price_change_pct >= 0 ? "+" : ""}${row.price_change_pct.toFixed(2)}%`
                      : "—"}
                  </td>

                  {/* Wyckoff events */}
                  <td className="px-3 py-1.5">
                    <div className="flex flex-wrap gap-1">
                      {(row.wyckoff_events ?? []).map(ev => (
                        <WyckoffTag key={ev} label={ev} />
                      ))}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {sorted.length > 30 && (
        <div className="flex justify-center">
          <Button variant="outline" size="sm" onClick={() => setShowAll(v => !v)}>
            {showAll ? "Show less" : `Show all ${sorted.length} rows`}
          </Button>
        </div>
      )}
    </div>
  );
}
