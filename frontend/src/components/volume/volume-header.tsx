"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { VolumeAnalysisResponse } from "@/lib/hooks";

function fmtVol(v: number | null): string {
  if (v == null) return "—";
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toFixed(0);
}

function ratioBadgeVariant(ratio: number | null): "destructive" | "bullish" | "bearish" | "neutral" {
  if (ratio == null) return "neutral";
  if (ratio >= 2) return "destructive";
  if (ratio >= 1.5) return "bearish";
  if (ratio < 0.8) return "bullish";
  return "neutral";
}

function SkeletonRow() {
  return (
    <div className="h-5 w-24 animate-pulse rounded bg-muted" />
  );
}

interface VolumeHeaderProps {
  data: VolumeAnalysisResponse | null;
  loading: boolean;
}

export function VolumeHeader({ data, loading }: VolumeHeaderProps) {
  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-6 pt-4">
        <div>
          <p className="text-xs text-muted-foreground">Ticker</p>
          {loading ? <SkeletonRow /> : (
            <p className="text-xl font-bold font-mono">{data?.ticker ?? "—"}</p>
          )}
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Name</p>
          {loading ? <SkeletonRow /> : (
            <p className="text-sm font-medium">{data?.name ?? "—"}</p>
          )}
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Current Price</p>
          {loading ? <SkeletonRow /> : (
            <p className="text-xl font-bold font-mono">
              {data?.current_price != null ? `$${data.current_price.toFixed(2)}` : "—"}
            </p>
          )}
        </div>
        <div>
          <p className="text-xs text-muted-foreground">30d Avg Volume</p>
          {loading ? <SkeletonRow /> : (
            <p className="text-sm font-mono">{fmtVol(data?.avg_vol_30d ?? null)}</p>
          )}
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">Vol Ratio</p>
          {loading ? <SkeletonRow /> : (
            <Badge variant={ratioBadgeVariant(data?.current_vol_ratio ?? null)}>
              {data?.current_vol_ratio != null ? `${data.current_vol_ratio.toFixed(2)}x` : "—"}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
