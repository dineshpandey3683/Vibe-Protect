# Vibe Protect — Desktop GUI

A cross-platform Tkinter app that monitors your clipboard, auto-redacts
secrets, and shows live history with stats. Everything runs locally — nothing
leaves your machine.

## Install

```bash
cd desktop
pip install -r requirements.txt
# plus, shared patterns come from ../cli/patterns.py — no extra setup
```

> Tkinter ships with CPython on macOS and Windows. On Debian/Ubuntu:
> `sudo apt install python3-tk xclip`.

## Run

```bash
python vibe_desktop.py
```

Click **● ARMED / ○ PAUSED** in the top right to toggle monitoring.
