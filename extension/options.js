/* global VP_PATTERNS */
const list = document.getElementById("list");

function row(p, disabledSet) {
  const li = document.createElement("li");
  const left = document.createElement("div");
  const name = document.createElement("div");
  name.className = "pname";
  name.textContent = p.label + "  ·  " + p.name;
  const desc = document.createElement("div");
  desc.className = "pdesc";
  desc.textContent = String(p.regex).slice(0, 80) + (String(p.regex).length > 80 ? "…" : "");
  left.appendChild(name);
  left.appendChild(desc);
  const right = document.createElement("label");
  right.className = "switch";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = !disabledSet.has(p.name);
  const slider = document.createElement("span");
  slider.className = "slider";
  right.appendChild(input);
  right.appendChild(slider);
  input.addEventListener("change", () => {
    chrome.storage.sync.get({ disabled: [] }, (cfg) => {
      const s = new Set(cfg.disabled || []);
      if (input.checked) s.delete(p.name);
      else s.add(p.name);
      chrome.storage.sync.set({ disabled: Array.from(s) });
    });
  });
  li.appendChild(left);
  li.appendChild(right);
  return li;
}

chrome.storage.sync.get({ disabled: [] }, (cfg) => {
  const disabled = new Set(cfg.disabled || []);
  for (const p of VP_PATTERNS) list.appendChild(row(p, disabled));
});
