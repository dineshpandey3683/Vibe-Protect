import React from "react";
import { Lock, ExternalLink, ArrowLeft } from "lucide-react";

/**
 * Stand-alone /privacy route.
 *
 * We don't pull react-router just for one static page, so App.js
 * branches on ``window.location.pathname === "/privacy"`` to render
 * this component. Keep it self-contained — the copy here must stay
 * in lock-step with ``/app/docs/PRIVACY.md``.
 */
export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 md:px-10 py-12 md:py-20 font-['IBM_Plex_Sans',sans-serif]">
      <a
        href="/"
        data-testid="privacy-back-link"
        className="inline-flex items-center gap-2 text-xs font-mono text-zinc-400 hover:text-amber-400 mb-8"
      >
        <ArrowLeft size={14} /> back to vibe.protect
      </a>

      <div className="flex items-center gap-3 mb-4">
        <Lock size={28} className="text-amber-400" />
        <div className="text-[11px] font-mono tracking-widest text-amber-400">
          // PRIVACY DECLARATION · v1.0.0
        </div>
      </div>

      <h1
        style={{ fontFamily: "Cabinet Grotesk, sans-serif" }}
        className="text-4xl md:text-5xl font-bold tracking-tight"
      >
        Zero data collection.
        <br />
        <span className="text-amber-400">Ever.</span>
      </h1>

      <p className="mt-6 text-zinc-400 text-lg">
        Vibe Protect never transmits your clipboard, your secrets, your
        redacted text, or anything about you. Period. This page tells you
        exactly what the code does — not a marketing summary.
      </p>

      <section className="mt-12 space-y-4">
        <h2 className="text-xl font-bold text-white">30-second summary</h2>
        <Row q="Does it transmit my clipboard, secrets, or redacted text?" a="No. Ever." />
        <Row q="Does it send usage analytics / telemetry / crash reports?" a="No." />
        <Row q="Does it upload anything to a cloud backend?" a="No." />
        <Row q="Does it store clipboard history or PII?" a="No." />
        <Row q="Does it phone home at startup?" a="One optional GET. Easy to disable. See below." />
      </section>

      <section className="mt-12 space-y-4">
        <h2 className="text-xl font-bold text-white">What networking actually happens</h2>
        <Mode
          title="Scanning / CI modes — fully offline"
          body="--file, --pre-commit, --install-hook, --json, every VS Code extension command, every Chrome extension action, the web Playground redaction. Zero outbound connections."
        />
        <Mode
          title="Clipboard monitor (interactive desktop / tray mode)"
          body="At startup, the process performs at most two HTTPS GETs — a version check against api.github.com and a pattern-library refresh against raw.githubusercontent.com. Both send only the default urllib User-Agent. Both cache for 6 hours. Neither sends anything about your clipboard, your machine, or your usage."
          mono="vibe-protect --no-update-check --no-pattern-sync"
        />
        <Mode
          title="Optional audit logging"
          body="--audit writes an AES-256-GCM + HMAC-authenticated ledger to ~/.vibeprotect/audit/. Local file only. Never transmitted. Stores event type, timestamp, secret-type label, and confidence — never the plaintext."
        />
      </section>

      <section className="mt-12 space-y-4">
        <h2 className="text-xl font-bold text-white">Verify it yourself</h2>
        <p className="text-zinc-400 text-sm">
          Don't trust us — inspect your live config:
        </p>
        <pre className="bg-black border border-white/10 p-4 font-mono text-[12px] text-amber-400 overflow-x-auto">
{`vibe-protect --verify-telemetry   # inspects your current config
ls -la ~/.vibeprotect/            # shows local files, if any
sudo tcpdump -i any host api.github.com   # watch the wire`}
        </pre>
      </section>

      <section className="mt-12 text-xs font-mono text-zinc-500">
        <p>
          Full declaration:{" "}
          <a
            href="https://github.com/dineshpandey3683/Vibe-Protect/blob/main/docs/PRIVACY.md"
            className="text-amber-400 hover:underline inline-flex items-center gap-1"
            data-testid="privacy-github-link"
          >
            docs/PRIVACY.md on GitHub <ExternalLink size={10} />
          </a>
        </p>
        <p className="mt-2">
          Network requirements:{" "}
          <a
            href="https://github.com/dineshpandey3683/Vibe-Protect/blob/main/docs/NETWORK.md"
            className="text-amber-400 hover:underline inline-flex items-center gap-1"
          >
            docs/NETWORK.md <ExternalLink size={10} />
          </a>
        </p>
        <p className="mt-2">Last updated 2026-04-21 · v1.0.0</p>
      </section>
    </div>
  );
}

function Row({ q, a }) {
  return (
    <div className="grid grid-cols-[1fr_auto] gap-4 border-b border-white/5 pb-3">
      <div className="text-zinc-300 text-sm">{q}</div>
      <div className="font-mono text-amber-400 text-sm">{a}</div>
    </div>
  );
}

function Mode({ title, body, mono }) {
  return (
    <div className="bg-[#0F0F0F] border border-white/10 p-4">
      <div className="font-bold text-sm text-white">{title}</div>
      <p className="mt-2 text-zinc-400 text-sm leading-relaxed">{body}</p>
      {mono && (
        <pre className="mt-3 bg-black border border-white/10 px-3 py-2 font-mono text-[11px] text-amber-400 overflow-x-auto">
          {mono}
        </pre>
      )}
    </div>
  );
}
