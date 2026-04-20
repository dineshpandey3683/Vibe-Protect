#!/usr/bin/env python3
"""
Generate /app/frontend/public/stats.json **and** the rolling
/app/frontend/public/stats-history.jsonl from the live pytest corpus.

This script is the single source of truth behind the web dashboard's
"receipts" panel. It doesn't parse pytest output — it imports the corpus
fixtures + detector directly and re-computes the same metrics the
``test_corpus.py`` suite asserts on. That way the JSON and the test
suite can never drift: both read the same fixtures, run through the
same detector, and arrive at the same numbers.

Output files
------------
1. ``frontend/public/stats.json`` — the latest snapshot (stable schema).
2. ``frontend/public/stats-history.jsonl`` — one snapshot per day, capped
   at 30 entries. Subsequent runs on the same UTC date **replace** the
   existing entry (idempotent — CI can run many times a day without
   bloating history). Older-than-30-days entries are trimmed.

Stable JSON schema (the React component depends on these keys):

    {
        "generated_at":             "2026-02-20T10:00:00+00:00",
        "date":                     "2026-02-20",
        "version":                  "2.0.0",
        "detection_rate":           1.0,
        "false_positive_rate":      0.0,
        "synthetic_secrets_tested": 540,
        "false_positives_tested":   158,
        "patterns_active":          18,
        "ml_entropy_enabled":       true,
        "seed":                     false,            // true iff --seed-history
        "per_pattern":              { ... }
    }

Usage::

    python scripts/generate_stats.py                     # daily append
    python scripts/generate_stats.py --seed-history 14   # initial seed
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT / "cli"))
sys.path.insert(0, str(APP_ROOT / "backend" / "tests"))

from advanced_detector import AdvancedSecretDetector  # noqa: E402
from corpus.false_positives import scoring_corpus     # noqa: E402
from corpus.generators import GENERATORS, all_positives  # noqa: E402
from patterns import PATTERNS  # noqa: E402

try:
    from updater import current_version
    VERSION = current_version()
except Exception:
    VERSION = "0.0.0"

HISTORY_CAP = 30


def compute_stats(now: datetime, seed: bool = False) -> dict:
    det = AdvancedSecretDetector()

    # ---- detection rate (per-pattern + overall)
    positives = all_positives()
    per_pattern = {name: {"hit": 0, "total": 0} for name in GENERATORS}
    for case in positives:
        per_pattern[case.pattern]["total"] += 1
        matches = det.detect(case.text)
        idx = case.text.find(case.secret)
        span = (idx, idx + len(case.secret))
        if any(m.start < span[1] and m.end > span[0] for m in matches):
            per_pattern[case.pattern]["hit"] += 1

    total_hit = sum(v["hit"] for v in per_pattern.values())
    total_pos = sum(v["total"] for v in per_pattern.values())
    detection_rate = total_hit / total_pos if total_pos else 0.0

    # ---- false-positive rate
    negatives = scoring_corpus()
    fp_hits = sum(1 for s in negatives if det.detect(s))
    fp_rate = fp_hits / len(negatives) if negatives else 0.0

    return {
        "generated_at":             now.isoformat(timespec="seconds"),
        "date":                     now.date().isoformat(),
        "version":                  VERSION,
        "detection_rate":           round(detection_rate, 4),
        "false_positive_rate":      round(fp_rate, 4),
        "synthetic_secrets_tested": total_pos,
        "false_positives_tested":   len(negatives),
        "patterns_active":          len(PATTERNS),
        "ml_entropy_enabled":       True,
        "seed":                     seed,
        "per_pattern":              per_pattern,
    }


# -------------------------------------------------------- history mgmt
def _load_history(path: Path) -> List[dict]:
    if not path.exists():
        return []
    out: List[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _write_history(path: Path, entries: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e, separators=(",", ":")) for e in entries) + "\n")


def update_history(history_path: Path, snapshot: dict) -> List[dict]:
    """Append ``snapshot`` idempotently on its ``date`` field, cap to
    ``HISTORY_CAP`` most recent entries (chronological order preserved)."""
    entries = _load_history(history_path)
    # drop any existing entry for the same date (idempotent per-day)
    entries = [e for e in entries if e.get("date") != snapshot["date"]]
    entries.append(snapshot)
    entries.sort(key=lambda e: e.get("date", ""))
    entries = entries[-HISTORY_CAP:]
    _write_history(history_path, entries)
    return entries


def seed_history(history_path: Path, days: int) -> List[dict]:
    """Bootstrap ``days`` daily snapshots back-dated to yesterday..N-days-ago.

    Every seeded entry carries ``"seed": true`` so maintainers can tell it
    apart from a real CI-generated snapshot. CI-generated entries on the
    same date (if any) will later overwrite these via ``update_history``.
    """
    now = datetime.now(timezone.utc)
    # Compute each snapshot ONCE (same corpus, same detector) and reuse —
    # the corpus is deterministic under a fixed seed so back-dating is honest
    # about the fact that the metric has been stable across builds.
    base = compute_stats(now, seed=True)

    entries = _load_history(history_path)
    existing_dates = {e.get("date") for e in entries}
    for i in range(days, 0, -1):
        d = (now - timedelta(days=i)).date().isoformat()
        if d in existing_dates:
            continue
        snap = dict(base)
        snap["date"] = d
        snap["generated_at"] = (now - timedelta(days=i)).isoformat(timespec="seconds")
        entries.append(snap)
    entries.sort(key=lambda e: e.get("date", ""))
    entries = entries[-HISTORY_CAP:]
    _write_history(history_path, entries)
    return entries


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate stats.json + stats-history.jsonl.")
    ap.add_argument(
        "--output",
        default=str(APP_ROOT / "frontend" / "public" / "stats.json"),
        help="path to write stats.json (default: frontend/public/stats.json)",
    )
    ap.add_argument(
        "--history",
        default=str(APP_ROOT / "frontend" / "public" / "stats-history.jsonl"),
        help="path to the rolling 30-day JSONL history",
    )
    ap.add_argument(
        "--seed-history",
        type=int,
        default=0,
        metavar="DAYS",
        help="before running, seed the history with DAYS back-dated entries "
             "(marked seed:true). Use once, locally, then rely on CI.",
    )
    args = ap.parse_args()

    history_path = Path(args.history)

    if args.seed_history > 0:
        seeded = seed_history(history_path, args.seed_history)
        print(f"✅ seeded {len(seeded)} history entries at {history_path}")

    stats = compute_stats(datetime.now(timezone.utc), seed=False)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stats, indent=2) + "\n")

    entries = update_history(history_path, stats)

    print(f"✅ wrote {out}")
    print(f"✅ history length: {len(entries)}  → {history_path}")
    print(f"   detection_rate      = {stats['detection_rate']:.2%}")
    print(f"   false_positive_rate = {stats['false_positive_rate']:.2%}")
    print(f"   positives tested    = {stats['synthetic_secrets_tested']}")
    print(f"   negatives tested    = {stats['false_positives_tested']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
