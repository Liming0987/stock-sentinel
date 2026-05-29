"use client";

import Link from "next/link";
import { Signal as SignalIcon, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatPrice, timeAgo } from "@/lib/utils";
import type { Signal } from "@/lib/mock-data";

interface SignalsCardProps {
  signals: Signal[];
}

export function SignalsCard({ signals }: SignalsCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <SignalIcon className="h-5 w-5 text-primary" />
          Active Signals
        </CardTitle>
        <Link href="/signals" className="text-sm text-primary hover:underline">
          View all
        </Link>
      </CardHeader>
      <CardContent>
        {signals.length === 0 ? (
          <p className="text-sm text-muted-foreground">No active signals</p>
        ) : (
          <div className="max-h-[460px] overflow-y-auto space-y-3 pr-1">
          {signals.map((signal) => (
            <Link
              key={signal.id}
              href={`/stock/${signal.ticker}`}
              className="block rounded-lg border p-4 transition-colors hover:bg-accent/50"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Badge
                    variant={signal.signal_type === "BUY" ? "bullish" : "neutral"}
                  >
                    {signal.signal_type}
                  </Badge>
                  <div>
                    <span className="font-semibold">{signal.ticker}</span>
                    <span className="ml-2 text-xs text-muted-foreground">{signal.name}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold">
                    {(signal.confidence * 100).toFixed(0)}% confidence
                  </div>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {timeAgo(signal.created_at)}
                  </div>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-3 gap-4 text-xs">
                <div>
                  <span className="text-muted-foreground">Entry Zone</span>
                  <p className="font-mono font-medium">
                    {formatPrice(signal.entry_low)} – {formatPrice(signal.entry_high)}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">Stop Loss</span>
                  <p className="font-mono font-medium text-bearish">
                    {formatPrice(signal.stop_loss)}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">Target</span>
                  <p className="font-mono font-medium text-bullish">
                    {formatPrice(signal.target)}
                  </p>
                </div>
              </div>

              <div className="mt-2 flex flex-wrap gap-1">
                {signal.reasoning.map((r, i) => (
                  <Badge key={i} variant="secondary" className="text-[10px]">
                    {r}
                  </Badge>
                ))}
              </div>
            </Link>
          ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
