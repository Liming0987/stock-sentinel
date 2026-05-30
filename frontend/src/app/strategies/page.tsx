"use client";

import { useState, useMemo } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { DollarSign, Activity, Radio, ChevronDown, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useStrategies, useStrategyTrades, useEquityCurve, useAlpacaAccount,
  useLivePositions,
} from "@/lib/hooks";
import type { LivePosition } from "@/lib/hooks";

const STRATEGY_COLORS: Record<string, string> = {
  momentum:              "hsl(217, 91%, 60%)",  // blue
  rsi_meanreversion:     "hsl(142, 71%, 45%)",  // green
  sentiment_driven:      "hsl(38,  92%, 50%)",  // amber
  bb_breakout:           "hsl(280, 70%, 60%)",  // purple
  macd_histogram:        "hsl(340, 82%, 55%)",  // rose
  opening_range_breakout:"hsl(173, 80%, 40%)",  // teal
  vwap_cross:            "hsl(24,  95%, 55%)",  // orange
};

function formatPnl(val: number) {
  const sign = val >= 0 ? "+" : "";
  return `${sign}$${val.toFixed(2)}`;
}

function PnlText({ val, className = "" }: { val: number; className?: string }) {
  return (
    <span className={`font-mono ${val >= 0 ? "text-bullish" : "text-bearish"} ${className}`}>
      {formatPnl(val)}
    </span>
  );
}

