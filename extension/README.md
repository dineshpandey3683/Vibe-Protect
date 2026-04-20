# Vibe Protect — Browser Extension

Intercepts every `copy` / `cut` event, redacts any detected secrets in the
selection, and writes the cleaned text back to the clipboard before the paste
target ever sees it. A badge flashes on the extension icon with the count of
secrets caught. Click the icon to see history + toggle the shield.

## Install (Chrome / Edge / Brave / Arc)

1. Open `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** → select this `extension/` folder
4. Pin the **Vibe Protect** action button so you can see the counter badge

## Install (Firefox)

1. Open `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on** → select `manifest.json`

## Customise

Right-click the extension icon → **Options** to toggle individual patterns on
or off (useful if, for example, you regularly copy `192.168.x.x` addresses and
don't want them redacted).

## Privacy

All regex matching runs in your browser. The extension makes **zero network
requests** — there is no analytics, no telemetry, no "phone home".
