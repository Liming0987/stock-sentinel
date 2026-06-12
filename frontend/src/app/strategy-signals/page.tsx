"use client";

import { useState, useMemo } from "react";
import { Zap, TrendingUp, TrendingDown, Minus, CheckCircle2, Clock, ChevronLeft, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useStrategies, useStrategySignals } from "@/lib/hooks";
import type { StrategySignalItem } from "@/lib/hooks";

const ACTION_STYLES = {
  buy: {
    badge: "bullish" as const,
    icon: TrendingUp,
    label: "BUY",
    border: "border-l-green-500",
    bg: "bg-green-500/5",
  },
  sell: {
    badge: "destructive" as const,
    icon: TrendingDown,
    label: "SELL",
    border: "border-l-red-500",
    bg: "bg-red-500/5",
  },
  hold: {
    badge: "secondary" as const,
    icon: Minus,
    label: "HOLD",
    border: "border-l-yellow-500",
    bg: "bg-yellow-500/5",
  },
};

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function PriceGrid({
  entry,
  stop,
  target,
}: {
  entry: number | null;
  stop: number | null;
  target: number | null;
}) {
  const fmt = (v: number | null) =>
    v != null ? `$${v.toFixed(2)}` : <span className="text-muted-foreground">—</span>;

  return (
    <div className="grid grid-cols-3 gap-2 text-xs">
      <div className="rounded bg-muted/50 px-2 py-1.5">
        <p className="text-muted-foreground mb-0.5">Entry</p>
        <p className="font-mono font-semibold">{fmt(entry)}</p>
      </div>
      <div className="rounded bg-muted/50 px-2 py-1.5">
        <p className="text-muted-foreground mb-0.5">Stop Loss</p>
        <p className="font-mono font-semibold text-bearish">{fmt(stop)}</p>
      </div>
      <div className="rounded bg-muted/50 px-2 py-1.5">
        <p className="text-muted-foreground mb-0.5">Target</p>
        <p className="font-mono font-semibold text-bullish">{fmt(target)}</p>
      </div>
    </div>
  );
}

