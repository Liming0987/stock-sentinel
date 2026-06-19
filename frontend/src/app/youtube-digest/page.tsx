import { readdir } from "fs/promises";
import path from "path";
import { YouTubeDigestClient } from "./client";

export default async function YouTubeDigestPage() {
  const dataDir = path.join(process.cwd(), "public", "youtube-reports", "data");
  let dates: string[] = [];
  try {
    const files = await readdir(dataDir);
    dates = files
      .filter((f) => /^\d{4}-\d{2}-\d{2}\.json$/.test(f))
      .map((f) => f.replace(".json", ""))
      .sort()
      .reverse();
  } catch {
    // data directory doesn't exist yet — first run
  }
  return <YouTubeDigestClient dates={dates} />;
}
