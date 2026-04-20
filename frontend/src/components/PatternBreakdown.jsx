import React from "react";
import Sparkline from "./Sparkline";

/**
 * PatternBreakdown — per-pattern audit-trail rendered inside a Receipts
 * tile drawer. Shows name, hit/total ratio, a coverage bar, and a
 * micro-sparkline of that pattern's history across the rolling window.
 *
 * Flags any pattern below ``threshold`` (default 90%) in amber so a
 * CISO skimming the list can see at a glance which controls are drifting.
 *
 * Props
 * -----
 *   perPattern  { [name]: { hit, total } }   latest snapshot
 *   history     array of full stats snapshots (may be empty)
 *   threshold   number                       amber boundary (default 0.9)
 */
export default function PatternBreakdown({ perPattern, history = [], threshold = 0.9 }) {
  const names = Object.keys(perPattern || {});
  if (!names.length) return null;

  // Build per-pattern time series from history:
  //   seriesFor(name) = [ rate_day1, rate_day2, ... ]
  const seriesFor = (name) =>
    history
      .map((h) => {
        const p = h.per_pattern && h.per_pattern[name];
        if (!p || !p.total) return null;
        return p.hit / p.total;
      })
      .filter((v) => v !== null);

  // Stable ordering: latest-hit-rate DESC, then alphabetical — puts any
  // underperformers at the bottom where they're easier to spot.
  const rows = names
    .map((name) => {
      const cur = perPattern[name] || { hit: 0, total: 0 };
      const rate = cur.total ? cur.hit / cur.total : 0;
      return { name, hit: cur.hit, total: cur.total, rate, series: seriesFor(name) };
    })
    .sort((a, b) => b.rate - a.rate || a.name.localeCompare(b.name));

  return (
    <div
      data-testid="pattern-breakdown"
      className="grid md:grid-cols-2 gap-x-8 gap-y-2 mt-6 pt-6 border-t border-white/10"
    >
      {rows.map((r) => {
        const below = r.rate < threshold;
        const stroke = below ? "#facc15" : "#22c55e";
        const barColour = below ? "bg-amber-400" : "bg-emerald-400";
        const pct = Math.round(r.rate * 100);
        return (
          <div
            key={r.name}
            data-testid={`pattern-row-${r.name}`}
            className="flex items-center gap-3 font-mono text-[12px] py-1"
          >
            <span
              className={`flex-1 truncate ${below ? "text-amber-400" : "text-zinc-300"}`}
              title={r.name}
            >
              {r.name}
            </span>
            <div className="relative w-20 h-1.5 bg-white/[0.06] overflow-hidden shrink-0">
              <div
                className={`absolute inset-y-0 left-0 ${barColour} transition-all`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span
              className={`w-14 text-right tabular-nums ${below ? "text-amber-400" : "text-zinc-400"}`}
            >
              {r.hit}/{r.total}
            </span>
            <div className="w-10 shrink-0">
              <Sparkline
                data={r.series}
                width={40}
                height={14}
                stroke={stroke}
                title={`${r.name} over ${r.series.length}-day window`}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
