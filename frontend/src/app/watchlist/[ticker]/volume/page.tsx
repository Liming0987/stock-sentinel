"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useVolumeAnalysis, useFundamentals, useStockNews, useLivePrice, useStockDCF } from "@/lib/hooks";
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
  const { data, loading } = useVolumeAnalysis(ticker, period);
  const { data: fundamentals, loading: fundLoading } = useFundamentals(ticker);
  const { data: newsData, loading: newsLoading } = useStockNews(ticker);
  const { price: livePrice, marketOpen } = useLivePrice(ticker);
  const { data: dcfData, loading: dcfLoading } = useStockDCF(ticker);

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
          <span className="text-sm font-medium">{ticker} Volume Analysis</span>
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
            <CardHeader>
              <CardTitle className="text-base">Volume History</CardTitle>
            </CardHeader>
            <CardContent>
              <VolumeTable data={data.history} />
            </CardContent>
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
