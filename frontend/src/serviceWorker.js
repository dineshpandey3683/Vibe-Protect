// src/serviceWorker.js
//
// Companion to ``public/service-worker.js`` (the worker itself must live
// in /public so CRA serves it at the root origin, which is the ONLY place
// a service worker can claim scope "/").
//
// This file holds:
//   • the single ``urlsToCache`` list that the public worker precaches
//     (duplicated here so it can be asserted in tests and surfaced in docs
//     without having to parse the raw worker script)
//   • ``register()`` — called from ``index.js``, production-only. We
//     centralise the registration here so the index file stays tiny.

export const CACHE_NAME = "vibe-protect-v1.0.0";

// NOTE — keep in lock-step with PRECACHE_URLS in public/service-worker.js.
// A sync test in ``shareLink.test.js`` would be one way to enforce this;
// for now they're both short lists and reviewed together.
export const urlsToCache = [
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

/**
 * Register the service worker on page load. Production only — during
 * ``yarn start`` the webpack dev server and the SW's aggressive caching
 * would fight over HMR.
 */
export function register() {
  if (typeof window === "undefined") return;
  if (!("serviceWorker" in navigator)) return;
  if (process.env.NODE_ENV !== "production") return;

  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/service-worker.js")
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.warn("[vibe-protect] SW registration failed:", err);
      });
  });
}

export function unregister() {
  if (typeof window === "undefined") return;
  if (!("serviceWorker" in navigator)) return;
  navigator.serviceWorker.getRegistrations().then((regs) => {
    regs.forEach((r) => r.unregister());
  });
}
