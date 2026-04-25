"""
Tests for ``cli/autostart.py`` — the cross-platform "start at login"
helper that ships with the desktop GUI.

We patch the desktop-file / plist paths to ``tmp_path`` so the tests
never touch the host's real ``~/.config/autostart`` or
``~/Library/LaunchAgents``. Windows isn't exercised here (the CI runs
on Linux) — the registry branch is manually verified on a Windows host.
"""
from __future__ import annotations

import platform
import plistlib
import sys
from pathlib import Path

import pytest

CLI_DIR = Path(__file__).resolve().parents[2] / "cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import autostart  # noqa: E402


@pytest.fixture
def sandboxed(tmp_path, monkeypatch):
    """Redirect every OS artefact path into tmp_path."""
    autostart._override_paths_for_tests(
        linux_desktop=tmp_path / "autostart" / "vibe-protect.desktop",
        mac_plist=tmp_path / "LaunchAgents" / "dev.vibeprotect.desktop.plist",
    )
    return tmp_path


class TestRoundTrip:
    def test_enable_then_disable_is_idempotent(self, sandboxed):
        if platform.system() not in ("Linux", "Darwin"):
            pytest.skip("platform-specific test")
        assert autostart.is_enabled() is False

        path = autostart.enable()
        assert Path(path).exists()
        assert autostart.is_enabled() is True

        # enabling twice must not error or duplicate
        autostart.enable()
        assert autostart.is_enabled() is True

        autostart.disable()
        assert autostart.is_enabled() is False

        # disabling an already-disabled autostart is a no-op
        autostart.disable()
        assert autostart.is_enabled() is False


class TestLinuxDesktopFile:
    def test_desktop_file_contents(self, sandboxed):
        if platform.system() != "Linux":
            pytest.skip("Linux-only test")
        autostart.enable()
        content = (sandboxed / "autostart" / "vibe-protect.desktop").read_text()
        assert "[Desktop Entry]" in content
        assert "Type=Application" in content
        assert "Exec=" in content
        assert "Vibe Protect" in content
        assert "X-GNOME-Autostart-enabled=true" in content
        # Launch argv must include the --tray-on-launch flag so login
        # doesn't pop a window in the user's face.
        assert "--tray-on-launch" in content


class TestMacLaunchAgent:
    def test_plist_structure(self, sandboxed):
        if platform.system() != "Darwin":
            pytest.skip("macOS-only test")
        autostart.enable()
        p = sandboxed / "LaunchAgents" / "dev.vibeprotect.desktop.plist"
        with p.open("rb") as f:
            data = plistlib.load(f)
        assert data["Label"] == "dev.vibeprotect.desktop"
        assert data["RunAtLoad"] is True
        argv = data["ProgramArguments"]
        assert isinstance(argv, list)
        assert argv[0] == sys.executable
        assert "--tray-on-launch" in argv


class TestPortableGuarantees:
    def test_launch_command_uses_current_interpreter(self):
        argv = autostart._launch_command()
        assert argv[0] == sys.executable
        assert argv[-1] == "--tray-on-launch"
        # the middle arg must be an absolute path to vibe_desktop.py
        assert Path(argv[1]).name == "vibe_desktop.py"
        assert Path(argv[1]).is_absolute()

    def test_unsupported_platform_raises(self, monkeypatch):
        monkeypatch.setattr(autostart, "_SYSTEM", "FreeBSD")
        with pytest.raises(OSError):
            autostart.enable()
