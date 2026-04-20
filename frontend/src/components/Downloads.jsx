import React, { useState } from "react";
import { Terminal, Monitor, Chrome, Copy, Check, Github, Download } from "lucide-react";
import { toast } from "sonner";

const CARDS = [
  {
    name: "cli",
    icon: Terminal,
    title: "CLI",
    tagline: "One Python script. Runs in your terminal.",
    install: "pip install pyperclip plyer\npython vibe_protect.py",
    bullets: [
      "macOS · Linux · Windows",
      "Desktop notifications",
      "JSONL event log",
      "--list-patterns, --quiet, --no-notify",
    ],
    href: "cli/",
  },
  {
    name: "desktop",
    icon: Monitor,
    title: "Desktop GUI",
    tagline: "A native window with live history.",
    install: "pip install pyperclip\npython desktop/vibe_desktop.py",
    bullets: [
      "Tkinter — no heavyweight deps",
      "Pause / arm with one click",
      "Live redaction feed + counters",
      "100% local, no network calls",
    ],
    href: "desktop/",
  },
  {
    name: "extension",
    icon: Chrome,
    title: "Browser Extension",
    tagline: "Intercepts every copy across every tab.",
    install: "chrome://extensions → Load unpacked\nselect /extension",
    bullets: [
      "Manifest v3 · Chrome, Edge, Brave, Arc",
      "Firefox (about:debugging)",
      "Per-pattern toggle in Options",
      "Badge counter + popup history",
    ],
    href: "extension/",
  },
];

function Card({ c }) {
  const [copied, setCopied] = useState(false);
  const doCopy = async () => {
    try {
      await navigator.clipboard.writeText(c.install);
      setCopied(true);
      toast.success(`${c.title} install command copied`);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      toast.error("Clipboard blocked — please copy manually");
    }
  };
  const Icon = c.icon;
  return (
    <div
      data-testid={`download-card-${c.name}`}
      className="group bg-[#121212] hover:bg-[#1A1A1A] border border-white/10 hover:border-amber-400/40 p-6 md:p-8 transition-colors flex flex-col"
    >
      <div className="flex items-center gap-3 mb-5">
        <span className="inline-flex items-center justify-center w-10 h-10 border border-amber-400/40 text-amber-400">
          <Icon size={18} />
        </span>
        <div>
          <div className="text-[10px] font-mono tracking-widest text-zinc-500">{c.name.toUpperCase()}</div>
          <div
            style={{ fontFamily: "Cabinet Grotesk, sans-serif" }}
            className="text-2xl font-bold text-white"
          >
            {c.title}
          </div>
        </div>
      </div>
      <p className="text-zinc-400 text-sm mb-6 leading-relaxed">{c.tagline}</p>
      <ul className="space-y-2 text-xs text-zinc-400 mb-6">
        {c.bullets.map((b) => (
          <li key={b} className="flex items-start gap-2">
            <span className="text-amber-400 font-mono mt-0.5">›</span>
            <span>{b}</span>
          </li>
        ))}
      </ul>

      <div className="mt-auto">
        <div className="relative border border-white/10 bg-black p-3 font-mono text-[12px] text-zinc-300 whitespace-pre overflow-x-auto">
          <pre className="pr-8">{c.install}</pre>
          <button
            onClick={doCopy}
            data-testid={`copy-${c.name}-install`}
            aria-label="copy install command"
            className="absolute top-2 right-2 text-zinc-500 hover:text-amber-400 transition-colors"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Downloads() {
  return (
    <section
      id="downloads"
      data-testid="downloads-section"
      className="border-b border-white/10"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-16 md:py-24">
        <div className="mb-10 md:mb-14 flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="text-[11px] font-mono text-amber-400 tracking-[0.2em] mb-2">// 04 DOWNLOADS</div>
            <h2
              style={{ fontFamily: "Cabinet Grotesk, sans-serif" }}
              className="text-3xl md:text-5xl font-bold tracking-tight"
            >
              Three ways to arm your clipboard.
            </h2>
            <p className="mt-3 text-zinc-400 max-w-2xl">
              Pick whichever fits your workflow. They all use the exact same pattern library
              — so behaviour is identical across the terminal, the desktop app, and the browser.
            </p>
          </div>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            data-testid="downloads-github-cta"
            className="inline-flex items-center gap-2 text-sm font-mono text-zinc-300 border border-white/20 hover:border-white/50 hover:bg-white/5 px-4 py-2.5 transition-colors"
          >
            <Github size={14} /> git clone / fork
          </a>
        </div>
        <div className="grid md:grid-cols-3 gap-[1px] bg-white/10 border border-white/10">
          {CARDS.map((c) => (
            <Card key={c.name} c={c} />
          ))}
        </div>
        <div className="mt-8 flex items-center gap-3 text-xs font-mono text-zinc-500">
          <Download size={12} className="text-amber-400" />
          <span>MIT licensed · zero telemetry in any component · patterns library shared across all three</span>
        </div>
      </div>
    </section>
  );
}
