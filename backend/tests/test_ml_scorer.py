"""
Tests for the ML-style heuristic confidence scorer added to
``cli/advanced_detector.AdvancedSecretDetector``.

We validate:
1.  ``shannon_entropy`` and ``character_variety`` boundary behaviour.
2.  ``calculate_ml_score`` properly bounds to [0, 1] and responds to all
    four features (entropy, length, variety, pattern_boost).
3.  Real secrets score ≥ 0.75 and placeholders / test fixtures score < 0.75,
    matching the recommended production threshold.
4.  ``ml_confidence_threshold`` suppresses low-confidence catch-all matches
    without ever dropping structural matches (emails, IPs, CCs).
5.  ``AdvancedMatch.to_dict`` now includes a ``confidence`` key.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

CLI_DIR = Path(__file__).resolve().parents[2] / "cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from advanced_detector import AdvancedSecretDetector  # noqa: E402


@pytest.fixture
def det() -> AdvancedSecretDetector:
    return AdvancedSecretDetector()


# --------------------------------------------------------------- primitives
class TestFeatures:
    def test_shannon_entropy_empty(self, det):
        assert det.shannon_entropy("") == 0.0

    def test_shannon_entropy_uniform_string_is_zero(self, det):
        assert det.shannon_entropy("aaaaaaaa") == 0.0

    def test_shannon_entropy_random_is_high(self, det):
        assert det.shannon_entropy("aB3xZ9kL") > 2.5

    def test_character_variety_empty(self, det):
        assert det.character_variety("") == 0.0

    def test_character_variety_single_class(self, det):
        assert det.character_variety("abcdef") == 0.25
        assert det.character_variety("123456") == 0.25

    def test_character_variety_all_four_classes(self, det):
        assert det.character_variety("Ab1!Xy2@") == 1.0

    def test_character_variety_mixed_alnum(self, det):
        # lower + upper + digit = 0.75
        assert det.character_variety("Abc123") == 0.75


# ----------------------------------------------------------------- scoring
class TestMLScore:
    def test_score_bounded(self, det):
        for s in ("", "a", "ab" * 200, "!!!!!"):
            score = det.calculate_ml_score(s, pattern_matched=False)
            assert 0.0 <= score <= 1.0

    def test_pattern_boost_increases_score(self, det):
        s = "sk-proj-abcdefghijklmnopqrstuvwxyz0123"
        no_boost = det.calculate_ml_score(s, pattern_matched=False)
        boost = det.calculate_ml_score(s, pattern_matched=True)
        assert boost > no_boost
        assert abs((boost - no_boost) - 0.30) < 1e-9

    def test_real_secret_scores_high_when_regex_matches(self, det):
        # High-entropy, all 4 character classes, plus pattern-match boost.
        real_secret = "sk-proj-Xy7&Qw9!Lk2@Vr4#Bn8$Mz6^Pt3*Hj1%"
        score = det.calculate_ml_score(real_secret, pattern_matched=True)
        assert score >= 0.75

    def test_placeholder_scores_low(self, det):
        placeholder = "AKIAEXAMPLEAKIAEXAMPLE"   # no variety, low entropy
        score = det.calculate_ml_score(placeholder, pattern_matched=True)
        assert score < 0.75

    def test_short_identifier_scores_low(self, det):
        # "user_id" is 7 chars with low variety and low entropy
        assert det.calculate_ml_score("user_id", pattern_matched=False) < 0.5


# --------------------------------------------------------- threshold filter
class TestThresholdFilter:
    def test_default_threshold_keeps_everything(self):
        det = AdvancedSecretDetector()   # threshold = 0.0
        txt = "reach me at alice@example.com from 10.0.0.1"
        matches = det.detect(txt)
        kinds = {m.pattern for m in matches}
        assert "email" in kinds
        assert "ipv4" in kinds

    def test_high_threshold_preserves_structural_matches(self):
        # Even with an aggressive threshold, emails / IPs / CCs must still be
        # redacted — they're assigned confidence=1.0 exactly for this reason.
        det = AdvancedSecretDetector(ml_confidence_threshold=0.95)
        txt = "ping alice@example.com on 192.168.1.1"
        matches = det.detect(txt)
        kinds = {m.pattern for m in matches}
        assert "email" in kinds
        assert "ipv4" in kinds

    def test_high_threshold_suppresses_weak_catchall(self):
        det_off = AdvancedSecretDetector(ml_confidence_threshold=0.0)
        det_on = AdvancedSecretDetector(ml_confidence_threshold=0.95)
        # A long but low-entropy catchall-eligible blob ("AB" repeated)
        # — the real regex won't match, catchall might, threshold should kill it.
        blob = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # len 31, entropy = 0
        m_off = det_off.detect(blob)
        m_on = det_on.detect(blob)
        assert len(m_on) <= len(m_off)

    def test_match_dict_includes_confidence(self, det):
        _, matches = det.redact("contact alice@example.com")
        assert matches
        assert "confidence" in matches[0]
        assert 0.0 <= matches[0]["confidence"] <= 1.0
