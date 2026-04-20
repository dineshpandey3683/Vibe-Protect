"""
Vibe Protect — shared pattern library.

Each pattern is a (name, regex, description, example) tuple.
Patterns are intentionally conservative to minimise false positives while
catching the majority of real-world secrets that get copy-pasted by accident.
"""

import re

PATTERNS = [
    (
        "anthropic_api_key",
        r"sk-ant-[A-Za-z0-9_\-]{20,}",
        "Anthropic Claude API keys",
        "sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxx",
    ),
    (
        "openai_api_key",
        r"sk-(?:proj-)?[A-Za-z0-9_\-]{20,}",
        "OpenAI API keys (sk-... and sk-proj-...)",
        "sk-proj-abcd1234efgh5678ijkl9012mnop3456",
    ),
    (
        "aws_access_key",
        r"\bAKIA[0-9A-Z]{16}\b",
        "AWS access key IDs",
        "AKIAIOSFODNN7EXAMPLE",
    ),
    (
        "aws_secret_key",
        r"(?i)aws(.{0,20})?(secret|private)?(.{0,20})?['\"][0-9a-zA-Z/+]{40}['\"]",
        "AWS secret access keys (quoted)",
        'aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"',
    ),
    (
        "github_token",
        r"\bgh[pousr]_[A-Za-z0-9]{36,}\b",
        "GitHub personal access / OAuth tokens",
        "ghp_1234567890abcdefghijklmnopqrstuvwxyz12",
    ),
    (
        "stripe_key",
        r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{20,}\b",
        "Stripe secret / publishable / restricted keys",
        "sk_live_51HqABCDEFghijklmnopqrstuvwxyz",
    ),
    (
        "google_api_key",
        r"\bAIza[0-9A-Za-z_\-]{35}\b",
        "Google API / Firebase keys",
        "AIzaSyA-1234567890abcdefghijklmnopqrstuv",
    ),
    (
        "slack_token",
        r"\bxox[abpors]-[A-Za-z0-9\-]{10,}\b",
        "Slack bot / user / app tokens",
        "xoxb-123456789012-abcdefghijklmnopqrstuvwx",
    ),
    (
        "jwt_token",
        r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b",
        "JSON Web Tokens",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcXYZ",
    ),
    (
        "private_key_block",
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----",
        "PEM-encoded private key blocks (RSA / EC / OpenSSH / PGP)",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIB...\n-----END RSA PRIVATE KEY-----",
    ),
    (
        "ssh_public_key",
        r"ssh-(?:rsa|ed25519|dss) [A-Za-z0-9+/=]{100,}(?: [^\s]+)?",
        "SSH public keys (often leaked with comment/email)",
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@host",
    ),
    (
        "db_connection_string",
        r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s:@]+:[^\s:@]+@[^\s/]+",
        "Database URLs with embedded credentials",
        "postgresql://admin:s3cr3t@db.example.com:5432/prod",
    ),
    (
        "email",
        r"\b[\w._%+\-]+@[\w.\-]+\.[A-Za-z]{2,}\b",
        "Email addresses",
        "alice@example.com",
    ),
    (
        "ipv4",
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        "IPv4 addresses (public & private)",
        "192.168.1.42",
    ),
    (
        "credit_card",
        # Covers 7 brands — every match is additionally Luhn-validated by
        # the detector so a random 16-digit number cannot false-positive:
        #
        # 1) Visa            4######## (13 or 16 digits)
        # 2) Mastercard 2-   2221–2720 (16 digits) — BINs activated 2016+
        # 3) Mastercard 5-   51–55     (16 digits, legacy range)
        # 4) Amex            34 / 37   (15 digits)
        # 5) Discover        6011, 65, 644–649, 622126–622925 (16 digits)
        # 6) Diners (14)     300–305 / 36 / 38–39 (14 digits)
        # 7) JCB             3528–3589 (16 digits)
        # 8) UnionPay        62 (16 digits; 17–19 length reserved for future)
        #
        # Deliberately **not** included: Maestro and RuPay. Their published
        # prefix ranges (5xx, 6xx, 60, 65, 81, 82) collide with every other
        # brand above and would match any 13+ digit numeric string starting
        # with 5 or 6 — catastrophic FP risk on order IDs, build numbers,
        # timestamps. Tracked in TestKnownLimitations.
        r"\b(?:"
        # Visa
        r"4[0-9]{12}(?:[0-9]{3})?"
        # Mastercard 2-series 2221-2720 and 5-series 51-55
        r"|(?:5[1-5][0-9]{2}|222[1-9]|22[3-9][0-9]|2[3-6][0-9]{2}|27[0-1][0-9]|2720)[0-9]{12}"
        # Amex
        r"|3[47][0-9]{13}"
        # Discover (6011, 65xx, 644-649, 622126-622925)
        r"|(?:6011|65[0-9]{2}|64[4-9][0-9]|622(?:1(?:2[6-9]|[3-9][0-9])|[2-8][0-9]{2}|9(?:[01][0-9]|2[0-5])))[0-9]{10,12}"
        # Diners 14-digit (300-305, 36, 38-39)
        r"|3(?:0[0-5]|[68][0-9])[0-9]{11}"
        # JCB (3528-3589)
        r"|(?:352[89]|35[3-8][0-9])[0-9]{12}"
        # UnionPay (62 + 14 more digits; 16-total-digit card)
        r"|62[0-9]{14}"
        r")\b",
        "Credit card numbers (Visa, MC incl. 2-series, Amex, Discover, Diners 14d, JCB, UnionPay)",
        "4111111111111111",
    ),
    (
        "shell_prompt",
        r"[\w.\-]+@[\w.\-]+:~[#$] ?",
        "Shell prompts leaking username@hostname",
        "alice@macbook-pro:~$ ",
    ),
    (
        "generic_secret_assignment",
        r"(?i)(?:password|passwd|secret|token|api[_\-]?key)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]",
        "Generic password/token assignments in code/config",
        'PASSWORD="hunter2_super_secret"',
    ),
    (
        "long_base64_blob",
        # Require at least one non-hex-digit char ([G-Z]|[g-z]|'+'|'/') to
        # exclude 60+ char hex digests (git SHAs, docker `@sha256:…`, hash
        # output) which are almost never secrets.
        r"(?<![A-Za-z0-9+/])(?=[A-Za-z0-9+/]*[G-Zg-z+/])[A-Za-z0-9+/]{60,}={0,2}(?![A-Za-z0-9+/])",
        "Long base64 blobs (likely encoded secrets/certs)",
        "VGhpc0lzQVZlcnlMb25nQmFzZTY0U3RyaW5nVGhhdE1pZ2h0QmVBU2VjcmV0UGF5bG9hZA==",
    ),
]


