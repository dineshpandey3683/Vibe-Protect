import React, { useEffect, useState } from "react";
import { CheckCircle2, Shield, Brain, AlertCircle, ChevronDown } from "lucide-react";
import Sparkline from "./Sparkline";
import PatternBreakdown from "./PatternBreakdown";

/**
 * Receipts — proof-points auto-generated from /stats.json and sparklined
 * from /stats-history.jsonl.
 *
 * Both files are produced by scripts/generate_stats.py which runs the same
 * pattern corpus the test suite asserts on. Every number and every point
 * on the sparkline is tied to a green pytest run — "claims" become
 * "receipts", and the trendline shows we stay honest every build.
 *
 * Falls back silently if either file is missing so a fresh checkout
 * without a CI run doesn't render a broken panel.
 */
export default function Receipts() {
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [expanded, setExpanded] = useState(null);   // tile id or null

  useEffect(() => {
    const base = process.env.PUBLIC_URL || "";
    fetch(`${base}/stats.json`, { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setStats)
      .catch(() => {});

    fetch(`${base}/stats-history.jsonl`, { cache: "no-cache" })
      .then((r) => (r.ok ? r.text() : Promise.reject(r.status)))
      .then((txt) => {
        const lines = txt
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean)
          .map((l) => {
            try { return JSON.parse(l); } catch { return null; }
          })
          .filter(Boolean);
        setHistory(lines);
      })
      .catch(() => {});
  }, []);

  if (!stats) return null;

  const generated = stats.generated_at
    ? new Date(stats.generated_at).toISOString().slice(0, 10)
    : "—";

  const detSeries = history.map((h) => h.detection_rate ?? 0);
  const fpSeries  = history.map((h) => h.false_positive_rate ?? 0);
  const patSeries = history.map((h) => h.patterns_active ?? 0);
  const seedMask  = history.map((h) => !!h.seed);
  const hasSeeded = seedMask.some((s) => s);

  const items = [
    {
      id: "detection",
      icon: <CheckCircle2 size={22} className="text-emerald-400" />,
      metric: `${(stats.detection_rate * 100).toFixed(1)}%`,
      label: "detection rate",
      sub: `${stats.synthetic_secrets_tested} synthetic API keys, JWTs, PEMs, DB URLs`,
      testid: "receipt-detection-rate",
      series: detSeries,
      stroke: "#22c55e",
      title: "Detection rate — rolling 30-day history",
      expandable: true,
      hint: "per-pattern breakdown",
    },
    {
      id: "fp",
      icon: <Shield size={22} className="text-emerald-400" />,
      metric: `${(stats.false_positive_rate * 100).toFixed(2)}%`,
      label: "false-positive rate",
      sub: `${stats.false_positives_tested} code, docs & config samples audited`,
      testid: "receipt-fp-rate",
      series: fpSeries,
      stroke: stats.false_positive_rate <= 0.01 ? "#22c55e" : "#facc15",
      title: "False-positive rate — rolling 30-day history",
    },
    {
      id: "patterns",
      icon: <Brain size={22} className="text-amber-400" />,
      metric: `${stats.patterns_active}`,
      label: "patterns + ML entropy",
      sub: stats.ml_entropy_enabled
        ? "Shannon entropy × variety × length × pattern boost"
        : "regex patterns active",
      testid: "receipt-patterns",
      series: patSeries,
      stroke: "#facc15",
      title: "Patterns active — rolling 30-day history",
    },
  ];

  return (
    <section
      id="receipts"
      data-testid="receipts-section"
      className="relative border-b border-white/10 bg-[#0A0A0A]"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-14 md:py-20">
        <div className="flex items-baseline justify-between gap-6 mb-8 flex-wrap">
          <div>
            <div className="font-mono text-[11px] tracking-[0.18em] text-amber-400 mb-2">
              ▍ RECEIPTS, NOT CLAIMS
            </div>
            <h2
              style={{ fontFamily: "Cabinet Grotesk, sans-serif" }}
              className="text-3xl md:text-5xl font-extrabold tracking-tight text-white"
              data-testid="receipts-headline"
            >
              Measured on every build.
            </h2>
          </div>
          <div className="font-mono text-[11px] text-zinc-500 text-right" data-testid="receipts-timestamp">
            generated {generated} · <span className="text-zinc-400">stats.json</span> ·{" "}
            <span className="text-zinc-400">v{stats.version}</span>
            {history.length >= 2 && (
              <div className="mt-1">
                trend · <span className="text-zinc-400">{history.length}-day window</span>
                {hasSeeded && <> · <span className="text-zinc-500">dashed = seed</span></>}
              </div>
            )}
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-px bg-white/10 border border-white/10">
          {items.map((it) => {
            const isExpandable = !!it.expandable;
            const isOpen = expanded === it.id;
            const TileTag = isExpandable ? "button" : "div";
            const tileProps = isExpandable
              ? {
                  onClick: () => setExpanded(isOpen ? null : it.id),
                  "aria-expanded": isOpen,
                  "aria-controls": `${it.testid}-drawer`,
                  type: "button",
                }
              : {};
            return (
              <TileTag
                key={it.label}
                data-testid={it.testid}
                {...tileProps}
                className={`bg-[#0A0A0A] p-7 md:p-9 flex flex-col gap-4 transition-colors text-left w-full ${
                  isExpandable ? "hover:bg-white/[0.03] cursor-pointer" : "hover:bg-white/[0.02]"
                } ${isOpen ? "bg-white/[0.03]" : ""}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {it.icon}
                    <span className="font-mono text-[10px] tracking-[0.16em] text-zinc-500 uppercase">
                      {it.label}
                    </span>
                  </div>
                  <div data-testid={`${it.testid}-sparkline`} className="shrink-0">
                    <Sparkline
                      data={it.series}
                      width={88}
                      height={26}
                      stroke={it.stroke}
                      seedMask={seedMask}
                      title={it.title}
                    />
                  </div>
                </div>
                <div
                  style={{ fontFamily: "Cabinet Grotesk, sans-serif" }}
                  className="text-5xl md:text-6xl font-extrabold tracking-tight text-white leading-none"
                >
                  {it.metric}
                </div>
                <div className="text-sm text-zinc-400 leading-snug">{it.sub}</div>
                {isExpandable && (
                  <div
                    className="mt-1 flex items-center gap-1.5 font-mono text-[10px] text-zinc-500 tracking-widest uppercase"
                    data-testid={`${it.testid}-expand-hint`}
                  >
                    <ChevronDown
                      size={12}
                      className={`transition-transform ${isOpen ? "rotate-180" : ""}`}
                    />
                    {isOpen ? "hide" : "show"} {it.hint}
                  </div>
                )}
              </TileTag>
            );
          })}
        </div>

        {expanded === "detection" && (
          <div
            id="receipt-detection-rate-drawer"
            data-testid="receipt-detection-rate-drawer"
            className="border-x border-b border-white/10 bg-[#0A0A0A] px-7 md:px-9 pb-8"
          >
            <div className="font-mono text-[10px] tracking-[0.16em] text-zinc-500 uppercase pt-6">
              ▍ per-pattern detection · {Object.keys(stats.per_pattern || {}).length} controls
            </div>
            <PatternBreakdown
              perPattern={stats.per_pattern}
              history={history}
              threshold={0.9}
            />
          </div>
        )}

        <div className="mt-6 flex items-center gap-2 font-mono text-[11px] text-zinc-500">
          <AlertCircle size={12} />
          <span>
            Regenerated by <code className="text-zinc-400">scripts/generate_stats.py</code>{" "}
            on every push; trendline reads{" "}
            <code className="text-zinc-400">stats-history.jsonl</code> (rolling 30-day window).
          </span>
        </div>
      </div>
    </section>
  );
}
