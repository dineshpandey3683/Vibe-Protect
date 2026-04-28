# Vibe Protect — Network Requirements

**TL;DR:** Works 100% offline. Only the clipboard-monitor mode makes
optional startup update checks, and only against two public read-only
GitHub URLs.

## Firewall rules

| Direction | Port | Protocol | Default  | Required for |
|-----------|------|----------|----------|------------------------------------|
| Outbound  | —    | —        | ✅ none  | Core redaction — works fully offline |
| Outbound  | 443  | HTTPS    | optional | `--check-update` + `--sync-patterns` (disable with `--no-update-check` / `--no-pattern-sync`) |
| Inbound   | —    | —        | ❌ never | Never required |

No ports are opened. No listeners are started. Nothing binds to any
interface.

## What exactly is reached over HTTPS

- `api.github.com` — used by `updater.py` to fetch the latest
  release metadata (read-only, public).
- `github.com` (`raw.githubusercontent.com`) — used by `patterns.py`
  and `community_rules.py` to fetch the signed pattern bundle
  (read-only, public).

Both are cached for 6 hours, both fail closed (the CLI continues to
work if the request fails), and both can be disabled globally with
`VP_DISABLE_UPDATE_CHECK=1 VP_DISABLE_PATTERN_SYNC=1`.

## Air-gapped / offline mode

```bash
# one command — survives a disconnected boot / firewall blackhole
VP_DISABLE_UPDATE_CHECK=1 VP_DISABLE_PATTERN_SYNC=1 vibe-protect
```

## CI / Docker / pre-commit

These entry points are **network-silent by design**:

- `vibe-protect --file <path>`
- `vibe-protect --pre-commit`
- `vibe-protect --install-hook`
- `vibe-protect --json`
- the Docker image (`docker run dineshpandey3683/Vibe-Protect …`)
- the VS Code extension's redact / scan commands

They exit before any update-check code path runs. Verify with
`vibe-protect --verify-telemetry`.
