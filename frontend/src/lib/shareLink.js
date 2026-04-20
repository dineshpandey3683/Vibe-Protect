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

/* ---------------------------------- clipboard bookmarklet codec
 *
 * The "Scan my clipboard" bookmarklet reads the user's clipboard on whatever
 * page they're on and opens our site with the text tucked into the URL
 * fragment. The fragment never leaves the browser, so the secret text is
 * never transmitted to any server — including ours.
 *
 * Shape:  #playground&clip=<base64url(UTF-8 JSON)>
 * Payload: { v:1, c: <clipboard-text> }
 */
const CLIP_VERSION = 1;
const CLIP_MAX_CHARS = 20_000; // ~15 KB base64 — safely inside every URL limit

// Unicode-safe base64url (the simple btoa() only handles Latin-1)
function utf8Btoa(s) {
  const bytes = new TextEncoder().encode(s);
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function utf8Atob(s) {
  let pad = s.replace(/-/g, "+").replace(/_/g, "/");
  while (pad.length % 4) pad += "=";
  const bin = atob(pad);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

export function encodeClip(text) {
  if (typeof text !== "string" || !text) return null;
  const trimmed = text.slice(0, CLIP_MAX_CHARS);
  return utf8Btoa(JSON.stringify({ v: CLIP_VERSION, c: trimmed }));
}

export function decodeClipFromHash(
  hash = typeof window !== "undefined" ? window.location.hash : ""
) {
  const m = /(?:^|[#&])clip=([A-Za-z0-9_-]+)/.exec(hash || "");
  if (!m) return null;
  try {
    const payload = JSON.parse(utf8Atob(m[1]));
    if (!payload || payload.v !== CLIP_VERSION || typeof payload.c !== "string") return null;
    return payload.c;
  } catch {
    return null;
  }
}

/* ---------------------------------- receipt codec
 *
 * A **receipt** is a redaction snapshot the user can share to prove
 * "X tool with Y secrets was scrubbed to Z chars." It encodes only
 * aggregate counts — never the plaintext — so receipts are safe to
 * post publicly.
 */
const RECEIPT_VERSION = 1;

export function encodeReceipt({ matches = [], charsBefore = 0, charsAfter = 0, advanced = false }) {
  const pp = {};
  for (const m of matches) {
    pp[m.pattern] = (pp[m.pattern] || 0) + 1;
  }
  const payload = {
    v: RECEIPT_VERSION,
    t: new Date().toISOString(),
    n: matches.length,
    cb: charsBefore,
    ca: charsAfter,
    a: !!advanced,
    pp,
  };
  return utf8Btoa(JSON.stringify(payload));
}

export function decodeReceiptFromHash(
  hash = typeof window !== "undefined" ? window.location.hash : ""
) {
  const m = /(?:^|[#&])receipt=([A-Za-z0-9_-]+)/.exec(hash || "");
  if (!m) return null;
  try {
    const p = JSON.parse(utf8Atob(m[1]));
    if (!p || p.v !== RECEIPT_VERSION) return null;
    return {
      generated_at: p.t,
      total_matches: p.n || 0,
      chars_before: p.cb || 0,
      chars_after: p.ca || 0,
      chars_saved: Math.max(0, (p.cb || 0) - (p.ca || 0)),
      advanced: !!p.a,
      per_pattern: p.pp || {},
    };
  } catch {
    return null;
  }
}

export function buildReceiptUrl(receiptPayload, baseUrl = window.location.href) {
  const enc = encodeReceipt(receiptPayload);
  if (!enc) return null;
  const url = new URL(baseUrl);
  url.hash = `playground&receipt=${enc}`;
  return url.toString();
}

// Exposed only for tests / debugging; not part of the shipped UI.
export const __test = {
  squash,
  expand,
  b64urlEncode,
  b64urlDecode,
  VERSION,
  CLIP_VERSION,
  RECEIPT_VERSION,
  CLIP_MAX_CHARS,
  utf8Btoa,
  utf8Atob,
};
