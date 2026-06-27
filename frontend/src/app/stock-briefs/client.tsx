"use client";

import { useState, useMemo } from "react";
import { ArrowUpRight, ArrowDownRight, X, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/layout/page-header";
import type { StockAnalysis } from "./page";

type Stance = "accumulate" | "watch" | "hold" | "avoid";
type StanceFilter = Stance | "all";

const STANCE_LABEL: Record<Stance, string> = {
  accumulate: "Accumulate",
  watch: "Watch",
  hold: "Hold",
  avoid: "Avoid",
};

const STANCE_BADGE: Record<Stance, "bullish" | "secondary" | "destructive"> = {
  accumulate: "bullish",
  watch: "secondary",
  hold: "secondary",
  avoid: "destructive",
};

const FILTER_STYLES: Record<StanceFilter, string> = {
  all: "border-foreground/20 bg-foreground/5 text-foreground",
  accumulate: "border-bullish/40 bg-bullish/10 text-bullish",
  watch: "border-yellow-500/40 bg-yellow-500/10 text-yellow-500",
  hold: "border-primary/40 bg-primary/10 text-primary",
  avoid: "border-bearish/40 bg-bearish/10 text-bearish",
};

interface Props {
  dates: string[];
  allData: Record<string, StockAnalysis[]>;
}

function StockCard({
  a,
  selected,
  compact,
  onClick,
}: {
  a: StockAnalysis;
  selected: boolean;
  compact: boolean;
  onClick: () => void;
}) {
  const chg = Number(a.change_pct ?? 0);
  const up = chg >= 0;

  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-xl border bg-card p-4 transition-colors hover:border-primary focus:outline-none ${
        selected ? "border-primary bg-accent/30" : "border-border"
      }`}
    >
      {/* Top row */}
      <div className="mb-1 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="font-mono text-sm font-bold">{a.ticker}</span>
          {a.technical?.vcp_detected && (
            <span className="rounded bg-bullish/10 px-1.5 py-px text-[9px] font-bold text-bullish border border-bullish/20 leading-4">
              VCP
            </span>
          )}
          {(a.strategy_signals?.length ?? 0) > 0 && (
            <span className="rounded bg-primary/10 px-1.5 py-px text-[9px] font-bold text-primary border border-primary/20 leading-4">
              ⚡{a.strategy_signals.length}
            </span>
          )}
        </div>
        <Badge variant={STANCE_BADGE[a.overall_stance] ?? "secondary"} className="text-[9px] shrink-0 py-px">
          {STANCE_LABEL[a.overall_stance] ?? a.overall_stance}
        </Badge>
      </div>

      {/* Company + price */}
      {!compact && (
        <p className="mb-1.5 text-[11px] text-muted-foreground truncate">{a.company_name}</p>
      )}
      <div className="mb-2 flex items-baseline gap-2">
        <span className="font-mono text-sm font-semibold">
          ${Number(a.price).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
        <span className={`flex items-center gap-0.5 text-xs font-mono font-semibold ${up ? "text-bullish" : "text-bearish"}`}>
          {up ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
          {up ? "+" : ""}{chg.toFixed(2)}%
        </span>
      </div>

      {/* One-liner */}
      {!compact && (
        <p className="mb-2 text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
          {a.one_liner}
        </p>
      )}

      {/* Footer */}
      <div className="flex flex-wrap gap-x-2 text-[10px] text-muted-foreground/60">
        <span className="truncate">{a.technical?.wyckoff_phase ?? "—"}</span>
        {a.technical?.rsi != null && <span>RSI {Number(a.technical.rsi).toFixed(0)}</span>}
        {!compact && <span>{a.sentiment?.label ?? "—"}</span>}
      </div>
    </button>
  );
}

export function StockBriefsClient({ dates, allData }: Props) {
  const [selectedDate, setSelectedDate] = useState(dates[0] ?? "");
  const [stanceFilter, setStanceFilter] = useState<StanceFilter>("all");
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  const analyses = allData[selectedDate] ?? [];

  const counts = useMemo<Record<Stance, number>>(
    () => ({
      accumulate: analyses.filter((a) => a.overall_stance === "accumulate").length,
      watch:      analyses.filter((a) => a.overall_stance === "watch").length,
      hold:       analyses.filter((a) => a.overall_stance === "hold").length,
      avoid:      analyses.filter((a) => a.overall_stance === "avoid").length,
    }),
    [analyses]
  );

  const filtered = useMemo(
    () => (stanceFilter === "all" ? analyses : analyses.filter((a) => a.overall_stance === stanceFilter)),
    [analyses, stanceFilter]
  );

  const handleDateChange = (d: string) => {
    setSelectedDate(d);
    setSelectedTicker(null);
  };

  const handleCardClick = (ticker: string) => {
    setSelectedTicker((prev) => (prev === ticker ? null : ticker));
  };

  const reportOpen = selectedTicker !== null;

  return (
    <div className="space-y-4">
      <PageHeader
        kicker="Research"
        title="Stock Briefs"
        description="Pre-market intelligence briefings — Wyckoff, VCP, DCF, fundamentals, and news catalysts."
      />

      {/* Date tabs */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-xs text-muted-foreground mr-1">Date:</span>
        {dates.map((d) => (
          <button
            key={d}
            onClick={() => handleDateChange(d)}
            className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
              d === selectedDate
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground"
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      {/* Stance filter */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-xs text-muted-foreground mr-1">Filter:</span>
        {(["all", "accumulate", "watch", "avoid"] as StanceFilter[]).map((s) => {
          const count = s === "all" ? analyses.length : counts[s as Stance];
          if (s !== "all" && count === 0) return null;
          return (
            <button
              key={s}
              onClick={() => setStanceFilter((prev) => (prev === s ? "all" : s))}
              className={`rounded-full border px-3 py-0.5 text-xs font-medium capitalize transition-colors ${
                stanceFilter === s
                  ? FILTER_STYLES[s]
                  : "border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground"
              }`}
            >
              {s === "all" ? "All" : STANCE_LABEL[s as Stance]} ({count})
            </button>
          );
        })}
      </div>

      {/* Main area */}
      <div className={`flex gap-4 items-start ${reportOpen ? "" : ""}`}>
        {/* Card list / grid */}
        <div
          className={
            reportOpen
              ? "w-64 shrink-0 flex flex-col gap-2 overflow-y-auto"
              : "grid w-full grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3"
          }
          style={reportOpen ? { maxHeight: "calc(100vh - 280px)" } : {}}
        >
          {filtered.length === 0 ? (
            <p className="col-span-full py-8 text-center text-sm text-muted-foreground">
              No stocks match this filter.
            </p>
          ) : (
            filtered.map((a) => (
              <StockCard
                key={a.ticker}
                a={a}
                selected={selectedTicker === a.ticker}
                compact={reportOpen}
                onClick={() => handleCardClick(a.ticker)}
              />
            ))
          )}
        </div>

        {/* Report panel */}
        {reportOpen && (
          <div className="flex-1 min-w-0 flex flex-col gap-2">
            {/* Panel header */}
            <div className="flex items-center justify-between rounded-lg border bg-card px-4 py-2">
              <div className="flex items-center gap-3">
                <span className="font-mono font-bold">{selectedTicker}</span>
                <span className="text-xs text-muted-foreground">
                  {analyses.find((a) => a.ticker === selectedTicker)?.company_name}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={`/morning-briefs/${selectedDate}/${selectedTicker}.html`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  <ExternalLink className="h-3 w-3" />
                  Open full page
                </a>
                <button
                  onClick={() => setSelectedTicker(null)}
                  className="rounded-md p-1 hover:bg-accent transition-colors"
                  aria-label="Close report"
                >
                  <X className="h-4 w-4 text-muted-foreground" />
                </button>
              </div>
            </div>

            {/* iframe */}
            <iframe
              key={`${selectedDate}-${selectedTicker}`}
              src={`/morning-briefs/${selectedDate}/${selectedTicker}.html`}
              className="w-full rounded-xl border bg-card"
              style={{ height: "calc(100vh - 280px)", minHeight: 500 }}
              title={`${selectedTicker} Morning Brief`}
            />
          </div>
        )}
      </div>
    </div>
  );
}
