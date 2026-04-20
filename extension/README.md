# Vibe Protect — Browser Extension (v2.0)

**What's new in v2.0:** radically narrower permission footprint.

| | v1.0 | v2.0 |
|---|---|---|
| Host permissions | `<all_urls>` (every site) | Only ChatGPT, Claude, GitHub |
| Auto-injected content script | Every site | Only ChatGPT & Claude |
| Clipboard permissions | Always granted | `clipboardRead` is optional, requested on demand |
| Other sites | Always protected | One-click **Protect this site** in the popup (uses `activeTab`) |
| Notifications | Permission always granted | Removed (badge counter is enough) |

## How it works now

* **ChatGPT (`chat.openai.com`, `chatgpt.com`) and Claude (`claude.ai`)** —
  the redactor is auto-injected on page load. Every copy / cut that would
  contain a secret gets scrubbed before the browser hands it to the destination.
* **Any other site** — nothing runs automatically. Click the extension icon
  → **⚠ Protect this site** to inject the redactor into just that tab for the
  current session. No permanent permission, no cross-site scanning.
* **Toggle off** — the master switch in the popup disables the redactor
  across every tab without uninstalling.

## Install (Chrome / Edge / Brave / Arc)

1. `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** → select this `extension/` folder
4. Pin the amber shield to your toolbar so you can see the badge counter

## Install (Firefox)

1. `about:debugging#/runtime/this-firefox`
2. **Load Temporary Add-on** → select `manifest.json`

## Customise patterns

Right-click the extension icon → **Options** to toggle any of the 18 built-in
patterns on or off.

## Privacy

* The content script runs **only** on the whitelisted hosts (or on-demand via
  your explicit click).
* **Zero network requests.** No analytics, no telemetry, no "phone home".
* Stats, settings, and the last-50 redaction events are stored in
  `chrome.storage.sync` / `chrome.storage.local` — browser-local only.
