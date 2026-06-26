"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DCFResult, DCFScenario } from "@/lib/hooks";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtB(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1e9) return `${n < 0 ? "-" : ""}$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${n < 0 ? "-" : ""}$${(abs / 1e6).toFixed(0)}M`;
  return `$${n.toFixed(0)}`;
}

function fmtPct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

function fmtShares(n: number): string {
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  return n.toFixed(0);
}

// ── Margin-of-safety gauge ────────────────────────────────────────────────────

function MoSGauge({ mos, current, iv }: { mos: number; current: number; iv: number }) {
  const overvalued = mos < 0;
  const clampedPct = Math.min(Math.abs(mos), 100);
  const color = overvalued ? "#ef4444" : "#22c55e";
  const label = overvalued
    ? `${Math.abs(mos).toFixed(1)}% overvalued`
    : `${mos.toFixed(1)}% margin of safety`;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Current <span className="font-mono font-semibold text-foreground">${current.toFixed(2)}</span></span>
        <span>Intrinsic <span className="font-mono font-semibold text-foreground">${iv.toFixed(2)}</span></span>
      </div>
      <div className="relative h-3 w-full rounded-full bg-muted overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all"
          style={{ width: `${clampedPct}%`, background: color }}
        />
      </div>
      <p className="text-xs text-center font-medium" style={{ color }}>{label}</p>
    </div>
  );
}

// ── Scenario column ───────────────────────────────────────────────────────────

function ScenarioCol({ label, s }: { label: string; s: DCFScenario | null | undefined; current: number }) {
  if (!s) return (
    <div className="flex flex-col items-center gap-1">
      <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">{label}</p>
      <p className="text-muted-foreground text-xs">—</p>
    </div>
  );
  const up = s.upside_pct != null && s.upside_pct >= 0;
  return (
    <div className="flex flex-col items-center gap-1 rounded-lg border p-3">
      <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">{label}</p>
      <p className="text-lg font-bold font-mono">${s.intrinsic_value.toFixed(2)}</p>
      {s.upside_pct != null && (
        <p className={`text-xs font-semibold ${up ? "text-bullish" : "text-bearish"}`}>
          {up ? "+" : ""}{s.upside_pct.toFixed(1)}%
        </p>
      )}
      <div className="mt-1 space-y-0.5 text-center text-[10px] text-muted-foreground">
        <p>Growth {fmtPct(s.growth_rate)}</p>
        <p>Discount {fmtPct(s.discount_rate)}</p>
      </div>
    </div>
  );
}

// ── Sensitivity table ─────────────────────────────────────────────────────────

