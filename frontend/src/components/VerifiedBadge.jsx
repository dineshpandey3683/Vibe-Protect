import React, { useEffect, useState } from "react";
import { BadgeCheck, ArrowUpRight } from "lucide-react";

/**
 * VerifiedBadge — inline hero badge linking to the Receipts section.
 *
 * Pulls live detection/FP numbers from the same /stats.json that feeds
 * the Receipts panel. If stats.json hasn't been generated yet (fresh
 * checkout, no CI run), the badge silently renders nothing — better a
 * clean hero than a half-broken claim.
 *
 * Click → smooth-scrolls to ``#receipts`` so a visitor reaches the
 * buy-vs-build decision with the evidence in view, not buried below
 * the fold.
 */
export default function VerifiedBadge() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const base = process.env.PUBLIC_URL || "";
    fetch(`${base}/stats.json`, { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setStats)
      .catch(() => {});
  }, []);

  if (!stats) return null;

  const det = `${(stats.detection_rate * 100).toFixed(stats.detection_rate === 1 ? 0 : 1)}%`;
  const fp  = `${(stats.false_positive_rate * 100).toFixed(stats.false_positive_rate === 0 ? 0 : 2)}%`;
  const tip = `View live security audit · ${stats.synthetic_secrets_tested} secrets tested · ${stats.false_positives_tested} FPs audited`;

  const scroll = (e) => {
    e.preventDefault();
    const el = document.getElementById("receipts");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    // update the URL without the jump; users can share-link the receipts view
    if (window.history && window.history.pushState) {
      window.history.pushState(null, "", "#receipts");
    }
  };

  return (
    <a
      href="#receipts"
      onClick={scroll}
      data-testid="hero-verified-badge"
      title={tip}
      aria-label={tip}
      className="group inline-flex items-center gap-2 border border-amber-400/40 bg-amber-400/[0.06] hover:bg-amber-400/[0.12] hover:border-amber-400 transition-colors px-3 py-1.5 font-mono text-[11px] tracking-wide"
    >
      <BadgeCheck size={14} className="text-amber-400 shrink-0" strokeWidth={2.2} />
      <span className="text-amber-300">verified</span>
      <span className="text-zinc-600">·</span>
      <span className="text-amber-400 font-semibold">{det}</span>
      <span className="text-zinc-500 hidden sm:inline">detection</span>
      <span className="text-zinc-600 hidden sm:inline">·</span>
      <span className="text-amber-400 font-semibold hidden sm:inline">{fp}</span>
      <span className="text-zinc-500 hidden sm:inline">false-positive</span>
      <ArrowUpRight
        size={12}
        className="text-zinc-500 group-hover:text-amber-400 transition-colors -mr-0.5"
      />
    </a>
  );
}
