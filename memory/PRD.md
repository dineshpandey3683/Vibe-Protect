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

## Prioritised backlog / future

**P1**
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
