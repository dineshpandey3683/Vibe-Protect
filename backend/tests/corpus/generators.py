"""
Synthetic secret generators for the pattern-corpus test suite.

Design principles
-----------------
* **Zero real leaked secrets.** Every positive is generated locally from the
  public pattern specification. We never scrape GitHub / public gists /
  bug-bounty dumps — (a) it risks ingesting still-live credentials, and
  (b) it bakes the plaintext of those secrets into our test tree. Synthetic
  generation gives us a distribution-faithful corpus without either risk.
* **Reproducible.** All generators take a ``seed`` so test runs are
  deterministic. CI failures will repro bit-for-bit.
* **Realistic context.** Each generator returns ``(secret, sentence)`` —
  the raw secret plus a realistic surrounding sentence. The detector is
  run against the sentence so the context-word filter in
  ``advanced_detector.py`` is exercised the way it would be in production.
* **Documentation-words avoided.** Contexts never contain
  "example"/"sample"/"demo"/"test"/"dummy"/"fake" since those are in the
  detector's context blocklist and would cause legitimate positives to
  be suppressed. Avoiding them here isolates detection-ability from the
  (correct) suppression behaviour.

Every generator yields ``N`` cases by default (30). Call ``all_positives()``
for the union (~540 cases across 18 patterns).
"""
from __future__ import annotations

import base64
import random
import string
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple


@dataclass
class PositiveCase:
    pattern: str
    secret: str
    sentence: str

    @property
    def text(self) -> str:
        return self.sentence


# ---------------------------------------------------- primitives
def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def _alnum(r: random.Random, n: int, *, extra: str = "") -> str:
    pool = string.ascii_letters + string.digits + extra
    return "".join(r.choice(pool) for _ in range(n))


def _b64(r: random.Random, n: int) -> str:
    """Return n random base64 characters (not necessarily valid base64)."""
    pool = string.ascii_letters + string.digits + "+/"
    return "".join(r.choice(pool) for _ in range(n))


def _b64url(r: random.Random, n: int) -> str:
    pool = string.ascii_letters + string.digits + "-_"
    return "".join(r.choice(pool) for _ in range(n))


def _upper_digit(r: random.Random, n: int) -> str:
    pool = string.ascii_uppercase + string.digits
    return "".join(r.choice(pool) for _ in range(n))


def _digits(r: random.Random, n: int) -> str:
    return "".join(r.choice(string.digits) for _ in range(n))


def _hostname(r: random.Random) -> str:
    return r.choice([
        "api.internal", "db.prod-01", "cache.useast1", "queue.euwest1",
        "workers.ap-south", "ingest.internal", "vault.corp", "edge.global",
    ])


def _username(r: random.Random) -> str:
    return r.choice([
        "alice", "bob", "carol", "dave", "eve", "frank", "grace", "heidi",
        "ivan", "judy", "kate", "leo", "mallory", "nancy", "oscar", "peggy",
    ])


