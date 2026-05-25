"use client";

import Link from "next/link";
import { Clock, CheckCircle2, XCircle, Timer, Signal as SignalIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatPrice, timeAgo } from "@/lib/utils";
import { type Signal } from "@/lib/mock-data";
import { useSignals } from "@/lib/hooks";

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
  const { data: signalsData, loading } = useSignals();

  const activeSignals = signalsData.signals;

  if (loading) {
    return <p className="text-muted-foreground text-center py-8">Loading signals...</p>;
  }

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
              <p className="text-2xl font-bold">{activeSignals.length}</p>
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
              <p className="text-2xl font-bold">–</p>
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
              <p className="text-2xl font-bold">0</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-3">
        {activeSignals.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4">
            No active signals yet. Signals will be generated once Reddit scraping and analysis are running.
          </p>
        ) : (
          activeSignals.map((s: Signal) => <SignalRow key={s.id} signal={s} showOutcome={false} />)
        )}
      </div>
    </div>
  );
}
