import React from "react";
import { Github, Shield } from "lucide-react";

export default function Footer() {
  return (
    <footer
      data-testid="footer"
      className="bg-[#0A0A0A] border-t border-white/10"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-14 grid md:grid-cols-12 gap-10">
        <div className="md:col-span-5">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-6 h-6 bg-amber-400 text-black">
              <Shield size={14} strokeWidth={2.5} />
            </span>
            <span className="font-bold tracking-tight">
              vibe<span className="text-amber-400">.</span>protect
            </span>
          </div>
          <p className="mt-4 text-sm text-zinc-400 max-w-sm leading-relaxed">
            A clipboard guardian for developers in the AI era. Open source, MIT licensed,
            zero telemetry, runs entirely on your machine.
          </p>
          <a
            href="https://github.com/dineshpandey3683/Vibe-Protect"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-5 inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white border border-white/10 hover:border-white/30 px-3 py-1.5 transition-colors"
            data-testid="footer-github-link"
          >
            <Github size={14} /> github.com/dineshpandey3683/Vibe-Protect
          </a>
        </div>
        <div className="md:col-span-2">
          <div className="text-[10px] font-mono tracking-widest text-zinc-500 mb-3">PRODUCT</div>
          <ul className="space-y-2 text-sm text-zinc-300">
            <li><a href="#playground" className="hover:text-amber-400">Playground</a></li>
            <li><a href="#patterns" className="hover:text-amber-400">Patterns</a></li>
            <li><a href="#downloads" className="hover:text-amber-400">Downloads</a></li>
            <li><a href="#stats" className="hover:text-amber-400">Stats</a></li>
          </ul>
        </div>
        <div className="md:col-span-2">
          <div className="text-[10px] font-mono tracking-widest text-zinc-500 mb-3">CLIENTS</div>
          <ul className="space-y-2 text-sm text-zinc-300">
            <li>CLI</li>
            <li>Desktop GUI</li>
            <li>Browser Extension</li>
          </ul>
        </div>
        <div className="md:col-span-3">
          <div className="text-[10px] font-mono tracking-widest text-zinc-500 mb-3">LEGAL</div>
          <ul className="space-y-2 text-sm text-zinc-300">
            <li>MIT License</li>
            <li>No telemetry</li>
            <li>Local-first</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10">
        <div className="max-w-7xl mx-auto px-6 md:px-10 py-5 flex flex-wrap items-center justify-between gap-3 font-mono text-[11px] text-zinc-500">
          <span>© {new Date().getFullYear()} vibe.protect · built for developers who paste too fast</span>
          <span>clipboard guardian · v1.0 · armed &amp; watching</span>
        </div>
      </div>
    </footer>
  );
}
