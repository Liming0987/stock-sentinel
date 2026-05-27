"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "./api";
import type { TrendingStock, Signal, WatchlistItem } from "./mock-data";

interface TrendingResponse {
  timeframe: string;
  stocks: TrendingStock[];
  updated_at: string | null;
}

interface SignalsResponse {
  signals: Signal[];
}

interface SentimentResponse {
  ticker: string;
  current_score: number;
  period: string;
  history: { date: string; sentiment: number; mentions: number }[];
}

interface PriceResponse {
  ticker: string;
  name: string;
  period: string;
  interval: string;
  candles: { date: string; open: number; high: number; low: number; close: number; volume: number }[];
  indicators: Record<string, number>;
}

function useApi<T>(fetcher: () => Promise<T>, fallback: T) {
  const [data, setData] = useState<T>(fallback);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(() => {
    setLoading(true);
    setError(null);
    fetcher()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [fetcher]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}

export function useTrending(timeframe = "24h", limit = 20) {
  const fetcher = useCallback(
    () => api.trending.list(timeframe, limit) as Promise<TrendingResponse>,
    [timeframe, limit]
  );
  return useApi(fetcher, { timeframe, stocks: [], updated_at: null } as TrendingResponse);
}

export function useSignals() {
  const fetcher = useCallback(() => api.signals.active() as Promise<SignalsResponse>, []);
  return useApi(fetcher, { signals: [] } as SignalsResponse);
}

export function useSentiment(ticker: string, period = "7d") {
  const fetcher = useCallback(
    () => api.sentiment.get(ticker, period) as Promise<SentimentResponse>,
    [ticker, period]
  );
  return useApi(fetcher, { ticker, current_score: 0, period, history: [] } as SentimentResponse);
}

export function usePrices(ticker: string, period = "1M", interval = "1d") {
  const fetcher = useCallback(
    () => api.prices.get(ticker, period, interval) as Promise<PriceResponse>,
    [ticker, period, interval]
  );
  return useApi(fetcher, { ticker, name: "", period, interval, candles: [], indicators: {} } as PriceResponse);
}

interface MarketSentimentResponse {
  period: string;
  history: { date: string; sentiment: number; mentions: number }[];
}

interface WatchlistResponse {
  stocks: WatchlistItem[];
}

export function useMarketSentiment(period = "7d") {
  const fetcher = useCallback(
    () => api.sentiment.market(period) as Promise<MarketSentimentResponse>,
    [period]
  );
  return useApi(fetcher, { period, history: [] } as MarketSentimentResponse);
}

export function useWatchlist() {
  const fetcher = useCallback(() => api.watchlist.list() as Promise<WatchlistResponse>, []);
  return useApi(fetcher, { stocks: [] } as WatchlistResponse);
}

export function useTrendingDetail(ticker: string) {
  const fetcher = useCallback(
    () => api.trending.detail(ticker) as Promise<TrendingStock & { indicators: Record<string, number> }>,
    [ticker]
  );
  return useApi(fetcher, {
    ticker, name: "", price: 0, change_pct: 0, mention_count: 0,
    mention_velocity: 0, sentiment_score: 0, trend_score: 0, volume_ratio: 1, sources: [], indicators: {},
  } as TrendingStock & { indicators: Record<string, number> });
}
