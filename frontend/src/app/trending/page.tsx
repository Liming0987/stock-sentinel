"use client";

import { useState } from "react";
import { TrendingTable } from "@/components/dashboard/trending-table";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/page-header";
import { useTrending } from "@/lib/hooks";

const timeframes = ["1h", "6h", "24h", "7d"] as const;

export default function TrendingPage() {
  const [timeframe, setTimeframe] = useState<string>("24h");
  const { data: trending, loading } = useTrending(timeframe);

  return (
    <div className="mx-auto max-w-[1180px] space-y-[18px]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <PageHeader
          kicker="Markets"
          title="Trending"
          description="Ranked by a trend score that weighs mention velocity, sentiment and unusual volume."
        />
        <div className="flex gap-1 rounded-lg border p-1 self-start sm:self-auto">
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
