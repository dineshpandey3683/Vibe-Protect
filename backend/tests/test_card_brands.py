"""
Tests for the per-brand credit-card classifier added to
``advanced_detector.classify_card_brand`` and wired into
``AdvancedMatch.mask``.

Each Luhn-verified PAN must redact to a brand-specific tag (`[VISA]`,
`[MC]`, `[AMEX]`, `[DISCOVER]`, `[DINERS]`, `[JCB]`, `[UNIONPAY]`) so
audit logs surface brand-level telemetry without exposing the PAN.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

CLI_DIR = Path(__file__).resolve().parents[2] / "cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from advanced_detector import AdvancedSecretDetector, classify_card_brand  # noqa: E402


@pytest.fixture(scope="module")
def det() -> AdvancedSecretDetector:
    return AdvancedSecretDetector()


# Every PAN below is Luhn-valid and comes from public payment-processor
# test documentation — no real cardholder data.
CASES = [
    # Visa
    ("4242424242424242",   "VISA"),
    ("4000056655665556",   "VISA"),
    # Mastercard 5-series (legacy)
    ("5555555555554444",   "MC"),
    ("5200828282828210",   "MC"),
    # Mastercard 2-series (2221-2720, activated 2016+)
    ("2223003122003222",   "MC"),
    ("2223000048400011",   "MC"),
    # American Express
    ("378282246310005",    "AMEX"),
    ("371449635398431",    "AMEX"),
    # Discover
    ("6011111111111117",   "DISCOVER"),
    ("6011000990139424",   "DISCOVER"),
    # Diners Club (14-digit)
    ("30569309025904",     "DINERS"),
    ("38520000023237",     "DINERS"),
    # JCB
    ("3566002020360505",   "JCB"),
    ("3530111333300000",   "JCB"),
    # UnionPay
    ("6200000000000005",   "UNIONPAY"),
    ("6250947000000014",   "UNIONPAY"),
]


class TestClassifierPure:
    @pytest.mark.parametrize("pan,expected", CASES)
    def test_classifier_returns_expected_brand(self, pan, expected):
        assert classify_card_brand(pan) == expected


class TestMaskEndToEnd:
    @pytest.mark.parametrize("pan,expected", CASES)
    def test_detector_mask_is_brand_specific(self, det, pan, expected):
        text = f"Card on file: {pan}"
        matches = det.detect(text)
        cc = [m for m in matches if m.pattern == "credit_card"]
        assert cc, f"{pan} not detected as credit_card"
        assert cc[0].mask == f"[{expected}]", (
            f"{pan} should mask as [{expected}] but got {cc[0].mask}"
        )

    def test_non_credit_card_masks_unchanged(self, det):
        """Sanity-check that other patterns still use their default mask."""
        text = "contact alice@example.com from 10.0.0.1"
        matches = det.detect(text)
        masks = {m.pattern: m.mask for m in matches}
        assert masks.get("email") == "[EMAIL]"
        assert masks.get("ipv4") == "[IPV4]"


class TestClassifierFallback:
    def test_unknown_prefix_falls_back(self):
        # A 16-digit Luhn-valid number whose prefix doesn't match any
        # of our supported brands — shouldn't classify, gets CREDIT_CARD.
        assert classify_card_brand("9999999999999995") == "CREDIT_CARD"
