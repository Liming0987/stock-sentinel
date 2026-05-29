"use client";

import Link from "next/link";
import { TrendingUp, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SentimentGauge } from "./sentiment-gauge";
import { formatNumber, formatPrice, formatPercent } from "@/lib/utils";
import type { TrendingStock } from "@/lib/mock-data";

interface TrendingTableProps {
  stocks: TrendingStock[];
  compact?: boolean;
}

export function TrendingTable({ stocks, compact = false }: TrendingTableProps) {
  const displayStocks = compact ? stocks.slice(0, 5) : stocks;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between shrink-0">
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          Trending Stocks
        </CardTitle>
        {compact && (
          <Link href="/trending" className="text-sm text-primary hover:underline">
            View all
          </Link>
        )}
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto min-h-0 pt-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-3 font-medium">#</th>
                <th className="pb-3 font-medium">Ticker</th>
                <th className="pb-3 font-medium">Price</th>
                <th className="pb-3 font-medium">Change</th>
                <th className="pb-3 font-medium">Mentions</th>
                {!compact && <th className="pb-3 font-medium">Velocity</th>}
                <th className="pb-3 font-medium">Sentiment</th>
                {!compact && <th className="pb-3 font-medium">Vol Ratio</th>}
                {!compact && <th className="pb-3 font-medium">Sources</th>}
                <th className="pb-3 font-medium">Score</th>
              </tr>
            </thead>
            <tbody>
              {displayStocks.map((stock, i) => (
                <tr key={stock.ticker} className="border-b last:border-0 hover:bg-accent/50 transition-colors">
                  <td className="py-3 text-muted-foreground">{i + 1}</td>
                  <td className="py-3">
                    <Link href={`/stock/${stock.ticker}`} className="group">
                      <span className="font-semibold text-foreground group-hover:text-primary transition-colors">
                        {stock.ticker}
                      </span>
                      {!compact && (
                        <span className="ml-2 text-xs text-muted-foreground">{stock.name}</span>
                      )}
                    </Link>
                  </td>
                  <td className="py-3 font-mono">{formatPrice(stock.price)}</td>
                  <td className="py-3">
                    <span className={`inline-flex items-center gap-0.5 font-mono ${stock.change_pct >= 0 ? "text-bullish" : "text-bearish"}`}>
                      {stock.change_pct >= 0 ? (
                        <ArrowUpRight className="h-3 w-3" />
                      ) : (
                        <ArrowDownRight className="h-3 w-3" />
                      )}
                      {formatPercent(stock.change_pct)}
                    </span>
                  </td>
                  <td className="py-3 font-mono">{formatNumber(stock.mention_count)}</td>
                  {!compact && (
                    <td className="py-3 font-mono text-muted-foreground">
                      {stock.mention_velocity.toFixed(1)}/hr
                    </td>
                  )}
                  <td className="py-3">
                    <SentimentGauge score={stock.sentiment_score} size="sm" />
                  </td>
                  {!compact && (
                    <td className="py-3 font-mono">
                      <span className={stock.volume_ratio >= 1.5 ? "text-bullish font-semibold" : "text-muted-foreground"}>
                        {stock.volume_ratio.toFixed(1)}x
                      </span>
                    </td>
                  )}
                  {!compact && (
                    <td className="py-3">
                      <div className="flex gap-1">
                        {stock.sources.map((s) => (
                          <Badge key={s} variant="secondary" className="text-[10px]">
                            {s}
                          </Badge>
                        ))}
                      </div>
                    </td>
                  )}
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-16 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${stock.trend_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono">{(stock.trend_score * 100).toFixed(0)}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
