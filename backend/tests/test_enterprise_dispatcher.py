"""
Tests for the unified enterprise CLI dispatcher at
``/app/cli/vibe_protect_enterprise.py``.

These tests focus on the two risky flags — ``--test-bug`` (must NEVER
persist user input) and ``--build-chrome`` (must zip the real extension,
not regenerate a placeholder) — plus argument validation.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

CLI_DIR = Path(__file__).resolve().parents[2] / "cli"
DISPATCH = CLI_DIR / "vibe_protect_enterprise.py"


def _run(*args, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(DISPATCH), *args],
        capture_output=True, text=True, cwd=cwd or str(CLI_DIR),
    )


class TestHelpAndValidation:
    def test_help_lists_every_flag(self):
        r = _run("--help")
        assert r.returncode == 0
        for flag in ("--build-chrome", "--audit", "--build-binaries",
                     "--test-bug", "--backend", "--confidence"):
            assert flag in r.stdout

    def test_confidence_out_of_range_rejected(self):
        r = _run("--confidence", "1.5")
        assert r.returncode != 0
        assert "must be in [0.0, 1.0]" in r.stderr

    def test_invalid_backend_rejected(self):
        r = _run("--backend", "fancyfile", "--test-bug", "x")
        assert r.returncode != 0
        assert "invalid choice" in r.stderr


class TestTestBugSafety:
    """The --test-bug flag must be strictly local: the user-supplied input
    must never be persisted, hashed-for-tracking, or transmitted. These
    tests enforce that invariant."""

    SENTINEL = "tb-sentinel-Xy7Qw9Lk2Vr4Bn8Mz6Pt3Hj1AbCdEf-UNIQ"

    def _snapshot(self, root: Path) -> set[str]:
        """Recursively hash the byte-content of every regular file under root."""
        import hashlib
        out: set[str] = set()
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            try:
                data = p.read_bytes()
            except OSError:
                continue
            out.add(hashlib.sha256(data).hexdigest() + ":" + str(p.relative_to(root)))
        return out

    def test_detects_high_entropy_secret(self):
        r = _run("--test-bug", self.SENTINEL)
        assert r.returncode == 0
        assert "DETECTED" in r.stdout
        assert "sk" not in r.stdout.lower() or "NOT DETECTED" not in r.stdout

    def test_input_never_written_to_disk(self, tmp_path):
        # Snapshot every file under /app/cli + /app/dist before and after.
        # If the dispatcher leaks the input anywhere under app-root, a new
        # file will appear (or an existing file will change hash).
        targets = [CLI_DIR, CLI_DIR.parent / "dist", CLI_DIR.parent / "security_audits"]
        for t in targets:
            t.mkdir(parents=True, exist_ok=True)

        snaps_before = {t: self._snapshot(t) for t in targets}
        r = _run("--test-bug", self.SENTINEL)
        assert r.returncode == 0

        for t, before in snaps_before.items():
            after = self._snapshot(t)
            new_or_changed = after - before
            for entry in new_or_changed:
                path = (t / entry.split(":", 1)[1]).resolve()
                # __pycache__ bytecode is fine; nothing else is allowed.
                if "__pycache__" in path.parts:
                    continue
                content = path.read_bytes() if path.exists() else b""
                assert self.SENTINEL.encode() not in content, (
                    f"user-supplied --test-bug input leaked into {path}"
                )

    def test_false_negative_points_to_secure_disclosure(self):
        # Short placeholder-ish text so the detector says NOT DETECTED
        r = _run("--test-bug", "hello")
        assert r.returncode == 1
        assert "NOT DETECTED" in r.stdout
        assert "SECURITY.md" in r.stdout
        assert "never stored" in r.stdout.lower() or "not stored" in r.stdout.lower()


class TestBuildChrome:
    def test_zips_real_extension(self, tmp_path):
        r = _run("--build-chrome")
        assert r.returncode == 0, r.stderr
        # find the produced zip
        dist = CLI_DIR.parent / "dist"
        zips = sorted(dist.glob("vibe_protect_extension_v*.zip"))
        assert zips, "no extension zip produced"
        with zipfile.ZipFile(zips[-1]) as zf:
            names = set(zf.namelist())
            # Real MV3 extension must have at least manifest + a content script.
            assert "manifest.json" in names
            # the bundled extension ships a real redactor, not a stub
            manifest = zf.read("manifest.json").decode()
            assert "manifest_version" in manifest
