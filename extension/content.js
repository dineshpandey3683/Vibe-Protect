// Vibe Protect — content script. Runs in every frame of every page.
// Intercepts `copy` and `cut` events, redacts the selection, and pushes the
// cleaned text back into the clipboard. Also reports the event to the
// background worker for the popup history.

(function () {
  function getDisabledSet() {
    return new Promise((resolve) => {
      try {
        chrome.storage.sync.get({ disabled: [], enabled: true }, (cfg) => {
          resolve({ disabled: new Set(cfg.disabled || []), enabled: cfg.enabled !== false });
        });
      } catch {
        resolve({ disabled: new Set(), enabled: true });
      }
    });
  }

  async function handleCopy(e) {
    const state = await getDisabledSet();
    if (!state.enabled) return;

    const selection = (window.getSelection && window.getSelection().toString()) || "";
    const sourceText = selection || (e.clipboardData && e.clipboardData.getData("text/plain")) || "";
    if (!sourceText) return;

    // eslint-disable-next-line no-undef
    const { cleaned, matches } = vpRedact(sourceText, state.disabled);
    if (!matches || matches.length === 0) return;

    try {
      e.clipboardData.setData("text/plain", cleaned);
      e.preventDefault();
    } catch {
      // fallthrough: best-effort
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
      /* ignore */
    }
  }

  document.addEventListener("copy", handleCopy, true);
  document.addEventListener("cut", handleCopy, true);
})();
