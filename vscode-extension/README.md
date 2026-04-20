# Vibe Protect for VS Code

Redact API keys, tokens, and PII from your code with one keystroke — powered by
the same detection engine as the [Vibe Protect CLI, desktop app, and Chrome
extension](https://github.com/vibeprotect/vibe-protect).

> **One source of truth.** This extension does not re-implement the pattern
> library in TypeScript. It shells out to `vibe-protect --file - --json`, so
> every pattern update you get from `pip install vibe-protect --upgrade`
> immediately propagates to VS Code.

## Features

- **`Vibe Protect: Redact selection`** (`Ctrl+Alt+R` / `Cmd+Alt+R`) — replaces
  the selected text in place with a scrubbed version.
- **`Vibe Protect: Copy scrubbed selection to clipboard`** (`Ctrl+Alt+C`) — leaves
  your editor untouched, puts the safe version on the clipboard.
- **`Vibe Protect: Scan current file`** — warns if the active file contains any
  secret (does not modify the file).
- **Optional scan-on-save** (opt-in in settings) — non-blocking notification
  whenever you save a file with a secret in it.

Right-click in any editor with a selection to get Redact / Copy-scrubbed in the
context menu.

## Requirements

The extension requires the `vibe-protect` CLI on your `$PATH`:

```bash
pip install vibe-protect
```

If you prefer an absolute path, set `vibeProtect.cliPath` in VS Code settings
to e.g. `/usr/local/bin/vibe-protect`.

## Settings

| Setting | Default | What it does |
|---|---|---|
| `vibeProtect.cliPath` | `vibe-protect` | Path / command used to invoke the CLI. |
| `vibeProtect.advanced` | `false` | Pass `--advanced` to the CLI — enables entropy-aware detection. Higher recall, slightly more false positives. |
| `vibeProtect.scanOnSave` | `false` | Scan every file on save and warn (non-blocking) if a secret is present. |

## Privacy

- **No network calls.** The extension only spawns the local CLI.
- **No plaintext in logs or notifications.** The redacted preview is the only
  thing the extension ever reads from the CLI's JSON output.
- Detections in the JSON payload carry pattern name, mask, confidence, and
  offsets — never the original secret string.

## Development

```bash
cd vscode-extension
yarn install
npm run compile
# F5 in VS Code to launch an Extension Development Host
```

The compiled extension lives in `out/extension.js`. Run `node
test/cli-bridge.test.js` to smoke-test the CLI bridge without booting a full
VS Code instance.

## License

MIT
