"use client";

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceDot,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { VolumeHistoryPoint } from "@/lib/hooks";

const PERIODS = [
  { label: "1M", value: "30d" },
  { label: "3M", value: "90d" },
  { label: "6M", value: "6mo" },
  { label: "1Y", value: "1y" },
] as const;

interface TooltipPayload {
  dataKey: string;
  value: number;
  payload: VolumeHistoryPoint;
}

interface CustomTooltipProps {
  active?: boolean;
  label?: string;
  payload?: TooltipPayload[];
}

function CustomTooltip({ active, label, payload }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div
      style={{
        backgroundColor: "hsl(var(--card))",
        border: "1px solid hsl(var(--border))",
        borderRadius: 8,
        fontSize: 12,
        padding: "8px 12px",
      }}
    >
      <p style={{ color: "hsl(var(--foreground))", fontWeight: 600 }}>{label}</p>
      <p style={{ color: "#60a5fa" }}>Close: ${p.close?.toFixed(2)}</p>
      <p style={{ color: "hsl(var(--muted-foreground))" }}>
        Volume: {p.volume != null ? (p.volume / 1_000_000).toFixed(2) + "M" : "—"}
      </p>
      <p style={{ color: "hsl(var(--muted-foreground))" }}>
        Vol Ratio: {p.vol_ratio?.toFixed(2) ?? "—"}x
      </p>
      <p style={{ color: "hsl(var(--muted-foreground))" }}>{p.interpretation}</p>
    </div>
  );
}

interface PriceVolumeChartProps {
  data: VolumeHistoryPoint[];
  selectedPeriod: string;
  onPeriodChange: (period: string) => void;
}

export function PriceVolumeChart({ data, selectedPeriod, onPeriodChange }: PriceVolumeChartProps) {
  const spikes = data.filter((d) => d.is_spike);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base">Price &amp; Volume</CardTitle>
        <div className="flex gap-1">
          {PERIODS.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => onPeriodChange(value)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                selectedPeriod === value
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickFormatter={(v: string) => v.slice(5)}
                interval="preserveStartEnd"
              />
              <YAxis
                yAxisId="price"
                orientation="left"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
                domain={["auto", "auto"]}
              />
              <YAxis
                yAxisId="volume"
                orientation="right"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickFormatter={(v: number) =>
                  v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` : `${(v / 1_000).toFixed(0)}K`
                }
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar yAxisId="volume" dataKey="volume" radius={[2, 2, 0, 0]}>
                {data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      entry.close != null && entry.open != null && entry.close >= entry.open
                        ? "#22c55e"
                        : "#ef4444"
                    }
                  />
                ))}
              </Bar>
              <Line
                yAxisId="volume"
                dataKey="avg_vol_30"
                stroke="#94a3b8"
                strokeDasharray="4 2"
                strokeWidth={1.5}
                dot={false}
              />
              <Line
                yAxisId="price"
                dataKey="close"
                stroke="#60a5fa"
                strokeWidth={2}
                dot={false}
              />
              {spikes.map((spike, i) => (
                <ReferenceDot
                  key={`spike-${i}`}
                  yAxisId="volume"
                  x={spike.date}
                  y={spike.volume}
                  r={4}
                  fill="#f59e0b"
                  stroke="none"
                />
              ))}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
