const KEYS = ["captchaButtons"];

const DEFAULTS = {
  captchaButtons: true,
};

function syncForm(values) {
  for (const k of KEYS) {
    const el = document.getElementById(k);
    if (el) el.checked = !!values[k];
  }
}

chrome.storage.local.get(DEFAULTS, (got) => {
  syncForm(chrome.runtime.lastError ? DEFAULTS : got);
});

for (const k of KEYS) {
  const el = document.getElementById(k);
  if (!el) continue;
  el.addEventListener("change", () => {
    chrome.storage.local.set({ [k]: el.checked });
  });
}
