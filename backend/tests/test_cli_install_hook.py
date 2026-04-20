"""
Tests for the ``--install-hook`` / ``--uninstall-hook`` CLI flags.

Covers:
  • install into a clean repo (0 → hook on disk, executable, marker present)
  • idempotent re-install when our own marker is already there
  • refusal when a foreign hook exists (exit 3)
  • --force path: backs up foreign hook, installs ours (exit 0)
  • uninstall removes our hook and exits 0
  • uninstall refuses to remove a foreign hook (exit 3)
  • outside a git repo → exit 2 with a clear message
  • end-to-end: after install, `git commit` of a file with a secret fails
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest

CLI = Path(__file__).resolve().parents[2] / "cli" / "vibe_protect.py"
PY = sys.executable


def run(*args, cwd=None):
    r = subprocess.run(
        [PY, str(CLI), *args], capture_output=True, text=True, cwd=cwd,
    )
    return r.returncode, r.stdout, r.stderr


def _init_repo(p: Path) -> None:
    subprocess.check_call(["git", "init", "-q"], cwd=p)
    subprocess.check_call(["git", "config", "user.email", "t@t.t"], cwd=p)
    subprocess.check_call(["git", "config", "user.name", "t"], cwd=p)


def _strip_ansi(s: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


class TestInstall:
    def test_fresh_install_creates_executable_hook(self, tmp_path):
        _init_repo(tmp_path)
        code, out, _ = run("--install-hook", cwd=str(tmp_path))
        assert code == 0
        hook = tmp_path / ".git" / "hooks" / "pre-commit"
        assert hook.exists()
        # executable by owner
        assert hook.stat().st_mode & stat.S_IXUSR
        content = hook.read_text()
        assert "vibe-protect-managed-hook" in content
        assert "vibe-protect --pre-commit" in content

    def test_reinstall_is_idempotent(self, tmp_path):
        _init_repo(tmp_path)
        assert run("--install-hook", cwd=str(tmp_path))[0] == 0
        code, out, _ = run("--install-hook", cwd=str(tmp_path))
        assert code == 0
        assert "updated" in _strip_ansi(out)

    def test_refuses_to_overwrite_foreign_hook(self, tmp_path):
        _init_repo(tmp_path)
        hook = tmp_path / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho 'not ours'\n")
        hook.chmod(0o755)
        code, _, err = run("--install-hook", cwd=str(tmp_path))
        assert code == 3
        assert "existing pre-commit hook" in _strip_ansi(err)

    def test_force_backs_up_foreign_hook(self, tmp_path):
        _init_repo(tmp_path)
        hook = tmp_path / ".git" / "hooks" / "pre-commit"
        foreign = "#!/bin/sh\necho 'not ours'\n"
        hook.write_text(foreign)
        hook.chmod(0o755)

        code, _, _ = run("--install-hook", "--force", cwd=str(tmp_path))
        assert code == 0
        assert "vibe-protect-managed-hook" in hook.read_text()
        backup = tmp_path / ".git" / "hooks" / "pre-commit.vibe-protect.bak"
        assert backup.exists()
        assert backup.read_text() == foreign

    def test_install_outside_a_repo_errors_cleanly(self, tmp_path):
        # tmp_path is not a git repo
        code, _, err = run("--install-hook", cwd=str(tmp_path))
        assert code == 2
        assert "not inside a git repository" in _strip_ansi(err).lower()

    def test_respects_core_hookspath_override(self, tmp_path):
        """If core.hooksPath is set (monorepos, dotfile repos), install
        into THAT directory instead of .git/hooks/."""
        _init_repo(tmp_path)
        custom = tmp_path / "my-hooks"
        custom.mkdir()
        subprocess.check_call(
            ["git", "config", "core.hooksPath", str(custom)],
            cwd=tmp_path,
        )
        code, _, _ = run("--install-hook", cwd=str(tmp_path))
        assert code == 0
        assert (custom / "pre-commit").exists()
        # the default .git/hooks path should NOT have been touched
        assert not (tmp_path / ".git" / "hooks" / "pre-commit").exists()


class TestUninstall:
    def test_removes_our_hook(self, tmp_path):
        _init_repo(tmp_path)
        run("--install-hook", cwd=str(tmp_path))
        hook = tmp_path / ".git" / "hooks" / "pre-commit"
        assert hook.exists()

        code, out, _ = run("--uninstall-hook", cwd=str(tmp_path))
        assert code == 0
        assert not hook.exists()
        assert "removed" in _strip_ansi(out)

    def test_refuses_to_remove_foreign_hook(self, tmp_path):
        _init_repo(tmp_path)
        hook = tmp_path / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho 'not ours'\n")
        code, _, err = run("--uninstall-hook", cwd=str(tmp_path))
        assert code == 3
        assert hook.exists()  # untouched
        assert "refusing" in _strip_ansi(err).lower()

    def test_missing_hook_is_a_noop(self, tmp_path):
        _init_repo(tmp_path)
        code, out, _ = run("--uninstall-hook", cwd=str(tmp_path))
        assert code == 0
        assert "no pre-commit hook" in _strip_ansi(out).lower()


class TestEndToEnd:
    """After installing the hook, `git commit` of a file with a secret
    MUST fail and leave the commit out of the log.

    Requires `vibe-protect` on PATH. Skipped otherwise — the unit tests
    above already prove the installer works."""

    @pytest.fixture
    def repo(self, tmp_path):
        _init_repo(tmp_path)
        # Make the just-built wheel available so the hook's `exec vibe-protect`
        # resolves. If we haven't got a venv with it installed, skip.
        return tmp_path

    def test_commit_with_secret_is_blocked(self, repo, monkeypatch):
        import shutil
        vp = shutil.which("vibe-protect")
        if vp is None:
            pytest.skip("vibe-protect not on PATH — unit tests cover the installer")

        # install hook
        assert run("--install-hook", cwd=str(repo))[0] == 0

        (repo / "secret.env").write_text(
            "OPENAI_API_KEY=sk-proj-qR7pK2mNvEwXzB9aLdTfYh3JwC5xPnM2vK8Bd0AbCdEfGh\n"
        )
        subprocess.check_call(["git", "add", "secret.env"], cwd=repo)

        r = subprocess.run(
            ["git", "commit", "-m", "leaks"],
            cwd=repo, capture_output=True, text=True,
        )
        assert r.returncode != 0, "commit should have been blocked"

        # log should still be empty
        log = subprocess.run(
            ["git", "log", "--oneline"], cwd=repo, capture_output=True, text=True,
        )
        assert "leaks" not in log.stdout
