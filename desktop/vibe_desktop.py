#!/usr/bin/env python3
"""
Vibe Protect — Desktop GUI.

Two-pane Tkinter app:
  • Monitor tab   — passive clipboard watcher with live redaction history
  • Scrubber tab  — manual paste-and-scrub pane with read-only output

Plus:
  • System-tray icon (pause/show/quit) via pystray — optional
  • Desktop notifications via plyer — optional
  • Background update check + dynamic pattern sync via shared modules

Run:
    python vibe_desktop.py
"""

from __future__ import annotations

import os
import sys
import threading
import time
import queue
from datetime import datetime

# sibling cli/ dir is single source of truth for patterns / updater
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "cli")))
sys.path.insert(0, _HERE)   # so `autostart` resolves locally

import tkinter as tk
from tkinter import ttk

import pyperclip  # noqa: E402
from patterns import redact, PATTERNS  # noqa: E402
from updater import current_version  # noqa: E402
from production_updater import ProductionUpdater  # noqa: E402

try:
    from autostart import is_enabled as _autostart_on, enable as _autostart_enable, disable as _autostart_disable
    _HAS_AUTOSTART = True
except Exception:
    _HAS_AUTOSTART = False

# ------------------------------------------------------------------ optional deps
try:
    from plyer import notification as _plyer_notification  # type: ignore
    _HAS_NOTIFY = True
except Exception:
    _HAS_NOTIFY = False

try:
    import pystray  # type: ignore
    from PIL import Image, ImageDraw  # type: ignore
    _HAS_TRAY = True
except Exception:
    _HAS_TRAY = False


# ------------------------------------------------------------------ theme
BG = "#0A0A0A"
SURFACE = "#121212"
ELEV = "#1A1A1A"
FG = "#FAFAFA"
MUTED = "#A1A1AA"
AMBER = "#FACC15"
BORDER = "#2A2A2A"
SUCCESS = "#86EFAC"


class VibeApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Vibe Protect — Clipboard Guardian")
        self.root.geometry("820x620")
        self.root.configure(bg=BG)
        self.root.minsize(680, 480)

        self.enabled = tk.BooleanVar(value=True)
        self.total_redactions = 0
        self.total_chars = 0
        self._q: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._last_clip = ""
        self._last_notify_ts = 0.0

        self._build_ui()
        self._start_clipboard_worker()
        self.root.after(150, self._drain_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._setup_system_tray()
        threading.Thread(target=self._startup_update_check, daemon=True).start()

    # ===================================================================== UI
    def _build_ui(self):
        self._configure_styles()

        # header ------------------------------------------------------------
        header = tk.Frame(self.root, bg=BG, highlightthickness=0)
        header.pack(fill="x", padx=20, pady=(18, 8))
        tk.Label(
            header, text="▍ VIBE PROTECT",
            fg=AMBER, bg=BG, font=("Courier New", 14, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text="clipboard guardian",
            fg=MUTED, bg=BG, font=("Courier New", 10),
        ).pack(side="left", padx=(10, 0))

        self.toggle_btn = tk.Button(
            header, text="● ARMED", command=self._toggle,
            bg=SURFACE, fg=AMBER, activebackground=ELEV, activeforeground=AMBER,
            bd=0, padx=14, pady=6, font=("Courier New", 10, "bold"), cursor="hand2",
        )
        self.toggle_btn.pack(side="right")

        # stats row ---------------------------------------------------------
        stats = tk.Frame(self.root, bg=BG)
        stats.pack(fill="x", padx=20, pady=(0, 10))
        self.events_lbl = self._stat_card(stats, "EVENTS", "0")
        self.chars_lbl = self._stat_card(stats, "CHARS SCRUBBED", "0")
        self.patterns_lbl = self._stat_card(stats, "PATTERNS ACTIVE", str(len(PATTERNS)))

        # tabs --------------------------------------------------------------
        self.notebook = ttk.Notebook(self.root, style="Vibe.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        self.monitor_tab = tk.Frame(self.notebook, bg=BG)
        self.scrubber_tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.monitor_tab, text="  MONITOR  ")
        self.notebook.add(self.scrubber_tab, text="  PASTE & SCRUB  ")

        self._build_monitor_tab(self.monitor_tab)
        self._build_scrubber_tab(self.scrubber_tab)

        # footer ------------------------------------------------------------
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", padx=20, pady=(0, 14))
        tray_note = " · system tray enabled" if _HAS_TRAY else ""
        notify_note = " · notifications on" if _HAS_NOTIFY else ""
        tk.Label(
            footer,
            text=f"v{current_version()} · 300ms poll · local only{tray_note}{notify_note}",
            fg=MUTED, bg=BG, font=("Courier New", 9),
        ).pack(side="left")
        self.update_lbl = tk.Label(
            footer, text="check for updates",
            fg=MUTED, bg=BG, font=("Courier New", 9, "underline"), cursor="hand2",
        )
        self.update_lbl.pack(side="right")
        self.update_lbl.bind("<Button-1>", lambda _e: self._check_update(force=True))

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Vibe.TNotebook", background=BG, borderwidth=0, tabmargins=[0, 4, 0, 0])
        style.configure(
            "Vibe.TNotebook.Tab",
            background=SURFACE,
            foreground=MUTED,
            font=("Courier New", 9, "bold"),
            padding=(16, 8),
            borderwidth=0,
        )
        style.map(
            "Vibe.TNotebook.Tab",
            background=[("selected", BG)],
            foreground=[("selected", AMBER)],
        )
        style.layout("Vibe.TNotebook.Tab", [
            ("Notebook.tab", {
                "sticky": "nswe",
                "children": [("Notebook.padding", {
                    "side": "top", "sticky": "nswe",
                    "children": [("Notebook.label", {"side": "top", "sticky": ""})],
                })],
            }),
        ])

    def _stat_card(self, parent, label, value):
        card = tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(card, text=label, fg=MUTED, bg=SURFACE,
                 font=("Courier New", 9), anchor="w", padx=12, pady=(8, 0)).pack(fill="x")
        val = tk.Label(card, text=value, fg=FG, bg=SURFACE,
                       font=("Courier New", 22, "bold"), anchor="w", padx=12, pady=(0, 10))
        val.pack(fill="x")
        return val

    # ----------------------------------------------------------- monitor tab
    def _build_monitor_tab(self, parent):
        wrap = tk.Frame(parent, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        wrap.pack(fill="both", expand=True)
        tk.Label(wrap, text="  redaction history",
                 fg=MUTED, bg=BG, font=("Courier New", 10), anchor="w").pack(fill="x", pady=(6, 4))

        self.hist = tk.Text(
            wrap, bg=BG, fg=FG, insertbackground=AMBER,
            bd=0, relief="flat", font=("Courier New", 10),
            padx=12, pady=8, wrap="word",
        )
        self.hist.pack(fill="both", expand=True)
        self.hist.tag_config("ts", foreground=MUTED)
        self.hist.tag_config("amber", foreground=AMBER)
        self.hist.tag_config("muted", foreground=MUTED)
        self.hist.tag_config("green", foreground=SUCCESS)
        self.hist.configure(state="disabled")
        self._append_hist("Armed. Copy something sensitive to see it redacted.\n", "muted")

    # ---------------------------------------------------------- scrubber tab
    def _build_scrubber_tab(self, parent):
        intro = tk.Label(
            parent,
            text="paste anything on the left. the scrubbed version appears on the right, read-only.",
            fg=MUTED, bg=BG, font=("Courier New", 9), anchor="w",
        )
        intro.pack(fill="x", padx=2, pady=(8, 6))

        split = tk.Frame(parent, bg=BG)
        split.pack(fill="both", expand=True)
        split.grid_columnconfigure(0, weight=1, uniform="pane")
        split.grid_columnconfigure(1, weight=1, uniform="pane")
        split.grid_rowconfigure(0, weight=1)

        # INPUT
        in_wrap = tk.Frame(split, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        in_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        tk.Label(in_wrap, text="  INPUT · editable", fg=MUTED, bg=BG,
                 font=("Courier New", 9), anchor="w").pack(fill="x", pady=(4, 0))
        self.input_text = tk.Text(
            in_wrap, bg=BG, fg=FG, insertbackground=AMBER,
            bd=0, relief="flat", font=("Courier New", 10),
            padx=10, pady=8, wrap="word",
        )
        self.input_text.pack(fill="both", expand=True)
        self.input_text.bind("<<Modified>>", self._on_input_modified)

        # OUTPUT (read-only)
        out_wrap = tk.Frame(split, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        out_wrap.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        tk.Label(out_wrap, text="  OUTPUT · read-only, safe to copy",
                 fg=AMBER, bg=BG, font=("Courier New", 9), anchor="w").pack(fill="x", pady=(4, 0))
        self.output_text = tk.Text(
            out_wrap, bg=BG, fg=FG,
            bd=0, relief="flat", font=("Courier New", 10),
            padx=10, pady=8, wrap="word",
        )
        self.output_text.pack(fill="both", expand=True)
        self.output_text.tag_config("redact", background=AMBER, foreground=BG)
        self.output_text.tag_config("plain", foreground=FG)
        self.output_text.configure(state="disabled")

        # action bar
        actions = tk.Frame(parent, bg=BG)
        actions.pack(fill="x", pady=(8, 0))
        self.scrub_summary = tk.Label(
            actions, text="ready · paste text to scrub",
            fg=MUTED, bg=BG, font=("Courier New", 9),
        )
        self.scrub_summary.pack(side="left")
        tk.Button(
            actions, text="Paste from clipboard", command=self._paste_into_input,
            bg=SURFACE, fg=FG, activebackground=ELEV, activeforeground=FG,
            bd=0, padx=12, pady=6, font=("Courier New", 9), cursor="hand2",
        ).pack(side="right", padx=(6, 0))
        tk.Button(
            actions, text="Clear", command=self._clear_scrubber,
            bg=SURFACE, fg=FG, activebackground=ELEV, activeforeground=FG,
            bd=0, padx=12, pady=6, font=("Courier New", 9), cursor="hand2",
        ).pack(side="right", padx=(6, 0))
        self.copy_btn = tk.Button(
            actions, text="Copy scrubbed ✓", command=self._copy_scrubbed,
            bg=AMBER, fg=BG, activebackground="#FDE047", activeforeground=BG,
            bd=0, padx=14, pady=6, font=("Courier New", 9, "bold"), cursor="hand2",
        )
        self.copy_btn.pack(side="right")

    # ================================================================= actions
    def _toggle(self):
        self.enabled.set(not self.enabled.get())
        if self.enabled.get():
            self.toggle_btn.configure(text="● ARMED", fg=AMBER)
            self._append_hist("Re-armed.\n", "amber")
        else:
            self.toggle_btn.configure(text="○ PAUSED", fg=MUTED)
            self._append_hist("Paused. Clipboard is not being monitored.\n", "muted")

    def _paste_into_input(self):
        try:
            text = pyperclip.paste() or ""
        except Exception:
            text = ""
        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", text)
        self._recompute_scrub()

    def _clear_scrubber(self):
        self.input_text.delete("1.0", "end")
        self._render_scrubbed("", [])

    def _copy_scrubbed(self):
        scrubbed = self.output_text.get("1.0", "end").rstrip("\n")
        if not scrubbed.strip():
            return
        try:
            pyperclip.copy(scrubbed)
            self._notify("Copied scrubbed text — safe to paste anywhere")
            self.copy_btn.configure(text="Copied ✓")
            self.root.after(1400, lambda: self.copy_btn.configure(text="Copy scrubbed ✓"))
        except Exception as e:
            self._append_hist(f"copy failed: {e}\n", "muted")

    def _on_input_modified(self, _event=None):
        self.input_text.edit_modified(False)
        self._recompute_scrub()

    def _recompute_scrub(self):
        source = self.input_text.get("1.0", "end").rstrip("\n")
        if not source:
            self._render_scrubbed("", [])
            self.scrub_summary.configure(text="ready · paste text to scrub")
            return
        cleaned, matches = redact(source)
        self._render_scrubbed(cleaned, matches)
        if matches:
            counts = {}
            for m in matches:
                counts[m["pattern"]] = counts.get(m["pattern"], 0) + 1
            summary = ", ".join(f"{k}×{v}" for k, v in counts.items())
            self.scrub_summary.configure(
                text=f"● scrubbed {len(matches)} secret(s) · {len(source) - len(cleaned)} chars removed · {summary}"
            )
        else:
            self.scrub_summary.configure(text="clean · nothing detected")

    def _render_scrubbed(self, cleaned: str, matches: list):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        if not cleaned:
            self.output_text.configure(state="disabled")
            return
        # highlight [TAG] masks in amber — everything else plain
        import re
        cursor = 0
        for m in re.finditer(r"\[[A-Z_]+\]", cleaned):
            if m.start() > cursor:
                self.output_text.insert("end", cleaned[cursor:m.start()], "plain")
            self.output_text.insert("end", m.group(0), "redact")
            cursor = m.end()
        if cursor < len(cleaned):
            self.output_text.insert("end", cleaned[cursor:], "plain")
        self.output_text.configure(state="disabled")

    # ================================================================ worker
    def _start_clipboard_worker(self):
        threading.Thread(target=self._clipboard_worker, daemon=True).start()

    def _clipboard_worker(self):
        try:
            self._last_clip = pyperclip.paste() or ""
        except Exception:
            self._last_clip = ""
        while not self._stop.is_set():
            time.sleep(0.3)
            if not self.enabled.get():
                continue
            try:
                current = pyperclip.paste() or ""
            except Exception:
                continue
            if not current or current == self._last_clip:
                continue
            cleaned, matches = redact(current)
            if matches:
                try:
                    pyperclip.copy(cleaned)
                except Exception:
                    pass
                self._last_clip = cleaned
                self._q.put({"original": current, "cleaned": cleaned, "matches": matches, "ts": datetime.now()})
            else:
                self._last_clip = current

    def _drain_queue(self):
        try:
            while True:
                evt = self._q.get_nowait()
                self._render_event(evt)
        except queue.Empty:
            pass
        self.root.after(150, self._drain_queue)

    def _render_event(self, evt):
        self.total_redactions += 1
        self.total_chars += max(0, len(evt["original"]) - len(evt["cleaned"]))
        self.events_lbl.configure(text=str(self.total_redactions))
        self.chars_lbl.configure(text=str(self.total_chars))

        kinds = {}
        for m in evt["matches"]:
            kinds[m["pattern"]] = kinds.get(m["pattern"], 0) + 1
        summary = ", ".join(f"{k}×{v}" for k, v in kinds.items())
        stamp = evt["ts"].strftime("%H:%M:%S")

        self.hist.configure(state="normal")
        self.hist.insert("end", f"[{stamp}]  ", "ts")
        self.hist.insert("end", f"● redacted {len(evt['matches'])} secret(s)  ", "amber")
        self.hist.insert("end", f"({summary})\n", "muted")
        preview_in = evt["original"].replace("\n", " ⏎ ")[:100]
        preview_out = evt["cleaned"].replace("\n", " ⏎ ")[:100]
        self.hist.insert("end", f"  in : {preview_in}\n", "muted")
        self.hist.insert("end", f"  out: {preview_out}\n\n", "green")
        self.hist.see("end")
        self.hist.configure(state="disabled")

        # throttled notification
        now = time.time()
        if now - self._last_notify_ts > 3:
            self._notify(f"Redacted {len(evt['matches'])} secret(s): {summary}")
            self._last_notify_ts = now

    def _append_hist(self, text, tag=None):
        self.hist.configure(state="normal")
        if tag:
            self.hist.insert("end", text, tag)
        else:
            self.hist.insert("end", text)
        self.hist.see("end")
        self.hist.configure(state="disabled")

    # ================================================================ tray
    def _setup_system_tray(self):
        if not _HAS_TRAY:
            return
        try:
            image = self._make_tray_icon()
            menu = pystray.Menu(
                pystray.MenuItem("Show window", self._tray_show, default=True),
                pystray.MenuItem(
                    lambda _i: "Pause protection" if self.enabled.get() else "Resume protection",
                    self._tray_toggle,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Start at login",
                    self._tray_toggle_autostart,
                    checked=lambda _i: _HAS_AUTOSTART and _autostart_on(),
                    enabled=lambda _i: _HAS_AUTOSTART,
                ),
                pystray.MenuItem(
                    "Open audit folder",
                    self._tray_open_audit_folder,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit Vibe Protect", self._tray_quit),
            )
            self.tray_icon = pystray.Icon("vibe_protect", image, "Vibe Protect", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            print(f"[vibe-protect] tray setup skipped: {e}")

    def _make_tray_icon(self):
        """Generate a 64x64 amber shield icon programmatically (no file needed)."""
        img = Image.new("RGBA", (64, 64), (10, 10, 10, 0))
        d = ImageDraw.Draw(img)
        # amber rounded square
        d.rounded_rectangle((4, 4, 60, 60), radius=10, fill=(250, 204, 21, 255))
        # subtle shield glyph (a triangle)
        d.polygon([(32, 14), (50, 22), (50, 36), (32, 52), (14, 36), (14, 22)],
                  fill=(10, 10, 10, 255))
        d.polygon([(32, 20), (44, 26), (44, 34), (32, 44), (20, 34), (20, 26)],
                  fill=(250, 204, 21, 255))
        return img

    def _tray_show(self, _icon=None, _item=None):
        try:
            self.root.after(0, self.root.deiconify)
            self.root.after(0, self.root.lift)
        except Exception:
            pass

    def _tray_toggle(self, _icon=None, _item=None):
        self.root.after(0, self._toggle)

    def _tray_quit(self, _icon=None, _item=None):
        try:
            self.tray_icon.stop()
        except Exception:
            pass
        self.root.after(0, self._really_quit)

    def _tray_toggle_autostart(self, _icon=None, _item=None):
        if not _HAS_AUTOSTART:
            return
        try:
            if _autostart_on():
                _autostart_disable()
                self._notify("Start at login disabled.")
            else:
                path = _autostart_enable()
                self._notify(f"Start at login enabled\n{path}")
        except Exception as e:
            self._notify(f"Couldn't change auto-start: {e}")

    def _tray_open_audit_folder(self, _icon=None, _item=None):
        # The audit logger stores encrypted logs in ~/.vibeprotect/audit by
        # default — open the containing folder in the OS file manager.
        from pathlib import Path
        audit_dir = Path.home() / ".vibeprotect" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        try:
            import subprocess
            import sys as _sys
            if _sys.platform == "darwin":
                subprocess.Popen(["open", str(audit_dir)])
            elif _sys.platform.startswith("win"):
                os.startfile(str(audit_dir))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(audit_dir)])
        except Exception as e:
            self._notify(f"Couldn't open audit folder: {e}")

    # =============================================================== notify
    def _notify(self, message: str):
        if not _HAS_NOTIFY:
            return
        try:
            _plyer_notification.notify(
                title="Vibe Protect",
                message=message,
                timeout=3,
                app_name="Vibe Protect",
            )
        except Exception:
            pass

    # =========================================================== lifecycle
    def _check_update(self, force: bool = False, silent: bool = False):
        updater = ProductionUpdater(on_update=lambda _info: None, force=force)
        info = updater.check_for_update()
        def _apply():
            if info.error and not silent:
                self.update_lbl.configure(text="update check failed", fg=MUTED)
                return
            if info.is_update_available:
                self.update_lbl.configure(text=f"▲ update available → v{info.latest}", fg=AMBER)
                self.update_lbl.bind(
                    "<Button-1>",
                    lambda _e, url=info.release_url: self._open_url(url),
                )
            elif not silent:
                self.update_lbl.configure(text=f"✓ v{info.current} · up to date", fg=MUTED)
        try:
            self.root.after(0, _apply)
        except Exception:
            pass

    def _startup_update_check(self):
        ProductionUpdater(on_update=self._on_update_available).check_for_update()

    def _on_update_available(self, info):
        if not info or not info.is_update_available:
            return
        try:
            self.root.after(
                0,
                lambda: self.update_lbl.configure(
                    text=f"▲ update available → v{info.latest}", fg=AMBER
                ),
            )
            self.root.after(
                0,
                lambda: self.update_lbl.bind(
                    "<Button-1>", lambda _e, url=info.release_url: self._open_url(url)
                ),
            )
        except Exception:
            pass

    @staticmethod
    def _open_url(url: str):
        if not url:
            return
        import webbrowser
        try:
            webbrowser.open(url, new=2)
        except Exception:
            pass

    def _on_close(self):
        """Window-close handler — behaves as 'minimize to tray' when a tray
        icon is active, and only truly quits if no tray is available (or
        if the user explicitly chose Quit from the tray menu). This gives
        us the standard productivity-app UX: X hides, Quit exits.
        """
        if _HAS_TRAY and hasattr(self, "tray_icon") and self.tray_icon is not None:
            try:
                self.root.withdraw()
                if not getattr(self, "_hinted_tray", False):
                    self._notify("Vibe Protect is still running in the tray.\n"
                                 "Right-click the tray icon to quit.")
                    self._hinted_tray = True
            except Exception:
                self._really_quit()
            return
        self._really_quit()

    def _really_quit(self):
        self._stop.set()
        try:
            if hasattr(self, "tray_icon") and self.tray_icon is not None:
                self.tray_icon.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    root = tk.Tk()
    app = VibeApp(root)
    # When launched by the OS auto-start hook, open directly to the tray
    # instead of popping a window in the user's face at login.
    if "--tray-on-launch" in sys.argv and _HAS_TRAY:
        try:
            root.withdraw()
            app._hinted_tray = True  # don't show the "still running" hint on launch
        except Exception:
            pass
    root.mainloop()


if __name__ == "__main__":
    main()