def get_compiled():
    """Return (name, compiled_regex, description, example) list."""
    return [(n, re.compile(p), d, ex) for n, p, d, ex in PATTERNS]


# Pre-compiled union for speed — tagged groups so we can identify matches.
_INLINE_FLAG_RE = re.compile(r"^\(\?([aiLmsux]+)\)")


def _to_scoped(pat: str) -> str:
    """Convert leading inline flags like '(?i)foo' to scoped '(?i:foo)' so the
    pattern can be safely concatenated inside a larger alternation."""
    m = _INLINE_FLAG_RE.match(pat)
    if not m:
        return pat
    flags = m.group(1)
    rest = pat[m.end():]
    return f"(?{flags}:{rest})"


def compile_union():
    parts = [f"(?P<{name}>{_to_scoped(pat)})" for name, pat, _, _ in PATTERNS]
    return re.compile("|".join(parts))


UNION = compile_union()


# ------------------------------------------------------------- dynamic merge
def merged_patterns():
    """Return the bundled 18 + any locally-cached dynamic + community patterns.

    Strict precedence (earlier = higher priority, earlier match wins in the
    union regex because of Python's left-to-right alternation):
        1. bundled (cli/patterns.py) — audited, always wins
        2. dynamic signed (pattern_updater.py)  — additive, `dyn_` prefix
        3. community       (community_rules.py) — additive, `community_` prefix
    Name collisions at any lower tier are dropped, not shadowed — so lower
    tiers can never weaken a higher tier's protection.
    """
    seen = {n for n, *_ in PATTERNS}
    out = list(PATTERNS)

    try:
        from pattern_updater import PatternLibraryUpdater
        for entry in PatternLibraryUpdater().load_dynamic_patterns():
            if entry[0] in seen:
                continue
            seen.add(entry[0])
            out.append(entry)
    except Exception:
        pass

    try:
        from community_rules import CommunityRulesFetcher
        for entry in CommunityRulesFetcher().load_patterns():
            if entry[0] in seen:
                continue
            seen.add(entry[0])
            out.append(entry)
    except Exception:
        pass

    return out


def compile_union_dynamic():
    """Recompile the UNION including dynamic patterns (safe — additive only)."""
    parts = [f"(?P<{n}>{_to_scoped(p)})" for n, p, _, _ in merged_patterns()]
    return re.compile("|".join(parts))


def redact(text: str, mask: str = "[REDACTED]"):
    """
    Redact all known secret patterns from `text`.
    Returns (cleaned_text, matches) where matches is a list of dicts:
      {pattern, original, start, end, mask}
    """
    matches = []

    def _sub(m):
        kind = m.lastgroup or "secret"
        original = m.group(0)
        masked = f"[{kind.upper()}]" if mask == "[REDACTED]" else mask
        matches.append(
            {
                "pattern": kind,
                "original_len": len(original),
                "start": m.start(),
                "end": m.end(),
                "mask": masked,
            }
        )
        return masked

    cleaned = UNION.sub(_sub, text)
    return cleaned, matches
