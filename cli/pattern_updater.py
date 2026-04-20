"""
Vibe Protect — signed dynamic pattern library updater.

Downloads a daily-refreshed pattern bundle from a CDN, verifies its Ed25519
signature against a bundled public key, validates the schema, and caches it
locally. Purely **additive** to the bundled 18 patterns — a compromised CDN
cannot remove or weaken detection, only attempt to add false positives (which
the local user can toggle off in `custom_rules.json`).

Threat model
------------
* **CDN hijack / MITM / tampered TLS intermediary.** Mitigated by Ed25519
  signature over the JSON payload. Attacker must compromise the offline
  private signing key, not just the CDN.
* **Stripped / rolled-back pattern bundle.** Mitigated by a monotonic
  `version` field; we refuse any bundle whose semver is older than the last
  accepted one (stored in `~/.vibeprotect/patterns_meta.json`).
* **Malicious new patterns** (e.g. a regex that is pathologically slow or
  matches everything). Mitigated by (a) built-in regex complexity sniffing
  before we compile and (b) additive-only merge — built-ins always win.
* **CDN unreachable.** Graceful fallback to the local cache, then to the
  bundled 18. No hard dependency on network access.

Public API
----------
    from pattern_updater import PatternLibraryUpdater
    updater = PatternLibraryUpdater()
    updater.update_patterns()        # fetch + verify + save, returns bool
    updater.load_dynamic_patterns()  # merge cache into [(name, regex, …)] list

Opt-in:
    VP_ENABLE_PATTERN_SYNC=1   # default: disabled
    VP_PATTERN_URL=…           # override CDN origin
    VP_SIGNING_PUBKEY_PEM=…    # override bundled public key (PEM)
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# ---------------------------------------------------------------- crypto dep
try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PublicKey,
        Ed25519PrivateKey,
    )
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        PrivateFormat,
        PublicFormat,
        NoEncryption,
    )
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

# ------------------------------------------------------------ configurables
_DEFAULT_CDN = "https://cdn.vibeprotect.com/patterns"
CDN_BASE = os.environ.get("VP_PATTERN_URL") or _DEFAULT_CDN
PATTERNS_URL = f"{CDN_BASE}/latest.json"
SIG_URL = f"{CDN_BASE}/latest.sig"

CACHE_DIR = Path(os.environ.get("VP_CACHE_DIR") or Path.home() / ".vibeprotect")
CACHE_PATTERNS = CACHE_DIR / "patterns.json"
CACHE_META = CACHE_DIR / "patterns_meta.json"
CACHE_PRIVATE_KEY = CACHE_DIR / "signing_key.pem"

MIN_BUNDLE_VERSION = "2.0.0"
THROTTLE_SECONDS = 24 * 60 * 60  # 1 day
REQUEST_TIMEOUT = 6.0
MAX_PATTERNS = 500
MAX_REGEX_LEN = 512

# Placeholder Ed25519 public key. Replace before the first signed release by
# running `python -m pattern_updater generate` (writes signing_key.pem) and
# pasting the printed public-key PEM here — OR set VP_SIGNING_PUBKEY_PEM at
# runtime.
#
# Until replaced, every signature verification will fail and the updater will
# gracefully fall back to the bundled 18 patterns — which is the safe default.
BUNDLED_PUBLIC_KEY_PEM = os.environ.get(
    "VP_SIGNING_PUBKEY_PEM",
    """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
