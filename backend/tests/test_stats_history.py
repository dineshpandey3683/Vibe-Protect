"""
Tests for the rolling JSONL history logic in ``scripts/generate_stats.py``.

Covers:
1. First-run behaviour — one entry written.
2. Idempotency — re-running on the same UTC date replaces the existing
   entry rather than appending a duplicate.
3. 30-entry cap — older-than-30-days entries are trimmed.
4. Seed history — ``seed_history(N)`` writes N back-dated entries, all
   marked ``seed=true``, and a later regular run marks itself ``seed=false``.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP_ROOT / "scripts"))
sys.path.insert(0, str(APP_ROOT / "cli"))
sys.path.insert(0, str(APP_ROOT / "backend" / "tests"))

import generate_stats as gs  # noqa: E402


def _load(path: Path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


class TestHistoryManagement:
    def test_first_run_writes_one_entry(self, tmp_path):
        hist = tmp_path / "stats-history.jsonl"
        snap = gs.compute_stats(datetime.now(timezone.utc), seed=False)
        gs.update_history(hist, snap)
        rows = _load(hist)
        assert len(rows) == 1
        assert rows[0]["date"] == snap["date"]

    def test_same_day_is_idempotent(self, tmp_path):
        hist = tmp_path / "stats-history.jsonl"
        snap = gs.compute_stats(datetime.now(timezone.utc), seed=False)
        gs.update_history(hist, snap)
        gs.update_history(hist, snap)
        gs.update_history(hist, snap)
        rows = _load(hist)
        assert len(rows) == 1

    def test_cap_at_30_entries(self, tmp_path):
        hist = tmp_path / "stats-history.jsonl"
        # synthesize 45 entries on consecutive days
        base = gs.compute_stats(datetime.now(timezone.utc), seed=True)
        rows = []
        for i in range(45):
            d = (datetime.now(timezone.utc) - timedelta(days=44 - i)).date().isoformat()
            row = dict(base)
            row["date"] = d
            rows.append(row)
        hist.write_text("\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n")

        snap = gs.compute_stats(datetime.now(timezone.utc), seed=False)
        gs.update_history(hist, snap)

        final = _load(hist)
        assert len(final) == gs.HISTORY_CAP
        # The most recent entry must be today; oldest must be HISTORY_CAP-1 days back
        dates = [r["date"] for r in final]
        assert dates == sorted(dates)
        assert dates[-1] == snap["date"]

    def test_seed_history_fills_n_days(self, tmp_path):
        hist = tmp_path / "stats-history.jsonl"
        gs.seed_history(hist, days=10)
        rows = _load(hist)
        assert len(rows) == 10
        assert all(r["seed"] is True for r in rows)

    def test_real_run_after_seed_is_marked_unseeded(self, tmp_path):
        hist = tmp_path / "stats-history.jsonl"
        gs.seed_history(hist, days=7)
        snap = gs.compute_stats(datetime.now(timezone.utc), seed=False)
        gs.update_history(hist, snap)
        rows = _load(hist)
        # last entry = today's real run, not seeded
        last = rows[-1]
        assert last["date"] == snap["date"]
        assert last["seed"] is False
        # seeded prefix preserved
        assert sum(1 for r in rows if r["seed"]) == 7

    def test_schema_stability(self, tmp_path):
        """The React component depends on these keys — fail loudly if one
        gets renamed."""
        snap = gs.compute_stats(datetime.now(timezone.utc), seed=False)
        for k in [
            "generated_at", "date", "version",
            "detection_rate", "false_positive_rate",
            "synthetic_secrets_tested", "false_positives_tested",
            "patterns_active", "ml_entropy_enabled", "seed", "per_pattern",
        ]:
            assert k in snap, f"stats schema missing key: {k}"

    def test_history_entry_is_a_single_jsonl_line(self, tmp_path):
        """Every line of stats-history.jsonl must be a complete JSON value
        on a single line — our React reader splits by newline."""
        hist = tmp_path / "stats-history.jsonl"
        snap = gs.compute_stats(datetime.now(timezone.utc), seed=False)
        gs.update_history(hist, snap)
        for line in hist.read_text().splitlines():
            if not line.strip():
                continue
            # would raise if JSON spanned multiple lines
            json.loads(line)
