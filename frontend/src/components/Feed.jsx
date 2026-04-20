import React, { useEffect, useState } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function formatRelative(iso) {
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return `${Math.max(1, Math.floor(diff))}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function sourceBadge(s) {
  const map = {
    web: "bg-amber-400/10 text-amber-400 border-amber-400/40",
    cli: "bg-emerald-400/10 text-emerald-400 border-emerald-400/40",
    desktop: "bg-sky-400/10 text-sky-400 border-sky-400/40",
    extension: "bg-fuchsia-400/10 text-fuchsia-400 border-fuchsia-400/40",
    other: "bg-zinc-400/10 text-zinc-400 border-zinc-400/40",
  };
  return map[s] || map.other;
}

export default function Feed() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await axios.get(`${BACKEND_URL}/api/feed?limit=30`);
        setItems(data || []);
      } catch {
        setItems([]);
      }
    };
    load();
    const iv = setInterval(load, 3000);
    return () => clearInterval(iv);
  }, []);

  const ticker = items.length > 0 ? items : [
    { id: "x1", source: "web", patterns: ["openai_api_key"], chars_saved: 48, ts: new Date().toISOString() },
    { id: "x2", source: "cli", patterns: ["aws_access_key"], chars_saved: 20, ts: new Date().toISOString() },
    { id: "x3", source: "extension", patterns: ["github_token"], chars_saved: 40, ts: new Date().toISOString() },
    { id: "x4", source: "desktop", patterns: ["jwt_token"], chars_saved: 180, ts: new Date().toISOString() },
  ];
  const loop = [...ticker, ...ticker];

  return (
    <section
      id="feed"
      data-testid="live-feed-ticker"
      className="border-b border-white/10"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-16 md:py-20">
        <div className="mb-8 flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="text-[11px] font-mono text-amber-400 tracking-[0.2em] mb-2">// 05 LIVE FEED</div>
            <h2
              style={{ fontFamily: "Cabinet Grotesk, sans-serif" }}
              className="text-3xl md:text-5xl font-bold tracking-tight"
            >
              Redactions happening right now.
            </h2>
            <p className="mt-3 text-zinc-400 max-w-2xl">
              Anonymised ticker of the most recent events across every Vibe Protect instance.
              Pattern type only — never the secret itself.
            </p>
          </div>
        </div>

        <div className="relative border border-white/10 bg-black overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-8 border-b border-white/10 bg-[#0A0A0A] flex items-center px-3 font-mono text-[10px] text-zinc-500 tracking-widest z-10 justify-between">
            <span>▍ /api/feed · tail -f</span>
            <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" /> LIVE</span>
          </div>
          <div className="pt-8 py-4 vp-marquee">
            <div className="vp-marquee-track">
              {loop.map((it, idx) => (
                <div
                  key={`${it.id}-${idx}`}
                  className="flex items-center gap-3 font-mono text-[13px] text-zinc-400"
                >
                  <span className="text-zinc-600">[{formatRelative(it.ts)}]</span>
                  <span className={`border px-1.5 py-0.5 text-[10px] uppercase ${sourceBadge(it.source)}`}>
                    {it.source}
                  </span>
                  <span className="text-amber-400">● redacted</span>
                  {(it.patterns || []).slice(0, 3).map((p, i) => (
                    <span key={`${it.id}-${idx}-${p}-${i}`} className="text-white">{p}</span>
                  ))}
                  <span className="text-zinc-500">· {it.chars_saved} chars scrubbed</span>
                  <span className="text-zinc-700">|</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* recent list (static view of same data) */}
        <div className="mt-6 grid md:grid-cols-2 gap-[1px] bg-white/10 border border-white/10">
          {items.slice(0, 8).map((it) => (
            <div key={it.id} className="bg-[#0A0A0A] p-4 flex items-center justify-between gap-4" data-testid={`feed-row-${it.id}`}>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`border px-1.5 py-0.5 text-[10px] font-mono uppercase ${sourceBadge(it.source)}`}>
                    {it.source}
                  </span>
                  <span className="text-zinc-500 font-mono text-[11px]">
                    {formatRelative(it.ts)}
                  </span>
                </div>
                <div className="mt-1.5 font-mono text-sm text-zinc-200 truncate">
                  {(it.patterns || []).join(", ") || "(no patterns)"}
                </div>
              </div>
              <div className="font-mono text-amber-400 text-sm whitespace-nowrap">
                −{it.chars_saved}
              </div>
            </div>
          ))}
          {items.length === 0 && (
            <div className="bg-[#0A0A0A] p-6 text-sm text-zinc-500 md:col-span-2">
              No live events yet. Try the <a href="#playground" className="text-amber-400 hover:underline">playground</a> above.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
