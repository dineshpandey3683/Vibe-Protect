# Security Policy

Vibe Protect handles clipboards that contain developer secrets. We take
reports of vulnerabilities seriously.

## Supported versions

Security fixes are released for the current minor version and the previous
one. Anything older, please upgrade first before reporting.

| Version | Supported |
| --- | --- |
| 1.x     | ✅        |
| < 1.0   | ❌        |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security reports.**

- **Preferred:** submit through [Huntr.dev](https://huntr.dev/bounties/disclose/?target=https%3A%2F%2Fgithub.com%2Fvibeprotect%2Fvibe-protect) — researchers get credited and (eventually) paid via our program
- **Alternate:** open a [GitHub Security Advisory](https://github.com/dineshpandey3683/Vibe-Protect/security/advisories/new) — private, tracked, signed
- **Email (fallback):** `security@vibeprotect.com` — GPG key fingerprint `TODO_PUBLISH_BEFORE_FIRST_RELEASE`

Please include, where possible:

1. Version (`vibe_protect.py --version`)
2. Platform + Python version
3. Minimal reproduction — you can generate a pre-filled, PII-free evidence
   bundle via `python vibe_protect.py --report-vuln` and paste its output
   into your Huntr / Advisory submission
4. Impact assessment (what can an attacker do?)

## Scope

**In scope:**

- False negatives — a real secret shape the built-in patterns miss
- Bypass of the redactor (e.g., a way to get a copy event to dodge our content script)
- Cryptographic bugs in `audit_logger.py`, `pattern_updater.py`, `enterprise_config.py`
- Signature-verification bypass in the pattern-update path
- Privilege-escalation or sandbox-escape from the browser extension or desktop app
- Secrets leaked via log files, tempfiles, crash dumps, or telemetry that shouldn't exist

**Out of scope:**

- False positives on synthetic / low-quality corpora (open an issue instead)
- Social-engineering attacks against maintainers
- Physical attacks / local-attacker-with-root scenarios (the threat model is
  clearly documented in `audit_logger.py`)
- Denial of service via pathological regex input (we have ReDoS safety on
  dynamic patterns; built-ins are maintainer-audited)
- Vulnerabilities in third-party dependencies — report those upstream and
  open a PR bumping our pin

## Response commitments

| Stage | Target |
| --- | --- |
| First response | 72 hours |
| Triage + severity classification | 7 days |
| Fix for critical / high | 30 days |
| Fix for medium / low | best-effort |
| Public disclosure | coordinated; 90 days max from report |

## Safe harbour

Good-faith security research is welcome. We won't pursue legal action
against researchers who:

- Act in good faith to identify real vulnerabilities
- Don't access, modify, or exfiltrate data beyond the minimum needed to
  demonstrate impact
- Give us reasonable time (the 90-day window above) before public disclosure

## Hall of fame

Researchers who report valid vulnerabilities are credited in
[`CONTRIBUTORS.md`](CONTRIBUTORS.md) and in release notes (opt-out available).
