const fields = [
  "backendBaseUrl",
  "proxyToken",
  "model",
  "visionModel",
  "nonApparelPrompt",
  "apparelFinalPrompt",
  "defaultUserPrompt",
  "imageResolution",
  "imageAspectRatio",
  "responseDataPath",
  "extraBody"
];

const form = document.querySelector("#settings-form");
const status = document.querySelector("#status");
const saveButton = document.querySelector("#save-button");
const historyGrid = document.querySelector("#history-grid");
const historyEmpty = document.querySelector("#history-empty");
const runningSummary = document.querySelector("#running-summary");
const tabButtons = Array.from(document.querySelectorAll("[data-tab-target]"));
const tabPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));
const lightbox = document.querySelector("#lightbox");
const lightboxImage = document.querySelector("#lightbox-image");
const lightboxDetail = document.querySelector("#lightbox-detail");
const lightboxClose = document.querySelector("#lightbox-close");
const SETTINGS_KEY = "userSettings";
const GENERATION_RECORDS_KEY = "generationRecords";
const LOCAL_TEST_SETTINGS = {
  backendBaseUrl: "http://127.0.0.1:8787",
  proxyToken: "",
  model: "dreamina/image2image:5.0Pro",
  visionModel: "kimi-k2.6",
  defaultUserPrompt: ""
};
const MODEL_MIGRATIONS = {
  "doubao-seedream-4-5-251128": "dreamina/image2image:5.0Pro",
  "dreamina/image2image:4.7": "dreamina/image2image:5.0Pro",
  "dreamina/image2image:5.0": "dreamina/image2image:5.0Pro",
  "doubao-seed-1-6-251015": "kimi-k2.6",
  "moonshotai/kimi-k2.6": "kimi-k2.6"
};

bootstrap();

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === "local" && changes[GENERATION_RECORDS_KEY]) {
    renderGenerationRecords().catch(() => {});
  }
});

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
      ...storage,
      ...LOCAL_TEST_SETTINGS
    };
    settings.nonApparelPrompt = defaults.nonApparelPrompt || settings.nonApparelPrompt;
    settings.apparelFinalPrompt = defaults.apparelFinalPrompt || settings.apparelFinalPrompt;
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
  const legacyImageSize = String(settings.imageSize || "").trim().toLowerCase();
  if (!settings.imageResolution) {
    settings.imageResolution = "1k";
  }
  if (!settings.imageAspectRatio) {
    settings.imageAspectRatio = parseAspectRatio(legacyImageSize) ? legacyImageSize : "follow";
  }
}

