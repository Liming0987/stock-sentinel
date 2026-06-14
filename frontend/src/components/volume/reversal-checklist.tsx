"use client";

import { CheckCircle2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { VolumeChecklist } from "@/lib/hooks";

const STEPS: { key: keyof Omit<VolumeChecklist, "overall" | "score" | "details">; label: string; fallback: string }[] = [
  {
    key: "selling_climax",
    label: "Selling Climax",
    fallback: "Vol spike 2.5x+ with intraday recovery",
  },
  {
    key: "high_vol_breakout",
    label: "High-Volume Breakout",
    fallback: "Price +3%+ on 1.5x+ volume",
  },
  {
    key: "low_vol_retest",
    label: "Low-Volume Retest",
    fallback: "Sellers drying up post-spike",
  },
  {
    key: "higher_low_pivot",
    label: "Higher Low Pivot",
    fallback: "Price structure improving",
  },
  {
    key: "vwap_reclaim",
    label: "VWAP Reclamation",
    fallback: "Price above period VWAP",
  },
];

function overallBadgeVariant(overall: string): "bullish" | "neutral" | "bearish" {
  if (overall === "Bullish reversal forming") return "bullish";
  if (overall === "Early signs of reversal") return "neutral";
  return "bearish";
}

interface ReversalChecklistProps {
  checklist: VolumeChecklist;
}

export function ReversalChecklist({ checklist }: ReversalChecklistProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Bullish Reversal Checklist (Wyckoff)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {STEPS.map(({ key, label, fallback }) => {
          const passed = checklist[key] as boolean;
          const detail = checklist.details[key] ?? fallback;
          return (
            <div key={key} className="flex items-start gap-3">
              {passed ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
              ) : (
                <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
              )}
              <div>
                <p className={`text-sm font-medium ${passed ? "text-foreground" : "text-muted-foreground"}`}>
                  {label}
                </p>
                <p className="text-xs text-muted-foreground">{detail}</p>
              </div>
            </div>
          );
        })}

        <div className="mt-4 flex items-center gap-3 border-t border-border pt-3">
          <Badge variant={overallBadgeVariant(checklist.overall)}>{checklist.overall}</Badge>
          <span className="text-sm text-muted-foreground">{checklist.score}/5 signals confirmed</span>
        </div>
      </CardContent>
    </Card>
  );
}
