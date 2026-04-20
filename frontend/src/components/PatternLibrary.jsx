import React, { useState } from "react";
import { PATTERNS, redact } from "@/lib/patterns";
import { ChevronRight } from "lucide-react";

function PatternCard({ p, index }) {
  const [open, setOpen] = useState(false);
  const { cleaned } = redact(p.example);

  return (
    <button
      onClick={() => setOpen((v) => !v)}
      data-testid={`pattern-card-${p.name}`}
      className="text-left group bg-[#121212] hover:bg-[#1A1A1A] border border-white/10 hover:border-amber-400/40 p-5 transition-colors relative"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-mono tracking-widest text-zinc-500 mb-1">
            // {String(index + 1).padStart(2, "0")} · {p.name}
          </div>
          <div
            style={{ fontFamily: "Cabinet Grotesk, sans-serif" }}
            className="text-lg md:text-xl font-bold text-white"
          >
            {p.label}
          </div>
          <div className="mt-1 text-xs text-zinc-400 leading-relaxed max-w-[38ch]">
            {p.description}
          </div>
        </div>
        <ChevronRight
          size={16}
          className={`text-zinc-600 group-hover:text-amber-400 transition-transform mt-1 ${
            open ? "rotate-90" : ""
          }`}
        />
      </div>

      {open && (
        <div className="mt-4 space-y-2">
          <div className="text-[10px] font-mono tracking-widest text-zinc-500">REGEX</div>
          <pre className="font-mono text-[11px] text-amber-400 bg-black/60 border border-white/5 p-2 overflow-x-auto">
            {String(p.regex)}
          </pre>
          <div className="text-[10px] font-mono tracking-widest text-zinc-500 mt-3">SAMPLE IN</div>
          <pre className="font-mono text-[11px] text-zinc-300 bg-black/60 border border-white/5 p-2 overflow-x-auto whitespace-pre-wrap break-all">
            {p.example}
          </pre>
          <div className="text-[10px] font-mono tracking-widest text-zinc-500 mt-3">REDACTED OUT</div>
          <pre className="font-mono text-[11px] text-zinc-300 bg-black/60 border border-white/5 p-2 overflow-x-auto whitespace-pre-wrap break-all">
            {cleaned.split(/(\[[A-Z_]+\])/).map((chunk, i) =>
              /^\[[A-Z_]+\]$/.test(chunk) ? (
                <span key={i} className="vp-redact text-black">{chunk}</span>
              ) : (
                <span key={i}>{chunk}</span>
              )
            )}
          </pre>
        </div>
      )}
    </button>
  );
}

export default function PatternLibrary() {
  return (
    <section
      id="patterns"
      data-testid="pattern-library-grid"
      className="border-b border-white/10"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-16 md:py-24">
        <div className="mb-10 md:mb-14 flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="text-[11px] font-mono text-amber-400 tracking-[0.2em] mb-2">// 02 PATTERN LIBRARY</div>
            <h2
              style={{ fontFamily: "Cabinet Grotesk, sans-serif" }}
              className="text-3xl md:text-5xl font-bold tracking-tight"
            >
              {PATTERNS.length} ways we've got your back.
            </h2>
            <p className="mt-3 text-zinc-400 max-w-2xl">
              Every pattern below ships with the CLI, the desktop app, and the extension.
              Click any card to inspect the regex and see a before/after.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-[1px] bg-white/10 border border-white/10">
          {PATTERNS.map((p, i) => (
            <div key={p.name} className="bg-[#0A0A0A]">
              <PatternCard p={p} index={i} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
