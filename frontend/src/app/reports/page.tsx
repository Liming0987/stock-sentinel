"use client";

import { useDailyReports, useLatestReport } from "@/lib/hooks";
import { BarChart3, TrendingUp, TrendingDown, Zap } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function pnlColor(val: number | null | undefined): string {
  if (val == null) return "text-muted-foreground";
  return val >= 0 ? "text-green-500" : "text-red-500";
}

function fmtPnl(val: number | null | undefined): string {
  if (val == null) return "—";
  return `${val >= 0 ? "+" : ""}$${val.toFixed(2)}`;
}

function fmtPct(wins: number | null, total: number | null): string {
  if (!total) return "—";
  return `${((wins ?? 0) / total * 100).toFixed(1)}%`;
}

export default function ReportsPage() {
  const { data: reportsData, loading: reportsLoading } = useDailyReports(30);
  const { data: latestData, loading: latestLoading } = useLatestReport();

  const latest = latestData?.report ?? null;
  const reports = reportsData?.reports ?? [];

  // Chart data — oldest first for the line chart
  const chartData = [...reports].reverse().map((r) => ({
    date: r.report_date ?? "",
    pnl: r.total_pnl ?? 0,
  }));

  const loading = reportsLoading || latestLoading;

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <BarChart3 className="h-7 w-7 text-primary" />
        <h1 className="text-2xl font-bold">Daily Performance Reports</h1>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Total P&L */}
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Latest Day P&amp;L
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <span className="text-muted-foreground">Loading…</span>
            ) : (
              <span className={`text-2xl font-bold ${pnlColor(latest?.total_pnl)}`}>
                {fmtPnl(latest?.total_pnl)}
              </span>
            )}
          </CardContent>
        </Card>

        {/* Win rate */}
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Win Rate (today)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <span className="text-muted-foreground">Loading…</span>
            ) : (
              <span className="text-2xl font-bold">
                {fmtPct(latest?.winning_trades ?? null, latest?.total_trades ?? null)}
              </span>
            )}
            {latest?.total_trades != null && (
              <p className="mt-1 text-xs text-muted-foreground">
                {latest.winning_trades ?? 0} / {latest.total_trades} trades
              </p>
            )}
          </CardContent>
        </Card>

        {/* Signals generated */}
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <Zap className="h-4 w-4" /> Signals Today
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <span className="text-muted-foreground">Loading…</span>
            ) : (
              <span className="text-2xl font-bold">
                {latest?.signals_generated ?? "—"}
              </span>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Line chart */}
      {!loading && chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">30-Day P&amp;L Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: string) => v.slice(5)}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: number) => `$${v.toFixed(0)}`}
                />
                <Tooltip
                  formatter={(val) => [`$${Number(val).toFixed(2)}`, "P&L"]}
                  labelFormatter={(label) => `Date: ${label}`}
                />
                <Line
                  type="monotone"
                  dataKey="pnl"
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Past reports list */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Past Reports</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <p className="p-6 text-muted-foreground">Loading…</p>
          ) : reports.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-center text-muted-foreground">
              <BarChart3 className="h-10 w-10 opacity-30" />
              <p className="font-medium">No reports yet.</p>
              <p className="text-sm">
                Reports are generated daily after market close (5pm ET).
              </p>
            </div>
          ) : (
            <div className="divide-y">
              {reports.map((r) => {
                const winRate = r.total_trades
                  ? ((r.winning_trades ?? 0) / r.total_trades * 100).toFixed(1)
                  : null;
                return (
                  <div
                    key={r.id}
                    className="flex flex-col gap-1 px-6 py-3 sm:flex-row sm:items-center sm:gap-6"
                  >
                    <span className="w-28 shrink-0 font-mono text-sm text-muted-foreground">
                      {r.report_date ?? "—"}
                    </span>
                    <span className={`w-24 shrink-0 font-semibold ${pnlColor(r.total_pnl)}`}>
                      {fmtPnl(r.total_pnl)}
                    </span>
                    <span className="w-20 shrink-0 text-sm text-muted-foreground">
                      {r.total_trades ?? 0} trades
                    </span>
                    <span className="w-16 shrink-0 text-sm">
                      {winRate != null ? `${winRate}% WR` : "—"}
                    </span>
                    <div className="flex items-center gap-2 text-sm">
                      {r.best_strategy && (
                        <>
                          <TrendingUp className="h-3.5 w-3.5 text-green-500" />
                          <Badge variant="outline" className="text-green-600">
                            {r.best_strategy}
                          </Badge>
                        </>
                      )}
                      {r.worst_strategy && r.worst_strategy !== r.best_strategy && (
                        <>
                          <TrendingDown className="h-3.5 w-3.5 text-red-400" />
                          <Badge variant="outline" className="text-red-500">
                            {r.worst_strategy}
                          </Badge>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
