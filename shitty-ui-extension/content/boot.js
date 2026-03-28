(function () {
  "use strict";

  const U = window.__SHITTY_UI__;
  if (!U) return;

  const DEFAULTS = {
    captchaButtons: true,
  };

  U.settings = { ...DEFAULTS };

  function apply(data) {
    U.settings = { ...DEFAULTS, ...data };
  }

  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(DEFAULTS, (got) => {
      apply(chrome.runtime.lastError ? {} : got);
    });
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area !== "local") return;
      const next = { ...U.settings };
      for (const k of Object.keys(DEFAULTS)) {
        if (changes[k]) next[k] = changes[k].newValue;
      }
      U.settings = next;
    });
  }
})();
