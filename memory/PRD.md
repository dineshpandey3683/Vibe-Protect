# Vibe Protect — PRD

## Original problem statement

User shared `vibe_protect.py` — a Python clipboard monitor that auto-redacts
secrets (API keys, emails, IPs, shell prompts). User requested:
> "Do all and add it fit github repo so i can share it also, ty."

Meaning: build the full suite (CLI + Desktop GUI + Browser Extension + Web
Dashboard) and ship it as a shareable GitHub-ready repo.

## User personas

- **Developer using AI tools** — wants to paste error logs / code into
  ChatGPT/Claude without leaking `.env` secrets.
- **Security-conscious team lead** — wants a drop-in, zero-telemetry guardrail
  for every teammate's machine.
- **Open-source contributor / maintainer** — discovers the repo via a social
  post, wants to star/fork/share it.

## Core requirements (static)

1. **Single source of truth pattern library** shared across all four clients.
2. **Local-first**: CLI, desktop, extension make zero network calls.
3. **Web dashboard**: interactive playground + stats + downloads.
4. **MIT-licensed, GitHub-ready** with top-level README, LICENSE, .gitignore.
5. **Zero-telemetry** (web only stores counts, never plaintext).

## What's been implemented (2026-01)

### Shared pattern library (18 patterns)
OpenAI, Anthropic, AWS access/secret, GitHub, Stripe, Google/Firebase, Slack,
JWT, private key blocks, SSH public keys, DB connection URLs, email, IPv4,
credit card, shell prompts, generic `PASSWORD=`/`API_KEY=` assignments, long
base64 blobs.
- Python canonical: `/app/cli/patterns.py`
- JS mirror for web: `/app/frontend/src/lib/patterns.js`
- JS mirror for extension: `/app/extension/patterns.js`

### CLI (`/app/cli/`)
- Enhanced from the original 5-pattern one-liner to 18 patterns
- JSONL event log (`--log`), desktop notifications (plyer), `--list-patterns`,
  `--quiet`, `--no-notify`, configurable polling interval
- Pretty ANSI-color terminal output with session summary

### Desktop GUI (`/app/desktop/`)
- Tkinter app with arm/pause toggle, stats cards (events / chars / patterns
  active), live redaction history with before/after preview
- Re-uses `/app/cli/patterns.py` via sys.path — no duplication

### Browser Extension (`/app/extension/`)
- Manifest v3, Chrome/Edge/Brave/Arc/Firefox (dev)
- Content script intercepts `copy`/`cut` on every page, rewrites clipboard
  data with cleaned text before the browser hands it to the target
- Background service-worker tracks aggregate counts + last 50 events
- Popup with enable toggle, stats, recent feed
- Options page with per-pattern toggles (stored in `chrome.storage.sync`)

### Backend API (`/app/backend/server.py`)
- `GET  /api/` — health
- `GET  /api/patterns` — lists all 18 patterns with examples
- `POST /api/redact` — server-side redaction, auto-tracks events
- `POST /api/track` — opt-in event counter for CLI/desktop/extension
- `GET  /api/feed?limit=N` — most recent anonymised events
- `GET  /api/stats` — aggregated counts + events in last 24h

### Web Dashboard (`/app/frontend/`)
- Sticky Nav (brand, section links, GitHub + Download CTA)
- Hero with rotating "type-then-redact" animation + two CTAs
- Playground: two-pane textarea with live client-side redaction, diff
  highlighting, summary bar (4 metrics), reset / clear / verify-server-side
- Pattern Library: 18 expandable cards revealing regex + sample in/out
- Stats Panel: 4 animated counters polling `/api/stats` every 4s, plus 24h row
- Downloads: 3 cards (CLI, Desktop GUI, Extension) with copy-to-clipboard
  install commands
- Live Feed: marquee ticker + grid polling `/api/feed` every 3s
- Footer with brand, GitHub, sitemap, legal pillars

### Repo structure / docs
- `/app/README.md` — top-level shareable README with install steps, badges,
  API reference, layout, contributing, privacy, license
- `/app/LICENSE` — MIT
- `/app/.gitignore` — Python + Node + env / logs
- Per-client READMEs in `cli/`, `desktop/`, `extension/`

