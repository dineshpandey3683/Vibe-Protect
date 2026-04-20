# Vibe Protect v1.0 — Release Checklist

**Status:** ✅ ship-ready  •  **Generated:** 2026-04-20  •  **Owner:** you

All automated gates are green. What's left below is everything only a
human with credentials can do.

---

## 1. Automated verification (already done)

| Gate | Status | Evidence |
|---|---|---|
| Python test suite (`pytest backend/tests/`) | ✅ **113 passed / 1 skipped** | macOS plist test is the one platform skip |
| Desktop app headless smoke (`xvfb-run pytest test_vibe_desktop.py`) | ✅ **4 / 4** | Tk+pystray import safely; scrubber pipeline E2E verified |
| Backend API liveness | ✅ | `GET /api/` → `{"service":"vibe-protect","status":"armed","patterns":18,"version":"1.0.0"}` |
| Backend redact contract | ✅ | `POST /api/redact` strips `sk-…` → `[OPENAI_API_KEY]` with confidence 1.0 |
| `/api/stats` + `/api/feed` | ✅ | 434 events, 4 030 secrets, 18 patterns active |
| Frontend build | ✅ | HTTP 200, dark / amber theme renders |
| Python wheel build (`python -m build`) | ✅ | `vibe_protect-1.0.0-py3-none-any.whl` (59 KB) + sdist (57 KB) |
| `twine check dist/*.{whl,tar.gz}` | ✅ **PASSED / PASSED** | Long-description metadata valid for PyPI render |
| Clean-venv install smoke | ✅ | `pip install dist/…whl` → both `vibe-protect` and `vibe-protect-enterprise` entry points wired |
| End-to-end detector in wheel | ✅ | `vibe-protect-enterprise --test-bug '…sk-…'` → 2 matches, confidence 0.79 / 1.00 |
| Chrome extension bundle | ✅ | `vibe_protect_extension_v1.0.0.zip` (15 files, 27 KB, MV3, 16/32/48/128 icons, no missing manifest keys) |

---

## 2. Human-only steps to launch

### 2a. PyPI publish
```bash
# one-time: create a scoped API token at https://pypi.org/manage/account/token/
#          (scope = "Project: vibe-protect" after first upload, or "Entire account" for first-time)

python -m build                               # → dist/*.whl, dist/*.tar.gz
python -m twine check  dist/vibe_protect-*    # sanity
python -m twine upload dist/vibe_protect-*    # asks for __token__ / pypi-…
```
Then tag the commit:
```bash
git tag -a v1.0.0 -m "Vibe Protect 1.0"
git push origin v1.0.0
```

### 2b. Chrome Web Store
1. Upload `dist/vibe_protect_extension_v1.0.0.zip` at
   <https://chrome.google.com/webstore/devconsole>.
2. Paste copy from `docs/chrome-store/listing.md`.
3. Link privacy policy: `docs/chrome-store/privacy-policy.md`
   (host it at a stable URL — the store requires a public link).
4. Upload the 4 promo tiles from `docs/chrome-store/` (440×280,
   920×680, 1400×560).
5. After the store approves you'll get a **listing ID**.
6. Flip the front-end env var:
   ```env
   REACT_APP_CWS_LISTING_ID=<your-listing-id>
   ```
   and redeploy — the download page picks it up automatically.

> **Heads-up:** `extension/manifest.json` declares `"version": "2.0.0"`
> (carried over from a previous Chrome release numbering) while the
> zip file is named `…_v1.0.0.zip` to match the PyPI product version.
> The Chrome Web Store uses the **manifest's** version string, so
> this is intentional — but double-check it matches whatever version
> was last approved on the store before you submit.

### 2c. GitHub release
After PyPI + Chrome are live:
```bash
gh release create v1.0.0 \
  dist/vibe_protect-1.0.0-py3-none-any.whl \
  dist/vibe_protect-1.0.0.tar.gz \
  dist/vibe_protect_extension_v1.0.0.zip \
  --title "Vibe Protect v1.0 — Clipboard Guardian" \
  --notes-file docs/chrome-store/listing.md
```

### 2d. Launch
- Post the Show HN / r/programming / Hacker News.
- Announce the PyPI + CWS links in the project README badges.

---

## 3. What changed in this hardening pass (A → C → B)

**A. Headless desktop test unblocked**
- Installed `python3-tk` / `tk8.6` / `xvfb` so `tkinter` loads in CI
- Added `/app/backend/tests/test_vibe_desktop.py` — 2 pure-import checks
  (always run) + 2 real-Tk integration checks (auto-skip without DISPLAY)
- Fixed a latent Tk widget bug in `_stat_card`: `tk.Label(…, pady=(8,0))`
  fails at widget construction (`bad screen distance "8 0"`), moved the
  tuple to the `.pack(pady=…)` call where Tk accepts it
- Made PIL import stand on its own so `_make_tray_icon` works even when
  `pystray` can't attach to an X systray (`_HAS_TRAY` now = `pystray ∧ PIL`)

**B. Launch artefacts re-verified**
- Re-built wheel + sdist, both pass `twine check`
- Clean-venv install smoke proved both console scripts land on `$PATH`
- `vibe-protect-enterprise --test-bug` returns the expected confidence
  scores end-to-end out of the installed wheel
- Chrome zip manifest validated: MV3, all 4 icon sizes present, no
  missing required keys

**C. Full regression**
- `pytest backend/tests/`: **113 passed, 1 skipped** (was 109)
- No regressions in ML scorer, audit SQLite, card brands, corpus,
  stats history, dispatcher, or web-API routes
