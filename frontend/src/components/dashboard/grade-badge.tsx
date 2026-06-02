"use client";

import { cn } from "@/lib/utils";

const GRADE_STYLES: Record<string, string> = {
  A: "bg-bullish/15 text-bullish border-bullish/30",
  B: "bg-blue-500/15 text-blue-500 border-blue-500/30",
  C: "bg-yellow-500/15 text-yellow-500 border-yellow-500/30",
  D: "bg-orange-500/15 text-orange-500 border-orange-500/30",
  F: "bg-bearish/15 text-bearish border-bearish/30",
};

interface GradeBadgeProps {
  grade: string;
  size?: "sm" | "md";
}

export function GradeBadge({ grade, size = "md" }: GradeBadgeProps) {
  const style = GRADE_STYLES[grade] ?? "bg-muted/50 text-muted-foreground border-muted";
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full border font-bold",
        size === "sm" ? "h-5 w-5 text-[10px]" : "h-7 w-7 text-sm",
        style
      )}
    >
      {grade}
    </span>
  );
}
