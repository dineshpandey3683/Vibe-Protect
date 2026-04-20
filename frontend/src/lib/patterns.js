// Vibe Protect — shared pattern library (JavaScript mirror of cli/patterns.py)
// Used by the browser extension and the web playground.
//
// Keep in sync with /app/cli/patterns.py — these regexes are intentionally
// conservative to minimise false positives.

/* eslint-disable no-useless-escape */
export const PATTERNS = [
  {
    name: "openai_api_key",
    label: "OpenAI API Key",
    regex: /sk-(?:proj-)?[A-Za-z0-9_\-]{20,}/g,
    description: "OpenAI API keys (sk-... and sk-proj-...)",
    example: "sk-proj-abcd1234efgh5678ijkl9012mnop3456",
  },
  {
    name: "anthropic_api_key",
    label: "Anthropic Key",
    regex: /sk-ant-[A-Za-z0-9_\-]{20,}/g,
    description: "Anthropic Claude API keys",
    example: "sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxx",
  },
  {
    name: "aws_access_key",
    label: "AWS Access Key",
    regex: /\bAKIA[0-9A-Z]{16}\b/g,
    description: "AWS access key IDs",
    example: "AKIAIOSFODNN7EXAMPLE",
  },
  {
    name: "aws_secret_key",
    label: "AWS Secret Key",
    regex: /aws(?:.{0,20})?(?:secret|private)?(?:.{0,20})?['"][0-9a-zA-Z/+]{40}['"]/gi,
    description: "AWS secret access keys (quoted)",
    example: 'aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"',
  },
  {
    name: "github_token",
    label: "GitHub Token",
    regex: /\bgh[pousr]_[A-Za-z0-9]{36,}\b/g,
    description: "GitHub personal access / OAuth tokens",
    example: "ghp_1234567890abcdefghijklmnopqrstuvwxyz12",
  },
  {
    name: "stripe_key",
    label: "Stripe Key",
    regex: /\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{20,}\b/g,
    description: "Stripe secret / publishable / restricted keys",
    example: "sk_live_51HqABCDEFghijklmnopqrstuvwxyz",
  },
  {
    name: "google_api_key",
    label: "Google API Key",
    regex: /\bAIza[0-9A-Za-z_\-]{35}\b/g,
    description: "Google API / Firebase keys",
    example: "AIzaSyA-1234567890abcdefghijklmnopqrstuv",
  },
  {
    name: "slack_token",
    label: "Slack Token",
    regex: /\bxox[abpors]-[A-Za-z0-9\-]{10,}\b/g,
    description: "Slack bot / user / app tokens",
    example: "xoxb-123456789012-abcdefghijklmnopqrstuvwx",
  },
  {
    name: "jwt_token",
    label: "JWT",
    regex: /\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b/g,
    description: "JSON Web Tokens",
    example: "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcXYZ",
  },
  {
    name: "private_key_block",
    label: "Private Key Block",
    regex: /-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----/g,
    description: "PEM-encoded private key blocks",
    example: "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIB...\n-----END RSA PRIVATE KEY-----",
  },
  {
    name: "ssh_public_key",
    label: "SSH Public Key",
    regex: /ssh-(?:rsa|ed25519|dss) [A-Za-z0-9+/=]{100,}(?: [^\s]+)?/g,
    description: "SSH public keys (often leaked with user@host)",
    example: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@host",
  },
  {
    name: "db_connection_string",
    label: "DB URL with Creds",
    regex: /\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp):\/\/[^\s:@]+:[^\s:@]+@[^\s/]+/g,
    description: "Database URLs with embedded credentials",
    example: "postgresql://admin:s3cr3t@db.example.com:5432/prod",
  },
  {
    name: "email",
    label: "Email",
    regex: /\b[\w._%+\-]+@[\w.\-]+\.[A-Za-z]{2,}\b/g,
    description: "Email addresses",
    example: "alice@example.com",
  },
  {
    name: "ipv4",
    label: "IPv4",
    regex: /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g,
    description: "IPv4 addresses",
    example: "192.168.1.42",
  },
  {
    name: "credit_card",
    label: "Credit Card",
    regex: /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b/g,
    description: "Credit card numbers",
    example: "4111111111111111",
  },
  {
    name: "shell_prompt",
    label: "Shell Prompt",
    regex: /[\w.\-]+@[\w.\-]+:~[#$] ?/g,
    description: "Shell prompts leaking username@hostname",
    example: "alice@macbook-pro:~$ ",
  },
  {
    name: "generic_secret_assignment",
    label: "Generic Secret",
    regex: /(?:password|passwd|secret|token|api[_\-]?key)\s*[:=]\s*['"][^'"\s]{8,}['"]/gi,
    description: "Generic password/token assignments in code/config",
    example: 'PASSWORD="hunter2_super_secret"',
  },
  {
    name: "long_base64_blob",
    label: "Base64 Blob",
    regex: /(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{60,}={0,2}(?![A-Za-z0-9+/])/g,
    description: "Long base64 blobs (likely encoded secrets/certs)",
    example: "VGhpc0lzQVZlcnlMb25nQmFzZTY0U3RyaW5nVGhhdE1pZ2h0QmVBU2VjcmV0UGF5bG9hZA==",
  },
];

/**
 * Run every pattern against `text`, returning:
 *   { cleaned, matches: [{ pattern, label, start, end, original, mask }] }
 * Non-overlapping matches, earliest-wins strategy.
 */
export function redact(text) {
  if (!text) return { cleaned: text || "", matches: [] };
  const all = [];
  for (const p of PATTERNS) {
    p.regex.lastIndex = 0;
    let m;
    while ((m = p.regex.exec(text)) !== null) {
      all.push({
        pattern: p.name,
        label: p.label,
        start: m.index,
        end: m.index + m[0].length,
        original: m[0],
      });
      if (m[0].length === 0) p.regex.lastIndex++;
    }
  }
  all.sort((a, b) => a.start - b.start || b.end - a.end);
  const chosen = [];
  let lastEnd = -1;
  for (const m of all) {
    if (m.start >= lastEnd) {
      chosen.push(m);
      lastEnd = m.end;
    }
  }
  let cleaned = "";
  let cursor = 0;
  for (const m of chosen) {
    cleaned += text.slice(cursor, m.start);
    m.mask = `[${m.pattern.toUpperCase()}]`;
    cleaned += m.mask;
    cursor = m.end;
  }
  cleaned += text.slice(cursor);
  return { cleaned, matches: chosen };
}
