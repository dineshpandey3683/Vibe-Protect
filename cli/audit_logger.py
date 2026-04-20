"""
Vibe Protect — encrypted audit log.

Produces an at-rest-encrypted, tamper-evident audit trail suitable for SOC2 /
HIPAA / GDPR evidence collection. We deliberately never store the plaintext
of redacted secrets; entries only ever contain the pattern NAME, counts, and
character-length deltas.

Cryptographic design
--------------------
* Master key material: a per-install 32-byte value stored in
  ``~/.vibeprotect/audit/.audit_key`` (chmod 600 where supported). The first
  time the process runs it's derived via PBKDF2-HMAC-SHA256 from
  ``hostname + username + app`` with 200k iterations and a freshly-generated
  salt — the salt is persisted alongside the key so the derivation is
  reproducible if the file is ever deleted and the caller has the same
  identity.
* From that master we derive two sub-keys via HKDF-SHA256 with separate
  info strings:
    - ``vibe-protect/audit/enc``  — AES-256-GCM encryption
    - ``vibe-protect/audit/mac``  — HMAC-SHA256 for tamper detection
* AES-256-GCM already provides authentication, but we additionally attach an
  HMAC over the sort-keyed JSON payload so the audit trail stays verifiable
  even if the ciphertext is later copied into a different container.

Disclaimer
----------
The algorithms used (AES-256-GCM, HMAC-SHA256, PBKDF2, HKDF) are all FIPS-approved,
but true FIPS 140-2 compliance requires running against a validated crypto
module (RHEL FIPS mode, Microsoft CNG, BoringCrypto, etc.). We describe this
module as "uses FIPS-approved algorithms" rather than "FIPS certified".

Public API
----------
    from audit_logger import AuditLogger, EventType, Action
    a = AuditLogger()
    a.log(EventType.REDACTION, secret_type="openai_api_key", action=Action.SCRUBBED)
    a.query(start_date=..., event_type=EventType.REDACTION)
    a.generate_compliance_report(output_format="json")
"""

from __future__ import annotations

import base64
import getpass
import hashlib
import hmac as hmac_mod
import json
import os
import platform
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False


APP_NAME = "vibe_protect"
APP_VERSION = "2.0.0"
PBKDF2_ITERATIONS = 200_000
AUDIT_TRAIL_CAP = 2000  # cap in-memory trail; disk is source of truth


# ----------------------------------------------------------- enums / helpers
class EventType(str, Enum):
    REDACTION = "REDACTION"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    PATTERN_SYNC = "PATTERN_SYNC"
    STARTUP = "STARTUP"
    SHUTDOWN = "SHUTDOWN"
    TAMPER_DETECTED = "TAMPER_DETECTED"


class Action(str, Enum):
    SCRUBBED = "SCRUBBED"
    BLOCKED = "BLOCKED"
    ALLOWED = "ALLOWED"
    INFO = "INFO"


def _default_dir() -> Path:
    base = os.environ.get("VP_CACHE_DIR") or (Path.home() / f".{APP_NAME}")
    return Path(base) / "audit"


@dataclass
class TamperReport:
    total: int = 0
    good: int = 0
    tampered: List[str] = None  # list of line references "<file>:<lineno>"

    def __post_init__(self):
        if self.tampered is None:
            self.tampered = []


