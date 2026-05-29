"use client";

import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { DollarSign, Activity } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useStrategies, useStrategyTrades, useEquityCurve, useAlpacaAccount } from "@/lib/hooks";

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

  // Merge all dates across strategies for the chart x-axis
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
                        formatter={(val: number) => [`$${val.toFixed(2)}`, ""]}
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
