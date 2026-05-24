export interface TrendingStock {
  ticker: string;
  name: string;
  price: number;
  change_pct: number;
  mention_count: number;
  mention_velocity: number;
  sentiment_score: number;
  trend_score: number;
  volume_ratio: number;
  sources: string[];
}

export interface Signal {
  id: number;
  ticker: string;
  name: string;
  signal_type: "BUY" | "HOLD" | "AVOID";
  confidence: number;
  entry_low: number;
  entry_high: number;
  stop_loss: number;
  target: number;
  reasoning: string[];
  created_at: string;
  expires_at: string;
  outcome?: "hit_target" | "hit_stop" | "expired" | null;
}

export interface SentimentPost {
  id: number;
  source: string;
  subreddit?: string;
  title: string;
  body: string;
  author: string;
  score: number;
  sentiment_score: number;
  created_at: string;
  url: string;
}

export interface PriceCandle {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface WatchlistItem {
  ticker: string;
  name: string;
  price: number;
  change_pct: number;
  sentiment_score: number;
  has_active_signal: boolean;
}

// Mock data for development before backend is wired up
export const mockTrendingStocks: TrendingStock[] = [
  {
    ticker: "NVDA",
    name: "NVIDIA Corporation",
    price: 131.28,
    change_pct: 3.42,
    mention_count: 1847,
    mention_velocity: 42.3,
    sentiment_score: 0.72,
    trend_score: 0.89,
    volume_ratio: 2.1,
    sources: ["reddit", "stocktwits"],
  },
  {
    ticker: "TSLA",
    name: "Tesla, Inc.",
    price: 342.15,
    change_pct: -1.87,
    mention_count: 1523,
    mention_velocity: 35.1,
    sentiment_score: -0.15,
    trend_score: 0.82,
    volume_ratio: 1.8,
    sources: ["reddit", "stocktwits", "news"],
  },
  {
    ticker: "AAPL",
    name: "Apple Inc.",
    price: 213.07,
    change_pct: 0.54,
    mention_count: 982,
    mention_velocity: 18.7,
    sentiment_score: 0.45,
    trend_score: 0.71,
    volume_ratio: 1.2,
    sources: ["reddit", "stocktwits"],
  },
  {
    ticker: "GME",
    name: "GameStop Corp.",
    price: 28.43,
    change_pct: 12.65,
    mention_count: 2341,
    mention_velocity: 89.2,
    sentiment_score: 0.61,
    trend_score: 0.95,
    volume_ratio: 4.3,
    sources: ["reddit"],
  },
  {
    ticker: "PLTR",
    name: "Palantir Technologies",
    price: 24.87,
    change_pct: 5.21,
    mention_count: 756,
    mention_velocity: 28.4,
    sentiment_score: 0.58,
    trend_score: 0.74,
    volume_ratio: 1.9,
    sources: ["reddit", "stocktwits"],
  },
  {
    ticker: "AMD",
    name: "Advanced Micro Devices",
    price: 167.32,
    change_pct: 2.18,
    mention_count: 643,
    mention_velocity: 15.2,
    sentiment_score: 0.52,
    trend_score: 0.68,
    volume_ratio: 1.4,
    sources: ["reddit", "news"],
  },
  {
    ticker: "MSFT",
    name: "Microsoft Corporation",
    price: 425.52,
    change_pct: -0.32,
    mention_count: 521,
    mention_velocity: 10.8,
    sentiment_score: 0.38,
    trend_score: 0.61,
    volume_ratio: 0.9,
    sources: ["reddit", "stocktwits", "news"],
  },
  {
    ticker: "AMZN",
    name: "Amazon.com, Inc.",
    price: 186.49,
    change_pct: 1.03,
    mention_count: 478,
    mention_velocity: 12.1,
    sentiment_score: 0.41,
    trend_score: 0.59,
    volume_ratio: 1.1,
    sources: ["reddit", "news"],
  },
  {
    ticker: "SOFI",
    name: "SoFi Technologies",
    price: 9.87,
    change_pct: 7.43,
    mention_count: 412,
    mention_velocity: 31.6,
    sentiment_score: 0.67,
    trend_score: 0.72,
    volume_ratio: 2.4,
    sources: ["reddit", "stocktwits"],
  },
  {
    ticker: "META",
    name: "Meta Platforms, Inc.",
    price: 502.30,
    change_pct: -0.89,
    mention_count: 389,
    mention_velocity: 9.4,
    sentiment_score: 0.22,
    trend_score: 0.55,
    volume_ratio: 1.0,
    sources: ["reddit", "news"],
  },
];

export const mockSignals: Signal[] = [
  {
    id: 1,
    ticker: "NVDA",
    name: "NVIDIA Corporation",
    signal_type: "BUY",
    confidence: 0.82,
    entry_low: 128.5,
    entry_high: 132.0,
    stop_loss: 122.0,
    target: 145.0,
    reasoning: [
      "RSI oversold at 28",
      "Positive sentiment surge +40%",
      "Volume 2.1x average",
    ],
    created_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    expires_at: new Date(Date.now() + 46 * 3600000).toISOString(),
  },
  {
    id: 2,
    ticker: "SOFI",
    name: "SoFi Technologies",
    signal_type: "BUY",
    confidence: 0.71,
    entry_low: 9.5,
    entry_high: 10.0,
    stop_loss: 8.8,
    target: 11.5,
    reasoning: [
      "Strong Reddit sentiment momentum",
      "Price near lower Bollinger Band",
      "Volume 2.4x average",
    ],
    created_at: new Date(Date.now() - 5 * 3600000).toISOString(),
    expires_at: new Date(Date.now() + 43 * 3600000).toISOString(),
  },
  {
    id: 3,
    ticker: "PLTR",
    name: "Palantir Technologies",
    signal_type: "HOLD",
    confidence: 0.59,
    entry_low: 24.0,
    entry_high: 25.2,
    stop_loss: 22.5,
    target: 28.0,
    reasoning: [
      "Moderate bullish sentiment",
      "Volume slightly above average",
    ],
    created_at: new Date(Date.now() - 8 * 3600000).toISOString(),
    expires_at: new Date(Date.now() + 40 * 3600000).toISOString(),
  },
];

export const mockWatchlist: WatchlistItem[] = [
  { ticker: "NVDA", name: "NVIDIA Corporation", price: 131.28, change_pct: 3.42, sentiment_score: 0.72, has_active_signal: true },
  { ticker: "AAPL", name: "Apple Inc.", price: 213.07, change_pct: 0.54, sentiment_score: 0.45, has_active_signal: false },
  { ticker: "TSLA", name: "Tesla, Inc.", price: 342.15, change_pct: -1.87, sentiment_score: -0.15, has_active_signal: false },
  { ticker: "PLTR", name: "Palantir Technologies", price: 24.87, change_pct: 5.21, sentiment_score: 0.58, has_active_signal: true },
  { ticker: "SOFI", name: "SoFi Technologies", price: 9.87, change_pct: 7.43, sentiment_score: 0.67, has_active_signal: true },
];

export const mockSentimentHistory = Array.from({ length: 30 }, (_, i) => {
  const date = new Date();
  date.setDate(date.getDate() - (29 - i));
  return {
    date: date.toISOString().split("T")[0],
    sentiment: Math.sin(i * 0.3) * 0.4 + 0.3 + (Math.random() - 0.5) * 0.2,
    mentions: Math.floor(Math.random() * 200 + 50),
  };
});

export const mockPriceData: PriceCandle[] = Array.from({ length: 30 }, (_, i) => {
  const date = new Date();
  date.setDate(date.getDate() - (29 - i));
  const basePrice = 125 + i * 0.3;
  const open = basePrice + (Math.random() - 0.5) * 4;
  const close = basePrice + (Math.random() - 0.5) * 4;
  return {
    date: date.toISOString().split("T")[0],
    open: parseFloat(open.toFixed(2)),
    high: parseFloat((Math.max(open, close) + Math.random() * 3).toFixed(2)),
    low: parseFloat((Math.min(open, close) - Math.random() * 3).toFixed(2)),
    close: parseFloat(close.toFixed(2)),
    volume: Math.floor(Math.random() * 50000000 + 20000000),
  };
});
