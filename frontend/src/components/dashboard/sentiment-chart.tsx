"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Bar,
  ComposedChart,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity } from "lucide-react";

interface DataPoint {
  date: string;
  sentiment: number;
  mentions: number;
}

interface SentimentChartProps {
  data: DataPoint[];
  title?: string;
}

export function SentimentChart({ data, title = "Market Sentiment" }: SentimentChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="sentimentGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(142, 71%, 45%)" stopOpacity={0.3} />
                  <stop offset="50%" stopColor="hsl(142, 71%, 45%)" stopOpacity={0.05} />
                  <stop offset="95%" stopColor="hsl(0, 84%, 60%)" stopOpacity={0.3} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickFormatter={(v) => v.slice(5)}
              />
              <YAxis
                yAxisId="sentiment"
                domain={[-1, 1]}
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickFormatter={(v: number) => v.toFixed(1)}
              />
              <YAxis
                yAxisId="mentions"
                orientation="right"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                labelStyle={{ color: "hsl(var(--foreground))" }}
              />
              <Bar
                yAxisId="mentions"
                dataKey="mentions"
                fill="hsl(var(--primary))"
                opacity={0.2}
                radius={[2, 2, 0, 0]}
              />
              <Area
                yAxisId="sentiment"
                type="monotone"
                dataKey="sentiment"
                stroke="hsl(142, 71%, 45%)"
                fill="url(#sentimentGradient)"
                strokeWidth={2}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
