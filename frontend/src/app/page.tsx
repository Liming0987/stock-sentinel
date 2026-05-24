"use client";

import { StatsCards } from "@/components/dashboard/stats-cards";
import { TrendingTable } from "@/components/dashboard/trending-table";
import { SignalsCard } from "@/components/dashboard/signals-card";
import { SentimentChart } from "@/components/dashboard/sentiment-chart";
import {
  mockTrendingStocks,
  mockSignals,
  mockWatchlist,
  mockSentimentHistory,
} from "@/lib/mock-data";

export default function DashboardPage() {
  const totalMentions = mockTrendingStocks.reduce((sum, s) => sum + s.mention_count, 0);

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
        trendingCount={mockTrendingStocks.length}
        activeSignals={mockSignals.length}
        watchlistCount={mockWatchlist.length}
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <SentimentChart data={mockSentimentHistory} />
        </div>
        <div>
          <SignalsCard signals={mockSignals} />
        </div>
      </div>

      <TrendingTable stocks={mockTrendingStocks} compact />
    </div>
  );
}
