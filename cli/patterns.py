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
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",
        "Credit card numbers (Visa, MC, Amex, Discover)",
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
        r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{60,}={0,2}(?![A-Za-z0-9+/])",
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
