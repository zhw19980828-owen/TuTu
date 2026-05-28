(function initCommerceReplicator() {
  if (window.__xhsReplicatorMounted) {
    return;
  }
  window.__xhsReplicatorMounted = true;

  const state = {
    currentImage: null,
    currentImageUrl: "",
    generatedImageUrl: "",
    analysisPrompt: "",
    imageRequestDebug: null,
    productImageDataUrl: "",
    productFileName: "",
    generationPath: "",
    generationPathSource: "",
    classificationPending: false,
    classificationJobId: 0,
    stageTimer: null,
    progressTimer: null,
    progressSteps: [],
    currentStageIndex: 0,
    hideTimer: null,
    pointerOnTrigger: false
  };

  const trigger = createTrigger();
  const modal = createModal();

  document.addEventListener("mousemove", handleMouseMove, true);
  document.addEventListener("scroll", () => hideTrigger(), true);
  window.addEventListener("resize", () => hideTrigger());

  function handleMouseMove(event) {
    if (modal.mask.dataset.open === "true") {
      return;
    }

    if (event.target === trigger || trigger.contains(event.target)) {
      return;
    }

    const target = event.target instanceof Element ? event.target.closest("img") : null;
    if (!target || !isCandidateImage(target)) {
      scheduleHideTrigger();
      return;
    }

    const imageUrl = pickImageUrl(target);
    if (!imageUrl) {
      scheduleHideTrigger();
      return;
    }

    clearHideTrigger();
    state.currentImage = target;
    state.currentImageUrl = imageUrl;
    placeTrigger(target);
  }

  function createTrigger() {
    const button = document.createElement("button");
    button.className = "xhs-replicator-trigger";
    button.type = "button";
    button.textContent = "替换成我的商品";
    button.addEventListener("mouseenter", () => {
      state.pointerOnTrigger = true;
      clearHideTrigger();
    });
    button.addEventListener("mouseleave", () => {
      state.pointerOnTrigger = false;
      scheduleHideTrigger();
    });
    button.addEventListener("pointerdown", suppressNativeClick, true);
    button.addEventListener("mousedown", suppressNativeClick, true);
    button.addEventListener(
      "click",
      (event) => {
        suppressNativeClick(event);
        openModal();
      },
      true
    );
    document.documentElement.appendChild(button);
    return button;
  }

  function createModal() {
    const mask = document.createElement("div");
    mask.className = "xhs-replicator-mask";
    mask.innerHTML = `
      <div class="xhs-replicator-modal">
        <div class="xhs-replicator-panel">
          <section class="xhs-replicator-preview">
            <div class="xhs-replicator-preview-inner">
              <div class="xhs-replicator-preview-card">
                <img alt="参考图预览" />
              </div>
            </div>
          </section>
          <section class="xhs-replicator-form">
            <div class="xhs-replicator-form-card">
              <div class="xhs-replicator-row">
                <input id="xhs-replicator-product" class="xhs-replicator-product-input" type="file" accept="image/*" />
                <div class="xhs-replicator-upload-card" data-role="upload-card" tabindex="0">
                  <div class="xhs-replicator-upload-plus">+</div>
                  <div class="xhs-replicator-upload-copy">
                    <div class="xhs-replicator-upload-title">上传商品图</div>
                    <div class="xhs-replicator-upload-subtitle">点击添加你的商品主体</div>
                  </div>
                </div>
                <div class="xhs-replicator-product-chip" data-role="product-chip" hidden>
                  <img class="xhs-replicator-product-thumb" data-role="product-thumb" alt="商品缩略图" />
                  <div class="xhs-replicator-product-actions">
                    <button class="xhs-replicator-inline-action" type="button" data-role="replace-product">替换</button>
                    <button class="xhs-replicator-inline-action" type="button" data-role="remove-product">删除</button>
                  </div>
                </div>
              </div>
              <div class="xhs-replicator-row">
                <label>生成路径</label>
                <div class="xhs-replicator-path-switch" data-role="path-switch">
                  <button class="xhs-replicator-path-chip" type="button" data-path="apparel">服饰</button>
                  <button class="xhs-replicator-path-chip" type="button" data-path="non_apparel">非服饰</button>
                </div>
              </div>
              <div class="xhs-replicator-row">
                <label for="xhs-replicator-subject">商品主体说明（可选）</label>
                <input id="xhs-replicator-subject" type="text" placeholder="例如：女装连衣裙、银色戒指、玻璃香水瓶。白底商品图不写也可以。" />
              </div>
              <div class="xhs-replicator-row">
                <label for="xhs-replicator-notes">补充要求</label>
                <input id="xhs-replicator-notes" type="text" placeholder="可选：比如更适合首页头图、突出面料、突出光泽、保留模特上身效果、改成静物陈列等" />
              </div>
              <div class="xhs-replicator-row">
                <label for="xhs-replicator-ratio">画面比例</label>
                <select id="xhs-replicator-ratio">
                  <option value="follow">跟随原图比例</option>
                  <option value="4:3">4:3</option>
                  <option value="3:4">3:4</option>
                  <option value="16:9">16:9</option>
                  <option value="9:16">9:16</option>
                  <option value="1:1">1:1</option>
                  <option value="21:9">21:9</option>
                </select>
              </div>
              <div class="xhs-replicator-actions">
                <button class="xhs-replicator-button" data-variant="primary" data-role="generate">生成</button>
                <button class="xhs-replicator-button" data-variant="secondary" data-role="settings">我的</button>
              </div>
            </div>
            <div class="xhs-replicator-status"></div>
            <div class="xhs-replicator-progress" hidden>
              <div class="xhs-replicator-progress-label">准备开始...</div>
              <div class="xhs-replicator-progress-track">
                <div class="xhs-replicator-progress-fill"></div>
              </div>
              <div class="xhs-replicator-progress-steps"></div>
            </div>
            <div class="xhs-replicator-result" hidden>
              <div class="xhs-replicator-result-card">
                <div class="xhs-replicator-result-header">
                  <div class="xhs-replicator-result-title">生成结果</div>
                  <button class="xhs-replicator-button" data-variant="secondary" data-role="download">下载图片</button>
                </div>
                <div class="xhs-replicator-timing" data-role="timing" hidden></div>
                <details class="xhs-replicator-debug">
                  <summary>查看最终生图 Prompt</summary>
                  <pre class="xhs-replicator-debug-text"></pre>
                </details>
                <img alt="复刻结果" />
              </div>
            </div>
          </section>
        </div>
      </div>
    `;

    const previewImage = mask.querySelector(".xhs-replicator-preview img");
    const productInput = mask.querySelector("#xhs-replicator-product");
    const uploadCard = mask.querySelector('[data-role="upload-card"]');
    const productChip = mask.querySelector('[data-role="product-chip"]');
    const productThumb = mask.querySelector('[data-role="product-thumb"]');
    const pathButtons = Array.from(mask.querySelectorAll(".xhs-replicator-path-chip"));
    const subjectInput = mask.querySelector("#xhs-replicator-subject");
    const notesInput = mask.querySelector("#xhs-replicator-notes");
    const ratioInput = mask.querySelector("#xhs-replicator-ratio");
    const status = mask.querySelector(".xhs-replicator-status");
    const progressWrap = mask.querySelector(".xhs-replicator-progress");
    const progressLabel = mask.querySelector(".xhs-replicator-progress-label");
    const progressFill = mask.querySelector(".xhs-replicator-progress-fill");
    const progressSteps = mask.querySelector(".xhs-replicator-progress-steps");
    const resultWrap = mask.querySelector(".xhs-replicator-result");
    const debugText = mask.querySelector(".xhs-replicator-debug-text");
    const resultImage = mask.querySelector(".xhs-replicator-result img");
    const timing = mask.querySelector('[data-role="timing"]');
    const generateButton = mask.querySelector('[data-role="generate"]');
    const formSection = mask.querySelector(".xhs-replicator-form");
    const replaceProductButton = mask.querySelector('[data-role="replace-product"]');
    const removeProductButton = mask.querySelector('[data-role="remove-product"]');

    mask.addEventListener("click", (event) => {
      if (event.target === mask) {
        closeModal();
      }
    });

    mask
      .querySelector('[data-role="settings"]')
      .addEventListener("click", async () => {
        const response = await chrome.runtime.sendMessage({ type: "open-options-page" });
        if (!response?.ok) {
          status.textContent = `打开设置失败：${response?.error || "未知错误"}`;
        }
      });
    mask.querySelector('[data-role="download"]').addEventListener("click", async () => {
      if (!state.generatedImageUrl) {
        return;
      }
      const filename = `commerce-replica-${Date.now()}.png`;
      const response = await chrome.runtime.sendMessage({
        type: "download-image",
        payload: {
          url: state.generatedImageUrl,
          filename
        }
      });
      status.textContent = response?.ok
        ? "已打开下载面板。"
        : `下载失败：${response?.error || "未知错误"}`;
      });

    uploadCard.addEventListener("click", () => {
      productInput.click();
    });
    uploadCard.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        productInput.click();
      }
    });
    replaceProductButton.addEventListener("click", () => {
      productInput.click();
    });
    removeProductButton.addEventListener("click", () => {
      clearProductSelection({
        productInput,
        productThumb,
        uploadCard,
        productChip
      });
      setGenerationPath(pathButtons, "");
    });

    productInput.addEventListener("change", async () => {
      const file = productInput.files?.[0];
      if (!file) {
        clearProductSelection({
          productInput,
          productThumb,
          uploadCard,
          productChip
        });
        setGenerationPath(pathButtons, "");
        return;
      }

      try {
        state.classificationJobId += 1;
        state.productImageDataUrl = await readFileAsDataUrl(file);
        state.productFileName = file.name;
        productThumb.src = state.productImageDataUrl;
        uploadCard.hidden = true;
        productChip.hidden = false;
        setGenerationPath(pathButtons, state.generationPath || "apparel", "default");
        status.textContent = "已上传商品图。默认走服饰路径，需要非服饰时可手动切换。";
      } catch (error) {
        clearProductSelection({
          productInput,
          productThumb,
          uploadCard,
          productChip
        });
        status.textContent = `商品图片读取失败：${error instanceof Error ? error.message : String(error)}`;
      }
    });

    pathButtons.forEach((button) => {
      button.addEventListener("click", () => {
        setGenerationPath(pathButtons, button.dataset.path || "", "manual");
        status.textContent =
          state.generationPath === "apparel"
            ? "已切换为服饰路径。"
            : state.generationPath === "non_apparel"
              ? "已切换为非服饰路径。"
              : "";
      });
    });

    generateButton.addEventListener("click", async () => {
      if (!state.currentImageUrl) {
        status.textContent = "没有拿到参考图地址，请重新 hover 一次图片。";
        return;
      }
      if (!state.productImageDataUrl) {
        status.textContent = "请先上传你自己的商品图片。";
        return;
      }
      if (!state.generationPath) {
        status.textContent = "请选择服饰或非服饰路径。";
        return;
      }

      generateButton.disabled = true;
      generateButton.textContent = "生成中...";
      status.textContent = "正在处理中，请稍等。";
      const progressId = createProgressId();
      startProgress(progressWrap, progressLabel, progressFill, state.generationPath, progressId);
      try {
        const productThumbDataUrl = await createHistoryThumbnail(state.productImageDataUrl);
        const response = await replicateImageDirectly({
          imageUrl: state.currentImageUrl,
          productImageDataUrl: state.productImageDataUrl,
          productFileName: state.productFileName,
          productSubjectHint: subjectInput.value.trim(),
          generationPath: state.generationPath,
          userPrompt: notesInput.value.trim(),
          imageSizeOverride: resolveImageSizeOverride(ratioInput.value),
          progressId
        });
        if (!response?.ok) {
          throw new Error(response?.error || "请求失败");
        }
        state.generatedImageUrl = response.result.imageUrl;
        state.analysisPrompt = response.result.analysisPrompt || "";
        debugText.textContent = response.result.prompt || "";
        renderTiming(timing, response.result.timings || []);
        resultImage.src = state.generatedImageUrl;
        resultWrap.hidden = false;
        const resultThumbDataUrl = await createHistoryThumbnail(state.generatedImageUrl, {
          maxSide: 720,
          quality: 0.78
        });
        await saveGenerationRecord({
          imageUrl: state.generatedImageUrl,
          resultImageDataUrl: resultThumbDataUrl,
          prompt: response.result.prompt || "",
          referenceImageUrl: state.currentImageUrl,
          productImageDataUrl: productThumbDataUrl,
          productFileName: state.productFileName,
          productSubjectHint: subjectInput.value.trim(),
          generationPath: response.result.generationPath || state.generationPath,
          userPrompt: notesInput.value.trim(),
          imageSize: resolveImageSizeOverride(ratioInput.value)
        });
        finishProgress(progressWrap, progressLabel, progressFill);
        status.textContent = "";
        requestAnimationFrame(() => {
          scrollResultIntoView(formSection, resultWrap);
        });
      } catch (error) {
        failProgress(progressWrap, progressLabel, progressFill);
        status.textContent = `生成失败：${error instanceof Error ? error.message : String(error)}`;
      } finally {
        generateButton.disabled = false;
        generateButton.textContent = "生成";
      }
    });

    document.documentElement.appendChild(mask);
    return {
      mask,
      previewImage,
      productInput,
      uploadCard,
      productChip,
      productThumb,
      pathButtons,
      subjectInput,
      notesInput,
      ratioInput,
      status,
      progressWrap,
      progressLabel,
      progressFill,
      progressSteps,
      formSection,
      resultWrap,
      debugText,
      resultImage,
      timing
    };
  }

  function openModal() {
    if (!state.currentImageUrl) {
      return;
    }
    modal.previewImage.src = state.currentImageUrl;
    modal.subjectInput.value = "";
    modal.notesInput.value = "";
    modal.ratioInput.value = "follow";
    modal.status.textContent = "";
    stopProgress(modal.progressWrap, modal.progressLabel, modal.progressFill);
    clearProductSelection({
      productInput: modal.productInput,
      productThumb: modal.productThumb,
      uploadCard: modal.uploadCard,
      productChip: modal.productChip
    });
    setGenerationPath(modal.pathButtons, "");
    modal.resultWrap.hidden = true;
    modal.debugText.textContent = "";
    renderTiming(modal.timing, []);
    modal.resultImage.removeAttribute("src");
    modal.mask.dataset.open = "true";
    modal.mask.style.display = "flex";
    modal.formSection.scrollTop = 0;
  }

  function closeModal() {
    modal.mask.dataset.open = "false";
    modal.mask.style.display = "";
  }

  function placeTrigger(image) {
    const rect = image.getBoundingClientRect();
    trigger.style.display = "inline-flex";
    trigger.style.left = `${Math.max(12, rect.right - 176)}px`;
    trigger.style.top = `${Math.max(12, rect.top + 12)}px`;
  }

  function hideTrigger() {
    clearHideTrigger();
    trigger.style.display = "none";
  }

  function scrollResultIntoView(container, resultWrap) {
    if (!container || !resultWrap) {
      return;
    }
    const targetTop = Math.max(0, resultWrap.offsetTop - 12);
    container.scrollTo({
      top: targetTop,
      behavior: "smooth"
    });
  }

  function clearProductSelection({ productInput, productThumb, uploadCard, productChip }) {
    state.classificationJobId += 1;
    state.productImageDataUrl = "";
    state.productFileName = "";
    state.generationPath = "";
    state.generationPathSource = "";
    state.classificationPending = false;
    if (productInput) {
      productInput.value = "";
    }
    if (productThumb) {
      productThumb.removeAttribute("src");
    }
    if (uploadCard) {
      uploadCard.hidden = false;
    }
    if (productChip) {
      productChip.hidden = true;
    }
  }

  function setGenerationPath(pathButtons, nextPath, source = "") {
    state.generationPath = nextPath;
    state.generationPathSource = nextPath ? source : "";
    pathButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.path === nextPath);
    });
  }

  function createProgressId() {
    if (window.crypto?.randomUUID) {
      return window.crypto.randomUUID();
    }
    return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function scheduleHideTrigger() {
    clearHideTrigger();
    state.hideTimer = window.setTimeout(() => {
      if (!state.pointerOnTrigger && modal.mask.dataset.open !== "true") {
        trigger.style.display = "none";
      }
    }, 120);
  }

  function clearHideTrigger() {
    if (state.hideTimer) {
      window.clearTimeout(state.hideTimer);
      state.hideTimer = null;
    }
  }

  function suppressNativeClick(event) {
    event.preventDefault();
    event.stopPropagation();
    if (typeof event.stopImmediatePropagation === "function") {
      event.stopImmediatePropagation();
    }
  }

  function isCandidateImage(image) {
    if (!(image instanceof HTMLImageElement)) {
      return false;
    }

    const width = image.naturalWidth || image.width;
    const height = image.naturalHeight || image.height;
    if (width < 120 || height < 120) {
      return false;
    }

    const src = pickImageUrl(image);
    if (!src) {
      return false;
    }

    return isSupportedHost(src) || isSupportedHost(location.hostname);
  }

  function isSupportedHost(value) {
    return (
      value.includes("xhscdn.com") ||
      value.includes("xiaohongshu.com") ||
      value.includes("pinimg.com") ||
      value.includes("pinterest.com") ||
      value.includes("alicdn.com") ||
      value.includes("taobao.com")
    );
  }

  function pickImageUrl(image) {
    return (
      image.currentSrc ||
      image.src ||
      image.getAttribute("src") ||
      image.getAttribute("data-src") ||
      ""
    ).trim();
  }

  function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("商品图片读取失败"));
      reader.onloadend = () => resolve(reader.result || "");
      reader.readAsDataURL(file);
    });
  }

  async function replicateImageDirectly(payload) {
    const settings = await getLocalTestSettings();
    const requestBody = {
      imageUrl: payload.imageUrl,
      productImageDataUrl: payload.productImageDataUrl,
      productFileName: payload.productFileName || "",
      productSubjectHint: payload.productSubjectHint || "",
      generationPath: payload.generationPath || "",
      progressId: payload.progressId || "",
      userPrompt: payload.userPrompt || "",
      model: settings.model,
      visionModel: settings.visionModel,
      nonApparelPrompt: settings.nonApparelPrompt,
      apparelFinalPrompt: settings.apparelFinalPrompt,
      defaultUserPrompt: settings.defaultUserPrompt,
      imageSize: payload.imageSizeOverride || settings.imageSize,
      responseDataPath: settings.responseDataPath,
      extraBody: parseExtraBody(settings.extraBody)
    };

    const response = await fetch(`${settings.backendBaseUrl.replace(/\/+$/, "")}/replicate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(formatBackendError(response.status, text));
    }

    const data = await response.json();
    if (!data?.imageUrl) {
      throw new Error("后端返回成功，但没有提供生成图片地址。");
    }
    return {
      ok: true,
      result: {
        imageUrl: data.imageUrl,
        prompt: data.prompt || "",
        imageRequestDebug: data.imageRequestDebug || null,
        timings: Array.isArray(data.timings) ? data.timings : [],
        generationPath: data.generationPath || payload.generationPath || "",
        referenceHasFace: Boolean(data.referenceHasFace),
        analysisPrompt: data.analysisPrompt || "",
        productAnalysisPrompt: data.productAnalysisPrompt || "",
        referenceAnalysisPrompt: data.referenceAnalysisPrompt || ""
      }
    };
  }

  async function saveGenerationRecord(record) {
    try {
      await chrome.runtime.sendMessage({
        type: "save-generation-record",
        payload: record
      });
    } catch (error) {
      console.warn("[Commerce Replicator] 保存生成记录失败", error);
    }
  }

  async function createHistoryThumbnail(imageSource, options = {}) {
    if (!imageSource) {
      return "";
    }
    try {
      const image = await loadImage(imageSource);
      const maxSide = options.maxSide || 360;
      const quality = options.quality || 0.72;
      const scale = Math.min(1, maxSide / Math.max(image.naturalWidth || image.width, image.naturalHeight || image.height));
      const width = Math.max(1, Math.round((image.naturalWidth || image.width) * scale));
      const height = Math.max(1, Math.round((image.naturalHeight || image.height) * scale));
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      context.drawImage(image, 0, 0, width, height);
      return canvas.toDataURL("image/jpeg", quality);
    } catch (error) {
      return "";
    }
  }

  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.crossOrigin = "anonymous";
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error("缩略图生成失败"));
      image.src = src;
    });
  }

  function isDataUrl(value) {
    return typeof value === "string" && value.startsWith("data:");
  }

  async function getLocalTestSettings() {
    const response = await chrome.runtime.sendMessage({ type: "get-default-settings" });
    const defaults = response?.ok ? response.result || {} : {};
    return {
      ...defaults,
      backendBaseUrl: "http://127.0.0.1:8787",
      proxyToken: "",
      model: "openai/gpt-5.4-image-2",
      visionModel: "moonshotai/kimi-k2.6",
      nonApparelPrompt: defaults.nonApparelPrompt || "",
      defaultUserPrompt: ""
    };
  }

  function parseExtraBody(raw) {
    if (!raw || !String(raw).trim()) {
      return {};
    }
    try {
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (error) {
      throw new Error("extraBody 不是合法 JSON，请到设置页修正后重试。");
    }
  }

  function formatBackendError(status, text) {
    if (!text) {
      return `复刻失败 (${status})：未知错误`;
    }
    try {
      const parsed = JSON.parse(text);
      const message = parsed?.error || text;
      const debugText = parsed?.imageRequestDebug
        ? `\n\n发给生图模型的输入：\n${JSON.stringify(parsed.imageRequestDebug, null, 2)}`
        : "";
      const visionDebugText = parsed?.visionDebug
        ? `\n\n识图模型返回摘要：\n${JSON.stringify(parsed.visionDebug, null, 2)}`
        : "";
      return `复刻失败 (${status})：${String(message).slice(0, 400)}${debugText}${visionDebugText}`;
    } catch (error) {
      return `复刻失败 (${status})：${text.slice(0, 400)}`;
    }
  }

  function renderTiming(container, timings) {
    if (!container) {
      return;
    }
    const kimiTimings = Array.isArray(timings)
      ? timings.filter((item) => item?.label?.startsWith?.("kimi_"))
      : [];
    if (!kimiTimings.length) {
      container.hidden = true;
      container.textContent = "";
      return;
    }

    const totalMs = kimiTimings.reduce((sum, item) => sum + Number(item.elapsedMs || 0), 0);
    const details = kimiTimings
      .map((item) => `${formatTimingLabel(item.label)} ${formatDuration(item.elapsedMs)}`)
      .join(" / ");
    container.hidden = false;
    container.innerHTML = `
      <span>Kimi 耗时 ${formatDuration(totalMs)}</span>
      <small>${escapeHtml(details)}</small>
    `;
  }

  function formatTimingLabel(label) {
    const labels = {
      kimi_product_classification: "分类",
      kimi_apparel_reference_analysis: "参考图分析",
      kimi_reference_face: "人脸判断",
      kimi_non_apparel_prompt: "非服饰 Prompt",
      kimi_apparel_reference_description: "参考图描述",
      kimi_apparel_final_prompt: "服饰 Prompt"
    };
    return labels[label] || label || "Kimi";
  }

  function formatDuration(value) {
    const ms = Number(value || 0);
    if (!Number.isFinite(ms) || ms <= 0) {
      return "0.0s";
    }
    return `${(ms / 1000).toFixed(1)}s`;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function resolveImageSizeOverride(value) {
    if (value === "follow") {
      return getReferenceAspectRatio();
    }
    return parseRatio(value) ? value : "";
  }

  function getReferenceAspectRatio() {
    const image = state.currentImage;
    if (!(image instanceof HTMLImageElement)) {
      return "";
    }
    const rect = image.getBoundingClientRect();
    const width = image.naturalWidth || image.width || Math.round(rect.width);
    const height = image.naturalHeight || image.height || Math.round(rect.height);
    if (!width || !height) {
      return "";
    }
    return closestSupportedAspectRatio(width / height);
  }

  function parseRatio(value) {
    if (!value) {
      return null;
    }
    const normalized = value.trim().toLowerCase();
    const separator = normalized.includes(":") ? ":" : normalized.includes("/") ? "/" : null;
    if (!separator) {
      return null;
    }
    const [rawWidth, rawHeight] = normalized.split(separator);
    const width = Number(rawWidth);
    const height = Number(rawHeight);
    if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
      return null;
    }
    return { width, height };
  }

  function closestSupportedAspectRatio(ratio) {
    if (!Number.isFinite(ratio) || ratio <= 0) {
      return "";
    }
    const supported = [
      { value: "1:1", ratio: 1 },
      { value: "2:3", ratio: 2 / 3 },
      { value: "3:2", ratio: 3 / 2 },
      { value: "3:4", ratio: 3 / 4 },
      { value: "4:3", ratio: 4 / 3 },
      { value: "4:5", ratio: 4 / 5 },
      { value: "5:4", ratio: 5 / 4 },
      { value: "9:16", ratio: 9 / 16 },
      { value: "16:9", ratio: 16 / 9 },
      { value: "21:9", ratio: 21 / 9 }
    ];
    return supported.reduce((best, item) => {
      const currentDistance = Math.abs(Math.log(item.ratio / ratio));
      const bestDistance = Math.abs(Math.log(best.ratio / ratio));
      return currentDistance < bestDistance ? item : best;
    }).value;
  }

  function startProgress(progressWrap, progressLabel, progressFill, generationPath, progressId) {
    stopProgress(progressWrap, progressLabel, progressFill);
    progressWrap.hidden = false;
    const steps = getProgressSteps(generationPath);
    state.progressSteps = steps;
    state.currentStageIndex = 0;
    renderProgressSteps(0);
    progressLabel.textContent = `${1}/${steps.length} ${steps[0].title}`;
    progressFill.style.width = `${steps[0].progress}%`;
    state.progressTimer = window.setInterval(() => {
      pollBackendProgress(progressId, progressLabel, progressFill);
    }, 900);
    pollBackendProgress(progressId, progressLabel, progressFill);
  }

  async function pollBackendProgress(progressId, progressLabel, progressFill) {
    if (!progressId) {
      return;
    }
    try {
      const response = await fetch(`http://127.0.0.1:8787/progress/${encodeURIComponent(progressId)}`);
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      updateProgressFromBackend(data, progressLabel, progressFill);
    } catch (error) {
      // 进度轮询失败不打断主生成请求，最终错误由主请求展示。
    }
  }

  function updateProgressFromBackend(data, progressLabel, progressFill) {
    if (!data || !Array.isArray(data.steps) || !data.steps.length) {
      return;
    }
    state.progressSteps = data.steps;
    const index = Math.max(0, Math.min(Number(data.activeIndex || 0), data.steps.length - 1));
    state.currentStageIndex = index;
    const terminalState = data.status === "done" ? "done" : data.status === "error" ? "error" : "";
    renderProgressSteps(index, terminalState);
    progressLabel.textContent =
      data.status === "done"
        ? `${data.steps.length}/${data.steps.length} 生成完成`
        : `${index + 1}/${data.steps.length} ${data.message || data.steps[index].title}`;
    progressFill.style.width =
      data.status === "done" ? "100%" : `${data.steps[index].progress || 0}%`;
  }

  function finishProgress(progressWrap, progressLabel, progressFill) {
    clearProgressTimers();
    const steps = state.progressSteps.length ? state.progressSteps : getProgressSteps(state.generationPath);
    state.currentStageIndex = steps.length - 1;
    renderProgressSteps(steps.length - 1, "done");
    progressLabel.textContent = `${steps.length}/${steps.length} 生成完成`;
    progressFill.style.width = "100%";
    progressWrap.hidden = true;
  }

  function stopProgress(progressWrap, progressLabel, progressFill) {
    clearProgressTimers();
    progressWrap.hidden = true;
    progressLabel.textContent = "准备开始...";
    progressFill.style.width = "0%";
    state.progressSteps = [];
    state.currentStageIndex = 0;
    renderProgressSteps(0);
  }

  function failProgress(progressWrap, progressLabel, progressFill) {
    clearProgressTimers();
    if (!state.progressSteps.length) {
      stopProgress(progressWrap, progressLabel, progressFill);
      return;
    }
    progressWrap.hidden = false;
    renderProgressSteps(state.currentStageIndex, "error");
    progressLabel.textContent = `停在 ${state.currentStageIndex + 1}/${state.progressSteps.length} ${state.progressSteps[state.currentStageIndex].title}`;
    progressFill.style.width = `${state.progressSteps[state.currentStageIndex].progress}%`;
  }

  function clearProgressTimers() {
    if (state.stageTimer) {
      window.clearInterval(state.stageTimer);
      state.stageTimer = null;
    }
    if (state.progressTimer) {
      window.clearInterval(state.progressTimer);
      state.progressTimer = null;
    }
  }

  function getProgressSteps(generationPath) {
    return generationPath === "apparel"
      ? [
          {
            title: "分析参考图",
            detail: "Kimi 读取小红书参考图，提取人物形象、场景、姿势和构图。",
            progress: 25
          },
          {
            title: "融合服饰约束",
            detail: "Kimi 写最终服饰换装 Prompt，商品图只提供服饰外观。",
            progress: 55
          },
          {
            title: "生成最终图片",
            detail: "参考图约束人物和场景，商品图只约束服饰。",
            progress: 88
          }
        ]
      : [
          {
            title: "生成复刻 Prompt",
            detail: "Kimi 分析参考图的场景、机位、光线和商品摆放关系。",
            progress: 35
          },
          {
            title: "生成最终图片",
            detail: "Prompt 返回后，调用生图模型输出结果图。",
            progress: 84
          }
        ];
  }

  function renderProgressSteps(activeIndex, terminalState = "") {
    const container = modal?.progressSteps;
    if (!container) {
      return;
    }
    const steps = state.progressSteps || [];
    if (!steps.length) {
      container.innerHTML = "";
      return;
    }
    container.innerHTML = steps
      .map((step, index) => {
        let status = "pending";
        if (terminalState === "done") {
          status = "done";
        } else if (terminalState === "error" && index === activeIndex) {
          status = "error";
        } else if (index < activeIndex) {
          status = "done";
        } else if (index === activeIndex) {
          status = "active";
        }
        return `
          <div class="xhs-replicator-progress-step" data-state="${status}">
            <span class="xhs-replicator-progress-dot"></span>
            <div>
              <strong>${escapeHtml(step.title)}</strong>
              <small>${escapeHtml(step.detail)}</small>
            </div>
          </div>
        `;
      })
      .join("");
  }

  function formatImageRequestDebug(debug) {
    if (!debug) {
      return "当前没有可用的生图模型输入记录。";
    }
    try {
      return JSON.stringify(debug, null, 2);
    } catch (error) {
      return "生图模型输入记录格式化失败。";
    }
  }
})();
