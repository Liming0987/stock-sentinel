"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { VolumeHistoryPoint } from "@/lib/hooks";

interface OBVChartProps {
  data: VolumeHistoryPoint[];
}

export function OBVChart({ data }: OBVChartProps) {
  const window = data.slice(-30);

  let hasDivergence = false;
  let divStart: string | undefined;
  let divEnd: string | undefined;

  if (window.length >= 2) {
    const firstObv = window[0].obv;
    const lastObv = window[window.length - 1].obv;
    const firstClose = window[0].close;
    const lastClose = window[window.length - 1].close;

    const obvUp = lastObv != null && firstObv != null && lastObv > firstObv;
    const priceDown = lastClose != null && firstClose != null && lastClose < firstClose;

    if (obvUp && priceDown) {
      hasDivergence = true;
      divStart = window[0].date;
      divEnd = window[window.length - 1].date;
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">On-Balance Volume (OBV)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickFormatter={(v: string) => v.slice(5)}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickFormatter={(v: number) =>
                  v >= 1_000_000
                    ? `${(v / 1_000_000).toFixed(1)}M`
                    : v >= 1_000
                    ? `${(v / 1_000).toFixed(0)}K`
                    : v.toFixed(0)
                }
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: "hsl(var(--foreground))" }}
              />
              {hasDivergence && divStart && divEnd && (
                <ReferenceArea
                  x1={divStart}
                  x2={divEnd}
                  fill="#f59e0b20"
                  stroke="#f59e0b"
                  strokeOpacity={0.3}
                  label={{ value: "Bullish Divergence Detected", fill: "#f59e0b", fontSize: 11 }}
                />
              )}
              <Line
                type="monotone"
                dataKey="obv"
                stroke="#a78bfa"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
