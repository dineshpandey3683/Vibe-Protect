# Windows installer

This folder builds a native Windows installer for Vibe Protect —
`VibeProtect-Setup-<version>.exe` — using **PyInstaller** to freeze the
desktop app and **Inno Setup** to wrap it. No admin privileges required to
install.

## Layout

```
installer/
├── setup.iss               # Inno Setup script
├── vibe_desktop.spec       # PyInstaller spec
├── build_windows.py        # one-shot build chain (exports patterns, icons, runs both tools)
├── patterns.json           # (generated) 18 bundled patterns
└── icon.ico                # (generated) multi-size Windows icon
```

## Build locally (Windows only)

1. Install:
   - Python 3.11+
   - [Inno Setup 6](https://jrsoftware.org/isinfo.php) (adds `ISCC.exe` to Program Files)
   - `pip install pyinstaller pillow -r desktop/requirements.txt -r cli/requirements.txt`

2. Run:
   ```cmd
   python installer\build_windows.py
   ```

3. Output:
   ```
   dist\VibeProtect-Setup-<version>.exe
   ```

## Build via CI (recommended)

Every `git push` of a `v*.*.*` tag triggers
`.github/workflows/release-windows.yml`, which builds the installer on a
fresh `windows-latest` runner and attaches it to the GitHub Release. No
Windows machine of your own required.

```bash
git tag v2.0.0
git push origin v2.0.0
# → GitHub Actions builds VibeProtect-Setup-2.0.0.exe and uploads it
```

## What the installer does

- Installs to `%LOCALAPPDATA%\Programs\VibeProtect` (user-level, **no UAC**)
- Creates Start Menu + optional Desktop shortcuts
- Optional **Start with Windows** tick during install (puts a shortcut in
  the user's startup folder — no registry writes, easy to reverse)
- Uninstaller leaves `~/.vibeprotect/` (user settings + cache) intact
- All bundled files — `vibe_desktop.exe`, `patterns.json`, `icon.ico`,
  `LICENSE.txt`, `README.txt` — live under the install dir

## Code signing (recommended before wide distribution)

Unsigned Windows executables trigger SmartScreen's "Unknown publisher"
warning. To sign:

1. Get a code-signing certificate (DigiCert, SSL.com, etc.; ~$300/year).
2. Add repo secrets: `WINDOWS_CERTIFICATE_PFX` (base64) and
   `WINDOWS_CERTIFICATE_PASSWORD`.
3. Add a signing step after **Build installer** in the workflow:

   ```yaml
   - name: Sign installer
     run: |
       $pfx = [Convert]::FromBase64String("${{ secrets.WINDOWS_CERTIFICATE_PFX }}")
       [IO.File]::WriteAllBytes("cert.pfx", $pfx)
       & signtool sign /f cert.pfx /p "${{ secrets.WINDOWS_CERTIFICATE_PASSWORD }}" `
         /tr http://timestamp.digicert.com /td sha256 /fd sha256 `
         dist\VibeProtect-Setup-*.exe
   ```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ISCC.exe not found` | Install Inno Setup 6, or add it to `PATH` |
| PyInstaller import errors for `pystray` / `plyer` | `pip install -r desktop/requirements.txt` |
| Tiny icon in Start Menu | Delete `installer/icon.ico` and re-run `build_windows.py --icon` |
| SmartScreen "Windows protected your PC" on install | Expected until you code-sign — see above |