# ---------------------------------------------------- per-pattern gens
def gen_anthropic(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        s = "sk-ant-api03-" + _alnum(r, r.randint(40, 80), extra="_-")
        out.append(PositiveCase("anthropic_api_key", s, f"ANTHROPIC_KEY={s}"))
    return out


def gen_openai(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        prefix = r.choice(["sk-", "sk-proj-"])
        s = prefix + _alnum(r, r.randint(40, 60), extra="_-")
        out.append(PositiveCase("openai_api_key", s, f"OPENAI_API_KEY={s}"))
    return out


def gen_aws_access(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        s = "AKIA" + _upper_digit(r, 16)
        out.append(PositiveCase("aws_access_key", s, f"AWS_ACCESS_KEY_ID={s}"))
    return out


def gen_aws_secret(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        s = _alnum(r, 40, extra="/+")
        line = f'aws_secret_access_key = "{s}"'
        out.append(PositiveCase("aws_secret_key", s, line))
    return out


def gen_github(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        kind = r.choice(["ghp", "ghs", "gho", "ghu", "ghr"])
        body = _alnum(r, r.randint(36, 40))
        s = f"{kind}_{body}"
        out.append(PositiveCase("github_token", s, f"GITHUB_TOKEN={s}"))
    return out


def gen_stripe(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        kind = r.choice(["sk", "pk", "rk"])
        env = r.choice(["live", "test"])
        s = f"{kind}_{env}_" + _alnum(r, r.randint(24, 32))
        out.append(PositiveCase("stripe_key", s, f"STRIPE_SECRET={s}"))
    return out


def gen_google(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        s = "AIza" + _alnum(r, 35, extra="_-")
        out.append(PositiveCase("google_api_key", s, f"FIREBASE_API_KEY={s}"))
    return out


def gen_slack(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        kind = r.choice(["xoxb", "xoxa", "xoxp", "xoxo", "xoxr", "xoxs"])
        body = f"{_digits(r, 12)}-{_alnum(r, r.randint(20, 32))}"
        s = f"{kind}-{body}"
        out.append(PositiveCase("slack_token", s, f"SLACK_BOT_TOKEN={s}"))
    return out


def gen_jwt(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        head = "eyJ" + _b64url(r, r.randint(15, 30))
        body = "eyJ" + _b64url(r, r.randint(30, 100))
        sig = _b64url(r, r.randint(40, 80))
        s = f"{head}.{body}.{sig}"
        out.append(PositiveCase("jwt_token", s, f"Authorization: Bearer {s}"))
    return out


def gen_private_key(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        kind = r.choice(["RSA ", "EC ", "OPENSSH ", "DSA ", ""])
        body_lines = [_b64(r, 64) for _ in range(r.randint(15, 30))]
        body = "\n".join(body_lines)
        s = (
            f"-----BEGIN {kind}PRIVATE KEY-----\n"
            f"{body}\n"
            f"-----END {kind}PRIVATE KEY-----"
        )
        out.append(PositiveCase("private_key_block", s, s))
    return out


def gen_ssh_public_key(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        kind = r.choice(["ssh-rsa", "ssh-ed25519", "ssh-dss"])
        body = _b64(r, r.randint(150, 350)) + "="
        comment = f"{_username(r)}@{_hostname(r)}"
        s = f"{kind} {body} {comment}"
        # Put it on its own line — ~/.ssh/authorized_keys style
        out.append(PositiveCase("ssh_public_key", s, s))
    return out


def gen_db_connection(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    schemes = ["postgresql", "postgres", "mysql", "mongodb", "mongodb+srv", "redis", "amqp"]
    out = []
    for _ in range(n):
        scheme = r.choice(schemes)
        user = _username(r)
        pwd = _alnum(r, r.randint(12, 20), extra="!#%")
        host = _hostname(r)
        db = r.choice(["prod", "users", "orders", "billing", "logs"])
        s = f"{scheme}://{user}:{pwd}@{host}:5432/{db}"
        out.append(PositiveCase("db_connection_string", s, f"DATABASE_URL={s}"))
    return out


def gen_email(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    domains = ["internal.corp", "workers.io", "acme-corp.net", "contoso.biz", "fabrikam.org"]
    out = []
    for _ in range(n):
        u = _username(r)
        d = r.choice(domains)
        s = f"{u}.{_alnum(r, 4).lower()}@{d}"
        out.append(PositiveCase("email", s, f"Contact: {s}"))
    return out


def gen_ipv4(seed: int, n: int = 30) -> List[PositiveCase]:
    """Use RFC 5737 TEST-NET ranges so we never generate a real public IP."""
    r = _rng(seed)
    # 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24 are reserved for docs
    nets = ["192.0.2", "198.51.100", "203.0.113", "10.0.0", "172.16.0"]
    out = []
    for _ in range(n):
        s = f"{r.choice(nets)}.{r.randint(1, 254)}"
        out.append(PositiveCase("ipv4", s, f"Connected from {s}"))
    return out


def gen_credit_card(seed: int, n: int = 30) -> List[PositiveCase]:
    """Use well-known public test-card numbers so we never ship a real PAN.

    Restricted to card brands currently covered by the ``credit_card``
    regex in ``cli/patterns.py`` (Visa, 5-series Mastercard, Amex,
    Discover). Brands the regex does not yet cover — 2-series Mastercard
    (2221-2720), 14-digit Diners, and JCB — are asserted as known
    limitations by ``test_corpus::TestKnownLimitations`` and tracked
    as a P1 roadmap item. All numbers below are documented test PANs
    from stripe.com/docs/testing — they cannot belong to any real
    cardholder and cannot be charged.
    """
    test_cards = [
        "4242424242424242",  # Visa
        "4000056655665556",  # Visa (debit)
        "5555555555554444",  # Mastercard 5-series
        "5200828282828210",  # Mastercard 5-series (debit)
        "378282246310005",   # Amex
        "371449635398431",   # Amex
        "6011111111111117",  # Discover
        "6011000990139424",  # Discover
    ]
    r = _rng(seed)
    out = []
    for i in range(n):
        s = test_cards[i % len(test_cards)]
        # small rng-driven variation so the corpus isn't identical rows
        wrap = r.choice([
            f"Card on file: {s}",
            f"PAN={s}",
            f"last charge used {s} ending in …{s[-4:]}",
        ])
        out.append(PositiveCase("credit_card", s, wrap))
    return out


def gen_shell_prompt(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        s = f"{_username(r)}@{_hostname(r)}:~$ "
        out.append(PositiveCase("shell_prompt", s, s + "ls -la"))
    return out


def gen_generic_secret(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    keys = ["password", "PASSWORD", "secret", "Secret", "token", "API_KEY", "api-key"]
    out = []
    for _ in range(n):
        k = r.choice(keys)
        v = _alnum(r, r.randint(12, 24), extra="!@#$")
        s = f'{k}="{v}"'
        out.append(PositiveCase("generic_secret_assignment", s, s))
    return out


def gen_long_base64(seed: int, n: int = 30) -> List[PositiveCase]:
    r = _rng(seed)
    out = []
    for _ in range(n):
        raw = bytes(r.randint(0, 255) for _ in range(r.randint(60, 150)))
        s = base64.b64encode(raw).decode()
        out.append(PositiveCase("long_base64_blob", s, f"CERT_PAYLOAD={s}"))
    return out


# ---------------------------------------------------- master assembler
GENERATORS: Dict[str, Callable[[int, int], List[PositiveCase]]] = {
    "anthropic_api_key":          gen_anthropic,
    "openai_api_key":             gen_openai,
    "aws_access_key":             gen_aws_access,
    "aws_secret_key":             gen_aws_secret,
    "github_token":               gen_github,
    "stripe_key":                 gen_stripe,
    "google_api_key":             gen_google,
    "slack_token":                gen_slack,
    "jwt_token":                  gen_jwt,
    "private_key_block":          gen_private_key,
    "ssh_public_key":             gen_ssh_public_key,
    "db_connection_string":       gen_db_connection,
    "email":                      gen_email,
    "ipv4":                       gen_ipv4,
    "credit_card":                gen_credit_card,
    "shell_prompt":               gen_shell_prompt,
    "generic_secret_assignment":  gen_generic_secret,
    "long_base64_blob":           gen_long_base64,
}


def all_positives(seed: int = 20260220, per_pattern: int = 30) -> List[PositiveCase]:
    """Generate the full positive corpus (~540 cases by default)."""
    out: List[PositiveCase] = []
    for i, (name, gen) in enumerate(GENERATORS.items()):
        # offset seed per-pattern so cases are independent
        out.extend(gen(seed + i * 97, per_pattern))
    return out


__all__ = ["PositiveCase", "GENERATORS", "all_positives"]
