/*
 * Vibe Protect — service worker
 *
 * Goals (in order):
 *   1. Never break the app if the SW itself is broken — every handler
 *      is defensive and falls back to the network.
 *   2. Never cache API responses. /api/* must always hit the live
 *      backend, or `/api/redact` would start returning stale scrubs.
 *   3. Cache the shell (HTML + hashed JS/CSS chunks + icons + og/stats
 *      JSON) on first visit so the landing page renders instantly on
 *      every subsequent load, and works offline.
 *   4. Clean up old caches on activate so shipping a new build doesn't
 *      leave stale assets forever.
 *
 * We deliberately use a "stale-while-revalidate" strategy for the shell
 * and a **network-only** strategy for /api/*. Anything else uses
 * cache-first-then-network.
 */

const VERSION = "v1.0.0";
const STATIC_CACHE = `vibe-protect-static-${VERSION}`;
const RUNTIME_CACHE = `vibe-protect-runtime-${VERSION}`;

// Just the absolutely-stable files we know exist by name. Hashed CRA
// chunks are added to the runtime cache lazily on first fetch — trying
// to enumerate them at install time would force us to guess the hashes.
const PRECACHE_URLS = [
  "/",
  "/index.html",
  "/manifest.json",
  "/og-image.png",
  "/stats.json",
  "/stats-history.jsonl",
  "/icon-16.png",
  "/icon-32.png",
  "/icon-128.png",
  "/icon-192.png",
  "/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) =>
      // addAll is atomic — if any URL 404s, install fails. Use Promise.all
      // on individual puts so a single missing asset doesn't brick SW boot.
      Promise.all(
        PRECACHE_URLS.map((url) =>
          fetch(url, { cache: "no-cache" })
            .then((resp) => (resp && resp.ok ? cache.put(url, resp) : null))
            .catch(() => null)
        )
      )
    )
  );
  // New SW takes over the next page load without requiring a second refresh.
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== STATIC_CACHE && k !== RUNTIME_CACHE)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  // Service workers only handle GET; let the browser do the rest.
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // 1) Never cache the API. A stale /api/redact would be a correctness
  //    bug (caller gets yesterday's scrub for today's input).
  if (url.pathname.startsWith("/api/")) return;

  // 2) Don't touch third-party origins (fonts, analytics, Emergent JS).
  if (url.origin !== self.location.origin) return;

  // 3) For the navigation request ("/" or any hash route) use
  //    network-first so returning users see fresh builds immediately,
  //    with cache fallback for offline.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((resp) => {
          const copy = resp.clone();
          caches.open(STATIC_CACHE).then((c) => c.put("/index.html", copy));
          return resp;
        })
        .catch(() => caches.match("/index.html"))
    );
    return;
  }

  // 4) Everything else (hashed JS/CSS/images) is cache-first with a
  //    background revalidate so subsequent visits are instant.
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request)
        .then((networkResp) => {
          if (networkResp && networkResp.status === 200) {
            const copy = networkResp.clone();
            caches
              .open(RUNTIME_CACHE)
              .then((c) => c.put(request, copy))
              .catch(() => {});
          }
          return networkResp;
        })
        .catch(() => cached); // offline and no cache: let it fail
      return cached || fetchPromise;
    })
  );
});
