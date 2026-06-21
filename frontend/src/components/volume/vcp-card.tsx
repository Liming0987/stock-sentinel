"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { VCPAnalysis } from "@/lib/hooks";

function statusBadge(status: VCPAnalysis["status"]) {
  if (status === "breaking_out")
    return <Badge className="bg-green-500/15 text-green-400 border-green-500/30">Breaking Out</Badge>;
  if (status === "ready")
    return <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/30">Ready</Badge>;
  if (status === "forming")
    return <Badge className="bg-blue-500/15 text-blue-400 border-blue-500/30">Forming</Badge>;
  return <Badge variant="secondary">Not Detected</Badge>;
}

interface VCPCardProps {
  vcp: VCPAnalysis;
}

export function VCPCard({ vcp }: VCPCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">VCP Analysis</CardTitle>
          <div className="flex items-center gap-2">
            {vcp.detected && statusBadge(vcp.status)}
            {!vcp.detected && <Badge variant="secondary">Not Detected</Badge>}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Stage 2 + Pivot row */}
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <div className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${vcp.stage2 ? "bg-green-500" : "bg-muted-foreground/40"}`} />
            <span className={vcp.stage2 ? "text-green-400" : "text-muted-foreground"}>
              Stage 2 uptrend
            </span>
          </div>
          {vcp.pivot != null && (
            <div className="text-muted-foreground">
              Pivot{" "}
              <span className="font-semibold text-amber-400 tabular-nums">
                ${vcp.pivot.toFixed(2)}
              </span>
            </div>
          )}
          {vcp.base_start_date && (
            <div className="text-muted-foreground text-xs">
              Base since {vcp.base_start_date}
            </div>
          )}
        </div>

        {/* Contractions */}
        {vcp.contractions.length > 0 ? (
          <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/60">
              Contractions ({vcp.contractions.length})
            </p>
            <div className="space-y-1.5">
              {vcp.contractions.map((c, i) => (
                <div key={i} className="flex items-center gap-2 rounded-md bg-muted/30 px-3 py-2">
                  <span className="text-[10px] font-bold text-amber-400 w-5">C{i + 1}</span>
                  <div className="flex-1">
                    {/* Depth bar */}
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-amber-400/70 transition-all"
                          style={{ width: `${Math.min(100, c.depth_pct * 4)}%` }}
                        />
                      </div>
                      <span className="text-xs font-semibold tabular-nums text-amber-400 w-10 text-right">
                        {c.depth_pct}%
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <span className="tabular-nums">${c.high.toFixed(2)} → ${c.low.toFixed(2)}</span>
                    {c.vol_dry && (
                      <span className="text-green-400 font-semibold" title="Volume dried up at this low">
                        vol✓
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* VCP checklist summary */}
            <div className="mt-3 grid grid-cols-2 gap-1.5 text-xs">
              {[
                { label: "Contractions ≥ 2", ok: vcp.contractions.length >= 2 },
                { label: "Depth decreasing", ok: vcp.detected },
                { label: "Volume drying up", ok: vcp.contractions.some(c => c.vol_dry) },
                { label: "Stage 2 uptrend", ok: vcp.stage2 },
              ].map(({ label, ok }) => (
                <div key={label} className="flex items-center gap-1.5">
                  <span className={ok ? "text-green-400" : "text-muted-foreground/50"}>
                    {ok ? "✓" : "✗"}
                  </span>
                  <span className={ok ? "text-foreground" : "text-muted-foreground/60"}>{label}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No contractions detected in the current window.</p>
        )}

        {/* Note */}
        {vcp.note && (
          <p className="text-[11px] text-muted-foreground leading-relaxed border-t border-border pt-3">
            {vcp.note}
          </p>
        )}

        {/* Execution rules reminder */}
        {vcp.detected && (
          <div className="rounded-md border border-border bg-muted/20 px-3 py-2 space-y-1 text-[11px] text-muted-foreground">
            <p><span className="text-foreground font-medium">Entry:</span> Buy-stop just above pivot on volume +40%</p>
            <p><span className="text-foreground font-medium">Stop:</span> 7–8% below entry or under C{vcp.contractions.length} low</p>
            <p><span className="text-foreground font-medium">Filter:</span> Only trade when broader market is in uptrend</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