## Testing

- `/app/test_reports/iteration_1.json` — 7/8 backend pytest + 100% frontend
  flows; one pattern-classification tweak (Anthropic ordering) has been fixed
  post-test
- `/app/backend/tests/test_ml_scorer.py` — 16 tests for the ML-style
  heuristic scorer (entropy, variety, length, pattern-boost, threshold
  filter) — all green
- `/app/backend/tests/test_audit_sqlite.py` — 8 tests for the optional
  SQLite audit backend (schema, encryption-at-rest, round-trip, tamper
  detection, date-range / event-type filters) — all green
- **32/32** pytest tests currently passing

## What's been implemented (2026-02)

### Live "Receipts" panel on the web dashboard
- `/app/scripts/generate_stats.py` — re-computes detection-rate / FP-rate
  from the same fixtures the pytest corpus asserts on, writes both
  `/app/frontend/public/stats.json` (latest snapshot) and
  `/app/frontend/public/stats-history.jsonl` (rolling 30-day window,
  idempotent per UTC date). Supports `--seed-history N` for initial
  bootstrapping; seeded entries are flagged `"seed": true` so they can
  be visually distinguished from real CI-generated snapshots.
- `/app/frontend/src/components/Sparkline.jsx` — dependency-free inline
  SVG polyline with auto-scaling + seed-vs-real dashed-vs-solid rendering.
- `/app/frontend/src/components/Receipts.jsx` — fetches stats.json **and**
  stats-history.jsonl, renders three metric tiles (detection rate %, FP
  rate %, patterns + ML entropy count), each with a 88×26 sparkline in
  the top-right corner showing the 30-day trend. Colour shifts to amber
  if FP rate creeps above 1%. Wired into `App.js` between Hero and
  Playground, plus a `#receipts` nav link.
- `/app/.github/workflows/ci.yml` — runs pytest corpus on every push/PR,
  downloads prior `stats-history` artifact, regenerates both files, and
  re-uploads both (stats.json 30-day retention, stats-history 90-day).

### Pattern-corpus regression suite
- 540 synthetic positives (30 per pattern, seeded, distribution-faithful;
  zero real leaked secrets — RFC-5737 TEST-NET IPs + public Stripe test
  PANs)
- 158 curated false positives (UUIDs, git SHAs, version strings,
  placeholders, docker digests, code comments)
- Tightened `long_base64_blob` regex to exclude pure-hex digests — real
  product win surfaced by the FP corpus (git SHAs / docker digests no
  longer get redacted). Detection rate for true base64 blobs stays 100%.
- Pinned known-limitation cases for 2-series Mastercard, 14-digit Diners,
  and JCB — tests will *fail loudly* when the CC regex expansion lands,
  inviting a clean corpus migration.

### Unified enterprise CLI dispatcher (`/app/cli/vibe_protect_enterprise.py`)
Thin (~225-line) dispatcher that routes every flag to existing hardened
modules — no inlined crypto, no duplicated logic:

| Flag | Delegates to |
|---|---|
| *(none)* | `vibe_protect.main()` clipboard monitor (monkey-patched to apply `--backend` + `--confidence`) |
| `--build-chrome` | zips real `/app/extension/` → `dist/vibe_protect_extension_v<ver>.zip` |
| `--audit` (+ `--audit-format html|json|md`) | `SecurityAuditor.generate_report()` |
| `--build-binaries` | delegates to `installer/build_windows.py` on Windows; prints precise PyInstaller recipe for macOS/Linux (tracked P2) |
| `--test-bug "<text>"` | **LOCAL-ONLY** detector self-test — input is never persisted, hashed, or transmitted; on miss, points user to `SECURITY.md` |
| `--backend sqlite\|flatfile` | `AuditLogger(backend=…)` |
| `--confidence 0.0..1.0` | `AdvancedSecretDetector(ml_confidence_threshold=…)` |

**Security boundaries preserved** (vs. the user's monolithic v3.0 script
that was NOT adopted verbatim):
- Master-key salt stays persisted across runs (monolith would regenerate
  it, breaking decryption of all prior logs).
