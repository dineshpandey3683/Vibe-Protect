const $ = (id) => document.getElementById(id);

function render(stats, events) {
  $("events-count").textContent = stats.totalEvents || 0;
  $("secrets-count").textContent = stats.totalSecrets || 0;
  $("enabled").checked = stats.enabled !== false;

  const feed = $("feed");
  feed.innerHTML = "";
  if (!events || events.length === 0) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "No redactions yet. Try copying an API key.";
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

function refresh() {
  chrome.storage.sync.get(
    { enabled: true, totalEvents: 0, totalSecrets: 0 },
    (cfg) => {
      chrome.storage.local.get({ events: [] }, (loc) => {
        render(cfg, loc.events || []);
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

refresh();
setInterval(refresh, 1500);
