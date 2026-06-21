"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { FundamentalsData } from "@/lib/hooks";

// ── helpers ──────────────────────────────────────────────────────────────────

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function fmtNum(v: number | null | undefined, decimals = 1): string {
  if (v == null) return "—";
  return v.toFixed(decimals);
}

function fmtBillions(v: number | null | undefined): string {
  if (v == null) return "—";
  const b = v / 1e9;
  return b >= 1 ? `$${b.toFixed(1)}B` : `$${(v / 1e6).toFixed(0)}M`;
}

function pillarColor(score: number): string {
  if (score >= 0.75) return "bg-green-500";
  if (score >= 0.50) return "bg-amber-500";
  return "bg-red-500";
}

function gradeColor(grade: string): string {
  if (grade === "A") return "bg-green-500/15 text-green-400 border-green-500/30";
  if (grade === "B") return "bg-blue-500/15 text-blue-400 border-blue-500/30";
  if (grade === "C") return "bg-amber-500/15 text-amber-400 border-amber-500/30";
  if (grade === "D") return "bg-orange-500/15 text-orange-400 border-orange-500/30";
  return "bg-red-500/15 text-red-400 border-red-500/30";
}

function MetricRow({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="text-right">
        <span className="text-xs font-medium">{value}</span>
        {sub && <span className="ml-1.5 text-[10px] text-muted-foreground">{sub}</span>}
      </div>
    </div>
  );
}

function PillarBar({ label, score }: { label: string; score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="capitalize text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">{pct}</span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${pillarColor(score)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ── main component ───────────────────────────────────────────────────────────

interface FundamentalsCardProps {
  data: FundamentalsData;
  loading: boolean;
}

export function FundamentalsCard({ data, loading }: FundamentalsCardProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Fundamental Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-48 w-full animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    );
  }

  const m = data.metrics ?? {};
  const pillars = data.pillars ?? {};
  const hasData = data.score != null;

  // analyst upside
  const current = m.currentPrice as number | null;
  const target = m.targetMeanPrice as number | null;
  const upside = current && target ? (target - current) / current : null;

  // next earnings
  const nextEarnings = data.next_earnings
    ? new Date(data.next_earnings).toLocaleDateString("en-US", { month: "short", day: "numeric" })
    : null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-base">Fundamental Analysis</CardTitle>
          {nextEarnings && (
            <span className="shrink-0 rounded-full border px-2 py-0.5 text-[10px] text-muted-foreground">
              Earnings {nextEarnings}
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        {!hasData ? (
          <p className="text-sm text-muted-foreground">No fundamental data available.</p>
        ) : (
          <>
            {/* Grade + score row */}
            <div className="flex items-center gap-4">
              <span
                className={`inline-flex items-center justify-center rounded-lg border px-4 py-2 text-2xl font-bold leading-none ${gradeColor(data.grade)}`}
              >
                {data.grade}
              </span>
              <div>
                <p className="text-2xl font-bold tabular-nums">
                  {Math.round((data.score ?? 0) * 100)}
                  <span className="ml-0.5 text-sm font-normal text-muted-foreground">/100</span>
                </p>
                <p className="text-xs text-muted-foreground">Composite score</p>
              </div>
              {data.flags.length > 0 && (
                <div className="ml-auto flex flex-wrap gap-1 justify-end">
                  {data.flags.map((f) => (
                    <Badge key={f} variant="destructive" className="text-[10px] py-0">
                      {f}
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Pillar bars */}
            <div className="space-y-2">
              {(["valuation", "profitability", "growth", "health", "analyst"] as const).map((key) =>
                pillars[key] != null ? (
                  <PillarBar key={key} label={key} score={pillars[key]} />
                ) : null
              )}
            </div>

            {/* Metrics grid — 2 columns */}
            <div className="grid grid-cols-1 gap-x-6 sm:grid-cols-2">
              {/* Valuation */}
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/60">
                  Valuation
                </p>
                <MetricRow label="Trailing P/E" value={fmtNum(m.trailingPE as number)} />
                <MetricRow label="Forward P/E" value={fmtNum(m.forwardPE as number)} />
                <MetricRow label="PEG" value={fmtNum(m.pegRatio as number, 2)} />
                <MetricRow label="P/S (TTM)" value={fmtNum(m.priceToSalesTrailing12Months as number, 2)} />
                <MetricRow label="EV/EBITDA" value={fmtNum(m.enterpriseToEbitda as number, 1)} />
              </div>

              {/* Profitability */}
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/60">
                  Profitability
                </p>
                <MetricRow label="Net Margin" value={fmtPct(m.profitMargins as number)} />
                <MetricRow label="Op. Margin" value={fmtPct(m.operatingMargins as number)} />
                <MetricRow label="ROE" value={fmtPct(m.returnOnEquity as number)} />
                <MetricRow label="ROA" value={fmtPct(m.returnOnAssets as number)} />
                <MetricRow label="Free Cash Flow" value={fmtBillions(m.freeCashflow as number)} />
              </div>

              {/* Growth */}
              <div className="mt-3">
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/60">
                  Growth
                </p>
                <MetricRow label="Revenue Growth" value={fmtPct(m.revenueGrowth as number)} />
                <MetricRow label="Earnings Growth" value={fmtPct(m.earningsGrowth as number)} />
                <MetricRow label="QoQ Earnings" value={fmtPct(m.earningsQuarterlyGrowth as number)} />
              </div>

              {/* Health + Analyst */}
              <div className="mt-3">
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/60">
                  Health
                </p>
                <MetricRow label="Debt / Equity" value={fmtNum(m.debtToEquity as number, 1)} />
                <MetricRow label="Current Ratio" value={fmtNum(m.currentRatio as number, 2)} />
                {target != null && (
                  <>
                    <p className="mb-1 mt-3 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/60">
                      Analyst
                    </p>
                    <MetricRow
                      label="Price Target"
                      value={`$${fmtNum(target, 2)}`}
                      sub={
                        upside != null
                          ? upside >= 0
                            ? `+${fmtPct(upside)} upside`
                            : `${fmtPct(upside)} downside`
                          : undefined
                      }
                    />
                    <MetricRow
                      label="Rating Mean"
                      value={fmtNum(m.recommendationMean as number, 1)}
                      sub={`${m.numberOfAnalystOpinions ?? "—"} analysts`}
                    />
                  </>
                )}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
