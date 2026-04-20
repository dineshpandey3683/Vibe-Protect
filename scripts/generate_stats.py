#!/usr/bin/env python3
"""
Generate /app/frontend/public/stats.json from the live pytest corpus.

This script is the single source of truth behind the web dashboard's
"receipts" panel. It doesn't parse pytest output — it imports the corpus
fixtures + detector directly and re-computes the same metrics the
``test_corpus.py`` suite asserts on. That way the JSON and the test
suite can never drift: both read the same fixtures, run through the
same detector, and arrive at the same numbers.

Output JSON schema (stable contract — the React component depends on it):

    {
        "generated_at":             "2026-02-20T10:00:00+00:00",
        "version":                  "2.0.0",
        "detection_rate":           1.0,
        "false_positive_rate":      0.0,
        "synthetic_secrets_tested": 540,
        "false_positives_tested":   158,
        "patterns_active":          18,
        "ml_entropy_enabled":       true,
        "per_pattern": {
            "openai_api_key":   { "hit": 30, "total": 30 },
            ...
        }
    }

Usage:
    python scripts/generate_stats.py [--output PATH]

Run from CI after pytest passes — that guarantees the published numbers
correspond to a green build.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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


def compute_stats() -> dict:
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
        "generated_at":             datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version":                  VERSION,
        "detection_rate":           round(detection_rate, 4),
        "false_positive_rate":      round(fp_rate, 4),
        "synthetic_secrets_tested": total_pos,
        "false_positives_tested":   len(negatives),
        "patterns_active":          len(PATTERNS),
        "ml_entropy_enabled":       True,
        "per_pattern":              per_pattern,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate stats.json for the web dashboard.")
    ap.add_argument(
        "--output",
        default=str(APP_ROOT / "frontend" / "public" / "stats.json"),
        help="path to write stats.json (default: frontend/public/stats.json)",
    )
    args = ap.parse_args()

    stats = compute_stats()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stats, indent=2) + "\n")

    print(f"✅ wrote {out}")
    print(f"   detection_rate      = {stats['detection_rate']:.2%}")
    print(f"   false_positive_rate = {stats['false_positive_rate']:.2%}")
    print(f"   positives tested    = {stats['synthetic_secrets_tested']}")
    print(f"   negatives tested    = {stats['false_positives_tested']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
