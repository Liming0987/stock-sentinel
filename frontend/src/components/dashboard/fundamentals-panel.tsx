"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GradeBadge } from "@/components/dashboard/grade-badge";
import type { FundamentalsData } from "@/lib/hooks";

interface Props {
  data: FundamentalsData;
}

function fmtPct(val: number | null | undefined): string {
  if (val == null) return "—";
  return `${(val * 100).toFixed(1)}%`;
}

function fmtRaw(val: number | null | undefined, decimals = 2): string {
  if (val == null) return "—";
  return val.toFixed(decimals);
}

const PILLAR_LABELS: Record<string, string> = {
  valuation: "Valuation",
  profitability: "Profitability",
  growth: "Growth",
  health: "Health",
  analyst: "Analyst",
};

function pillarColor(score: number): string {
  if (score >= 0.65) return "var(--bullish)";
  if (score >= 0.40) return "hsl(50 100% 50%)";
  return "var(--bearish)";
}

export function FundamentalsPanel({ data }: Props) {
  const isEmpty = data.grade === "N/A" && Object.keys(data.metrics).length === 0;

  const pillarData = Object.entries(data.pillars).map(([key, val]) => ({
    name: PILLAR_LABELS[key] ?? key,
    score: Math.round(val * 100),
    raw: val,
  }));

  const m = data.metrics;

  const metricRows = [
    { label: "P/E (TTM)", value: fmtRaw(m.trailingPE) },
    { label: "Forward P/E", value: fmtRaw(m.forwardPE) },
    { label: "P/B", value: fmtRaw(m.priceToBook) },
    { label: "P/S (TTM)", value: fmtRaw(m.priceToSalesTrailing12Months) },
    { label: "PEG", value: fmtRaw(m.pegRatio) },
    { label: "Net Margin", value: fmtPct(m.profitMargins) },
    { label: "Op. Margin", value: fmtPct(m.operatingMargins) },
    { label: "ROE", value: fmtPct(m.returnOnEquity) },
    { label: "Rev Growth", value: fmtPct(m.revenueGrowth) },
    { label: "EPS Growth", value: fmtPct(m.earningsGrowth) },
    { label: "Debt/Equity", value: fmtRaw(m.debtToEquity) },
    { label: "Current Ratio", value: fmtRaw(m.currentRatio) },
    { label: "Analyst Target", value: m.targetMeanPrice != null ? `$${fmtRaw(m.targetMeanPrice)}` : "—" },
    { label: "# Analysts", value: m.numberOfAnalystOpinions != null ? String(Math.round(m.numberOfAnalystOpinions)) : "—" },
    {
      label: "Upside to Target",
      value:
        m.targetMeanPrice != null && m.currentPrice != null && m.currentPrice > 0
          ? fmtPct((m.targetMeanPrice - m.currentPrice) / m.currentPrice)
          : "—",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Fundamental Analysis
          {!isEmpty && (
            <span className="flex items-center gap-1.5 ml-1">
              <GradeBadge grade={data.grade} />
              {data.score != null && (
                <span className="text-sm font-normal text-muted-foreground">
                  {(data.score * 100).toFixed(0)}/100
                </span>
              )}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {isEmpty ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-10 rounded-md bg-muted/40 animate-pulse" />
            ))}
          </div>
        ) : (
          <>
            {pillarData.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">Pillar Scores</p>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={pillarData}
                      layout="vertical"
                      margin={{ top: 0, right: 40, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
                      <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} tickFormatter={(v) => `${v}`} />
                      <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
                      <Tooltip
                        formatter={(v) => [`${Number(v)}%`, "Score"]}
                        contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: "8px", fontSize: "12px" }}
                      />
                      <Bar dataKey="score" radius={[0, 3, 3, 0]} maxBarSize={20}>
                        {pillarData.map((entry, idx) => (
                          <Cell key={idx} fill={pillarColor(entry.raw)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">Key Metrics</p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {metricRows.map(({ label, value }) => (
                  <div key={label} className="rounded-md border px-3 py-2">
                    <p className="text-[10px] text-muted-foreground">{label}</p>
                    <p className="text-sm font-semibold font-mono">{value}</p>
                  </div>
                ))}
              </div>
            </div>

            {data.flags.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">Flags</p>
                <div className="flex flex-wrap gap-2">
                  {data.flags.map((flag) => (
                    <Badge key={flag} variant="bearish">{flag}</Badge>
                  ))}
                </div>
              </div>
            )}

            {data.next_earnings && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1 uppercase tracking-wide">Next Earnings</p>
                <p className="text-sm font-semibold">
                  {new Date(data.next_earnings).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}
                </p>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
