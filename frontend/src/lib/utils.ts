import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(num: number): string {
  if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(1) + "B";
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + "M";
  if (num >= 1_000) return (num / 1_000).toFixed(1) + "K";
  return num.toString();
}

export function formatPrice(price: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(price);
}

export function formatPercent(value: number): string {
  return (value >= 0 ? "+" : "") + value.toFixed(2) + "%";
}

export function sentimentLabel(score: number): string {
  if (score >= 0.5) return "Very Bullish";
  if (score >= 0.2) return "Bullish";
  if (score > -0.2) return "Neutral";
  if (score > -0.5) return "Bearish";
  return "Very Bearish";
}

export function sentimentColor(score: number): string {
  if (score >= 0.2) return "text-bullish";
  if (score > -0.2) return "text-neutral";
  return "text-bearish";
}

export function timeAgo(date: string | Date): string {
  const now = new Date();
  const past = new Date(date);
  const seconds = Math.floor((now.getTime() - past.getTime()) / 1000);

  if (seconds < 60) return "just now";
  if (seconds < 3600) return Math.floor(seconds / 60) + "m ago";
  if (seconds < 86400) return Math.floor(seconds / 3600) + "h ago";
  return Math.floor(seconds / 86400) + "d ago";
}
