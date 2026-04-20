/**
 * Jest tests for the bookmarklet / receipt codecs in ``shareLink.js``.
 *
 * Run via ``yarn test src/lib/shareLink.test.js`` (CRA / craco default Jest).
 *
 * The codecs live entirely on the front-end — no server involvement —
 * and encode/decode three kinds of payloads shared via URL fragments:
 *
 *   #receipts&evidence=<b64>   existing evidence-snapshot panel
 *   #playground&clip=<b64>     bookmarklet clipboard handoff
 *   #playground&receipt=<b64>  share-a-redaction receipt
 */
import {
  encodeSnapshot,
  decodeFromHash,
  buildShareUrl,
  encodeClip,
  decodeClipFromHash,
  encodeReceipt,
  decodeReceiptFromHash,
  buildReceiptUrl,
  __test,
} from "./shareLink";

// jsdom supplies window but not TextEncoder in every node version.
if (typeof global.TextEncoder === "undefined") {
  /* eslint-disable global-require */
  global.TextEncoder = require("util").TextEncoder;
  global.TextDecoder = require("util").TextDecoder;
}

/* ---------------------------------- evidence-snapshot codec (regression) */
describe("evidence snapshot codec", () => {
  const stats = {
    generated_at: "2026-02-20T10:00:00+00:00",
    version: "1.0.0",
    detection_rate: 1.0,
    false_positive_rate: 0.0,
    synthetic_secrets_tested: 540,
    false_positives_tested: 158,
    patterns_active: 18,
    ml_entropy_enabled: true,
    per_pattern: {
      openai_api_key: { hit: 10, total: 10 },
      email: { hit: 5, total: 5 },
    },
  };

  test("roundtrip preserves structure", () => {
    const enc = encodeSnapshot(stats);
    const decoded = decodeFromHash("#receipts&evidence=" + enc);
    expect(decoded.detection_rate).toBe(1.0);
    expect(decoded.per_pattern.openai_api_key).toEqual({ hit: 10, total: 10 });
  });

  test("buildShareUrl produces #receipts&evidence=<b64>", () => {
    const url = buildShareUrl(stats, "https://vibe.protect/");
    expect(url).toContain("#receipts&evidence=");
  });
});

/* ---------------------------------- clip codec (bookmarklet handoff) */
describe("clip codec", () => {
  test("roundtrip preserves text exactly", () => {
    const secret = "API_KEY=sk-abcdef0123456789 and email hi@world.com";
    const enc = encodeClip(secret);
    expect(decodeClipFromHash("#playground&clip=" + enc)).toBe(secret);
  });

  test("survives unicode (emoji, rtl, non-latin, control chars)", () => {
    const weird = "shy guy 🙈 العربية 漢字 \"quotes\" & <xml> \n\t";
    const enc = encodeClip(weird);
    expect(decodeClipFromHash("#playground&clip=" + enc)).toBe(weird);
  });

  test("hard-caps to CLIP_MAX_CHARS", () => {
    const huge = "a".repeat(__test.CLIP_MAX_CHARS + 1000);
    const enc = encodeClip(huge);
    expect(decodeClipFromHash("#playground&clip=" + enc).length).toBe(
      __test.CLIP_MAX_CHARS
    );
  });

  test("returns null on missing / malformed / wrong version", () => {
    expect(decodeClipFromHash("")).toBeNull();
    expect(decodeClipFromHash("#playground")).toBeNull();
    expect(decodeClipFromHash("#playground&clip=not_valid_$$$")).toBeNull();
    const wrong = __test.utf8Btoa(JSON.stringify({ v: 99, c: "x" }));
    expect(decodeClipFromHash("#playground&clip=" + wrong)).toBeNull();
  });

  test("output is base64url (no +, /, =)", () => {
    const enc = encodeClip("hello+/=+world");
    expect(enc).not.toMatch(/[+/=]/);
  });

  test("rejects empty / non-string input", () => {
    expect(encodeClip("")).toBeNull();
    expect(encodeClip(null)).toBeNull();
    expect(encodeClip(undefined)).toBeNull();
    expect(encodeClip(123)).toBeNull();
  });
});

/* ---------------------------------- receipt codec (privacy-critical) */
describe("receipt codec", () => {
  test("NEVER carries plaintext", () => {
    const secret = "sk-leaked-key-do-not-ship";
    const enc = encodeReceipt({
      matches: [
        { pattern: "openai_api_key", original: secret },
        { pattern: "email", original: "a@b.c" },
      ],
      charsBefore: 100,
      charsAfter: 40,
    });
    // The encoded blob itself must not contain the plaintext
    expect(enc).not.toContain(secret);
    // The decoded payload must not contain the plaintext anywhere
    const decoded = decodeReceiptFromHash("#playground&receipt=" + enc);
    expect(JSON.stringify(decoded)).not.toContain(secret);
    expect(decoded.total_matches).toBe(2);
    expect(decoded.chars_saved).toBe(60);
    expect(decoded.per_pattern).toEqual({ openai_api_key: 1, email: 1 });
  });

  test("returns null on wrong version", () => {
    const bad = __test.utf8Btoa(JSON.stringify({ v: 99, n: 1 }));
    expect(decodeReceiptFromHash("#playground&receipt=" + bad)).toBeNull();
  });

  test("buildReceiptUrl embeds receipt in fragment", () => {
    const url = buildReceiptUrl(
      { matches: [{ pattern: "email" }], charsBefore: 10, charsAfter: 3 },
      "https://vibe.protect/"
    );
    expect(url).toMatch(/^https:\/\/vibe\.protect\//);
    expect(url).toContain("#playground&receipt=");
  });

  test("handles zero-match case without crashing", () => {
    const enc = encodeReceipt({ matches: [], charsBefore: 0, charsAfter: 0 });
    const decoded = decodeReceiptFromHash("#playground&receipt=" + enc);
    expect(decoded.total_matches).toBe(0);
    expect(decoded.per_pattern).toEqual({});
  });
});
