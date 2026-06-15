"use client";

import { useState, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import {
  FlaskConical, Play, X, Plus, TrendingUp, TrendingDown,
  BarChart2, Trophy, AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/page-header";

// ── Types ──────────────────────────────────────────────────────────────────
interface StrategyMeta { name: string; description: string }
interface Trade {
  ticker: string; entry_date: string; exit_date: string | null;
  entry_price: number; exit_price: number | null;
  qty: number; pnl: number; return_pct: number;
  exit_reason: string; reasoning: string;
}
interface Metrics {
  total_pnl: number; total_return_pct: number; num_trades: number;
  win_rate: number; max_drawdown: number; sharpe_ratio: number | null;
  avg_win: number; avg_loss: number; profit_factor: number | null;
}
interface BacktestResult {
  strategy: string; tickers: string[]; start_date: string; end_date: string;
  metrics: Metrics; equity_curve: { date: string; equity: number }[];
  trades: Trade[];
}

// ── Constants ──────────────────────────────────────────────────────────────
const PERIOD_PRESETS = [
  { label: "1 mo",  days: 30  },
  { label: "3 mo",  days: 90  },
  { label: "6 mo",  days: 180 },
  { label: "1 yr",  days: 365 },
  { label: "2 yr",  days: 730 },
];

const TICKER_PRESETS: { label: string; tickers: string[] }[] = [
  { label: "Mag 7",    tickers: ["AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA"] },
  { label: "Finance",  tickers: ["JPM","GS","BAC","WFC","MS","C","BLK"] },
  { label: "Energy",   tickers: ["XOM","CVX","COP","OXY","SLB","PSX","VLO"] },
  { label: "Meme",     tickers: ["GME","AMC","BBBY","PLTR","SOFI","RIVN","LCID"] },
];

function toDateStr(d: Date) {
  return d.toISOString().slice(0, 10);
}

// ── Metric card ────────────────────────────────────────────────────────────
function MetricCard({
  label, value, sub, positive, icon: Icon,
}: {
  label: string; value: string; sub?: string;
  positive?: boolean; icon: React.ElementType;
}) {
  const color = positive === undefined
    ? "text-foreground"
    : positive ? "text-bullish" : "text-bearish";
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <p className="text-xs text-muted-foreground">{label}</p>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
        <p className={`mt-1 text-xl font-bold font-mono ${color}`}>{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────
export default function BacktestPage() {
  const [strategies, setStrategies] = useState<StrategyMeta[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [tickers, setTickers] = useState<string[]>(["AAPL", "MSFT", "NVDA"]);
  const [tickerInput, setTickerInput] = useState("");
  const [periodPreset, setPeriodPreset] = useState(2); // 6 mo default
  const [startDate, setStartDate] = useState(() =>
    toDateStr(new Date(Date.now() - 180 * 86400000))
  );
  const [endDate, setEndDate] = useState(() => toDateStr(new Date()));
  const [useCustomDates, setUseCustomDates] = useState(false);

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (api.backtest.strategies() as Promise<{ strategies: StrategyMeta[] }>).then((res) => {
      setStrategies(res.strategies);
      if (res.strategies.length > 0) setSelectedStrategy(res.strategies[0].name);
    }).catch(() => {});
  }, []);

  const applyPreset = (idx: number) => {
    setPeriodPreset(idx);
    setUseCustomDates(false);
    const days = PERIOD_PRESETS[idx].days;
    setStartDate(toDateStr(new Date(Date.now() - days * 86400000)));
    setEndDate(toDateStr(new Date()));
  };

  const addTicker = () => {
    const t = tickerInput.trim().toUpperCase();
    if (t && !tickers.includes(t) && tickers.length < 20) {
      setTickers([...tickers, t]);
    }
    setTickerInput("");
  };

  const removeTicker = (t: string) => setTickers(tickers.filter((x) => x !== t));

  const applyTickerPreset = (preset: typeof TICKER_PRESETS[0]) => {
    const merged = Array.from(new Set([...tickers, ...preset.tickers])).slice(0, 20);
    setTickers(merged);
  };

  const handleRun = async () => {
    if (!selectedStrategy || tickers.length === 0) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.backtest.run({
        strategy: selectedStrategy,
        tickers,
        start_date: startDate,
        end_date: endDate,
      });
      if (res.detail) throw new Error(res.detail);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Backtest failed");
    } finally {
      setRunning(false);
    }
  };

  const pct = (v: number) => `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)}%`;
  const usd = (v: number) => `${v >= 0 ? "+" : ""}$${Math.abs(v).toFixed(2)}`;

  return (
    <div className="mx-auto max-w-[1180px] space-y-[18px]">
      <PageHeader
        kicker="Research"
        title="Backtest"
        description="Replay any strategy against historical prices to see how it would have performed — no live orders, just the lesson."
      />

      {/* ── Configuration card ─────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">

          {/* Strategy */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Strategy</label>
            <div className="flex flex-wrap gap-2">
              {strategies.map((s) => (
                <button
                  key={s.name}
                  onClick={() => setSelectedStrategy(s.name)}
                  className={`rounded-md border px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                    selectedStrategy === s.name
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground"
                  }`}
                  title={s.description}
                >
                  {s.name.replace(/_/g, " ")}
                </button>
              ))}
            </div>
            {selectedStrategy && (
              <p className="text-xs text-muted-foreground">
                {strategies.find((s) => s.name === selectedStrategy)?.description}
              </p>
            )}
          </div>

          {/* Period */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Time Period</label>
            <div className="flex flex-wrap gap-2">
              {PERIOD_PRESETS.map((p, i) => (
                <button
                  key={p.label}
                  onClick={() => applyPreset(i)}
                  className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
                    !useCustomDates && periodPreset === i
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground"
                  }`}
                >
                  {p.label}
                </button>
              ))}
              <button
                onClick={() => setUseCustomDates(true)}
                className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
                  useCustomDates
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground"
                }`}
              >
                Custom
              </button>
            </div>
            {useCustomDates && (
              <div className="flex flex-wrap gap-3 mt-2">
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Start</label>
                  <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
                    className="h-8 rounded-md border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">End</label>
                  <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
                    className="h-8 rounded-md border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring" />
                </div>
              </div>
            )}
            {!useCustomDates && (
              <p className="text-xs text-muted-foreground">{startDate} → {endDate}</p>
            )}
          </div>

          {/* Stocks */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Stocks</label>

            {/* Presets */}
            <div className="flex flex-wrap gap-1.5">
              <span className="text-xs text-muted-foreground self-center">Quick add:</span>
              {TICKER_PRESETS.map((p) => (
                <button key={p.label} onClick={() => applyTickerPreset(p)}
                  className="rounded border px-2 py-0.5 text-xs text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors">
                  {p.label}
                </button>
              ))}
            </div>

            {/* Ticker chips */}
            <div className="flex flex-wrap gap-1.5 min-h-8">
              {tickers.map((t) => (
                <span key={t} className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
                  {t}
                  <button onClick={() => removeTicker(t)} className="hover:text-destructive">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>

            {/* Add ticker input */}
            <div className="flex gap-2">
              <input
                value={tickerInput}
                onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
                onKeyDown={(e) => { if (e.key === "Enter") addTicker(); }}
                placeholder="Add ticker (e.g. TSLA)"
                className="h-8 w-40 rounded-md border bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
              />
              <Button size="sm" variant="outline" onClick={addTicker} className="h-8 text-xs">
                <Plus className="h-3 w-3 mr-1" /> Add
              </Button>
              {tickers.length > 0 && (
                <button onClick={() => setTickers([])} className="text-xs text-muted-foreground hover:text-destructive">
                  Clear all
                </button>
              )}
            </div>
            <p className="text-xs text-muted-foreground">{tickers.length}/20 stocks selected</p>
          </div>

          {/* Run button */}
          <Button
            onClick={handleRun}
            disabled={running || !selectedStrategy || tickers.length === 0}
            className="w-full sm:w-auto"
          >
            {running ? (
              <>
                <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Running backtest…
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Backtest
              </>
            )}
          </Button>

          {error && (
            <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Results ──────────────────────────────────────────────────────── */}
      {result && (
        <div className="space-y-4">
          {/* Summary header */}
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">Results</h2>
            <Badge variant="secondary" className="capitalize text-xs">
              {result.strategy.replace(/_/g, " ")}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {result.start_date} → {result.end_date}
            </span>
          </div>

          {/* Metric cards */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <MetricCard
              label="Total P&L"
              value={usd(result.metrics.total_pnl)}
              sub={pct(result.metrics.total_return_pct) + " return"}
              positive={result.metrics.total_pnl >= 0}
              icon={result.metrics.total_pnl >= 0 ? TrendingUp : TrendingDown}
            />
            <MetricCard
              label="Win Rate"
              value={`${(result.metrics.win_rate * 100).toFixed(0)}%`}
              sub={`${result.metrics.num_trades} trades`}
              positive={result.metrics.win_rate >= 0.5}
              icon={Trophy}
            />
            <MetricCard
              label="Max Drawdown"
              value={pct(result.metrics.max_drawdown)}
              positive={false}
              icon={AlertTriangle}
            />
            <MetricCard
              label="Sharpe Ratio"
              value={result.metrics.sharpe_ratio !== null ? result.metrics.sharpe_ratio.toFixed(2) : "—"}
              sub={result.metrics.profit_factor !== null ? `PF ${result.metrics.profit_factor.toFixed(2)}` : undefined}
              positive={result.metrics.sharpe_ratio !== null ? result.metrics.sharpe_ratio > 1 : undefined}
              icon={BarChart2}
            />
          </div>

          {/* Equity curve */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Equity Curve</CardTitle>
            </CardHeader>
            <CardContent>
              {result.equity_curve.length < 2 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  Not enough data points to draw curve — no trades were triggered in this period.
                </p>
              ) : (
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={result.equity_curve} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                        tickFormatter={(v) => v.slice(5)}
                        interval="preserveStartEnd"
                      />
                      <YAxis
                        tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                        tickFormatter={(v) => `$${v}`}
                        width={50}
                      />
                      <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="4 4" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                          fontSize: "12px",
                        }}
                        formatter={(v) => [`$${Number(v).toFixed(2)}`, "P&L"]}
                        labelFormatter={(l) => `Date: ${l}`}
                      />
                      <Line
                        type="monotone"
                        dataKey="equity"
                        stroke={result.metrics.total_pnl >= 0 ? "hsl(142, 71%, 45%)" : "hsl(0, 84%, 60%)"}
                        strokeWidth={2}
                        dot={false}
                        isAnimationActive={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Trade table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Trade History
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  {result.trades.length} trade{result.trades.length !== 1 ? "s" : ""}
                  {" · "}{result.trades.filter((t) => t.pnl > 0).length}W /
                  {" "}{result.trades.filter((t) => t.pnl <= 0).length}L
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {result.trades.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4">
                  No trades were triggered in this period. Try a longer window or different stocks.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs sm:text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="pb-2 pr-3 font-medium">Ticker</th>
                        <th className="pb-2 pr-3 font-medium">Entry date</th>
                        <th className="pb-2 pr-3 font-medium">Exit date</th>
                        <th className="pb-2 pr-3 font-medium">Entry $</th>
                        <th className="pb-2 pr-3 font-medium">Exit $</th>
                        <th className="pb-2 pr-3 font-medium">P&L</th>
                        <th className="pb-2 pr-3 font-medium">Return</th>
                        <th className="pb-2 font-medium">Exit reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.trades.map((t, i) => (
                        <tr key={i} className="border-b last:border-0 hover:bg-accent/30">
                          <td className="py-2 pr-3 font-semibold">{t.ticker}</td>
                          <td className="py-2 pr-3 font-mono text-muted-foreground">{t.entry_date}</td>
                          <td className="py-2 pr-3 font-mono text-muted-foreground">{t.exit_date ?? "—"}</td>
                          <td className="py-2 pr-3 font-mono">${t.entry_price.toFixed(2)}</td>
                          <td className="py-2 pr-3 font-mono">{t.exit_price != null ? `$${t.exit_price.toFixed(2)}` : "—"}</td>
                          <td className="py-2 pr-3 font-mono">
                            <span className={t.pnl >= 0 ? "text-bullish" : "text-bearish"}>
                              {t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}
                            </span>
                          </td>
                          <td className="py-2 pr-3 font-mono">
                            <span className={t.return_pct >= 0 ? "text-bullish" : "text-bearish"}>
                              {(t.return_pct * 100).toFixed(2)}%
                            </span>
                          </td>
                          <td className="py-2 text-muted-foreground text-xs">
                            {t.exit_reason.replace(/_/g, " ")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
