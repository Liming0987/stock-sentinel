"use client";

import { useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { VolumeHistoryPoint, VCPAnalysis } from "@/lib/hooks";

const PERIODS = [
  { label: "1M", value: "30d" },
  { label: "3M", value: "90d" },
  { label: "6M", value: "6mo" },
  { label: "1Y", value: "1y" },
] as const;

// SVG coordinate system
const W = 1000;          // total viewBox width
const H = 440;           // total viewBox height
const ML = 58;           // left margin (price labels)
const MR = 62;           // right margin (volume labels)
const CANDLE_TOP = 8;
const CANDLE_BOT = 268;  // candlestick pane bottom
const VOL_TOP = 280;     // volume pane top
const VOL_BOT = 378;     // volume pane bottom
const XAXIS_Y = 400;     // x-axis label baseline
const IW = W - ML - MR; // inner width

function lerp(v: number, lo: number, hi: number, yTop: number, yBot: number) {
  const span = hi - lo || 1;
  return yBot - ((v - lo) / span) * (yBot - yTop);
}

function fmtVol(v: number) {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return String(v);
}

function fmtDate(s: string) { return s.slice(5); }

interface PriceVolumeChartProps {
  data: VolumeHistoryPoint[];
  selectedPeriod: string;
  onPeriodChange: (period: string) => void;
  tradingRange?: { support: number | null; resistance: number | null };
  vcp?: VCPAnalysis | null;
}

export function PriceVolumeChart({ data, selectedPeriod, onPeriodChange, tradingRange, vcp }: PriceVolumeChartProps) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (data.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const rawX = ((e.clientX - rect.left) / rect.width) * W;
    const x = rawX - ML;
    const slotW = IW / data.length;
    const idx = Math.round(x / slotW);
    setHoverIdx(Math.max(0, Math.min(data.length - 1, idx)));
  }, [data]);

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-base">Price &amp; Volume</CardTitle>
          <PeriodPicker selected={selectedPeriod} onChange={onPeriodChange} />
        </CardHeader>
        <CardContent>
          <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
            No data available
          </div>
        </CardContent>
      </Card>
    );
  }

  const n = data.length;
  const slotW = IW / n;
  const bodyW = Math.max(2, slotW * 0.7);
  const wickW = Math.max(1, bodyW * 0.2);

  // Date → index map for VCP overlay
  const dateIndexMap = new Map<string, number>(data.map((d, i) => [d.date, i]));

  // Price scale (candlestick pane)
  const priceValues = data.flatMap(c => [c.high ?? c.close ?? 0, c.low ?? c.open ?? 0]).filter(Boolean);
  const priceMin = Math.min(...priceValues);
  const priceMax = Math.max(...priceValues);
  const pricePad = (priceMax - priceMin) * 0.05;
  const pLo = priceMin - pricePad;
  const pHi = priceMax + pricePad;

  // Extend domain to include support/resistance and VCP pivot if outside range
  const vcpPivot = vcp?.detected ? vcp.pivot : null;
  const effLo = tradingRange?.support != null && tradingRange.support < pLo ? tradingRange.support - pricePad : pLo;
  const effHiBase = tradingRange?.resistance != null && tradingRange.resistance > pHi ? tradingRange.resistance + pricePad : pHi;
  const effHi = vcpPivot != null && vcpPivot > effHiBase ? vcpPivot + pricePad : effHiBase;

  const py = (v: number) => lerp(v, effLo, effHi, CANDLE_TOP, CANDLE_BOT);

  // Volume scale
  const maxVol = Math.max(...data.map(c => c.volume ?? 0), 1);
  const vy = (v: number) => lerp(v, 0, maxVol, VOL_TOP, VOL_BOT);

  // X-axis tick indices — show ~6 labels
  const tickStep = Math.max(1, Math.floor(n / 6));
  const xTicks = Array.from({ length: n }, (_, i) => i).filter(i => i % tickStep === 0 || i === n - 1);

  // Price Y-axis ticks
  const priceTicks = 5;
  const priceTickVals = Array.from({ length: priceTicks }, (_, i) =>
    effLo + (i / (priceTicks - 1)) * (effHi - effLo)
  );

  // Volume Y-axis ticks
  const volTicks = [0, maxVol * 0.5, maxVol];

  const hovered = hoverIdx != null ? data[hoverIdx] : null;
  const hoverX = hoverIdx != null ? ML + hoverIdx * slotW + slotW / 2 : null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base">Price &amp; Volume</CardTitle>
        <PeriodPicker selected={selectedPeriod} onChange={onPeriodChange} />
      </CardHeader>
      <CardContent className="relative">
        {/* Hover tooltip */}
        {hovered && (
          <div
            className="pointer-events-none absolute z-10 rounded-lg border bg-card p-2 text-xs shadow-lg"
            style={{ top: 8, right: 12, minWidth: 160 }}
          >
            <p className="font-semibold mb-1">{hovered.date}</p>
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 font-mono">
              <span className="text-muted-foreground">O</span><span>${hovered.open?.toFixed(2) ?? "—"}</span>
              <span className="text-muted-foreground">H</span><span className="text-bullish">${hovered.high?.toFixed(2) ?? "—"}</span>
              <span className="text-muted-foreground">L</span><span className="text-bearish">${hovered.low?.toFixed(2) ?? "—"}</span>
              <span className="text-muted-foreground">C</span><span>${hovered.close?.toFixed(2) ?? "—"}</span>
              <span className="text-muted-foreground">Vol</span><span>{hovered.volume != null ? fmtVol(hovered.volume) : "—"}</span>
              <span className="text-muted-foreground">Ratio</span><span>{hovered.vol_ratio?.toFixed(2) ?? "—"}×</span>
            </div>
            {hovered.is_spike && (
              <p className="mt-1 text-[10px] text-amber-400">⚡ Volume spike</p>
            )}
          </div>
        )}

        <svg
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          style={{ display: "block", cursor: "crosshair" }}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setHoverIdx(null)}
        >
          {/* ── Grid lines ── */}
          {priceTickVals.map((v, i) => (
            <line key={i} x1={ML} x2={W - MR} y1={py(v)} y2={py(v)}
              stroke="var(--border)" strokeWidth={0.5} strokeDasharray="3 3" />
          ))}
          <line x1={ML} x2={W - MR} y1={VOL_TOP} y2={VOL_TOP}
            stroke="var(--border)" strokeWidth={0.5} strokeDasharray="3 3" />

          {/* ── Price Y-axis labels ── */}
          {priceTickVals.map((v, i) => (
            <text key={i} x={ML - 4} y={py(v) + 4} textAnchor="end"
              fontSize={10} fill="var(--muted-foreground)">
              ${v.toFixed(0)}
            </text>
          ))}

          {/* ── Volume Y-axis labels ── */}
          {volTicks.map((v, i) => (
            <text key={i} x={W - MR + 4} y={vy(v) + 4} textAnchor="start"
              fontSize={10} fill="var(--muted-foreground)">
              {fmtVol(v)}
            </text>
          ))}

          {/* ── Support / Resistance lines ── */}
          {tradingRange?.support != null && (
            <>
              <line x1={ML} x2={W - MR} y1={py(tradingRange.support)} y2={py(tradingRange.support)}
                stroke="#22c55e" strokeWidth={1.5} strokeDasharray="6 3" />
              <text x={ML + 4} y={py(tradingRange.support) - 3} fontSize={10} fill="#22c55e">
                Support ${tradingRange.support.toFixed(0)}
              </text>
            </>
          )}
          {tradingRange?.resistance != null && (
            <>
              <line x1={ML} x2={W - MR} y1={py(tradingRange.resistance)} y2={py(tradingRange.resistance)}
                stroke="#ef4444" strokeWidth={1.5} strokeDasharray="6 3" />
              <text x={ML + 4} y={py(tradingRange.resistance) + 12} fontSize={10} fill="#ef4444">
                Resistance ${tradingRange.resistance.toFixed(0)}
              </text>
            </>
          )}

          {/* ── VCP overlay ── */}
          {vcp?.detected && (() => {
            const pivotY = vcp.pivot != null ? py(vcp.pivot) : null;
            const pivotColor = vcp.status === "breaking_out" ? "#22c55e" : "#e8a33d";
            const zoneColor = "#e8a33d";
            return (
              <g>
                {/* Contraction zone rectangles — same amber, let size & label show tightening */}
                {vcp.contractions.map((c, ci) => {
                  const hiIdx = dateIndexMap.get(c.high_date) ?? -1;
                  const loIdx = dateIndexMap.get(c.low_date) ?? -1;
                  if (hiIdx < 0 || loIdx < 0) return null;
                  const x1 = ML + hiIdx * slotW;
                  const x2 = ML + loIdx * slotW + slotW;
                  const y1 = py(c.high);
                  const y2 = py(c.low);
                  const labelY = Math.max(CANDLE_TOP + 10, y1 - 6);
                  return (
                    <g key={`vcp-c${ci}`}>
                      <rect x={x1} y={y1} width={x2 - x1} height={y2 - y1}
                        fill={zoneColor} fillOpacity={0.10} stroke={zoneColor} strokeOpacity={0.50}
                        strokeWidth={1} rx={2} />
                      <text x={x1 + 4} y={labelY} fontSize={9} fill={zoneColor} opacity={0.95} fontWeight="600">
                        C{ci + 1} {c.depth_pct}%{c.vol_dry ? " vol✓" : ""}
                      </text>
                    </g>
                  );
                })}
                {/* Pivot line */}
                {pivotY != null && (
                  <>
                    <line x1={ML} x2={W - MR} y1={pivotY} y2={pivotY}
                      stroke={pivotColor} strokeWidth={1.5} strokeDasharray="8 4" opacity={0.9} />
                    <rect x={W - MR - 78} y={pivotY - 9} width={76} height={14} rx={3}
                      fill={pivotColor} fillOpacity={0.15} />
                    <text x={W - MR - 5} y={pivotY + 3} textAnchor="end"
                      fontSize={10} fill={pivotColor} fontWeight="600">
                      VCP Pivot ${vcp.pivot?.toFixed(2)}
                    </text>
                  </>
                )}
              </g>
            );
          })()}

          {/* ── Candlesticks ── */}
          {data.map((c, i) => {
            if (c.open == null || c.high == null || c.low == null || c.close == null) return null;
            const bullish = c.close >= c.open;
            const fill = bullish ? "#22c55e" : "#ef4444";
            const cx = ML + i * slotW + slotW / 2;
            const bodyTop = py(Math.max(c.open, c.close));
            const bodyBot = py(Math.min(c.open, c.close));
            const bodyH = Math.max(1, bodyBot - bodyTop);
            const wickTop = py(c.high);
            const wickBot = py(c.low);
            return (
              <g key={c.date}>
                {/* Wick */}
                <rect x={cx - wickW / 2} y={wickTop} width={wickW}
                  height={Math.max(1, wickBot - wickTop)} fill={fill} opacity={0.8} />
                {/* Body */}
                <rect x={cx - bodyW / 2} y={bodyTop} width={bodyW} height={bodyH}
                  fill={fill} rx={1} />
              </g>
            );
          })}

          {/* ── 30d avg volume line ── */}
          {(() => {
            const pts = data
              .map((c, i) => c.avg_vol_30 != null
                ? `${ML + i * slotW + slotW / 2},${vy(c.avg_vol_30)}`
                : null)
              .filter(Boolean)
              .join(" ");
            return pts ? (
              <polyline points={pts} fill="none" stroke="#94a3b8"
                strokeWidth={1.5} strokeDasharray="4 2" />
            ) : null;
          })()}

          {/* ── Volume bars ── */}
          {data.map((c, i) => {
            if (c.volume == null) return null;
            const bullish = (c.close ?? 0) >= (c.open ?? 0);
            const fill = bullish ? "#22c55e" : "#ef4444";
            const cx = ML + i * slotW + slotW / 2;
            const top = vy(c.volume);
            const bot = VOL_BOT;
            return (
              <g key={`vol-${c.date}`}>
                <rect x={cx - bodyW / 2} y={top} width={bodyW}
                  height={Math.max(1, bot - top)} fill={fill} opacity={c.is_spike ? 1 : 0.55}
                  rx={1} />
                {/* Spike dot */}
                {c.is_spike && (
                  <circle cx={cx} cy={top - 4} r={3} fill="#f59e0b" />
                )}
              </g>
            );
          })}

          {/* ── Hover crosshair ── */}
          {hoverX != null && (
            <line x1={hoverX} x2={hoverX} y1={CANDLE_TOP} y2={VOL_BOT}
              stroke="var(--muted-foreground)" strokeWidth={1} strokeDasharray="4 3" opacity={0.6} />
          )}

          {/* ── X-axis labels ── */}
          {xTicks.map(i => (
            <text key={i}
              x={ML + i * slotW + slotW / 2}
              y={XAXIS_Y}
              textAnchor="middle"
              fontSize={10}
              fill="var(--muted-foreground)"
            >
              {fmtDate(data[i].date)}
            </text>
          ))}

          {/* ── Pane borders ── */}
          <rect x={ML} y={CANDLE_TOP} width={IW} height={CANDLE_BOT - CANDLE_TOP}
            fill="none" stroke="var(--border)" strokeWidth={0.5} />
          <rect x={ML} y={VOL_TOP} width={IW} height={VOL_BOT - VOL_TOP}
            fill="none" stroke="var(--border)" strokeWidth={0.5} />
        </svg>

        {/* Legend */}
        <div className="mt-2 flex items-center gap-4 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-3 rounded-sm bg-[#22c55e]" />Up day
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-3 rounded-sm bg-[#ef4444]" />Down day
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-px w-5 bg-[#94a3b8]" style={{ borderTop: "1.5px dashed #94a3b8" }} />30d avg vol
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-amber-400" />Volume spike
          </span>
          {vcp?.detected && (
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-5 rounded-sm bg-amber-400/20 border border-amber-400/50" />VCP zones
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function PeriodPicker({ selected, onChange }: { selected: string; onChange: (v: string) => void }) {
  return (
    <div className="flex gap-1">
      {PERIODS.map(({ label, value }) => (
        <button
          key={value}
          onClick={() => onChange(value)}
          className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
            selected === value
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-foreground"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
