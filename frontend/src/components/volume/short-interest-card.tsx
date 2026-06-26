"use client";

import { Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface ShortInterestData {
  show: boolean;
  market_cap: number | null;
  market_cap_category: string | null;
  float_shares: number | null;
  shares_outstanding: number | null;
  pct_float_shorted: number | null;
  days_to_cover: number | null;
  tight_float: boolean;
  small_cap: boolean;
  squeeze_candidate: boolean;
  note: string | null;
}

function fmtShares(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return n.toFixed(0);
}

function fmtCap(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9)  return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6)  return `$${(n / 1e6).toFixed(0)}M`;
  return `$${n.toFixed(0)}`;
}

function Metric({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="space-y-0.5">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`text-sm font-semibold tabular-nums ${highlight ? "text-bearish" : ""}`}>{value}</p>
    </div>
  );
}

interface Props {
  data: ShortInterestData;
  ticker: string;
}

export function ShortInterestCard({ data, ticker }: Props) {
  if (!data.show) return null;

  const pctShorted = data.pct_float_shorted != null
    ? `${(data.pct_float_shorted * 100).toFixed(1)}%`
    : "—";
  const highShort = data.pct_float_shorted != null && data.pct_float_shorted >= 0.15;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Short Interest — {ticker}</CardTitle>
          <div className="flex gap-1.5">
            {data.squeeze_candidate && (
              <Badge variant="bearish" className="gap-1 text-[10px]">
                <Zap className="h-2.5 w-2.5" />
                Squeeze Candidate
              </Badge>
            )}
            {data.tight_float && !data.squeeze_candidate && (
              <Badge variant="secondary" className="text-[10px]">Tight Float</Badge>
            )}
            {data.small_cap && !data.squeeze_candidate && (
              <Badge variant="secondary" className="text-[10px]">{data.market_cap_category}</Badge>
            )}
            {!data.tight_float && !data.small_cap && data.market_cap_category && (
              <Badge variant="secondary" className="text-[10px]">{data.market_cap_category}</Badge>
            )}
          </div>
        </div>
        {data.note && (
          <p className="text-xs text-muted-foreground mt-1">{data.note}</p>
        )}
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
          <Metric
            label="Float Size"
            value={fmtShares(data.float_shares)}
          />
          <Metric
            label="Shares Outstanding"
            value={fmtShares(data.shares_outstanding)}
          />
          <Metric
            label="% Float Shorted"
            value={pctShorted}
            highlight={highShort}
          />
          <Metric
            label="Days to Cover"
            value={data.days_to_cover != null ? `${data.days_to_cover.toFixed(1)} days` : "—"}
            highlight={data.days_to_cover != null && data.days_to_cover >= 5}
          />
        </div>
        <div className="mt-4 pt-4 border-t grid grid-cols-2 gap-x-6 sm:grid-cols-4">
          <Metric
            label="Market Cap"
            value={fmtCap(data.market_cap)}
          />
          <Metric
            label="Cap Category"
            value={data.market_cap_category ?? "—"}
          />
          <div className="col-span-2 space-y-0.5">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Locked-up Shares</p>
            <p className="text-sm font-semibold tabular-nums">
              {data.float_shares != null && data.shares_outstanding != null
                ? fmtShares(data.shares_outstanding - data.float_shares)
                : "—"}
              {data.float_shares != null && data.shares_outstanding != null && data.shares_outstanding > 0 && (
                <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                  ({((1 - data.float_shares / data.shares_outstanding) * 100).toFixed(0)}% of total)
                </span>
              )}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
