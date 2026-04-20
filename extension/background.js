// Vibe Protect — background service worker.
// * Tracks aggregate redaction stats & recent events for the popup.
// * Mediates just-in-time permission requests for optional permissions
//   (currently: clipboardRead), keeping the install-time footprint minimal.

const MAX_EVENTS = 50;

// ---------------------------------------------------------- install defaults
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.get(
    { enabled: true, disabled: [], totalEvents: 0, totalSecrets: 0 },
    (cfg) => chrome.storage.sync.set(cfg)
  );
});

// --------------------------------------------------------------- message bus
chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  // 1) redaction event reported by redactor.js --------------------------------
  if (request && request.type === "vp:redaction") {
    chrome.storage.sync.get({ totalEvents: 0, totalSecrets: 0 }, (cfg) => {
      chrome.storage.sync.set({
        totalEvents: (cfg.totalEvents || 0) + 1,
        totalSecrets: (cfg.totalSecrets || 0) + (request.count || 0),
      });
    });
    chrome.storage.local.get({ events: [] }, (cfg) => {
      const events = [
        {
          host: request.host,
          count: request.count,
          patterns: request.patterns,
          before_len: request.before_len,
          after_len: request.after_len,
          ts: request.ts,
        },
        ...(cfg.events || []),
      ].slice(0, MAX_EVENTS);
      chrome.storage.local.set({ events });
    });
    try {
      chrome.action.setBadgeText({ text: String(request.count || "").slice(0, 3) });
      chrome.action.setBadgeBackgroundColor({ color: "#FACC15" });
      setTimeout(() => chrome.action.setBadgeText({ text: "" }), 1800);
    } catch {
      /* ignore */
    }
    return false; // sync — no sendResponse needed
  }

  // 2) just-in-time clipboardRead permission request --------------------------
  // Asked for from the popup (user-gesture-originated) before we call
  // navigator.clipboard.readText(). Keeps the install-time footprint minimal:
  // no clipboard access unless the user explicitly opts in.
  if (request && request.type === "REQUEST_CLIPBOARD_ACCESS") {
    chrome.permissions.request(
      { permissions: ["clipboardRead"] },
      (granted) => {
        sendResponse({ status: granted ? "allowed" : "denied" });
      }
    );
    return true; // async response
  }

  // 3) let the popup query whether clipboardRead is already granted -----------
  if (request && request.type === "HAS_CLIPBOARD_ACCESS") {
    chrome.permissions.contains(
      { permissions: ["clipboardRead"] },
      (has) => sendResponse({ status: has ? "allowed" : "denied" })
    );
    return true; // async response
  }

  // 4) let the popup revoke clipboardRead if the user changes their mind ------
  if (request && request.type === "REVOKE_CLIPBOARD_ACCESS") {
    chrome.permissions.remove(
      { permissions: ["clipboardRead"] },
      (removed) => sendResponse({ status: removed ? "revoked" : "kept" })
    );
    return true; // async response
  }

  return false;
});
