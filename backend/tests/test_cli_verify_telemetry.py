"""
Tests for ``vibe-protect --verify-telemetry``.

Black-box integration: we invoke the CLI as a subprocess and assert on
its stdout. That way we also exercise argparse wiring, not just the
internal ``_verify_telemetry`` helper.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

CLI = Path(__file__).resolve().parents[2] / "cli" / "vibe_protect.py"
PY = sys.executable


def run(*args, env=None):
    r = subprocess.run(
        [PY, str(CLI), *args], capture_output=True, text=True,
        env={**os.environ, **(env or {})},
    )
    return r.returncode, r.stdout, r.stderr


def _strip_ansi(s: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


class TestVerifyTelemetry:
    def test_runs_and_exits_zero(self):
        code, out, _ = run("--verify-telemetry")
        assert code == 0
        text = _strip_ansi(out)
        # top-level headings
        assert "telemetry verification" in text.lower()
        assert "1. Data on disk" in text
        assert "2. Network touchpoints" in text
        assert "3. What is NEVER sent" in text

    def test_reports_never_sent_list(self):
        code, out, _ = run("--verify-telemetry")
        assert code == 0
        text = _strip_ansi(out)
        # the invariant list must be exhaustive
        for item in (
            "clipboard content",
            "detected secrets",
            "redacted output",
            "usage / analytics / telemetry",
            "IP address",
            "audit log contents",
        ):
            assert item in text, f"missing {item!r} from 'never sent' list"

    def test_env_disable_updates_is_reflected(self):
        code, out, _ = run(
            "--verify-telemetry",
            env={
                "VP_DISABLE_UPDATE_CHECK": "1",
                "VP_DISABLE_PATTERN_SYNC": "1",
            },
        )
        assert code == 0
        text = _strip_ansi(out)
        # When BOTH are disabled the "on (opt-out)" status must not appear
        # for update-check or pattern-sync lines.
        # We look for "update check" line and assert its status shows disabled
        # rather than opt-out.
        for anchor in ("update check", "pattern library refresh"):
            idx = text.find(anchor)
            assert idx != -1
            # inspect the surrounding ~100 chars for the status marker
            neighbourhood = text[max(0, idx - 40):idx + 60]
            assert "disabled" in neighbourhood, (
                f"expected 'disabled' near {anchor!r}, got: {neighbourhood!r}"
            )

    def test_env_default_shows_opt_out_warning(self):
        # unset both env vars to simulate default behaviour
        code, out, _ = run(
            "--verify-telemetry",
            env={"VP_DISABLE_UPDATE_CHECK": "", "VP_DISABLE_PATTERN_SYNC": ""},
        )
        assert code == 0
        text = _strip_ansi(out)
        # In default state both probes show "on (opt-out)" status
        assert "on (opt-out)" in text

    def test_output_mentions_opt_out_flags(self):
        code, out, _ = run("--verify-telemetry")
        text = _strip_ansi(out)
        assert "--no-update-check" in text
        assert "--no-pattern-sync" in text
        assert "VP_DISABLE_UPDATE_CHECK" in text
        assert "VP_DISABLE_PATTERN_SYNC" in text
