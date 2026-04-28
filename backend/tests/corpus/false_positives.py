"""
Hand-curated false-positive corpus.

These are strings that look secret-ish (high-entropy, long, alphanumeric)
or live in contexts where a naive regex would fire, but which the detector
MUST NOT redact. A single stray match here is a production-visible bug
(imagine a user pasting ``react@18.2.0`` into Slack and getting
``[LONG_BASE64_BLOB]`` back).

Buckets (roughly balanced):
    * package names, versions, semver strings
    * UUIDs, git SHAs, docker digests
    * URLs without credentials
    * prose and code comments with "secret"-like words but no actual secrets
    * config snippets with placeholder values (``<YOUR_KEY>``, ``${ENV}``)
    * file paths, ANSI escapes, timestamps, build IDs
    * short hex / numeric tokens

Each entry is a single string. The detector should return **zero** matches
for every one of these.
"""

FALSE_POSITIVES = [
    # ------------------------------------------------ prose / documentation
    "Welcome to our product. We care about your privacy.",
    "Please read the Terms of Service before continuing.",
    "This release contains breaking changes — see the migration guide.",
    "The quick brown fox jumps over the lazy dog.",
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    "Users should rotate their credentials regularly.",
    "Never commit secrets to version control — use a secret manager.",
    "Copy the value from the dashboard into your CI/CD pipeline.",
    "Authentication requires a signed bearer token (opaque string).",
    "Tokens are scoped to a single project and expire after 90 days.",

    # ------------------------------------------------ short identifiers
    "user_id",
    "org_id",
    "team_id",
    "project_name",
    "resource_name",
    "ENABLED",
    "DEBUG",
    "PRODUCTION",

    # ------------------------------------------------ package / version IDs
    "react@18.2.0",
    "next@14.1.3",
    "@angular/core@17.0.0",
    "express@4.18.2",
    "fastapi==0.109.2",
    "numpy==1.26.4",
    "pandas==2.2.0",
    "django>=4.2,<5.0",
    "typescript@~5.3.3",
    "go1.21.6 linux/amd64",
    "python3.11.8",
    "nodejs-lts-iron",
    "rustc 1.75.0 (82e1608df 2023-12-21)",
    "openjdk-17.0.10",

    # ------------------------------------------------ semver / build IDs
    "1.0.0",
    "1.2.3",
    "1.2.3-beta.4",
    "1.2.3-rc.1+build.456",
    "v2024.02.15",
    "2024.02.20-nightly",
    "build-12345",
    "ci-job-987654321",

    # ------------------------------------------------ UUIDs (not secrets)
    "123e4567-e89b-12d3-a456-426614174000",
    "550e8400-e29b-41d4-a716-446655440000",
    "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
    "6ba7b812-9dad-11d1-80b4-00c04fd430c8",
    "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",

    # ------------------------------------------------ git SHAs (40 hex)
    "git rev-parse HEAD returns e83c5163316f89bfbde7d9ab23ca2e25604af290",
    "commit 2b0f4a09d1e8f7d51d6c3da3c9b4d0e1a6b8f2e9 merged",
    "tag at 4a5d8e1f2c3b7a9d6e0f1c8b7a5e3d2f1c0b9a8d",
    "rollback to d3c5b4a9e8f7c6d5b4a3e2d1c0b9a8f7e6d5c4b3",

    # ------------------------------------------------ docker image digests
    "nginx@sha256:abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
    "postgres:16-alpine@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "node:20-slim",
    "python:3.11-bookworm",

    # ------------------------------------------------ URLs without credentials
    "https://api.example.com/v1/users",
    "https://github.com/dineshpandey3683/Vibe-Protect",
    "https://docs.anthropic.com/claude/docs",
    "https://platform.openai.com/docs/api-reference",
    "https://aws.amazon.com/iam/",
    "ftp://files.internal/public/readme.txt",
    "wss://stream.company.io/live",
    "contact us via the support page",

    # ------------------------------------------------ config placeholders
    "API_KEY=${API_KEY}",
    "TOKEN=<REPLACE_WITH_YOUR_TOKEN>",
    "PASSWORD=<not-set>",
    "SECRET=<see-vault>",
    "DATABASE_URL=${DATABASE_URL}",
    "STRIPE_KEY=${STRIPE_KEY:-pk_test_default}",
    "BEARER=$(cat ~/.config/token)",
    "token: !Ref ApiToken",

    # ------------------------------------------------ CSS / design tokens
    "color: #2563EB;",
    "background: #0a0a0a;",
    "font-family: 'Inter', sans-serif;",
    "margin: 16px 24px 16px 24px;",
    "transform: translateY(-4px);",
    "cubic-bezier(0.4, 0, 0.2, 1)",
    "rgba(255, 255, 255, 0.08)",
    "linear-gradient(180deg, #000 0%, #111 100%)",

    # ------------------------------------------------ file paths
    "/usr/local/bin/python3",
    "/Users/alice/projects/vibe-protect/src/main.py",
    "C:\\Program Files\\VibeProtect\\vibe_protect.exe",
    "~/.config/vibeprotect/config.yaml",
    "./node_modules/@angular/core/bundles/core.umd.js",

    # ------------------------------------------------ timestamps / logs
    "2026-02-20T15:30:00.000Z",
    "2026-02-20 15:30:00 +0000",
    "[2026-02-20 15:30:00] INFO request_id=42 route=/api/v1/users",
    "Feb 20 15:30:00 host kernel: [12345.678901] CPU: 0 PID: 1234",
    "HTTP/1.1 200 OK",
    "Content-Length: 1024",

    # ------------------------------------------------ code snippets w/o creds
    "const USER = 'alice'",
    "def hash_password(pw: str) -> str: return hashlib.sha256(pw.encode()).hexdigest()",
    "if (err != nil) { return err }",
    "SELECT id, name FROM users WHERE active = true;",
    "for i in range(10): print(i)",
    "// TODO: rotate the key before 2026-06-01",
    "# store the hash, not the password",
    "/* password field uses argon2id */",

    # ------------------------------------------------ placeholders in docs
    "export ANTHROPIC_API_KEY=<your-anthropic-key>",
    "export OPENAI_API_KEY=<put-key-here>",
    "# replace YOUR_TOKEN below with a real value",
    "# do NOT commit your real credentials",

    # ------------------------------------------------ short hex tokens (not SHAs)
    "0xdeadbeef",
    "0xcafebabe",
    "#ff0000",
    "#00ff00",
    "#0000ff",

    # ------------------------------------------------ ANSI escape colours
    "\\x1b[31mERROR\\x1b[0m failed to connect",
    "\\e[1;34minfo\\e[0m request accepted",

    # ------------------------------------------------ build artefacts / hashes
    "sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "sha1: da39a3ee5e6b4b0d3255bfef95601890afd80709",
    "md5: d41d8cd98f00b204e9800998ecf8427e",

    # ------------------------------------------------ numeric sequences
    "1234567890",
    "0000000000",
    "9999999999",
    "phone digits: 1234567",

    # ------------------------------------------------ CLI help output
    "Usage: vibe_protect [OPTIONS] COMMAND [ARGS]...",
    "  --help  Show this message and exit.",
    "  -v, --verbose  enable debug output",

    # ------------------------------------------------ HTTP headers
    "Content-Type: application/json",
    "Accept: application/json",
    "Cache-Control: no-cache",
    "X-Request-ID: req-abc123",
    "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",

    # ------------------------------------------------ json blobs w/o secrets
    '{"name": "alice", "age": 30}',
    '{"ok": true, "count": 42}',
    '{"status": "healthy", "uptime": 12345}',
    '{"patterns_active": 18, "total_events": 0}',

    # ------------------------------------------------ CSV rows w/o secrets
    "id,name,email_domain\n1,alice,internal.corp\n2,bob,acme-corp.net",
    "timestamp,event,count\n2026-02-20,startup,1",

    # ------------------------------------------------ misc technical prose
    "The Shannon entropy of uniformly random bytes approaches 8 bits/char.",
    "HKDF derives sub-keys from a master via separate info strings.",
    "AES-256-GCM provides both confidentiality and authentication.",
    "PBKDF2 with 200k iterations makes brute-force economically infeasible.",
    "SOC2 Type II requires evidence that controls operate over a period.",

    # ------------------------------------------------ generic words / names
    "Production",
    "Staging",
    "Development",
    "us-east-1",
    "eu-west-2",
    "ap-southeast-1",
    "Primary Region",

    # ------------------------------------------------ punctuation / symbols
    "...",
    "———",
    "✓",
    "=>",
    ">=<",

    # ------------------------------------------------ short alphanumeric that
    # shouldn't look like secrets (too short to hit catchall min_len=24)
    "abc123",
    "HELLO_WORLD",
    "Main.tsx",
    "README.md",
    "LICENSE",
    "TODO.md",

    # ------------------------------------------------ phone-number-shaped
    "+1 (555) 010-1234",
    "+44 20 7123 4567",
    "+91 98765 43210",

    # ------------------------------------------------ IP-address-shaped but
    # actually version strings / dotted identifiers
    "v1.2.3.4-release",

    # ------------------------------------------------ Stripe docs placeholders
    "pk_test_TYooMQauvdEDq54NiTphI7jx",   # Stripe's own publicly documented stub — appears in 10M+ READMEs; we keep it here to prove the detector still flags it as a STRIPE key (moved to positives would duplicate)
]

# The Stripe doc placeholder above intentionally *does* match — it's the most
# famous secret-ish string in open source. We keep it in one place as a
# reference and remove from FP scoring:
_KNOWN_INTENDED_MATCHES = {
    "pk_test_TYooMQauvdEDq54NiTphI7jx",
}


def scoring_corpus():
    """Return the FP corpus with known-intended matches stripped out."""
    return [s for s in FALSE_POSITIVES if s not in _KNOWN_INTENDED_MATCHES]


__all__ = ["FALSE_POSITIVES", "scoring_corpus"]
