# Vibe Protect — Privacy & Data Collection Declaration

**Version:** 1.0.0
**Last Updated:** 2026-04-21
**Short answer:** the product never sends data **about you** anywhere.

---

## 30-second summary

| Question | Answer |
|----------|--------|
| Does Vibe Protect transmit my clipboard, secrets, or redacted text? | **No. Ever.** |
| Does it send usage analytics / telemetry / crash reports? | **No.** |
| Does it upload anything to a cloud backend? | **No.** |
| Does it store clipboard history or PII? | **No.** |
| Does it phone home at startup? | **One optional GET**, see below — easy to disable. |

---

## Exactly what data the product handles

| Data | Saved? | Transmitted? |
|---|---|---|
| Clipboard content | ❌ never written to disk | ❌ never sent |
| Detected secrets (the plaintext) | ❌ never written to disk | ❌ never sent |
| Redacted output | ❌ never written to disk | ❌ never sent |
| Usage analytics | ❌ not collected | ❌ not sent |
| IP address | ❌ not collected | ❌ not sent |
| Device identifiers | ❌ not collected | ❌ not sent |

---

## What networking actually happens

Vibe Protect has **three** modes; their network behaviour differs.

### (a) Scanning / CI modes — **fully offline**
`--file`, `--pre-commit`, `--install-hook`, `--json`, every VS Code extension
command, every Chrome extension action, the web Playground redaction.

Zero outbound connections. Guaranteed by code path — these entry points
exit before the clipboard-monitor banner runs.

### (b) Clipboard monitor (interactive desktop / tray mode)
When you run plain `vibe-protect` (the always-on clipboard watcher), the
process performs **at most two** HTTPS GETs at startup:

| Request | URL | What's sent | Opt out |
|---|---|---|---|
| Version check | `api.github.com/repos/<org>/vibe-protect/releases/latest` | only the default `urllib` User-Agent | `--no-update-check` or `VP_DISABLE_UPDATE_CHECK=1` |
| Pattern library refresh | `github.com/<org>/vibe-protect/raw/main/patterns.bundle.json` | only the default `urllib` User-Agent | `--no-pattern-sync` or `VP_DISABLE_PATTERN_SYNC=1` |

Both are cached for 6 hours. Neither sends **anything about your
clipboard, your machine, or your usage** — they're plain GETs for
public files.

If you need a truly air-gapped run:
```bash
vibe-protect --no-update-check --no-pattern-sync
# or
VP_DISABLE_UPDATE_CHECK=1 VP_DISABLE_PATTERN_SYNC=1 vibe-protect
```

### (c) Optional enterprise audit logging
`--audit` writes an AES-256-GCM + HMAC-authenticated ledger to
`~/.vibeprotect/audit/`. **Local file only.** Never transmitted.

| Stored | Not stored |
|---|---|
| Event type (`REDACTED`) | Secret plaintext |
| Timestamp | Original clipboard text |
| Secret-type label (`openai_api_key`) | User identity |
| Confidence score | IP address |

Disable by simply not passing `--audit`.

---

## Verify it yourself

```bash
# Show exactly which network touchpoints will/won't run for your config
vibe-protect --verify-telemetry

# Check what's actually on disk
ls -la ~/.vibeprotect/

# Sniff the wire while it runs
sudo tcpdump -i any host api.github.com
```

`--verify-telemetry` inspects **your live configuration** and prints the
truth — not a pre-canned marketing string.

---

## Third-party surfaces (each documents its own)

- **Web playground** (`vibe.protect` / the Emergent-hosted site) — makes
  `POST /api/redact` to our backend **only when you click "verify
  server-side"**. The local-regex path is the default and never hits
  the network. See the site privacy footer for details.
- **Chrome extension** — runs entirely in-page; no background network
  calls. See `docs/chrome-store/privacy-policy.md`.
- **VS Code extension** — spawns the local CLI only. No network calls
  of its own. See `vscode-extension/README.md`.

---

## Reporting a privacy concern

Open an issue tagged `privacy` on GitHub, or email
`security@vibe.protect` (PGP key in `SECURITY.md`).

We will fix any real leak within one release cycle and publish the fix
in `CHANGELOG.md` with an `SEC-` tag.
