"use client";

import { useState, useMemo, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from "recharts";
import {
  Activity, ChevronDown, ChevronRight, RefreshCw, AlertTriangle,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import {
  useStrategies, useStrategyTrades, useEquityCurve, useAlpacaAccount,
  useLivePositions, useTaskErrors,
} from "@/lib/hooks";
import type { LivePosition } from "@/lib/hooks";

const STRATEGY_COLORS: Record<string, string> = {
  momentum:               "hsl(217, 91%, 60%)",
  rsi_meanreversion:      "hsl(142, 71%, 45%)",
  sentiment_driven:       "hsl(38,  92%, 50%)",
  bb_breakout:            "hsl(280, 70%, 60%)",
  macd_histogram:         "hsl(340, 82%, 55%)",
  opening_range_breakout: "hsl(173, 80%, 40%)",
  vwap_cross:             "hsl(24,  95%, 55%)",
  fib_retracement:        "hsl(48,  95%, 50%)",
  elliott_fib:            "hsl(199, 89%, 48%)",
};

function PnlText({ val, className = "" }: { val: number; className?: string }) {
  const sign = val >= 0 ? "+" : "";
  return (
    <span className={`font-mono ${val >= 0 ? "text-bullish" : "text-bearish"} ${className}`}>
      {sign}${val.toFixed(2)}
    </span>
  );
}

function Kpi({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border bg-card px-4 py-3.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <div className="mt-1">{children}</div>
    </div>
  );
}

function StatCell({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 shrink-0">
      <span className="text-[10px] uppercase tracking-wide text-muted-foreground/60">{label}</span>
      <div className="text-sm">{children}</div>
    </div>
  );
}

function PositionRow({ pos }: { pos: LivePosition }) {
  const positive = pos.current_price >= pos.entry_price;
  const atRisk = pos.stop_loss !== null && pos.current_price <= pos.stop_loss * 1.02;
  const nearTarget = pos.target !== null && pos.current_price >= pos.target * 0.98;
  const isUntracked = pos.source === "alpaca";
  return (
    <tr className={`border-b last:border-0 hover:bg-accent/30 ${isUntracked ? "opacity-80" : ""}`}>
      <td className="py-2 pr-3 font-semibold">
        {pos.ticker}
        {isUntracked && (
          <span title="Not tracked in DB — sync with Alpaca to attribute">
            <AlertTriangle className="inline ml-1 h-3 w-3 text-amber-500" />
          </span>
        )}
      </td>
      <td className="py-2 pr-3 font-mono text-muted-foreground whitespace-nowrap">
        {pos.opened_at
          ? new Date(pos.opened_at).toLocaleString("en-US", {
              month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
            })
          : "—"}
      </td>
      <td className="py-2 pr-3 font-mono text-muted-foreground">
        ${(pos.entry_price * pos.qty).toFixed(2)}
      </td>
      <td className="py-2 pr-3 font-mono font-semibold">
        <span className={positive ? "text-bullish" : "text-bearish"}>
          ${pos.current_price.toFixed(2)}
        </span>
      </td>
      <td className="py-2 pr-3 font-mono">
        <span className={positive ? "text-bullish" : "text-bearish"}>
          {positive ? "+" : ""}{(pos.return_pct * 100).toFixed(2)}%
        </span>
      </td>
      <td className="py-2 pr-3 font-mono">
        {pos.stop_loss !== null ? (
          <span className={atRisk ? "text-bearish font-semibold" : "text-muted-foreground"}>
            ${pos.stop_loss.toFixed(2)}{atRisk && " ⚠"}
          </span>
        ) : <span className="text-muted-foreground">—</span>}
      </td>
      <td className="py-2 pr-3 font-mono">
        {pos.target !== null ? (
          <span className={nearTarget ? "text-bullish font-semibold" : "text-muted-foreground"}>
            ${pos.target.toFixed(2)}{nearTarget && " ★"}
          </span>
        ) : <span className="text-muted-foreground">—</span>}
      </td>
      <td className="py-2 pr-3 font-mono text-muted-foreground">{pos.qty}</td>
      <td className="py-2">
        <PnlText val={pos.unrealized_pnl} />
      </td>
    </tr>
  );
}

function StrategyDetail({
  stratName,
  positions,
}: {
  stratName: string;
  positions: LivePosition[];
}) {
  const [tab, setTab] = useState<"positions" | "history">("positions");
  const { data, loading } = useStrategyTrades(stratName);

  return (
    <div className="border-t bg-muted/20">
      <div className="flex gap-1 px-5 pt-3 pb-1">
        {(["positions", "history"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-[7px] px-3 py-1 text-xs font-medium transition-colors ${
              tab === t
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent"
            }`}
          >
            {t === "positions" ? `Open Positions (${positions.length})` : "Trade History"}
          </button>
        ))}
      </div>

      <div className="px-5 pb-5 pt-2">
        {tab === "positions" && (
          positions.length === 0 ? (
            <p className="text-xs text-muted-foreground py-2">No open positions.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-3 font-medium">Ticker</th>
                    <th className="pb-2 pr-3 font-medium">Opened</th>
                    <th className="pb-2 pr-3 font-medium">Cost</th>
                    <th className="pb-2 pr-3 font-medium">Price</th>
                    <th className="pb-2 pr-3 font-medium">Change</th>
                    <th className="pb-2 pr-3 font-medium">Stop</th>
                    <th className="pb-2 pr-3 font-medium">Target</th>
                    <th className="pb-2 pr-3 font-medium">Qty</th>
                    <th className="pb-2 font-medium">Unrealized</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((pos, i) => (
                    <PositionRow key={`${pos.ticker}-${i}`} pos={pos} />
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}

        {tab === "history" && (
          loading ? (
            <p className="text-xs text-muted-foreground py-2">Loading…</p>
          ) : data.trades.length === 0 ? (
            <p className="text-xs text-muted-foreground py-2">No trades yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-4 font-medium">Ticker</th>
                    <th className="pb-2 pr-4 font-medium">Entry</th>
                    <th className="pb-2 pr-4 font-medium">Qty</th>
                    <th className="pb-2 pr-4 font-medium">Cost</th>
                    <th className="pb-2 pr-4 font-medium">Exit</th>
                    <th className="pb-2 pr-4 font-medium">P&amp;L</th>
                    <th className="pb-2 pr-4 font-medium">Return</th>
                    <th className="pb-2 pr-4 font-medium">Status</th>
                    <th className="pb-2 pr-4 font-medium">Entered</th>
                    <th className="pb-2 font-medium">Exited</th>
                  </tr>
                </thead>
                <tbody>
                  {data.trades.map((t) => (
                    <tr key={t.id} className="border-b last:border-0 hover:bg-accent/30">
                      <td className="py-2 pr-4 font-semibold">{t.ticker}</td>
                      <td className="py-2 pr-4 font-mono">${t.entry_price.toFixed(2)}</td>
                      <td className="py-2 pr-4 font-mono">{t.qty}</td>
                      <td className="py-2 pr-4 font-mono text-muted-foreground">
                        {t.total_cost != null
                          ? `$${t.total_cost.toFixed(2)}`
                          : `$${(t.entry_price * t.qty).toFixed(2)}`}
                      </td>
                      <td className="py-2 pr-4 font-mono">
                        {t.exit_price ? `$${t.exit_price.toFixed(2)}` : "—"}
                      </td>
                      <td className="py-2 pr-4">
                        {t.pnl != null ? (
                          <PnlText val={t.pnl} />
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="py-2 pr-4 font-mono">
                        {t.return_pct != null ? (
                          <span className={t.return_pct >= 0 ? "text-bullish" : "text-bearish"}>
                            {(t.return_pct * 100).toFixed(2)}%
                          </span>
                        ) : "—"}
                      </td>
                      <td className="py-2 pr-4">
                        <Badge
                          variant={
                            t.status === "open"
                              ? "bullish"
                              : t.status === "cancelled"
                              ? "destructive"
                              : "secondary"
                          }
                          className="text-[10px]"
                        >
                          {t.status}
                        </Badge>
                      </td>
                      <td className="py-2 pr-4 font-mono text-muted-foreground whitespace-nowrap">
                        {t.opened_at ? new Date(t.opened_at).toLocaleString() : "—"}
                      </td>
                      <td className="py-2 font-mono text-muted-foreground whitespace-nowrap">
                        {t.closed_at ? new Date(t.closed_at).toLocaleString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>
    </div>
  );
}

type StrategyData = ReturnType<typeof useStrategies>["data"]["strategies"][0];

function StrategyRow({
  strat,
  liveUnrealized,
  positions,
  isOpen,
  onToggle,
}: {
  strat: StrategyData;
  liveUnrealized: number | undefined;
  positions: LivePosition[];
  isOpen: boolean;
  onToggle: () => void;
}) {
  const color = STRATEGY_COLORS[strat.name] || "hsl(260, 70%, 60%)";
  const unrealized = liveUnrealized ?? strat.unrealized_pnl;
  const winPct = (strat.win_rate * 100).toFixed(0);

  return (
    <div className="border-b last:border-0">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-5 py-3.5 hover:bg-accent/30 transition-colors text-left"
      >
        <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: color }} />

        <span className="capitalize font-medium text-sm w-48 shrink-0 truncate">
          {strat.name.replace(/_/g, " ")}
        </span>

        <Badge
          variant={strat.enabled ? "bullish" : "secondary"}
          className="text-[10px] px-1.5 py-0.5 shrink-0"
        >
          {strat.enabled ? "Active" : "Off"}
        </Badge>

        <div className="flex flex-1 items-center gap-6 ml-2 overflow-hidden">
          <StatCell label="Realized">
            <PnlText val={strat.total_pnl} className="font-semibold" />
          </StatCell>
          <StatCell label="Unrealized">
            <PnlText val={unrealized} className="font-semibold" />
          </StatCell>
          <StatCell label="Win Rate">
            <span className="font-mono font-semibold">{winPct}%</span>
          </StatCell>
          <StatCell label="Trades">
            <span className="font-mono font-semibold">{strat.total_trades}</span>
            <span className="ml-1 text-[10px] text-muted-foreground">
              {strat.winning_trades}W / {strat.losing_trades}L
            </span>
          </StatCell>
          {strat.sharpe_ratio != null && (
            <StatCell label="Sharpe">
              <span
                className={`font-mono font-semibold ${
                  strat.sharpe_ratio >= 1
                    ? "text-green-500"
                    : strat.sharpe_ratio >= 0
                    ? "text-yellow-500"
                    : "text-red-500"
                }`}
              >
                {strat.sharpe_ratio.toFixed(2)}
              </span>
            </StatCell>
          )}
          {strat.max_drawdown != null && (
            <StatCell label="Max DD">
              <span className="font-mono font-semibold text-bearish">
                -{strat.max_drawdown.toFixed(1)}%
              </span>
            </StatCell>
          )}
          {positions.length > 0 && (
            <span className="text-[11px] font-medium text-primary bg-primary/10 rounded-full px-2 py-0.5 shrink-0">
              {positions.length} open
            </span>
          )}
          {strat.last_run_at && (
            <span className="text-[10px] text-muted-foreground/60 ml-auto shrink-0 hidden xl:block">
              ran {new Date(strat.last_run_at).toLocaleString("en-US", {
                month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
              })}
            </span>
          )}
        </div>

        {isOpen
          ? <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
          : <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />}
      </button>

      {isOpen && <StrategyDetail stratName={strat.name} positions={positions} />}
    </div>
  );
}

export default function StrategiesPage() {
  const { data: strategiesData, loading } = useStrategies();
  const { data: curveData } = useEquityCurve();
  const { data: liveData } = useLivePositions();
  const { data: acc } = useAlpacaAccount();
  const taskErrors = useTaskErrors();

  const [openMap, setOpenMap] = useState<Record<string, boolean>>({});
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [isReconciling, setIsReconciling] = useState(false);
  const [reconcileMsg, setReconcileMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!reconcileMsg) return;
    const timer = setTimeout(() => setReconcileMsg(null), 5000);
    return () => clearTimeout(timer);
  }, [reconcileMsg]);

  const handleSync = async () => {
    setSyncing(true);
    setSyncMsg(null);
    try {
      const res = await (api.strategies.syncAlpaca() as Promise<{ synced: number; message: string }>);
      setSyncMsg(res.message);
    } catch {
      setSyncMsg("Sync failed — check server logs.");
    } finally {
      setSyncing(false);
    }
  };

  const handleReconcile = async () => {
    setIsReconciling(true);
    setReconcileMsg(null);
    try {
      const res = await (api.strategies.reconcile() as Promise<{
        alpaca_orphans_cancelled?: number;
        db_orphans_closed?: number;
        message?: string;
        [key: string]: unknown;
      }>);
      const alphaOrphans = res.alpaca_orphans_cancelled ?? 0;
      const dbOrphans = res.db_orphans_closed ?? 0;
      setReconcileMsg(
        res.message ??
          `Reconciled: ${alphaOrphans} Alpaca orphan(s) cancelled, ${dbOrphans} DB orphan(s) closed.`
      );
    } catch (err) {
      setReconcileMsg(err instanceof Error ? err.message : "Reconcile failed — check server logs.");
    } finally {
      setIsReconciling(false);
    }
  };

  const strategies = strategiesData.strategies;
  const isOpen = (name: string) => openMap[name] === true;
  const toggle = (name: string) =>
    setOpenMap((prev) => ({ ...prev, [name]: !isOpen(name) }));

  const totalRealized = useMemo(
    () => strategies.reduce((s, x) => s + x.total_pnl, 0),
    [strategies]
  );
  const totalUnrealized = useMemo(
    () => Object.values(liveData.by_strategy).reduce((s, x) => s + x.unrealized_pnl, 0),
    [liveData.by_strategy]
  );
  const activeCount = strategies.filter((s) => s.enabled).length;
  const bestStrat = useMemo(
    () =>
      strategies.length > 0
        ? [...strategies].sort((a, b) => b.total_pnl - a.total_pnl)[0]
        : null,
    [strategies]
  );

  const chartData = useMemo(() => {
    const allDates = Array.from(
      new Set(Object.values(curveData.curves).flatMap((pts) => pts.map((p) => p.date)))
    ).sort();
    return allDates.map((date) => {
      const point: Record<string, number | string> = { date };
      for (const [name, pts] of Object.entries(curveData.curves)) {
        const found = pts.find((p) => p.date === date);
        if (found) point[name] = found.cumulative_pnl;
      }
      return point;
    });
  }, [curveData.curves]);

  const hasUntracked = liveData.positions.some((p) => p.source === "alpaca");

  return (
    <div className="mx-auto max-w-[1180px] space-y-5">
      <PageHeader
        kicker="Research"
        title="Strategies"
        description="Rule-based strategies trading a paper account. Track which edges are working before risking real capital."
      />

      {/* Task error banner */}
      {taskErrors.length > 0 && (
        <div className="space-y-2">
          {taskErrors.slice(0, 3).map((e) => (
            <div key={e.id} className="flex items-start gap-2.5 rounded-lg border border-bearish/30 bg-bearish/5 px-4 py-3 text-sm">
              <AlertTriangle className="h-4 w-4 text-bearish shrink-0 mt-0.5" />
              <div className="min-w-0">
                <span className="font-semibold text-bearish">[{(e.meta.task_name as string) ?? "task"}]</span>
                <span className="ml-2 text-muted-foreground">{e.message.replace(/^\[.*?\]\s*/, "")}</span>
                <span className="ml-2 text-[10px] text-muted-foreground">
                  {new Date(e.timestamp).toLocaleString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Account + controls row */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
          {acc.configured ? (
            <>
              <span className="text-xs font-semibold text-primary">Alpaca Paper</span>
              <span className="text-muted-foreground">
                Cash <span className="font-mono text-foreground">
                  ${acc.cash?.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </span>
              </span>
              <span className="text-muted-foreground">
                Equity <span className="font-mono text-foreground">
                  ${acc.equity?.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </span>
              </span>
              <span className="text-muted-foreground">
                BP <span className="font-mono text-foreground">
                  ${acc.buying_power?.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </span>
              </span>
            </>
          ) : (
            <span className="text-xs text-muted-foreground">
              Alpaca not configured — simulation only
            </span>
          )}
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="relative flex h-2 w-2 shrink-0">
              <span
                className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  liveData.market_open ? "animate-ping bg-primary" : "bg-muted-foreground"
                }`}
              />
              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${
                  liveData.market_open ? "bg-primary" : "bg-muted-foreground"
                }`}
              />
            </span>
            {liveData.market_open ? "Live — updates every 5s" : "Market closed"}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleSync}
            disabled={syncing}
            title="Pull Alpaca positions into the DB and attribute them to strategies"
            className="flex items-center gap-1.5 rounded-[8px] border px-3 py-1.5 text-xs font-medium hover:bg-accent transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${syncing ? "animate-spin" : ""}`} />
            Sync Alpaca
          </button>
          <button
            onClick={handleReconcile}
            disabled={isReconciling}
            title="Compare DB open trades vs live Alpaca positions and close any orphans"
            className="flex items-center gap-1.5 rounded-[8px] border px-3 py-1.5 text-xs font-medium hover:bg-accent transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${isReconciling ? "animate-spin" : ""}`} />
            Reconcile
          </button>
        </div>
      </div>

      {syncMsg && (
        <p className="text-xs text-muted-foreground px-1">{syncMsg}</p>
      )}
      {reconcileMsg && (
        <div className="flex items-center justify-between rounded-lg border bg-muted/40 px-3 py-2 text-xs">
          <span className="text-muted-foreground">{reconcileMsg}</span>
          <button
            onClick={() => setReconcileMsg(null)}
            className="ml-3 text-muted-foreground hover:text-foreground"
          >
            &times;
          </button>
        </div>
      )}
      {hasUntracked && !syncing && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            Some Alpaca positions aren&rsquo;t tracked in the DB. Click{" "}
            <strong>Sync Alpaca</strong> to attribute them.
          </span>
        </div>
      )}

      {loading ? (
        <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
          Loading strategies…
        </div>
      ) : (
        <>
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Kpi label="Total Realized P&L">
              <PnlText val={totalRealized} className="text-xl font-bold" />
            </Kpi>
            <Kpi label="Total Unrealized">
              <PnlText val={totalUnrealized} className="text-xl font-bold" />
            </Kpi>
            <Kpi label="Active Strategies">
              <span className="text-xl font-bold">{activeCount}</span>
              <span className="ml-1 text-sm text-muted-foreground font-normal">
                / {strategies.length}
              </span>
            </Kpi>
            <Kpi label="Top Strategy">
              {bestStrat ? (
                <span className="text-base font-semibold capitalize truncate block">
                  {bestStrat.name.replace(/_/g, " ")}
                </span>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </Kpi>
          </div>

          {/* Cumulative P&L chart */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="h-4 w-4 text-primary" />
                Cumulative P&amp;L by Strategy
              </CardTitle>
            </CardHeader>
            <CardContent>
              {chartData.length === 0 ? (
                <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                  No closed trades yet — chart will populate as strategies execute.
                </div>
              ) : (
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={chartData}
                      margin={{ top: 5, right: 10, left: -10, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                        tickFormatter={(v) => v.slice(5)}
                      />
                      <YAxis
                        tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                        tickFormatter={(v) => `$${v}`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "var(--card)",
                          border: "1px solid var(--border)",
                          borderRadius: "8px",
                          fontSize: "12px",
                        }}
                        formatter={(val) => [`$${Number(val).toFixed(2)}`, ""]}
                      />
                      <Legend />
                      {Object.keys(curveData.curves).map((name) => (
                        <Line
                          key={name}
                          type="monotone"
                          dataKey={name}
                          stroke={STRATEGY_COLORS[name] || "hsl(260, 70%, 60%)"}
                          strokeWidth={2}
                          dot={false}
                          connectNulls
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Strategy accordion */}
          <Card className="overflow-hidden p-0">
            {strategies.length === 0 ? (
              <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
                No strategies registered.
              </div>
            ) : (
              strategies.map((strat) => (
                <StrategyRow
                  key={strat.name}
                  strat={strat}
                  liveUnrealized={liveData.by_strategy[strat.name]?.unrealized_pnl}
                  positions={liveData.positions.filter((p) => p.strategy === strat.name)}
                  isOpen={isOpen(strat.name)}
                  onToggle={() => toggle(strat.name)}
                />
              ))
            )}
          </Card>
        </>
      )}
    </div>
  );
}
