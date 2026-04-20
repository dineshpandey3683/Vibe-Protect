"""
Tests for the CLI scanner modes added in v1.0:
  --file <path>    scan a single file or stdin
  --json           machine-readable output
  --pre-commit     git staged-file scanner (implies --json)

These are black-box integration tests: they invoke ``vibe_protect.py``
as a subprocess and assert on the process exit code + JSON payload.
That way we also exercise the argparse wiring, not just the helpers.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

CLI = Path(__file__).resolve().parents[2] / "cli" / "vibe_protect.py"
PY = sys.executable


def run(*extra, input_text: str | None = None, cwd: str | None = None, env: dict | None = None):
    """Run the CLI and return (exit_code, stdout_text)."""
    result = subprocess.run(
        [PY, str(CLI), *extra],
        capture_output=True,
        text=True,
        input=input_text,
        cwd=cwd,
        env={**os.environ, **(env or {})},
    )
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------- --file

class TestFileMode:
    def test_clean_file_exits_zero(self, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text("def add(a, b):\n    return a + b\n")
        code, out, _ = run("--file", str(f))
        assert code == 0
        assert "clean" in out

    def test_dirty_file_exits_one_in_human_mode(self, tmp_path):
        f = tmp_path / "dirty.py"
        f.write_text(
            'OPENAI_API_KEY = "sk-proj-qR7pK2mNvEwXzB9aLdTfYh3JwC5xPnM2vK8Bd0AbCdEfGh"\n'
            'user_email = "alice@example.com"\n'
        )
        code, out, _ = run("--file", str(f))
        assert code == 1
        assert "secret(s)" in out or "email" in out

    def test_json_output_is_parseable_and_redacts_plaintext(self, tmp_path):
        f = tmp_path / "dirty.py"
        secret = "sk-proj-qR7pK2mNvEwXzB9aLdTfYh3JwC5xPnM2vK8Bd0AbCdEfGh"
        f.write_text(f'OPENAI_API_KEY = "{secret}"\n')
        code, out, _ = run("--file", str(f), "--json")
        assert code == 1
        payload = json.loads(out)
        assert payload["ok"] is True
        assert payload["secrets_found"] >= 1
        assert payload["exit_code"] == 1
        # No plaintext in the detections projection — only pattern name,
        # mask, confidence, start, end.
        for d in payload["detections"]:
            assert secret not in json.dumps(d)
        # `redacted` field must contain the mask, not the plaintext
        assert secret not in payload["redacted"]

    def test_stdin_scan(self):
        # '-' means stdin
        code, out, _ = run(
            "--file", "-", "--json",
            input_text='api_key = "sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH"\n',
        )
        assert code == 1
        payload = json.loads(out)
        assert payload["file"] == "<stdin>"
        assert payload["secrets_found"] >= 1

    def test_missing_file_exits_two(self, tmp_path):
        code, _, err = run("--file", str(tmp_path / "nope.py"))
        assert code == 2
        assert "cannot read" in err.lower() or "no such" in err.lower()


# ---------------------------------------------------------------- --pre-commit

def _init_repo(tmp: Path) -> Path:
    subprocess.check_call(["git", "init", "-q"], cwd=tmp)
    subprocess.check_call(["git", "config", "user.email", "t@t.t"], cwd=tmp)
    subprocess.check_call(["git", "config", "user.name", "t"], cwd=tmp)
    return tmp


class TestPreCommitMode:
    def test_staged_secret_blocks_commit(self, tmp_path):
        _init_repo(tmp_path)
        (tmp_path / "secrets.env").write_text(
            "OPENAI_API_KEY=sk-proj-qR7pK2mNvEwXzB9aLdTfYh3JwC5xPnM2vK8Bd0AbCdEfGh\n"
        )
        (tmp_path / "readme.md").write_text("hello world\n")
        subprocess.check_call(["git", "add", "."], cwd=tmp_path)

        code, out, _ = run("--pre-commit", cwd=str(tmp_path))
        assert code == 1, "pre-commit must block when secrets are staged"
        payload = json.loads(out)
        assert payload["mode"] == "pre-commit"
        assert payload["files_scanned"] == 2
        assert payload["files_with_secrets"] == 1
        assert payload["total_secrets"] >= 1
        # Only the bad file is flagged
        flagged = {f["file"] for f in payload["findings"]}
        assert flagged == {"secrets.env"}

    def test_clean_staging_passes(self, tmp_path):
        _init_repo(tmp_path)
        (tmp_path / "readme.md").write_text("hello world\n")
        subprocess.check_call(["git", "add", "."], cwd=tmp_path)

        code, out, _ = run("--pre-commit", cwd=str(tmp_path))
        assert code == 0
        payload = json.loads(out)
        assert payload["total_secrets"] == 0
        assert payload["findings"] == []

    def test_binary_files_are_skipped(self, tmp_path):
        _init_repo(tmp_path)
        (tmp_path / "logo.bin").write_bytes(b"\x00\x01\x02\x03" + b"sk-proj-aaaaaaaaa" * 20)
        subprocess.check_call(["git", "add", "."], cwd=tmp_path)
        code, out, _ = run("--pre-commit", cwd=str(tmp_path))
        payload = json.loads(out)
        # binary file should neither be scanned nor crash the hook
        assert payload["files_with_secrets"] == 0

    def test_outside_a_repo_returns_clean_error(self, tmp_path):
        # tmp_path is not a git repo
        code, out, _ = run("--pre-commit", cwd=str(tmp_path))
        assert code == 2
        payload = json.loads(out)
        assert payload["ok"] is False
        assert "git" in payload.get("error", "").lower()


# ---------------------------------------------------------------- --json flag

class TestJsonFlag:
    def test_pre_commit_implies_json(self, tmp_path):
        _init_repo(tmp_path)
        (tmp_path / "readme.md").write_text("hello\n")
        subprocess.check_call(["git", "add", "."], cwd=tmp_path)
        # we don't pass --json — the mode should emit JSON anyway
        code, out, _ = run("--pre-commit", cwd=str(tmp_path))
        assert code == 0
        # must be parseable as JSON
        json.loads(out)

    def test_file_mode_without_json_is_human_readable(self, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text("print('hi')\n")
        code, out, _ = run("--file", str(f))
        assert code == 0
        # default output is ANSI-coloured text, not JSON — so it should NOT parse as JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(out)
