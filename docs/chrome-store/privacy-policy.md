# Privacy Policy — Vibe Protect Browser Extension

_Last updated: 2026-02_

## Summary (plain English)

**We don't collect anything. The extension runs entirely inside your
browser. We cannot see what you copy, what you paste, or what was
redacted — because none of it ever leaves your machine.**

## What data the extension handles

| Surface                        | Where it lives             | Who can see it    |
| ------------------------------ | -------------------------- | ----------------- |
| Clipboard text on enabled pages | Your browser (RAM only)   | You               |
| Per-site opt-in preferences    | `chrome.storage.local`     | You               |
| Pattern definitions            | Bundled with the extension | Anyone (open src) |

That's the complete list. There is no server component, no telemetry
endpoint, no analytics SDK, no error-reporting pipeline, no heartbeat
ping. We do not have infrastructure to receive your data if we wanted
to — and we don't want to.

## What data the extension DOES NOT handle

* Personally Identifiable Information (PII)
* Health information
* Financial & payment info
* Authentication info (passwords, credentials, security tokens)
* Personal communications
* Location
* Web history
* User activity
* Website content

*(These are the exact categories from Google's CWS disclosure form, for
 easy copy-paste into the dashboard. The answer is "No" for every row.)*

## Permissions, in detail

* **`activeTab`** — the extension can only read the tab you currently
  click on. It cannot observe background tabs.
* **`storage`** — remembers per-site opt-in so you don't re-click on
  every page load. Storage is `chrome.storage.local` (never synced to
  Google servers via `chrome.storage.sync`).
* **`scripting`** — injects the redactor content-script on tabs you
  explicitly enable.
* **`clipboardRead` (optional)** — requested *only* after you click
  "enable protection on this site". Used to sanitise the clipboard
  payload before your target page sees it. Revoking this permission
  disables redaction; it does not disable the extension.

## Open source

The full source is at <https://github.com/vibeprotect/vibe-protect>.
Every line of code that runs in your browser is auditable — including
the builds we ship to the Chrome Web Store (the zip is produced by
`cli/vibe_protect_enterprise.py --build-chrome` from the public repo).

## Contact

Security issues: see [SECURITY.md](../../SECURITY.md) for our
responsible-disclosure process. For everything else:
<security@vibeprotect.dev> or open a GitHub issue.

## Changes to this policy

If we ever change this policy we'll (a) bump the "Last updated" date
above, (b) mention it in the extension's release notes, and (c) write
a blog post explaining what changed and why. We will never
retroactively weaken these guarantees.
