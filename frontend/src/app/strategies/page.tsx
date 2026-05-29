"use client";

import { useState, useMemo } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { DollarSign, Activity, Radio } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useStrategies, useStrategyTrades, useEquityCurve, useAlpacaAccount,
  useLivePositions,
} from "@/lib/hooks";
import type { LivePosition } from "@/lib/hooks";

const STRATEGY_COLORS: Record<string, string> = {
  momentum: "hsl(var(--primary))",
  rsi_meanreversion: "hsl(142, 71%, 45%)",
  sentiment_driven: "hsl(38, 92%, 50%)",
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
      <div className="flex flex-wrap items-center gap-6 text-sm">
        <span className="font-semibold text-primary">Alpaca Paper Account</span>
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
      <td className="py-2 pr-3">
        <span
          className="inline-block h-2 w-2 rounded-full mr-2"
          style={{ backgroundColor: STRATEGY_COLORS[pos.strategy] || "hsl(var(--primary))" }}
        />
        <span className="text-xs capitalize text-muted-foreground">
          {pos.strategy.replace(/_/g, " ")}
        </span>
      </td>
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

function LivePositionsPanel() {
  const { data, history, loading } = useLivePositions(3000);
  const activeStrategies = Object.keys(data.by_strategy);
  const hasPositions = data.positions.length > 0;
  const hasHistory = history.length > 1;

  // Fixed-width windowed data: last REAL_SLOTS real points + PAD_SLOTS empty
  // slots on the right so the live line always ends at ~70% across the chart.
  const REAL_SLOTS = 40;
  const PAD_SLOTS = 16;
  const chartData = useMemo(() => {
    const recent = history.slice(-REAL_SLOTS);
    const pads = Array.from({ length: PAD_SLOTS }, (_, i) => ({ time: `\x00${i}` }));
    return [...recent, ...pads];
  }, [history]);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Radio className="h-5 w-5 text-primary" />
            Live Unrealized P&amp;L
          </CardTitle>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
            </span>
            Updates every 3s
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Per-strategy summary badges */}
        {hasPositions && (
          <div className="flex flex-wrap gap-3">
            {Object.entries(data.by_strategy).map(([name, s]) => (
              <div
                key={name}
                className="rounded-lg border px-3 py-2 text-sm flex items-center gap-3"
                style={{ borderColor: STRATEGY_COLORS[name] || "hsl(var(--border))" }}
              >
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ backgroundColor: STRATEGY_COLORS[name] || "hsl(var(--primary))" }}
                />
                <span className="capitalize text-muted-foreground text-xs">
                  {name.replace(/_/g, " ")}
                </span>
                <PnlText val={s.unrealized_pnl} className="font-bold" />
                <span className="text-xs text-muted-foreground">
                  {s.position_count} pos
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Time-series chart */}
        <div className="h-56">
          {loading ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              Fetching live prices&hellip;
            </div>
          ) : !hasPositions ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              No open positions — chart will appear once strategies open trades.
            </div>
          ) : !hasHistory ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              Collecting data&hellip;
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                  interval={7}
                  tickFormatter={(v: string) => (v.startsWith("\x00") ? "" : v)}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  tickFormatter={(v) => `$${Number(v).toFixed(2)}`}
                />
                <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="4 4" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                  formatter={(val, name) => [
                    `$${Number(val).toFixed(2)}`,
                    String(name).replace(/_/g, " "),
                  ]}
                />
                <Legend formatter={(val) => String(val).replace(/_/g, " ")} />
                {activeStrategies.map((name) => (
                  <Line
                    key={name}
                    type="monotone"
                    dataKey={name}
                    stroke={STRATEGY_COLORS[name] || "hsl(var(--primary))"}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                    isAnimationActive={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Position table: cost vs real-time price */}
        {hasPositions ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2 pr-3 font-medium">Strategy</th>
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
                {data.positions.map((pos, i) => (
                  <PositionRow key={`${pos.strategy}-${pos.ticker}-${i}`} pos={pos} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          !loading && (
            <p className="text-xs text-muted-foreground">
              No open positions across all strategies.
            </p>
          )
        )}
      </CardContent>
    </Card>
  );
}

function StrategyCard({ strat }: { strat: ReturnType<typeof useStrategies>["data"]["strategies"][0] }) {
  const winPct = (strat.win_rate * 100).toFixed(0);
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
            <PnlText val={strat.unrealized_pnl} className="text-base font-bold" />
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
            <th className="pb-2 font-medium">Opened</th>
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
              <td className="py-2 text-muted-foreground">
                {t.opened_at ? new Date(t.opened_at).toLocaleDateString() : "—"}
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
            {strategies.map((s) => <StrategyCard key={s.name} strat={s} />)}
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
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-primary" />
                  Trade History
                </CardTitle>
                <div className="flex gap-1">
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
