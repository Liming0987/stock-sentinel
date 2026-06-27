"use client";

import { ArrowUpRight, ArrowDownRight, MessageSquare, TrendingUp, DollarSign, BarChart2, AlertTriangle, Newspaper, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { StockAnalysis } from "./page";

const STANCE_BADGE: Record<string, "bullish" | "secondary" | "destructive"> = {
  accumulate: "bullish",
  watch: "secondary",
  hold: "secondary",
  avoid: "destructive",
};

function fmt(v: number | null | undefined, prefix = "$", decimals = 2): string {
  if (v == null) return "—";
  return `${prefix}${Number(v).toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
}

function fmtPct(v: number | null | undefined, sign = true): string {
  if (v == null) return "—";
  const n = Number(v);
  return `${sign && n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
}

function MetricRow({ label, value, className }: { label: string; value: React.ReactNode; className?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border/50 py-2 last:border-0 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={`font-mono font-medium ${className ?? ""}`}>{value}</span>
    </div>
  );
}

function ScoreBar({ score, max = 5, colorClass }: { score: number; max?: number; colorClass: string }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
      <div className={`h-full rounded-full ${colorClass}`} style={{ width: `${(score / max) * 100}%` }} />
    </div>
  );
}

export function StockReport({ analysis: a }: { analysis: StockAnalysis }) {
  const chg = Number(a.change_pct ?? 0);
  const up = chg >= 0;
  const tech = a.technical ?? {};
  const val = a.valuation ?? {};
  const fund = a.fundamentals ?? {};
  const sent = a.sentiment ?? {};
  const news = a.news_catalyst ?? {};
  const wyBias = tech.wyckoff_bias ?? "neutral";
  const wyScore = tech.wyckoff_signals_detected ?? 0;
  const upside = val.upside_pct;

  return (
    <div className="space-y-4">
      {/* ── Header ── */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-2xl font-bold font-mono">{a.ticker}</h2>
          <Badge variant={STANCE_BADGE[a.overall_stance] ?? "secondary"}>
            {a.overall_stance.toUpperCase()}
          </Badge>
          {fund.grade && fund.grade !== "N/A" && (
            <Badge variant="secondary">Grade {fund.grade}</Badge>
          )}
          <Badge variant="secondary">{(a.watchlist_priority ?? "medium").toUpperCase()} PRIORITY</Badge>
        </div>
        <p className="text-muted-foreground text-sm">{a.company_name}</p>
        <div className="flex items-baseline gap-3">
          <span className="text-2xl font-bold font-mono">{fmt(a.price)}</span>
          <span className={`flex items-center gap-0.5 text-base font-mono font-semibold ${up ? "text-bullish" : "text-bearish"}`}>
            {up ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
            {up ? "+" : ""}{chg.toFixed(2)}%
          </span>
        </div>

        {/* Conviction bar */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground w-16 shrink-0">Conviction</span>
          <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${Number(a.conviction ?? 0) * 100}%` }}
            />
          </div>
          <span className="text-xs font-mono text-muted-foreground w-8 text-right">
            {Math.round(Number(a.conviction ?? 0) * 100)}%
          </span>
        </div>

        {/* One-liner */}
        <p className="text-sm text-muted-foreground italic border-l-2 border-border pl-3 leading-relaxed">
          {a.one_liner}
        </p>
      </div>

      {/* ── News & Catalyst ── */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Newspaper className="h-4 w-4 text-primary" />
            News &amp; Catalyst
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className={`border-l-2 pl-3 ${
            news.sentiment === "bullish" ? "border-bullish" :
            news.sentiment === "bearish" ? "border-bearish" : "border-border"
          }`}>
            <div className="flex items-start gap-2 mb-1">
              <Badge
                variant={news.sentiment === "bullish" ? "bullish" : news.sentiment === "bearish" ? "destructive" : "secondary"}
                className="text-[10px] shrink-0 mt-px"
              >
                {(news.sentiment ?? "neutral").toUpperCase()}
              </Badge>
              {news.source_url ? (
                <a href={news.source_url} target="_blank" rel="noopener noreferrer"
                  className="text-sm font-medium hover:underline text-foreground leading-snug">
                  {news.headline}
                </a>
              ) : (
                <p className="text-sm font-medium leading-snug">{news.headline}</p>
              )}
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">{news.summary}</p>
          </div>
        </CardContent>
      </Card>

      {/* ── Strategy Signals ── */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Zap className="h-4 w-4 text-primary" />
            Strategy Signals
          </CardTitle>
        </CardHeader>
        <CardContent>
          {(a.strategy_signals ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No active strategy signals</p>
          ) : (
            <div className="space-y-2">
              {a.strategy_signals.map((sig, i) => (
                <div key={i} className="rounded-lg border bg-muted/30 px-3 py-2">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="text-sm font-semibold">{sig.strategy}</span>
                    <Badge variant={sig.action === "buy" ? "bullish" : sig.action === "sell" ? "destructive" : "secondary"}
                      className="text-[10px]">
                      {sig.action.toUpperCase()}
                    </Badge>
                    <span className="ml-auto text-xs text-muted-foreground">
                      {Math.round(Number(sig.confidence ?? 0) * 100)}% confidence
                    </span>
                  </div>
                  <p className="text-xs font-mono text-muted-foreground">
                    Entry: {fmt(sig.entry_low)}–{fmt(sig.entry_high)}
                    &nbsp;·&nbsp;
                    Stop: <span className="text-bearish">{fmt(sig.stop_loss)}</span>
                    &nbsp;·&nbsp;
                    Target: <span className="text-bullish">{fmt(sig.target)}</span>
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Technical Analysis ── */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <TrendingUp className="h-4 w-4 text-primary" />
            Technical Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <MetricRow label="Trend" value={tech.trend ?? "—"} />
          <MetricRow label="Wyckoff Phase" value={tech.wyckoff_phase ?? "—"} />
          <MetricRow
            label="Wyckoff Bias"
            value={
              <Badge variant={wyBias === "bullish" ? "bullish" : wyBias === "bearish" ? "destructive" : "secondary"}
                className="text-[10px]">
                {wyBias.toUpperCase()}
              </Badge>
            }
          />
          <div className="py-2 border-b border-border/50">
            <div className="flex justify-between text-sm mb-1.5">
              <span className="text-muted-foreground">Wyckoff Signals</span>
              <span className="font-mono font-medium">{wyScore} / 5</span>
            </div>
            <ScoreBar
              score={wyScore}
              colorClass={wyBias === "bullish" ? "bg-bullish" : wyBias === "bearish" ? "bg-bearish" : "bg-muted-foreground"}
            />
          </div>

          {tech.vcp_detected && (
            <div className="rounded-lg border border-bullish/30 bg-bullish/5 px-3 py-2 text-sm">
              <span className="font-semibold text-bullish">✓ VCP Detected</span>
              <span className="text-muted-foreground ml-2">Pivot: {fmt(tech.vcp_pivot)}</span>
              {tech.vcp_stage && <p className="text-xs text-muted-foreground mt-0.5">{tech.vcp_stage}</p>}
            </div>
          )}

          <MetricRow label="Key Support" value={fmt(tech.key_support)} className="text-bullish" />
          <MetricRow label="Key Resistance" value={fmt(tech.key_resistance)} className="text-bearish" />
          <MetricRow label="RSI (14)" value={tech.rsi != null ? Number(tech.rsi).toFixed(1) : "—"} />
          <MetricRow label="MACD" value={tech.macd_signal ?? "—"} />
          <MetricRow label="Volume Ratio" value={tech.volume_ratio_today != null ? `${Number(tech.volume_ratio_today).toFixed(2)}×` : "—"} />
          <MetricRow label="Volume Signal" value={tech.volume_signal ?? "—"} />

          {tech.summary && (
            <p className="text-xs text-muted-foreground leading-relaxed pt-1">{tech.summary}</p>
          )}
        </CardContent>
      </Card>

      {/* ── DCF Valuation ── */}
      {val.feasible && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <DollarSign className="h-4 w-4 text-primary" />
              DCF Valuation
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-0">
            <MetricRow label="Intrinsic Value (base)" value={fmt(val.base_intrinsic_value)} />
            <MetricRow
              label="Upside / Downside"
              value={fmtPct(upside)}
              className={upside != null && Number(upside) >= 0 ? "text-bullish" : "text-bearish"}
            />
            <MetricRow
              label="Bear / Bull Range"
              value={`${fmt(val.bear_value)} – ${fmt(val.bull_value)}`}
            />
            <MetricRow label="Discount Rate" value={val.discount_rate != null ? fmtPct(Number(val.discount_rate) * 100, false) : "—"} />
            <MetricRow label="Growth Rate" value={val.growth_rate != null ? fmtPct(Number(val.growth_rate) * 100, false) : "—"} />
            {val.summary && (
              <p className="text-xs text-muted-foreground leading-relaxed pt-3">{val.summary}</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── Fundamentals ── */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <BarChart2 className="h-4 w-4 text-primary" />
            Fundamentals
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-bullish mb-2">Strengths</p>
              <ul className="space-y-1">
                {(fund.key_strengths ?? []).length > 0
                  ? fund.key_strengths.map((s, i) => (
                      <li key={i} className="text-xs text-muted-foreground flex gap-1.5">
                        <span className="text-bullish shrink-0">✓</span>{s}
                      </li>
                    ))
                  : <li className="text-xs text-muted-foreground">—</li>}
              </ul>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-bearish mb-2">Concerns</p>
              <ul className="space-y-1">
                {(fund.key_concerns ?? []).length > 0
                  ? fund.key_concerns.map((c, i) => (
                      <li key={i} className="text-xs text-muted-foreground flex gap-1.5">
                        <span className="text-bearish shrink-0">✗</span>{c}
                      </li>
                    ))
                  : <li className="text-xs text-muted-foreground">—</li>}
              </ul>
            </div>
          </div>
          {fund.summary && (
            <p className="text-xs text-muted-foreground leading-relaxed border-t border-border/50 pt-3">{fund.summary}</p>
          )}
        </CardContent>
      </Card>

      {/* ── Sentiment ── */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <MessageSquare className="h-4 w-4 text-primary" />
            Social Sentiment
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-0">
          <MetricRow
            label="Score"
            value={
              <span className="flex items-center gap-2">
                <Badge variant={Number(sent.score ?? 0) > 0.1 ? "bullish" : Number(sent.score ?? 0) < -0.1 ? "destructive" : "secondary"}
                  className="text-[10px]">
                  {sent.label ?? "Neutral"}
                </Badge>
                <span className="text-xs">{Number(sent.score ?? 0) >= 0 ? "+" : ""}{Number(sent.score ?? 0).toFixed(2)}</span>
              </span>
            }
          />
          <MetricRow label="Mentions (24h)" value={String(sent.mentions_24h ?? 0)} />
          <MetricRow label="Trend" value={sent.trend ?? "—"} />
        </CardContent>
      </Card>

      {/* ── Risks ── */}
      {(a.risks ?? []).length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <AlertTriangle className="h-4 w-4 text-primary" />
              Risks to Watch
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {a.risks.map((r, i) => (
                <li key={i} className="flex gap-2 text-xs text-muted-foreground">
                  <span className="text-bearish shrink-0 mt-px">•</span>
                  {r}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <p className="text-[11px] text-muted-foreground/50 text-center pb-2">
        {a.report_date} · Stock Sentinel Morning Brief
      </p>
    </div>
  );
}
