import React, { useEffect, useState, useRef } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function useAnimatedNumber(target) {
  const [v, setV] = useState(0);
  const raf = useRef(null);
  useEffect(() => {
    const start = performance.now();
    const from = v;
    const to = target;
    const dur = 900;
    const tick = (t) => {
      const p = Math.min(1, (t - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      setV(Math.round(from + (to - from) * eased));
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => raf.current && cancelAnimationFrame(raf.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);
  return v;
}

function Cell({ label, value, suffix = "", testId }) {
  const n = useAnimatedNumber(value || 0);
  return (
    <div className="bg-[#0A0A0A] p-6 md:p-8" data-testid={testId}>
      <div className="text-[10px] font-mono tracking-[0.18em] text-zinc-500">{label}</div>
      <div
        style={{ fontFamily: "JetBrains Mono, monospace" }}
        className="mt-3 text-4xl md:text-6xl font-bold tracking-tight text-white tabular-nums"
      >
        {n.toLocaleString()}
        {suffix && <span className="text-amber-400 ml-1">{suffix}</span>}
      </div>
    </div>
  );
}

export default function StatsPanel() {
  const [stats, setStats] = useState({
    total_events: 0,
    total_secrets: 0,
    total_chars_scrubbed: 0,
    patterns_active: 18,
    events_last_24h: 0,
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const { data } = await axios.get(`${BACKEND_URL}/api/stats`);
        setStats(data);
      } catch (e) {
        // keep defaults — no user-facing error, but surface for devs
        // eslint-disable-next-line no-console
        console.debug("[vp] /api/stats fetch failed, using defaults:", e);
      }
    };
    fetchStats();
    const iv = setInterval(fetchStats, 4000);
    return () => clearInterval(iv);
  }, []);

  return (
    <section
      id="stats"
      data-testid="stats-panel"
      className="border-b border-white/10"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-16 md:py-24">
        <div className="mb-10 md:mb-14">
          <div className="text-[11px] font-mono text-amber-400 tracking-[0.2em] mb-2">// 03 LIVE STATS</div>
          <h2
            style={{ fontFamily: "Cabinet Grotesk, sans-serif" }}
            className="text-3xl md:text-5xl font-bold tracking-tight"
          >
            Secrets intercepted so far.
          </h2>
          <p className="mt-3 text-zinc-400 max-w-2xl">
            Updates every 4 seconds from the playground + any opted-in CLI/desktop/extension
            instances. No text, no IPs, no identifiers — just counts.
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-[1px] bg-white/10 border border-white/10">
          <Cell label="TOTAL EVENTS" value={stats.total_events} testId="stat-total-events" />
          <Cell label="SECRETS CAUGHT" value={stats.total_secrets} testId="stat-total-secrets" />
          <Cell label="CHARS SCRUBBED" value={stats.total_chars_scrubbed} testId="stat-total-chars" />
          <Cell label="PATTERNS ACTIVE" value={stats.patterns_active} testId="stat-patterns-active" />
        </div>
        <div className="mt-[1px] grid grid-cols-1 bg-white/10 border border-white/10 border-t-0">
          <div className="bg-[#0A0A0A] p-6 flex flex-wrap items-center gap-6" data-testid="stat-footer-row">
            <div>
              <div className="text-[10px] font-mono tracking-[0.18em] text-zinc-500">LAST 24H</div>
              <div className="font-mono text-2xl text-amber-400 mt-1">
                {stats.events_last_24h.toLocaleString()} events
              </div>
            </div>
            <div className="flex-1 h-px bg-white/10 min-w-[60px]" />
            <div className="text-xs font-mono text-zinc-500">
              everything below this line is aggregated · nothing identifiable is stored
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
