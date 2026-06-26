const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  trending: {
    list: (timeframe = "24h", limit = 20) =>
      fetchApi(`/api/trending?timeframe=${timeframe}&limit=${limit}`),
    detail: (ticker: string) => fetchApi(`/api/trending/${ticker}`),
  },
  sentiment: {
    market: (period = "7d") => fetchApi(`/api/sentiment/market?period=${period}`),
    get: (ticker: string, period = "7d") =>
      fetchApi(`/api/sentiment/${ticker}?period=${period}`),
    posts: (ticker: string, limit = 20) =>
      fetchApi(`/api/sentiment/${ticker}/posts?limit=${limit}`),
  },
  prices: {
    get: (ticker: string, period = "1M", interval = "1d") =>
      fetchApi(`/api/prices/${ticker}?period=${period}&interval=${interval}`),
    live: (ticker: string) =>
      fetchApi(`/api/prices/${ticker}/live`),
  },
  signals: {
    active: () => fetchApi("/api/signals"),
    history: (limit = 50) => fetchApi(`/api/signals/history?limit=${limit}`),
  },
  watchlist: {
    list: () => fetchApi("/api/watchlist"),
    add: (ticker: string) =>
      fetch(`${API_BASE}/api/watchlist/${ticker}`, { method: "POST" })
        .then(r => { if (!r.ok) throw new Error(`Failed to add ${ticker}`); return r.json(); }),
    remove: (ticker: string) =>
      fetch(`${API_BASE}/api/watchlist/${ticker}`, { method: "DELETE" })
        .then(r => { if (!r.ok) throw new Error(`Failed to remove ${ticker}`); return r.json(); }),
    volumeAnalysis: (ticker: string, period = "90d") =>
      fetchApi(`/api/watchlist/${ticker}/volume-analysis?period=${period}`),
    news: (ticker: string, limit = 20) =>
      fetchApi(`/api/watchlist/${ticker}/news?limit=${limit}`),
    dcf: (ticker: string) =>
      fetchApi(`/api/watchlist/${ticker}/dcf`),
  },
  notifications: {
    list: (limit = 30) => fetchApi(`/api/notifications?limit=${limit}`),
  },
  backtest: {
    strategies: () => fetchApi("/api/backtest/strategies"),
    run: (body: object) =>
      fetch(`${API_BASE}/api/backtest/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then((r) => r.json()),
  },
  fundamentals: {
    get: (ticker: string) => fetchApi(`/api/fundamentals/${ticker}`),
  },
  strategies: {
    list: () => fetchApi("/api/strategies"),
    trades: (name: string, status = "all") =>
      fetchApi(`/api/strategies/${name}/trades?status=${status}&limit=100`),
    equityCurve: () => fetchApi("/api/strategies/equity-curve"),
    alpacaAccount: () => fetchApi("/api/strategies/alpaca/account"),
    livePositions: () => fetchApi("/api/strategies/live-positions"),
    setEnabled: (name: string, enabled: boolean) =>
      fetchApi(`/api/strategies/${name}/enabled`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      }),
    syncAlpaca: () => fetchApi("/api/strategies/sync-alpaca", { method: "POST" }),
    reconcile: () => fetchApi("/api/strategies/reconcile", { method: "POST" }),
    signals: (name: string, action = "all", limit = 50) =>
      fetchApi(`/api/strategies/${name}/signals?action=${action}&limit=${limit}`),
  },
  strategySignalsLatest: (since: string, limit = 20) =>
    fetchApi(`/api/strategy-signals/latest?since=${encodeURIComponent(since)}&limit=${limit}`),
  strategySignals: (filters: { strategy?: string; action?: string; ticker?: string; date_from?: string; date_to?: string; limit?: number; offset?: number } = {}) => {
    const params = new URLSearchParams();
    if (filters.strategy) params.set("strategy", filters.strategy);
    if (filters.action) params.set("action", filters.action);
    if (filters.ticker) params.set("ticker", filters.ticker);
    if (filters.date_from) params.set("date_from", filters.date_from);
    if (filters.date_to) params.set("date_to", filters.date_to);
    if (filters.limit) params.set("limit", String(filters.limit));
    if (filters.offset) params.set("offset", String(filters.offset));
    const qs = params.toString();
    return fetchApi(`/api/strategy-signals${qs ? `?${qs}` : ""}`);
  },
  reports: {
    list: (limit = 30) => fetchApi(`/api/reports?limit=${limit}`),
    latest: () => fetchApi("/api/reports/latest"),
  },
};
