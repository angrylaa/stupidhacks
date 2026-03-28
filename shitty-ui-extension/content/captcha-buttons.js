(function () {
  "use strict";

  const U = window.__SHITTY_UI__;
  const D = window.__SHITTY_DOM__;
  if (!U || !D) return;

  const SKIP_ATTR = "data-shitty-captcha-pass";
  const AD_COUNT = 16;
  const CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const QTE_KEYS = ["W", "A", "S", "D", "Q", "E", "R", "F", "H", "J", "K", "L"];

  /** Match the digit(s) hidden in your color-blind.png (edit if you swap the image). */
  const COLORBLIND_EXPECTED = "74";

  const SLOT_SYM = ["🍒", "💎", "7", "BAR", "🍋"];
  const DICE_FACE = ["\u2680", "\u2681", "\u2682", "\u2683", "\u2684", "\u2685"];

  const G_BLUE = "#4285f4";
  const G_TEXT = "#202124";
  const G_MUTED = "#5f6368";
  const G_BORDER = "#d3d3d3";

  const STEP_HINTS = [
    "1/7 — Type the distorted code.",
    "2/7 — Color vision: enter the digit you see in the plate.",
    "3/7 — Roll until two dice total the target number.",
    "4/7 — Slots: keep spinning until your balance is $0 or less.",
    "5/7 — Drag the ad piece into the gap.",
    "6/7 — Quick time: press the key before time runs out.",
    "7/7 — Wait, then click as soon as you see GO.",
  ];

  function randomChallenge() {
    let s = "";
    for (let i = 0; i < 5; i++) s += CHARS[Math.floor(Math.random() * CHARS.length)];
    return s;
  }

  function randomAdImage(done) {
    const n = 1 + Math.floor(Math.random() * AD_COUNT);
    let url;
    try {
      url = chrome.runtime.getURL("ads/" + n + ".png");
    } catch (_) {
      done(null);
      return;
    }
    const im = new Image();
    im.onload = () => done(im);
    im.onerror = () => done(null);
    im.src = url;
  }

  function recaptchaStyleLogoSvg() {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", "28");
    svg.setAttribute("height", "28");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.style.display = "block";
    svg.style.margin = "0 auto 2px";
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute(
      "d",
      "M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"
    );
    p.setAttribute("fill", G_BLUE);
    svg.appendChild(p);
    return svg;
  }

  function buildPuzzleFromImage(mountEl, im, fail, onSolved) {
    const PUZZLE_MAX_W = 268;
    const PUZZLE_MAX_H = 152;
    const SNAP_PX = 14;

    const nw = im.naturalWidth || im.width;
    const nh = im.naturalHeight || im.height;
    if (nw < 8 || nh < 8) {
      fail("Image too small.");
      return;
    }

    const scale = Math.min(PUZZLE_MAX_W / nw, PUZZLE_MAX_H / nh);
    const dw = Math.max(1, Math.round(nw * scale));
    const dh = Math.max(1, Math.round(nh * scale));

    const pieceW = Math.max(40, Math.min(68, Math.round(dw * 0.22)));
    const pieceH = Math.max(40, Math.min(68, Math.round(dh * 0.22)));

    const margin = 6;
    const holeX = margin + Math.floor(Math.random() * Math.max(1, dw - pieceW - margin * 2));
    const holeY = margin + Math.floor(Math.random() * Math.max(1, dh - pieceH - margin * 2));

    const sx = (holeX / dw) * nw;
    const sy = (holeY / dh) * nh;
    const sw = (pieceW / dw) * nw;
    const sh = (pieceH / dh) * nh;

    mountEl.textContent = "";

    const puzzleRoot = document.createElement("div");
    Object.assign(puzzleRoot.style, {
      position: "relative",
      width: dw + "px",
      margin: "0 auto 10px",
      userSelect: "none",
      touchAction: "none",
    });

    const base = document.createElement("canvas");
    base.width = dw;
    base.height = dh;
    base.style.display = "block";
    base.style.borderRadius = "2px";
    base.style.border = "1px solid #bdbdbd";
    const bctx = base.getContext("2d");
    bctx.drawImage(im, 0, 0, nw, nh, 0, 0, dw, dh);
    bctx.fillStyle = "#9e9e9e";
    bctx.fillRect(holeX, holeY, pieceW, pieceH);
    bctx.strokeStyle = "rgba(0,0,0,0.25)";
    bctx.lineWidth = 1;
    bctx.strokeRect(holeX + 0.5, holeY + 0.5, pieceW - 1, pieceH - 1);

    const piece = document.createElement("canvas");
    piece.width = pieceW;
    piece.height = pieceH;
    Object.assign(piece.style, {
      position: "absolute",
      left: "0px",
      top: "0px",
      cursor: "grab",
      boxShadow: "0 2px 8px rgba(0,0,0,0.35)",
      border: "2px solid #fff",
      borderRadius: "2px",
      zIndex: "2",
    });
    const pctx = piece.getContext("2d");
    pctx.drawImage(im, sx, sy, sw, sh, 0, 0, pieceW, pieceH);

    const railH = 12;
    puzzleRoot.style.height = dh + pieceH + railH + 8 + "px";

    const startX = Math.floor(Math.random() * Math.max(1, dw - pieceW));
    const startY = dh + 8;
    piece.style.left = startX + "px";
    piece.style.top = startY + "px";

    let drag = null;
    let solved = false;

    function rootPoint(clientX, clientY) {
      const r = puzzleRoot.getBoundingClientRect();
      return { x: clientX - r.left, y: clientY - r.top };
    }

    function trySolve() {
      if (solved) return true;
      const left = parseFloat(piece.style.left) || 0;
      const top = parseFloat(piece.style.top) || 0;
      const dx = left - holeX;
      const dy = top - holeY;
      if (Math.hypot(dx, dy) <= SNAP_PX) {
        solved = true;
        piece.style.left = holeX + "px";
        piece.style.top = holeY + "px";
        piece.style.cursor = "default";
        piece.style.boxShadow = "none";
        onSolved();
        return true;
      }
      return false;
    }

    function onPointerDown(e) {
      if (solved) return;
      if (e.pointerType === "mouse" && e.button !== 0) return;
      e.preventDefault();
      piece.setPointerCapture(e.pointerId);
      piece.style.cursor = "grabbing";
      const p = rootPoint(e.clientX, e.clientY);
      const left = parseFloat(piece.style.left) || 0;
      const top = parseFloat(piece.style.top) || 0;
      drag = { ox: p.x - left, oy: p.y - top };
    }

    function onPointerMove(e) {
      if (solved || !drag) return;
      e.preventDefault();
      const p = rootPoint(e.clientX, e.clientY);
      let nx = p.x - drag.ox;
      let ny = p.y - drag.oy;
      const pad = 4;
      nx = Math.max(-pad, Math.min(nx, dw - pieceW + pad));
      ny = Math.max(-pad, Math.min(ny, dh + railH + pieceH));
      piece.style.left = nx + "px";
      piece.style.top = ny + "px";
    }

    function onPointerUp(e) {
      const hadDrag = !!drag;
      drag = null;
      try {
        if (typeof piece.hasPointerCapture === "function" && piece.hasPointerCapture(e.pointerId)) {
          piece.releasePointerCapture(e.pointerId);
        }
      } catch (_) {}
      if (solved) return;
      piece.style.cursor = "grab";
      if (!hadDrag) return;
      if (!trySolve()) fail("Close — align the piece with the gray gap.");
    }

    piece.addEventListener("pointerdown", onPointerDown);
    piece.addEventListener("pointermove", onPointerMove);
    piece.addEventListener("pointerup", onPointerUp);
    piece.addEventListener("pointercancel", onPointerUp);

    puzzleRoot.appendChild(base);
    puzzleRoot.appendChild(piece);
    mountEl.appendChild(puzzleRoot);
  }

  function openCaptchaModal(target, onSuccess) {
    U.ensureHost();

    const root = document.createElement("div");
    Object.assign(root.style, {
      width: "340px",
      maxWidth: "min(96vw, 340px)",
      fontFamily: 'Roboto, "Helvetica Neue", Helvetica, Arial, sans-serif',
      background: "#fafafa",
      border: `1px solid ${G_BORDER}`,
      borderRadius: "3px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.15)",
      overflow: "hidden",
    });

    const mainRow = document.createElement("div");
    Object.assign(mainRow.style, {
      display: "flex",
      alignItems: "center",
      padding: "10px 14px 10px 12px",
      minHeight: "74px",
      background: "#fafafa",
      boxSizing: "border-box",
    });

    const cbOuter = document.createElement("div");
    Object.assign(cbOuter.style, {
      flexShrink: "0",
      width: "30px",
      height: "30px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    });

    const cb = document.createElement("div");
    cb.setAttribute("role", "checkbox");
    cb.setAttribute("aria-checked", "false");
    cb.setAttribute("tabindex", "0");
    Object.assign(cb.style, {
      width: "28px",
      height: "28px",
      boxSizing: "border-box",
      border: "2px solid #c1c1c1",
      borderRadius: "2px",
      background: "#ffffff",
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      transition: "border-color 0.15s ease",
    });

    const cbSpinner = document.createElement("div");
    Object.assign(cbSpinner.style, {
      display: "none",
      width: "22px",
      height: "22px",
      border: `3px solid #e8e8e8`,
      borderTopColor: G_BLUE,
      borderRadius: "50%",
      animation: "shitty-recaptcha-spin 0.7s linear infinite",
    });

    const cbCheck = document.createElement("div");
    cbCheck.textContent = "✓";
    Object.assign(cbCheck.style, {
      display: "none",
      color: "#34a853",
      fontSize: "20px",
      fontWeight: "bold",
      lineHeight: "1",
    });

    cb.appendChild(cbSpinner);
    cb.appendChild(cbCheck);

    const labelCol = document.createElement("div");
    Object.assign(labelCol.style, {
      flex: "1",
      marginLeft: "14px",
      minWidth: "0",
    });
    const mainLabel = document.createElement("div");
    mainLabel.textContent = "I'm not a robot";
    Object.assign(mainLabel.style, {
      fontSize: "15px",
      fontWeight: "400",
      color: G_TEXT,
      lineHeight: "1.35",
    });
    const subHint = document.createElement("div");
    subHint.textContent = "Checkbox required to continue";
    Object.assign(subHint.style, {
      fontSize: "11px",
      color: G_MUTED,
      marginTop: "3px",
    });
    labelCol.appendChild(mainLabel);
    labelCol.appendChild(subHint);

    const brandCol = document.createElement("div");
    Object.assign(brandCol.style, {
      width: "64px",
      flexShrink: "0",
      textAlign: "center",
      paddingLeft: "8px",
      borderLeft: "none",
    });
    brandCol.appendChild(recaptchaStyleLogoSvg());
    const brandTitle = document.createElement("div");
    brandTitle.textContent = "Security check";
    Object.assign(brandTitle.style, {
      fontSize: "9px",
      color: G_MUTED,
      lineHeight: "1.2",
      marginTop: "2px",
    });
    const brandSub = document.createElement("div");
    brandSub.innerHTML = "Privacy · Terms";
    Object.assign(brandSub.style, {
      fontSize: "8px",
      color: "#9aa0a6",
      marginTop: "3px",
      lineHeight: "1.2",
    });
    brandCol.appendChild(brandTitle);
    brandCol.appendChild(brandSub);

    mainRow.appendChild(cbOuter);
    cbOuter.appendChild(cb);
    mainRow.appendChild(labelCol);
    mainRow.appendChild(brandCol);

    const challengeWrap = document.createElement("div");
    Object.assign(challengeWrap.style, {
      display: "none",
      borderTop: `1px solid ${G_BORDER}`,
      background: "#f5f5f5",
      padding: "14px 14px 12px",
    });

    const challengeTitle = document.createElement("div");
    Object.assign(challengeTitle.style, {
      fontSize: "12px",
      color: G_MUTED,
      marginBottom: "4px",
      textAlign: "center",
      lineHeight: "1.35",
    });

    const stageMount = document.createElement("div");
    stageMount.style.minHeight = "36px";

    const err = document.createElement("div");
    Object.assign(err.style, {
      color: "#d93025",
      fontSize: "12px",
      minHeight: "1.2em",
      marginBottom: "6px",
    });

    const btnRow = document.createElement("div");
    Object.assign(btnRow.style, {
      display: "flex",
      gap: "8px",
      alignItems: "center",
      justifyContent: "flex-end",
    });

    const giveUp = document.createElement("button");
    giveUp.type = "button";
    giveUp.textContent = "Cancel";
    Object.assign(giveUp.style, {
      border: "none",
      background: "transparent",
      color: G_MUTED,
      fontSize: "12px",
      cursor: "pointer",
      fontFamily: "inherit",
    });

    btnRow.appendChild(giveUp);

    challengeWrap.appendChild(challengeTitle);
    challengeWrap.appendChild(stageMount);
    challengeWrap.appendChild(err);
    challengeWrap.appendChild(btnRow);

    root.appendChild(mainRow);
    root.appendChild(challengeWrap);

    const { close: closeBackdrop } = U.showBackdrop(root);

    let phase = "checkbox";
    let verifying = false;
    let puzzleFailTimer = null;
    let stageCleanup = null;

    function injectSpinKeyframes() {
      const sh = U.shadow;
      if (!sh || sh.querySelector("#shitty-recaptcha-spin-style")) return;
      const st = document.createElement("style");
      st.id = "shitty-recaptcha-spin-style";
      st.textContent = `@keyframes shitty-recaptcha-spin { to { transform: rotate(360deg); } }`;
      sh.appendChild(st);
    }
    injectSpinKeyframes();

    function clearStage() {
      if (stageCleanup) {
        try {
          stageCleanup();
        } catch (_) {}
        stageCleanup = null;
      }
      stageMount.textContent = "";
    }

    function close() {
      clearStage();
      closeBackdrop();
    }

    function fail(msg) {
      err.textContent = msg;
      root.style.animation = "shake 0.35s ease";
      if (puzzleFailTimer) clearTimeout(puzzleFailTimer);
      puzzleFailTimer = window.setTimeout(() => {
        err.textContent = "";
        puzzleFailTimer = null;
      }, 2200);
      setTimeout(() => {
        root.style.animation = "";
      }, 400);
    }

    function setStepHeader(stepIndex) {
      challengeTitle.textContent = STEP_HINTS[stepIndex];
    }

    function completeAll() {
      clearStage();
      cbCheck.style.display = "block";
      cb.style.borderColor = "#34a853";
      window.setTimeout(() => {
        closeBackdrop();
        onSuccess();
      }, 450);
    }

    function mountStep1Typing() {
      clearStage();
      setStepHeader(0);
      const challenge = randomChallenge();

      const distort = document.createElement("div");
      distort.textContent = challenge.split("").join(" ");
      Object.assign(distort.style, {
        fontSize: "22px",
        fontWeight: "bold",
        letterSpacing: "0.28em",
        textAlign: "center",
        padding: "14px 10px",
        marginBottom: "10px",
        background: "linear-gradient(180deg, #ececec 0%, #d8d8d8 100%)",
        border: "1px solid #bdbdbd",
        borderRadius: "2px",
        color: "#4a148c",
        transform: "skewX(-5deg)",
        textShadow: "1px 1px 0 #fff, 2px 2px 0 rgba(66,133,244,0.35)",
        userSelect: "none",
        fontFamily: "Arial, Helvetica, sans-serif",
      });

      const input = document.createElement("input");
      input.type = "text";
      input.autocomplete = "off";
      input.placeholder = "Enter the characters";
      Object.assign(input.style, {
        width: "100%",
        boxSizing: "border-box",
        padding: "10px 12px",
        borderRadius: "2px",
        border: `1px solid ${G_BORDER}`,
        background: "#ffffff",
        color: G_TEXT,
        fontSize: "14px",
        fontFamily: "inherit",
        marginBottom: "10px",
      });

      const verifyBtn = document.createElement("button");
      verifyBtn.type = "button";
      verifyBtn.textContent = "VERIFY";
      Object.assign(verifyBtn.style, {
        border: "none",
        borderRadius: "2px",
        padding: "8px 20px",
        fontSize: "12px",
        fontWeight: "500",
        fontFamily: "inherit",
        color: "#ffffff",
        background: G_BLUE,
        cursor: "pointer",
        boxShadow: "0 1px 2px rgba(0,0,0,0.2)",
        display: "block",
        marginLeft: "auto",
      });

      function tryTyping() {
        const v = input.value.trim().toUpperCase().replace(/\s/g, "");
        if (v === challenge) {
          mountStep2Colorblind();
        } else {
          fail("Wrong answer. Humans are bad at this too.");
        }
      }

      verifyBtn.addEventListener("click", tryTyping);
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") tryTyping();
      });

      stageCleanup = () => {
        input.blur();
      };

      stageMount.appendChild(distort);
      stageMount.appendChild(input);
      stageMount.appendChild(verifyBtn);
      window.setTimeout(() => input.focus(), 50);
    }

    function mountStep2Colorblind() {
      clearStage();
      setStepHeader(1);

      let plateOk = false;
      const img = document.createElement("img");
      img.alt = "Color vision plate";
      Object.assign(img.style, {
        maxWidth: "100%",
        height: "auto",
        display: "block",
        margin: "0 auto 10px",
        borderRadius: "4px",
        border: "1px solid #ccc",
        background: "#eee",
      });
      try {
        img.src = chrome.runtime.getURL("color-blind.png");
      } catch (_) {
        err.textContent = "Missing color-blind.png.";
      }
      img.onload = () => {
        plateOk = true;
      };
      img.onerror = () => {
        plateOk = false;
        fail("Add color-blind.png next to manifest.json.");
      };

      const cap = document.createElement("div");
      cap.textContent = "Enter the digit you see (numbers only).";
      Object.assign(cap.style, { fontSize: "13px", color: G_TEXT, marginBottom: "8px", textAlign: "center" });

      const input = document.createElement("input");
      input.type = "text";
      input.inputMode = "numeric";
      input.autocomplete = "off";
      input.placeholder = "Digit";
      Object.assign(input.style, {
        width: "100%",
        boxSizing: "border-box",
        padding: "10px 12px",
        borderRadius: "2px",
        border: `1px solid ${G_BORDER}`,
        background: "#ffffff",
        color: G_TEXT,
        fontSize: "16px",
        fontFamily: "inherit",
        marginBottom: "10px",
        textAlign: "center",
      });

      const verifyBtn = document.createElement("button");
      verifyBtn.type = "button";
      verifyBtn.textContent = "VERIFY";
      Object.assign(verifyBtn.style, {
        border: "none",
        borderRadius: "2px",
        padding: "8px 20px",
        fontSize: "12px",
        fontWeight: "500",
        fontFamily: "inherit",
        color: "#ffffff",
        background: G_BLUE,
        cursor: "pointer",
        boxShadow: "0 1px 2px rgba(0,0,0,0.2)",
        display: "block",
        marginLeft: "auto",
      });

      function tryPlate() {
        if (!plateOk) {
          fail("Plate image not loaded yet.");
          return;
        }
        const v = String(input.value).trim();
        if (v === COLORBLIND_EXPECTED) {
          mountStep3Dice();
        } else {
          fail("That does not match our records.");
        }
      }

      verifyBtn.addEventListener("click", tryPlate);
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") tryPlate();
      });

      stageCleanup = () => {
        input.blur();
      };

      stageMount.appendChild(img);
      stageMount.appendChild(cap);
      stageMount.appendChild(input);
      stageMount.appendChild(verifyBtn);
      window.setTimeout(() => input.focus(), 80);
    }

    function mountStep3Dice() {
      clearStage();
      setStepHeader(2);

      const target = 2 + Math.floor(Math.random() * 11);

      const instr = document.createElement("div");
      instr.innerHTML = `Roll the dice until the total is exactly <strong style="color:${G_BLUE}">${target}</strong>.`;
      Object.assign(instr.style, { fontSize: "13px", color: G_TEXT, textAlign: "center", marginBottom: "10px" });

      function dieFaceEl() {
        const d = document.createElement("div");
        d.textContent = "?";
        Object.assign(d.style, {
          width: "52px",
          height: "52px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "34px",
          lineHeight: "1",
          background: "#fff",
          border: `2px solid ${G_BORDER}`,
          borderRadius: "8px",
          boxShadow: "inset 0 1px 2px rgba(0,0,0,0.08)",
        });
        return d;
      }

      const dieRow = document.createElement("div");
      Object.assign(dieRow.style, {
        display: "flex",
        gap: "14px",
        justifyContent: "center",
        alignItems: "center",
        marginBottom: "12px",
      });
      const leftDie = dieFaceEl();
      const plus = document.createElement("span");
      plus.textContent = "+";
      Object.assign(plus.style, { fontSize: "22px", color: G_MUTED, fontWeight: "600" });
      const rightDie = dieFaceEl();
      dieRow.appendChild(leftDie);
      dieRow.appendChild(plus);
      dieRow.appendChild(rightDie);

      const sumLine = document.createElement("div");
      sumLine.textContent = "Total: —";
      Object.assign(sumLine.style, { textAlign: "center", fontSize: "14px", color: G_MUTED, marginBottom: "10px" });

      const rollBtn = document.createElement("button");
      rollBtn.type = "button";
      rollBtn.textContent = "ROLL";
      Object.assign(rollBtn.style, {
        border: "none",
        borderRadius: "2px",
        padding: "10px 28px",
        fontSize: "13px",
        fontWeight: "600",
        fontFamily: "inherit",
        color: "#ffffff",
        background: G_BLUE,
        cursor: "pointer",
        display: "block",
        margin: "0 auto",
        boxShadow: "0 1px 2px rgba(0,0,0,0.2)",
      });

      let rolling = false;
      let diceIv = null;

      rollBtn.addEventListener("click", () => {
        if (rolling) return;
        rolling = true;
        rollBtn.disabled = true;
        rollBtn.style.opacity = "0.65";
        let ticks = 0;
        diceIv = window.setInterval(() => {
          ticks++;
          const s1 = 1 + Math.floor(Math.random() * 6);
          const s2 = 1 + Math.floor(Math.random() * 6);
          leftDie.textContent = DICE_FACE[s1 - 1];
          rightDie.textContent = DICE_FACE[s2 - 1];
          sumLine.textContent = "Total: " + (s1 + s2);
          if (ticks >= 14) {
            if (diceIv) window.clearInterval(diceIv);
            diceIv = null;
            const d1 = 1 + Math.floor(Math.random() * 6);
            const d2 = 1 + Math.floor(Math.random() * 6);
            leftDie.textContent = DICE_FACE[d1 - 1];
            rightDie.textContent = DICE_FACE[d2 - 1];
            const sum = d1 + d2;
            sumLine.textContent = "Total: " + sum;
            sumLine.style.color = sum === target ? "#2e7d32" : G_TEXT;
            rolling = false;
            rollBtn.disabled = false;
            rollBtn.style.opacity = "1";
            if (sum === target) {
              window.setTimeout(() => mountStep4Slots(), 280);
            } else {
              fail(`Rolled ${sum}. You need ${target}.`);
            }
          }
        }, 70);
      });

      stageCleanup = () => {
        if (diceIv) window.clearInterval(diceIv);
        diceIv = null;
        rolling = false;
      };

      stageMount.appendChild(instr);
      stageMount.appendChild(dieRow);
      stageMount.appendChild(sumLine);
      stageMount.appendChild(rollBtn);
    }

    function mountStep4Slots() {
      clearStage();
      setStepHeader(3);

      let balance = 60;

      const sub = document.createElement("div");
      sub.innerHTML =
        "Each spin costs <strong>$10</strong>. Triples pay out (bad). Goal: <strong>$0</strong> or broke.";
      Object.assign(sub.style, { fontSize: "12px", color: G_MUTED, textAlign: "center", marginBottom: "10px" });

      const balEl = document.createElement("div");
      balEl.textContent = "Balance: $60";
      Object.assign(balEl.style, {
        textAlign: "center",
        fontSize: "20px",
        fontWeight: "700",
        color: G_TEXT,
        marginBottom: "10px",
      });

      const reelRow = document.createElement("div");
      Object.assign(reelRow.style, {
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gap: "8px",
        marginBottom: "12px",
      });

      function makeReelCell() {
        const c = document.createElement("div");
        c.textContent = SLOT_SYM[0];
        Object.assign(c.style, {
          background: "#1a1a1a",
          color: "#ffe082",
          borderRadius: "4px",
          border: "2px groove #999",
          padding: "12px 6px",
          textAlign: "center",
          fontSize: "15px",
          fontWeight: "700",
          minHeight: "48px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        });
        return c;
      }

      const cells = [makeReelCell(), makeReelCell(), makeReelCell()];
      cells.forEach((c) => reelRow.appendChild(c));

      const spinBtn = document.createElement("button");
      spinBtn.type = "button";
      spinBtn.textContent = "SPIN (−$10)";
      Object.assign(spinBtn.style, {
        border: "none",
        borderRadius: "2px",
        padding: "10px 24px",
        fontSize: "13px",
        fontWeight: "600",
        fontFamily: "inherit",
        color: "#ffffff",
        background: "#c62828",
        cursor: "pointer",
        display: "block",
        margin: "0 auto",
        boxShadow: "0 1px 2px rgba(0,0,0,0.2)",
      });

      function updateBal() {
        balEl.textContent = "Balance: $" + balance;
        balEl.style.color = balance <= 0 ? "#2e7d32" : G_TEXT;
      }

      let slotIv = null;

      function spinOnce() {
        if (balance <= 0) return;
        balance -= 10;
        let flicker = 0;
        slotIv = window.setInterval(() => {
          flicker++;
          for (let i = 0; i < 3; i++) {
            cells[i].textContent = SLOT_SYM[Math.floor(Math.random() * SLOT_SYM.length)];
          }
          if (flicker > 16) {
            if (slotIv) window.clearInterval(slotIv);
            slotIv = null;
            const a = SLOT_SYM[Math.floor(Math.random() * SLOT_SYM.length)];
            const b = SLOT_SYM[Math.floor(Math.random() * SLOT_SYM.length)];
            const c = SLOT_SYM[Math.floor(Math.random() * SLOT_SYM.length)];
            cells[0].textContent = a;
            cells[1].textContent = b;
            cells[2].textContent = c;
            let gain = 0;
            if (a === b && b === c) gain = 35;
            else if (a === b || b === c || a === c) gain = 14;
            balance += gain;
            updateBal();
            spinBtn.disabled = false;
            spinBtn.style.opacity = "1";
            if (balance <= 0) {
              window.setTimeout(() => mountStep5Puzzle(), 320);
            }
          }
        }, 55);
      }

      spinBtn.addEventListener("click", () => {
        if (balance <= 0) return;
        spinBtn.disabled = true;
        spinBtn.style.opacity = "0.65";
        spinOnce();
      });

      stageCleanup = () => {
        if (slotIv) window.clearInterval(slotIv);
        slotIv = null;
      };

      stageMount.appendChild(sub);
      stageMount.appendChild(balEl);
      stageMount.appendChild(reelRow);
      stageMount.appendChild(spinBtn);
    }

    function mountStep5Puzzle() {
      clearStage();
      setStepHeader(4);
      const loading = document.createElement("div");
      loading.textContent = "Loading puzzle…";
      Object.assign(loading.style, {
        fontSize: "12px",
        color: G_MUTED,
        textAlign: "center",
        padding: "24px 8px",
      });
      stageMount.appendChild(loading);

      randomAdImage((im) => {
        stageMount.textContent = "";
        if (!im) {
          fail("Could not load ads/1.png–ads/16.png.");
          return;
        }
        buildPuzzleFromImage(stageMount, im, fail, function puzzleSolved() {
          mountStep6QTE();
        });
      });
    }

    function mountStep6QTE() {
      clearStage();
      setStepHeader(5);

      const target = QTE_KEYS[Math.floor(Math.random() * QTE_KEYS.length)];
      const totalMs = 2200;
      const t0 = performance.now();

      const prompt = document.createElement("div");
      prompt.innerHTML = `Press <strong style="color:${G_BLUE};font-size:22px">${target}</strong> on your keyboard`;
      Object.assign(prompt.style, {
        textAlign: "center",
        fontSize: "14px",
        color: G_TEXT,
        marginBottom: "10px",
      });

      const barWrap = document.createElement("div");
      Object.assign(barWrap.style, {
        height: "8px",
        background: "#e0e0e0",
        borderRadius: "4px",
        overflow: "hidden",
        marginBottom: "8px",
      });
      const bar = document.createElement("div");
      Object.assign(bar.style, {
        height: "100%",
        width: "100%",
        background: G_BLUE,
        transformOrigin: "left center",
        transition: "transform 0.05s linear",
      });
      barWrap.appendChild(bar);

      const sub = document.createElement("div");
      sub.textContent = "Wrong key eats time. Too slow = retry this step.";
      Object.assign(sub.style, { fontSize: "11px", color: G_MUTED, textAlign: "center" });

      stageMount.appendChild(prompt);
      stageMount.appendChild(barWrap);
      stageMount.appendChild(sub);

      let finished = false;
      let raf = 0;

      function tick(now) {
        if (finished) return;
        const elapsed = now - t0;
        const left = Math.max(0, 1 - elapsed / totalMs);
        bar.style.transform = `scaleX(${left})`;
        if (elapsed >= totalMs) {
          finished = true;
          fail("Too slow. Again.");
          window.removeEventListener("keydown", onKey, true);
          if (raf) cancelAnimationFrame(raf);
          mountStep6QTE();
          return;
        }
        raf = requestAnimationFrame(tick);
      }
      raf = requestAnimationFrame(tick);

      function onKey(e) {
        if (finished) return;
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        const k = e.key.length === 1 ? e.key.toUpperCase() : "";
        if (!k || k < "A" || k > "Z") return;
        e.preventDefault();
        e.stopPropagation();
        if (k === target) {
          finished = true;
          window.removeEventListener("keydown", onKey, true);
          if (raf) cancelAnimationFrame(raf);
          mountStep7Reflex();
        } else {
          fail("Wrong key.");
        }
      }

      window.addEventListener("keydown", onKey, true);

      stageCleanup = () => {
        finished = true;
        window.removeEventListener("keydown", onKey, true);
        if (raf) cancelAnimationFrame(raf);
      };
    }

    function mountStep7Reflex() {
      clearStage();
      setStepHeader(6);

      const status = document.createElement("div");
      status.textContent = "Wait…";
      Object.assign(status.style, {
        textAlign: "center",
        fontSize: "15px",
        fontWeight: "600",
        color: "#e65100",
        marginBottom: "12px",
      });

      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = "Do not click yet";
      Object.assign(btn.style, {
        display: "block",
        width: "100%",
        boxSizing: "border-box",
        padding: "14px 16px",
        fontSize: "15px",
        fontWeight: "600",
        fontFamily: "inherit",
        border: "none",
        borderRadius: "2px",
        cursor: "pointer",
        background: "#bdbdbd",
        color: "#424242",
      });

      const fine = document.createElement("div");
      fine.textContent = "Wait for green GO — early click fails.";
      Object.assign(fine.style, { fontSize: "11px", color: G_MUTED, textAlign: "center", marginTop: "8px" });

      stageMount.appendChild(status);
      stageMount.appendChild(btn);
      stageMount.appendChild(fine);

      let state = "wait";
      let waitTimer = null;
      let goTimer = null;

      waitTimer = window.setTimeout(() => {
        waitTimer = null;
        if (state !== "wait") return;
        state = "go";
        status.textContent = "GO!";
        status.style.color = "#2e7d32";
        btn.textContent = "CLICK NOW";
        btn.style.cursor = "pointer";
        btn.style.background = "#34a853";
        btn.style.color = "#fff";

        goTimer = window.setTimeout(() => {
          goTimer = null;
          if (state !== "go") return;
          state = "missed";
          btn.style.cursor = "not-allowed";
          btn.style.background = "#bdbdbd";
          btn.style.color = "#424242";
          btn.textContent = "Missed";
          fail("Too slow.");
          mountStep7Reflex();
        }, 780);
      }, 700 + Math.random() * 1500);

      btn.addEventListener("click", () => {
        if (state === "wait") {
          if (waitTimer) clearTimeout(waitTimer);
          waitTimer = null;
          fail("Too soon.");
          mountStep7Reflex();
          return;
        }
        if (state === "go") {
          state = "done";
          if (goTimer) clearTimeout(goTimer);
          goTimer = null;
          completeAll();
        }
      });

      stageCleanup = () => {
        state = "done";
        if (waitTimer) clearTimeout(waitTimer);
        if (goTimer) clearTimeout(goTimer);
      };
    }

    function beginChallenges() {
      err.textContent = "";
      mountStep1Typing();
    }

    function runVerifyPhase() {
      if (verifying || phase !== "checkbox") return;
      verifying = true;
      cb.style.borderColor = G_BORDER;
      cbSpinner.style.display = "block";
      cbCheck.style.display = "none";

      window.setTimeout(() => {
        cbSpinner.style.display = "none";
        challengeWrap.style.display = "block";
        phase = "challenge";
        verifying = false;
        beginChallenges();
      }, 1200 + Math.random() * 600);
    }

    cb.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      if (phase === "checkbox") runVerifyPhase();
    });
    cb.addEventListener("keydown", (ev) => {
      if (ev.key === " " || ev.key === "Enter") {
        ev.preventDefault();
        if (phase === "checkbox") runVerifyPhase();
      }
    });

    giveUp.addEventListener("click", () => close());
  }

  document.addEventListener(
    "click",
    function (e) {
      const s = U.settings;
      if (!s || !s.captchaButtons) return;

      if (e.composedPath().some((n) => n instanceof Element && n.id === "shitty-ui-extension-root")) return;

      const t = e.target;
      if (t && t.closest && t.closest("[data-shitty-ui]")) return;

      const clickable = D.findCaptchableFromEvent(e);
      if (!clickable) return;
      if (D.elementIsDisabled(clickable)) return;
      if (clickable.hasAttribute(SKIP_ATTR)) {
        clickable.removeAttribute(SKIP_ATTR);
        return;
      }

      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();

      openCaptchaModal(clickable, function () {
        clickable.setAttribute(SKIP_ATTR, "1");
        clickable.click();
      });
    },
    true
  );
})();
