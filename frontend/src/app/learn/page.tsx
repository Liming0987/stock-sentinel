"use client";

import { useState } from "react";
import {
  BookOpen,
  TrendingUp,
  TrendingDown,
  Minus,
  BarChart2,
  ShieldCheck,
  ChevronDown,
  ChevronRight,
  Search,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/layout/page-header";

// ---------------------------------------------------------------------------
// Collapsible Section wrapper
// ---------------------------------------------------------------------------
function Section({
  title,
  icon: Icon,
  defaultOpen = false,
  children,
}: {
  title: string;
  icon: React.ElementType;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-6 py-4 text-left"
      >
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-primary" />
          <span className="text-base font-semibold">{title}</span>
        </div>
        {open ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
      </button>
      {open && <CardContent className="pt-0 pb-5 px-6">{children}</CardContent>}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Section 1 — How to Read a Signal
// ---------------------------------------------------------------------------
function HowToReadSignal() {
  return (
    <div className="space-y-5">
      {/* Example signal card */}
      <div className="rounded-lg border border-l-4 border-l-green-500 bg-green-500/5 p-4 space-y-3">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-base font-bold">AAPL</span>
            <Badge variant="bullish" className="flex items-center gap-1 text-xs px-2 py-0.5">
              <TrendingUp className="h-3 w-3" />
              BUY
            </Badge>
            <span className="text-xs text-muted-foreground font-mono">78% confidence</span>
            <span className="text-xs text-muted-foreground">R/R&nbsp;1:2.4</span>
          </div>
          <span className="text-[10px] text-muted-foreground shrink-0">Example signal</span>
        </div>
        {/* Price grid */}
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="rounded bg-muted/50 px-2 py-1.5">
            <p className="text-muted-foreground mb-0.5">Entry</p>
            <p className="font-mono font-semibold">$182.50</p>
          </div>
          <div className="rounded bg-muted/50 px-2 py-1.5">
            <p className="text-muted-foreground mb-0.5">Stop Loss</p>
            <p className="font-mono font-semibold text-destructive">$179.00</p>
          </div>
          <div className="rounded bg-muted/50 px-2 py-1.5">
            <p className="text-muted-foreground mb-0.5">Target</p>
            <p className="font-mono font-semibold text-bullish">$191.00</p>
          </div>
        </div>
      </div>

      {/* Field explanations */}
      <ul className="space-y-2.5 text-sm">
        {[
          {
            label: "Action (BUY / SELL / HOLD)",
            desc: "Whether to enter a new position, exit an existing one, or wait.",
          },
          {
            label: "Entry Price",
            desc: "The suggested price at which to open the position.",
          },
          {
            label: "Stop Loss",
            desc: "Maximum loss level — exit the trade if price falls to this level.",
          },
          {
            label: "Target",
            desc: "Take-profit level — the algorithm's price objective for the trade.",
          },
          {
            label: "Confidence",
            desc: "0–100 % score representing how strongly all conditions align for this signal.",
          },
          {
            label: "R/R Ratio",
            desc: "(target − entry) ÷ (entry − stop loss). A 1:2 ratio means risking $1 to potentially make $2. We target a minimum of 1:2.",
          },
        ].map(({ label, desc }) => (
          <li key={label} className="flex gap-2">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/60" />
            <span>
              <span className="font-semibold">{label}:</span> {desc}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section 2 — Key Indicators
// ---------------------------------------------------------------------------
const INDICATORS = [
  {
    name: "RSI",
    full: "Relative Strength Index",
    def: "Momentum oscillator scaled 0–100 that measures the speed and change of recent price moves.",
    bullish: "RSI < 30 — oversold territory, expect a bounce.",
    bearish: "RSI > 70 — overbought territory, expect a pullback.",
  },
  {
    name: "MACD",
    full: "Moving Average Convergence Divergence",
    def: "Trend-following momentum indicator derived from two exponential moving averages.",
    bullish: "Histogram crosses above zero — upward momentum building.",
    bearish: "Histogram crosses below zero — downward momentum building.",
  },
  {
    name: "Bollinger Bands",
    full: "Bollinger Bands",
    def: "Volatility envelope drawn 2 standard deviations above and below a 20-period moving average.",
    bullish: "Price breaks above the upper band with elevated volume.",
    bearish: "Price falls below the lower band on high volume.",
  },
  {
    name: "VWAP",
    full: "Volume-Weighted Average Price",
    def: "The average price weighted by volume — the benchmark institutional traders use intraday.",
    bullish: "Price reclaims VWAP from below with momentum.",
    bearish: "Price loses VWAP as a support level.",
  },
  {
    name: "EMA 50 / 200",
    full: "Exponential Moving Averages",
    def: "Trend-direction indicators that weight recent prices more heavily than older ones.",
    bullish: "50 EMA crosses above 200 EMA (golden cross) — long-term uptrend.",
    bearish: "50 EMA crosses below 200 EMA (death cross) — long-term downtrend.",
  },
  {
    name: "Fibonacci Levels",
    full: "Fibonacci Retracement",
    def: "Support and resistance levels at 23.6 %, 38.2 %, 50 %, 61.8 %, and 78.6 % of a prior move.",
    bullish: "Price bounces off the 61.8 % level with increased volume.",
    bearish: "Price breaks below the 61.8 % level on high selling pressure.",
  },
  {
    name: "Volume",
    full: "Trade Volume",
    def: "The number of shares traded in a period — a measure of conviction behind a price move.",
    bullish: "Breakout accompanied by 2× or more of average volume.",
    bearish: "Rally on declining volume — weak, unconvincing move.",
  },
];

function KeyIndicators() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {INDICATORS.map((ind) => (
        <div key={ind.name} className="rounded-lg border bg-muted/20 p-4 space-y-2">
          <div>
            <p className="font-semibold text-sm">{ind.name}</p>
            <p className="text-[11px] text-muted-foreground">{ind.full}</p>
          </div>
          <p className="text-xs text-muted-foreground">{ind.def}</p>
          <div className="space-y-1 text-xs">
            <div className="flex gap-1.5 items-start">
              <TrendingUp className="h-3.5 w-3.5 shrink-0 mt-0.5 text-green-500" />
              <span className="text-green-700 dark:text-green-400">{ind.bullish}</span>
            </div>
            <div className="flex gap-1.5 items-start">
              <TrendingDown className="h-3.5 w-3.5 shrink-0 mt-0.5 text-red-500" />
              <span className="text-red-700 dark:text-red-400">{ind.bearish}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section 3 — Our 9 Strategies
// ---------------------------------------------------------------------------
const STRATEGIES = [
  {
    name: "Momentum",
    desc: "Follows stocks trending strongly above their 50 and 200-day EMAs with bullish MACD. Confirms with volume spikes to ensure institutional participation.",
    best: "Strong trending bull markets.",
  },
  {
    name: "RSI Mean Reversion",
    desc: "Buys extreme oversold conditions (RSI < 30) near the lower Bollinger Band, expecting a bounce back to fair value. Targets a return to the middle band.",
    best: "Volatile markets with defined support levels.",
  },
  {
    name: "Sentiment-Driven",
    desc: "Combines high social media mention velocity with positive FinBERT sentiment and price confirmation. Captures retail-driven momentum surges early.",
    best: "Momentum stocks with active retail interest.",
  },
  {
    name: "BB Breakout",
    desc: "Enters when price closes above the upper Bollinger Band with elevated volume, signaling a volatility expansion and the start of a new trend leg.",
    best: "Low-volatility consolidations that are breaking out.",
  },
  {
    name: "VWAP Cross",
    desc: "Triggers when price crosses above VWAP with positive momentum, a signal institutional traders watch closely. Exits when price falls back below VWAP.",
    best: "Intraday momentum on high-volume stocks.",
  },
  {
    name: "MACD Histogram",
    desc: "Fires when the histogram turns positive from negative territory, signaling a momentum shift from bearish to bullish. Uses histogram magnitude for confidence.",
    best: "Stocks transitioning from downtrend to uptrend.",
  },
  {
    name: "Opening Range Breakout",
    desc: "Defines the first 30-minute high and low as the day's range, then trades breakouts above that high. Stop is placed at the opening range low.",
    best: "High-momentum morning sessions with news catalysts.",
  },
  {
    name: "Fibonacci Retracement",
    desc: "Looks for price bouncing off the 61.8 % Fibonacci retracement level with volume confirmation after an established trend move.",
    best: "Trending stocks in healthy pullback phases.",
  },
  {
    name: "Elliott Wave + Fib",
    desc: "Uses wave count structure combined with Fibonacci targets for high-confluence entries. Requires a clear 5-wave impulse pattern before signaling.",
    best: "Mature trends with clear wave structure.",
  },
];

function OurStrategies() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {STRATEGIES.map((s, i) => (
        <div key={s.name} className="rounded-lg border bg-muted/20 p-4 space-y-2">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary shrink-0">
              {i + 1}
            </span>
            <p className="font-semibold text-sm">{s.name}</p>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">{s.desc}</p>
          <p className="text-[11px] text-primary/80">
            <span className="font-semibold">Best in:</span> {s.best}
          </p>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section 4 — Risk Management
// ---------------------------------------------------------------------------
const RISK_RULES = [
  {
    title: "Fixed Position Sizing",
    icon: BarChart2,
    desc: "We risk a fixed dollar amount per trade, not a variable percentage. This prevents one large loss from wiping out prior gains.",
  },
  {
    title: "Always Set a Stop Loss",
    icon: ShieldCheck,
    desc: "Every trade has a predefined exit price if the thesis is wrong. Never hold a losing trade hoping it recovers.",
  },
  {
    title: "Target 1:2 Risk / Reward",
    icon: TrendingUp,
    desc: "For every $1 risked, target a minimum $2 gain. With this ratio you can be right only 40 % of the time and still be profitable.",
  },
  {
    title: "Limit Open Positions",
    icon: Minus,
    desc: "Each strategy caps the number of concurrent open positions. Diversification prevents correlated losses from multiple trades moving against you simultaneously.",
  },
];

function RiskManagement() {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {RISK_RULES.map(({ title, icon: Icon, desc }) => (
        <div key={title} className="rounded-lg border bg-muted/20 p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4 text-primary shrink-0" />
            <p className="font-semibold text-sm">{title}</p>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section 5 — Glossary
// ---------------------------------------------------------------------------
const GLOSSARY: { term: string; def: string }[] = [
  { term: "Alpha", def: "Returns generated above a benchmark index, a measure of a strategy's edge." },
  { term: "ATH (All-Time High)", def: "The highest price a security has ever traded at." },
  { term: "ATL (All-Time Low)", def: "The lowest price a security has ever traded at." },
  { term: "Bear Market", def: "A market decline of 20 % or more from recent highs, characterized by widespread pessimism." },
  { term: "Bollinger Bands", def: "Volatility envelope: upper and lower bands drawn 2 standard deviations around a 20-period moving average." },
  { term: "Breakout", def: "When price moves decisively above a resistance level or below a support level on elevated volume." },
  { term: "Bull Market", def: "A sustained market rise of 20 % or more, characterized by investor optimism." },
  { term: "Buying Power", def: "The total capital available in a brokerage account to purchase securities." },
  { term: "Consolidation", def: "A period of sideways price movement as buyers and sellers reach a temporary equilibrium." },
  { term: "Correction", def: "A decline of 10–20 % from recent highs, often seen as a healthy reset within a longer uptrend." },
  { term: "Day Trading", def: "Opening and closing positions within the same trading day to avoid overnight risk." },
  { term: "Dead Cat Bounce", def: "A brief, temporary recovery in a declining asset before the downtrend resumes." },
  { term: "Drawdown", def: "The peak-to-trough decline in portfolio value over a specific period." },
  { term: "EMA", def: "Exponential Moving Average — a moving average that weights recent prices more heavily than older ones." },
  { term: "Entry Price", def: "The price at which a position is opened." },
  { term: "Exit", def: "Closing an open position, either at a profit (target) or a loss (stop loss)." },
  { term: "Float", def: "The number of shares available for public trading, excluding insider and restricted shares." },
  { term: "FOMO", def: "Fear Of Missing Out — emotionally chasing a position after a large move has already occurred." },
  { term: "Gap Up / Down", def: "When a stock opens significantly higher or lower than the prior day's close." },
  { term: "Going Long", def: "Buying a security with the expectation that it will rise in value." },
  { term: "Going Short", def: "Selling borrowed shares to profit from a decline in price." },
  { term: "High of Day", def: "The highest intraday price reached by a security during the current trading session." },
  { term: "Liquidity", def: "How easily a security can be bought or sold without significantly moving its price." },
  { term: "MACD", def: "Moving Average Convergence Divergence — a trend-following momentum indicator." },
  { term: "Margin", def: "Borrowed capital from a broker used to increase buying power, amplifying both gains and losses." },
  { term: "Market Cap", def: "Total market value of a company's outstanding shares (price × shares outstanding)." },
  { term: "Momentum", def: "The tendency for a security moving strongly in one direction to continue in that direction." },
  { term: "Open Interest", def: "The total number of outstanding options or futures contracts not yet settled." },
  { term: "Overbought", def: "A condition where a security has risen too far too fast, often signaled by RSI > 70." },
  { term: "Oversold", def: "A condition where a security has fallen too far too fast, often signaled by RSI < 30." },
  { term: "Paper Trading", def: "Simulated trading using virtual money to practice strategies without real financial risk." },
  { term: "Pattern", def: "A recognizable formation in a price chart (e.g. head and shoulders, cup and handle) that suggests a future move." },
  { term: "Position", def: "An open trade — the amount of a security currently held (long or short)." },
  { term: "Rally", def: "A sharp, sustained rise in price following a period of decline or consolidation." },
  { term: "Resistance", def: "A price level where selling pressure has historically halted or reversed an upward move." },
  { term: "RSI", def: "Relative Strength Index — a momentum oscillator measuring the speed and change of price movements, scaled 0–100." },
  { term: "Scalping", def: "A very short-term trading style targeting small, frequent gains over seconds to minutes." },
  { term: "Sector Rotation", def: "The movement of institutional money between market sectors as economic conditions change." },
  { term: "Sentiment", def: "The overall attitude of investors toward a security, measured here via Reddit and StockTwits using FinBERT and VADER." },
  { term: "Short Squeeze", def: "A rapid price increase that forces short sellers to buy back shares, amplifying the upward move." },
  { term: "Signal", def: "A buy, sell, or hold recommendation generated by one of the platform's trading strategies." },
  { term: "Slippage", def: "The difference between the expected execution price and the actual fill price." },
  { term: "Stop Loss", def: "A predefined price at which a losing trade is automatically exited to limit further losses." },
  { term: "Support", def: "A price level where buying interest has historically halted or reversed a downward move." },
  { term: "Swing Trading", def: "Holding positions for days to weeks to capture a single directional price move." },
  { term: "Target", def: "The take-profit price at which a winning trade is exited according to the strategy's objective." },
  { term: "Ticker Symbol", def: "The unique alphabetic abbreviation used to identify a publicly traded company (e.g. AAPL for Apple)." },
  { term: "Trend", def: "The general directional movement of a security's price over time — uptrend, downtrend, or sideways." },
  { term: "Unrealized P&L", def: "The paper profit or loss on an open position that has not yet been closed." },
  { term: "VWAP", def: "Volume-Weighted Average Price — the average price weighted by volume, used as an institutional benchmark." },
  { term: "Volatility", def: "The degree of variation in a security's price over time; higher volatility means larger price swings." },
  { term: "Volume", def: "The total number of shares traded during a given period — a measure of market conviction." },
  { term: "Watchlist", def: "A curated list of securities being monitored for potential trading opportunities." },
  { term: "Whipsaw", def: "Rapid, sharp price reversals that trigger stop losses before the intended move occurs." },
];

function Glossary() {
  const [query, setQuery] = useState("");
  const filtered = GLOSSARY.filter(
    (g) =>
      g.term.toLowerCase().includes(query.toLowerCase()) ||
      g.def.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        <input
          type="text"
          placeholder="Search terms…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full rounded-md border bg-background pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
      </div>

      {/* Table */}
      <div className="rounded-md border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="text-left px-4 py-2.5 font-semibold text-xs uppercase tracking-wide w-40 shrink-0">
                Term
              </th>
              <th className="text-left px-4 py-2.5 font-semibold text-xs uppercase tracking-wide">
                Definition
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={2} className="px-4 py-8 text-center text-muted-foreground text-sm">
                  No terms match &ldquo;{query}&rdquo;
                </td>
              </tr>
            ) : (
              filtered.map((g, i) => (
                <tr
                  key={g.term}
                  className={i % 2 === 0 ? "bg-background" : "bg-muted/20"}
                >
                  <td className="px-4 py-2.5 font-medium text-xs align-top whitespace-nowrap w-40 shrink-0">
                    {g.term}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground leading-relaxed">
                    {g.def}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground text-right">
        {filtered.length} of {GLOSSARY.length} terms
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function LearnPage() {
  return (
    <div className="mx-auto max-w-[1180px] space-y-[18px]">
      <PageHeader
        kicker="Grow"
        title="Learn"
        description="Short, plain-English lessons that explain the metrics you see across Sentinel — one concept at a time."
      />

      {/* Section 1 */}
      <Section title="How to Read a Signal" icon={BookOpen} defaultOpen>
        <HowToReadSignal />
      </Section>

      {/* Section 2 */}
      <Section title="Key Indicators" icon={BarChart2} defaultOpen>
        <KeyIndicators />
      </Section>

      {/* Section 3 */}
      <Section title="Our 9 Strategies" icon={TrendingUp} defaultOpen>
        <OurStrategies />
      </Section>

      {/* Section 4 */}
      <Section title="Risk Management" icon={ShieldCheck} defaultOpen>
        <RiskManagement />
      </Section>

      {/* Section 5 */}
      <Section title="Trading Glossary" icon={BookOpen} defaultOpen>
        <Glossary />
      </Section>
    </div>
  );
}
