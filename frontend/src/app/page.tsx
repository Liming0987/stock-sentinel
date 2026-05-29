"use client";

import { StatsCards } from "@/components/dashboard/stats-cards";
import { TrendingTable } from "@/components/dashboard/trending-table";
import { SignalsCard } from "@/components/dashboard/signals-card";
import { SentimentChart } from "@/components/dashboard/sentiment-chart";
import { useTrending, useSignals, useMarketSentiment } from "@/lib/hooks";

export default function DashboardPage() {
  const { data: trending, loading: trendingLoading } = useTrending();
  const { data: signalsData } = useSignals();
  const { data: marketSentiment } = useMarketSentiment();

  const stocks = trending.stocks;
  const signals = signalsData.signals;
  const totalMentions = stocks.reduce((sum, s) => sum + s.mention_count, 0);

  if (trendingLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Loading market data...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Real-time stock sentiment from Reddit, StockTwits & more
        </p>
      </div>

      <StatsCards
        totalMentions={totalMentions}
        trendingCount={stocks.length}
        activeSignals={signals.length}
        watchlistCount={0}
      />

      {/* Trending table + compact signals sidebar — equal height */}
      <div className="flex flex-col gap-6 xl:flex-row xl:h-[460px]">
        <div className="min-w-0 xl:flex-[2] h-full">
          <TrendingTable stocks={stocks} compact />
        </div>
        <div className="min-w-0 xl:flex-1 h-full">
          <SignalsCard signals={signals} />
        </div>
      </div>

      {/* Sentiment chart spans full width */}
      <SentimentChart data={marketSentiment.history} />
    </div>
  );
}
