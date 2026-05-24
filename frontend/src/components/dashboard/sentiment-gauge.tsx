"use client";

import { cn } from "@/lib/utils";
import { sentimentLabel } from "@/lib/utils";

interface SentimentGaugeProps {
  score: number;
  size?: "sm" | "md" | "lg";
}

export function SentimentGauge({ score, size = "md" }: SentimentGaugeProps) {
  const normalized = ((score + 1) / 2) * 100;
  const label = sentimentLabel(score);

  const dimensions = {
    sm: { width: 80, height: 44, stroke: 6, fontSize: 11, labelSize: 9 },
    md: { width: 120, height: 66, stroke: 8, fontSize: 16, labelSize: 11 },
    lg: { width: 160, height: 88, stroke: 10, fontSize: 20, labelSize: 13 },
  };

  const d = dimensions[size];
  const radius = (d.width - d.stroke) / 2;
  const circumference = Math.PI * radius;
  const progress = (normalized / 100) * circumference;

  const getColor = () => {
    if (score >= 0.2) return "hsl(142, 71%, 45%)";
    if (score > -0.2) return "hsl(220, 9%, 46%)";
    return "hsl(0, 84%, 60%)";
  };

  return (
    <div className="flex flex-col items-center">
      <svg width={d.width} height={d.height} viewBox={`0 0 ${d.width} ${d.height + 4}`}>
        <path
          d={`M ${d.stroke / 2} ${d.height} A ${radius} ${radius} 0 0 1 ${d.width - d.stroke / 2} ${d.height}`}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={d.stroke}
          strokeLinecap="round"
        />
        <path
          d={`M ${d.stroke / 2} ${d.height} A ${radius} ${radius} 0 0 1 ${d.width - d.stroke / 2} ${d.height}`}
          fill="none"
          stroke={getColor()}
          strokeWidth={d.stroke}
          strokeLinecap="round"
          strokeDasharray={`${progress} ${circumference}`}
        />
        <text
          x={d.width / 2}
          y={d.height - 4}
          textAnchor="middle"
          fill="currentColor"
          fontSize={d.fontSize}
          fontWeight="bold"
        >
          {(score * 100).toFixed(0)}
        </text>
      </svg>
      <span
        className={cn(
          "mt-1 font-medium",
          score >= 0.2 ? "text-bullish" : score > -0.2 ? "text-muted-foreground" : "text-bearish"
        )}
        style={{ fontSize: d.labelSize }}
      >
        {label}
      </span>
    </div>
  );
}
