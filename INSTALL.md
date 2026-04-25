# Vibe Protect — install in 30 seconds

Three surfaces. One brand. All shipped from this single repo.

```
┌─────────────┬──────────────────────────────────────┬──────────────────────────────┐
│ Surface     │ Command                              │ Notes                        │
├─────────────┼──────────────────────────────────────┼──────────────────────────────┤
│ CLI         │ pip install vibe-protect             │ macOS · Linux · Windows · WSL│
│             │ vibe-protect                         │ also: python -m vibe_protect │
│ Desktop GUI │ pip install "vibe-protect[desktop]"  │ Tkinter + pystray + plyer    │
│             │ vibe-protect-desktop                 │                              │
│ Chrome ext. │ Add to Chrome (Web Store, pending)   │ MV3, all Chromium browsers   │
│             │ — or — chrome://extensions → Load    │                              │
│             │   unpacked → select extension/       │                              │
└─────────────┴──────────────────────────────────────┴──────────────────────────────┘
```

## "I installed it but the shell can't find `vibe-protect`"

That means pip put it in `~/.local/bin/` (or `~/Library/Python/3.11/bin/` on
macOS) and that path isn't on your `$PATH`. Pick one:

### Option A — fix `$PATH` once
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc   # or ~/.zshrc
source ~/.bashrc
```

### Option B — invoke as a module (no PATH needed)
```bash
python -m vibe_protect            # CLI
python -m vibe_protect --help
python -c "import vibe_desktop; vibe_desktop.main()"   # desktop GUI
```

### Option C — system-wide install
```bash
sudo pip install vibe-protect          # writes to /usr/local/bin
# or
pipx install vibe-protect              # isolated venv, auto-PATH'd
```

## Desktop extras explained

`pip install vibe-protect` ships only the lightweight CLI dependencies
(no Pillow, no pystray, no Tk integration). Adding `[desktop]` pulls in:

- `pyperclip` — clipboard read/write
- `pillow` — tray icon rendering
- `pystray` — actual system tray
- `plyer` — cross-platform desktop notifications

`vibe-protect-desktop` is the entry point — it boots the Tkinter window,
the tray icon, and (if enabled) autostart-at-login.

## Verify everything works

```bash
vibe-protect --version              # → vibe-protect v1.0.0
vibe-protect --list-patterns        # 18 entries
vibe-protect --verify-telemetry     # full network surface inspection
vibe-protect --file myproject/.env  # one-shot scan, exit 1 if leaks
vibe-protect --pre-commit           # CI-friendly all-staged-files scan
vibe-protect --install-hook         # add a git pre-commit hook
```

## Chrome extension

While the Chrome Web Store listing is pending review, install manually:

```
1. Download dist/vibe_protect_extension_v1.0.0.zip from the Releases page
2. Unzip somewhere
3. Open chrome://extensions
4. Toggle "Developer mode" on
5. Click "Load unpacked", select the unzipped folder
```

Once approved, the **Add to Chrome** button on the landing page
(`/#downloads`) will deep-link to the store listing automatically — the
frontend reads `REACT_APP_CWS_LISTING_ID` from the deploy env.
