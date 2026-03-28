(function () {
  "use strict";

  window.__SHITTY_UI__ = window.__SHITTY_UI__ || {};

  function ensureHost() {
    if (window.__SHITTY_UI__.host) return window.__SHITTY_UI__;

    const host = document.createElement("div");
    host.id = "shitty-ui-extension-root";
    host.setAttribute("data-shitty-ui", "true");
    Object.assign(host.style, {
      position: "fixed",
      inset: "0",
      pointerEvents: "none",
      zIndex: "2147483646",
    });

    const shadow = host.attachShadow({ mode: "closed" });
    const sheet = document.createElement("style");
    sheet.textContent = `
      :host { all: initial; }
      * {
        box-sizing: border-box;
        font-family: Tahoma, Arial, Helvetica, sans-serif;
      }
      .backdrop {
        pointer-events: auto;
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.55);
        display: flex;
        align-items: center;
        justify-content: center;
      }
      @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
      }
      .panel {
        pointer-events: auto;
        background: #f7f7f7;
        background: linear-gradient(to bottom, #ffffff 0%, #f0f0f0 100%);
        color: #333333;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 18px 20px;
        max-width: min(92vw, 420px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25), inset 0 1px 0 #ffffff;
      }
      .panel h2 {
        margin: 0 0 6px;
        font-size: 18px;
        font-weight: bold;
        color: #2c3e50;
        letter-spacing: 0;
      }
      .panel p.sub {
        margin: 0 0 14px;
        font-size: 12px;
        color: #666666;
        line-height: 1.45;
        opacity: 1;
      }
      .row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        align-items: center;
      }
      button.btn {
        cursor: pointer;
        border-radius: 3px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: bold;
        font-family: Tahoma, Arial, Helvetica, sans-serif;
      }
      button.btn-primary {
        color: #ffffff;
        border: 1px solid #2a6496;
        background: #428bca;
        background: linear-gradient(to bottom, #5cb0e8 0%, #428bca 100%);
        text-shadow: 0 -1px 0 rgba(0, 0, 0, 0.2);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25);
      }
      button.btn-primary:hover {
        background: linear-gradient(to bottom, #6db6eb 0%, #3071a9 100%);
      }
      button.btn-primary:active {
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
      }
      button.btn-ghost {
        color: #333333;
        border: 1px solid #b3b3b3;
        background: #fafafa;
        background: linear-gradient(to bottom, #ffffff 0%, #e6e6e6 100%);
        text-shadow: 0 1px 0 rgba(255, 255, 255, 0.8);
      }
      button.btn-ghost:hover {
        background: linear-gradient(to bottom, #ffffff 0%, #dcdcdc 100%);
      }
      button.btn-ghost:active {
        background: #e0e0e0;
        box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.12);
      }
      .error-msg {
        color: #c9302c;
        font-size: 12px;
        margin-top: 8px;
        min-height: 1.2em;
      }
    `;
    shadow.appendChild(sheet);

    const portal = document.createElement("div");
    portal.className = "shitty-portal";
    Object.assign(portal.style, { pointerEvents: "none" });
    shadow.appendChild(portal);

    document.documentElement.appendChild(host);

    window.__SHITTY_UI__.host = host;
    window.__SHITTY_UI__.shadow = shadow;
    window.__SHITTY_UI__.portal = portal;

    return window.__SHITTY_UI__;
  }

  window.__SHITTY_UI__.ensureHost = ensureHost;

  window.__SHITTY_UI__.showBackdrop = function (innerNode) {
    const { portal } = ensureHost();
    const backdrop = document.createElement("div");
    backdrop.className = "backdrop";
    backdrop.appendChild(innerNode);
    portal.appendChild(backdrop);
    portal.style.pointerEvents = "auto";
    setHostPointerBlock(true);

    function close() {
      backdrop.remove();
      if (!portal.children.length) {
        portal.style.pointerEvents = "none";
        setHostPointerBlock(false);
      }
    }

    return { backdrop, close };
  };

  function setHostPointerBlock(on) {
    const { host } = ensureHost();
    host.style.pointerEvents = on ? "auto" : "none";
  }
})();
