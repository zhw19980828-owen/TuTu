const fields = [
  "backendBaseUrl",
  "proxyToken",
  "model",
  "visionModel",
  "visionSystemPrompt",
  "defaultUserPrompt",
  "imageSize",
  "responseDataPath",
  "extraBody"
];

const form = document.querySelector("#settings-form");
const status = document.querySelector("#status");
const saveButton = document.querySelector("#save-button");
const SETTINGS_KEY = "userSettings";

bootstrap();

async function bootstrap() {
  try {
    setStatus("正在加载当前配置...", "info");
    const defaultsResponse = await chrome.runtime.sendMessage({
      type: "get-default-settings"
    });
    const defaults = defaultsResponse?.ok ? defaultsResponse.result || {} : {};
    const storage = await getSavedSettings();
    const settings = {
      ...defaults,
      ...storage
    };
    for (const field of fields) {
      const element = form.elements.namedItem(field);
      if (!element) {
        continue;
      }
      element.value = settings[field] || "";
    }
    setStatus("当前展示的是最新默认配置叠加你已保存的自定义配置。", "info");
  } catch (error) {
    setStatus(
      `配置加载失败：${error instanceof Error ? error.message : String(error)}`,
      "error"
    );
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {};
  for (const field of fields) {
    const element = form.elements.namedItem(field);
    payload[field] = element?.value?.trim?.() ?? "";
  }

  if (payload.extraBody) {
    try {
      JSON.parse(payload.extraBody);
    } catch (error) {
      setStatus("额外请求体 JSON 格式不正确，请修正后再保存。", "error");
      return;
    }
  }

  try {
    setSaving(true);
    setStatus("正在保存配置...", "info");
    await chrome.storage.local.set({ [SETTINGS_KEY]: payload });
    await chrome.storage.sync.remove(SETTINGS_KEY);
    setStatus(`设置已保存。之后生成会使用你这次保存的配置。保存时间：${formatNow()}`, "success");
  } catch (error) {
    setStatus(
      `保存失败：${error instanceof Error ? error.message : String(error)}`,
      "error"
    );
  } finally {
    setSaving(false);
  }
});

function setSaving(isSaving) {
  if (!saveButton) {
    return;
  }
  saveButton.disabled = isSaving;
  saveButton.textContent = isSaving ? "保存中..." : "保存设置";
}

function setStatus(message, state) {
  status.textContent = message;
  status.dataset.state = state || "info";
}

function formatNow() {
  return new Date().toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

async function getSavedSettings() {
  const localStorage = await chrome.storage.local.get([SETTINGS_KEY]);
  if (localStorage[SETTINGS_KEY]) {
    return localStorage[SETTINGS_KEY];
  }
  const syncStorage = await chrome.storage.sync.get([SETTINGS_KEY]);
  return syncStorage[SETTINGS_KEY] || {};
}