function parseAspectRatio(value) {
  return /^(21:9|16:9|3:2|4:3|1:1|3:4|2:3|9:16)$/.test(String(value || ""));
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
    runningSummary.hidden = true;
    runningSummary.textContent = "";
    historyEmpty.hidden = false;
    historyEmpty.textContent = `加载记录失败：${response?.error || "未知错误"}`;
    return;
  }

  const records = (Array.isArray(response.result) ? response.result : [])
    .filter((record) => Boolean(record?.status || record?.resultImageDataUrl || record?.imageUrl))
    .sort((left, right) => getRecordTimestamp(right) - getRecordTimestamp(left));
  const runningCount = records.filter((record) => record.status === "running").length;
  runningSummary.hidden = runningCount === 0;
  runningSummary.textContent = runningCount ? `${runningCount} 个任务生成中` : "";
  if (!records.length) {
    historyGrid.innerHTML = "";
    historyEmpty.hidden = false;
    historyEmpty.textContent = "还没有生成记录，先去生成一张试试。";
    return;
  }

  historyEmpty.hidden = true;
  historyGrid.innerHTML = records
    .map((record) => {
      const imageUrl = record.imageUrl || "";
      const displayImageUrl = record.resultImageDataUrl || imageUrl;
      const recordId = record.id || imageUrl;
      const recordStatus = record.status || (displayImageUrl ? "done" : "error");
      if (recordStatus === "running") {
        const background = record.referenceImageUrl
          ? `<img class="history-placeholder-image" src="${escapeHtml(record.referenceImageUrl)}" alt="任务参考图" loading="lazy" />`
          : "";
        return `
          <article class="history-card is-running" data-record-id="${escapeHtml(recordId)}">
            <div class="history-image-wrap">
              ${background}
              <div class="history-placeholder">
                <span class="history-spinner" aria-hidden="true"></span>
                <strong>正在生成</strong>
                <small>${escapeHtml(record.stageLabel || "正在分析参考图")}</small>
              </div>
              <div class="history-overlay"><div class="history-time">${formatRecordTime(record.createdAt)}</div></div>
            </div>
          </article>
        `;
      }
      if (recordStatus === "error" || !displayImageUrl) {
        return `
          <article class="history-card is-error" data-record-id="${escapeHtml(recordId)}">
            <div class="history-image-wrap">
              <div class="history-placeholder">
                <span class="history-error-mark" aria-hidden="true">!</span>
                <strong>生成失败</strong>
                <button class="history-retry-button" type="button" data-retry-record="${escapeHtml(recordId)}">重试</button>
              </div>
              <div class="history-overlay"><div class="history-time">${formatRecordTime(record.createdAt)}</div></div>
            </div>
          </article>
        `;
      }
      return `
        <article class="history-card is-done" data-record-id="${escapeHtml(recordId)}">
          <div class="history-image-wrap">
            <img class="history-image" src="${escapeHtml(displayImageUrl)}" alt="生成结果" loading="lazy" />
            <div class="history-overlay">
              <div class="history-time">${formatRecordTime(record.createdAt)}</div>
              <button class="history-download-button" type="button" data-download-record="${escapeHtml(recordId)}" aria-label="下载生成结果">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 3v11m0 0 4-4m-4 4-4-4M5 18v2h14v-2" />
                </svg>
                <span>下载</span>
              </button>
            </div>
          </div>
        </article>
      `;
    })
    .join("");

  const recordMap = new Map(records.map((record) => [record.id || record.imageUrl || "", record]));
  historyGrid.querySelectorAll("[data-download-record]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      const record = recordMap.get(button.dataset.downloadRecord || "");
      const imageUrl = record?.resultImageDataUrl || record?.imageUrl || "";
      if (!imageUrl || button.disabled) {
        return;
      }
      button.disabled = true;
      try {
        const response = await chrome.runtime.sendMessage({
          type: "download-image",
          payload: {
            url: imageUrl,
            filename: `AIC-${formatDownloadTimestamp(record.createdAt)}.png`
          }
        });
        if (!response?.ok) {
          throw new Error(response?.error || "下载失败");
        }
      } finally {
        button.disabled = false;
      }
    });
  });
  historyGrid.querySelectorAll("[data-retry-record]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      if (button.disabled) {
        return;
      }
      button.disabled = true;
      button.textContent = "重试中";
      try {
        const response = await chrome.runtime.sendMessage({
          type: "retry-generation-record",
          payload: { id: button.dataset.retryRecord || "" }
        });
        if (!response?.ok) {
          throw new Error(response?.error || "重试失败");
        }
      } catch (error) {
        button.textContent = "请回原页面重试";
      }
    });
  });
  historyGrid.querySelectorAll(".history-card").forEach((card) => {
    card.addEventListener("click", () => {
      const record = recordMap.get(card.dataset.recordId || "");
      if ((record?.status || "done") === "done") {
        openHistoryLightbox(record);
      }
    });
  });
}

function getRecordTimestamp(record) {
  const value = record?.createdAt;
  const timestamp = typeof value === "number" ? value : Date.parse(value || "");
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function formatDownloadTimestamp(value) {
  const timestamp = typeof value === "number" ? value : Date.parse(value || "");
  const date = new Date(Number.isFinite(timestamp) ? timestamp : Date.now());
  const pad = (number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}-${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
}

function renderLightboxThumb(label, imageUrl, alt) {
  if (!imageUrl) {
    return `
      <div class="lightbox-thumb is-empty">
        <span>${escapeHtml(label)}</span>
        <small>未保存</small>
      </div>
    `;
  }
  return `
    <button class="lightbox-thumb" type="button" data-preview-url="${escapeHtml(imageUrl)}" aria-label="查看${escapeHtml(label)}">
      <img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(alt)}" />
      <span>${escapeHtml(label)}</span>
    </button>
  `;
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

function openHistoryLightbox(record) {
  const resultImageUrl = record?.resultImageDataUrl || record?.imageUrl || "";
  if (!resultImageUrl) {
    return;
  }
  lightboxImage.src = resultImageUrl;
  lightboxDetail.innerHTML = `
    <div class="lightbox-detail-title">${formatRecordTime(record.createdAt)}</div>
    <div class="lightbox-thumbs">
      ${renderLightboxThumb("参考图", record.referenceImageUrl || "", "参考图")}
      ${renderLightboxThumb("商品图", record.productImageDataUrl || "", "商品图")}
      ${renderLightboxThumb("结果图", resultImageUrl, "生成结果")}
    </div>
  `;
  lightboxDetail.querySelectorAll("[data-preview-url]").forEach((button) => {
    button.addEventListener("click", () => {
      lightboxImage.src = button.dataset.previewUrl || "";
    });
  });
  lightbox.hidden = false;
}

function closeLightbox() {
  lightbox.hidden = true;
  lightboxImage.removeAttribute("src");
  lightboxDetail.innerHTML = "";
}
