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
                  <option value="2.35:1">2.35:1</option>
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
            </div>
            <div class="xhs-replicator-result" hidden>
              <div class="xhs-replicator-result-card">
                <div class="xhs-replicator-result-header">
                  <div class="xhs-replicator-result-title">生成结果</div>
                  <button class="xhs-replicator-button" data-variant="secondary" data-role="download">下载图片</button>
                </div>
                <details class="xhs-replicator-debug">
                  <summary>查看最终生图 Prompt</summary>
                  <pre class="xhs-replicator-debug-text"></pre>
                </details>
                <details class="xhs-replicator-debug">
                  <summary>查看发给生图模型的输入</summary>
                  <pre class="xhs-replicator-debug-request"></pre>
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
    const resultWrap = mask.querySelector(".xhs-replicator-result");
    const debugText = mask.querySelector(".xhs-replicator-debug-text");
    const debugRequestText = mask.querySelector(".xhs-replicator-debug-request");
    const resultImage = mask.querySelector(".xhs-replicator-result img");
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
        const classificationJobId = ++state.classificationJobId;
        state.productImageDataUrl = await readFileAsDataUrl(file);
        state.productFileName = file.name;
        state.generationPath = "";
        state.generationPathSource = "";
        productThumb.src = state.productImageDataUrl;
        uploadCard.hidden = true;
        productChip.hidden = false;
        status.textContent = "正在识别商品类型...";
        await autoClassifyProduct(pathButtons, status, classificationJobId);
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
      if (state.classificationPending && !state.generationPath) {
        status.textContent = "正在识别商品类型，请稍等一下。";
        return;
      }
      if (!state.generationPath) {
        status.textContent = "还没有识别出商品路径，请重新上传商品图或手动选择。";
        return;
      }

      generateButton.disabled = true;
      generateButton.textContent = "生成中...";
      status.textContent = "正在处理中，请稍等。";
      startProgress(progressWrap, progressLabel, progressFill, state.generationPath);
      try {
        const response = await chrome.runtime.sendMessage({
          type: "replicate-image",
          payload: {
            imageUrl: state.currentImageUrl,
            productImageDataUrl: state.productImageDataUrl,
            productFileName: state.productFileName,
            productSubjectHint: subjectInput.value.trim(),
            generationPath: state.generationPath,
            userPrompt: notesInput.value.trim(),
            imageSizeOverride: resolveImageSizeOverride(ratioInput.value)
          }
        });
        if (!response?.ok) {
          throw new Error(response?.error || "请求失败");
        }
        state.generatedImageUrl = response.result.imageUrl;
        state.analysisPrompt = response.result.analysisPrompt || "";
        state.imageRequestDebug = response.result.imageRequestDebug || null;
        debugText.textContent = response.result.prompt || "";
        debugRequestText.textContent = formatImageRequestDebug(state.imageRequestDebug);
        resultImage.src = state.generatedImageUrl;
        resultWrap.hidden = false;
        finishProgress(progressLabel, progressFill);
        progressWrap.hidden = true;
        status.textContent = "";
        requestAnimationFrame(() => {
          scrollResultIntoView(formSection, resultWrap);
        });
      } catch (error) {
        stopProgress(progressWrap, progressLabel, progressFill);
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
      formSection,
      resultWrap,
      debugText,
      debugRequestText,
      resultImage
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
    modal.debugRequestText.textContent = "";
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

  async function autoClassifyProduct(pathButtons, status, classificationJobId) {
    state.classificationPending = true;
    try {
      const response = await chrome.runtime.sendMessage({
        type: "classify-product",
        payload: {
          productImageDataUrl: state.productImageDataUrl
        }
      });
      if (!response?.ok) {
        throw new Error(response?.error || "识别失败");
      }
      if (classificationJobId !== state.classificationJobId) {
        return;
      }
      const nextPath = response.result?.productKind === "apparel" ? "apparel" : "non_apparel";
      if (state.generationPathSource !== "manual") {
        setGenerationPath(pathButtons, nextPath, "auto");
        status.textContent =
          nextPath === "apparel" ? "已自动识别为服饰。可手动切换。" : "已自动识别为非服饰。可手动切换。";
      } else {
        status.textContent =
          nextPath === "apparel"
            ? "自动识别为服饰，你当前使用的是手动选择。"
            : "自动识别为非服饰，你当前使用的是手动选择。";
      }
    } catch (error) {
      if (classificationJobId !== state.classificationJobId) {
        return;
      }
      const message = error instanceof Error ? error.message : String(error);
      if (message.includes("Extension context invalidated")) {
        status.textContent = "扩展刚刚更新，刷新当前页面后再试。";
        return;
      }
      if (!state.generationPath) {
        status.textContent = `自动识别失败，请手动选择路径：${message}`;
      } else {
        status.textContent = `自动识别失败，但已保留你当前的手动路径：${message}`;
      }
    } finally {
      if (classificationJobId === state.classificationJobId) {
        state.classificationPending = false;
      }
    }
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

  function resolveImageSizeOverride(value) {
    if (value === "follow") {
      const ratio = getReferenceRatio();
      return ratio ? buildSizeFromRatio(ratio) : "";
    }
    const ratio = parseRatio(value);
    return ratio ? buildSizeFromRatio(ratio.width / ratio.height) : "";
  }

  function getReferenceRatio() {
    const image = state.currentImage;
    if (!(image instanceof HTMLImageElement)) {
      return 0;
    }
    const width = image.naturalWidth || image.width;
    const height = image.naturalHeight || image.height;
    if (!width || !height) {
      return 0;
    }
    return width / height;
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

  function buildSizeFromRatio(ratio) {
    if (!ratio || !Number.isFinite(ratio) || ratio <= 0) {
      return "";
    }

    let width;
    let height;
    if (ratio >= 1) {
      width = 3072;
      height = roundEven(width / ratio);
      if (height < 1024) {
        height = 1024;
        width = roundEven(height * ratio);
      }
    } else {
      height = 3072;
      width = roundEven(height * ratio);
      if (width < 1024) {
        width = 1024;
        height = roundEven(width / ratio);
      }
    }

    width = Math.min(4096, width);
    height = Math.min(4096, height);
    return `${width}x${height}`;
  }

  function roundEven(value) {
    const rounded = Math.max(2, Math.round(value));
    return rounded % 2 === 0 ? rounded : rounded + 1;
  }

  function startProgress(progressWrap, progressLabel, progressFill, generationPath) {
    stopProgress(progressWrap, progressLabel, progressFill);
    progressWrap.hidden = false;
    const steps =
      generationPath === "apparel"
        ? [
            { label: "1/5 正在识别商品是服饰，并检查参考图里是否有人脸", progress: 14 },
            { label: "2/5 正在学习参考图并生成人像垫图 Prompt", progress: 30 },
            { label: "3/5 正在生成模特人像垫图", progress: 48 },
            { label: "4/5 正在融合参考图、人像图和商品图约束", progress: 72 },
            { label: "5/5 正在生成最终服饰画面", progress: 88 }
          ]
        : [
            { label: "1/4 正在分析参考图里的场景、时间和主体关系", progress: 18 },
            { label: "2/4 正在识别商品图里的主体与高辨识度细节", progress: 38 },
            { label: "3/4 正在融合商品与场景约束", progress: 62 },
            { label: "4/4 正在生成最终画面", progress: 84 }
          ];
    let index = 0;
    progressLabel.textContent = steps[0].label;
    progressFill.style.width = `${steps[0].progress}%`;
    state.stageTimer = window.setInterval(() => {
      index = Math.min(index + 1, steps.length - 1);
      progressLabel.textContent = steps[index].label;
      progressFill.style.width = `${steps[index].progress}%`;
    }, 2200);
  }

  function finishProgress(progressLabel, progressFill) {
    clearProgressTimers();
    progressLabel.textContent = "4/4 生成完成";
    progressFill.style.width = "100%";
  }

  function stopProgress(progressWrap, progressLabel, progressFill) {
    clearProgressTimers();
    progressWrap.hidden = true;
    progressLabel.textContent = "准备开始...";
    progressFill.style.width = "0%";
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
