"""
Vibe Protect — community rules fetcher.

Pulls a PR-gated pattern list from a public GitHub repo. Trust here is rooted
in the *repo moderation process* (maintainers review every PR before merge),
not in an offline-signed bundle like `pattern_updater.py`. Community rules
therefore land under a separate `community_` namespace and are **strictly
additive, strictly opt-in, and strictly lower-priority** than bundled + signed
patterns — a compromised or misbehaving community pattern can only add false
positives, never weaken existing protection.

Public API
----------
    from community_rules import CommunityRulesFetcher
    f = CommunityRulesFetcher()
    f.sync()                    # fetch + validate + cache, returns Result
    f.load_patterns()           # -> [(name, regex, desc, ex), ...] for merging

Opt-in
------
    VP_ENABLE_COMMUNITY_RULES=1    # default: disabled
    VP_COMMUNITY_RULES_URL=…       # override repo URL
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from pattern_updater import PatternLibraryUpdater  # reuse schema + safety checks

DEFAULT_URL = (
    "https://raw.githubusercontent.com/vibeprotect/community-rules/main/approved_patterns.json"
)
COMMUNITY_RULES_URL = os.environ.get("VP_COMMUNITY_RULES_URL") or DEFAULT_URL

CACHE_DIR = Path(os.environ.get("VP_CACHE_DIR") or Path.home() / ".vibeprotect")
CACHE_FILE = CACHE_DIR / "community_rules.json"
CACHE_META = CACHE_DIR / "community_rules_meta.json"

THROTTLE_SECONDS = 24 * 60 * 60  # 1 day
REQUEST_TIMEOUT = 6.0
MAX_COMMUNITY_PATTERNS = 200   # stricter than signed bundle


@dataclass
class SyncResult:
    ok: bool
    reason: str = ""
    added: int = 0
    version: str = ""

    def __str__(self) -> str:
        return (
            f"community rules v{self.version}: +{self.added} (✓)"
            if self.ok
            else f"community rules skipped: {self.reason}"
        )


class CommunityRulesFetcher:
    def __init__(
        self,
        url: str = COMMUNITY_RULES_URL,
        cache_path: Path = CACHE_FILE,
        meta_path: Path = CACHE_META,
    ) -> None:
        self.url = url
        self.cache_path = Path(cache_path)
        self.meta_path = Path(meta_path)

    # ------------------------------------------------------------ public API
    def sync(self, force: bool = False) -> SyncResult:
        if os.environ.get("VP_ENABLE_COMMUNITY_RULES") != "1" and not force:
            return SyncResult(False, reason="disabled (set VP_ENABLE_COMMUNITY_RULES=1)")

        if not force and not self._throttle_elapsed():
            return SyncResult(False, reason="throttled (checked <24h ago)")

        try:
            req = urllib.request.Request(
                self.url,
                headers={
                    "User-Agent": "vibe-protect/community-rules",
                    "Accept": "application/json",
                    **self._conditional_headers(),
                },
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                body = resp.read()
                etag = resp.headers.get("ETag", "")
        except urllib.error.HTTPError as e:
            if e.code == 304:
                return SyncResult(False, reason="not modified (304)")
            return SyncResult(False, reason=f"HTTP {e.code}")
        except Exception as e:
            return SyncResult(False, reason=f"network: {e}")

        try:
            bundle = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            return SyncResult(False, reason=f"malformed JSON: {e}")

        ok, err = self._validate(bundle)
        if not ok:
            return SyncResult(False, reason=f"schema: {err}")

        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_bytes(body)
            self._write_meta({"fetched_at": time.time(), "etag": etag, "version": bundle.get("version", "")})
        except OSError as e:
            return SyncResult(False, reason=f"cache write: {e}")

        return SyncResult(
            True,
            reason="ok",
            added=len(bundle.get("patterns", [])),
            version=bundle.get("version", "?"),
        )

    def load_patterns(self) -> List[Tuple[str, str, str, str]]:
        """Return community patterns as (name, regex, description, example)."""
        if not self.cache_path.exists():
            return []
        try:
            bundle = json.loads(self.cache_path.read_text())
        except Exception:
            return []
        ok, _ = self._validate(bundle)
        if not ok:
            return []
        out: List[Tuple[str, str, str, str]] = []
        for p in bundle.get("patterns", []):
            name = p.get("name")
            regex = p.get("regex")
            if not name or not regex:
                continue
            if not PatternLibraryUpdater._is_safe_regex(regex):
                continue
            # prefix aggressively — community rules are always distinguishable
            out.append((
                f"community_{name}",
                regex,
                p.get("description", "(community-submitted pattern)"),
                p.get("example", ""),
            ))
        return out

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _validate(bundle: dict) -> Tuple[bool, str]:
        # we intentionally reuse PatternLibraryUpdater's validator, then layer
        # a stricter per-pattern cap on top
        ok, err = PatternLibraryUpdater._validate_bundle(bundle)
        if not ok:
            return ok, err
        if len(bundle.get("patterns", [])) > MAX_COMMUNITY_PATTERNS:
            return False, f"too many patterns (>{MAX_COMMUNITY_PATTERNS})"
        return True, ""

    def _throttle_elapsed(self) -> bool:
        try:
            meta = json.loads(self.meta_path.read_text())
            return (time.time() - float(meta.get("fetched_at", 0))) >= THROTTLE_SECONDS
        except Exception:
            return True

    def _conditional_headers(self) -> dict:
        try:
            meta = json.loads(self.meta_path.read_text())
            etag = meta.get("etag")
            if etag:
                return {"If-None-Match": etag}
        except Exception:
            pass
        return {}

    def _write_meta(self, meta: dict) -> None:
        try:
            self.meta_path.parent.mkdir(parents=True, exist_ok=True)
            self.meta_path.write_text(json.dumps(meta, indent=2))
        except OSError:
            pass


__all__ = ["CommunityRulesFetcher", "SyncResult", "COMMUNITY_RULES_URL"]


# -------------------------------------------------------------- CLI entry
if __name__ == "__main__":
    result = CommunityRulesFetcher().sync(force=True)
    print(result)
