"use client";

import Link from "next/link";
import { useTrending, useSignals, useMarketSentiment, useWatchlist } from "@/lib/hooks";

const DAILY_LESSONS = [
  {
    title: "What a volume spike actually tells you",
    body: "When a stock trades 2–3× its average volume, conviction is entering the move. Pair that with rising sentiment and it's a higher-quality signal — but volume without a story is often just noise.",
  },
  {
    title: "Reading RSI without overthinking it",
    body: "RSI below 30 means a stock may be oversold, above 70 overbought. It's a clue, not a command — strong trends can stay 'overbought' for weeks. Use it to time entries, never as a standalone reason.",
  },
  {
    title: "Why crowd mood leads price (sometimes)",
    body: "Social sentiment can front-run price when retail flow drives a name. But sentiment also peaks at tops. Watch for divergence: price up while mentions fade is a quiet warning.",
  },
  {
    title: "Position sizing beats stock picking",
    body: "Where you set your stop and how much you risk per trade matters more than being right. Risk a fixed small % of your account per idea so no single trade can hurt you.",
  },
  {
    title: "Bollinger Bands as a rubber band",
    body: "Price tends to revert when it stretches to the outer bands. A touch of the lower band in an uptrend can be a buy zone — but in a downtrend it's just gravity.",
  },
  {
    title: "The cost of chasing green candles",
    body: "Buying after a stock has already run is the most common retail mistake. Wait for a pullback into your entry zone; the best trades feel slightly uncomfortable to enter.",
  },
  {
    title: "What the Wyckoff accumulation pattern looks like",
    body: "Smart money buys quietly — volume dries up on pullbacks, then surges on breakouts. A selling climax followed by low-volume retests is the setup; the breakout with conviction is the entry.",
  },
];

function MoodSparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const min = Math.min(...values), max = Math.max(...values);
  const span = (max - min) || 1;
  const w = 320, h = 52, pad = 4;
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - pad - ((v - min) / span) * (h - 2 * pad);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="w-full" style={{ height: 52 }}>
      <polyline points={pts} fill="none" stroke="var(--sentinel-up)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SentBar({ value }: { value: number }) {
  const pct = Math.round(((value + 1) / 2) * 100);
  const color = value >= 0.25 ? "var(--sentinel-up)" : value < -0.1 ? "var(--sentinel-down)" : "var(--muted-foreground)";
  const label = value >= 0.25 ? "Bullish" : value < -0.1 ? "Bearish" : "Neutral";
  return (
    <div className="flex items-center justify-end gap-2">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span className="relative h-[5px] w-11 rounded-full overflow-hidden" style={{ background: "var(--border)" }}>
        <span className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${pct}%`, background: color }} />
      </span>
    </div>
  );
}

export default function DashboardPage() {
  const { data: trendingData, loading } = useTrending();
  const { data: signalsData } = useSignals();
  const { data: marketSentiment } = useMarketSentiment();
  const { data: watchlistData } = useWatchlist();

  const signals = signalsData.signals.slice(0, 3);
  const sentHistory = marketSentiment.history;
  const moodValues = sentHistory.map((h) => h.sentiment);
  const currentMood = moodValues.length ? moodValues[moodValues.length - 1] : 0;
  const prevMood = moodValues.length > 1 ? moodValues[moodValues.length - 2] : currentMood;
  const moodDelta = currentMood - prevMood;
  const moodLabel = currentMood >= 0.25 ? "Bullish" : currentMood < -0.1 ? "Bearish" : "Neutral";

  const today = new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
  const lessonIdx = new Date().getDay() % DAILY_LESSONS.length;
  const lesson = DAILY_LESSONS[lessonIdx];

  const totalMentions = trendingData.stocks.reduce((s, t) => s + t.mention_count, 0);
  const fmtMentions = totalMentions >= 1000 ? `${(totalMentions / 1000).toFixed(1)}k` : String(totalMentions);
  const watchlistAvgChg = watchlistData.stocks.length
    ? watchlistData.stocks.reduce((s, w) => s + (w.change_pct ?? 0), 0) / watchlistData.stocks.length
    : 0;

  const glance = [
    { label: "Trending now", value: String(trendingData.stocks.length), color: "var(--foreground)" },
    { label: "Active signals", value: String(signalsData.signals.length), color: "var(--primary)" },
    { label: "Total mentions (24h)", value: fmtMentions, color: "var(--foreground)" },
    { label: "Watchlist avg", value: `${watchlistAvgChg >= 0 ? "+" : ""}${watchlistAvgChg.toFixed(2)}%`, color: watchlistAvgChg >= 0 ? "var(--sentinel-up)" : "var(--sentinel-down)" },
  ];

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">Loading market data…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1180px] space-y-[18px]">
      {/* Page header */}
      <div className="mb-[30px]">
        <p className="mb-1.5 text-[12.5px] font-semibold uppercase tracking-[0.1em] text-primary">{today}</p>
        <h1 className="font-serif text-[38px] font-medium leading-[1.05] tracking-[-0.02em]">Good morning, Alex.</h1>
        <p className="mt-2.5 max-w-[520px] text-[15px] leading-relaxed text-muted-foreground">
          Here&apos;s what the crowd is talking about and where the signals are pointing today.
        </p>
      </div>

      {/* Row 1: Market mood + Today at a glance */}
      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-[1.5fr_1fr]">
        {/* Market mood */}
        <div className="rounded-[16px] border bg-card p-[26px] flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground/70">
              Market mood
            </span>
            <span
              title="A blend of sentiment across Reddit, StockTwits & news. Above 0 = net bullish chatter."
              className="inline-flex h-[15px] w-[15px] cursor-help items-center justify-center rounded-full border text-[10px] text-muted-foreground"
            >?</span>
          </div>
          <div className="my-[18px] flex items-end gap-[18px]">
            <span
              className="font-serif text-[60px] font-medium leading-[0.9] tracking-[-0.02em]"
              style={{ color: currentMood >= 0 ? "var(--sentinel-up)" : "var(--sentinel-down)" }}
            >
              {currentMood >= 0 ? "+" : ""}{currentMood.toFixed(2)}
            </span>
            <div className="pb-2">
              <p className="text-[17px] font-semibold" style={{ color: currentMood >= 0 ? "var(--sentinel-up)" : "var(--sentinel-down)" }}>
                {moodLabel}
              </p>
              <p className="mt-0.5 text-[12.5px] text-muted-foreground">
                {moodDelta >= 0 ? "+" : ""}{moodDelta.toFixed(2)} vs. yesterday
              </p>
            </div>
          </div>
          <MoodSparkline values={moodValues.slice(-14)} />
        </div>

        {/* Today at a glance */}
        <div className="rounded-[16px] border bg-card p-[22px] flex flex-col">
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground/70">Today at a glance</p>
          <div className="flex-1 flex flex-col justify-center gap-0.5">
            {glance.map((g) => (
              <div key={g.label} className="flex items-center justify-between border-b border-border/50 py-[11px]">
                <span className="text-[13.5px] text-muted-foreground">{g.label}</span>
                <span className="font-mono text-[15px] font-semibold" style={{ color: g.color }}>{g.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Row 2: Watchlist snapshot + Daily lesson */}
      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-[1.5fr_1fr]">
        {/* Watchlist */}
        <div className="rounded-[16px] border bg-card overflow-hidden">
          <div className="flex items-center justify-between px-6 pb-3.5 pt-5">
            <h2 className="font-serif text-[21px] font-semibold leading-none">Your watchlist</h2>
            <Link href="/watchlist" className="text-[13px] font-medium text-primary hover:underline">
              View all →
            </Link>
          </div>
          {watchlistData.stocks.length === 0 ? (
            <p className="px-6 pb-6 text-[13px] text-muted-foreground">No stocks in watchlist yet.</p>
          ) : (
            watchlistData.stocks.slice(0, 5).map((w) => (
              <div key={w.ticker} className="grid items-center gap-3 border-t px-6 py-[13px]"
                style={{ gridTemplateColumns: "1.4fr 1fr 1fr 1.1fr" }}>
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="font-bold text-[14px]">{w.ticker}</span>
                  {w.has_active_signal && (
                    <span className="rounded-[5px] bg-[var(--sentinel-accent-soft)] px-[7px] py-0.5 text-[9.5px] font-bold uppercase tracking-wide text-primary">
                      SIGNAL
                    </span>
                  )}
                </div>
                <span className="font-mono text-[13.5px] text-right">
                  {w.price ? `$${w.price.toFixed(2)}` : "—"}
                </span>
                <span
                  className="font-mono text-[13.5px] font-semibold text-right"
                  style={{ color: (w.change_pct ?? 0) >= 0 ? "var(--sentinel-up)" : "var(--sentinel-down)" }}
                >
                  {w.change_pct != null ? `${w.change_pct >= 0 ? "+" : ""}${w.change_pct.toFixed(2)}%` : "—"}
                </span>
                <SentBar value={w.sentiment_score ?? 0} />
              </div>
            ))
          )}
        </div>

        {/* Daily lesson */}
        <div
          className="rounded-[16px] border p-6 flex flex-col"
          style={{ background: "linear-gradient(160deg, var(--sentinel-accent-soft), transparent)" }}
        >
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-primary">Today&apos;s lesson</p>
          <h3 className="font-serif text-[22px] font-semibold leading-[1.2] mb-2.5">{lesson.title}</h3>
          <p className="flex-1 text-[13.5px] leading-relaxed text-muted-foreground">{lesson.body}</p>
          <Link
            href="/learn"
            className="mt-4 self-start rounded-[9px] px-4 py-2 text-[13px] font-semibold transition-opacity hover:opacity-90"
            style={{ background: "var(--primary)", color: "var(--sentinel-accent-ink)" }}
          >
            Read 2-min lesson
          </Link>
        </div>
      </div>

      {/* Row 3: Active signals */}
      <div className="rounded-[16px] border bg-card p-5 pb-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-serif text-[21px] font-semibold leading-none">Active signals</h2>
          <Link href="/signals" className="text-[13px] font-medium text-primary hover:underline">
            View all →
          </Link>
        </div>
        {signals.length === 0 ? (
          <p className="text-[13px] text-muted-foreground">No active signals right now.</p>
        ) : (
          <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 xl:grid-cols-3">
            {signals.map((s) => (
              <div key={s.id} className="rounded-[13px] border p-[16px] bg-card" style={{ background: "var(--muted)" }}>
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span
                      className="rounded-[6px] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
                      style={{
                        background: s.signal_type === "BUY" ? "var(--sentinel-accent-soft)" : "var(--border)",
                        color: s.signal_type === "BUY" ? "var(--primary)" : "var(--muted-foreground)",
                      }}
                    >
                      {s.signal_type}
                    </span>
                    <span className="font-bold text-[15px]">{s.ticker}</span>
                  </div>
                  <span className="font-mono text-[12px] text-muted-foreground">
                    {Math.round(s.confidence * 100)}%
                  </span>
                </div>
                <div className="flex justify-between gap-1.5 font-mono text-[12px]">
                  <div>
                    <p className="mb-0.5 text-[10px] font-sans text-muted-foreground/70">Entry</p>
                    {s.entry_low ? `$${s.entry_low.toFixed(0)}–${s.entry_high.toFixed(0)}` : "—"}
                  </div>
                  <div className="text-center">
                    <p className="mb-0.5 text-[10px] font-sans text-muted-foreground/70">Stop</p>
                    <span style={{ color: "var(--sentinel-down)" }}>
                      {s.stop_loss ? `$${s.stop_loss.toFixed(2)}` : "—"}
                    </span>
                  </div>
                  <div className="text-right">
                    <p className="mb-0.5 text-[10px] font-sans text-muted-foreground/70">Target</p>
                    <span style={{ color: "var(--sentinel-up)" }}>
                      {s.target ? `$${s.target.toFixed(2)}` : "—"}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
