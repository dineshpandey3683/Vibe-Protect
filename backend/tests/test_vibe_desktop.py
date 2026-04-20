"""
Headless test suite for ``/app/desktop/vibe_desktop.py``.

Strategy
========
The desktop app is a Tkinter UI that also optionally drags in ``pystray``
and ``plyer``. CI runners don't have a display server, so we exercise
two layers:

1. **Pure-import smoke** — just importing the module must never raise,
   regardless of whether ``pystray`` / ``tkinter`` / ``plyer`` resolved.
2. **Integration under Xvfb** — if an X display is reachable (locally
   or because the container has ``xvfb-run``) we construct a real
   ``VibeApp`` and drive its scrubber pipeline end-to-end.

The second block is automatically skipped when there's no display,
which keeps the suite green on minimal CI images without losing the
real behaviour check when Xvfb is available.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Desktop-app tests require Tkinter to import the module at all. In CI
# images without ``libtk`` (or on the bare web-deploy container) the
# test file must skip cleanly rather than hard-error.
pytest.importorskip("tkinter", reason="Tkinter not available — desktop tests skipped")

ROOT = Path(__file__).resolve().parents[2]
DESKTOP_DIR = ROOT / "desktop"
CLI_DIR = ROOT / "cli"
for p in (str(DESKTOP_DIR), str(CLI_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


# --------------------------------------------------------------------- #
# 1) pure-import smoke                                                  #
# --------------------------------------------------------------------- #

def test_vibe_desktop_imports_cleanly():
    """The module must import with zero side-effects even when optional
    deps (pystray, plyer) can't start their backends."""
    import vibe_desktop  # noqa: F401

    # Optional-feature flags must be booleans — never raise on probe.
    assert isinstance(vibe_desktop._HAS_TRAY, bool)
    assert isinstance(vibe_desktop._HAS_NOTIFY, bool)
    assert isinstance(vibe_desktop._HAS_AUTOSTART, bool)
    # Core class surface exists
    assert hasattr(vibe_desktop, "VibeApp")
    assert hasattr(vibe_desktop, "main")


def test_make_tray_icon_is_pure_pil():
    """The tray-icon factory must not need an X server — it's just PIL."""
    import vibe_desktop

    # Call the unbound method directly so we don't need a VibeApp
    # instance (which would need Tk).
    img = vibe_desktop.VibeApp._make_tray_icon(None)  # type: ignore[arg-type]
    assert img.size == (64, 64)
    assert img.mode == "RGBA"


# --------------------------------------------------------------------- #
# 2) real-Tk integration (auto-skipped without a display)               #
# --------------------------------------------------------------------- #

def _display_available() -> bool:
    if not os.environ.get("DISPLAY"):
        return False
    try:
        import tkinter as tk
        r = tk.Tk()
        r.destroy()
        return True
    except Exception:
        return False


requires_display = pytest.mark.skipif(
    not _display_available(),
    reason="no X display available (run under xvfb-run to enable)",
)


@requires_display
def test_vibeapp_builds_and_scrubs_end_to_end():
    import tkinter as tk
    from vibe_desktop import VibeApp

    root = tk.Tk()
    try:
        app = VibeApp(root)
        # Both tabs were registered
        assert len(app.notebook.tabs()) == 2
        # Scrubber pipeline — drop a clearly-sensitive string and
        # assert it's masked in the output pane.
        secret = (
            "key=sk-abcdefghijklmnopqrstuvwxyz"
            "0123456789ABCDEFGHIJabcdef"
        )
        app.input_text.insert("1.0", secret)
        app._recompute_scrub()
        out = app.output_text.get("1.0", "end").strip()
        assert "[" in out and "]" in out, f"no redaction tag in: {out!r}"
        assert "sk-abcdefghijklmnop" not in out
    finally:
        try:
            root.destroy()
        except Exception:
            pass


@requires_display
def test_close_without_tray_really_quits():
    """When pystray isn't active, clicking the window X must destroy
    the root and stop the clipboard worker."""
    import tkinter as tk
    import vibe_desktop

    root = tk.Tk()
    app = vibe_desktop.VibeApp(root)
    # Force the "no tray" path regardless of runtime availability.
    app.tray_icon = None
    monkey_has_tray = vibe_desktop._HAS_TRAY
    vibe_desktop._HAS_TRAY = False
    try:
        app._on_close()
        assert app._stop.is_set()
    finally:
        vibe_desktop._HAS_TRAY = monkey_has_tray
        try:
            root.destroy()
        except Exception:
            pass
