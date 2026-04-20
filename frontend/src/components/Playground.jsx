import React, { useMemo, useState, useEffect } from "react";
import { PATTERNS, redact } from "@/lib/patterns";
import { redactAdvanced } from "@/lib/advancedDetector";
import { Zap, RotateCcw, Copy, Check, Sparkles } from "lucide-react";
import axios from "axios";

const SAMPLE = `# a few things you should NEVER paste into a chat window

export OPENAI_API_KEY=sk-proj-qR7pK2mNvEwXzB9aLdTfYh3JwC5xPnM2vK8Bd0
ANTHROPIC_API_KEY=sk-ant-api03-Ax9XyZ12PqRsTuVwB3mNoPqRsTuVwXyZaBcDeFgHiJ
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
GITHUB_TOKEN=ghp_A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8
DATABASE_URL="postgresql://admin:h3llfire!@db.prod.example.com:5432/app"
STRIPE_SECRET=sk_live_51HqABCDEFghijklmnopqrstuvwxyz1234
JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkFsaWNlIn0.abc123xyz789

# and the classic
alice@macbook-pro:~$ curl http://10.0.13.42/admin -u alice@example.com:hunter2
`;

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function HighlightedOutput({ text, matches }) {
  if (!text) return <span className="text-zinc-600">[output appears here as you type…]</span>;
  if (!matches.length) return <span>{text}</span>;

  // matches are given against ORIGINAL text. For display we use cleaned text
  // and rebuild highlighted blocks from the inserted [TAG] substrings.
  const parts = [];
  let cursor = 0;
  // re-scan cleaned text for our own masks — they're the only uppercase-tagged blocks we inserted
  const maskRe = /\[[A-Z_]+\]/g;
  let m;
  while ((m = maskRe.exec(text)) !== null) {
    if (m.index > cursor) parts.push(<span key={`t-${cursor}`}>{text.slice(cursor, m.index)}</span>);
    parts.push(
      <span key={`r-${m.index}`} className="vp-redact text-black">
        {m[0]}
      </span>
    );
    cursor = m.index + m[0].length;
  }
  if (cursor < text.length) parts.push(<span key="t-end">{text.slice(cursor)}</span>);
  return <>{parts}</>;
}

