import { readdir } from "fs/promises";
import path from "path";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";

async function getLatestBriefs() {
  const briefsDir = path.join(process.cwd(), "public", "morning-briefs");
  try {
    const entries = await readdir(briefsDir, { withFileTypes: true });
    const dates = entries
      .filter((e) => e.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(e.name))
      .map((e) => e.name)
      .sort()
      .reverse();
    return dates;
  } catch {
    return [];
  }
}

export default async function StockBriefsPage() {
  const dates = await getLatestBriefs();
  const latestDate = dates[0] ?? null;

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Research"
        title="Stock Briefs"
        description="Pre-market intelligence briefings for every stock in the watchlist — Wyckoff, VCP, DCF, fundamentals, and news catalysts synthesized daily."
      />

      {latestDate ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
              Latest — {latestDate}
            </h2>
            <a
              href={`/morning-briefs/${latestDate}/index.html`}
              className="text-sm text-primary hover:underline"
            >
              Full report →
            </a>
          </div>

          <Card>
            <CardContent className="p-0">
              <iframe
                src={`/morning-briefs/${latestDate}/index.html`}
                className="w-full rounded-lg"
                style={{ height: "80vh", border: "none" }}
                title={`Morning Brief ${latestDate}`}
              />
            </CardContent>
          </Card>

          {dates.length > 1 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Past Briefs
              </p>
              <div className="flex flex-wrap gap-2">
                {dates.slice(1).map((d) => (
                  <a
                    key={d}
                    href={`/morning-briefs/${d}/index.html`}
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
