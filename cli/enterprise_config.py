"""
Vibe Protect — enterprise configuration (Group Policy / MDM).

Centralised policy management for IT admins rolling Vibe Protect out across
a fleet. A machine-wide YAML policy (pushed via GPO on Windows, MDM profile
on macOS, configuration management on Linux) overrides user preferences, and
enforced fields cannot be altered by local users at all.

Precedence (lowest → highest):
    1. Hard-coded defaults in ``EnterprisePolicy``
    2. User config     (``~/.vibeprotect/config.yaml`` or platform equivalent)
    3. Machine policy  (``/etc/vibeprotect/policy.yaml`` or platform equiv.)
    4. Enforced fields — the admin marks specific keys as ``ENFORCED`` in the
       machine policy, which blocks local-user overrides for those fields.

Public API
----------
    from enterprise_config import EnterpriseConfigManager, EnterprisePolicy
    m = EnterpriseConfigManager()
    policy = m.current_policy
    if not m.is_action_allowed("pause_protection"):
        ...

Optional dependencies
---------------------
    pyyaml     — YAML policy parsing       (JSON fallback if missing)
    pyjwt      — SSO token verification    (SSO disabled if missing)
    requests   — JWKS fetch                (SSO disabled if missing)
"""

from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# ------------------------------------------------------------ optional deps
try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

try:
    import jwt  # type: ignore  # PyJWT
    import requests  # type: ignore
    _HAS_JWT = True
except ImportError:
    _HAS_JWT = False

from audit_logger import AuditLogger, EventType, Action


# ----------------------------------------------------------------- policy
@dataclass
class EnterprisePolicy:
    """Group-policy-style declarative configuration.

    Every field has a documented safe default. Admins should ship only the
    fields they want to override; everything else stays at the default.
    """

    # ── protection behaviour ────────────────────────────────────────────
    enforce_redaction: bool = True
    """Bundled + dynamic + community + user-custom redaction is always on."""

    pause_allowed: bool = True
    """Whether local users are permitted to pause the clipboard watcher."""

    allowed_secret_types: Optional[List[str]] = None
    """If set, restrict active patterns to just these names.
    ``None`` = all patterns active (default)."""

    disabled_secret_types: List[str] = field(default_factory=list)
    """Additional patterns to disable (useful for false-positive suppression)."""

    blocked_applications: List[str] = field(default_factory=list)
    """Process/window titles where copy is strictly blocked (enforced by the
    desktop client only; out of scope for the pure CLI)."""

    # ── audit & compliance ─────────────────────────────────────────────
    audit_level: str = "standard"       # minimal | standard | verbose
    compliance_mode: str = "NONE"       # NONE | SOC2 | HIPAA | GDPR | PCI
    log_retention_days: int = 90

    # ── update policy ──────────────────────────────────────────────────
    auto_update: bool = True
    update_channel: str = "stable"      # stable | beta | enterprise
    pattern_update_frequency_hours: int = 24

    # ── SSO / identity ─────────────────────────────────────────────────
    sso_enabled: bool = False
    sso_provider: str = ""              # azure | okta | google | ""
    sso_tenant_id: str = ""
    sso_client_id: str = ""             # expected audience
    sso_jwks_url: str = ""              # overrideable (else derived)
    required_groups: List[str] = field(default_factory=list)

    # ── which fields cannot be overridden by users ─────────────────────
    enforced_fields: List[str] = field(default_factory=list)
    """Keys in this list are frozen — user config cannot override them."""

    policy_version: str = "1.0.0"

    def sanitised(self) -> Dict[str, Any]:
        return asdict(self)


# ----------------------------------------------- schema + validation
_VALID_FIELDS: Set[str] = {f.name for f in fields(EnterprisePolicy)}
_VALID_AUDIT_LEVELS = {"minimal", "standard", "verbose"}
_VALID_COMPLIANCE = {"NONE", "SOC2", "HIPAA", "GDPR", "PCI"}
_VALID_CHANNELS = {"stable", "beta", "enterprise"}
_VALID_SSO_PROVIDERS = {"", "azure", "okta", "google"}


