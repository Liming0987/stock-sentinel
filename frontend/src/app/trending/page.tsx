"use client";

import { useState } from "react";
import { TrendingTable } from "@/components/dashboard/trending-table";
import { Button } from "@/components/ui/button";
import { mockTrendingStocks } from "@/lib/mock-data";

const timeframes = ["1h", "6h", "24h", "7d"] as const;

export default function TrendingPage() {
  const [timeframe, setTimeframe] = useState<string>("24h");

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

      <TrendingTable stocks={mockTrendingStocks} />
    </div>
  );
}
