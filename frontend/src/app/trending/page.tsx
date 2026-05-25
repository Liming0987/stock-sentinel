"use client";

import { useState } from "react";
import { TrendingTable } from "@/components/dashboard/trending-table";
import { Button } from "@/components/ui/button";
import { useTrending } from "@/lib/hooks";

const timeframes = ["1h", "6h", "24h", "7d"] as const;

export default function TrendingPage() {
  const [timeframe, setTimeframe] = useState<string>("24h");
  const { data: trending, loading } = useTrending(timeframe);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Trending Stocks</h1>
          <p className="text-sm text-muted-foreground">
            Most discussed stocks ranked by mention velocity, sentiment & engagement
          </p>
        </div>
        <div className="flex gap-1 rounded-lg border p-1">
          {timeframes.map((tf) => (
            <Button
              key={tf}
              variant={timeframe === tf ? "default" : "ghost"}
              size="sm"
              onClick={() => setTimeframe(tf)}
              className="text-xs"
            >
              {tf}
            </Button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-muted-foreground text-center py-8">Loading...</p>
      ) : (
        <TrendingTable stocks={trending.stocks} />
      )}
    </div>
  );
}
