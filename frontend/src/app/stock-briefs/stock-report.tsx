"use client";

import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { StockAnalysis } from "./page";

// ── helpers ────────────────────────────────────────────────────────────────────

const STANCE_BADGE: Record<string, "bullish" | "secondary" | "destructive"> = {
  accumulate: "bullish",
  watch: "secondary",
  hold: "secondary",
  avoid: "destructive",
};

function fmt(v: number | null | undefined, decimals = 2): string {
  if (v == null) return "—";
  return `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
}

function fmtVol(v: number | null | undefined): string {
  if (v == null) return "—";
  const n = Number(v);
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return String(n);
}

function fmtPct(v: number | null | undefined, sign = true): string {
  if (v == null) return "—";
  const n = Number(v);
  return `${sign && n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
}

// Prose paragraphs — supports newlines in the stored text
function Prose({ text, className }: { text: string; className?: string }) {
  if (!text) return null;
  const paragraphs = text.split(/\n{2,}/).filter(Boolean);
  return (
    <div className={`space-y-2 ${className ?? ""}`}>
      {paragraphs.map((p, i) => (
        <p key={i} className="text-sm text-muted-foreground leading-relaxed">{p.trim()}</p>
      ))}
    </div>
  );
}

// Inline chip for a key metric
function Chip({ label, value, highlight }: { label: string; value: React.ReactNode; highlight?: boolean }) {
  return (
    <div className={`rounded-lg border px-3 py-2 ${highlight ? "border-primary/30 bg-primary/5" : "border-border bg-muted/30"}`}>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-0.5">{label}</p>
      <p className="text-sm font-mono font-semibold">{value}</p>
    </div>
  );
}

function WyckoffBar({ score, bias }: { score: number; bias: string }) {
  const colorClass = bias === "bullish" ? "bg-bullish" : bias === "bearish" ? "bg-bearish" : "bg-muted-foreground";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${colorClass}`} style={{ width: `${(score / 5) * 100}%` }} />
      </div>
      <span className="text-xs font-mono text-muted-foreground shrink-0">{score}/5 signals</span>
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────────

export function StockReport({ analysis: a }: { analysis: StockAnalysis }) {
  const chg = Number(a.change_pct ?? 0);
  const up = chg >= 0;
  const tech = a.technical ?? {};
  const val = a.valuation ?? {};
  const fund = a.fundamentals ?? {};
  const sent = a.sentiment ?? {};
  const news = a.news_catalyst ?? {};
  const pa = a.price_action;
  const wyBias = tech.wyckoff_bias ?? "neutral";
  const wyScore = tech.wyckoff_signals_detected ?? 0;
  const upside = val.upside_pct;

  return (
    <div className="space-y-4">

      {/* ── Header ───────────────────────────────────────────────────────────── */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-2xl font-bold font-mono">{a.ticker}</h2>
          <Badge variant={STANCE_BADGE[a.overall_stance] ?? "secondary"}>
            {a.overall_stance.toUpperCase()}
          </Badge>
          {fund.grade && fund.grade !== "N/A" && (
            <Badge variant="secondary">Grade {fund.grade}</Badge>
          )}
        </div>

        <p className="text-sm text-muted-foreground">{a.company_name}</p>

        <div className="flex items-baseline gap-3">
          <span className="text-2xl font-bold font-mono">{fmt(a.price)}</span>
          <span className={`flex items-center gap-0.5 text-lg font-mono font-semibold ${up ? "text-bullish" : "text-bearish"}`}>
            {up ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
            {up ? "+" : ""}{chg.toFixed(2)}%
          </span>
        </div>

        {/* Conviction */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground shrink-0">Conviction</span>
          <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
            <div className="h-full rounded-full bg-primary" style={{ width: `${Number(a.conviction ?? 0) * 100}%` }} />
          </div>
          <span className="text-xs font-mono text-muted-foreground shrink-0">
            {Math.round(Number(a.conviction ?? 0) * 100)}%
          </span>
        </div>

        {/* One-liner — the pre-market verdict */}
        <blockquote className="border-l-2 border-primary/40 pl-3 text-sm text-foreground font-medium leading-relaxed">
          {a.one_liner}
        </blockquote>
      </div>

      {/* ── The story: news + technical narrative ────────────────────────────── */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Today&apos;s Reading</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">

          {/* News headline */}
          {news.headline && (
            <div className={`border-l-2 pl-3 space-y-1.5 ${
              news.sentiment === "bullish" ? "border-bullish" :
              news.sentiment === "bearish" ? "border-bearish" : "border-border"
            }`}>
              <div className="flex items-start gap-2">
                <Badge
                  variant={news.sentiment === "bullish" ? "bullish" : news.sentiment === "bearish" ? "destructive" : "secondary"}
                  className="text-[10px] shrink-0 mt-px"
                >
                  {(news.sentiment ?? "neutral").toUpperCase()}
                </Badge>
                {news.source_url ? (
                  <a href={news.source_url} target="_blank" rel="noopener noreferrer"
                    className="text-sm font-semibold hover:underline text-foreground leading-snug">
                    {news.headline}
                  </a>
                ) : (
                  <p className="text-sm font-semibold text-foreground leading-snug">{news.headline}</p>
                )}
              </div>
              {/* Full news summary — no clipping */}
              <Prose text={news.summary} />
            </div>
          )}

          {/* Divider if both sections present */}
          {news.summary && tech.summary && <hr className="border-border" />}

          {/* Technical narrative — the main analytical prose */}
          {tech.summary && <Prose text={tech.summary} />}

          {/* Richer Wyckoff narrative if available */}
          {a.wyckoff_narrative && (
            <>
              <hr className="border-border" />
              <Prose text={a.wyckoff_narrative} />
            </>
          )}

          {/* Framework analysis if available */}
          {a.framework_analysis && (
            <>
              <hr className="border-border" />
              <Prose text={a.framework_analysis} />
            </>
          )}
        </CardContent>
      </Card>

      {/* ── Price & Volume (if price_action available, otherwise infer from data) */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Price &amp; Volume</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* OHLCV grid */}
          {pa ? (
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
              <Chip label="Open"   value={fmt(pa.open)} />
              <Chip label="High"   value={fmt(pa.high)} />
              <Chip label="Low"    value={fmt(pa.low)} />
              <Chip label="Close"  value={fmt(pa.close)} />
              <Chip label="Volume" value={fmtVol(pa.volume)} />
              <Chip label="Vol ×"  value={`${Number(pa.vol_ratio ?? 0).toFixed(2)}×`} highlight />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Chip label="Close"      value={fmt(a.price)} />
              <Chip label="Change"     value={<span className={up ? "text-bullish" : "text-bearish"}>{fmtPct(chg)}</span>} />
              <Chip label="Vol ×"      value={tech.volume_ratio_today != null ? `${Number(tech.volume_ratio_today).toFixed(2)}×` : "—"} highlight={Number(tech.volume_ratio_today) >= 2} />
              <Chip label="Support"    value={fmt(tech.key_support)} />
            </div>
          )}

          {/* Volume signal badge + rank */}
          <div className="flex flex-wrap items-center gap-2">
            {tech.volume_signal && (
              <Badge variant={
                tech.volume_signal.toLowerCase().includes("climactic") ? "destructive" :
                tech.volume_signal.toLowerCase().includes("elevated") ? "bullish" : "secondary"
              } className="text-[10px]">
                {tech.volume_signal.toUpperCase()}
              </Badge>
            )}
            {pa?.vol_rank && (
              <span className="text-xs text-muted-foreground">{pa.vol_rank}</span>
            )}
          </div>

          {/* Intraday story if available */}
          {pa?.intraday_story && <Prose text={pa.intraday_story} />}
        </CardContent>
      </Card>

      {/* ── Technical framework ──────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Technical Framework</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Wyckoff section */}
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Wyckoff</span>
              <Badge variant={wyBias === "bullish" ? "bullish" : wyBias === "bearish" ? "destructive" : "secondary"}
                className="text-[10px]">
                {wyBias.toUpperCase()}
              </Badge>
              <span className="text-xs text-muted-foreground">{tech.wyckoff_phase}</span>
            </div>
            <WyckoffBar score={wyScore} bias={wyBias} />
          </div>

          {/* VCP */}
          {tech.vcp_detected && (
            <div className="rounded-lg border border-bullish/30 bg-bullish/5 px-3 py-2">
              <p className="text-sm font-semibold text-bullish">✓ VCP Pattern Forming</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Pivot: {fmt(tech.vcp_pivot)}{tech.vcp_stage ? ` · ${tech.vcp_stage}` : ""}
              </p>
            </div>
          )}

          {/* Key levels + indicators as compact grid */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Chip label="Support"    value={<span className="text-bullish">{fmt(tech.key_support)}</span>} />
            <Chip label="Resistance" value={<span className="text-bearish">{fmt(tech.key_resistance)}</span>} />
            <Chip label="RSI (14)"   value={tech.rsi != null ? Number(tech.rsi).toFixed(1) : "—"}
              highlight={tech.rsi != null && (Number(tech.rsi) < 30 || Number(tech.rsi) > 70)} />
            <Chip label="MACD"       value={
              <span className={tech.macd_signal?.includes("bullish") ? "text-bullish" : tech.macd_signal?.includes("bearish") ? "text-bearish" : ""}>
                {tech.macd_signal?.replace(" crossover", "") ?? "—"}
              </span>
            } />
          </div>

          {/* Trend */}
          <p className="text-xs text-muted-foreground">
            Trend: <span className="font-medium text-foreground capitalize">{tech.trend ?? "—"}</span>
          </p>
        </CardContent>
      </Card>

      {/* ── Strategy Signals ─────────────────────────────────────────────────── */}
      {(a.strategy_signals ?? []).length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Strategy Signals</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {a.strategy_signals.map((sig, i) => (
              <div key={i} className="rounded-lg border bg-muted/30 px-3 py-2.5">
                <div className="flex flex-wrap items-center gap-2 mb-1.5">
                  <span className="text-sm font-semibold">{sig.strategy}</span>
                  <Badge variant={sig.action === "buy" ? "bullish" : sig.action === "sell" ? "destructive" : "secondary"}
                    className="text-[10px]">
                    {sig.action.toUpperCase()}
                  </Badge>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {Math.round(Number(sig.confidence ?? 0) * 100)}% confidence
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-[11px]">
                  <div>
                    <span className="text-muted-foreground">Entry</span>
                    <p className="font-mono font-medium">{fmt(sig.entry_low)}–{fmt(sig.entry_high)}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Stop</span>
                    <p className="font-mono font-medium text-bearish">{fmt(sig.stop_loss)}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Target</span>
                    <p className="font-mono font-medium text-bullish">{fmt(sig.target)}</p>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* ── Valuation ────────────────────────────────────────────────────────── */}
      {val.feasible && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Valuation (DCF)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Upside headline */}
            <div className="flex items-baseline gap-3">
              <span className={`text-3xl font-bold font-mono ${upside != null && Number(upside) >= 0 ? "text-bullish" : "text-bearish"}`}>
                {fmtPct(upside)}
              </span>
              <span className="text-sm text-muted-foreground">
                to base case {fmt(val.base_intrinsic_value)}
              </span>
            </div>
            {/* Bear / Bull range */}
            <div className="grid grid-cols-3 gap-2">
              <Chip label="Bear"     value={<span className="text-bearish">{fmt(val.bear_value)}</span>} />
              <Chip label="Base"     value={fmt(val.base_intrinsic_value)} highlight />
              <Chip label="Bull"     value={<span className="text-bullish">{fmt(val.bull_value)}</span>} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Chip label="Discount Rate" value={val.discount_rate != null ? fmtPct(Number(val.discount_rate) * 100, false) : "—"} />
              <Chip label="Growth Rate"   value={val.growth_rate != null ? fmtPct(Number(val.growth_rate) * 100, false) : "—"} />
            </div>
            {/* DCF prose */}
            {val.summary && <Prose text={val.summary} />}
          </CardContent>
        </Card>
      )}

      {/* ── Fundamentals ─────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            Fundamentals
            {fund.grade && fund.grade !== "N/A" && (
              <Badge variant="secondary" className="text-xs">Grade {fund.grade}</Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-bullish mb-2">Strengths</p>
              <ul className="space-y-1.5">
                {(fund.key_strengths ?? []).length > 0
                  ? fund.key_strengths.map((s, i) => (
                      <li key={i} className="flex gap-2 text-xs text-muted-foreground">
                        <span className="text-bullish shrink-0">✓</span>{s}
                      </li>
                    ))
                  : <li className="text-xs text-muted-foreground">—</li>}
              </ul>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-bearish mb-2">Concerns</p>
              <ul className="space-y-1.5">
                {(fund.key_concerns ?? []).length > 0
                  ? fund.key_concerns.map((c, i) => (
                      <li key={i} className="flex gap-2 text-xs text-muted-foreground">
                        <span className="text-bearish shrink-0">✗</span>{c}
                      </li>
                    ))
                  : <li className="text-xs text-muted-foreground">—</li>}
              </ul>
            </div>
          </div>
          {fund.summary && (
            <div className="border-t border-border/50 pt-3">
              <Prose text={fund.summary} />
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Social Sentiment ─────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Social Sentiment</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-2">
            <Chip label="Score" value={
              <span className={Number(sent.score ?? 0) > 0.1 ? "text-bullish" : Number(sent.score ?? 0) < -0.1 ? "text-bearish" : ""}>
                {Number(sent.score ?? 0) >= 0 ? "+" : ""}{Number(sent.score ?? 0).toFixed(2)}
              </span>
            } highlight />
            <Chip label="Mentions (24h)" value={String(sent.mentions_24h ?? 0)} />
            <Chip label="Trend" value={sent.trend ?? "—"} />
          </div>
          <div className="mt-2">
            <Badge variant={Number(sent.score ?? 0) > 0.1 ? "bullish" : Number(sent.score ?? 0) < -0.1 ? "destructive" : "secondary"}
              className="text-[10px]">
              {sent.label ?? "Neutral"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* ── Risks ────────────────────────────────────────────────────────────── */}
      {(a.risks ?? []).length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Risks to Watch</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {a.risks.map((r, i) => (
                <li key={i} className="flex gap-2 text-sm text-muted-foreground leading-relaxed">
                  <span className="text-bearish shrink-0 mt-0.5">•</span>
                  {r}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <p className="text-[11px] text-muted-foreground/40 text-center pb-2">
        {a.report_date} · Stock Sentinel Morning Brief
      </p>
    </div>
  );
}
