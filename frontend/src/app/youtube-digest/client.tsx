"use client";

import { useState, useEffect } from "react";
import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/layout/page-header";

// ── Types ──────────────────────────────────────────────────────────────────

type Sentiment = "bullish" | "bearish" | "neutral" | "mixed";

type StockMention = {
  channel: string;
  video_title: string;
  video_url: string;
  sentiment: Sentiment;
  conviction: number;
  thesis: string;
  key_points: string[];
  price_target: string | null;
};

type ConsensusItem = {
  symbol: string | null;
  company_name: string | null;
  display: string;
  channel_count: number;
  channels: string[];
  overall_sentiment: Sentiment;
  avg_conviction: number;
  top_thesis: string;
  mentions: StockMention[];
};

type VideoStock = {
  symbol: string | null;
  company_name: string | null;
  sentiment: Sentiment;
  conviction: number;
  thesis: string;
  price_target: string | null;
  key_points: string[];
};

type Analysis = {
  video_id: string;
  channel_name: string;
  video_title: string;
  video_url: string;
  published_at: string;
  duration_minutes: number;
  summary: string;
  macro_topics: string[];
  stocks: VideoStock[];
  key_theses: string[];
  warnings_or_risks: string[];
};

type AllStockEntry = {
  symbol: string | null;
  company_name: string | null;
  display: string;
  mentions: StockMention[];
};

type Source = {
  channel: string;
  title: string;
  url: string;
};

type MacroTopic = {
  title: string;
  description: string;
};

type ReportData = {
  date: string;
  generated_at: string;
  video_count: number;
  stock_count: number;
  consensus: ConsensusItem[];
  analyses: Analysis[];
  all_stocks: AllStockEntry[];
  macro_topics: MacroTopic[];
  sources: Source[];
};

// ── Helpers ────────────────────────────────────────────────────────────────

const SENTIMENT_VARIANT: Record<Sentiment, "bullish" | "bearish" | "neutral" | "secondary"> = {
  bullish: "bullish",
  bearish: "bearish",
  neutral: "neutral",
  mixed: "secondary",
};

function SentimentBadge({ s }: { s: Sentiment }) {
  return (
    <Badge variant={SENTIMENT_VARIANT[s]} className="text-[10px] capitalize">
      {s}
    </Badge>
  );
}

function ConvictionBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-10 rounded-full bg-border overflow-hidden">
        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-muted-foreground">{pct}%</span>
    </div>
  );
}

function TickerDisplay({ symbol, company_name }: { symbol: string | null; company_name: string | null }) {
  return (
    <span>
      {symbol && <span className="font-mono font-semibold">{symbol}</span>}
      {company_name && company_name !== symbol && (
        <span className="ml-1.5 text-muted-foreground font-normal text-sm">{company_name}</span>
      )}
    </span>
  );
}

// ── Tab components ─────────────────────────────────────────────────────────

