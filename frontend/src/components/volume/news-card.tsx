"use client";

import { useState } from "react";
import Image from "next/image";
import { ExternalLink, ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { StockNewsItem } from "@/lib/hooks";

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function NewsItem({ item }: { item: StockNewsItem }) {
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex gap-3 rounded-lg p-3 transition-colors hover:bg-accent/40"
    >
      {item.image_url && (
        <Image
          src={item.image_url}
          alt=""
          width={80}
          height={56}
          unoptimized
          className="h-14 w-20 shrink-0 rounded-md object-cover"
        />
      )}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium leading-snug group-hover:text-primary line-clamp-2">
          {item.title}
        </p>
        {item.summary && (
          <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{item.summary}</p>
        )}
        <div className="mt-1.5 flex items-center gap-2 text-[11px] text-muted-foreground">
          <span className="font-medium">{item.source}</span>
          {item.published_at && (
            <>
              <span>·</span>
              <span>{timeAgo(item.published_at)}</span>
            </>
          )}
          <ExternalLink className="ml-auto h-3 w-3 shrink-0 opacity-0 group-hover:opacity-60 transition-opacity" />
        </div>
      </div>
    </a>
  );
}

interface NewsCardProps {
  news: StockNewsItem[];
  loading: boolean;
  ticker: string;
}

export function NewsCard({ news, loading, ticker }: NewsCardProps) {
  const [open, setOpen] = useState(false);
  return (
    <Card>
      <CardHeader
        className="cursor-pointer select-none"
        onClick={() => setOpen((v) => !v)}
      >
        <CardTitle className="flex items-center justify-between text-base">
          <span>Latest News — {ticker}</span>
          {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </CardTitle>
      </CardHeader>
      {open && (
        <CardContent className="p-2">
          {loading ? (
            <div className="space-y-2 p-2">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="flex gap-3">
                  <div className="h-14 w-20 shrink-0 animate-pulse rounded-md bg-muted" />
                  <div className="flex-1 space-y-2 pt-1">
                    <div className="h-3 w-full animate-pulse rounded bg-muted" />
                    <div className="h-3 w-4/5 animate-pulse rounded bg-muted" />
                    <div className="h-2.5 w-1/3 animate-pulse rounded bg-muted" />
                  </div>
                </div>
              ))}
            </div>
          ) : news.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No recent news found for {ticker}.
            </p>
          ) : (
            <div className="divide-y">
              {news.map((item, i) => (
                <NewsItem key={item.url || i} item={item} />
              ))}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
