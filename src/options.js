const fields = [
  "backendBaseUrl",
  "proxyToken",
  "model",
  "visionModel",
  "nonApparelPrompt",
  "apparelPortraitPrompt",
  "apparelFinalPrompt",
  "defaultUserPrompt",
  "imageSize",
  "responseDataPath",
  "extraBody"
];

const form = document.querySelector("#settings-form");
const status = document.querySelector("#status");
const saveButton = document.querySelector("#save-button");
const historyGrid = document.querySelector("#history-grid");
const historyEmpty = document.querySelector("#history-empty");
const tabButtons = Array.from(document.querySelectorAll("[data-tab-target]"));
const tabPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));
const lightbox = document.querySelector("#lightbox");
const lightboxImage = document.querySelector("#lightbox-image");
const lightboxClose = document.querySelector("#lightbox-close");
const SETTINGS_KEY = "userSettings";
const GENERATION_RECORDS_KEY = "generationRecords";
const MODEL_MIGRATIONS = {
  "doubao-seedream-4-5-251128": "openai/gpt-5.4-image-2",
  "doubao-seed-1-6-251015": "moonshotai/kimi-k2.6"
};

bootstrap();

async function bootstrap() {
  try {
    closeLightbox();
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
    migrateLegacyModels(settings);
    for (const field of fields) {
      const element = form.elements.namedItem(field);
      if (!element) {
        continue;
      }
      element.value = settings[field] || "";
    }
    bindTabs();
    bindLightbox();
    await renderGenerationRecords();
    setStatus("已加载当前配置。", "info");
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
    setStatus(`已保存 ${formatNow()}`, "success");
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
    const settings = { ...localStorage[SETTINGS_KEY] };
    migrateLegacyModels(settings);
    return settings;
  }
  const syncStorage = await chrome.storage.sync.get([SETTINGS_KEY]);
  const settings = { ...(syncStorage[SETTINGS_KEY] || {}) };
  migrateLegacyModels(settings);
  return settings;
}

function migrateLegacyModels(settings) {
  if (!settings || typeof settings !== "object") {
    return;
  }
  if (settings.model && MODEL_MIGRATIONS[settings.model]) {
    settings.model = MODEL_MIGRATIONS[settings.model];
  }
  if (settings.visionModel && MODEL_MIGRATIONS[settings.visionModel]) {
    settings.visionModel = MODEL_MIGRATIONS[settings.visionModel];
  }
}

function bindTabs() {
  activateTab("history");
  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      activateTab(button.dataset.tabTarget);
    });
  });
}

function activateTab(target) {
  tabButtons.forEach((item) => {
    item.classList.toggle("is-active", item.dataset.tabTarget === target);
  });
  tabPanels.forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.tabPanel === target);
  });
}

async function renderGenerationRecords() {
  const response = await chrome.runtime.sendMessage({ type: "get-generation-records" });
  if (!response?.ok) {
    historyGrid.innerHTML = "";
    historyEmpty.hidden = false;
    historyEmpty.textContent = `加载记录失败：${response?.error || "未知错误"}`;
    return;
  }

  const records = Array.isArray(response.result) ? response.result : [];
  if (!records.length) {
    historyGrid.innerHTML = "";
    historyEmpty.hidden = false;
    historyEmpty.textContent = "还没有生成记录，先去生成一张试试。";
    return;
  }

  historyEmpty.hidden = true;
  historyGrid.innerHTML = records
    .map(
      (record) => `
        <article class="history-card" data-image-url="${escapeHtml(record.imageUrl || "")}">
          <div class="history-image-wrap">
            <img class="history-image" src="${escapeHtml(record.imageUrl || "")}" alt="生成结果" loading="lazy" />
            <div class="history-overlay">
              <div class="history-time">${formatRecordTime(record.createdAt)}</div>
            </div>
          </div>
        </article>
      `
    )
    .join("");

  historyGrid.querySelectorAll(".history-card").forEach((card) => {
    card.addEventListener("click", () => {
      openLightbox(card.dataset.imageUrl || "");
    });
  });
}

function formatRecordTime(value) {
  if (!value) {
    return "刚刚生成";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "刚刚生成";
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function decodeHtml(value) {
  const textarea = document.createElement("textarea");
  textarea.innerHTML = value;
  return textarea.value;
}

function bindLightbox() {
  lightboxClose.addEventListener("click", closeLightbox);
  lightbox.addEventListener("click", (event) => {
    if (event.target === lightbox) {
      closeLightbox();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !lightbox.hidden) {
      closeLightbox();
    }
  });
}

function openLightbox(imageUrl) {
  if (!imageUrl) {
    return;
  }
  lightboxImage.src = decodeHtml(imageUrl);
  lightbox.hidden = false;
}

function closeLightbox() {
  lightbox.hidden = true;
  lightboxImage.removeAttribute("src");
}