function SignalCard({ sig }: { sig: StrategySignalItem }) {
  const style = ACTION_STYLES[sig.action] ?? ACTION_STYLES.hold;
  const ActionIcon = style.icon;
  const rr =
    sig.entry_price && sig.stop_loss && sig.target
      ? ((sig.target - sig.entry_price) / (sig.entry_price - sig.stop_loss)).toFixed(1)
      : null;

  return (
    <div
      className={`rounded-lg border border-l-4 ${style.border} ${style.bg} p-4 space-y-3`}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-base font-bold">{sig.ticker}</span>
          <Badge variant={style.badge} className="flex items-center gap-1 text-xs px-2 py-0.5">
            <ActionIcon className="h-3 w-3" />
            {style.label}
          </Badge>
          {sig.confidence != null && (
            <span className="text-xs text-muted-foreground font-mono">
              {(sig.confidence * 100).toFixed(0)}% confidence
            </span>
          )}
          {rr && (
            <span className="text-xs text-muted-foreground">
              R/R&nbsp;1:{rr}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {sig.executed ? (
            <span className="flex items-center gap-1 text-[10px] font-medium text-green-600 dark:text-green-400">
              <CheckCircle2 className="h-3 w-3" />
              Executed
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <Clock className="h-3 w-3" />
              Not executed
            </span>
          )}
          <span className="text-[10px] text-muted-foreground">{timeAgo(sig.created_at)}</span>
        </div>
      </div>

      {/* Strategy label */}
      <p className="text-[11px] text-muted-foreground capitalize">
        {sig.strategy_name.replace(/_/g, " ")}
      </p>

      {/* Price grid */}
      {sig.action !== "hold" && (
        <PriceGrid entry={sig.entry_price} stop={sig.stop_loss} target={sig.target} />
      )}

      {/* Reasoning */}
      {sig.reasoning.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-1.5">
            Why this signal
          </p>
          <ul className="space-y-1">
            {sig.reasoning.map((r, i) => (
              <li key={i} className="flex gap-2 text-xs">
                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/60 mt-1.5" />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Timestamp */}
      <p className="text-[10px] text-muted-foreground">
        {sig.created_at ? new Date(sig.created_at).toLocaleString() : ""}
      </p>
    </div>
  );
}

const PAGE_SIZE = 50;

export default function StrategySignalsPage() {
  const { data: strategiesData } = useStrategies();
  const strategies = strategiesData.strategies;

  const [selectedStrategy, setSelectedStrategy] = useState<string>("all");
  const [selectedAction, setSelectedAction] = useState<"all" | "buy" | "sell">("all");
  const [page, setPage] = useState(1);

  const filters = useMemo(() => {
    const f: { strategy?: string; action?: string; limit: number; offset: number } = {
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    };
    if (selectedStrategy !== "all") f.strategy = selectedStrategy;
    if (selectedAction !== "all") f.action = selectedAction;
    return f;
  }, [selectedStrategy, selectedAction, page]);

  const { data, loading } = useStrategySignals(filters);
  const signals = data.signals;
  const total = data.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const resetPage = () => setPage(1);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Zap className="h-6 w-6 text-primary" />
          Signal Log
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Full history of buy and sell signals with entry, stop loss, target, and reasoning for each strategy.
        </p>
      </div>

      {/* Strategy filter */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Filter by Strategy
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => { setSelectedStrategy("all"); resetPage(); }}
              className={`rounded px-3 py-1 text-xs font-medium transition-colors capitalize ${
                selectedStrategy === "all"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent"
              }`}
            >
              All Strategies
            </button>
            {strategies.map((s) => (
              <button
                key={s.name}
                onClick={() => { setSelectedStrategy(s.name); resetPage(); }}
                className={`rounded px-3 py-1 text-xs font-medium transition-colors capitalize ${
                  selectedStrategy === s.name
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent"
                }`}
              >
                {s.name.replace(/_/g, " ")}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Action filter */}
      <div className="flex gap-2">
        {(["all", "buy", "sell"] as const).map((a) => (
          <button
            key={a}
            onClick={() => { setSelectedAction(a); resetPage(); }}
            className={`rounded-full px-4 py-1.5 text-xs font-semibold transition-colors uppercase ${
              selectedAction === a
                ? a === "buy"
                  ? "bg-green-600 text-white"
                  : a === "sell"
                  ? "bg-red-600 text-white"
                  : "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-accent"
            }`}
          >
            {a === "all" ? "All Actions" : a}
          </button>
        ))}
      </div>

      {/* Signal count */}
      {!loading && (
        <p className="text-sm text-muted-foreground">
          Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total} signal{total !== 1 ? "s" : ""}
          {selectedStrategy !== "all" && ` for ${selectedStrategy.replace(/_/g, " ")}`}
          {selectedAction !== "all" && ` · ${selectedAction} only`}
        </p>
      )}

      {/* Signal cards */}
      {loading ? (
        <p className="text-sm text-muted-foreground py-8 text-center">Loading signals&hellip;</p>
      ) : signals.length === 0 ? (
        <div className="rounded-lg border bg-muted/30 py-16 text-center">
          <Zap className="mx-auto h-10 w-10 text-muted-foreground/40 mb-3" />
          <p className="text-sm text-muted-foreground">
            No signals yet. Signals are recorded each time a strategy evaluates a stock.
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Trigger a strategy run from the Strategies page to generate signals.
          </p>
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {signals.map((sig) => (
              <SignalCard key={sig.id} sig={sig} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="flex items-center gap-1 rounded px-3 py-1.5 text-xs font-medium bg-muted text-muted-foreground hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                Prev
              </button>

              <div className="flex items-center gap-1">
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
                  .reduce<(number | "…")[]>((acc, p, idx, arr) => {
                    if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push("…");
                    acc.push(p);
                    return acc;
                  }, [])
                  .map((item, idx) =>
                    item === "…" ? (
                      <span key={`ellipsis-${idx}`} className="px-1 text-xs text-muted-foreground">…</span>
                    ) : (
                      <button
                        key={item}
                        onClick={() => setPage(item as number)}
                        className={`min-w-[28px] rounded px-2 py-1 text-xs font-medium transition-colors ${
                          page === item
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-muted-foreground hover:bg-accent"
                        }`}
                      >
                        {item}
                      </button>
                    )
                  )}
              </div>

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="flex items-center gap-1 rounded px-3 py-1.5 text-xs font-medium bg-muted text-muted-foreground hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
