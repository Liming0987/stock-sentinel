"use client";

import { useState } from "react";
import Link from "next/link";
import { Clock, CheckCircle2, XCircle, Timer, Signal as SignalIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatPrice, timeAgo } from "@/lib/utils";
import { mockSignals, type Signal } from "@/lib/mock-data";

const pastSignals: Signal[] = [
  {
    id: 10, ticker: "AMD", name: "Advanced Micro Devices", signal_type: "BUY",
    confidence: 0.76, entry_low: 155.0, entry_high: 160.0, stop_loss: 148.0, target: 175.0,
    reasoning: ["RSI at 27", "Volume 1.8x average"],
    created_at: new Date(Date.now() - 5 * 86400000).toISOString(),
    expires_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    outcome: "hit_target",
  },
  {
    id: 11, ticker: "TSLA", name: "Tesla, Inc.", signal_type: "BUY",
    confidence: 0.62, entry_low: 330.0, entry_high: 338.0, stop_loss: 318.0, target: 360.0,
    reasoning: ["Sentiment surge", "MACD crossover"],
    created_at: new Date(Date.now() - 7 * 86400000).toISOString(),
    expires_at: new Date(Date.now() - 5 * 86400000).toISOString(),
    outcome: "hit_stop",
  },
  {
    id: 12, ticker: "MSFT", name: "Microsoft Corporation", signal_type: "HOLD",
    confidence: 0.58, entry_low: 420.0, entry_high: 428.0, stop_loss: 410.0, target: 445.0,
    reasoning: ["Moderate sentiment"],
    created_at: new Date(Date.now() - 10 * 86400000).toISOString(),
    expires_at: new Date(Date.now() - 8 * 86400000).toISOString(),
    outcome: "expired",
  },
];

function OutcomeIcon({ outcome }: { outcome?: string | null }) {
  if (outcome === "hit_target") return <CheckCircle2 className="h-4 w-4 text-bullish" />;
  if (outcome === "hit_stop") return <XCircle className="h-4 w-4 text-bearish" />;
  if (outcome === "expired") return <Timer className="h-4 w-4 text-muted-foreground" />;
  return <Clock className="h-4 w-4 text-primary" />;
}

function SignalRow({ signal, showOutcome }: { signal: Signal; showOutcome: boolean }) {
  return (
    <Link
      href={`/stock/${signal.ticker}`}
      className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-accent/50"
    >
      <div className="flex items-center gap-4">
        {showOutcome && <OutcomeIcon outcome={signal.outcome} />}
        <Badge variant={signal.signal_type === "BUY" ? "bullish" : "neutral"}>
          {signal.signal_type}
        </Badge>
        <div>
          <span className="font-semibold">{signal.ticker}</span>
          <span className="ml-2 text-xs text-muted-foreground">{signal.name}</span>
        </div>
      </div>

      <div className="flex items-center gap-8 text-sm">
        <div className="text-right">
          <div className="text-xs text-muted-foreground">Entry</div>
          <div className="font-mono">{formatPrice(signal.entry_low)} – {formatPrice(signal.entry_high)}</div>
        </div>
        <div className="text-right">
          <div className="text-xs text-muted-foreground">Stop</div>
          <div className="font-mono text-bearish">{formatPrice(signal.stop_loss)}</div>
        </div>
        <div className="text-right">
          <div className="text-xs text-muted-foreground">Target</div>
          <div className="font-mono text-bullish">{formatPrice(signal.target)}</div>
        </div>
        <div className="text-right">
          <div className="text-xs text-muted-foreground">Confidence</div>
          <div className="font-semibold">{(signal.confidence * 100).toFixed(0)}%</div>
        </div>
        <div className="text-right text-xs text-muted-foreground">
          {timeAgo(signal.created_at)}
        </div>
      </div>
    </Link>
  );
}

export default function SignalsPage() {
  const [tab, setTab] = useState<"active" | "history">("active");

  const hitCount = pastSignals.filter((s) => s.outcome === "hit_target").length;
  const hitRate = pastSignals.length > 0 ? ((hitCount / pastSignals.length) * 100).toFixed(0) : "0";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Signals</h1>
        <p className="text-sm text-muted-foreground">
          Buy/hold recommendations from the multi-factor analysis engine
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="flex items-center gap-3 p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <SignalIcon className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Active</p>
              <p className="text-2xl font-bold">{mockSignals.length}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-bullish/10">
              <CheckCircle2 className="h-5 w-5 text-bullish" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Hit Rate</p>
              <p className="text-2xl font-bold">{hitRate}%</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
              <Timer className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Past</p>
              <p className="text-2xl font-bold">{pastSignals.length}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex gap-1 rounded-lg border p-1 w-fit">
        <Button variant={tab === "active" ? "default" : "ghost"} size="sm" onClick={() => setTab("active")}>
          Active ({mockSignals.length})
        </Button>
        <Button variant={tab === "history" ? "default" : "ghost"} size="sm" onClick={() => setTab("history")}>
          History ({pastSignals.length})
        </Button>
      </div>

      <div className="space-y-3">
        {tab === "active" ? (
          mockSignals.length === 0 ? (
            <p className="text-sm text-muted-foreground">No active signals right now.</p>
          ) : (
            mockSignals.map((s) => <SignalRow key={s.id} signal={s} showOutcome={false} />)
          )
        ) : (
          pastSignals.map((s) => <SignalRow key={s.id} signal={s} showOutcome={true} />)
        )}
      </div>
    </div>
  );
}
