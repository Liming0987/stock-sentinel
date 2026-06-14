"use client";

import { useState, useEffect } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { WyckoffAnalysis, WyckoffCheckItem, WyckoffSide } from "@/lib/hooks";

const ACC_STEPS: { key: keyof WyckoffSide; label: string }[] = [
  { key: "selling_climax", label: "Selling Climax (SC)" },
  { key: "automatic_rally", label: "Automatic Rally (AR)" },
  { key: "secondary_test", label: "Secondary Test (ST)" },
  { key: "sign_of_strength", label: "Sign of Strength (SOS)" },
  { key: "last_point_support", label: "Last Point of Support (LPS)" },
];

const DIST_STEPS: { key: keyof WyckoffSide; label: string }[] = [
  { key: "buying_climax", label: "Buying Climax (BC)" },
  { key: "automatic_reaction", label: "Automatic Reaction (AR)" },
  { key: "upthrust", label: "Upthrust (UT/UTAD)" },
  { key: "sign_of_weakness", label: "Sign of Weakness (SOW)" },
  { key: "last_point_supply", label: "Last Point of Supply (LPSY)" },
];

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return dateStr;
  }
}

function CheckRow({ item, label }: { item: WyckoffCheckItem | undefined; label: string }) {
  if (!item) return null;
  return (
    <div className="flex items-start gap-3">
      {item.detected ? (
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-400" />
      ) : (
        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">{label}</span>
          {item.date && (
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
              {formatDate(item.date)}
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground">{item.detail}</p>
      </div>
    </div>
  );
}

function ScoreBar({ score, isAcc }: { score: number; isAcc: boolean }) {
  return (
    <div className="mt-4 border-t border-border pt-3 space-y-2">
      <p className="text-xs text-muted-foreground">{score} / 5 signals detected</p>
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${isAcc ? "bg-green-500" : "bg-red-500"}`}
          style={{ width: `${(score / 5) * 100}%` }}
        />
      </div>
    </div>
  );
}

export function ReversalChecklist({ wyckoff }: { wyckoff: WyckoffAnalysis | undefined }) {
  const [tab, setTab] = useState<"accumulation" | "distribution">(
    wyckoff?.bias === "bearish" ? "distribution" : "accumulation"
  );

  useEffect(() => {
    setTab(wyckoff?.bias === "bearish" ? "distribution" : "accumulation");
  }, [wyckoff?.bias]);

  if (!wyckoff) return null;

  const { support, resistance } = wyckoff.trading_range;
  const biasBadgeVariant =
    wyckoff.bias === "bullish" ? "bullish" : wyckoff.bias === "bearish" ? "destructive" : "secondary";

  const interpretation =
    wyckoff.bias === "bullish"
      ? "Accumulation signals detected — smart money appears to be building positions"
      : wyckoff.bias === "bearish"
      ? "Distribution signals detected — institutional selling pressure may be capping upside"
      : "No dominant structural bias — stock is in a neutral consolidation range";

  const side: WyckoffSide = tab === "accumulation" ? wyckoff.accumulation : wyckoff.distribution;
  const steps = tab === "accumulation" ? ACC_STEPS : DIST_STEPS;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Wyckoff Structural Analysis</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant={biasBadgeVariant as "bullish" | "destructive" | "secondary"}>{wyckoff.bias.charAt(0).toUpperCase() + wyckoff.bias.slice(1)}</Badge>
            <span className="text-sm font-medium">{wyckoff.phase}</span>
          </div>
          <div className="text-sm text-muted-foreground">
            Trading Range:{" "}
            <span className="text-green-400 font-medium">
              {support != null ? `$${support.toFixed(2)}` : "—"}
            </span>
            {" – "}
            <span className="text-red-400 font-medium">
              {resistance != null ? `$${resistance.toFixed(2)}` : "—"}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">{interpretation}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex gap-1">
            {(["accumulation", "distribution"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                  tab === t
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                }`}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {steps.map(({ key, label }) => (
            <CheckRow key={key} item={side[key] as WyckoffCheckItem | undefined} label={label} />
          ))}
          <ScoreBar score={side.score} isAcc={tab === "accumulation"} />
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{side.overall}</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
