const BRIDGE_URL = "http://127.0.0.1:47616/api/web-trigger";
const REQUEST_TIMEOUT_MS = 45000;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "trigger_quittok_web_meme") {
    return false;
  }

  handleQuitTokTrigger(message.payload || {}, sender)
    .then(sendResponse)
    .catch((error) => {
      sendResponse({ ok: false, reason: String(error) });
    });

  return true;
});

async function handleQuitTokTrigger(payload, sender) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const body = {
    source: "web-click",
    browser_name: "Microsoft Edge",
    page_url: sender?.tab?.url || payload.page_url || "",
    page_title: sender?.tab?.title || payload.page_title || "",
    element_tag: payload.element_tag || "",
    element_role: payload.element_role || "",
    element_text: payload.element_text || "",
  };

  try {
    const response = await fetch(BRIDGE_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    let data = null;
    try {
      data = await response.json();
    } catch (_) {
      data = null;
    }

    if (!response.ok || !data || !data.ok) {
      return {
        ok: false,
        reason: (data && data.error) || `http-${response.status}`,
      };
    }

    return { ok: true };
  } catch (error) {
    if (error && error.name === "AbortError") {
      return { ok: false, reason: "timeout" };
    }
    return { ok: false, reason: String(error) };
  } finally {
    clearTimeout(timeoutId);
  }
}
