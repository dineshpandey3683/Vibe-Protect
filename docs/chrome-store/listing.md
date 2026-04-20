# Chrome Web Store — Submission Assets

Everything a maintainer needs to copy-paste into the Chrome Web Store
Developer Dashboard at <https://chrome.google.com/webstore/devconsole>.

## Listing metadata

### Name (max 45 chars)

    Vibe Protect — Clipboard Guardian

### Short description (max 132 chars)

    Auto-redacts API keys, tokens, and PII from your clipboard before they reach ChatGPT, Claude, or Gemini. Zero telemetry.

### Detailed description

    Stop pasting your secrets into AI chats.

    Vibe Protect watches every paste you make on ChatGPT, Claude, and
    Gemini and auto-redacts anything that looks like a real credential —
    API keys, tokens, emails, credit-card numbers, database URLs, JWTs,
    SSH keys, and more — BEFORE the model ever sees it.

    WHY VIBE PROTECT

    • Catches 18 pattern families + a Shannon-entropy fallback for novel
      secrets. Published metrics: 100% detection across 540 synthetic
      positives, 0% false-positive rate across 158 code/docs/config
      samples. See the live audit at https://vibeprotect.dev#receipts.

    • Per-brand masks for credit cards — redacts show as [VISA], [AMEX],
      [MC], [DISCOVER], [DINERS], [JCB], [UNIONPAY]. Every match is
      Luhn-validated to kill random-number false positives.

    • Zero telemetry. Every decision happens locally in your browser.
      We never see what you copy, what you paste, or what was redacted.
      No external network calls of any kind from the content script.

    PRIVACY GUARANTEES

    • The extension does NOT request "read clipboard" permission at
      install — it asks only when you actively enable protection on a
      page (just-in-time permission model).
    • No analytics, no error reporting, no "call home" heartbeat.
    • Source code at https://github.com/vibeprotect/vibe-protect —
      audit it yourself, or run your own build.

    FREE AND OPEN SOURCE

    MIT-licensed. No trials, no feature-gating, no ads. If your team
    needs SOC2-compliant audit logging or enterprise policy deployment,
    the companion Python CLI ships those features free too
    (pip install vibe-protect).

### Category

    Productivity

### Language

    English

### Keywords (search terms)

    clipboard, security, secrets, redaction, api-keys, chatgpt-safety,
    claude-safety, developer-tools, privacy, DLP

## Permission justifications (required in CWS submission form)

| Permission         | Why we need it                                                   |
| ------------------ | ---------------------------------------------------------------- |
| `activeTab`        | Injects the redactor only into the tab the user explicitly enables. |
| `storage`          | Remembers per-site opt-in so the user doesn't re-click every page load. |
| `scripting`        | Enables JIT injection of the content script on user-enabled tabs. |
| `clipboardRead` *(optional)* | User opts in per-site. Required to sanitise the paste payload before the target page receives it. |

Host permissions (`https://chat.openai.com/*`, `https://chatgpt.com/*`,
`https://claude.ai/*`, `https://github.com/*`) are scoped to the AI chat
and code-sharing surfaces the user actually needs protection on. We
explicitly do NOT request `<all_urls>`.

## Screenshots to capture (1280×800 each — CWS spec)

1. **Hero**: the Vibe Protect landing page with the "✓ verified · 100%
   detection" badge visible.
2. **Playground in action**: a user pasting `sk-proj-…` into the demo
   textarea and seeing it replaced with `[OPENAI_API_KEY]`.
3. **Drawer**: the per-pattern drawer expanded, showing all 18 controls
   with coverage bars at 30/30.
4. **Popup**: the extension popup (1280×800 capture with the browser
   chrome, or 640×400 close-up).
5. **Receipts**: the receipts panel with sparklines visible — screenshots
   the rolling 30-day trend.

See `screenshots/` in this directory for the capture scripts.

## Promotional images (optional but recommended)

* Small tile:  440×280
* Marquee:    1400×560

Generated via `python scripts/generate_icons.py --force` (master icon
up-scaled by the Nano Banana pipeline — ask for the marquee variant).

## Promo tiles (required for Editor's Pick)

Ready at `/app/docs/chrome-store/promo/`:

- `small_440x280.png` — required for every non-basic listing
- `marquee_1400x560.png` — required for Editor's Pick / featured placement

These are "blank canvas" masters (shield on the left, negative space on
the right) so a maintainer can drop localised marketing copy in Figma
without re-running the image model. Regenerate via:

```bash
python scripts/generate_icons.py --promo-only          # reuse existing master
python scripts/generate_icons.py --promo --force       # re-render from scratch
```

## Go-live: flip the "Add to Chrome" button on the website

The web dashboard's hero has a conditional CTA: if the
`REACT_APP_CWS_LISTING_ID` build-time env var is set, the secondary
"Install on your machine" button is replaced with an amber
"🌐 Add to Chrome" button that deep-links to
`https://chromewebstore.google.com/detail/<LISTING_ID>`.

Once CWS approves the listing and assigns you a 32-char listing ID
(e.g. `abcdefghijklmnopqrstuvwxyz123456`):

```bash
# frontend/.env
REACT_APP_CWS_LISTING_ID=abcdefghijklmnopqrstuvwxyz123456
```

Rebuild the frontend (`yarn build`) and the button flips automatically.
No code change needed.

## Version-bump checklist

Before every `vibe-protect-enterprise --build-chrome`:

1. Bump `version` in `extension/manifest.json` (semver).
2. Regenerate icons if the design changed (`python scripts/generate_icons.py --force`).
3. `python cli/vibe_protect_enterprise.py --build-chrome` — produces the zip.
4. Upload the zip in the CWS dashboard → save draft.
5. Paste the text from this file into the listing form.
6. Submit for review. Approval typically takes 1–3 business days.