export default function Playground() {
  const [input, setInput] = useState(SAMPLE);
  const [copied, setCopied] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const [serverVerified, setServerVerified] = useState(null); // null | boolean

  const { cleaned, matches } = useMemo(
    () => (advanced ? redactAdvanced(input) : redact(input)),
    [input, advanced]
  );

  // summary by pattern
  const summary = useMemo(() => {
    const c = {};
    for (const m of matches) c[m.pattern] = (c[m.pattern] || 0) + 1;
    return Object.entries(c).sort((a, b) => b[1] - a[1]);
  }, [matches]);

  const charsSaved = Math.max(0, input.length - cleaned.length);

  const doCopy = async () => {
    try {
      await navigator.clipboard.writeText(cleaned);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* ignore */
    }
  };

  const reset = () => setInput(SAMPLE);
  const clearAll = () => setInput("");

  // optional: re-verify server-side
  const verify = async () => {
    try {
      const { data } = await axios.post(`${BACKEND_URL}/api/redact`, { text: input, advanced });
      setServerVerified(data.matches.length === matches.length);
      setTimeout(() => setServerVerified(null), 2200);
    } catch {
      setServerVerified(false);
      setTimeout(() => setServerVerified(null), 2200);
    }
  };

  // autoverify once on mount so the backend is seeded with an event
  useEffect(() => {
    verify();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section
      id="playground"
      data-testid="live-playground-container"
      className="relative border-b border-white/10"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-16 md:py-24">
        <div className="flex items-end justify-between flex-wrap gap-4 mb-8">
          <div>
            <div className="text-[11px] font-mono text-amber-400 tracking-[0.2em] mb-2">// 01 PLAYGROUND</div>
            <h2
              style={{ fontFamily: "Cabinet Grotesk, sans-serif" }}
              className="text-3xl md:text-5xl font-bold tracking-tight"
            >
              Paste anything. Watch it get scrubbed.
            </h2>
            <p className="mt-3 text-zinc-400 max-w-2xl">
              Type or paste on the left. The right pane updates in real time using the exact
              same regex library that powers the CLI, desktop app, and browser extension.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAdvanced((v) => !v)}
              data-testid="playground-advanced-toggle"
              aria-pressed={advanced}
              title="Entropy-aware detection + context filtering + catch-all"
              className={`inline-flex items-center gap-1.5 text-xs font-mono px-3 py-2 border transition-colors ${
                advanced
                  ? "bg-amber-400 text-black border-amber-400 hover:bg-amber-300"
                  : "text-zinc-400 hover:text-white border-white/10 hover:border-white/30"
              }`}
            >
              <Sparkles size={13} />
              {advanced ? "advanced: ON" : "advanced: off"}
            </button>
            <button
              onClick={reset}
              data-testid="playground-reset-btn"
              className="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-white border border-white/10 hover:border-white/30 px-3 py-2"
            >
              <RotateCcw size={13} /> sample
            </button>
            <button
              onClick={clearAll}
              data-testid="playground-clear-btn"
              className="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-white border border-white/10 hover:border-white/30 px-3 py-2"
            >
              clear
            </button>
            <button
              onClick={verify}
              data-testid="playground-verify-btn"
              className="inline-flex items-center gap-1.5 text-xs font-mono text-amber-400 hover:text-amber-300 border border-amber-400/40 hover:border-amber-400 px-3 py-2"
            >
              <Zap size={13} /> verify server-side
            </button>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-[1px] bg-white/10 border border-white/10">
          {/* input */}
          <div className="bg-[#0A0A0A]">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-2 font-mono text-[10px] text-zinc-500 tracking-widest">
              <span>INPUT · raw text</span>
              <span>{input.length} chars</span>
            </div>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              spellCheck={false}
              data-testid="playground-input-textarea"
              className="w-full h-[440px] resize-none bg-transparent p-4 font-mono text-[13px] leading-relaxed text-zinc-200 focus:outline-none"
              placeholder="# Try dropping a .env file here…"
            />
          </div>
          {/* output */}
          <div className="bg-[#0A0A0A]">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-2 font-mono text-[10px] text-zinc-500 tracking-widest">
              <span className="flex items-center gap-2">
                OUTPUT · scrubbed
                {serverVerified === true && (
                  <span className="text-amber-400">✓ verified</span>
                )}
                {serverVerified === false && (
                  <span className="text-red-400">✗ mismatch</span>
                )}
              </span>
              <button
                onClick={doCopy}
                data-testid="playground-copy-btn"
                className="inline-flex items-center gap-1 hover:text-amber-400"
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}{" "}
                {copied ? "copied" : "copy cleaned"}
              </button>
            </div>
            <pre
              className="w-full h-[440px] overflow-auto p-4 font-mono text-[13px] leading-relaxed text-zinc-200 whitespace-pre-wrap break-all"
              data-testid="playground-output-pane"
            >
              <HighlightedOutput text={cleaned} matches={matches} />
            </pre>
          </div>
        </div>

        {/* summary bar */}
        <div
          className="grid grid-cols-2 md:grid-cols-4 gap-[1px] bg-white/10 border border-white/10 border-t-0"
          data-testid="playground-summary-bar"
        >
          <div className="bg-[#0A0A0A] p-4">
            <div className="text-[10px] font-mono text-zinc-500 tracking-widest">SECRETS CAUGHT</div>
            <div className="mt-1 text-3xl font-bold font-mono text-amber-400">{matches.length}</div>
          </div>
          <div className="bg-[#0A0A0A] p-4">
            <div className="text-[10px] font-mono text-zinc-500 tracking-widest">CHARS SCRUBBED</div>
            <div className="mt-1 text-3xl font-bold font-mono text-white">{charsSaved}</div>
          </div>
          <div className="bg-[#0A0A0A] p-4">
            <div className="text-[10px] font-mono text-zinc-500 tracking-widest">PATTERNS ACTIVE</div>
            <div className="mt-1 text-3xl font-bold font-mono text-white">{PATTERNS.length}</div>
          </div>
          <div className="bg-[#0A0A0A] p-4 overflow-hidden">
            <div className="text-[10px] font-mono text-zinc-500 tracking-widest">BY TYPE</div>
            <div className="mt-2 flex flex-wrap gap-1.5 overflow-auto max-h-16">
              {summary.length === 0 && (
                <span className="text-xs font-mono text-zinc-600">—</span>
              )}
              {summary.map(([name, n]) => (
                <span
                  key={name}
                  className="text-[10px] font-mono text-amber-400 border border-amber-400/40 px-1.5 py-0.5"
                >
                  {name} ×{n}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
