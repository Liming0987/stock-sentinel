"use client";

import { useState } from "react";
import Link from "next/link";
import { Star, ArrowUpRight, ArrowDownRight, Trash2, Bell, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SentimentGauge } from "@/components/dashboard/sentiment-gauge";
import { formatPrice, formatPercent } from "@/lib/utils";
import { useWatchlist } from "@/lib/hooks";
import { api } from "@/lib/api";

export default function WatchlistPage() {
  const { data, refetch } = useWatchlist();
  const stocks = data.stocks;

  const [adding, setAdding] = useState(false);
  const [tickerInput, setTickerInput] = useState("");
  const [addError, setAddError] = useState<string | null>(null);

  const handleAdd = async () => {
    const ticker = tickerInput.trim().toUpperCase();
    if (!ticker) return;
    setAddError(null);
    try {
      const res = await api.watchlist.add(ticker);
      if (!res.ok) {
        const body = await res.json();
        setAddError(body.detail || "Failed to add ticker");
        return;
      }
      setTickerInput("");
      setAdding(false);
      refetch();
    } catch {
      setAddError("Network error — is the backend running?");
    }
  };

  const handleRemove = async (ticker: string) => {
    await api.watchlist.remove(ticker);
    refetch();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Watchlist</h1>
          <p className="text-sm text-muted-foreground">
            Track your favorite stocks with sentiment alerts
          </p>
        </div>
        <Button size="sm" onClick={() => { setAdding(true); setAddError(null); }}>
          <Star className="mr-2 h-4 w-4" />
          Add Ticker
        </Button>
      </div>

      {adding && (
        <Card>
          <CardContent className="flex items-center gap-3 pt-4">
            <input
              autoFocus
              className="flex-1 rounded-md border bg-background px-3 py-2 text-sm uppercase placeholder:normal-case placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="e.g. NVDA"
              value={tickerInput}
              onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
              onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); if (e.key === "Escape") setAdding(false); }}
            />
            <Button size="sm" onClick={handleAdd}>
              <Plus className="mr-1 h-4 w-4" /> Add
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setAdding(false)}>
              Cancel
            </Button>
            {addError && <p className="text-xs text-destructive">{addError}</p>}
          </CardContent>
        </Card>
      )}

      {stocks.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Star className="mb-4 h-12 w-12 text-muted-foreground/50" />
            <p className="text-lg font-medium">Your watchlist is empty</p>
            <p className="text-sm text-muted-foreground">Click &ldquo;Add Ticker&rdquo; to start tracking stocks</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {stocks.map((stock) => (
            <Card key={stock.ticker} className="relative overflow-hidden">
              {stock.has_active_signal && (
                <div className="absolute right-3 top-3">
                  <Badge variant="bullish" className="text-[10px]">
                    SIGNAL
                  </Badge>
                </div>
              )}
              <CardHeader className="pb-2">
                <Link href={`/stock/${stock.ticker}`} className="group">
                  <CardTitle className="flex items-center gap-2 group-hover:text-primary transition-colors">
                    {stock.ticker}
                    <span className="text-sm font-normal text-muted-foreground">{stock.name}</span>
                  </CardTitle>
                </Link>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-bold font-mono">{formatPrice(stock.price)}</p>
                    <p className={`flex items-center gap-0.5 text-sm font-mono ${stock.change_pct >= 0 ? "text-bullish" : "text-bearish"}`}>
                      {stock.change_pct >= 0 ? (
                        <ArrowUpRight className="h-3 w-3" />
                      ) : (
                        <ArrowDownRight className="h-3 w-3" />
                      )}
                      {formatPercent(stock.change_pct)}
                    </p>
                  </div>
                  <SentimentGauge score={stock.sentiment_score} size="sm" />
                </div>

                <div className="mt-4 flex gap-2">
                  <Button variant="ghost" size="sm" className="flex-1 text-xs">
                    <Bell className="mr-1 h-3 w-3" />
                    Alerts
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs text-bearish hover:text-bearish"
                    onClick={() => handleRemove(stock.ticker)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
