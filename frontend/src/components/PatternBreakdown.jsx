import React, { useState } from "react";
import { Copy, Check } from "lucide-react";
import Sparkline from "./Sparkline";

/**
 * PatternBreakdown — per-pattern audit-trail rendered inside a Receipts
 * tile drawer. Shows name, hit/total ratio, a coverage bar, and a
 * micro-sparkline of that pattern's history across the rolling window.
 *
 * Flags any pattern below ``threshold`` (default 90%) in amber so a
 * CISO skimming the list can see at a glance which controls are drifting.
 *
 * Includes a "Copy as Markdown" button that builds a paste-ready
 * evidence table — one click turns the audit trail into something a
 * security reviewer can drop straight into a vendor questionnaire.
 *
 * Props
 * -----
 *   perPattern   { [name]: { hit, total } }   latest snapshot
 *   history      array of full stats snapshots (may be empty)
 *   threshold    number                       amber boundary (default 0.9)
 *   generatedAt  string | undefined           ISO timestamp of latest run
 *   version      string | undefined           app version
 */

// Unicode block sparkline characters (low → high).
const BLOCKS = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"];

function asciiSpark(series) {
  if (!series || !series.length) return "—";
  const lo = Math.min(...series);
  const hi = Math.max(...series);
  const range = hi - lo || 1;
  return series
    .map((v) => {
      const idx = Math.min(BLOCKS.length - 1, Math.floor(((v - lo) / range) * BLOCKS.length));
      return BLOCKS[idx];
    })
    .join("");
}

function buildMarkdown(rows, meta) {
  const header =
    `# Vibe Protect — per-pattern detection evidence\n\n` +
    (meta.generatedAt ? `Generated: \`${meta.generatedAt}\`  \n` : "") +
    (meta.version ? `Version: \`${meta.version}\`  \n` : "") +
    (meta.historyDays ? `Rolling window: ${meta.historyDays} day(s)  \n` : "") +
    `\n`;
  const table = [
    "| Pattern | Detection | Hit / Total | Trend (rolling window) |",
    "| --- | ---: | ---: | :--- |",
    ...rows.map((r) => {
      const pct = (r.rate * 100).toFixed(1) + "%";
      const flag = r.rate < 0.9 ? " ⚠" : "";
      const spark = asciiSpark(r.series);
      return `| \`${r.name}\` | ${pct}${flag} | ${r.hit}/${r.total} | \`${spark}\` |`;
    }),
  ].join("\n");
  return header + table + "\n";
}

async function copyText(text) {
  // modern API
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return true;
  }
  // fallback for non-https / older browsers
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand("copy");
    return true;
  } finally {
    document.body.removeChild(ta);
  }
}

export default function PatternBreakdown({
  perPattern,
  history = [],
  threshold = 0.9,
  generatedAt,
  version,
}) {
  const [copied, setCopied] = useState(false);
  const names = Object.keys(perPattern || {});
  if (!names.length) return null;

  const seriesFor = (name) =>
    history
      .map((h) => {
        const p = h.per_pattern && h.per_pattern[name];
        if (!p || !p.total) return null;
        return p.hit / p.total;
      })
      .filter((v) => v !== null);

  const rows = names
    .map((name) => {
      const cur = perPattern[name] || { hit: 0, total: 0 };
      const rate = cur.total ? cur.hit / cur.total : 0;
      return { name, hit: cur.hit, total: cur.total, rate, series: seriesFor(name) };
    })
    .sort((a, b) => b.rate - a.rate || a.name.localeCompare(b.name));

  const handleCopy = async () => {
    const md = buildMarkdown(rows, {
      generatedAt,
      version,
      historyDays: history.length,
    });
    try {
      await copyText(md);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // eslint-disable-next-line no-alert
      alert("Copy failed — your browser blocked clipboard access.");
    }
  };

  return (
    <>
      <div className="flex items-center justify-between mt-4">
        <div className="font-mono text-[10px] tracking-[0.16em] text-zinc-500 uppercase">
          {rows.length} controls · sorted by detection rate
        </div>
        <button
          type="button"
          onClick={handleCopy}
          data-testid="pattern-breakdown-copy-md"
          aria-live="polite"
          className={`inline-flex items-center gap-2 border px-3 py-1.5 font-mono text-[11px] tracking-wide transition-colors ${
            copied
              ? "border-emerald-400/60 text-emerald-400 bg-emerald-400/5"
              : "border-white/15 text-zinc-300 hover:border-amber-400 hover:text-amber-400 hover:bg-amber-400/5"
          }`}
        >
          {copied ? (
            <>
              <Check size={13} />
              <span>copied · paste into your security review</span>
            </>
          ) : (
            <>
              <Copy size={13} />
              <span>copy as markdown</span>
            </>
          )}
        </button>
      </div>

      <div
        data-testid="pattern-breakdown"
        className="grid md:grid-cols-2 gap-x-8 gap-y-2 mt-4 pt-4 border-t border-white/10"
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
    </>
  );
}

export { asciiSpark, buildMarkdown };