- SQLite audit rows store the AES-GCM + HMAC-signed entry as an encrypted
  blob; metadata is never persisted in cleartext.
- `--test-bug` never writes the user's input to disk — covered by
  `test_input_never_written_to_disk` regression test.
- `--build-chrome` zips the real working Manifest V3 extension, not a
  placeholder that returns text unchanged.

### ML-style heuristic secret scoring
- `AdvancedSecretDetector.calculate_ml_score(text, pattern_matched)` —
  bounded [0, 1] weighted sum of:
  Shannon entropy (0.35) + length/128 (0.15) + char variety (0.20) +
  pattern-match boost (+0.30)
- Every `AdvancedMatch` now carries a `confidence` float; structural
  patterns (emails, IPs, CCs, shell prompts, DB URLs) are always 1.0 so an
  aggressive threshold can't suppress real PII.
- Configurable `ml_confidence_threshold` (default 0.0 = keep everything).
- API `Match` model now exposes `confidence` over the wire.

### Optional SQLite audit backend
- `AuditLogger(backend="sqlite")` persists AES-256-GCM encrypted,
  HMAC-signed entries in an indexed `audit_events` table with SQL-side
  date-range / event-type filters.
- Flat-file (`BACKEND_FLATFILE`) remains the default; both backends share
  identical crypto + tamper detection.
- `audit_logger.py --backend sqlite {verify|list|report}` CLI support.

## Testing (66/66 pytest green)
- `/app/backend/tests/test_vibe_protect.py` — 8 FastAPI endpoint tests
- `/app/backend/tests/test_ml_scorer.py` — 16 tests for heuristic scorer
  (entropy, variety, length, pattern-boost, threshold filter)
- `/app/backend/tests/test_audit_sqlite.py` — 8 tests for SQLite backend
  (schema, encryption-at-rest, round-trip, tamper, isolation)
- `/app/backend/tests/test_enterprise_dispatcher.py` — 7 tests for the
  unified CLI (help surface, arg validation, `--test-bug` secret-never-
  persisted regression, `--build-chrome` real-extension check)
- `/app/backend/tests/test_corpus.py` — **27 tests** over a 540-case
  synthetic positive corpus + 158-case FP corpus. Current scores:
  per-pattern detection ≥ 90%, overall **100%**, FP rate **0%**,
  confidence–entropy monotonicity across quartiles, real-vs-placeholder
  confidence gap ≥ 0.10, + 4 pinned known-limitation assertions for
  unsupported CC brands (2-series MC, 14-digit Diners, JCB). Corpus
  fixtures live under `/app/backend/tests/corpus/`.

### Regex improvement (2026-02)
- `long_base64_blob` tightened to exclude pure-hex 60+ char strings
  (git SHAs, docker `@sha256:…` digests, hash output). Surfaced by the
  new FP corpus; detection rate for true base64 blobs stays 100%.

## Prioritised backlog / future

**P1**
- Expand `credit_card` regex to cover 2-series Mastercard (2221-2720),
  14-digit Diners, and JCB (16-digit). Pinned by
  `test_corpus::TestKnownLimitations` — those tests will flip to failing
  when the regex lands, at which point move the PANs into the main corpus.
- Package CLI as a `pip install vibe-protect` with console script
- Publish the extension to Chrome Web Store + Firefox Add-ons
- Real PNG icons for the extension (currently placeholder-only)
- System-tray icon (`pystray`) for the desktop app + auto-start on login
- Unit tests for each regex pattern (true-positive + false-positive corpora)

**P2**
- User-defined custom patterns in the desktop app (dropped-in via settings)
- Encrypted cloud-sync of custom patterns across a user's machines
- Dark-mode / light-mode toggle for the web dashboard (current: dark only)
- Localisation (es, pt, fr, ja)
- Safari Web Extension port
- CI: GitHub Actions workflow running pytest + eslint on every PR

## Next task list

1. Add real icons for the browser extension (`icons/icon{16,32,48,128}.png`)
2. Add unit tests for the pattern library (Python + JS)
3. Optionally publish to PyPI / Chrome Web Store / Firefox AMO
