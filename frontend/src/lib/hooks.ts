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

interface Post {
  id: number;
  source: string;
  subreddit: string | null;
  title: string;
  body: string;
  author: string;
  score: number;
  sentiment_score: number;
  created_at: string;
  url: string;
}

interface PostsResponse {
  ticker: string;
  posts: Post[];
}

export function usePosts(ticker: string, limit = 20) {
  const fetcher = useCallback(
    () => api.sentiment.posts(ticker, limit) as Promise<PostsResponse>,
    [ticker, limit]
  );
  return useApi(fetcher, { ticker, posts: [] } as PostsResponse);
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

interface StrategyMetrics {
  id?: number;
  name: string;
  description: string;
  enabled: boolean;
  paper: boolean;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  unrealized_pnl: number;
  avg_return_pct: number;
  last_run_at: string | null;
}

interface StrategiesResponse {
  strategies: StrategyMetrics[];
}

interface StrategyTrade {
  id: number;
  ticker: string;
  side: string;
  qty: number;
  entry_price: number;
  exit_price: number | null;
  stop_loss: number | null;
  target: number | null;
  status: string;
  pnl: number | null;
  return_pct: number | null;
  reasoning: string | null;
  opened_at: string | null;
  closed_at: string | null;
}

interface StrategyTradesResponse {
  strategy: string;
  trades: StrategyTrade[];
}

interface EquityCurvePoint {
  date: string;
  cumulative_pnl: number;
  daily_pnl: number;
}

interface EquityCurveResponse {
  curves: Record<string, EquityCurvePoint[]>;
}

interface AlpacaAccountResponse {
  configured: boolean;
  paper?: boolean;
  cash?: number;
  portfolio_value?: number;
  buying_power?: number;
  equity?: number;
  positions?: Array<{
    symbol: string;
    qty: number;
    avg_entry_price: number;
    current_price: number | null;
    unrealized_pl: number;
  }>;
  message?: string;
}

export function useStrategies() {
  const fetcher = useCallback(() => api.strategies.list() as Promise<StrategiesResponse>, []);
  return useApi(fetcher, { strategies: [] } as StrategiesResponse);
}

export function useStrategyTrades(name: string, status = "all") {
  const fetcher = useCallback(
    () => api.strategies.trades(name, status) as Promise<StrategyTradesResponse>,
    [name, status]
  );
  return useApi(fetcher, { strategy: name, trades: [] } as StrategyTradesResponse);
}

export function useEquityCurve() {
  const fetcher = useCallback(() => api.strategies.equityCurve() as Promise<EquityCurveResponse>, []);
  return useApi(fetcher, { curves: {} } as EquityCurveResponse);
}

export function useAlpacaAccount() {
  const fetcher = useCallback(() => api.strategies.alpacaAccount() as Promise<AlpacaAccountResponse>, []);
  return useApi(fetcher, { configured: false } as AlpacaAccountResponse);
}

export interface LivePosition {
  strategy: string;
  ticker: string;
  qty: number;
  entry_price: number;
  current_price: number;
  stop_loss: number | null;
  target: number | null;
  unrealized_pnl: number;
  return_pct: number;
  /** "db" = tracked by strategy runner; "alpaca" = in Alpaca but no DB record yet */
  source?: "db" | "alpaca";
}

interface ByStrategy {
  unrealized_pnl: number;
  position_count: number;
}

export interface LivePositionsResponse {
  timestamp: string;
  positions: LivePosition[];
  by_strategy: Record<string, ByStrategy>;
  market_open: boolean;
}

export interface LiveHistoryPoint {
  time: string;
  [key: string]: number | string;
}

export function useLivePositions() {
  const [data, setData] = useState<LivePositionsResponse>({
    timestamp: "",
    positions: [],
    by_strategy: {},
    market_open: false,
  });
  const [history, setHistory] = useState<LiveHistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    let timerId: ReturnType<typeof setTimeout>;

    const appendHistory = (result: LivePositionsResponse) => {
      const time = new Date(result.timestamp || Date.now()).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
      const point: LiveHistoryPoint = { time };
      for (const [name, s] of Object.entries(result.by_strategy)) {
        point[name] = s.unrealized_pnl;
      }
      setHistory((prev) => [...prev, point].slice(-120));
    };

    const fetchOnce = async () => {
      try {
        const result = await (api.strategies.livePositions() as Promise<LivePositionsResponse>);
        if (!active) return;
        setData(result);
        setLoading(false);
        return result;
      } catch {
        if (active) setLoading(false);
        return null;
      }
    };

    const pollMarketOpen = async () => {
      // Poll prices every 5s and grow the chart while the market is open
      const result = await fetchOnce();
      if (!active) return;

      if (result?.market_open) {
        appendHistory(result);
        timerId = setTimeout(pollMarketOpen, 5000);
      } else {
        // Market just closed — stop price polling, switch to status-only checks
        scheduleStatusCheck();
      }
    };

    const scheduleStatusCheck = () => {
      // Re-check every 5 minutes whether the market has opened; don't touch history
      timerId = setTimeout(async () => {
        if (!active) return;
        const result = await fetchOnce();
        if (result?.market_open) {
          // Market opened — start live polling
          pollMarketOpen();
        } else {
          scheduleStatusCheck();
        }
      }, 5 * 60 * 1000);
    };

    // Initial fetch — determines which mode to enter
    fetchOnce().then((result) => {
      if (!active || !result) return;
      if (result.market_open) {
        appendHistory(result);
        timerId = setTimeout(pollMarketOpen, 5000);
      } else {
        // Market closed — show last-known prices, start quiet status checks
        scheduleStatusCheck();
      }
    });

    return () => {
      active = false;
      clearTimeout(timerId);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, history, loading };
}

export interface AppNotification {
  id: string;
  type: "signal" | "trade_open" | "trade_close";
  ticker: string;
  message: string;
  timestamp: string;
  meta: Record<string, unknown>;
}

const LAST_SEEN_KEY = "notif_last_seen";

export function useNotifications() {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [lastSeen, setLastSeen] = useState<string>(
    () => (typeof window !== "undefined" ? localStorage.getItem(LAST_SEEN_KEY) : null) ?? new Date(0).toISOString()
  );

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const res = await api.notifications.list() as { notifications: AppNotification[] };
        if (active) setNotifications(res.notifications);
      } catch { /* ignore */ }
      if (active) setTimeout(poll, 30000);
    };
    poll();
    return () => { active = false; };
  }, []);

  const unreadCount = notifications.filter(
    (n) => n.timestamp > lastSeen
  ).length;

  const markAllRead = () => {
    const now = new Date().toISOString();
    setLastSeen(now);
    localStorage.setItem(LAST_SEEN_KEY, now);
  };

  return { notifications, unreadCount, markAllRead };
}
