/**
 * Share-link codec for Receipts evidence.
 *
 * Encodes a compact projection of stats.json into a URL-safe base64 string
 * that lives in the URL fragment (``#evidence=…``). Fragments are never
 * sent to any server, so the snapshot stays local to the forwarded link —
 * no hosting, no account, no tracking.
 *
 * Payload schema (intentionally minimal — we only include fields the
 * Receipts panel actually renders):
 *
 *     v: 1                                 // schema version — bump on break
 *     t: "2026-02-20T10:00:00+00:00"       // generated_at
 *     ver: "1.0.0"                         // version
 *     dr: 1.0                              // detection_rate
 *     fpr: 0.0                             // false_positive_rate
 *     sst: 540                             // synthetic_secrets_tested
 *     fpt: 158                             // false_positives_tested
 *     pa: 18                               // patterns_active
 *     ml: true                             // ml_entropy_enabled
 *     pp: { name: [hit, total] }           // per-pattern (array-packed)
 *
 * Average encoded size: ~700 bytes — well inside every browser's URL
 * length limit, email client truncation threshold, and Slack link preview.
 */

const VERSION = 1;

/* ---------------------------------- base64url (RFC 4648 §5) */
function b64urlEncode(str) {
  // btoa handles Latin-1; JSON is already ASCII so we're fine.
  const std = btoa(str);
  return std.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function b64urlDecode(s) {
  // re-pad to multiple of 4
  let pad = s.replace(/-/g, "+").replace(/_/g, "/");
  while (pad.length % 4) pad += "=";
  return atob(pad);
}

/* ---------------------------------- schema squash / expand */
function squash(stats) {
  const pp = {};
  for (const [name, v] of Object.entries(stats.per_pattern || {})) {
    pp[name] = [v.hit ?? 0, v.total ?? 0];
  }
  return {
    v: VERSION,
    t: stats.generated_at,
    ver: stats.version,
    dr: stats.detection_rate,
    fpr: stats.false_positive_rate,
    sst: stats.synthetic_secrets_tested,
    fpt: stats.false_positives_tested,
    pa: stats.patterns_active,
    ml: !!stats.ml_entropy_enabled,
    pp,
  };
}

function expand(payload) {
  if (!payload || payload.v !== VERSION) return null;
  const per_pattern = {};
  for (const [name, pair] of Object.entries(payload.pp || {})) {
    const [hit, total] = Array.isArray(pair) ? pair : [0, 0];
    per_pattern[name] = { hit, total };
  }
  return {
    generated_at: payload.t,
    version: payload.ver,
    detection_rate: payload.dr,
    false_positive_rate: payload.fpr,
    synthetic_secrets_tested: payload.sst,
    false_positives_tested: payload.fpt,
    patterns_active: payload.pa,
    ml_entropy_enabled: !!payload.ml,
    per_pattern,
  };
}

/* ---------------------------------- public API */
export function encodeSnapshot(stats) {
  if (!stats) return null;
  const json = JSON.stringify(squash(stats));
  return b64urlEncode(json);
}

export function decodeFromHash(hash = (typeof window !== "undefined" ? window.location.hash : "")) {
  const m = /(?:^|[#&])evidence=([A-Za-z0-9_-]+)/.exec(hash || "");
  if (!m) return null;
  try {
    const json = b64urlDecode(m[1]);
    return expand(JSON.parse(json));
  } catch {
    return null;
  }
}

export function buildShareUrl(stats, baseUrl = window.location.href) {
  const enc = encodeSnapshot(stats);
  if (!enc) return null;
  const url = new URL(baseUrl);
  url.hash = `receipts&evidence=${enc}`;
  return url.toString();
}

// Exposed only for tests / debugging; not part of the shipped UI.
export const __test = { squash, expand, b64urlEncode, b64urlDecode, VERSION };
