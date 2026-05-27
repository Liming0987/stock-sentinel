const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
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
  },
  signals: {
    active: () => fetchApi("/api/signals"),
    history: (limit = 50) => fetchApi(`/api/signals/history?limit=${limit}`),
  },
  watchlist: {
    list: () => fetchApi("/api/watchlist"),
    add: (ticker: string) =>
      fetch(`${API_BASE}/api/watchlist/${ticker}`, { method: "POST" }),
    remove: (ticker: string) =>
      fetch(`${API_BASE}/api/watchlist/${ticker}`, { method: "DELETE" }),
  },
};