function AlpacaBar() {
  const { data: acc } = useAlpacaAccount();
  if (!acc.configured) {
    return (
      <div className="rounded-lg border bg-muted/50 px-4 py-3 text-sm text-muted-foreground">
        Alpaca not configured — trades are simulated only
      </div>
    );
  }
  return (
    <div className="rounded-lg border bg-card px-4 py-3">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <span className="font-semibold text-primary w-full sm:w-auto">Alpaca Paper Account</span>
        <span>Cash: <span className="font-mono">${acc.cash?.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span></span>
        <span>Equity: <span className="font-mono">${acc.equity?.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span></span>
        <span>Buying Power: <span className="font-mono">${acc.buying_power?.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span></span>
        {acc.positions && acc.positions.length > 0 && (
          <span className="text-muted-foreground">{acc.positions.length} open position{acc.positions.length !== 1 ? "s" : ""}</span>
        )}
      </div>
    </div>
  );
}

function PositionRow({ pos }: { pos: LivePosition }) {
  const priceDiff = pos.current_price - pos.entry_price;
  const positive = priceDiff >= 0;
  const atRisk = pos.stop_loss !== null && pos.current_price <= pos.stop_loss * 1.02;
  const nearTarget = pos.target !== null && pos.current_price >= pos.target * 0.98;
  return (
    <tr className="border-b last:border-0 hover:bg-accent/30">
      <td className="py-2 pr-3 font-semibold">{pos.ticker}</td>
      <td className="py-2 pr-3 font-mono text-muted-foreground">${pos.entry_price.toFixed(2)}</td>
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
            ${pos.stop_loss.toFixed(2)}
            {atRisk && " ⚠"}
          </span>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
      <td className="py-2 pr-3 font-mono">
        {pos.target !== null ? (
          <span className={nearTarget ? "text-bullish font-semibold" : "text-muted-foreground"}>
            ${pos.target.toFixed(2)}
            {nearTarget && " ★"}
          </span>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
      <td className="py-2 pr-3 font-mono text-muted-foreground">{pos.qty}</td>
      <td className="py-2">
        <PnlText val={pos.unrealized_pnl} />
      </td>
    </tr>
  );
}

const REAL_SLOTS = 40;
const PAD_SLOTS = 16;

interface StrategyLivePanelProps {
  stratName: string;
  summary: { unrealized_pnl: number; position_count: number } | undefined;
  positions: LivePosition[];
  chartData: ReturnType<typeof useLivePositions>["history"];
  isOpen: boolean;
  onToggle: () => void;
  marketOpen: boolean;
  loading: boolean;
}

function StrategyLivePanel({
  stratName, summary, positions, chartData, isOpen, onToggle, marketOpen, loading,
}: StrategyLivePanelProps) {
  const color = STRATEGY_COLORS[stratName] || "hsl(var(--primary))";
  const hasData = chartData.some(
    (pt) => !pt.time.startsWith("\x00") && pt[stratName] !== undefined
  );

  return (
    <Card>
      {/* Clickable header */}
      <button
        onClick={onToggle}
        className="w-full text-left px-5 py-4 flex items-center justify-between gap-4 hover:bg-accent/30 transition-colors rounded-t-lg"
        style={{ borderBottom: isOpen ? "1px solid hsl(var(--border))" : undefined }}
      >
        <div className="flex items-center gap-3">
          <span className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: color }} />
          <span className="font-semibold capitalize">{stratName.replace(/_/g, " ")}</span>
          {summary ? (
            <PnlText val={summary.unrealized_pnl} className="text-sm font-bold" />
          ) : (
            <span className="text-xs text-muted-foreground">no open positions</span>
          )}
          {summary && (
            <span className="text-xs text-muted-foreground">
              {summary.position_count} position{summary.position_count !== 1 ? "s" : ""}
            </span>
          )}
          {!marketOpen && (
            <Badge variant="secondary" className="text-[10px] shrink-0">Market closed</Badge>
          )}
        </div>
        {isOpen
          ? <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
          : <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />}
      </button>

      {/* Collapsible body */}
      {isOpen && (
        <CardContent className="pt-4 space-y-4">
          {/* Chart */}
          <div className="h-48">
            {loading || !hasData ? (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                {loading ? "Fetching data…" : "No data yet…"}
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="time"
                    tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                    interval={7}
                    tickFormatter={(v: string) => (v.startsWith("\x00") ? "" : v)}
                  />
                  <YAxis tick={false} width={0} tickCount={10} />
                  <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="4 4" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    formatter={(val) => [`$${Number(val).toFixed(2)}`, stratName.replace(/_/g, " ")]}
                  />
                  <Line
                    type="monotone"
                    dataKey={stratName}
                    stroke={color}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Position table */}
          {positions.length === 0 ? (
            <p className="text-xs text-muted-foreground">No open positions for this strategy.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-3 font-medium">Ticker</th>
                    <th className="pb-2 pr-3 font-medium">Cost</th>
                    <th className="pb-2 pr-3 font-medium">Price</th>
                    <th className="pb-2 pr-3 font-medium">Change</th>
                    <th className="pb-2 pr-3 font-medium">Stop Loss</th>
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
          )}
        </CardContent>
      )}
    </Card>
  );
}

function LivePositionsPanel() {
  const { data, history, loading } = useLivePositions();

  const chartData = useMemo(() => {
    const recent = history.slice(-REAL_SLOTS);
    const pads = Array.from({ length: PAD_SLOTS }, (_, i) => ({ time: `\x00${i}` }));
    return [...recent, ...pads];
  }, [history]);

  // All known strategy names (from registry or from positions)
  const allStrategies = useMemo(() => {
    const fromPositions = data.positions.map((p) => p.strategy);
    const fromHistory = history.flatMap((pt) =>
      Object.keys(pt).filter((k) => k !== "time")
    );
    return Array.from(new Set([...fromPositions, ...fromHistory]));
  }, [data.positions, history]);

  // Default all open
  const [openMap, setOpenMap] = useState<Record<string, boolean>>({});
  const isOpen = (name: string) => openMap[name] !== false; // open by default

  const toggle = (name: string) =>
    setOpenMap((prev) => ({ ...prev, [name]: !isOpen(name) }));

  return (
    <div className="space-y-2">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-base font-semibold">
          <Radio className="h-4 w-4 text-primary" />
          Live Unrealized P&amp;L
        </h2>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="relative flex h-2 w-2 shrink-0">
            <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${data.market_open ? "animate-ping bg-primary" : "bg-muted-foreground"}`} />
            <span className={`relative inline-flex rounded-full h-2 w-2 ${data.market_open ? "bg-primary" : "bg-muted-foreground"}`} />
          </span>
          <span className="hidden sm:inline">{data.market_open ? "Updates every 5s" : "Market closed — showing last close prices"}</span>
          <span className="sm:hidden">{data.market_open ? "Live" : "Closed"}</span>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground py-4">Fetching live prices&hellip;</p>
      ) : allStrategies.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">
          No open positions — panels will appear once strategies open trades.
        </p>
      ) : (
        allStrategies.map((name) => (
          <StrategyLivePanel
            key={name}
            stratName={name}
            summary={data.by_strategy[name]}
            positions={data.positions.filter((p) => p.strategy === name)}
            chartData={chartData}
            isOpen={isOpen(name)}
            onToggle={() => toggle(name)}
            marketOpen={data.market_open}
            loading={loading}
          />
        ))
      )}
    </div>
  );
}

function StrategyCard({
  strat,
  liveUnrealized,
}: {
  strat: ReturnType<typeof useStrategies>["data"]["strategies"][0];
  liveUnrealized: number | undefined;
}) {
  const winPct = (strat.win_rate * 100).toFixed(0);
  // Prefer live real-time unrealized P&L; fall back to the last value the strategy runner saved
  const unrealized = liveUnrealized ?? strat.unrealized_pnl;
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="font-semibold capitalize">{strat.name.replace(/_/g, " ")}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{strat.description}</p>
          </div>
          <Badge variant={strat.enabled ? "bullish" : "secondary"} className="shrink-0 text-[10px]">
            {strat.enabled ? "Active" : "Disabled"}
          </Badge>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Realized P&L</p>
            <PnlText val={strat.total_pnl} className="text-base font-bold" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Unrealized</p>
            <PnlText val={unrealized} className="text-base font-bold" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Win Rate</p>
            <p className="font-mono text-base font-bold">{winPct}%</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Trades</p>
            <p className="font-mono text-base font-bold">
              {strat.total_trades}
              <span className="ml-1 text-xs text-muted-foreground font-normal">
                ({strat.winning_trades}W / {strat.losing_trades}L)
              </span>
            </p>
          </div>
        </div>
        {strat.last_run_at && (
          <p className="mt-3 text-[10px] text-muted-foreground">
            Last run: {new Date(strat.last_run_at).toLocaleString()}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function TradesTable({ strategyName }: { strategyName: string }) {
  const { data, loading } = useStrategyTrades(strategyName);
  if (loading) return <p className="text-sm text-muted-foreground p-4">Loading trades&hellip;</p>;
  if (data.trades.length === 0) return <p className="text-sm text-muted-foreground p-4">No trades yet.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="pb-2 pr-4 font-medium">Ticker</th>
            <th className="pb-2 pr-4 font-medium">Entry</th>
            <th className="pb-2 pr-4 font-medium">Exit</th>
            <th className="pb-2 pr-4 font-medium">Qty</th>
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
              <td className="py-2 pr-4 font-mono">{t.exit_price ? `$${t.exit_price.toFixed(2)}` : "—"}</td>
              <td className="py-2 pr-4 font-mono">{t.qty}</td>
              <td className="py-2 pr-4">
                {t.pnl != null ? <PnlText val={t.pnl} /> : <span className="text-muted-foreground">open</span>}
              </td>
              <td className="py-2 pr-4 font-mono">
                {t.return_pct != null ? (
                  <span className={t.return_pct >= 0 ? "text-bullish" : "text-bearish"}>
                    {(t.return_pct * 100).toFixed(2)}%
                  </span>
                ) : "—"}
              </td>
              <td className="py-2 pr-4">
                <Badge variant={t.status === "open" ? "bullish" : "secondary"} className="text-[10px]">
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
  );
}

export default function StrategiesPage() {
  const { data: strategiesData, loading } = useStrategies();
  const { data: curveData } = useEquityCurve();
  const { data: liveData } = useLivePositions();
  const [activeTab, setActiveTab] = useState<string | null>(null);

  const strategies = strategiesData.strategies;

  const allDates = Array.from(
    new Set(Object.values(curveData.curves).flatMap((pts) => pts.map((p) => p.date)))
  ).sort();

  const chartData = allDates.map((date) => {
    const point: Record<string, number | string> = { date };
    for (const [name, pts] of Object.entries(curveData.curves)) {
      const found = pts.find((p) => p.date === date);
      if (found) point[name] = found.cumulative_pnl;
    }
    return point;
  });

  const selectedStrategy = activeTab ?? (strategies[0]?.name ?? null);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Strategies</h1>
        <p className="text-sm text-muted-foreground">
          Live paper-trading results and backtesting comparison
        </p>
      </div>

      <AlpacaBar />

      {/* Real-time live positions panel */}
      <LivePositionsPanel />

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <p className="text-muted-foreground">Loading strategies&hellip;</p>
        </div>
      ) : (
        <>
          {/* Strategy cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {strategies.map((s) => (
              <StrategyCard
                key={s.name}
                strat={s}
                liveUnrealized={liveData.by_strategy[s.name]?.unrealized_pnl}
              />
            ))}
          </div>

          {/* Cumulative P&L chart */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                Cumulative P&amp;L Comparison
              </CardTitle>
            </CardHeader>
            <CardContent>
              {chartData.length === 0 ? (
                <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                  No closed trades yet — chart will populate as strategies execute.
                </div>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickFormatter={(v) => v.slice(5)} />
                      <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickFormatter={(v) => `$${v}`} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                        formatter={(val) => [`$${Number(val).toFixed(2)}`, ""]}
                      />
                      <Legend />
                      {Object.keys(curveData.curves).map((name) => (
                        <Line
                          key={name}
                          type="monotone"
                          dataKey={name}
                          stroke={STRATEGY_COLORS[name] || "hsl(var(--primary))"}
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

          {/* Trades per strategy */}
          <Card>
            <CardHeader>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-primary" />
                  Trade History
                </CardTitle>
                <div className="flex flex-wrap gap-1">
                  {strategies.map((s) => (
                    <button
                      key={s.name}
                      onClick={() => setActiveTab(s.name)}
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
              </div>
            </CardHeader>
            <CardContent>
              {selectedStrategy && <TradesTable strategyName={selectedStrategy} />}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
