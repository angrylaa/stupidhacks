(function () {
  "use strict";

  const SHITTY_ROOT_ID = "shitty-ui-extension-root";

  const D = {};
  window.__SHITTY_DOM__ = D;

  D.walkComposedAncestors = function walkComposedAncestors(start, visit) {
    let el = start && start.nodeType === Node.TEXT_NODE ? start.parentElement : start;
    while (el) {
      if (el instanceof Element) {
        if (visit(el) === false) return;
      }
      if (el.parentElement) el = el.parentElement;
      else {
        const root = el.getRootNode();
        if (root instanceof ShadowRoot && root.host) el = root.host;
        else break;
      }
    }
  };

  D.elementIsDisabled = function elementIsDisabled(el) {
    if (!(el instanceof Element)) return true;
    if (el.hasAttribute("disabled")) return true;
    if (el.getAttribute("aria-disabled") === "true") return true;
    return false;
  };

  function isJunkHref(href) {
    if (!href) return true;
    const h = href.trim();
    return h === "#" || h.toLowerCase().startsWith("javascript:");
  }

  const CAPTCHA_ROLES = new Set([
    "button",
    "menuitem",
    "menuitemcheckbox",
    "menuitemradio",
    "tab",
    "switch",
  ]);

  D.findCaptchableFromNode = function findCaptchableFromNode(start) {
    let found = null;
    D.walkComposedAncestors(start, (el) => {
      if (!(el instanceof HTMLElement)) return;
      if (el.closest?.("[data-shitty-ui]")) {
        found = null;
        return false;
      }
      const tag = el.tagName;
      if (tag === "BUTTON") {
        if (!D.elementIsDisabled(el)) {
          found = el;
          return false;
        }
        return;
      }
      if (tag === "INPUT") {
        const t = (el.type || "").toLowerCase();
        if (t === "submit" || t === "button" || t === "reset" || t === "image") {
          if (!D.elementIsDisabled(el)) {
            found = el;
            return false;
          }
        }
        return;
      }
      const role = el.getAttribute("role")?.toLowerCase();
      if (role && CAPTCHA_ROLES.has(role)) {
        if (!D.elementIsDisabled(el)) {
          found = el;
          return false;
        }
        return;
      }
      if (tag === "A" && el.hasAttribute("href")) {
        const h = el.getAttribute("href") || "";
        if (!isJunkHref(h)) return;
        if (!D.elementIsDisabled(el)) {
          found = el;
          return false;
        }
        return;
      }
      if (role === "link" && isJunkHref(el.getAttribute("href"))) {
        if (!D.elementIsDisabled(el)) {
          found = el;
          return false;
        }
        return;
      }
    });
    return found;
  };

  D.findCaptchableFromEvent = function findCaptchableFromEvent(e) {
    if (e.composedPath().some((n) => n instanceof Element && n.id === SHITTY_ROOT_ID)) return null;
    const t = e.target;
    if (t && typeof t.closest === "function" && t.closest("[data-shitty-ui]")) return null;
    for (const n of e.composedPath()) {
      if (!(n instanceof Element)) continue;
      if (n.id === SHITTY_ROOT_ID) return null;
      const hit = D.findCaptchableFromNode(n);
      if (hit) return hit;
    }
    return null;
  };

  const TEXT_ROLES = new Set(["textbox", "searchbox"]);

  D.isInsideAriaCombobox = function isInsideAriaCombobox(el) {
    let n = el;
    for (let i = 0; i < 24 && n; i++) {
      if (n instanceof Element && n.getAttribute("role")?.toLowerCase() === "combobox") return true;
      if (n.parentElement) n = n.parentElement;
      else {
        const r = n.getRootNode();
        if (r instanceof ShadowRoot && r.host) n = r.host;
        else break;
      }
    }
    return false;
  };

  D.isTextFieldElement = function isTextFieldElement(el) {
    if (!(el instanceof Element)) return false;
    if (el.closest?.("[data-shitty-ui]")) return false;
    if (el instanceof HTMLTextAreaElement) {
      if (D.isInsideAriaCombobox(el)) return false;
      return !el.readOnly && !el.disabled;
    }
    if (el instanceof HTMLInputElement) {
      if (el.readOnly || el.disabled) return false;
      if (D.isInsideAriaCombobox(el)) return false;
      const t = (el.type || "text").toLowerCase();
      const ok = ["text", "search", "email", "url", "tel", "password", "number"];
      return ok.includes(t);
    }
    if (el.getAttribute("contenteditable") === "true") return true;
    const role = el.getAttribute("role")?.toLowerCase();
    if (role && TEXT_ROLES.has(role)) {
      if (el.getAttribute("aria-readonly") === "true") return false;
      if (D.elementIsDisabled(el)) return false;
      return true;
    }
    return false;
  };

  D.findTextFieldFromEventTarget = function findTextFieldFromEventTarget(target) {
    if (!(target instanceof Node)) return null;
    let found = null;
    D.walkComposedAncestors(target, (el) => {
      if (!(el instanceof Element)) return;
      if (el.id === SHITTY_ROOT_ID) {
        found = null;
        return false;
      }
      if (el.closest?.("[data-shitty-ui]")) {
        found = null;
        return false;
      }
      if (D.isTextFieldElement(el)) {
        found = el;
        return false;
      }
    });
    return found;
  };

  D.getTextFieldValue = function getTextFieldValue(el) {
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return el.value;
    if (el.isContentEditable) return (el.innerText || el.textContent || "").replace(/\u200b/g, "");
    return (el.textContent || "").replace(/\u200b/g, "");
  };

  D.setTextFieldValue = function setTextFieldValue(el, text) {
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
      const proto =
        el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const desc = Object.getOwnPropertyDescriptor(proto, "value");
      if (desc && desc.set) desc.set.call(el, text);
      else el.value = text;
      return;
    }
    if (el.isContentEditable) {
      el.textContent = text;
      return;
    }
    el.textContent = text;
  };

  function findListboxForHost(host) {
    const raw = host.getAttribute("aria-controls") || host.getAttribute("aria-owns") || "";
    const ids = raw.trim().split(/\s+/).filter(Boolean);
    const tryResolve = (id) => {
      if (!id) return null;
      const candidates = [];
      const r = host.getRootNode();
      if (r instanceof ShadowRoot) candidates.push(r);
      candidates.push(document);
      for (const scope of candidates) {
        try {
          const byId = scope.getElementById ? scope.getElementById(id) : null;
          if (!byId) continue;
          if (byId.getAttribute("role") === "listbox") return byId;
          const inner = byId.querySelector('[role="listbox"]');
          if (inner) return inner;
        } catch (_) {}
      }
      try {
        const g = document.getElementById(id);
        if (g) {
          if (g.getAttribute("role") === "listbox") return g;
          const inner = g.querySelector('[role="listbox"]');
          if (inner) return inner;
        }
      } catch (_) {}
      return null;
    };
    for (const id of ids) {
      const lb = tryResolve(id);
      if (lb) return lb;
    }
    let lb = host.querySelector('[role="listbox"]');
    if (lb) return lb;
    if (host.shadowRoot) {
      lb = findListboxInShadowTree(host.shadowRoot, 6);
      if (lb) return lb;
    }
    return null;
  }

  function findListboxInShadowTree(root, depth) {
    if (!root || depth <= 0) return null;
    const direct = root.querySelector('[role="listbox"]');
    if (direct) return direct;
    const nodes = root.querySelectorAll("*");
    for (let i = 0; i < nodes.length; i++) {
      const el = nodes[i];
      if (el.shadowRoot) {
        const inner = findListboxInShadowTree(el.shadowRoot, depth - 1);
        if (inner) return inner;
      }
    }
    return null;
  }

  function collectOptionElements(listbox) {
    return Array.from(listbox.querySelectorAll('[role="option"]')).filter((o) => {
      if (o.getAttribute("aria-disabled") === "true") return false;
      if (o.getAttribute("aria-hidden") === "true") return false;
      if (o.hasAttribute("hidden")) return false;
      return true;
    });
  }

  D.findSelectLikeFromEvent = function findSelectLikeFromEvent(e) {
    if (e.composedPath().some((n) => n instanceof Element && n.id === SHITTY_ROOT_ID)) return null;

    let native = null;
    let ariaHost = null;

    for (const n of e.composedPath()) {
      if (!(n instanceof Element)) continue;
      if (n instanceof HTMLSelectElement && !n.disabled && !D.elementIsDisabled(n)) native = n;
      if (n instanceof HTMLLabelElement && n.control instanceof HTMLSelectElement && !n.control.disabled) {
        native = n.control;
      }
      const role = n.getAttribute("role")?.toLowerCase();
      if (role === "combobox" && !D.elementIsDisabled(n)) ariaHost = n;
      const pop = n.getAttribute("aria-haspopup");
      if (
        (pop === "listbox" || pop === "menu") &&
        !D.elementIsDisabled(n) &&
        !ariaHost &&
        (n.tagName === "BUTTON" ||
          n.tagName === "INPUT" ||
          role === "button" ||
          n.hasAttribute("tabindex"))
      ) {
        ariaHost = n;
      }
      if (
        n instanceof HTMLInputElement &&
        !n.disabled &&
        (role === "combobox" || pop === "listbox")
      ) {
        ariaHost = n;
      }
    }

    if (native) return { kind: "native", el: native };
    if (ariaHost) return { kind: "aria", host: ariaHost };
    return null;
  };

  D.buildSlotModel = function buildSlotModel(ctx) {
    if (!ctx) return null;
    if (ctx.kind === "native") {
      const el = ctx.el;
      const opts = Array.from(el.options).map((o) => ({
        label: (o.textContent || "").trim() || o.value,
      }));
      if (!opts.length) return null;
      return {
        labels: opts.map((o) => o.label),
        apply: (index) => {
          el.selectedIndex = index;
          el.dispatchEvent(new Event("input", { bubbles: true }));
          el.dispatchEvent(new Event("change", { bubbles: true }));
        },
      };
    }

    const host = ctx.host;
    if (D.elementIsDisabled(host)) return null;

    const innerSelect = host.querySelector("select:not([disabled])");
    if (innerSelect instanceof HTMLSelectElement) return D.buildSlotModel({ kind: "native", el: innerSelect });

    const listbox = findListboxForHost(host);
    if (!listbox) return null;

    const optionEls = collectOptionElements(listbox);
    if (!optionEls.length) return null;

    const labels = optionEls.map((o) => {
      const t = (o.textContent || "").trim();
      return t || o.getAttribute("aria-label") || o.getAttribute("data-value") || "—";
    });

    return {
      labels,
      apply: (index) => {
        const opt = optionEls[index];
        if (!opt) return;
        opt.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, view: window }));
        opt.click();
        const input = host.querySelector('input:not([type="hidden"])');
        if (input) {
          input.dispatchEvent(new Event("input", { bubbles: true }));
          input.dispatchEvent(new Event("change", { bubbles: true }));
        }
        host.dispatchEvent(new Event("input", { bubbles: true }));
        host.dispatchEvent(new Event("change", { bubbles: true }));
      },
    };
  };

  D.findComboboxHostFromNode = function findComboboxHostFromNode(start) {
    let found = null;
    D.walkComposedAncestors(start, (el) => {
      if (!(el instanceof Element)) return;
      const role = el.getAttribute("role")?.toLowerCase();
      if (role === "combobox") {
        found = el;
        return false;
      }
      const pop = el.getAttribute("aria-haspopup");
      if (
        (pop === "listbox" || pop === "menu") &&
        (el.tagName === "BUTTON" || role === "button" || el.tagName === "INPUT")
      ) {
        found = el;
        return false;
      }
    });
    return found;
  };
})();
