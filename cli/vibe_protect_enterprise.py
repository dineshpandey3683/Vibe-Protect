#!/usr/bin/env python3
"""
Vibe Protect Enterprise — unified CLI dispatcher.

This is a thin entry point that routes every flag into the already-hardened
modular components under ``/app/cli/``, ``/app/extension/``, and
``/app/installer/``. It exists so end-users (and ops / CI) can run a single
``vibe_protect_enterprise.py`` with the flags listed in the README without
having to remember which module owns which feature.

Usage
-----
    vibe_protect_enterprise.py                     # clipboard monitor (default)
    vibe_protect_enterprise.py --build-chrome      # zip /app/extension for Web Store
    vibe_protect_enterprise.py --audit             # generate HTML security audit
    vibe_protect_enterprise.py --build-binaries    # invoke platform-native build
    vibe_protect_enterprise.py --test-bug "<text>" # LOCAL-ONLY detector self-test
    vibe_protect_enterprise.py --backend sqlite    # audit backend selector
    vibe_protect_enterprise.py --backend flatfile
    vibe_protect_enterprise.py --confidence 0.80   # ML-confidence threshold

Safety notes (why this file is *not* a monolithic rewrite)
----------------------------------------------------------
* We never copy crypto / key derivation inline — we instantiate the existing
  ``AuditLogger`` so the persistent PBKDF2 salt + HKDF sub-keys are reused.
* ``--test-bug`` is strictly local. The supplied text is never written to
  disk, never uploaded, never cached. Users who want to file a finding are
  pointed at ``report_vuln.py`` / ``SECURITY.md``.
* ``--build-chrome`` zips the real, working Manifest V3 extension shipped in
  ``/app/extension/`` — it does NOT regenerate a placeholder extension.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Ensure sibling modules resolve when running from any CWD.
CLI_DIR = Path(__file__).resolve().parent
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

APP_ROOT = CLI_DIR.parent
EXTENSION_DIR = APP_ROOT / "extension"
INSTALLER_DIR = APP_ROOT / "installer"
DIST_DIR = APP_ROOT / "dist"


# ----------------------------------------------------------- version helper
def _read_version() -> str:
    try:
        from updater import current_version
        return current_version()
    except Exception:
        return "3.0.0"


VERSION = _read_version()


# =========================================================================
# --build-chrome  →  zip the real /app/extension folder
# =========================================================================
def build_chrome() -> int:
    if not EXTENSION_DIR.exists():
        print(f"✖ extension dir not found: {EXTENSION_DIR}", file=sys.stderr)
        return 2
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DIST_DIR / f"vibe_protect_extension_v{VERSION}.zip"

    # Exclude any editor cruft or previously generated zips.
    exclude = {".DS_Store", "Thumbs.db"}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in EXTENSION_DIR.rglob("*"):
            if not f.is_file() or f.name in exclude:
                continue
            zf.write(f, f.relative_to(EXTENSION_DIR))

    print(f"✅ Chrome extension packaged: {zip_path}")
    print(f"   size: {zip_path.stat().st_size / 1024:.1f} KB")
    print("   Upload at: https://chrome.google.com/webstore/devconsole")
    return 0


# =========================================================================
# --audit  →  call the existing SecurityAuditor
# =========================================================================
def run_security_audit(output_format: str = "html") -> int:
    from security_audit import SecurityAuditor

    auditor = SecurityAuditor(app_root=APP_ROOT)
    snap = auditor.run_full_audit()
    path = auditor.generate_report(format=output_format)
    print(f"✅ security audit ({output_format.upper()}): {path}")
    print(f"   score: {snap['score']} / {snap['score_out_of']}  ·  grade: {snap['grade']}")
    # machine-readable summary for CI consumers
    print(json.dumps({
        "score": snap["score"],
        "score_out_of": snap["score_out_of"],
        "grade": snap["grade"],
        "report": str(path),
    }))
    return 0 if snap["grade"] not in ("F",) else 2


# =========================================================================
# --build-binaries  →  delegate per-platform
# =========================================================================
def build_binaries() -> int:
    import platform as _plat
    system = _plat.system()
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    if system == "Windows":
        script = INSTALLER_DIR / "build_windows.py"
        if not script.exists():
            print(f"✖ missing {script}", file=sys.stderr)
            return 2
        rc = subprocess.call([sys.executable, str(script)], cwd=str(INSTALLER_DIR))
        return rc

    if system == "Darwin":
        print("🍎 macOS binary build is not yet wired up in this dispatcher.")
        print("   Workaround: `pip install pyinstaller && pyinstaller "
              f"--onefile --name vibe_protect {CLI_DIR / 'vibe_protect.py'}`")
        print("   Then `hdiutil create ...` to wrap into a .dmg.")
        print("   Tracked on ROADMAP.md as P2 (macOS .dmg CI build).")
        return 0

    if system == "Linux":
        print("🐧 Linux binary build is not yet wired up in this dispatcher.")
        print("   Workaround: `pip install pyinstaller && pyinstaller "
              f"--onefile --name vibe_protect {CLI_DIR / 'vibe_protect.py'}`")
        print("   Then wrap with `appimagetool` into a .AppImage.")
        print("   Tracked on ROADMAP.md as P2 (Linux .AppImage CI build).")
        return 0

    print(f"⚠ unsupported platform: {system}", file=sys.stderr)
    return 2


# =========================================================================
# --test-bug "<text>"  →  LOCAL self-test, no disk writes of input
# =========================================================================
def test_bug(sample: str, confidence_threshold: float) -> int:
    """Run the detector against ``sample`` and print whether it was caught.

    This function is intentionally air-gapped: the user-supplied text is
    never persisted, hashed-for-tracking, or transmitted. It exists so a
    security researcher can quickly verify whether their test case would
    be caught; if it *isn't*, they are pointed at our published disclosure
    channel (SECURITY.md / report_vuln.py) rather than being auto-submitted.
    """
    from advanced_detector import AdvancedSecretDetector

    det = AdvancedSecretDetector(ml_confidence_threshold=confidence_threshold)
    matches = det.detect(sample)

    if matches:
        print(f"✅ DETECTED — {len(matches)} match(es) found:")
        for m in matches:
            print(
                f"   • pattern={m.pattern}  "
                f"confidence={m.confidence:.2f}  "
                f"entropy={m.entropy:.2f}  "
                f"len={len(m.original)}"
            )
        return 0

    print("⚠ NOT DETECTED — this input slipped past the current rules.")
    print("  Your input was NOT stored, logged, or transmitted anywhere.")
    print("  If you believe this is a real false negative worth reporting,")
    print("  please file it responsibly via:")
    print("    • /app/SECURITY.md  (private disclosure process)")
    print(f"    • python {CLI_DIR / 'report_vuln.py'}  (template generator)")
    print(
        f"  Current confidence threshold: {confidence_threshold:.2f} "
        f"(entropy={det.shannon_entropy(sample):.2f}, "
        f"variety={det.character_variety(sample):.2f}, len={len(sample)})"
    )
    return 1


# =========================================================================
# default  →  clipboard monitor, with --backend + --confidence applied
# =========================================================================
def run_monitor(backend: str, confidence_threshold: float) -> int:
    """Wrapper around ``vibe_protect.main()`` that applies the enterprise
    flags before handing off to the standard argparse-driven entry point."""
    # Late import so --build-* / --audit paths don't need pyperclip etc.
    import vibe_protect  # noqa: WPS433 (runtime import by design)
    from audit_logger import AuditLogger, VALID_BACKENDS  # noqa: F401
    from advanced_detector import AdvancedSecretDetector

    # Monkey-patch the two factories *in-module* so the existing argparse
    # CLI in vibe_protect.py picks up our enterprise values without needing
    # a rewrite. This is a narrow, well-scoped shim — no shared state leaks
    # back into tests.
    _orig_load = AdvancedSecretDetector.load_default

    def _patched_load(**overrides):  # type: ignore[no-untyped-def]
        overrides.setdefault("ml_confidence_threshold", confidence_threshold)
        return _orig_load(**overrides)

    AdvancedSecretDetector.load_default = classmethod(  # type: ignore[assignment]
        lambda cls, **kw: _patched_load(**kw)
    )

    _orig_init = AuditLogger.__init__

    def _patched_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs.setdefault("backend", backend)
        _orig_init(self, *args, **kwargs)

    AuditLogger.__init__ = _patched_init  # type: ignore[assignment]

    # Always-on: enterprise mode forces --advanced + --audit so the
    # enterprise flags actually take effect. End-users who want a plain
    # run should call vibe_protect.py directly.
    new_argv = [sys.argv[0], "--advanced", "--audit"] + [
        a for a in sys.argv[1:]
        if a not in {"--build-chrome", "--audit", "--build-binaries"}
        and not a.startswith("--backend")
        and not a.startswith("--confidence")
        and not a.startswith("--test-bug")
    ]
    sys.argv = new_argv
    return vibe_protect.main()


# =========================================================================
# argparse entry
# =========================================================================
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="vibe_protect_enterprise",
        description=f"Vibe Protect Enterprise v{VERSION} — unified CLI",
    )
    parser.add_argument("--build-chrome", action="store_true",
                        help="package /app/extension into dist/*.zip for Chrome Web Store")
    parser.add_argument("--audit", action="store_true",
                        help="generate HTML security-audit report")
    parser.add_argument("--audit-format", choices=["html", "json", "md"], default="html",
                        help="output format for --audit (default: html)")
    parser.add_argument("--build-binaries", action="store_true",
                        help="build platform-native binaries (delegates by OS)")
    parser.add_argument("--test-bug", metavar="TEXT",
                        help="LOCAL-ONLY detector self-test; input is never stored")
    parser.add_argument("--backend", choices=["sqlite", "flatfile"], default="flatfile",
                        help="audit-log storage backend for clipboard monitor "
                             "(default: flatfile; sqlite enables SQL queries)")
    parser.add_argument("--confidence", type=float, default=0.0,
                        help="ML confidence threshold in [0, 1] — matches "
                             "below this score are suppressed (default: 0.0 = off)")

    args = parser.parse_args(argv)

    if not (0.0 <= args.confidence <= 1.0):
        parser.error("--confidence must be in [0.0, 1.0]")

    if args.build_chrome:
        return build_chrome()
    if args.audit:
        return run_security_audit(args.audit_format)
    if args.build_binaries:
        return build_binaries()
    if args.test_bug is not None:
        return test_bug(args.test_bug, args.confidence)

    # default path — clipboard monitor with enterprise flags applied
    return run_monitor(args.backend, args.confidence)


if __name__ == "__main__":
    sys.exit(main())