function ConsensusTab({ data }: { data: ReportData }) {
  if (data.consensus.length === 0) {
    return (
      <div className="rounded-xl border bg-muted/30 py-12 text-center text-sm text-muted-foreground">
        No stocks mentioned by 2+ creators today.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        {data.consensus.length} stock{data.consensus.length !== 1 ? "s" : ""} mentioned by 2 or more creators
      </p>
      <Card className="overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/30">
              <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Stock</th>
              <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Sentiment</th>
              <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Conviction</th>
              <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-muted-foreground hidden sm:table-cell">Channels</th>
              <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-muted-foreground hidden lg:table-cell">Top thesis</th>
            </tr>
          </thead>
          <tbody>
            {data.consensus.map((item) => (
              <tr key={item.display} className="border-b last:border-0 hover:bg-accent/30">
                <td className="px-4 py-3">
                  <TickerDisplay symbol={item.symbol} company_name={item.company_name} />
                </td>
                <td className="px-4 py-3">
                  <SentimentBadge s={item.overall_sentiment} />
                </td>
                <td className="px-4 py-3">
                  <ConvictionBar value={item.avg_conviction} />
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground hidden sm:table-cell">
                  {item.channel_count} · {item.channels.join(", ")}
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground max-w-xs hidden lg:table-cell">
                  {item.top_thesis}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function VideosTab({ data }: { data: ReportData }) {
  const dates = Array.from(new Set(data.analyses.map((a) => a.published_at.slice(0, 10)))).sort().reverse();
  const [dateFilter, setDateFilter] = useState<string>("all");
  const visible = dateFilter === "all"
    ? data.analyses
    : data.analyses.filter((a) => a.published_at.slice(0, 10) === dateFilter);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">{visible.length} video{visible.length !== 1 ? "s" : ""}</span>
        {dates.length > 1 && (
          <div className="flex flex-wrap gap-1.5 ml-auto">
            <button
              onClick={() => setDateFilter("all")}
              className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-colors ${
                dateFilter === "all" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-accent"
              }`}
            >
              All dates
            </button>
            {dates.map((d) => (
              <button
                key={d}
                onClick={() => setDateFilter(d)}
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-colors ${
                  dateFilter === d ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-accent"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        )}
      </div>
      {visible.map((a) => (
        <Card key={a.video_id}>
          <CardContent className="p-5 space-y-3">
            <div>
              <p className="text-[11px] text-muted-foreground font-medium">{a.channel_name}</p>
              <a
                href={a.video_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-sm hover:text-primary transition-colors flex items-start gap-1 mt-0.5"
              >
                {a.video_title}
                <ExternalLink className="h-3 w-3 shrink-0 mt-0.5 text-muted-foreground" />
              </a>
              <p className="text-[10px] text-muted-foreground mt-0.5">
                {a.published_at.slice(0, 10)} · {Math.round(a.duration_minutes)}m
              </p>
            </div>

            {a.summary && (
              <p className="text-xs text-muted-foreground leading-relaxed line-clamp-4">
                {a.summary.split("\n")[0]}
              </p>
            )}

            {a.stocks.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {a.stocks.map((s, i) => (
                  <div key={i} className="flex items-center gap-1 rounded border px-2 py-0.5 text-xs bg-card">
                    <span className="font-mono font-semibold">{s.symbol ?? s.company_name}</span>
                    <SentimentBadge s={s.sentiment} />
                  </div>
                ))}
              </div>
            )}

            {a.key_theses.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">Key takeaways</p>
                <ul className="space-y-0.5">
                  {a.key_theses.map((t, i) => (
                    <li key={i} className="flex gap-2 text-xs text-muted-foreground">
                      <span className="mt-1.5 h-1 w-1 rounded-full bg-primary/50 shrink-0" />
                      {t}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function StocksTab({ data }: { data: ReportData }) {
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">{data.stock_count} stock{data.stock_count !== 1 ? "s" : ""} mentioned</p>
      {data.all_stocks.map((stock) => (
        <Card key={stock.display}>
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center justify-between">
              <TickerDisplay symbol={stock.symbol} company_name={stock.company_name} />
              <span className="text-[10px] text-muted-foreground">
                {stock.mentions.length} mention{stock.mentions.length !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="space-y-3">
              {stock.mentions.map((m, i) => (
                <div key={i} className="border-t pt-3 first:border-0 first:pt-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="text-xs font-semibold">{m.channel}</span>
                    <SentimentBadge s={m.sentiment} />
                    <ConvictionBar value={m.conviction} />
                    {m.price_target && (
                      <span className="text-[10px] text-muted-foreground">Target: {m.price_target}</span>
                    )}
                  </div>
                  {m.thesis && <p className="text-xs text-muted-foreground">{m.thesis}</p>}
                  {m.key_points.length > 0 && (
                    <ul className="mt-1 space-y-0.5">
                      {m.key_points.map((pt, j) => (
                        <li key={j} className="flex gap-2 text-[11px] text-muted-foreground">
                          <span className="mt-1.5 h-1 w-1 rounded-full bg-muted-foreground/50 shrink-0" />
                          {pt}
                        </li>
                      ))}
                    </ul>
                  )}
                  <a
                    href={m.video_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground hover:text-primary"
                  >
                    <ExternalLink className="h-2.5 w-2.5" />
                    {m.video_title}
                  </a>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function MacroTab({ data }: { data: ReportData }) {
  if (data.macro_topics.length === 0) {
    return (
      <div className="rounded-xl border bg-muted/30 py-12 text-center text-sm text-muted-foreground">
        No macro topics recorded.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        {data.macro_topics.length} themes discussed across today&apos;s videos
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {data.macro_topics.map((topic, i) => (
          <Card key={i}>
            <CardContent className="p-4 space-y-1.5">
              <p className="text-sm font-semibold">{topic.title}</p>
              {topic.description ? (
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {topic.description}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground italic">No description available.</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function SourcesTab({ data }: { data: ReportData }) {
  return (
    <Card className="overflow-hidden p-0">
      {data.sources.map((s, i) => (
        <div key={i} className="flex items-start gap-3 border-b last:border-0 px-5 py-3 hover:bg-accent/30">
          <div className="min-w-0">
            <p className="text-[10px] text-muted-foreground">{s.channel}</p>
            <a
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm hover:text-primary transition-colors flex items-center gap-1"
            >
              {s.title}
              <ExternalLink className="h-3 w-3 shrink-0 text-muted-foreground" />
            </a>
          </div>
        </div>
      ))}
    </Card>
  );
}

// ── Main client component ──────────────────────────────────────────────────

const TABS = ["Consensus", "Videos", "Stocks", "Macro", "Sources"] as const;
type Tab = (typeof TABS)[number];

export function YouTubeDigestClient({ dates }: { dates: string[] }) {
  const [selectedDate, setSelectedDate] = useState(dates[0] ?? null);
  const [activeTab, setActiveTab] = useState<Tab>("Consensus");
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedDate) return;
    setLoading(true);
    setError(null);
    setData(null);
    fetch(`/youtube-reports/data/${selectedDate}.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`No report data for ${selectedDate}`);
        return r.json();
      })
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selectedDate]);

  if (dates.length === 0) {
    return (
      <div className="mx-auto max-w-[1180px]">
        <PageHeader
          kicker="Research"
          title="YouTube Digest"
          description="No reports yet — run the daily pipeline to generate the first report."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1180px] space-y-5">
      <PageHeader
        kicker="Research"
        title="YouTube Digest"
        description="AI-generated summaries of finance YouTube content. Not financial advice."
      />

      {/* Date selector */}
      <div className="flex flex-wrap gap-2">
        {dates.map((d) => (
          <button
            key={d}
            onClick={() => { setSelectedDate(d); setActiveTab("Consensus"); }}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              selectedDate === d
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-accent"
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      {/* Report summary strip */}
      {data && !loading && (
        <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground border-b pb-4">
          <span>Generated <strong className="text-foreground">{data.generated_at}</strong></span>
          <span><strong className="text-foreground">{data.video_count}</strong> videos analyzed</span>
          <span><strong className="text-foreground">{data.stock_count}</strong> stocks identified</span>
          {data.consensus.length > 0 && (
            <span><strong className="text-foreground">{data.consensus.length}</strong> consensus pick{data.consensus.length !== 1 ? "s" : ""}</span>
          )}
        </div>
      )}

      {/* Section tabs */}
      <div className="flex gap-0 border-b">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
          Loading…
        </div>
      ) : error ? (
        <div className="rounded-xl border bg-muted/30 py-12 text-center text-sm text-muted-foreground">
          {error}
        </div>
      ) : data ? (
        <>
          {activeTab === "Consensus" && <ConsensusTab data={data} />}
          {activeTab === "Videos" && <VideosTab data={data} />}
          {activeTab === "Stocks" && <StocksTab data={data} />}
          {activeTab === "Macro" && <MacroTab data={data} />}
          {activeTab === "Sources" && <SourcesTab data={data} />}
        </>
      ) : null}
    </div>
  );
}
