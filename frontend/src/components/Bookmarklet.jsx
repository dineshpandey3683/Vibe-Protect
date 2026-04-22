import React, { useEffect, useMemo, useRef, useState } from "react";
import { Bookmark, MousePointer2, ArrowDown, Check, Copy } from "lucide-react";

/**
 * The bookmarklet source. Kept small on purpose — browsers truncate
 * `href="javascript:..."` at ~2 KB in some chromium builds.
 *
 * Flow:
 *   1. read clipboard text (requires user click — which is exactly what
 *      dragging a bookmarklet produces, so we're fine)
 *   2. base64url-encode as the `clip` fragment param
 *   3. open the landing page's Playground tab with the payload in the
 *      URL fragment — the fragment never leaves the browser, so the
 *      secret text is never transmitted to any server
 */
function buildBookmarklet(origin) {
  // Written as a tiny self-contained IIFE — no external deps, no eval.
  // The hard cap (8000) deliberately matches CLIP_MAX_CHARS in shareLink.js
  // so the truncation story is the same wherever it shows up. If we exceed
  // it we still hand off the truncated text AND a small warning flag so
  // the Playground can show the user "scrubbed first 8K; use the web app
  // for full text" instead of silently losing input.
  // eslint-disable-next-line no-template-curly-in-string
  const src = `(function(){
    var O='${origin}';
    var CAP=8000;
    function enc(s){
      var b=new TextEncoder().encode(s),x='';
      for(var i=0;i<b.length;i++)x+=String.fromCharCode(b[i]);
      return btoa(x).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'');
    }
    function go(t){
      t=t||'';
      var truncated=t.length>CAP;
      var c=t.slice(0,CAP);
      var p=enc(JSON.stringify({v:1,c:c,trunc:truncated,orig:t.length}));
      window.open(O+'/#playground&clip='+p,'_blank');
    }
    if(navigator.clipboard&&navigator.clipboard.readText){
      navigator.clipboard.readText().then(go).catch(function(){
        var t=prompt('Vibe Protect couldn\\'t read your clipboard directly.\\nPaste below to scan:');
        if(t!=null)go(t);
      });
    }else{
      var t=prompt('Paste the text you want to scan:');
      if(t!=null)go(t);
    }
  })();`;
  // Collapse whitespace so the href stays compact.
  return "javascript:" + encodeURIComponent(src.replace(/\s+/g, " ").trim());
}

export default function Bookmarklet() {
  const origin =
    typeof window !== "undefined" ? window.location.origin : "https://vibe.protect";

  const href = useMemo(() => buildBookmarklet(origin), [origin]);
  const [copied, setCopied] = useState(false);
  const linkRef = useRef(null);

  // React 16.9+ refuses to render `javascript:` hrefs (it swaps them for
  // an error-throwing snippet). Bookmarklets *must* use that scheme to be
  // draggable/accepted by the browser, so we set the attribute imperatively
  // after mount. This is deliberate and safe here — the URL is built from
  // a known, vetted string literal, not user input.
  useEffect(() => {
    if (linkRef.current) {
      linkRef.current.setAttribute("href", href);
    }
  }, [href]);

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(href);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch (e) {
      // clipboard API blocked; user can still drag the button
      // eslint-disable-next-line no-console
      console.debug("[vp] bookmarklet copy failed:", e);
    }
  };

  return (
    <section
      id="bookmarklet"
      data-testid="bookmarklet-section"
      className="relative border-b border-white/10"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-16 md:py-24">
        <div className="grid md:grid-cols-[1.2fr_1fr] gap-10 md:gap-16 items-start">
          {/* left — pitch + drag target */}
          <div>
            <div className="text-[11px] font-mono text-amber-400 tracking-[0.2em] mb-2">
              // 00 ONE-CLICK · NO INSTALL
            </div>
            <h2
              style={{ fontFamily: "Cabinet Grotesk, sans-serif" }}
              className="text-3xl md:text-5xl font-bold tracking-tight"
            >
              Try it in 3 seconds.
              <br />
              No extension, no CLI.
            </h2>
            <p className="mt-4 text-zinc-400 max-w-xl">
              Drag the button below to your bookmarks bar. Click it on any page —
              whatever you last copied gets scanned in the Playground, and you
              get a <span className="text-amber-400">shareable receipt</span> you
              can post publicly (no plaintext, just counts).
            </p>

            {/* The drag target — also clickable as a same-tab fallback */}
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <a
                ref={linkRef}
                href="#"
                draggable="true"
                onClick={(e) => e.preventDefault()}
                data-testid="bookmarklet-drag-link"
                className="group inline-flex items-center gap-2 bg-amber-400 text-black font-mono font-bold text-sm px-5 py-3 border-2 border-amber-400 cursor-grab active:cursor-grabbing hover:bg-amber-300 transition-colors select-none"
                title="Drag me to your bookmarks bar"
              >
                <Bookmark size={16} />
                Scan my clipboard
              </a>
              <span className="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-500">
                <MousePointer2 size={12} /> drag me up there
                <ArrowDown size={12} className="rotate-180" />
              </span>
            </div>

            {/* How-it-works strip */}
            <ol className="mt-10 grid gap-4 text-sm text-zinc-400 font-mono">
              <li className="flex gap-4">
                <span className="text-amber-400 font-bold tabular-nums">01</span>
                <span>Drag the button into your browser's bookmarks bar.</span>
              </li>
              <li className="flex gap-4">
                <span className="text-amber-400 font-bold tabular-nums">02</span>
                <span>
                  On any page, copy something sensitive — an API key, a&nbsp;
                  <span className="text-zinc-300">.env</span> blob, a DB URL.
                </span>
              </li>
              <li className="flex gap-4">
                <span className="text-amber-400 font-bold tabular-nums">03</span>
                <span>
                  Click the bookmarklet. A Vibe Protect tab opens with your text
                  already scrubbed and a shareable receipt URL ready to copy.
                </span>
              </li>
            </ol>
          </div>

          {/* right — "copy code" panel for users who can't drag (mobile) */}
          <div className="bg-[#0A0A0A] border border-white/10">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-2 font-mono text-[10px] text-zinc-500 tracking-widest">
              <span>BOOKMARKLET SOURCE</span>
              <button
                onClick={copyCode}
                data-testid="bookmarklet-copy-btn"
                className="inline-flex items-center gap-1 text-zinc-400 hover:text-amber-400"
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
                {copied ? "copied" : "copy"}
              </button>
            </div>
            <pre
              data-testid="bookmarklet-source"
              className="p-4 text-[11px] leading-relaxed font-mono text-zinc-400 whitespace-pre-wrap break-all max-h-[360px] overflow-auto"
            >
              {href}
            </pre>
            <div className="border-t border-white/10 px-4 py-3 text-[11px] font-mono text-zinc-500">
              On mobile? Create a bookmark to any page, edit it, and replace the
              URL with this. Same result.
            </div>
          </div>
        </div>

        {/* privacy note strip */}
        <div
          className="mt-12 border border-amber-400/20 bg-amber-400/5 text-[12px] font-mono text-amber-200 px-4 py-3 flex flex-wrap items-center gap-2"
          data-testid="bookmarklet-privacy-note"
        >
          <span className="text-amber-400">privacy:</span>
          your clipboard text rides in the URL <span className="text-zinc-400">fragment</span>
          (<span className="text-zinc-400">#clip=…</span>). Fragments are never sent to
          any server — including ours. Redaction happens entirely in your browser.
        </div>
      </div>
    </section>
  );
}
