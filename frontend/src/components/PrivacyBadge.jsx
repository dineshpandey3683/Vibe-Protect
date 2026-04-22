import React, { useState } from "react";
import { Lock, X } from "lucide-react";

/**
 * Persistent "zero data collection" badge.
 *
 * Intentionally unobtrusive — floats in the bottom-right corner, links
 * to the full privacy declaration, and is dismissible (session-scoped;
 * pops back on a new tab so a new visitor always sees it once).
 */
export default function PrivacyBadge() {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;

  return (
    <div
      data-testid="privacy-badge"
      className="fixed bottom-4 right-4 z-40 flex items-center gap-2 bg-black/85 backdrop-blur-sm border border-white/10 px-3 py-1.5 font-mono text-[11px] text-zinc-400 shadow-lg"
    >
      <Lock size={11} className="text-amber-400" />
      <span className="hidden sm:inline">zero data collection</span>
      <span className="sm:hidden">zero data</span>
      <span className="text-zinc-600">·</span>
      <a
        href="/privacy"
        className="text-amber-400 hover:text-amber-300 underline-offset-2 hover:underline"
        data-testid="privacy-badge-link"
      >
        read
      </a>
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss privacy badge"
        data-testid="privacy-badge-dismiss"
        className="ml-1 text-zinc-600 hover:text-zinc-300"
      >
        <X size={11} />
      </button>
    </div>
  );
}