def _validate(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Return only recognised, type-checked fields. Never raises — unknown or
    invalid fields are silently dropped so a typo in a central policy file
    can't brick every client in the fleet."""
    clean: Dict[str, Any] = {}
    for f in fields(EnterprisePolicy):
        if f.name not in raw:
            continue
        v = raw[f.name]
        # coerce simple types
        try:
            if f.type is bool:
                v = bool(v)
            elif f.type is int:
                v = int(v)
            elif f.type is str:
                v = str(v)
            elif "List" in str(f.type):
                if not isinstance(v, list):
                    continue
                v = [str(x) for x in v]
            elif "Optional[List" in str(f.type):
                if v is not None:
                    if not isinstance(v, list):
                        continue
                    v = [str(x) for x in v]
        except Exception:
            continue
        clean[f.name] = v

    # enum-style validation
    if clean.get("audit_level") and clean["audit_level"] not in _VALID_AUDIT_LEVELS:
        clean.pop("audit_level")
    if clean.get("compliance_mode") and clean["compliance_mode"] not in _VALID_COMPLIANCE:
        clean.pop("compliance_mode")
    if clean.get("update_channel") and clean["update_channel"] not in _VALID_CHANNELS:
        clean.pop("update_channel")
    if "sso_provider" in clean and clean["sso_provider"] not in _VALID_SSO_PROVIDERS:
        clean.pop("sso_provider")
    return clean


# ----------------------------------------------------------- config manager
class EnterpriseConfigManager:
    def __init__(self, audit: Optional[AuditLogger] = None):
        self.system = platform.system()
        self.config_paths = self._get_config_paths()
        self._audit = audit
        self.current_policy: EnterprisePolicy = EnterprisePolicy()
        self.source_trace: List[str] = []
        self.load_policy()

    # ---------------------------------------------------------- platform
    def _get_config_paths(self) -> Dict[str, Path]:
        if self.system == "Windows":
            programdata = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
            localappdata = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
            return {
                "machine": programdata / "VibeProtect" / "policy.yaml",
                "user": localappdata / "VibeProtect" / "config.yaml",
            }
        if self.system == "Darwin":
            return {
                "machine": Path("/Library/Application Support/VibeProtect/policy.yaml"),
                "user": Path.home() / "Library/Application Support/VibeProtect/config.yaml",
                "mdm": Path("/Library/Managed Preferences/com.vibeprotect.plist"),
            }
        # Linux / other
        return {
            "machine": Path("/etc/vibeprotect/policy.yaml"),
            "user": Path.home() / ".config/vibeprotect/config.yaml",
        }

    # ---------------------------------------------------------- loading
    def load_policy(self) -> EnterprisePolicy:
        policy = EnterprisePolicy()
        self.source_trace = ["defaults"]

        # 2) user config — applied first, at any field level
        user_raw = self._read_config_file(self.config_paths.get("user"))
        if user_raw:
            self._apply(policy, user_raw)
            self.source_trace.append(f"user:{self.config_paths['user']}")

        # 3) machine policy — overrides user
        machine_raw = self._read_config_file(self.config_paths.get("machine"))
        if machine_raw:
            self._apply(policy, machine_raw)
            self.source_trace.append(f"machine:{self.config_paths['machine']}")

        # 4) Windows registry (HKLM\Software\Policies\VibeProtect\*)
        reg_raw = self._read_windows_registry()
        if reg_raw:
            self._apply(policy, reg_raw)
            self.source_trace.append("registry:HKLM\\Software\\Policies\\VibeProtect")

        # 5) Enforced-fields re-lock: if the MACHINE policy listed fields as
        # enforced, re-apply them from the machine config on top of anything
        # the user set. This is the actual enforcement layer.
        if machine_raw and machine_raw.get("enforced_fields"):
            enforced_machine = _validate(
                {k: machine_raw[k] for k in machine_raw.get("enforced_fields", []) if k in machine_raw}
            )
            for k, v in enforced_machine.items():
                setattr(policy, k, v)

        self.current_policy = policy
        if self._audit:
            self._audit.log(
                EventType.POLICY_LOADED,
                action=Action.INFO,
                metadata={
                    "sources": self.source_trace,
                    "enforced": list(policy.enforced_fields),
                    "sso_enabled": policy.sso_enabled,
                    "compliance_mode": policy.compliance_mode,
                },
            )
        return policy

    def _read_config_file(self, path: Optional[Path]) -> Dict[str, Any]:
        if not path or not path.exists():
            return {}
        try:
            raw_text = path.read_text(encoding="utf-8")
            if path.suffix in (".yaml", ".yml"):
                if not _HAS_YAML:
                    # allow JSON-in-a-.yaml-file as a YAML subset fallback
                    return _validate(json.loads(raw_text))
                return _validate(yaml.safe_load(raw_text) or {})
            if path.suffix == ".json":
                return _validate(json.loads(raw_text))
        except Exception as e:
            print(f"[vibe-protect] ignored malformed policy at {path}: {e}", file=sys.stderr)
        return {}

    def _read_windows_registry(self) -> Dict[str, Any]:
        if self.system != "Windows":
            return {}
        try:
            import winreg  # type: ignore
        except ImportError:
            return {}
        subkey = r"Software\Policies\VibeProtect"
        out: Dict[str, Any] = {}
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey) as k:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(k, i)
                        out[name] = value
                        i += 1
                    except OSError:
                        break
        except OSError:
            return {}
        return _validate(out)

    def _apply(self, base: EnterprisePolicy, raw: Dict[str, Any]) -> None:
        clean = _validate(raw)
        for k, v in clean.items():
            setattr(base, k, v)

    # ---------------------------------------------------------- enforcement
    def is_action_allowed(self, action: str, details: Optional[Dict] = None) -> bool:
        """Return True if `action` is permitted by the current policy.

        Known actions:
          - ``pause_protection``  : blocked if pause_allowed is False
          - ``disable_pattern``   : blocked if the pattern is in allowed_secret_types-enforced
          - ``skip_audit``        : blocked if audit_level != minimal
          - ``disable_auto_update``: blocked if auto_update is enforced
        """
        details = details or {}
        pol = self.current_policy
        denied_reason: Optional[str] = None

        if action == "pause_protection" and not pol.pause_allowed:
            denied_reason = "pause disabled by policy"
        elif action == "disable_pattern":
            name = details.get("pattern")
            if pol.allowed_secret_types and name not in pol.allowed_secret_types:
                denied_reason = f"pattern '{name}' cannot be disabled while a policy allowlist is in effect"
        elif action == "skip_audit" and pol.audit_level in ("standard", "verbose"):
            denied_reason = f"audit_level={pol.audit_level} requires logging"
        elif action == "disable_auto_update" and pol.auto_update and "auto_update" in pol.enforced_fields:
            denied_reason = "auto_update is enforced by policy"

        if denied_reason is None:
            return True

        if self._audit:
            self._audit.log(
                EventType.POLICY_VIOLATION,
                secret_type="",
                action=Action.BLOCKED,
                metadata={"requested_action": action, "reason": denied_reason, **details},
            )
        return False

    def active_patterns(self, all_pattern_names: List[str]) -> List[str]:
        """Filter a candidate pattern-name list through the policy's
        ``allowed_secret_types`` and ``disabled_secret_types``."""
        pol = self.current_policy
        out = list(all_pattern_names)
        if pol.allowed_secret_types:
            out = [n for n in out if n in pol.allowed_secret_types]
        if pol.disabled_secret_types:
            out = [n for n in out if n not in pol.disabled_secret_types]
        return out

    # ------------------------------------------------------------------ SSO
    def authenticate_sso(self, id_token: str) -> bool:
        if not self.current_policy.sso_enabled:
            return True
        if not _HAS_JWT:
            self._record_sso(False, reason="pyjwt not installed")
            return False
        provider = self.current_policy.sso_provider
        try:
            if provider == "azure":
                ok = self._verify_generic(id_token, self._azure_jwks_url())
            elif provider == "okta":
                ok = self._verify_generic(id_token, self._okta_jwks_url())
            elif provider == "google":
                ok = self._verify_generic(id_token, "https://www.googleapis.com/oauth2/v3/certs")
            else:
                ok = False
        except Exception as e:
            self._record_sso(False, reason=f"{provider}:{e}")
            return False
        self._record_sso(ok, reason="ok" if ok else f"{provider}:verification-failed")
        return ok

    # -- provider-specific JWKS URLs ---------------------------------------
    def _azure_jwks_url(self) -> str:
        if self.current_policy.sso_jwks_url:
            return self.current_policy.sso_jwks_url
        tid = self.current_policy.sso_tenant_id
        if not tid:
            raise RuntimeError("sso_tenant_id required for azure")
        return f"https://login.microsoftonline.com/{tid}/discovery/v2.0/keys"

    def _okta_jwks_url(self) -> str:
        if self.current_policy.sso_jwks_url:
            return self.current_policy.sso_jwks_url
        tid = self.current_policy.sso_tenant_id
        if not tid:
            raise RuntimeError("sso_tenant_id (your Okta domain, e.g. acme.okta.com) required")
        return f"https://{tid}/oauth2/default/v1/keys"

    # -- shared verifier ---------------------------------------------------
    def _verify_generic(self, token: str, jwks_url: str) -> bool:
        # 1) resolve the correct key by `kid` (providers rotate keys)
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        resp = requests.get(jwks_url, timeout=6)
        resp.raise_for_status()
        jwks = resp.json()
        public_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                break
        if public_key is None:
            return False

        # 2) verify signature + audience + optional groups
        audience = self.current_policy.sso_client_id or None
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=audience,  # passing None = skip aud check (only for misconfigured tenants)
            options={"require": ["exp", "iat"]},
        )

        required = set(self.current_policy.required_groups or [])
        if required:
            user_groups = set(decoded.get("groups", []) or [])
            if required.isdisjoint(user_groups):
                return False
        return True

    def _record_sso(self, ok: bool, reason: str):
        if self._audit:
            self._audit.log(
                EventType.SSO_AUTH,
                action=Action.ALLOWED if ok else Action.BLOCKED,
                metadata={"provider": self.current_policy.sso_provider, "reason": reason},
            )

    # ---------------------------------------------------------- reporting
    def describe(self) -> str:
        pol = self.current_policy
        lines = [
            "vibe-protect · effective enterprise policy",
            "=" * 50,
            f"sources:     {', '.join(self.source_trace)}",
            f"policy ver:  {pol.policy_version}",
            f"enforced:    {', '.join(pol.enforced_fields) or '(none)'}",
            "",
            "protection:",
            f"  enforce_redaction      = {pol.enforce_redaction}",
            f"  pause_allowed          = {pol.pause_allowed}",
            f"  allowed_secret_types   = {pol.allowed_secret_types or '(all)'}",
            f"  disabled_secret_types  = {pol.disabled_secret_types or '(none)'}",
            f"  blocked_applications   = {pol.blocked_applications or '(none)'}",
            "",
            "audit & compliance:",
            f"  audit_level            = {pol.audit_level}",
            f"  compliance_mode        = {pol.compliance_mode}",
            f"  log_retention_days     = {pol.log_retention_days}",
            "",
            "updates:",
            f"  auto_update            = {pol.auto_update}",
            f"  update_channel         = {pol.update_channel}",
            f"  pattern_update_hours   = {pol.pattern_update_frequency_hours}",
            "",
            "sso:",
            f"  sso_enabled            = {pol.sso_enabled}",
            f"  sso_provider           = {pol.sso_provider or '(none)'}",
            f"  sso_tenant_id          = {pol.sso_tenant_id or '(none)'}",
            f"  required_groups        = {pol.required_groups or '(none)'}",
        ]
        return "\n".join(lines)


__all__ = [
    "EnterpriseConfigManager",
    "EnterprisePolicy",
]


# ---------------------------------------------------------------- CLI entry
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Vibe Protect enterprise policy inspector")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show", help="print the effective policy + sources")
    sub.add_parser("paths", help="print platform-specific config file paths")
    dump = sub.add_parser("dump", help="print the effective policy as JSON")
    dump.add_argument("--pretty", action="store_true")
    args = ap.parse_args()

    m = EnterpriseConfigManager()
    if args.cmd == "show":
        print(m.describe())
    elif args.cmd == "paths":
        for k, v in m.config_paths.items():
            print(f"{k:>10}: {v}")
    elif args.cmd == "dump":
        print(json.dumps(m.current_policy.sanitised(), indent=2 if args.pretty else None))
