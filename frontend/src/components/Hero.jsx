import React, { useEffect, useState } from "react";
import { ArrowRight, Terminal, Chrome, Monitor } from "lucide-react";
import VerifiedBadge from "./VerifiedBadge";

// pre-scripted "typing then redacting" hero demo
const LINES = [
  {
    text: "export OPENAI_API_KEY=sk-proj-qR7pK2mNvEwXzB9aLdTfYh3J",
    redact: { start: 21, end: 58 },
    tag: "OPENAI_API_KEY",
  },
  {
    text: "ssh alice@10.0.13.42  # prod-web-03",
    redact: { start: 10, end: 20 },
    tag: "IPV4",
  },
  {
    text: 'DATABASE_URL="postgresql://admin:h3llfire!@db:5432/prod"',
    redact: { start: 14, end: 55 },
    tag: "DB_CONNECTION_STRING",
  },
  {
    text: "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
    redact: { start: 18, end: 38 },
    tag: "AWS_ACCESS_KEY",
  },
];

function TypingDemo() {
  const [line, setLine] = useState(0);
  const [shown, setShown] = useState("");
  const [redacted, setRedacted] = useState(false);

  useEffect(() => {
    const L = LINES[line];
    setShown("");
    setRedacted(false);
    let i = 0;
    const typer = setInterval(() => {
      i += 1;
      setShown(L.text.slice(0, i));
      if (i >= L.text.length) {
        clearInterval(typer);
        setTimeout(() => setRedacted(true), 450);
        setTimeout(() => setLine((x) => (x + 1) % LINES.length), 2600);
      }
    }, 28);
    return () => clearInterval(typer);
  }, [line]);

  const L = LINES[line];
  const before = shown.slice(0, L.redact.start);
  const secret = shown.slice(L.redact.start, L.redact.end);
  const after = shown.slice(L.redact.end);

  return (
    <div className="relative">
      <pre className="font-mono text-[13px] md:text-[15px] leading-relaxed whitespace-pre-wrap break-all text-zinc-300 min-h-[140px]">
        <span className="text-amber-400 select-none">$ </span>
        {before}
        {redacted ? (
          <span className="vp-redact text-black">[{L.tag}]</span>
        ) : (
          <span>{secret}</span>
        )}
        {after}
        <span className="vp-blink text-amber-400 ml-0.5">▋</span>
      </pre>
    </div>
  );
}

export default function Hero() {
  return (
    <section
      id="top"
      data-testid="hero-section"
      className="relative overflow-hidden border-b border-white/10"
    >
      <div className="absolute inset-0 vp-grid opacity-60 pointer-events-none" />
      <div className="relative max-w-7xl mx-auto px-6 md:px-10 pt-16 md:pt-24 pb-20 md:pb-28 grid md:grid-cols-12 gap-10 md:gap-16 items-center">
        <div className="md:col-span-7">
          <div
            className="inline-flex items-center gap-2 border border-white/10 text-[11px] font-mono px-2.5 py-1 mb-8 text-zinc-400"
            data-testid="hero-eyebrow"
          >
            <span className="relative flex w-1.5 h-1.5">
              <span className="absolute inset-0 bg-amber-400 rounded-full animate-ping opacity-70" />
              <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-amber-400" />
            </span>
            CLIPBOARD GUARDIAN · ARMED & WATCHING
          </div>
          <h1
            style={{ fontFamily: "Cabinet Grotesk, sans-serif" }}
            className="text-5xl md:text-7xl font-extrabold tracking-tight leading-[0.95] text-white"
            data-testid="hero-headline"
          >
            Stop pasting
            <br />
            your{" "}
            <span className="relative inline-block">
              <span className="relative z-10">secrets</span>
              <span className="absolute inset-x-0 bottom-1 h-3 bg-amber-400/90 z-0" />
            </span>{" "}
            into
            <br />
            AI chats.
          </h1>
          <p className="mt-6 text-lg md:text-xl text-zinc-400 max-w-xl leading-relaxed" data-testid="hero-subhead">
            Vibe Protect watches your clipboard and <em className="not-italic text-white">auto-redacts</em>{" "}
            API keys, tokens, emails, IPs and more —{" "}
            <span className="font-mono text-amber-400">before</span> they reach ChatGPT,
            a Slack DM, or a GitHub issue.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-3">
            <a
              href="#playground"
              data-testid="hero-cta-playground"
              className="inline-flex items-center gap-2 bg-amber-400 hover:bg-amber-300 text-black font-bold px-5 py-3 transition-colors"
            >
              Try the playground <ArrowRight size={16} />
            </a>
            <a
              href="#downloads"
              data-testid="hero-cta-install"
              className="inline-flex items-center gap-2 border border-white/20 hover:border-white/50 hover:bg-white/5 text-zinc-100 px-5 py-3 font-mono text-sm transition-colors"
            >
              Install on your machine
            </a>
            <VerifiedBadge />
          </div>
          <div className="mt-10 flex items-center gap-6 text-[11px] font-mono text-zinc-500">
            <span className="flex items-center gap-2"><Terminal size={13} className="text-amber-400"/> CLI</span>
            <span className="flex items-center gap-2"><Monitor size={13} className="text-amber-400"/> Desktop</span>
            <span className="flex items-center gap-2"><Chrome size={13} className="text-amber-400"/> Extension</span>
            <span className="hidden sm:inline">· 18 patterns active · MIT</span>
          </div>
        </div>

        <div className="md:col-span-5">
          <div className="relative border border-white/10 bg-[#0A0A0A]">
            <div className="flex items-center gap-1.5 border-b border-white/10 px-3 py-2">
              <span className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
              <span className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
              <span className="ml-3 font-mono text-[10px] text-zinc-500 tracking-widest">
                clipboard • vibe_protect
              </span>
              <span className="ml-auto font-mono text-[10px] text-amber-400">● LIVE</span>
            </div>
            <div className="relative p-5 md:p-7 vp-scan">
              <TypingDemo />
            </div>
            <div className="flex items-center justify-between border-t border-white/10 px-3 py-2 font-mono text-[10px] text-zinc-500">
              <span>polling @ 300ms · local regex only</span>
              <span className="text-amber-400">0 secrets escaped ✓</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
