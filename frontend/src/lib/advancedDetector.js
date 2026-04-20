// Vibe Protect — AdvancedSecretDetector (JS mirror of cli/advanced_detector.py).
// Adds Shannon-entropy filtering, context filtering, and an entropy catch-all
// on top of the base pattern library.
//
// Per-pattern filtering is critical: low-entropy patterns (email, IPv4,
// credit_card, shell_prompt, DB URL, SSH/PEM blocks) must always match,
// otherwise real secrets slip through.

import { PATTERNS } from "@/lib/patterns";

const ENTROPY_CHECKED = new Set([
  "anthropic_api_key",
  "openai_api_key",
  "aws_access_key",
  "aws_secret_key",
  "github_token",
  "stripe_key",
  "google_api_key",
  "slack_token",
  "jwt_token",
  "long_base64_blob",
]);
const CONTEXT_CHECKED = new Set([...ENTROPY_CHECKED, "generic_secret_assignment"]);
const CONTEXT_WORDS = ["example", "sample", "demo", "placeholder", "dummy", "fake"];

const ENTROPY_THRESHOLD = 3.5;
const MIN_LEN = 16;
const MAX_LEN = 512;
const CATCHALL_MIN_LEN = 24;
const CATCHALL_ENTROPY = 4.2;

export function shannonEntropy(s) {
  if (!s) return 0;
  const counts = {};
  for (const c of s) counts[c] = (counts[c] || 0) + 1;
  let e = 0;
  for (const k in counts) {
    const p = counts[k] / s.length;
    e -= p * Math.log2(p);
  }
  return e;
}

function passesContext(text, start) {
  const lineStart = text.lastIndexOf("\n", start - 1) + 1;
  let lineEnd = text.indexOf("\n", start);
  if (lineEnd === -1) lineEnd = text.length;
  const line = text.slice(lineStart, lineEnd).toLowerCase();
  return !CONTEXT_WORDS.some((w) => line.includes(w));
}

function passesEntropy(s) {
  if (s.length < MIN_LEN || s.length > MAX_LEN) return true;
  return shannonEntropy(s) >= ENTROPY_THRESHOLD;
}

function scanPatterns(text) {
  const out = [];
  for (const p of PATTERNS) {
    // fresh regex per pass
    const rx = new RegExp(p.regex.source, p.regex.flags);
    let m;
    while ((m = rx.exec(text)) !== null) {
      const original = m[0];
      const needsEnt = ENTROPY_CHECKED.has(p.name);
      const needsCtx = CONTEXT_CHECKED.has(p.name);
      const ent = needsEnt ? shannonEntropy(original) : 0;
      if (needsEnt && !passesEntropy(original)) continue;
      if (needsCtx && !passesContext(text, m.index)) continue;
      out.push({
        pattern: p.name,
        label: p.label,
        start: m.index,
        end: m.index + original.length,
        original,
        entropy: ent,
        reason: "pattern",
      });
      if (original.length === 0) rx.lastIndex += 1;
    }
  }
  return out;
}

function scanCatchall(text, existing) {
  const taken = existing.map((m) => [m.start, m.end]);
  const overlaps = (a, b) => taken.some(([s, e]) => a < e && b > s);
  const rx = new RegExp(`[A-Za-z0-9_\\-]{${CATCHALL_MIN_LEN},}`, "g");
  const out = [];
  let m;
  while ((m = rx.exec(text)) !== null) {
    if (overlaps(m.index, m.index + m[0].length)) continue;
    const ent = shannonEntropy(m[0]);
    if (ent < CATCHALL_ENTROPY) continue;
    if (!passesContext(text, m.index)) continue;
    out.push({
      pattern: "high_entropy_string",
      label: "High-entropy Blob",
      start: m.index,
      end: m.index + m[0].length,
      original: m[0],
      entropy: ent,
      reason: "entropy_catchall",
    });
  }
  return out;
}

export function redactAdvanced(text) {
  if (!text) return { cleaned: text || "", matches: [] };
  const all = [...scanPatterns(text), ...scanCatchall(text, scanPatterns(text))];
  all.sort((a, b) => a.start - b.start || b.end - a.end);
  const chosen = [];
  let lastEnd = -1;
  for (const m of all) {
    if (m.start >= lastEnd) {
      chosen.push(m);
      lastEnd = m.end;
    }
  }
  let cleaned = "";
  let cursor = 0;
  for (const m of chosen) {
    cleaned += text.slice(cursor, m.start);
    m.mask = `[${m.pattern.toUpperCase()}]`;
    cleaned += m.mask;
    cursor = m.end;
  }
  cleaned += text.slice(cursor);
  return { cleaned, matches: chosen };
}
