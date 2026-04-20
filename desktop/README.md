# Vibe Protect — Desktop GUI

A cross-platform Tkinter app with:

- **Monitor tab** — passive clipboard watcher, live redaction history, stats
  counters, arm/pause toggle.
- **Paste & Scrub tab** — manual two-pane scrubber. Paste anything on the
  left, see the redacted version on the right (**read-only** — prevents
  accidentally editing the output back to a leaky form), then **Copy
  scrubbed** writes only the safe version to the clipboard.
- **System-tray icon** — pause/resume/quit without opening the window
  (requires `pystray` + `pillow`; falls back silently if unavailable).
- **Desktop notifications** on redaction (throttled to ≥3s intervals;
  requires `plyer`; falls back silently if unavailable).
- **Background update check** with an amber footer badge when a new release
  is out.

Everything runs locally — nothing leaves your machine.

## Install

```bash
cd desktop
pip install -r requirements.txt
```

> **Linux note:** Tk needs `python3-tk xclip`:
> `sudo apt install python3-tk xclip`
> pystray on Linux additionally wants a system-tray host —
> GNOME needs the AppIndicator extension; KDE/XFCE work out of the box.

On macOS and Windows Tk ships with CPython.

## Run

```bash
python vibe_desktop.py
```

Tabs:

- **MONITOR** — click **● ARMED / ○ PAUSED** in the top right to toggle the
  clipboard watcher.
- **PASTE & SCRUB** — type or click **Paste from clipboard**. The right pane
  updates live with redacted `[TAG]` blocks highlighted in amber. Hit
  **Copy scrubbed** to put the safe version on the clipboard.

## Patterns

The desktop app pulls the 18 bundled patterns (plus any signed / community /
user-custom rules you've opted into) directly from `../cli/patterns.py` —
there's no duplication. Adding a pattern to the CLI automatically shows up
here on the next launch.
