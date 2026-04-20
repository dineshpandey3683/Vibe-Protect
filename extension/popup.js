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
