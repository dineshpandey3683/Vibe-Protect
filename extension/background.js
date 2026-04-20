// Vibe Protect — background service worker.
// Tracks aggregate stats & recent events for the popup.

const MAX_EVENTS = 50;

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.get(
    { enabled: true, disabled: [], totalEvents: 0, totalSecrets: 0 },
    (cfg) => chrome.storage.sync.set(cfg)
  );
});

chrome.runtime.onMessage.addListener((msg, _sender, _sendResponse) => {
  if (msg && msg.type === "vp:redaction") {
    chrome.storage.sync.get({ totalEvents: 0, totalSecrets: 0 }, (cfg) => {
      chrome.storage.sync.set({
        totalEvents: (cfg.totalEvents || 0) + 1,
        totalSecrets: (cfg.totalSecrets || 0) + (msg.count || 0),
      });
    });
    chrome.storage.local.get({ events: [] }, (cfg) => {
      const events = [
        {
          host: msg.host,
          count: msg.count,
          patterns: msg.patterns,
          before_len: msg.before_len,
          after_len: msg.after_len,
          ts: msg.ts,
        },
        ...(cfg.events || []),
      ].slice(0, MAX_EVENTS);
      chrome.storage.local.set({ events });
    });
    try {
      chrome.action.setBadgeText({ text: String(msg.count || "").slice(0, 3) });
      chrome.action.setBadgeBackgroundColor({ color: "#FACC15" });
      setTimeout(() => chrome.action.setBadgeText({ text: "" }), 1800);
    } catch {
      /* ignore */
    }
  }
});
