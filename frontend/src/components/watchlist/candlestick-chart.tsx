"use client";

interface Candle {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface CandlestickChartProps {
  candles: Candle[];
  height?: number;
}

export function CandlestickChart({ candles, height = 88 }: CandlestickChartProps) {
  if (candles.length < 2) {
    return <div style={{ height }} className="flex items-center justify-center">
      <span className="text-[11px] text-muted-foreground">Loading chart…</span>
    </div>;
  }

  const data = candles.slice(-60);
  const n = data.length;
  const W = 600;
  const H = height;
  const padY = 6;
  const gapRatio = 0.25;

  const allLows  = data.map(c => c.low);
  const allHighs = data.map(c => c.high);
  const lo = Math.min(...allLows);
  const hi = Math.max(...allHighs);
  const span = hi - lo || 1;

  const toY = (v: number) => H - padY - ((v - lo) / span) * (H - 2 * padY);

  const slotW = W / n;
  const bodyW = Math.max(1, slotW * (1 - gapRatio));
  const wickW = Math.max(1, bodyW * 0.25);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      width="100%"
      height={height}
      style={{ display: "block" }}
    >
      {data.map((c, i) => {
        const bullish = c.close >= c.open;
        const fill   = bullish ? "var(--bullish)" : "var(--bearish)";
        const cx     = slotW * i + slotW / 2;

        const bodyTop = toY(Math.max(c.open, c.close));
        const bodyBot = toY(Math.min(c.open, c.close));
        const bodyH   = Math.max(1, bodyBot - bodyTop);

        const wickTop = toY(c.high);
        const wickBot = toY(c.low);

        return (
          <g key={c.date}>
            {/* Wick */}
            <rect
              x={cx - wickW / 2}
              y={wickTop}
              width={wickW}
              height={Math.max(1, wickBot - wickTop)}
              fill={fill}
              opacity={0.7}
            />
            {/* Body */}
            <rect
              x={cx - bodyW / 2}
              y={bodyTop}
              width={bodyW}
              height={bodyH}
              fill={fill}
              rx={1}
            />
          </g>
        );
      })}
    </svg>
  );
}
