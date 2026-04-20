// Vibe Protect — redactor.js (content script).
//
// Self-contained: carries its own pattern library so the manifest only has to
// inject a single file. Runs at document_idle in every frame on the whitelisted
// high-risk sites (ChatGPT, Claude). Also injectable on-demand into the
// active tab from the popup via chrome.scripting.executeScript.

(function () {
  if (window.__vibeProtectInstalled) return;
  window.__vibeProtectInstalled = true;

  /* eslint-disable no-useless-escape */
  const VP_PATTERNS = [
    { name: "anthropic_api_key",     regex: /sk-ant-[A-Za-z0-9_\-]{20,}/g },
    { name: "openai_api_key",        regex: /sk-(?:proj-)?[A-Za-z0-9_\-]{20,}/g },
    { name: "aws_access_key",        regex: /\bAKIA[0-9A-Z]{16}\b/g },
    { name: "aws_secret_key",        regex: /aws(?:.{0,20})?(?:secret|private)?(?:.{0,20})?['"][0-9a-zA-Z/+]{40}['"]/gi },
    { name: "github_token",          regex: /\bgh[pousr]_[A-Za-z0-9]{36,}\b/g },
    { name: "stripe_key",            regex: /\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{20,}\b/g },
    { name: "google_api_key",        regex: /\bAIza[0-9A-Za-z_\-]{35}\b/g },
    { name: "slack_token",           regex: /\bxox[abpors]-[A-Za-z0-9\-]{10,}\b/g },
    { name: "jwt_token",             regex: /\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b/g },
    { name: "private_key_block",     regex: /-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----/g },
    { name: "ssh_public_key",        regex: /ssh-(?:rsa|ed25519|dss) [A-Za-z0-9+/=]{100,}(?: [^\s]+)?/g },
    { name: "db_connection_string",  regex: /\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp):\/\/[^\s:@]+:[^\s:@]+@[^\s/]+/g },
    { name: "email",                 regex: /\b[\w._%+\-]+@[\w.\-]+\.[A-Za-z]{2,}\b/g },
    { name: "ipv4",                  regex: /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g },
    { name: "credit_card",           regex: /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b/g },
    { name: "shell_prompt",          regex: /[\w.\-]+@[\w.\-]+:~[#$] ?/g },
    { name: "generic_secret_assignment", regex: /(?:password|passwd|secret|token|api[_\-]?key)\s*[:=]\s*['"][^'"\s]{8,}['"]/gi },
    { name: "long_base64_blob",      regex: /(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{60,}={0,2}(?![A-Za-z0-9+/])/g },
  ];

  function vpRedact(text, disabledSet) {
    if (!text) return { cleaned: text || "", matches: [] };
    const all = [];
    for (const p of VP_PATTERNS) {
      if (disabledSet && disabledSet.has(p.name)) continue;
      p.regex.lastIndex = 0;
      let m;
      while ((m = p.regex.exec(text)) !== null) {
        all.push({ pattern: p.name, start: m.index, end: m.index + m[0].length });
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
      cleaned += "[" + m.pattern.toUpperCase() + "]";
      cursor = m.end;
    }
    cleaned += text.slice(cursor);
    return { cleaned, matches: chosen };
  }

  function getSettings() {
    return new Promise((resolve) => {
      try {
        chrome.storage.sync.get(
          { disabled: [], enabled: true },
          (cfg) => resolve({
            disabled: new Set(cfg.disabled || []),
            enabled: cfg.enabled !== false,
          })
        );
      } catch {
        resolve({ disabled: new Set(), enabled: true });
      }
    });
  }

  async function handleCopy(e) {
    const { enabled, disabled } = await getSettings();
    if (!enabled) return;

    const selection = (window.getSelection && window.getSelection().toString()) || "";
    const sourceText = selection || (e.clipboardData && e.clipboardData.getData("text/plain")) || "";
    if (!sourceText) return;

    const { cleaned, matches } = vpRedact(sourceText, disabled);
    if (!matches || matches.length === 0) return;

    try {
      e.clipboardData.setData("text/plain", cleaned);
      e.preventDefault();
    } catch {
      // best-effort; some rich editors own the event entirely
    }

    try {
      chrome.runtime.sendMessage({
        type: "vp:redaction",
        host: location.host,
        count: matches.length,
        patterns: matches.map((m) => m.pattern),
        before_len: sourceText.length,
        after_len: cleaned.length,
        ts: Date.now(),
      });
    } catch {
      /* background worker asleep — ignore */
    }
  }

  document.addEventListener("copy", handleCopy, true);
  document.addEventListener("cut", handleCopy, true);
})();
