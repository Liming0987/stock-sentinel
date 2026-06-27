import { readdir, readFile } from "fs/promises";
import path from "path";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowUpRight, ArrowDownRight, ExternalLink } from "lucide-react";

interface StockAnalysis {
  ticker: string;
  company_name: string;
  price: number;
  change_pct: number;
  overall_stance: "accumulate" | "watch" | "hold" | "avoid";
  conviction: number;
  one_liner: string;
  watchlist_priority: "high" | "medium" | "low";
  technical: { wyckoff_phase: string; rsi: number | null; vcp_detected: boolean };
  sentiment: { label: string };
  strategy_signals: unknown[];
}

const STANCE_VARIANT: Record<string, "bullish" | "secondary" | "destructive"> = {
  accumulate: "bullish",
  watch: "secondary",
  hold: "secondary",
  avoid: "destructive",
};

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

async function getAnalyses(date: string): Promise<StockAnalysis[]> {
  const dir = path.join(process.cwd(), "public", "morning-briefs", date);
  const analyses: StockAnalysis[] = [];
  try {
    const entries = await readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      try {
        const json = await readFile(path.join(dir, entry.name, "analysis.json"), "utf-8");
        analyses.push(JSON.parse(json));
      } catch {
        // no analysis.json for this entry
      }
    }
  } catch {
    // date dir doesn't exist
  }
  const ORDER = { accumulate: 0, watch: 1, hold: 2, avoid: 3 };
  const PRIORITY = { high: 0, medium: 1, low: 2 };
  return analyses.sort((a, b) =>
    (ORDER[a.overall_stance] ?? 1) - (ORDER[b.overall_stance] ?? 1) ||
    (PRIORITY[a.watchlist_priority] ?? 1) - (PRIORITY[b.watchlist_priority] ?? 1)
  );
}

export default async function StockBriefsPage() {
  const dates = await getBriefDates();
  const latestDate = dates[0] ?? null;
  const analyses = latestDate ? await getAnalyses(latestDate) : [];

  const accumulate = analyses.filter((a) => a.overall_stance === "accumulate");
  const watch      = analyses.filter((a) => a.overall_stance === "watch");
  const avoid      = analyses.filter((a) => a.overall_stance === "avoid");

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Research"
        title="Stock Briefs"
        description="Pre-market intelligence briefings for every stock in the watchlist — Wyckoff, VCP, DCF, fundamentals, and news catalysts synthesized daily."
      />

      {latestDate ? (
        <div className="space-y-6">
          {/* Header row */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-muted-foreground">{latestDate}</span>
              <span className="text-muted-foreground/40">·</span>
              <span className="text-sm text-muted-foreground">{analyses.length} stocks</span>
              <Badge variant="bullish" className="text-xs">✓ {accumulate.length} Accumulate</Badge>
              <Badge variant="secondary" className="text-xs">👁 {watch.length} Watch</Badge>
              <Badge variant="destructive" className="text-xs">✗ {avoid.length} Avoid</Badge>
            </div>
            <a
              href={`/morning-briefs/${latestDate}/index.html`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-sm text-primary hover:underline"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open full report
            </a>
          </div>

          {/* Stock cards grid */}
          {analyses.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-sm text-muted-foreground">
                No analyses found for {latestDate}.
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {analyses.map((a) => (
                <a
                  key={a.ticker}
                  href={`/morning-briefs/${latestDate}/${a.ticker}.html`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block rounded-xl border bg-card p-4 transition-colors hover:border-primary hover:bg-accent/30"
                >
                  {/* Top row */}
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-base font-bold">{a.ticker}</span>
                      {a.technical?.vcp_detected && (
                        <span className="rounded bg-bullish/10 px-1.5 py-0.5 text-[10px] font-bold text-bullish border border-bullish/20">
                          VCP
                        </span>
                      )}
                      {a.strategy_signals?.length > 0 && (
                        <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-bold text-primary border border-primary/20">
                          ⚡ {a.strategy_signals.length}
                        </span>
                      )}
                    </div>
                    <Badge variant={STANCE_VARIANT[a.overall_stance] ?? "secondary"} className="text-[10px] shrink-0">
                      {a.overall_stance.toUpperCase()}
                    </Badge>
                  </div>

                  {/* Company + price */}
                  <p className="mb-2 text-xs text-muted-foreground truncate">{a.company_name}</p>
                  <div className="mb-2 flex items-baseline gap-2">
                    <span className="font-mono font-semibold">
                      ${Number(a.price).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                    <span className={`flex items-center gap-0.5 text-xs font-mono font-semibold ${Number(a.change_pct) >= 0 ? "text-bullish" : "text-bearish"}`}>
                      {Number(a.change_pct) >= 0 ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                      {Number(a.change_pct) >= 0 ? "+" : ""}{Number(a.change_pct).toFixed(2)}%
                    </span>
                  </div>

                  {/* One-liner */}
                  <p className="mb-3 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                    {a.one_liner}
                  </p>

                  {/* Footer meta */}
                  <div className="text-[11px] text-muted-foreground/70 flex flex-wrap gap-x-3">
                    <span>{a.technical?.wyckoff_phase ?? "—"}</span>
                    {a.technical?.rsi != null && <span>RSI {Number(a.technical.rsi).toFixed(0)}</span>}
                    <span>{a.sentiment?.label ?? "—"}</span>
                  </div>
                </a>
              ))}
            </div>
          )}

          {/* Past briefs */}
          {dates.length > 1 && (
            <div className="space-y-2 border-t pt-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Past Briefs</p>
              <div className="flex flex-wrap gap-2">
                {dates.slice(1).map((d) => (
                  <a
                    key={d}
                    href={`/morning-briefs/${d}/index.html`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-md border px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:border-primary transition-colors"
                  >
                    {d}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <Card>
          <CardContent className="py-16 text-center text-sm text-muted-foreground">
            No briefs generated yet. Run the morning brief to generate your first report.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
