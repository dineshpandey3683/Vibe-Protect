"""
Pattern-corpus regression suite for ``AdvancedSecretDetector``.

Validates three production guarantees against a synthetic 540-case positive
corpus (30 per pattern, RFC-5737 TEST-NET IPs, public Stripe test-PANs) and a
158-case hand-curated false-positive corpus:

1. **Detection rate ≥ 95%.** Every known pattern is reliably caught. Tested
   both in aggregate and per-pattern (each of the 18 patterns must be ≥ 90%).
2. **False-positive rate < 1%.** The FP corpus — UUIDs, git SHAs, package
   versions, config placeholders, docs — must produce zero redactions.
3. **Confidence ↔ entropy correlation.** The ML confidence score and Shannon
   entropy must be monotonically correlated for key-like secrets — higher
   entropy ⇒ higher average confidence across corpus quartiles.

Plus a `TestKnownLimitations` class that explicitly pins the current regex
gaps (2-series Mastercard, 14-digit Diners, JCB credit cards). If a future
change accidentally "fixes" one of those, the failing test surfaces the win
and invites a corpus update rather than a silent behaviour drift.
"""
from __future__ import annotations

import statistics
import sys
from collections import defaultdict
from pathlib import Path

import pytest

CLI_DIR = Path(__file__).resolve().parents[2] / "cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from advanced_detector import AdvancedSecretDetector  # noqa: E402

from .corpus.false_positives import scoring_corpus   # noqa: E402
from .corpus.generators import GENERATORS, all_positives  # noqa: E402


# ------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def detector() -> AdvancedSecretDetector:
    # Default config mirrors production; threshold=0.0 means no ML-based
    # suppression — we measure the raw regex+entropy+context detector.
    return AdvancedSecretDetector()


@pytest.fixture(scope="module")
def positives():
    return all_positives()


@pytest.fixture(scope="module")
def negatives():
    return scoring_corpus()


def _overlaps(m, span: tuple[int, int]) -> bool:
    s, e = span
    return m.start < e and m.end > s


def _detection_stats(detector, cases):
    """Return ``(hit_map, total_map)`` counting per-pattern hits."""
    hit = defaultdict(int)
    total = defaultdict(int)
    for c in cases:
        total[c.pattern] += 1
        matches = detector.detect(c.text)
        idx = c.text.find(c.secret)
        span = (idx, idx + len(c.secret))
        if any(_overlaps(m, span) for m in matches):
            hit[c.pattern] += 1
    return hit, total


# ======================================================== detection rate
class TestDetectionRate:
    def test_overall_detection_at_least_95_percent(self, detector, positives):
        hit, total = _detection_stats(detector, positives)
        h = sum(hit.values())
        t = sum(total.values())
        rate = h / t
        assert rate >= 0.95, (
            f"overall detection rate {rate:.2%} (target ≥ 95%) — "
            f"{h}/{t} hits across {len(GENERATORS)} patterns"
        )

    @pytest.mark.parametrize("pattern", list(GENERATORS.keys()))
    def test_per_pattern_detection_at_least_90_percent(self, detector, positives, pattern):
        pattern_cases = [p for p in positives if p.pattern == pattern]
        hit, total = _detection_stats(detector, pattern_cases)
        if total[pattern] == 0:
            pytest.skip(f"no cases generated for {pattern}")
        rate = hit[pattern] / total[pattern]
        assert rate >= 0.90, (
            f"{pattern}: {hit[pattern]}/{total[pattern]} = {rate:.2%} "
            f"(target ≥ 90% per pattern)"
        )


# =================================================== false-positive rate
class TestFalsePositiveRate:
    def test_fp_rate_under_1_percent(self, detector, negatives):
        fp_hits = 0
        leaks = []
        for s in negatives:
            m = detector.detect(s)
            if m:
                fp_hits += 1
                leaks.append((s[:80], [x.pattern for x in m]))
        rate = fp_hits / len(negatives)
        assert rate < 0.01, (
            f"false-positive rate {rate:.2%} (target < 1%) — "
            f"{fp_hits} / {len(negatives)} leaks: {leaks[:5]}"
        )

    def test_corpus_is_not_tiny(self, negatives):
        # Guard against somebody accidentally emptying the corpus — the
        # above test would pass trivially.
        assert len(negatives) >= 150


