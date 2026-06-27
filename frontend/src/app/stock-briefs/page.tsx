import { readdir, readFile } from "fs/promises";
import path from "path";
import { StockBriefsClient } from "./client";
import { PageHeader } from "@/components/layout/page-header";

export interface StockAnalysis {
  ticker: string;
  company_name: string;
  price: number;
  change_pct: number;
  overall_stance: "accumulate" | "watch" | "hold" | "avoid";
  conviction: number;
  one_liner: string;
  watchlist_priority: "high" | "medium" | "low";
  technical: {
    wyckoff_phase: string;
    rsi: number | null;
    vcp_detected: boolean;
    wyckoff_bias: string;
    wyckoff_signals_detected: number;
  };
  sentiment: { label: string; score: number };
  strategy_signals: unknown[];
}

async function getBriefDates(): Promise<string[]> {
  const dir = path.join(process.cwd(), "public", "morning-briefs");
  try {
    const entries = await readdir(dir, { withFileTypes: true });
    return entries
      .filter((e) => e.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(e.name))
      .map((e) => e.name)
      .sort()
      .reverse();
  } catch {
    return [];
  }
}

async function getAnalysesForDate(date: string): Promise<StockAnalysis[]> {
  const dir = path.join(process.cwd(), "public", "morning-briefs", date);
  const analyses: StockAnalysis[] = [];
  try {
    const entries = await readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      try {
        const raw = await readFile(path.join(dir, entry.name, "analysis.json"), "utf-8");
        analyses.push(JSON.parse(raw));
      } catch {
        // no analysis.json
      }
    }
  } catch {
    // date dir missing
  }
  const ORDER = { accumulate: 0, watch: 1, hold: 2, avoid: 3 };
  const PRI = { high: 0, medium: 1, low: 2 };
  return analyses.sort(
    (a, b) =>
      (ORDER[a.overall_stance] ?? 1) - (ORDER[b.overall_stance] ?? 1) ||
      (PRI[a.watchlist_priority] ?? 1) - (PRI[b.watchlist_priority] ?? 1)
  );
}

export default async function StockBriefsPage() {
  const dates = await getBriefDates();
  const allData: Record<string, StockAnalysis[]> = {};
  for (const d of dates) {
    allData[d] = await getAnalysesForDate(d);
  }

  if (dates.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          kicker="Research"
          title="Stock Briefs"
          description="Pre-market intelligence briefings for every stock in the watchlist — Wyckoff, VCP, DCF, fundamentals, and news catalysts synthesized daily."
        />
        <p className="text-sm text-muted-foreground">
          No briefs generated yet. Run the morning brief to generate your first report.
        </p>
      </div>
    );
  }

  return <StockBriefsClient dates={dates} allData={allData} />;
}
