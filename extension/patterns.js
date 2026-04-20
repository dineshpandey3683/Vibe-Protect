// Vibe Protect — browser extension
// Shared pattern library (non-module version for extension contexts).
/* eslint-disable no-useless-escape */
const VP_PATTERNS = [
  { name: "openai_api_key",        label: "OpenAI API Key",   regex: /sk-(?:proj-)?[A-Za-z0-9_\-]{20,}/g },
  { name: "anthropic_api_key",     label: "Anthropic Key",    regex: /sk-ant-[A-Za-z0-9_\-]{20,}/g },
  { name: "aws_access_key",        label: "AWS Access Key",   regex: /\bAKIA[0-9A-Z]{16}\b/g },
  { name: "aws_secret_key",        label: "AWS Secret Key",   regex: /aws(?:.{0,20})?(?:secret|private)?(?:.{0,20})?['"][0-9a-zA-Z/+]{40}['"]/gi },
  { name: "github_token",          label: "GitHub Token",     regex: /\bgh[pousr]_[A-Za-z0-9]{36,}\b/g },
  { name: "stripe_key",            label: "Stripe Key",       regex: /\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{20,}\b/g },
  { name: "google_api_key",        label: "Google API Key",   regex: /\bAIza[0-9A-Za-z_\-]{35}\b/g },
  { name: "slack_token",           label: "Slack Token",      regex: /\bxox[abpors]-[A-Za-z0-9\-]{10,}\b/g },
  { name: "jwt_token",             label: "JWT",              regex: /\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b/g },
  { name: "private_key_block",     label: "Private Key",      regex: /-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----/g },
  { name: "ssh_public_key",        label: "SSH Public Key",   regex: /ssh-(?:rsa|ed25519|dss) [A-Za-z0-9+/=]{100,}(?: [^\s]+)?/g },
  { name: "db_connection_string",  label: "DB URL",           regex: /\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp):\/\/[^\s:@]+:[^\s:@]+@[^\s/]+/g },
  { name: "email",                 label: "Email",            regex: /\b[\w._%+\-]+@[\w.\-]+\.[A-Za-z]{2,}\b/g },
  { name: "ipv4",                  label: "IPv4",             regex: /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g },
  { name: "credit_card",           label: "Credit Card",      regex: /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b/g },
  { name: "shell_prompt",          label: "Shell Prompt",     regex: /[\w.\-]+@[\w.\-]+:~[#$] ?/g },
  { name: "generic_secret_assignment", label: "Generic Secret", regex: /(?:password|passwd|secret|token|api[_\-]?key)\s*[:=]\s*['"][^'"\s]{8,}['"]/gi },
  { name: "long_base64_blob",      label: "Base64 Blob",      regex: /(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{60,}={0,2}(?![A-Za-z0-9+/])/g },
];

// eslint-disable-next-line no-unused-vars
function vpRedact(text, disabledSet) {
  if (!text) return { cleaned: text || "", matches: [] };
  const all = [];
  for (const p of VP_PATTERNS) {
    if (disabledSet && disabledSet.has(p.name)) continue;
    p.regex.lastIndex = 0;
    let m;
    while ((m = p.regex.exec(text)) !== null) {
      all.push({ pattern: p.name, label: p.label, start: m.index, end: m.index + m[0].length, original: m[0] });
      if (m[0].length === 0) p.regex.lastIndex++;
    }
  }
  all.sort((a, b) => a.start - b.start || b.end - a.end);
  const chosen = [];
  let lastEnd = -1;
  for (const m of all) {
    if (m.start >= lastEnd) { chosen.push(m); lastEnd = m.end; }
  }
  let cleaned = "", cursor = 0;
  for (const m of chosen) {
    cleaned += text.slice(cursor, m.start);
    m.mask = "[" + m.pattern.toUpperCase() + "]";
    cleaned += m.mask;
    cursor = m.end;
  }
  cleaned += text.slice(cursor);
  return { cleaned, matches: chosen };
}

// expose to other extension scripts
if (typeof self !== "undefined") {
  self.VP_PATTERNS = VP_PATTERNS;
  self.vpRedact = vpRedact;
}