function SensitivityTable({ cells, current }: { cells: DCFResult["sensitivity"]; current: number }) {
  if (!cells?.length) return null;

  const discountRates = Array.from(new Set(cells.map(c => c.discount_rate))).sort((a, b) => a - b);
  const terminalGrowths = Array.from(new Set(cells.map(c => c.terminal_growth))).sort((a, b) => a - b);

  const get = (r: number, g: number) =>
    cells.find(c => c.discount_rate === r && c.terminal_growth === g)?.intrinsic_value ?? null;

  const cellColor = (iv: number | null) => {
    if (iv == null) return "text-muted-foreground";
    const mos = (iv - current) / iv;
    if (mos >= 0.15) return "text-bullish font-semibold";
    if (mos >= 0) return "text-bullish/70";
    if (mos >= -0.20) return "text-muted-foreground";
    return "text-bearish";
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="px-2 py-1.5 text-left text-muted-foreground font-medium">
              Discount ↓ / Terminal →
            </th>
            {terminalGrowths.map(g => (
              <th key={g} className="px-3 py-1.5 text-center text-muted-foreground font-medium">
                {fmtPct(g)} TV growth
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {discountRates.map(r => (
            <tr key={r} className="border-t">
              <td className="px-2 py-1.5 text-muted-foreground">{fmtPct(r)} discount</td>
              {terminalGrowths.map(g => {
                const iv = get(r, g);
                return (
                  <td key={g} className={`px-3 py-1.5 text-center font-mono ${cellColor(iv)}`}>
                    {iv != null ? `$${iv.toFixed(0)}` : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-1 text-[10px] text-muted-foreground">
        Green = ≥15% margin of safety vs ${current.toFixed(2)}. Red = ≥20% overvalued.
      </p>
    </div>
  );
}

// ── Projected cashflows ───────────────────────────────────────────────────────

function CashflowTable({ rows }: { rows: DCFResult["projected_cashflows"] }) {
  if (!rows?.length) return null;
  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="border-b">
          <th className="px-2 py-1.5 text-left text-muted-foreground font-medium">Year</th>
          <th className="px-2 py-1.5 text-right text-muted-foreground font-medium">FCF</th>
          <th className="px-2 py-1.5 text-right text-muted-foreground font-medium">PV</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className={`border-t ${r.year === "TV" ? "bg-muted/30 font-semibold" : ""}`}>
            <td className="px-2 py-1 font-mono">{r.year === "TV" ? "Terminal" : `Y${r.year}`}</td>
            <td className="px-2 py-1 font-mono text-right">{fmtB(r.fcf)}</td>
            <td className="px-2 py-1 font-mono text-right text-muted-foreground">{fmtB(r.pv)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ── Main card ─────────────────────────────────────────────────────────────────

interface Props {
  data: DCFResult;
  loading: boolean;
}

export function DCFCard({ data, loading }: Props) {
  const [showCashflows, setShowCashflows] = useState(false);
  const [showAssumptions, setShowAssumptions] = useState(false);

  if (loading) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">DCF Valuation</CardTitle></CardHeader>
        <CardContent><div className="h-32 animate-pulse rounded bg-muted" /></CardContent>
      </Card>
    );
  }

  if (!data.feasible) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">DCF Valuation</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{data.reason ?? "DCF not available."}</p>
        </CardContent>
      </Card>
    );
  }

  const { current_price, base_intrinsic_value, margin_of_safety_pct, inputs, scenarios, sensitivity, projected_cashflows } = data;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">DCF Valuation</CardTitle>
          {data.inputs && (
            <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
              data.inputs.growth_outlook === "forward"
                ? "bg-bullish/15 text-bullish border border-bullish/30"
                : "bg-amber-500/15 text-amber-400 border border-amber-500/30"
            }`}>
              {data.inputs.growth_outlook === "forward" ? "▲ Forward-looking" : "◀ Historical"}
            </span>
          )}
        </div>
        <p className="text-[11px] text-muted-foreground">
          10-year FCF projection · Gordon Growth terminal value · CAPM discount rate
          {data.inputs?.beta_multiplier && data.inputs.beta_multiplier > 1 && (
            <> · {data.inputs.beta_multiplier}× beta ({data.inputs.sector})</>
          )}
        </p>
      </CardHeader>
      <CardContent className="space-y-5">

        {/* Gauge */}
        {current_price != null && base_intrinsic_value != null && margin_of_safety_pct != null && (
          <MoSGauge mos={margin_of_safety_pct} current={current_price} iv={base_intrinsic_value} />
        )}

        {/* Three scenarios */}
        {scenarios && (
          <div className="grid grid-cols-3 gap-3">
            <ScenarioCol label="Bear" s={scenarios.bear} current={current_price ?? 0} />
            <ScenarioCol label="Base" s={scenarios.base} current={current_price ?? 0} />
            <ScenarioCol label="Bull" s={scenarios.bull} current={current_price ?? 0} />
          </div>
        )}

        {/* Sensitivity table */}
        {sensitivity && (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Sensitivity — Intrinsic Value per Share
            </p>
            <SensitivityTable cells={sensitivity} current={current_price ?? 0} />
          </div>
        )}

        {/* Assumptions toggle */}
        {inputs && (
          <div>
            <button
              onClick={() => setShowAssumptions(v => !v)}
              className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
            >
              {showAssumptions ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {showAssumptions ? "Hide" : "Show"} assumptions
            </button>
            {showAssumptions && (
              <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1.5 rounded-lg border bg-muted/30 p-3 text-xs sm:grid-cols-3">
                <div><p className="text-muted-foreground">TTM Free Cash Flow</p><p className="font-mono font-medium">{fmtB(inputs.fcf_ttm)}</p></div>
                <div><p className="text-muted-foreground">Net Debt</p><p className="font-mono font-medium">{fmtB(inputs.net_debt)}</p></div>
                <div><p className="text-muted-foreground">Shares Outstanding</p><p className="font-mono font-medium">{fmtShares(inputs.shares_outstanding)}</p></div>
                <div>
                  <p className="text-muted-foreground">Base Growth Rate</p>
                  <p className="font-mono font-medium">{fmtPct(inputs.growth_rate)}</p>
                  <p className="text-[10px] text-muted-foreground">{inputs.growth_rate_source}</p>
                  <span className={`inline-block mt-0.5 rounded px-1 text-[9px] font-semibold ${
                    inputs.growth_outlook === "forward"
                      ? "bg-bullish/15 text-bullish"
                      : "bg-amber-500/15 text-amber-400"
                  }`}>
                    {inputs.growth_outlook === "forward" ? "▲ Forward-looking" : "◀ Historical"}
                  </span>
                </div>
                <div>
                  <p className="text-muted-foreground">Discount Rate</p>
                  <p className="font-mono font-medium">{fmtPct(inputs.discount_rate)}</p>
                  <p className="text-[10px] text-muted-foreground">{inputs.discount_rate_note}</p>
                  {inputs.beta_multiplier > 1 && (
                    <p className="text-[10px] text-amber-400">
                      Raw β {inputs.beta_raw.toFixed(2)} × {inputs.beta_multiplier}× multiplier
                    </p>
                  )}
                </div>
                <div><p className="text-muted-foreground">Terminal Growth</p><p className="font-mono font-medium">{fmtPct(inputs.terminal_growth_rate)}</p></div>
              </div>
            )}
          </div>
        )}

        {/* Cashflow table toggle */}
        {projected_cashflows && (
          <div>
            <button
              onClick={() => setShowCashflows(v => !v)}
              className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
            >
              {showCashflows ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {showCashflows ? "Hide" : "Show"} projected cash flows
            </button>
            {showCashflows && (
              <div className="mt-2">
                <CashflowTable rows={projected_cashflows} />
              </div>
            )}
          </div>
        )}

        <p className="text-[10px] text-muted-foreground border-t pt-3">
          DCF is highly sensitive to growth and discount rate assumptions. Small changes compound
          significantly over a 10-year horizon. Use as a directional sanity check, not a price target.
        </p>
      </CardContent>
    </Card>
  );
}
