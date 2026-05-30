"use client";

import {
  TrendingUp,
  MessageSquare,
  Signal,
  Star,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { formatNumber } from "@/lib/utils";

interface StatsCardsProps {
  totalMentions: number;
  trendingCount: number;
  activeSignals: number;
  watchlistCount: number;
}

export function StatsCards({
  totalMentions,
  trendingCount,
  activeSignals,
  watchlistCount,
}: StatsCardsProps) {
  const stats = [
    {
      label: "Total Mentions (24h)",
      value: formatNumber(totalMentions),
      icon: MessageSquare,
      color: "text-blue-500",
      bgColor: "bg-blue-500/10",
    },
    {
      label: "Trending Stocks",
      value: trendingCount.toString(),
      icon: TrendingUp,
      color: "text-emerald-500",
      bgColor: "bg-emerald-500/10",
    },
    {
      label: "Active Signals",
      value: activeSignals.toString(),
      icon: Signal,
      color: "text-amber-500",
      bgColor: "bg-amber-500/10",
    },
    {
      label: "Watchlist",
      value: watchlistCount.toString(),
      icon: Star,
      color: "text-purple-500",
      bgColor: "bg-purple-500/10",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => (
        <Card key={stat.label}>
          <CardContent className="flex items-center gap-4 p-5">
            <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${stat.bgColor}`}>
              <stat.icon className={`h-6 w-6 ${stat.color}`} />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">{stat.label}</p>
              <p className="text-2xl font-bold">{stat.value}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
