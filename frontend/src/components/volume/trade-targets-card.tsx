"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PnFAnalysis, SwingEntry, LongtermEntry } from "@/lib/hooks";

type Tab = "pnf" | "swing" | "longterm";

function fmt(val: number | null, decimals = 2): string {
  if (val === null || val === undefined) return "—";
  return `$${val.toFixed(decimals)}`;
}

function fmtRR(val: number | null): string {
  if (val === null || val === undefined) return "—";
  return `${val.toFixed(2)}x`;
}

function RRBadge({ rr }: { rr: number | null }) {
  if (rr === null || rr === undefined) return <span className="text-muted-foreground">—</span>;
  const color =
    rr >= 2.0
      ? "text-green-400 font-bold"
      : rr >= 1.0
      ? "text-amber-400 font-bold"
      : "text-red-400 font-bold";
  return <span className={`text-lg ${color}`}>{fmtRR(rr)}</span>;
}

function MetricRow({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={`text-sm font-medium ${color ?? ""}`}>{value}</span>
    </div>
  );
}

function EntryZoneBar({
  low,
  high,
  isBullish,
}: {
  low: number | null;
  high: number | null;
  isBullish: boolean;
}) {
  if (low === null || high === null) return null;
  const barColor = isBullish ? "bg-green-500" : "bg-red-500";
  return (
    <div className="my-2 space-y-1">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{fmt(low)}</span>
        <span>{fmt(high)}</span>
      </div>
      <div className={`h-2 rounded-full ${barColor} opacity-70`} />
    </div>
  );
}

function PnFTab({ pnf }: { pnf: PnFAnalysis | undefined }) {
  if (!pnf) return <p className="text-sm text-muted-foreground">No P&F data available.</p>;

  const biasBg =
    pnf.bias === "bullish"
      ? "text-green-400"
      : pnf.bias === "bearish"
      ? "text-red-400"
      : "text-muted-foreground";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        {pnf.box_size !== null && (
          <span>
            Box size: <span className="font-medium text-foreground">${pnf.box_size}</span>
          </span>
        )}
        <span>
          Reversal: <span className="font-medium text-foreground">{pnf.reversal_boxes}-box</span>
        </span>
        {pnf.column_count !== null && (
          <span>
            Columns: <span className="font-medium text-foreground">{pnf.column_count}</span>
          </span>
        )}
        {pnf.bias && (
          <span>
            Bias:{" "}
            <span className={`font-semibold uppercase ${biasBg}`}>{pnf.bias}</span>
          </span>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between py-1.5 border-b border-border">
          <div className="flex items-center gap-2">
            <span className="text-base">&#x1F4C8;</span>
            <span className="text-sm text-muted-foreground">Bullish Vertical Target</span>
          </div>
          <span className="text-sm font-medium text-green-400">{fmt(pnf.bullish_vertical_target)}</span>
        </div>
        <div className="flex items-center justify-between py-1.5 border-b border-border">
          <div className="flex items-center gap-2">
            <span className="text-base">&#x1F4C9;</span>
            <span className="text-sm text-muted-foreground">Bearish Vertical Target</span>
          </div>
          <span className="text-sm font-medium text-red-400">{fmt(pnf.bearish_vertical_target)}</span>
        </div>
        <div className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
          <div className="flex items-center gap-2">
            <span className="text-base">&#x2194;&#xFE0F;</span>
            <span className="text-sm text-muted-foreground">Horizontal Count Target</span>
          </div>
          <span className="text-sm font-medium text-amber-400">{fmt(pnf.horizontal_target)}</span>
        </div>
      </div>

      {pnf.note && (
        <p className="text-[11px] text-muted-foreground leading-relaxed">{pnf.note}</p>
      )}
    </div>
  );
}

function SwingTab({ swing }: { swing: SwingEntry | undefined }) {
  if (!swing) return <p className="text-sm text-muted-foreground">No swing entry data available.</p>;

  const isBullish = swing.bias === "bullish";
  const badgeVariant = isBullish ? "bullish" : "destructive";
  const badgeLabel = isBullish ? "BULLISH SETUP" : "BEARISH SETUP";

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Badge variant={badgeVariant as "bullish" | "destructive"}>{badgeLabel}</Badge>
        <Badge variant="secondary">{swing.time_horizon}</Badge>
      </div>

      <EntryZoneBar low={swing.entry_zone_low} high={swing.entry_zone_high} isBullish={isBullish} />

      <div className="space-y-0.5">
        <MetricRow
          label="Entry Zone"
          value={
            swing.entry_zone_low !== null && swing.entry_zone_high !== null
              ? `${fmt(swing.entry_zone_low)} – ${fmt(swing.entry_zone_high)}`
              : "—"
          }
        />
        <MetricRow label="Stop Loss" value={fmt(swing.stop_loss)} color="text-red-400" />
        <MetricRow label="Target" value={fmt(swing.target)} color="text-green-400" />
      </div>

      <div className="flex items-center gap-3 pt-1">
        <span className="text-sm text-muted-foreground">Risk / Reward</span>
        <RRBadge rr={swing.risk_reward} />
      </div>

      {swing.note && (
        <p className="text-[11px] text-muted-foreground leading-relaxed">{swing.note}</p>
      )}
    </div>
  );
}

function LongtermTab({ lt }: { lt: LongtermEntry | undefined }) {
  if (!lt) return <p className="text-sm text-muted-foreground">No long-term entry data available.</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Badge variant="secondary">{lt.time_horizon}</Badge>
      </div>

      <div className="rounded-md bg-muted/40 p-3 space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">DCA Zone</span>
          <span className="text-sm font-medium text-green-400">
            {lt.entry_zone_low !== null && lt.entry_zone_high !== null
              ? `${fmt(lt.entry_zone_low)} – ${fmt(lt.entry_zone_high)}`
              : "—"}
          </span>
        </div>
        <p className="text-[11px] text-muted-foreground">Dollar-cost average into this zone</p>
      </div>

      <div className="space-y-0.5">
        <MetricRow label="Stop Loss" value={fmt(lt.stop_loss)} color="text-red-400" />
        <MetricRow label="Target" value={fmt(lt.target)} color="text-green-400" />
      </div>

      <div className="flex items-center gap-3 pt-1">
        <span className="text-sm text-muted-foreground">Risk / Reward</span>
        <RRBadge rr={lt.risk_reward} />
      </div>

      {lt.note && (
        <p className="text-[11px] text-muted-foreground leading-relaxed">{lt.note}</p>
      )}
    </div>
  );
}

interface TradeTargetsCardProps {
  pnf: PnFAnalysis | undefined;
  swingEntry: SwingEntry | undefined;
  longtermEntry: LongtermEntry | undefined;
}

const TABS: { id: Tab; label: string }[] = [
  { id: "pnf", label: "P&F Targets" },
  { id: "swing", label: "Swing Trade" },
  { id: "longterm", label: "Long-Term Entry" },
];

export function TradeTargetsCard({ pnf, swingEntry, longtermEntry }: TradeTargetsCardProps) {
  const [tab, setTab] = useState<Tab>("pnf");

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Trade Targets</CardTitle>
        <div className="flex gap-1 pt-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                tab === t.id
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {tab === "pnf" && <PnFTab pnf={pnf} />}
        {tab === "swing" && <SwingTab swing={swingEntry} />}
        {tab === "longterm" && <LongtermTab lt={longtermEntry} />}
      </CardContent>
    </Card>
  );
}
