import React, { useState, useEffect } from "react";
import axios from "axios";
import { Shield, Github, Download, ArrowUpRight } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [versionInfo, setVersionInfo] = useState(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await axios.get(`${BACKEND_URL}/api/version`);
        setVersionInfo(data);
      } catch {
        /* silently ignore */
      }
    };
    load();
    const iv = setInterval(load, 60 * 60 * 1000); // hourly
    return () => clearInterval(iv);
  }, []);

  const current = versionInfo?.current || "1.0";
  const hasUpdate = !!versionInfo?.is_update_available;

  return (
    <header
      data-testid="main-navigation"
      className={`sticky top-0 z-50 transition-colors ${
        scrolled ? "bg-[#0A0A0A]/95 backdrop-blur" : "bg-[#0A0A0A]"
      } border-b border-white/10`}
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10 h-14 flex items-center justify-between">
        <a href="#top" className="flex items-center gap-2 group" data-testid="nav-brand">
          <span className="relative inline-flex items-center justify-center w-6 h-6 bg-amber-400 text-black">
            <Shield size={14} strokeWidth={2.5} />
          </span>
          <span className="font-bold tracking-tight text-[15px]">
            vibe<span className="text-amber-400">.</span>protect
          </span>
          <span
            data-testid="nav-version-badge"
            className={`hidden sm:inline text-[10px] font-mono ml-2 px-1.5 py-0.5 border ${
              hasUpdate
                ? "text-black bg-amber-400 border-amber-400"
                : "text-zinc-500 border-white/10"
            }`}
          >
            v{current}
          </span>
          {hasUpdate && (
            <a
              href={versionInfo.release_url || "#"}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="nav-update-cta"
              className="hidden md:inline-flex items-center gap-1 text-[10px] font-mono text-amber-400 hover:text-amber-300 ml-1"
              title={`Update available: ${versionInfo.latest}`}
            >
              ▲ {versionInfo.latest} <ArrowUpRight size={10} />
            </a>
          )}
        </a>
        <nav className="hidden md:flex items-center gap-7 text-sm text-zinc-400 font-mono">
          <a href="#playground" className="hover:text-white transition-colors">playground</a>
          <a href="#patterns" className="hover:text-white transition-colors">patterns</a>
          <a href="#downloads" className="hover:text-white transition-colors">downloads</a>
          <a href="#stats" className="hover:text-white transition-colors">stats</a>
        </nav>
        <div className="flex items-center gap-2">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            data-testid="nav-github-link"
            className="hidden sm:inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white px-3 py-1.5 border border-white/10 hover:border-white/30 transition-colors"
          >
            <Github size={14} /> GitHub
          </a>
          <a
            href="#downloads"
            data-testid="nav-download-cta"
            className="inline-flex items-center gap-2 text-sm font-bold text-black bg-amber-400 hover:bg-amber-300 px-3 py-1.5 transition-colors"
          >
            <Download size={14} /> Download
          </a>
        </div>
      </div>
    </header>
  );
}
