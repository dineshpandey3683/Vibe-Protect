r"""
Cross-platform "start at login" helper for the Vibe Protect desktop app.

Public API — all idempotent, all safe to call from a UI thread:

    is_enabled() -> bool
    enable()     -> str     # returns a human-readable artefact path
    disable()    -> None

Per-OS mechanisms
-----------------
* **Linux / BSD** — writes an XDG autostart desktop file at
  ``~/.config/autostart/vibe-protect.desktop``. Every mainstream
  session manager (GNOME, KDE, Xfce, MATE, Cinnamon, LXDE, sway/
  Wayland compositors) reads from this directory.
* **macOS** — writes a per-user launch agent plist at
  ``~/Library/LaunchAgents/dev.vibeprotect.desktop.plist``. Loaded at
  login; reboot-safe.
* **Windows** — writes an ``HKEY_CURRENT_USER\Software\Microsoft\
  Windows\CurrentVersion\Run`` registry value. No admin rights needed.

All three mechanisms are per-user, reversible, and don't require
elevated privileges — appropriate for a productivity tool a developer
installs without involving IT.

Every write uses the current ``sys.executable`` + the absolute path to
``vibe_desktop.py`` so an uninstall + reinstall in a different venv
won't leave a stale loader pointing at the old path (the next
``enable()`` rewrites).
"""
from __future__ import annotations

import os
import plistlib
import platform
import shutil
import sys
from pathlib import Path
from typing import Optional

APP_ID = "dev.vibeprotect.desktop"
APP_NAME = "Vibe Protect"

# --------------------------------------------------------------- paths
_SYSTEM = platform.system()


def _desktop_entry_path() -> Path:
    return Path.home() / ".config" / "autostart" / "vibe-protect.desktop"


def _launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{APP_ID}.plist"


def _windows_run_key():
    # Imported lazily so the module is still importable on non-Windows.
    import winreg  # type: ignore
    return winreg, r"Software\Microsoft\Windows\CurrentVersion\Run", "VibeProtect"


# --------------------------------------------------------- launcher cmd
def _desktop_script_path() -> Path:
    """Return the absolute path to ``vibe_desktop.py``."""
    return Path(__file__).resolve().with_name("vibe_desktop.py")


def _launch_command() -> list[str]:
    """Return the argv the OS should run at login."""
    return [sys.executable, str(_desktop_script_path()), "--tray-on-launch"]


# --------------------------------------------------------- Linux / BSD
_LINUX_DESKTOP_TEMPLATE = """[Desktop Entry]
Type=Application
Name={name}
Comment=Clipboard guardian — auto-redacts secrets
Exec={exec_cmd}
X-GNOME-Autostart-enabled=true
X-KDE-autostart-after=panel
Terminal=false
Hidden=false
NoDisplay=false
"""


def _write_desktop_entry() -> Path:
    p = _desktop_entry_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    argv = _launch_command()
    # Desktop files don't support list argv — join with shlex.
    import shlex
    exec_cmd = " ".join(shlex.quote(a) for a in argv)
    p.write_text(_LINUX_DESKTOP_TEMPLATE.format(name=APP_NAME, exec_cmd=exec_cmd))
    p.chmod(0o644)
    return p


# --------------------------------------------------------------- macOS
def _write_launch_agent() -> Path:
    p = _launch_agent_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": APP_ID,
        "ProgramArguments": _launch_command(),
        "RunAtLoad": True,
        "KeepAlive": False,
        "ProcessType": "Interactive",
    }
    with p.open("wb") as f:
        plistlib.dump(plist, f)
    return p


# --------------------------------------------------------------- Windows
def _write_run_key() -> str:
    winreg, subkey, value_name = _windows_run_key()
    # Quote the argv so spaces in paths don't break the loader.
    argv = _launch_command()
    import subprocess
    cmd = subprocess.list2cmdline(argv)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0,
                        winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, cmd)
    return f"HKCU\\{subkey}\\{value_name}"


# ============================================================== public API
def is_enabled() -> bool:
    try:
        if _SYSTEM == "Linux":
            return _desktop_entry_path().exists()
        if _SYSTEM == "Darwin":
            return _launch_agent_path().exists()
        if _SYSTEM == "Windows":
            winreg, subkey, value_name = _windows_run_key()
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0,
                                    winreg.KEY_READ) as key:
                    winreg.QueryValueEx(key, value_name)
                return True
            except FileNotFoundError:
                return False
    except Exception:
        return False
    return False


def enable() -> str:
    if _SYSTEM == "Linux":
        return str(_write_desktop_entry())
    if _SYSTEM == "Darwin":
        return str(_write_launch_agent())
    if _SYSTEM == "Windows":
        return _write_run_key()
    raise OSError(f"unsupported platform: {_SYSTEM}")


def disable() -> None:
    try:
        if _SYSTEM == "Linux":
            p = _desktop_entry_path()
            if p.exists():
                p.unlink()
        elif _SYSTEM == "Darwin":
            p = _launch_agent_path()
            if p.exists():
                p.unlink()
        elif _SYSTEM == "Windows":
            winreg, subkey, value_name = _windows_run_key()
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0,
                                    winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, value_name)
            except FileNotFoundError:
                pass
    except Exception:
        # Best-effort — a failure here shouldn't crash the UI. The user
        # can always remove the artefact manually; we surface the path
        # via enable()'s return value so they know where to look.
        pass


# --------------------------------------------------- test-only hook
def _override_paths_for_tests(  # noqa: D401
    linux_desktop: Optional[Path] = None,
    mac_plist: Optional[Path] = None,
) -> None:
    """Swap in tmp paths — used by the pytest suite, not by the app."""
    global _desktop_entry_path, _launch_agent_path
    if linux_desktop is not None:
        def _fn_linux() -> Path:
            return linux_desktop  # type: ignore[return-value]
        _desktop_entry_path = _fn_linux
    if mac_plist is not None:
        def _fn_mac() -> Path:
            return mac_plist  # type: ignore[return-value]
        _launch_agent_path = _fn_mac


__all__ = [
    "is_enabled",
    "enable",
    "disable",
    "_override_paths_for_tests",
]


if __name__ == "__main__":
    # Tiny CLI for manual / CI use:
    #   python -m desktop.autostart enable|disable|status
    import argparse
    ap = argparse.ArgumentParser(description="Manage Vibe Protect auto-start.")
    ap.add_argument("cmd", choices=["enable", "disable", "status"])
    args = ap.parse_args()
    if args.cmd == "enable":
        print(f"✅ enabled: {enable()}")
    elif args.cmd == "disable":
        disable()
        print("✅ disabled (if it was set)")
    else:
        print(f"{'enabled' if is_enabled() else 'disabled'}  ({_SYSTEM})")
        if _SYSTEM == "Linux":
            print(f"  artefact: {_desktop_entry_path()}")
        elif _SYSTEM == "Darwin":
            print(f"  artefact: {_launch_agent_path()}")

    # Informational: the shutil import makes the linter happy in CLI mode.
    _ = shutil
    _ = os
