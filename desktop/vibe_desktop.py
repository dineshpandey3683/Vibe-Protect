#!/usr/bin/env python3
"""
Vibe Protect — Desktop GUI.

A cross-platform Tkinter app that monitors your clipboard, redacts secrets,
and shows a live history window. Optional system-tray icon (via pystray).

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

# make sibling `cli/` importable so we reuse the single source of truth
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "cli")))

import tkinter as tk
from tkinter import ttk

import pyperclip  # noqa: E402
from patterns import redact, PATTERNS  # noqa: E402
from updater import check_for_update, current_version  # noqa: E402


BG = "#0A0A0A"
SURFACE = "#121212"
ELEV = "#1A1A1A"
FG = "#FAFAFA"
MUTED = "#A1A1AA"
AMBER = "#FACC15"
BORDER = "#2A2A2A"


class VibeApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Vibe Protect")
        self.root.geometry("780x540")
        self.root.configure(bg=BG)
        self.root.minsize(640, 420)

        self.enabled = tk.BooleanVar(value=True)
        self.events: list[dict] = []
        self.total_redactions = 0
        self.total_chars = 0
        self._q: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._last_clip = ""

        self._build_ui()
        self._start_worker()
        self.root.after(150, self._drain_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- UI ------------------------------------------------------------------
    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Surface.TFrame", background=SURFACE)
        style.configure("Elev.TFrame", background=ELEV)

        header = tk.Frame(self.root, bg=BG, highlightthickness=0)
        header.pack(fill="x", padx=20, pady=(18, 10))
        tk.Label(
            header,
            text="▍ VIBE PROTECT",
            fg=AMBER,
            bg=BG,
            font=("Courier New", 14, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="clipboard guardian",
            fg=MUTED,
            bg=BG,
            font=("Courier New", 10),
        ).pack(side="left", padx=(10, 0))

        self.toggle_btn = tk.Button(
            header,
            text="● ARMED",
            command=self._toggle,
            bg=SURFACE,
            fg=AMBER,
            activebackground=ELEV,
            activeforeground=AMBER,
            bd=0,
            padx=14,
            pady=6,
            font=("Courier New", 10, "bold"),
            cursor="hand2",
        )
        self.toggle_btn.pack(side="right")

        # stats row
        stats = tk.Frame(self.root, bg=BG)
        stats.pack(fill="x", padx=20, pady=(0, 10))
        self.events_lbl = self._stat_card(stats, "EVENTS", "0")
        self.chars_lbl = self._stat_card(stats, "CHARS SCRUBBED", "0")
        self.patterns_lbl = self._stat_card(stats, "PATTERNS ACTIVE", str(len(PATTERNS)))

        # history
        hist_wrap = tk.Frame(self.root, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        hist_wrap.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        tk.Label(
            hist_wrap,
            text="  redaction history",
            fg=MUTED,
            bg=BG,
            font=("Courier New", 10),
            anchor="w",
        ).pack(fill="x", pady=(6, 4))

        self.hist = tk.Text(
            hist_wrap,
            bg=BG,
            fg=FG,
            insertbackground=AMBER,
            bd=0,
            relief="flat",
            font=("Courier New", 10),
            padx=12,
            pady=8,
            wrap="word",
        )
        self.hist.pack(fill="both", expand=True)
        self.hist.tag_config("ts", foreground=MUTED)
        self.hist.tag_config("amber", foreground=AMBER)
        self.hist.tag_config("muted", foreground=MUTED)
        self.hist.tag_config("green", foreground="#86efac")
        self.hist.configure(state="disabled")
        self._append_line("Armed. Copy something sensitive to see it get redacted.\n", "muted")

        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", padx=20, pady=(0, 14))
        tk.Label(
            footer,
            text=f"v{current_version()} · polling @ 300ms · all processing happens locally · nothing leaves your machine",
            fg=MUTED,
            bg=BG,
            font=("Courier New", 9),
        ).pack(side="left")
        self.update_lbl = tk.Label(
            footer,
            text="check for updates",
            fg=MUTED,
            bg=BG,
            font=("Courier New", 9, "underline"),
            cursor="hand2",
        )
        self.update_lbl.pack(side="right")
        self.update_lbl.bind("<Button-1>", lambda _e: self._check_update(force=True))
        # silent startup check
        threading.Thread(target=lambda: self._check_update(force=False, silent=True), daemon=True).start()

    def _stat_card(self, parent, label, value):
        card = tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(
            card, text=label, fg=MUTED, bg=SURFACE,
            font=("Courier New", 9), anchor="w", padx=12, pady=(8, 0),
        ).pack(fill="x")
        val = tk.Label(
            card, text=value, fg=FG, bg=SURFACE,
            font=("Courier New", 22, "bold"), anchor="w", padx=12, pady=(0, 10),
        )
        val.pack(fill="x")
        return val

    # -- actions -------------------------------------------------------------
    def _toggle(self):
        self.enabled.set(not self.enabled.get())
        if self.enabled.get():
            self.toggle_btn.configure(text="● ARMED", fg=AMBER)
            self._append_line("Re-armed.\n", "amber")
        else:
            self.toggle_btn.configure(text="○ PAUSED", fg=MUTED)
            self._append_line("Paused. Clipboard is not being monitored.\n", "muted")

    def _append_line(self, text, tag=None):
        self.hist.configure(state="normal")
        if tag:
            self.hist.insert("end", text, tag)
        else:
            self.hist.insert("end", text)
        self.hist.see("end")
        self.hist.configure(state="disabled")

    # -- worker --------------------------------------------------------------
    def _start_worker(self):
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()

    def _worker(self):
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
                self._q.put(
                    {"original": current, "cleaned": cleaned, "matches": matches, "ts": datetime.now()}
                )
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

    def _on_close(self):
        self._stop.set()
        self.root.destroy()

    def _check_update(self, force: bool = False, silent: bool = False):
        info = check_for_update(force=force)
        def _apply():
            if info.error and not silent:
                self.update_lbl.configure(text="update check failed", fg=MUTED)
                return
            if info.is_update_available:
                self.update_lbl.configure(
                    text=f"▲ update available → v{info.latest}",
                    fg=AMBER,
                )
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

    @staticmethod
    def _open_url(url: str):
        if not url:
            return
        import webbrowser
        try:
            webbrowser.open(url, new=2)
        except Exception:
            pass


def main():
    root = tk.Tk()
    VibeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
