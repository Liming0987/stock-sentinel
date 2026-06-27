"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, MessageSquare, ChevronDown, ChevronUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useVolumeAnalysis, useFundamentals, useStockNews, useLivePrice, useStockDCF, usePosts } from "@/lib/hooks";
import { VolumeHeader } from "@/components/volume/volume-header";
import { PriceVolumeChart } from "@/components/volume/price-volume-chart";
import { OBVChart } from "@/components/volume/obv-chart";
import { ReversalChecklist } from "@/components/volume/reversal-checklist";
import { VolumeTable } from "@/components/volume/volume-table";
import { WatchlistSwitcher } from "@/components/volume/watchlist-switcher";
import { TradeTargetsCard } from "@/components/volume/trade-targets-card";
import { FundamentalsCard } from "@/components/volume/fundamentals-card";
import { VCPCard } from "@/components/volume/vcp-card";
import { NewsCard } from "@/components/volume/news-card";
import { ShortInterestCard } from "@/components/volume/short-interest-card";
import { DCFCard } from "@/components/volume/dcf-card";

function PostCard({ post }: { post: ReturnType<typeof usePosts>["data"]["posts"][0] }) {
  const [expanded, setExpanded] = useState(false);
  const sentimentColor =
    post.sentiment_score > 0.05 ? "text-bullish" :
    post.sentiment_score < -0.05 ? "text-bearish" : "text-muted-foreground";
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
          <a href={post.url} target="_blank" rel="noopener noreferrer" className="text-sm font-medium hover:underline block">
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
          <button onClick={() => setExpanded((v) => !v)} className="text-[11px] text-primary hover:underline">
            {expanded ? "Show less" : "Show more"}
          </button>
        </>
      )}
    </div>
  );
}

function SectionSkeleton({ title }: { title: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-48 w-full animate-pulse rounded bg-muted" />
      </CardContent>
    </Card>
  );
}

export default function VolumeAnalysisPage() {
  const params = useParams();
  const ticker = (params?.ticker as string ?? "").toUpperCase();
  const [period, setPeriod] = useState("90d");
  const [postsOpen, setPostsOpen] = useState(false);
  const [volumeHistoryOpen, setVolumeHistoryOpen] = useState(false);
  const { data, loading } = useVolumeAnalysis(ticker, period);
  const { data: fundamentals, loading: fundLoading } = useFundamentals(ticker);
  const { data: newsData, loading: newsLoading } = useStockNews(ticker);
  const { price: livePrice, marketOpen } = useLivePrice(ticker);
  const { data: dcfData, loading: dcfLoading } = useStockDCF(ticker);
  const { data: postsData } = usePosts(ticker);

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            href="/watchlist"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Watchlist
          </Link>
          <span className="text-muted-foreground">/</span>
          <span className="text-sm font-medium">{ticker} Analysis</span>
        </div>
        <WatchlistSwitcher currentTicker={ticker} />
      </div>

      <VolumeHeader data={data} loading={loading} />

      {loading ? (
        <>
          <SectionSkeleton title="Price & Volume" />
          <SectionSkeleton title="On-Balance Volume (OBV)" />
          <SectionSkeleton title="Wyckoff Structural Analysis" />
          <SectionSkeleton title="Trade Targets" />
          <SectionSkeleton title="Volume History" />
        </>
      ) : data ? (
        <>
          <PriceVolumeChart
            data={data.history}
            selectedPeriod={period}
            onPeriodChange={setPeriod}
            tradingRange={data.wyckoff?.trading_range}
            vcp={data.vcp}
            vcpHistory={data.vcp_history}
            livePrice={livePrice}
            marketOpen={marketOpen}
          />
          <OBVChart data={data.history} />
          {data.vcp && <VCPCard vcp={data.vcp} />}
          <ReversalChecklist wyckoff={data.wyckoff} />
          {data.short_interest?.show && (
            <ShortInterestCard data={data.short_interest} ticker={ticker} />
          )}
          <TradeTargetsCard
            pnf={data.pnf}
            swingEntry={data.swing_entry}
            longtermEntry={data.longterm_entry}
          />
          <DCFCard data={dcfData} loading={dcfLoading} />
          <FundamentalsCard data={fundamentals} loading={fundLoading} />
          <NewsCard news={newsData.news} loading={newsLoading} ticker={ticker} />
          <Card>
            <CardHeader
              className="cursor-pointer select-none"
              onClick={() => setVolumeHistoryOpen((v) => !v)}
            >
              <CardTitle className="flex items-center justify-between text-base">
                <span>Volume History</span>
                {volumeHistoryOpen ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
              </CardTitle>
            </CardHeader>
            {volumeHistoryOpen && (
              <CardContent>
                <VolumeTable data={data.history} ticker={ticker} />
              </CardContent>
            )}
          </Card>

          <Card>
            <CardHeader
              className="cursor-pointer select-none"
              onClick={() => setPostsOpen((v) => !v)}
            >
              <CardTitle className="flex items-center justify-between text-base">
                <span className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-primary" />
                  Recent Posts & Mentions
                </span>
                {postsOpen ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
              </CardTitle>
            </CardHeader>
            {postsOpen && (
              <CardContent className="space-y-3">
                {postsData.posts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No recent posts found for {ticker}.</p>
                ) : (
                  postsData.posts.map((post) => (
                    <PostCard key={post.id} post={post} />
                  ))
                )}
              </CardContent>
            )}
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No volume data available for {ticker}.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
