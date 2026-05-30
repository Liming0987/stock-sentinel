"use client";

import { useState } from "react";
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
} from "@/lib/utils";
import { useTrendingDetail, usePrices, useSentiment, useSignals, usePosts } from "@/lib/hooks";

function PostCard({ post, sentimentColor }: { post: ReturnType<typeof usePosts>["data"]["posts"][0]; sentimentColor: string }) {
  const [expanded, setExpanded] = useState(false);
  const hasBody = Boolean(post.body);
  return (
    <div className="rounded-lg border p-3 space-y-1">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="secondary" className="text-[10px] capitalize">{post.source}</Badge>
          {post.subreddit && <span className="text-xs text-muted-foreground">r/{post.subreddit}</span>}
          {post.author && <span className="text-xs text-muted-foreground">u/{post.author}</span>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-xs font-mono ${sentimentColor}`}>
            {post.sentiment_score > 0 ? "+" : ""}{(post.sentiment_score * 100).toFixed(0)}%
          </span>
          <span className="text-xs text-muted-foreground">
            {new Date(post.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      {post.title && (
        post.url ? (
          <a href={post.url} target="_blank" rel="noopener noreferrer"
            className="text-sm font-medium hover:underline block">
            {post.title}
          </a>
        ) : (
          <p className="text-sm font-medium">{post.title}</p>
        )
      )}

      {hasBody && (
        <>
          <p className={`text-xs text-muted-foreground whitespace-pre-wrap ${expanded ? "" : "line-clamp-3"}`}>
            {post.body}
          </p>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-[11px] text-primary hover:underline"
          >
            {expanded ? "Show less" : "Show more"}
          </button>
        </>
      )}
    </div>
  );
}

export default function StockDetailPage() {
  const params = useParams();
  const ticker = (params.ticker as string).toUpperCase();

  const { data: stock, loading: stockLoading } = useTrendingDetail(ticker);
  const { data: priceData } = usePrices(ticker);
  const { data: sentimentData } = useSentiment(ticker);
  const { data: signalsData } = useSignals();
  const { data: postsData } = usePosts(ticker);

  const signal = signalsData.signals.find((s) => s.ticker === ticker);
  const candles = priceData.candles;
  const sentimentHistory = sentimentData.history;
  const posts = postsData.posts;

  if (stockLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Loading {ticker} data...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold sm:text-3xl">{stock.ticker}</h1>
            <span className="text-sm text-muted-foreground sm:text-lg">{stock.name}</span>
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
            <Star className="mr-1 h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Watchlist</span>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a
              href={`https://finance.yahoo.com/quote/${ticker}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="mr-1 h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">Yahoo Finance</span>
            </a>
          </Button>
        </div>
      </div>

      {signal && (
        <Card className="border-bullish/30 bg-bullish/5">
          <CardContent className="p-4 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="bullish">{signal.signal_type}</Badge>
              <span className="font-semibold">{(signal.confidence * 100).toFixed(0)}% confidence</span>
              <span className="text-sm text-muted-foreground">
                Entry: {formatPrice(signal.entry_low)} – {formatPrice(signal.entry_high)}
              </span>
            </div>
            <div className="flex gap-4 text-sm">
              <span>Stop: <span className="font-mono text-bearish">{formatPrice(signal.stop_loss)}</span></span>
              <span>Target: <span className="font-mono text-bullish">{formatPrice(signal.target)}</span></span>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
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
            <SentimentGauge score={stock.sentiment_score ?? 0} size="sm" />
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
            {candles.length === 0 ? (
              <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
                Price data unavailable for {ticker}
              </div>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={candles} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
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
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sentiment & Mentions (30D)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sentimentHistory} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
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
          {posts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent posts found for {ticker}.</p>
          ) : (
            posts.map((post) => {
              const sentimentColor =
                post.sentiment_score > 0.05
                  ? "text-bullish"
                  : post.sentiment_score < -0.05
                  ? "text-bearish"
                  : "text-muted-foreground";
              return <PostCard key={post.id} post={post} sentimentColor={sentimentColor} />;
            })
          )}
        </CardContent>
      </Card>
    </div>
  );
}
