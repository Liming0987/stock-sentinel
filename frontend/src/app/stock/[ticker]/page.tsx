"use client";

import { useParams } from "next/navigation";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import { ArrowUpRight, ArrowDownRight, Star, ExternalLink, MessageSquare } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SentimentGauge } from "@/components/dashboard/sentiment-gauge";
import {
  formatPrice,
  formatPercent,
  formatNumber,
  sentimentLabel,
  timeAgo,
} from "@/lib/utils";
import {
  mockTrendingStocks,
  mockSignals,
  mockSentimentHistory,
  mockPriceData,
} from "@/lib/mock-data";

const mockPosts = [
  {
    id: 1, source: "reddit", subreddit: "wallstreetbets",
    title: "NVDA earnings are going to be absolutely insane",
    author: "diamond_hands_42", score: 1247, sentiment_score: 0.81,
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: 2, source: "reddit", subreddit: "stocks",
    title: "Technical analysis on NVDA - oversold on RSI",
    author: "chart_master", score: 342, sentiment_score: 0.56,
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: 3, source: "stocktwits", subreddit: null,
    title: "Loading up on NVDA calls before earnings, this thing is coiled",
    author: "bullish_trader", score: 89, sentiment_score: 0.72,
    created_at: new Date(Date.now() - 10800000).toISOString(),
  },
  {
    id: 4, source: "reddit", subreddit: "investing",
    title: "Is NVDA still a buy at these levels? P/E concerns",
    author: "value_investor_99", score: 156, sentiment_score: -0.12,
    created_at: new Date(Date.now() - 14400000).toISOString(),
  },
];

export default function StockDetailPage() {
  const params = useParams();
  const ticker = (params.ticker as string).toUpperCase();

  const stock = mockTrendingStocks.find((s) => s.ticker === ticker) || {
    ticker,
    name: ticker,
    price: 131.28,
    change_pct: 3.42,
    mention_count: 1847,
    mention_velocity: 42.3,
    sentiment_score: 0.72,
    trend_score: 0.89,
    volume_ratio: 2.1,
    sources: ["reddit", "stocktwits"],
  };

  const signal = mockSignals.find((s) => s.ticker === ticker);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">{stock.ticker}</h1>
            <span className="text-lg text-muted-foreground">{stock.name}</span>
          </div>
          <div className="mt-1 flex items-center gap-4">
            <span className="text-2xl font-bold font-mono">{formatPrice(stock.price)}</span>
            <span className={`flex items-center gap-0.5 text-lg font-mono ${stock.change_pct >= 0 ? "text-bullish" : "text-bearish"}`}>
              {stock.change_pct >= 0 ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
              {formatPercent(stock.change_pct)}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <Star className="mr-2 h-4 w-4" />
            Watchlist
          </Button>
          <Button variant="outline" size="sm">
            <ExternalLink className="mr-2 h-4 w-4" />
            Yahoo Finance
          </Button>
        </div>
      </div>

      {signal && (
        <Card className="border-bullish/30 bg-bullish/5">
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <Badge variant="bullish">{signal.signal_type}</Badge>
              <span className="font-semibold">{(signal.confidence * 100).toFixed(0)}% confidence</span>
              <span className="text-sm text-muted-foreground">
                Entry: {formatPrice(signal.entry_low)} – {formatPrice(signal.entry_high)}
              </span>
            </div>
            <div className="flex gap-6 text-sm">
              <span>Stop: <span className="font-mono text-bearish">{formatPrice(signal.stop_loss)}</span></span>
              <span>Target: <span className="font-mono text-bullish">{formatPrice(signal.target)}</span></span>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground">Mentions (24h)</p>
            <p className="text-xl font-bold">{formatNumber(stock.mention_count)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground">Velocity</p>
            <p className="text-xl font-bold">{stock.mention_velocity.toFixed(1)}/hr</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground">Sentiment</p>
            <SentimentGauge score={stock.sentiment_score} size="sm" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground">Volume Ratio</p>
            <p className={`text-xl font-bold ${stock.volume_ratio >= 1.5 ? "text-bullish" : ""}`}>
              {stock.volume_ratio.toFixed(1)}x
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Price Chart (30D)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={mockPriceData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickFormatter={(v) => v.slice(5)} />
                  <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                  />
                  <Area type="monotone" dataKey="close" stroke="hsl(var(--primary))" fill="url(#priceGradient)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sentiment & Mentions (30D)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={mockSentimentHistory} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                  />
                  <Bar dataKey="mentions" fill="hsl(var(--primary))" opacity={0.6} radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-primary" />
            Recent Posts & Mentions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {mockPosts.map((post) => (
            <div key={post.id} className="flex items-start justify-between rounded-lg border p-3 transition-colors hover:bg-accent/50">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="secondary" className="text-[10px]">{post.source}</Badge>
                  {post.subreddit && <span className="text-xs text-muted-foreground">r/{post.subreddit}</span>}
                  <span className="text-xs text-muted-foreground">by u/{post.author}</span>
                  <span className="text-xs text-muted-foreground">{timeAgo(post.created_at)}</span>
                </div>
                <p className="text-sm">{post.title}</p>
              </div>
              <div className="ml-4 flex items-center gap-3">
                <span className="text-xs text-muted-foreground">{post.score} pts</span>
                <Badge variant={post.sentiment_score >= 0.2 ? "bullish" : post.sentiment_score > -0.2 ? "neutral" : "bearish"}>
                  {sentimentLabel(post.sentiment_score)}
                </Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