# --------------------------------------------------------------- the class
class AuditLogger:
    def __init__(
        self,
        app_name: str = APP_NAME,
        log_dir: Optional[Path] = None,
        max_trail: int = AUDIT_TRAIL_CAP,
    ):
        if not _HAS_CRYPTO:
            raise RuntimeError(
                "cryptography is required for the audit logger — pip install cryptography"
            )
        self.app_name = app_name
        self.log_dir = Path(log_dir) if log_dir else _default_dir()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._restrict(self.log_dir, is_dir=True)

        self._enc_key, self._mac_key = self._get_or_create_keys()

        self.audit_trail: List[dict] = []
        self.max_trail = max_trail

    # ----------------------------------------------------------- file paths
    @property
    def current_log_file(self) -> Path:
        """One encrypted log file per calendar month (easy rotation)."""
        return self.log_dir / f"audit_{datetime.now(timezone.utc).strftime('%Y%m')}.log.enc"

    @property
    def _key_file(self) -> Path:
        return self.log_dir / ".audit_key"

    @property
    def _salt_file(self) -> Path:
        return self.log_dir / ".audit_salt"

    # ------------------------------------------------------------ key mgmt
    def _get_or_create_keys(self) -> tuple:
        """Return (enc_key, mac_key) — 32 bytes each."""
        if self._key_file.exists():
            master = base64.b64decode(self._key_file.read_bytes())
        else:
            master = self._derive_master()
            self._key_file.write_bytes(base64.b64encode(master))
            self._restrict(self._key_file)

        enc = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"vibe-protect/audit/enc",
        ).derive(master)
        mac = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"vibe-protect/audit/mac",
        ).derive(master)
        return enc, mac

    def _derive_master(self) -> bytes:
        """One-time derivation seeded by stable-ish local identity + salt."""
        if self._salt_file.exists():
            salt = self._salt_file.read_bytes()
        else:
            salt = os.urandom(32)
            self._salt_file.write_bytes(salt)
            self._restrict(self._salt_file)

        identity = f"{platform.node()}:{getpass.getuser()}:{self.app_name}".encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return kdf.derive(identity)

    @staticmethod
    def _restrict(path: Path, is_dir: bool = False):
        """chmod 600 / 700 where the filesystem supports it."""
        try:
            mode = stat.S_IRWXU if is_dir else (stat.S_IRUSR | stat.S_IWUSR)
            os.chmod(path, mode)
        except (OSError, NotImplementedError):
            pass  # Windows / restricted FSes — best-effort

    # --------------------------------------------------------------- crypto
    def _encrypt(self, plaintext: bytes) -> str:
        """AES-256-GCM → base64(nonce || tag || ciphertext)."""
        aesgcm = AESGCM(self._enc_key)
        nonce = os.urandom(12)
        # AESGCM returns ciphertext || tag (tag is 16 bytes at the end)
        ct_tag = aesgcm.encrypt(nonce, plaintext, associated_data=None)
        return base64.b64encode(nonce + ct_tag).decode("ascii")

    def _decrypt(self, blob: str) -> bytes:
        raw = base64.b64decode(blob)
        nonce, ct_tag = raw[:12], raw[12:]
        return AESGCM(self._enc_key).decrypt(nonce, ct_tag, associated_data=None)

    def _compute_hmac(self, entry_without_hmac: dict) -> str:
        payload = json.dumps(entry_without_hmac, sort_keys=True, separators=(",", ":")).encode()
        return hmac_mod.new(self._mac_key, payload, hashlib.sha256).hexdigest()

    # ----------------------------------------------------------------- log
    def log(
        self,
        event_type: EventType,
        secret_type: str = "",
        action: Action = Action.INFO,
        metadata: Optional[Dict] = None,
    ) -> dict:
        """Append an audit entry. Never stores the plaintext of any secret."""
        entry = {
            "version": APP_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": EventType(event_type).value,
            "secret_type": secret_type or "",
            "action": Action(action).value,
            "user": self._safe_user(),
            "hostname": platform.node(),
            "pid": os.getpid(),
            "metadata": self._sanitise_metadata(metadata or {}),
        }
        entry["hmac"] = self._compute_hmac(entry)

        encrypted = self._encrypt(json.dumps(entry, separators=(",", ":")).encode())
        try:
            with self.current_log_file.open("a", encoding="utf-8") as f:
                f.write(encrypted + "\n")
            self._restrict(self.current_log_file)
        except OSError as e:
            print(f"[vibe-protect] audit write failed: {e}", file=sys.stderr)

        self.audit_trail.append(entry)
        if len(self.audit_trail) > self.max_trail:
            self.audit_trail = self.audit_trail[-self.max_trail:]
        return entry

    @staticmethod
    def _safe_user() -> str:
        try:
            return getpass.getuser()
        except Exception:
            return os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"

    @staticmethod
    def _sanitise_metadata(md: Dict) -> Dict:
        """Strip any fields that look like they might contain secret *content*
        — the audit log is a privacy-sensitive artifact, not a capture file."""
        FORBIDDEN = {"original", "plaintext", "clipboard_text", "cleaned_text", "secret", "raw"}
        return {k: v for k, v in md.items() if k not in FORBIDDEN}

    # ------------------------------------------------------------- queries
    def query(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[EventType] = None,
        verify: bool = True,
    ) -> List[dict]:
        """Return decrypted, HMAC-verified entries matching the filters.

        Tampered entries are silently skipped AND cause a
        ``TAMPER_DETECTED`` event to be recorded.
        """
        results: List[dict] = []
        report = TamperReport()
        for log_file in sorted(self.log_dir.glob("audit_*.log.enc")):
            with log_file.open("r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        plaintext = self._decrypt(line)
                        entry = json.loads(plaintext.decode("utf-8"))
                    except Exception:
                        report.tampered.append(f"{log_file.name}:{line_no} (decrypt)")
                        continue
                    report.total += 1
                    stored_hmac = entry.pop("hmac", "")
                    if verify:
                        expected = self._compute_hmac(entry)
                        if not hmac_mod.compare_digest(stored_hmac, expected):
                            report.tampered.append(f"{log_file.name}:{line_no} (hmac)")
                            continue
                    report.good += 1
                    entry["hmac"] = stored_hmac

                    ts = datetime.fromisoformat(entry["timestamp"])
                    if start_date and ts < start_date:
                        continue
                    if end_date and ts > end_date:
                        continue
                    if event_type and entry["event_type"] != EventType(event_type).value:
                        continue
                    results.append(entry)

        if report.tampered:
            # Record the tamper detection itself — ironic but useful.
            self.log(
                EventType.TAMPER_DETECTED,
                action=Action.BLOCKED,
                metadata={
                    "total": report.total,
                    "tampered_count": len(report.tampered),
                    "tampered_at": report.tampered[:20],
                },
            )
        return sorted(results, key=lambda x: x["timestamp"])

    def verify_integrity(self) -> TamperReport:
        """Walk every log file and return an integrity report (no filtering)."""
        report = TamperReport()
        for log_file in sorted(self.log_dir.glob("audit_*.log.enc")):
            with log_file.open("r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    report.total += 1
                    try:
                        entry = json.loads(self._decrypt(line).decode("utf-8"))
                        stored = entry.pop("hmac", "")
                        if hmac_mod.compare_digest(stored, self._compute_hmac(entry)):
                            report.good += 1
                        else:
                            report.tampered.append(f"{log_file.name}:{line_no}")
                    except Exception:
                        report.tampered.append(f"{log_file.name}:{line_no}")
        return report

    # -------------------------------------------------------------- reports
    def generate_compliance_report(self, output_format: str = "json") -> str:
        """SOC2/HIPAA-style aggregate report over EVERY entry on disk
        (not just the in-memory trail)."""
        all_events = self.query()
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "app_version": APP_VERSION,
            "log_directory": str(self.log_dir),
            "total_events": len(all_events),
            "window": {
                "first": all_events[0]["timestamp"] if all_events else None,
                "last": all_events[-1]["timestamp"] if all_events else None,
            },
            "events_by_type": {},
            "events_by_secret": {},
            "user_activity": {},
            "host_activity": {},
        }
        for e in all_events:
            report["events_by_type"][e["event_type"]] = report["events_by_type"].get(e["event_type"], 0) + 1
            if e.get("secret_type"):
                report["events_by_secret"][e["secret_type"]] = report["events_by_secret"].get(e["secret_type"], 0) + 1
            report["user_activity"][e["user"]] = report["user_activity"].get(e["user"], 0) + 1
            report["host_activity"][e["hostname"]] = report["host_activity"].get(e["hostname"], 0) + 1

        if output_format == "json":
            return json.dumps(report, indent=2)
        if output_format == "csv":
            import csv
            from io import StringIO
            out = StringIO()
            w = csv.DictWriter(
                out,
                fieldnames=["timestamp", "event_type", "secret_type", "action", "user", "hostname"],
            )
            w.writeheader()
            for e in all_events:
                w.writerow({
                    "timestamp": e["timestamp"],
                    "event_type": e["event_type"],
                    "secret_type": e.get("secret_type", ""),
                    "action": e["action"],
                    "user": e["user"],
                    "hostname": e["hostname"],
                })
            return out.getvalue()
        raise ValueError(f"unknown output_format: {output_format!r}")


__all__ = [
    "AuditLogger",
    "EventType",
    "Action",
    "TamperReport",
]


# ------------------------------------------------------- tiny CLI for ops
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Vibe Protect audit log inspector")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify", help="walk the log dir and report any tampered entries")
    r = sub.add_parser("report", help="emit a compliance report")
    r.add_argument("--format", choices=["json", "csv"], default="json")
    sub.add_parser("list", help="print every verified entry chronologically")
    args = ap.parse_args()

    a = AuditLogger()
    if args.cmd == "verify":
        rep = a.verify_integrity()
        print(f"total={rep.total} good={rep.good} tampered={len(rep.tampered)}")
        for t in rep.tampered:
            print(f"  ✖ {t}")
        sys.exit(0 if not rep.tampered else 2)
    elif args.cmd == "report":
        print(a.generate_compliance_report(args.format))
    elif args.cmd == "list":
        for e in a.query():
            print(json.dumps(e, separators=(",", ":")))
