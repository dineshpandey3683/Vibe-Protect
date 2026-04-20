#!/usr/bin/env python3
"""
Vibe Protect — Clipboard guardian for developers.

Monitors your clipboard and instantly redacts secrets (API keys, tokens,
private keys, DB URLs, emails, IPs, etc.) before you ever paste them into
chat, docs, tickets, or an AI assistant.

Usage:
    python vibe_protect.py                 # monitor with defaults
    python vibe_protect.py --log log.json  # append each redaction to JSONL log
    python vibe_protect.py --quiet         # no console output
    python vibe_protect.py --no-notify     # disable desktop notifications

GitHub: https://github.com/your-username/vibe-protect
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import pyperclip
except ImportError:
    print("✖ Missing dependency: pyperclip.  Install with: pip install pyperclip", file=sys.stderr)
    sys.exit(1)

from patterns import redact, PATTERNS
from advanced_detector import AdvancedSecretDetector, CUSTOM_RULES_FILE, write_sample_custom_rules
from pattern_updater import PatternLibraryUpdater
from community_rules import CommunityRulesFetcher
from audit_logger import AuditLogger, EventType, Action
from enterprise_config import EnterpriseConfigManager
from updater import check_for_update, print_update_banner, current_version


# --- optional desktop notifications ------------------------------------------
def _make_notifier(enabled: bool):
    if not enabled:
        return lambda *_a, **_kw: None
    try:
        from plyer import notification  # type: ignore

        def _notify(title: str, message: str):
            try:
                notification.notify(title=title, message=message, timeout=3, app_name="Vibe Protect")
            except Exception:
                pass

        return _notify
    except Exception:
        return lambda *_a, **_kw: None


# --- pretty console ----------------------------------------------------------
RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
AMBER = "\033[38;5;220m"
RED = "\033[38;5;203m"
GREY = "\033[38;5;245m"
GREEN = "\033[38;5;114m"


def banner():
    print(f"{AMBER}{BOLD}")
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║      V I B E   P R O T E C T                 ║")
    print("  ║      clipboard guardian, armed & watching    ║")
    print("  ╚══════════════════════════════════════════════╝")
    print(f"{RESET}{DIM}  → Copy anything. Secrets auto-redact before you paste.{RESET}\n")


def summarise(matches):
    counts = {}
    for m in matches:
        counts[m["pattern"]] = counts.get(m["pattern"], 0) + 1
    return ", ".join(f"{k}×{v}" for k, v in counts.items())


def main() -> int:
    parser = argparse.ArgumentParser(description="Vibe Protect — clipboard secret redactor")
    parser.add_argument("--log", help="Append each redaction event to a JSONL file")
    parser.add_argument("--quiet", action="store_true", help="Suppress console output")
    parser.add_argument("--no-notify", action="store_true", help="Disable desktop notifications")
    parser.add_argument("--interval", type=float, default=0.3, help="Polling interval (seconds)")
    parser.add_argument("--list-patterns", action="store_true", help="List patterns and exit")
    parser.add_argument("--check-update", action="store_true", help="Check for a newer release and exit")
    parser.add_argument("--no-update-check", action="store_true", help="Skip the startup update check")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument(
        "--advanced",
        action="store_true",
        help="Enable entropy-aware detection + custom rules + catch-all (reduces false positives)",
    )
    parser.add_argument(
        "--init-custom-rules",
        action="store_true",
        help="Write a sample ~/.vibeprotect/custom_rules.json and exit",
    )
    parser.add_argument(
        "--sync-patterns",
        action="store_true",
        help="Fetch + verify the signed dynamic pattern bundle from the CDN and exit",
    )
    parser.add_argument(
        "--sync-community-rules",
        action="store_true",
        help="Fetch the PR-gated community pattern list from GitHub and exit",
    )
    parser.add_argument(
        "--no-pattern-sync",
        action="store_true",
        help="Skip opportunistic pattern-library + community-rules sync on startup",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Write an encrypted, HMAC-authenticated audit log to ~/.vibeprotect/audit/",
    )
    parser.add_argument(
        "--audit-report",
        choices=["json", "csv"],
        help="Print a compliance report over the existing audit log and exit",
    )
    parser.add_argument(
        "--audit-verify",
        action="store_true",
        help="Verify integrity of every audit entry on disk and exit",
    )
    parser.add_argument(
        "--show-policy",
        action="store_true",
        help="Print the currently-effective enterprise policy and exit",
    )
    parser.add_argument(
        "--security-audit",
        choices=["json", "md", "html"],
        help="Run the automated security audit suite and write a report",
    )
    args = parser.parse_args()

    if args.version:
        print(f"vibe-protect v{current_version()}")
        return 0

    if args.check_update:
        info = check_for_update(force=True)
        print_update_banner(info)
        return 0

    if args.init_custom_rules:
        path = write_sample_custom_rules()
        print(f"✓ sample custom rules written to {path}")
        return 0

    if args.sync_patterns:
        result = PatternLibraryUpdater().update_patterns(force=True)
        icon = "✓" if result.ok else "⚠"
        print(f"{icon} pattern sync: {result}")
        return 0 if result.ok else 1

    if args.sync_community_rules:
        result = CommunityRulesFetcher().sync(force=True)
        icon = "✓" if result.ok else "⚠"
        print(f"{icon} {result}")
        return 0 if result.ok else 1

    if args.audit_report:
        print(AuditLogger().generate_compliance_report(args.audit_report))
        return 0

    if args.audit_verify:
        rep = AuditLogger().verify_integrity()
        print(f"total={rep.total} good={rep.good} tampered={len(rep.tampered)}")
        for t in rep.tampered:
            print(f"  ✖ {t}")
        return 0 if not rep.tampered else 2

    if args.show_policy:
        print(EnterpriseConfigManager().describe())
        return 0

    if args.security_audit:
        from security_audit import SecurityAuditor
        auditor = SecurityAuditor()
        snap = auditor.run_full_audit()
        path = auditor.generate_report(args.security_audit)
        print(f"✓ security audit: {snap['score']}/{snap['score_out_of']} · grade {snap['grade']}")
        print(f"  report: {path}")
        return 0

    if args.list_patterns:
        for name, _, desc, ex in PATTERNS:
            print(f"{AMBER}{name:<28}{RESET} {desc}")
            print(f"{DIM}    e.g. {ex}{RESET}")
        return 0

    if not args.quiet:
        banner()
        mode = "advanced (entropy + context + catch-all)" if args.advanced else "standard"
        print(f"{DIM}  v{current_version()} · {len(PATTERNS)} patterns · mode: {mode} · polling every {args.interval}s · Ctrl-C to stop{RESET}")
        if args.advanced and CUSTOM_RULES_FILE.exists():
            print(f"{DIM}  custom rules loaded from {CUSTOM_RULES_FILE}{RESET}")
        if not args.no_update_check:
            print_update_banner(check_for_update(force=False))
        if not args.no_pattern_sync:
            result = PatternLibraryUpdater().update_patterns(force=False)
            if result.ok:
                print(f"{DIM}  ↻ pattern library: {result}{RESET}")
            elif "disabled" not in result.reason and "throttled" not in result.reason:
                print(f"{DIM}  ↻ pattern sync skipped: {result.reason}{RESET}")
            cresult = CommunityRulesFetcher().sync(force=False)
            if cresult.ok:
                print(f"{DIM}  ↻ {cresult}{RESET}")
        print()

    advanced_detector = AdvancedSecretDetector.load_default() if args.advanced else None
    auditor = AuditLogger() if args.audit else None
    if auditor:
        auditor.log(EventType.STARTUP, action=Action.INFO, metadata={"mode": "advanced" if args.advanced else "standard"})

    def _do_redact(text: str):
        if advanced_detector is not None:
            return advanced_detector.redact(text)
        return redact(text)

    notify = _make_notifier(not args.no_notify)
    log_path = Path(args.log) if args.log else None
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)

    last = ""
    total_redactions = 0
    total_chars = 0

    try:
        current = pyperclip.paste() or ""
        last = current
    except Exception as e:
        print(f"{RED}✖ Cannot access clipboard: {e}{RESET}", file=sys.stderr)
        print(f"{DIM}  On Linux, install xclip or xsel:  sudo apt install xclip{RESET}", file=sys.stderr)
        return 2

    while True:
        try:
            time.sleep(args.interval)
            current = pyperclip.paste() or ""
            if not current or current == last:
                continue

            cleaned, matches = _do_redact(current)

            if matches:
                try:
                    pyperclip.copy(cleaned)
                except Exception:
                    pass
                last = cleaned
                total_redactions += 1
                chars_saved = len(current) - len(cleaned)
                total_chars += max(0, chars_saved)

                if auditor:
                    # one audit entry per detected pattern for fine-grained reporting
                    kinds_for_audit = {}
                    for m in matches:
                        kinds_for_audit[m["pattern"]] = kinds_for_audit.get(m["pattern"], 0) + 1
                    for k, v in kinds_for_audit.items():
                        auditor.log(
                            EventType.REDACTION,
                            secret_type=k,
                            action=Action.SCRUBBED,
                            metadata={"count": v, "chars_before": len(current), "chars_after": len(cleaned)},
                        )

                ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
                summary = summarise(matches)

                if not args.quiet:
                    stamp = datetime.now().strftime("%H:%M:%S")
                    print(
                        f"{GREY}[{stamp}]{RESET} "
                        f"{AMBER}● redacted{RESET} "
                        f"{BOLD}{len(matches)}{RESET} secret(s) "
                        f"{DIM}({summary}){RESET}"
                    )
                    preview_in = current.replace("\n", "⏎ ")[:80]
                    preview_out = cleaned.replace("\n", "⏎ ")[:80]
                    print(f"  {DIM}in :{RESET} {preview_in}{'…' if len(current) > 80 else ''}")
                    print(f"  {GREEN}out:{RESET} {preview_out}{'…' if len(cleaned) > 80 else ''}")
                    print(
                        f"  {DIM}Σ {total_redactions} events · "
                        f"{total_chars} chars scrubbed{RESET}\n"
                    )

                notify(
                    "Vibe Protect",
                    f"Redacted {len(matches)} secret(s): {summary}",
                )

                if log_path:
                    with log_path.open("a", encoding="utf-8") as f:
                        f.write(
                            json.dumps(
                                {
                                    "ts": ts,
                                    "match_count": len(matches),
                                    "patterns": [m["pattern"] for m in matches],
                                    "chars_before": len(current),
                                    "chars_after": len(cleaned),
                                }
                            )
                            + "\n"
                        )
            else:
                last = current

        except KeyboardInterrupt:
            if not args.quiet:
                print(
                    f"\n{DIM}  Session over. "
                    f"{total_redactions} events, {total_chars} chars scrubbed. Stay safe.{RESET}"
                )
            return 0
        except Exception as e:
            if not args.quiet:
                print(f"{RED}  ! error: {e}{RESET}", file=sys.stderr)
            time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