-----END PUBLIC KEY-----
""",
).strip()


# -------------------------------------------------------------- utilities
def _tuple(v: str) -> Tuple[int, int, int]:
    """Lenient semver tuple — mirrors updater._tuple."""
    v = (v or "0.0.0").lstrip("vV").split("-")[0].split("+")[0]
    parts = re.findall(r"\d+", v)
    nums = [int(x) for x in parts[:3]] + [0, 0, 0]
    return tuple(nums[:3])  # type: ignore[return-value]


def _read_meta() -> dict:
    try:
        return json.loads(CACHE_META.read_text())
    except Exception:
        return {}


def _write_meta(meta: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_META.write_text(json.dumps(meta, indent=2))
    except OSError:
        pass


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "vibe-protect/pattern-updater"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return resp.read()


# ------------------------------------------------------------ result dataclass
@dataclass
class UpdateResult:
    ok: bool
    reason: str = ""
    version: str = ""
    added: int = 0
    total: int = 0

    def __str__(self) -> str:
        if self.ok:
            return f"updated to pattern library v{self.version} (+{self.added} new, {self.total} total)"
        return f"skipped: {self.reason}"


# ------------------------------------------------------------ the main class
class PatternLibraryUpdater:
    def __init__(
        self,
        patterns_url: str = PATTERNS_URL,
        sig_url: str = SIG_URL,
        public_key_pem: str = BUNDLED_PUBLIC_KEY_PEM,
        local_path: Path = CACHE_PATTERNS,
    ) -> None:
        self.patterns_url = patterns_url
        self.sig_url = sig_url
        self.public_key_pem = public_key_pem
        self.local_path = Path(local_path)

    # ------------------------------------------------------------ public API
    def update_patterns(self, force: bool = False) -> UpdateResult:
        if os.environ.get("VP_ENABLE_PATTERN_SYNC") != "1" and not force:
            return UpdateResult(False, reason="disabled (set VP_ENABLE_PATTERN_SYNC=1)")

        if not force and not self._throttle_elapsed():
            return UpdateResult(False, reason="throttled (checked <24h ago)")

        if not _HAS_CRYPTO:
            return UpdateResult(False, reason="cryptography library not installed")

        try:
            body = _http_get(self.patterns_url)
            sig = _http_get(self.sig_url)
        except urllib.error.HTTPError as e:
            return UpdateResult(False, reason=f"CDN HTTP {e.code}")
        except Exception as e:
            return UpdateResult(False, reason=f"network: {e}")

        if not self.verify_signature(body, sig, self.public_key_pem):
            return UpdateResult(False, reason="signature verification FAILED — refusing update")

        try:
            bundle = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            return UpdateResult(False, reason=f"malformed JSON: {e}")

        valid, err = self._validate_bundle(bundle)
        if not valid:
            return UpdateResult(False, reason=f"schema: {err}")

        # rollback protection
        last_accepted = _read_meta().get("version", "0.0.0")
        if _tuple(bundle["version"]) < _tuple(last_accepted):
            return UpdateResult(
                False,
                reason=f"rollback rejected (cached v{last_accepted} newer than incoming v{bundle['version']})",
            )

        try:
            self.local_path.parent.mkdir(parents=True, exist_ok=True)
            self.local_path.write_bytes(body)
        except OSError as e:
            return UpdateResult(False, reason=f"cache write: {e}")

        _write_meta({"version": bundle["version"], "fetched_at": time.time()})
        return UpdateResult(
            True,
            reason="signed + validated + written",
            version=bundle["version"],
            added=len(bundle.get("patterns", [])),
            total=len(bundle.get("patterns", [])),
        )

    def load_dynamic_patterns(self) -> List[Tuple[str, str, str, str]]:
        """Return dynamic patterns as (name, regex, description, example).

        Returns an empty list if the cache is missing, corrupt, fails re-validation,
        or sync is not enabled. Callers MUST treat these as additive — never a
        replacement for the bundled static list.
        """
        if not self.local_path.exists():
            return []
        try:
            bundle = json.loads(self.local_path.read_text())
        except Exception:
            return []
        valid, _err = self._validate_bundle(bundle)
        if not valid:
            return []
        out: List[Tuple[str, str, str, str]] = []
        for p in bundle.get("patterns", []):
            name = p.get("name")
            regex = p.get("regex")
            if not name or not regex:
                continue
            if not self._is_safe_regex(regex):
                continue
            out.append((
                f"dyn_{name}",
                regex,
                p.get("description", "") or "(dynamic pattern)",
                p.get("example", "") or "",
            ))
        return out

    # --------------------------------------------------------- verification
    @staticmethod
    def verify_signature(data: bytes, signature: bytes, public_key_pem: str) -> bool:
        """Verify an Ed25519 signature over `data` using a PEM-encoded public key.

        `signature` may be raw 64 bytes or hex/base64 text (we tolerate both).
        """
        if not _HAS_CRYPTO:
            return False
        try:
            pub = load_pem_public_key(public_key_pem.encode("utf-8"))
        except Exception:
            return False
        if not isinstance(pub, Ed25519PublicKey):
            return False

        raw_sig = PatternLibraryUpdater._decode_signature(signature)
        if raw_sig is None:
            return False
        try:
            pub.verify(raw_sig, data)
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False

    @staticmethod
    def _decode_signature(sig: bytes) -> Optional[bytes]:
        """Accept raw, hex, or base64-encoded signatures — Ed25519 is 64 bytes."""
        if sig is None:
            return None
        if isinstance(sig, str):
            sig = sig.encode("utf-8")
        candidates = [sig.strip()]
        # try hex
        try:
            candidates.append(bytes.fromhex(sig.decode("utf-8").strip()))
        except Exception:
            pass
        # try base64
        try:
            import base64

            candidates.append(base64.b64decode(sig.decode("utf-8").strip(), validate=False))
        except Exception:
            pass
        for c in candidates:
            if isinstance(c, bytes) and len(c) == 64:
                return c
        return None

    # -------------------------------------------------------- schema & safety
    @staticmethod
    def _validate_bundle(bundle: dict) -> Tuple[bool, str]:
        if not isinstance(bundle, dict):
            return False, "top-level not object"
        if "version" not in bundle or "patterns" not in bundle:
            return False, "missing version/patterns"
        if _tuple(bundle["version"]) < _tuple(MIN_BUNDLE_VERSION):
            return False, f"version below minimum {MIN_BUNDLE_VERSION}"
        patterns = bundle["patterns"]
        if not isinstance(patterns, list):
            return False, "patterns must be a list"
        if len(patterns) > MAX_PATTERNS:
            return False, f"too many patterns (>{MAX_PATTERNS})"
        for i, p in enumerate(patterns):
            if not isinstance(p, dict):
                return False, f"patterns[{i}] not object"
            if not isinstance(p.get("name"), str) or not isinstance(p.get("regex"), str):
                return False, f"patterns[{i}] missing name/regex"
            if len(p["regex"]) > MAX_REGEX_LEN:
                return False, f"patterns[{i}] regex too long"
        return True, ""

    @staticmethod
    def _is_safe_regex(regex: str) -> bool:
        """Reject obviously catastrophic regexes before compile.

        This is heuristic — not a proof of non-backtracking — but it catches
        the common 'nested quantifier' and 'alternation in quantifier' shapes
        that tend to ReDoS.
        """
        if len(regex) > MAX_REGEX_LEN:
            return False
        # catastrophic patterns: (x+)+, (x|x)*, (.*)*, etc.
        bad = [
            r"\([^)]*\+\)\s*\+",
            r"\([^)]*\*\)\s*\*",
            r"\([^)]*\|\s*[^)]*\)\s*[+*]\s*[+*]",
        ]
        for b in bad:
            if re.search(b, regex):
                return False
        # ensure it compiles — if not, reject
        try:
            re.compile(regex)
        except re.error:
            return False
        return True

    # ---------------------------------------------------------------- util
    def _throttle_elapsed(self) -> bool:
        meta = _read_meta()
        last = float(meta.get("fetched_at", 0))
        return (time.time() - last) >= THROTTLE_SECONDS


# --------------------------------------------- developer helper: keypair gen
def generate_signing_keypair(out_dir: Path = CACHE_DIR) -> Tuple[Path, str]:
    """Create an Ed25519 keypair for signing pattern bundles. Writes the
    private key to `out_dir/signing_key.pem` (keep this offline!) and returns
    the matching PEM public key as a string so you can paste it into
    BUNDLED_PUBLIC_KEY_PEM or VP_SIGNING_PUBKEY_PEM.
    """
    if not _HAS_CRYPTO:
        raise RuntimeError("cryptography package is required — pip install cryptography")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    priv = Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    (out_dir / "signing_key.pem").write_bytes(priv_pem)
    pub_pem = priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    return out_dir / "signing_key.pem", pub_pem.decode("utf-8")


def sign_bundle(bundle_bytes: bytes, private_key_path: Path = CACHE_PRIVATE_KEY) -> bytes:
    """Sign a pattern bundle with the private key and return a hex signature."""
    if not _HAS_CRYPTO:
        raise RuntimeError("cryptography package is required")
    priv_pem = Path(private_key_path).read_bytes()
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    priv = load_pem_private_key(priv_pem, password=None)
    if not isinstance(priv, Ed25519PrivateKey):
        raise RuntimeError("not an Ed25519 private key")
    sig = priv.sign(bundle_bytes)
    return sig.hex().encode("utf-8")


# ---------------------------------------------------------------- CLI entry
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        priv_path, pub_pem = generate_signing_keypair()
        print(f"✓ private key written to {priv_path} — KEEP THIS OFFLINE.")
        print()
        print("# Paste the block below into pattern_updater.BUNDLED_PUBLIC_KEY_PEM")
        print("# (or set VP_SIGNING_PUBKEY_PEM at runtime):")
        print()
        print(pub_pem)
    elif len(sys.argv) > 1 and sys.argv[1] == "sign":
        if len(sys.argv) < 3:
            print("usage: python pattern_updater.py sign <bundle.json>")
            sys.exit(2)
        data = Path(sys.argv[2]).read_bytes()
        print(sign_bundle(data).decode("utf-8"))
    else:
        result = PatternLibraryUpdater().update_patterns(force=True)
        print(result)


__all__ = [
    "PatternLibraryUpdater",
    "UpdateResult",
    "generate_signing_keypair",
    "sign_bundle",
]
