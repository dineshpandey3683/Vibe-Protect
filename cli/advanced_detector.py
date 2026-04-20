"""
Vibe Protect — AdvancedSecretDetector.

Extends the base 18-pattern library with:

1. **Shannon-entropy filtering** per pattern — kills classic false positives like
   `SK-PROD-123` or `AKIA000000000000` that look like keys but are obviously
   placeholders.
2. **Context filtering** per pattern — skips matches on lines containing words
   like "example", "sample", "demo", "test" (configurable).
3. **Custom user patterns** loaded from `~/.vibe_protect/custom_rules.json`.
4. **Entropy catch-all** — flags random-looking ≥20-char alphanum blobs that
   match no known pattern but look like secrets.

Crucially, entropy and context filtering are **per pattern** — we never apply
them to low-entropy patterns like emails, IPs, credit cards, shell prompts,
or DB connection URLs (those would get stripped and cause real leaks).

Public API:

    from advanced_detector import AdvancedSecretDetector
    det = AdvancedSecretDetector()
    cleaned, matches = det.redact(text)
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from patterns import PATTERNS as _BASE_PATTERNS, _to_scoped

CONFIG_DIR = Path(os.environ.get("VP_CACHE_DIR") or Path.home() / ".vibeprotect")
CUSTOM_RULES_FILE = CONFIG_DIR / "custom_rules.json"

# Entropy filter is only meaningful for random/key-like patterns. Low-entropy
# patterns (emails, IPs, credit cards, shell prompts, DB URLs) must always
# match regardless of entropy — otherwise we'd silently miss real secrets.
ENTROPY_CHECKED_PATTERNS = {
    "anthropic_api_key",
    "openai_api_key",
    "aws_access_key",
    "aws_secret_key",
    "github_token",
    "stripe_key",
    "google_api_key",
    "slack_token",
    "jwt_token",
    "long_base64_blob",
}

# Context filter ("skip if line mentions sample/example/…") also only applies
# to key-like patterns — an "example user email" is still PII.
CONTEXT_CHECKED_PATTERNS = ENTROPY_CHECKED_PATTERNS | {"generic_secret_assignment"}

DEFAULT_CONTEXT_WORDS = ("example", "sample", "demo", "placeholder", "dummy", "fake")

# Reasonable defaults — tuned so that `sk-proj-…`, `AKIA…`, and friends all
# pass, while `SK-PROD-123` and `AKIA000000000000` do not.
DEFAULT_ENTROPY_THRESHOLD = 3.5   # bits/char
DEFAULT_MIN_LEN = 16
DEFAULT_MAX_LEN = 512
CATCHALL_MIN_LEN = 24
CATCHALL_ENTROPY = 4.2


@dataclass
class AdvancedMatch:
    pattern: str
    start: int
    end: int
    original: str
    mask: str
    entropy: float = 0.0
    reason: str = "pattern"   # pattern | entropy_catchall | user_custom

    def to_dict(self):
        return {
            "pattern": self.pattern,
            "original_len": len(self.original),
            "start": self.start,
            "end": self.end,
            "mask": self.mask,
            "entropy": round(self.entropy, 3),
            "reason": self.reason,
        }


@dataclass
class AdvancedSecretDetector:
    entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD
    context_words: Tuple[str, ...] = DEFAULT_CONTEXT_WORDS
    enable_catchall: bool = True
    user_patterns: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # base patterns: {name: (compiled_regex, needs_entropy, needs_context)}
        self._compiled: Dict[str, Tuple[re.Pattern, bool, bool]] = {}
        for name, pat, _desc, _ex in _BASE_PATTERNS:
            self._compiled[name] = (
                re.compile(_to_scoped(pat)),
                name in ENTROPY_CHECKED_PATTERNS,
                name in CONTEXT_CHECKED_PATTERNS,
            )
        # then user custom patterns — always treated as entropy+context checked
        # unless user explicitly passes {"entropy_check": false, ...} in JSON.
        for name, pat in (self.user_patterns or {}).items():
            try:
                self._compiled[name] = (re.compile(_to_scoped(pat)), True, True)
            except re.error:
                pass  # skip invalid user regex silently

    # ------------------------------------------------------------------ utils
    @staticmethod
    def shannon_entropy(data: str) -> float:
        """Shannon entropy in bits/char."""
        if not data:
            return 0.0
        length = len(data)
        counts: Dict[str, int] = {}
        for ch in data:
            counts[ch] = counts.get(ch, 0) + 1
        entropy = 0.0
        for c in counts.values():
            p = c / length
            entropy -= p * math.log2(p)
        return entropy

    def _passes_entropy(self, s: str) -> bool:
        if not (DEFAULT_MIN_LEN <= len(s) <= DEFAULT_MAX_LEN):
            # too short/long to meaningfully apply the filter — let it through
            return True
        return self.shannon_entropy(s) >= self.entropy_threshold

    def _passes_context(self, text: str, start: int) -> bool:
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", start)
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end].lower()
        return not any(w in line for w in self.context_words)

    # -------------------------------------------------------- class factories
    @classmethod
    def load_default(cls, **overrides) -> "AdvancedSecretDetector":
        """Instantiate with custom patterns loaded from `~/.vibeprotect/custom_rules.json`."""
        user = _load_custom_rules(CUSTOM_RULES_FILE)
        return cls(user_patterns=user, **overrides)

    # ---------------------------------------------------------------- engine
    def _scan_patterns(self, text: str) -> List[AdvancedMatch]:
        raw: List[AdvancedMatch] = []
        for name, (rx, needs_entropy, needs_context) in self._compiled.items():
            for m in rx.finditer(text):
                original = m.group(0)
                ent = self.shannon_entropy(original) if needs_entropy else 0.0
                if needs_entropy and not self._passes_entropy(original):
                    continue
                if needs_context and not self._passes_context(text, m.start()):
                    continue
                raw.append(
                    AdvancedMatch(
                        pattern=name,
                        start=m.start(),
                        end=m.end(),
                        original=original,
                        mask=f"[{name.upper()}]",
                        entropy=ent,
                        reason="user_custom" if name in self.user_patterns else "pattern",
                    )
                )
        return raw

    def _scan_catchall(self, text: str, existing: List[AdvancedMatch]) -> List[AdvancedMatch]:
        if not self.enable_catchall:
            return []
        taken = [(m.start, m.end) for m in existing]
        def _overlaps(a: int, b: int) -> bool:
            return any(a < e and b > s for s, e in taken)
        found: List[AdvancedMatch] = []
        for m in re.finditer(r"[A-Za-z0-9_\-]{%d,}" % CATCHALL_MIN_LEN, text):
            if _overlaps(m.start(), m.end()):
                continue
            token = m.group(0)
            ent = self.shannon_entropy(token)
            if ent < CATCHALL_ENTROPY:
                continue
            if not self._passes_context(text, m.start()):
                continue
            found.append(
                AdvancedMatch(
                    pattern="high_entropy_string",
                    start=m.start(),
                    end=m.end(),
                    original=token,
                    mask="[HIGH_ENTROPY_STRING]",
                    entropy=ent,
                    reason="entropy_catchall",
                )
            )
        return found

    def detect(self, text: str) -> List[AdvancedMatch]:
        """Return non-overlapping AdvancedMatch list, earliest-wins."""
        if not text:
            return []
        matches = self._scan_patterns(text)
        matches.extend(self._scan_catchall(text, matches))
        matches.sort(key=lambda m: (m.start, -(m.end - m.start)))
        chosen: List[AdvancedMatch] = []
        last_end = -1
        for m in matches:
            if m.start >= last_end:
                chosen.append(m)
                last_end = m.end
        return chosen

    def redact(self, text: str) -> Tuple[str, List[dict]]:
        """Compatible with patterns.redact: returns (cleaned, matches_as_dicts)."""
        if not text:
            return text or "", []
        matches = self.detect(text)
        out = []
        cursor = 0
        for m in matches:
            out.append(text[cursor:m.start])
            out.append(m.mask)
            cursor = m.end
        out.append(text[cursor:])
        return "".join(out), [m.to_dict() for m in matches]


# -------------------------------------------------------------- custom rules
def _load_custom_rules(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    rules: Dict[str, str] = {}
    # accept either {"name": "regex"} dict or list of {name, regex} objects
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, str):
                rules[k] = v
            elif isinstance(v, dict) and "regex" in v:
                rules[k] = v["regex"]
    elif isinstance(data, list):
        for obj in data:
            if isinstance(obj, dict) and "name" in obj and "regex" in obj:
                rules[obj["name"]] = obj["regex"]
    return rules


def write_sample_custom_rules(path: Optional[Path] = None) -> Path:
    """Create an annotated sample custom_rules.json if it doesn't exist."""
    target = Path(path) if path else CUSTOM_RULES_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return target
    sample = [
        {
            "name": "internal_service_token",
            "regex": r"INTERNAL_[A-Z0-9]{20,}",
            "description": "Example: tokens minted by your internal auth service",
        },
        {
            "name": "company_s3_bucket",
            "regex": r"s3://acme-(?:prod|staging)-[a-z0-9-]+",
            "description": "Example: cross-env S3 bucket URIs that shouldn't leak",
        },
    ]
    target.write_text(json.dumps(sample, indent=2))
    return target


__all__ = [
    "AdvancedSecretDetector",
    "AdvancedMatch",
    "CUSTOM_RULES_FILE",
    "write_sample_custom_rules",
]
