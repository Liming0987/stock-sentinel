"use client";

import { useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { VolumeHistoryPoint } from "@/lib/hooks";

type SortKey = "date" | "close" | "volume" | "avg_vol_30" | "vol_ratio" | "price_change_pct";
type SortDir = "asc" | "desc";

function fmtVol(v: number | null): string {
  if (v == null) return "—";
  return `${(v / 1_000_000).toFixed(2)}M`;
}

function volRatioColor(r: number | null): string {
  if (r == null) return "text-muted-foreground";
  if (r > 2) return "text-red-400";
  if (r >= 1.5) return "text-amber-400";
  return "text-slate-400";
}

interface VolumeTableProps {
  data: VolumeHistoryPoint[];
}

export function VolumeTable({ data }: VolumeTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [showAll, setShowAll] = useState(false);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sorted = [...data].sort((a, b) => {
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
    sortKey === col ? (
      sortDir === "asc" ? (
        <ChevronUp className="inline h-3 w-3" />
      ) : (
        <ChevronDown className="inline h-3 w-3" />
      )
    ) : null;

  const th = (label: string, col: SortKey) => (
    <th
      className="cursor-pointer select-none whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:text-foreground"
      onClick={() => handleSort(col)}
    >
      {label} <SortIcon col={col} />
    </th>
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            {th("Date", "date")}
            {th("Close", "close")}
            {th("Daily Vol", "volume")}
            {th("30d Avg", "avg_vol_30")}
            {th("Vol Ratio", "vol_ratio")}
            {th("Price Chg%", "price_change_pct")}
            <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">
              Interpretation
            </th>
          </tr>
        </thead>
        <tbody>
          {displayed.map((row, i) => (
            <tr
              key={i}
              className={`border-b border-border/50 transition-colors hover:bg-muted/30 ${
                row.is_spike ? "bg-amber-950/30" : ""
              }`}
            >
              <td className="px-3 py-1.5 font-mono text-xs">{row.date}</td>
              <td className="px-3 py-1.5 font-mono">
                {row.close != null ? `$${row.close.toFixed(2)}` : "—"}
              </td>
              <td className="px-3 py-1.5 font-mono">{fmtVol(row.volume)}</td>
              <td className="px-3 py-1.5 font-mono text-muted-foreground">
                {fmtVol(row.avg_vol_30)}
              </td>
              <td className={`px-3 py-1.5 font-mono font-medium ${volRatioColor(row.vol_ratio)}`}>
                {row.vol_ratio != null ? `${row.vol_ratio.toFixed(2)}x` : "—"}
              </td>
              <td
                className={`px-3 py-1.5 font-mono ${
                  row.price_change_pct != null && row.price_change_pct >= 0
                    ? "text-green-400"
                    : "text-red-400"
                }`}
              >
                {row.price_change_pct != null
                  ? `${row.price_change_pct >= 0 ? "+" : ""}${row.price_change_pct.toFixed(2)}%`
                  : "—"}
              </td>
              <td className="px-3 py-1.5 text-xs text-muted-foreground">{row.interpretation}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > 30 && (
        <div className="mt-3 flex justify-center">
          <Button variant="outline" size="sm" onClick={() => setShowAll((v) => !v)}>
            {showAll ? "Show less" : `Show all ${data.length} rows`}
          </Button>
        </div>
      )}
    </div>
  );
}
