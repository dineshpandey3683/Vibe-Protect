const $ = (id) => document.getElementById(id);

// Sites where the content script is auto-declared in the manifest.
const WHITELIST = [
  "chat.openai.com",
  "chatgpt.com",
  "claude.ai",
];

function isWhitelisted(hostname) {
  return WHITELIST.some((h) => hostname === h || hostname.endsWith("." + h));
}

// -----------------------------------------------------------------------------
// Current tab status
// -----------------------------------------------------------------------------
async function getActiveTab() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) =>
      resolve(tabs && tabs[0])
    );
  });
}

async function isInjected(tabId) {
  try {
    const [res] = await chrome.scripting.executeScript({
      target: { tabId, allFrames: false },
      func: () => !!window.__vibeProtectInstalled,
    });
    return !!(res && res.result);
  } catch {
    return false;
  }
}

async function refreshSiteStatus() {
  const tab = await getActiveTab();
  const url = tab && tab.url ? new URL(tab.url) : null;
  const hostname = url ? url.hostname : "(no active tab)";
  $("site-host").textContent = hostname;

  const dot = document.querySelector(".status-dot");
  const txt = document.querySelector(".status-text");
  const btn = $("protect-btn");
  const hint = $("hint");

  if (!url || !/^https?:$/.test(url.protocol)) {
    dot.className = "status-dot";
    txt.textContent = "unsupported page";
    txt.className = "status-text";
    btn.hidden = true;
    hint.textContent = "Open a webpage to enable clipboard protection.";
    return;
  }

  if (isWhitelisted(hostname)) {
    dot.className = "status-dot on";
    txt.textContent = "auto-protected";
    txt.className = "status-text on";
    btn.hidden = true;
    hint.textContent = "This site is in the built-in whitelist.";
    return;
  }

  const injected = await isInjected(tab.id);
  if (injected) {
    dot.className = "status-dot on";
    txt.textContent = "protected (this tab)";
    txt.className = "status-text on";
    btn.hidden = true;
    hint.textContent = "Injected for this session — reload the tab to undo.";
  } else {
    dot.className = "status-dot off";
    txt.textContent = "not protected";
    txt.className = "status-text off";
    btn.hidden = false;
    hint.textContent =
      "Vibe Protect only auto-runs on ChatGPT & Claude for privacy. Click above to enable on this tab.";
  }
}

// -----------------------------------------------------------------------------
// On-demand inject (uses activeTab + scripting)
// -----------------------------------------------------------------------------
$("protect-btn").addEventListener("click", async () => {
  const btn = $("protect-btn");
  btn.disabled = true;
  btn.textContent = "injecting…";
  const tab = await getActiveTab();
  try {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id, allFrames: true },
      files: ["redactor.js"],
    });
    btn.textContent = "✓ protected";
    setTimeout(refreshSiteStatus, 300);
  } catch (e) {
    btn.textContent = "inject failed";
    console.error("[vibe-protect] inject failed:", e);
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = "⚠ Protect this site";
    }, 1500);
  }
});

// -----------------------------------------------------------------------------
// Scan clipboard now — just-in-time clipboardRead permission
// -----------------------------------------------------------------------------
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

function vpRedactPopup(text) {
  if (!text) return { cleaned: "", matches: [] };
  const all = [];
  for (const p of VP_PATTERNS) {
    p.regex.lastIndex = 0;
    let m;
    while ((m = p.regex.exec(text)) !== null) {
      all.push({ pattern: p.name, start: m.index, end: m.index + m[0].length });
      if (m[0].length === 0) p.regex.lastIndex++;
    }
  }
  all.sort((a, b) => a.start - b.start || b.end - a.end);
  const chosen = [];
  let last = -1;
  for (const m of all) if (m.start >= last) { chosen.push(m); last = m.end; }
  let cleaned = "", cursor = 0;
  for (const m of chosen) {
    cleaned += text.slice(cursor, m.start);
    cleaned += "[" + m.pattern.toUpperCase() + "]";
    cursor = m.end;
  }
  cleaned += text.slice(cursor);
  return { cleaned, matches: chosen };
}

function setScanStatus(text, tone = "") {
  const el = $("scan-status");
  el.textContent = text || "";
  el.className = "scan-status" + (tone ? " " + tone : "");
}

async function ensureClipboardPermission() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "HAS_CLIPBOARD_ACCESS" }, (resp) => {
      if (resp && resp.status === "allowed") return resolve("allowed");
      chrome.runtime.sendMessage({ type: "REQUEST_CLIPBOARD_ACCESS" }, (r2) =>
        resolve((r2 && r2.status) || "denied")
      );
    });
  });
}

$("scan-btn").addEventListener("click", async () => {
  const btn = $("scan-btn");
  btn.disabled = true;
  setScanStatus("requesting access…");
  const status = await ensureClipboardPermission();
  if (status !== "allowed") {
    setScanStatus("clipboard access denied", "err");
    btn.disabled = false;
    return;
  }
  try {
    const text = await navigator.clipboard.readText();
    const { cleaned, matches } = vpRedactPopup(text);
    if (!matches.length) {
      setScanStatus("clean · nothing to redact");
    } else {
      await navigator.clipboard.writeText(cleaned);
      setScanStatus(`✓ scrubbed ${matches.length} secret(s)`, "ok");
      // mirror it into the stats/feed so the popup updates
      chrome.runtime.sendMessage({
        type: "vp:redaction",
        host: "clipboard://manual-scan",
        count: matches.length,
        patterns: matches.map((m) => m.pattern),
        before_len: text.length,
        after_len: cleaned.length,
        ts: Date.now(),
      });
      setTimeout(refreshStats, 250);
    }
  } catch (e) {
    console.error("[vibe-protect] scan failed:", e);
    setScanStatus("read/write failed", "err");
  } finally {
    btn.disabled = false;
  }
});

// -----------------------------------------------------------------------------
// Stats + feed + toggle
// -----------------------------------------------------------------------------
function renderStats(stats, events) {
  $("events-count").textContent = stats.totalEvents || 0;
  $("secrets-count").textContent = stats.totalSecrets || 0;
  $("enabled").checked = stats.enabled !== false;

  const feed = $("feed");
  feed.innerHTML = "";
  if (!events || events.length === 0) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "No redactions yet. Try copying a key on ChatGPT.";
    feed.appendChild(li);
    return;
  }
  for (const e of events.slice(0, 20)) {
    const li = document.createElement("li");
    const host = document.createElement("span");
    host.className = "host";
    host.title = e.host || "";
    host.textContent = e.host || "(unknown)";
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = `${e.count}× ${(e.patterns || [])[0] || "secret"}`;
    li.appendChild(host);
    li.appendChild(tag);
    feed.appendChild(li);
  }
}

function refreshStats() {
  chrome.storage.sync.get(
    { enabled: true, totalEvents: 0, totalSecrets: 0 },
    (cfg) => {
      chrome.storage.local.get({ events: [] }, (loc) => {
        renderStats(cfg, loc.events || []);
      });
    }
  );
}

$("enabled").addEventListener("change", (e) => {
  chrome.storage.sync.set({ enabled: e.target.checked });
});

$("options-link").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

// -----------------------------------------------------------------------------
// Boot
// -----------------------------------------------------------------------------
refreshStats();
refreshSiteStatus();
setInterval(refreshStats, 1500);