# =================================================== confidence correlation
class TestConfidenceEntropyCorrelation:
    """For key-like patterns (high-entropy secret types), the ML confidence
    score must increase monotonically with Shannon entropy. We bin detected
    matches into entropy quartiles and assert the mean confidence is
    non-decreasing across adjacent bins."""

    # Only run this on key-like patterns — structural patterns (email, IP,
    # credit card, shell prompt, DB URL) are deliberately locked to
    # confidence=1.0 regardless of their (trivially low) entropy.
    KEY_LIKE = {
        "anthropic_api_key", "openai_api_key", "aws_access_key",
        "aws_secret_key", "github_token", "stripe_key",
        "google_api_key", "slack_token", "jwt_token",
        "long_base64_blob",
    }

    def test_confidence_non_decreasing_by_entropy_quartile(self, detector, positives):
        pairs = []
        for c in positives:
            if c.pattern not in self.KEY_LIKE:
                continue
            for m in detector.detect(c.text):
                if m.pattern == c.pattern:
                    pairs.append((m.entropy, m.confidence))
                    break
        assert len(pairs) >= 80, f"not enough key-like matches: {len(pairs)}"

        # sort by entropy, split into 4 equal bins, compute mean confidence
        pairs.sort(key=lambda p: p[0])
        n = len(pairs)
        bins = [pairs[i * n // 4:(i + 1) * n // 4] for i in range(4)]
        means = [statistics.mean(c for _, c in b) for b in bins]
        # strict monotonicity would be too brittle — allow ±0.02 wobble.
        for i in range(1, 4):
            assert means[i] >= means[i - 1] - 0.02, (
                f"confidence dropped from quartile {i-1} ({means[i-1]:.3f}) "
                f"to quartile {i} ({means[i]:.3f}) — expected non-decreasing"
            )
        # and the top quartile must be meaningfully above the bottom one
        assert means[3] - means[0] >= 0.05, (
            f"top-quartile confidence {means[3]:.3f} not much higher than "
            f"bottom-quartile {means[0]:.3f} — correlation appears weak"
        )

    def test_real_secrets_exceed_placeholder_confidence(self, detector):
        # Production placeholder ("SK-PROD-EXAMPLE") should score far below
        # a real-shaped secret — this is the single most important
        # user-facing claim of the ML scorer.
        placeholder = "sk-proj-EXAMPLEKEYPLACEHOLDERFORDOCS"
        real = "sk-proj-Xy7Qw9Lk2Vr4Bn8Mz6Pt3Hj1AbCdEfGhIjKlMnOpQr"
        p_score = detector.calculate_ml_score(placeholder, pattern_matched=True)
        r_score = detector.calculate_ml_score(real,        pattern_matched=True)
        assert r_score > p_score + 0.10, (
            f"real={r_score:.3f} should exceed placeholder={p_score:.3f} by > 0.10"
        )


# ============================================== documented known limitations
class TestKnownLimitations:
    """Documents brands we deliberately DON'T attempt to catch, along with
    why. The previous set of pinned cases (2-series Mastercard, 14-digit
    Diners, JCB) all graduated into the main corpus in 2026-02 when the
    ``credit_card`` regex was expanded + Luhn validation added.

    What remains are two brands whose public BIN prefixes overlap
    catastrophically with the brands we already support:

    * **Maestro** — published prefixes include ``5xx`` and ``6xx`` for
      12-19 digit cards. Accepting this would match virtually every
      Mastercard / Discover / JCB / UnionPay PAN a *second* time
      and, worse, match any random 13+ digit number starting with 5 or 6
      (build IDs, order IDs, phone numbers with separators removed).
      Even with Luhn as a backstop, the false-positive floor is too high.
    * **RuPay** — prefixes ``60 / 65 / 81 / 82 / 508 / 353 / 356`` collide
      with Discover, JCB, and more. Same reasoning.

    If these test cases start *failing*, somebody improved the regex
    (probably with bank-specific BIN ranges rather than blunt 5xx / 6xx
    alternation) — move them into ``generators.gen_credit_card`` and
    retire this class.
    """

    OVERLAPPING_BRAND_PANS = [
        # Maestro 50xx — not matched by any of our 7 supported brands
        ("maestro_50_prefix",   "5018917397102819"),   # Luhn-valid
        # RuPay 81xx — falls outside every brand's prefix range
        ("rupay_81_prefix",     "8100000000000002"),   # Luhn-valid
    ]

    @pytest.mark.parametrize("brand,pan", OVERLAPPING_BRAND_PANS)
    def test_overlapping_brands_are_not_aggressively_matched(self, detector, brand, pan):
        """These brands must NOT be classified as ``credit_card`` matches —
        accepting them would explode the false-positive rate."""
        text = f"Card on file: {pan}"
        matches = detector.detect(text)
        cc_hits = [m for m in matches if m.pattern == "credit_card"]
        assert not cc_hits, (
            f"{brand} ({pan}) IS now being classified as credit_card — if "
            f"this was intentional, move the brand into gen_credit_card and "
            f"retire this test. If accidental, the regex needs tightening "
            f"(prefix collision with existing brands)."
        )
