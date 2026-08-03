(function initCommerceReplicator() {
  if (window.__xhsReplicatorMounted) {
    return;
  }
  window.__xhsReplicatorMounted = true;
  const PRODUCT_KIND_KEY = "xhsReplicatorProductKind";
  const SETTINGS_KEY = "userSettings";

  const state = {
    currentImage: null,
    currentImageUrl: "",
    generatedImageUrl: "",
    analysisPrompt: "",
    imageRequestDebug: null,
    productImageDataUrl: "",
    productFileName: "",
    generationPath: "apparel",
    generationPathSource: "memory",
    imageModel: "dreamina/image2image:5.0Pro",
    faceIdentityMode: "regenerate",
    floatingX: null,
    floatingY: null,
    classificationPending: false,
    classificationJobId: 0,
    progressTimer: null,
    progressSteps: [],
    currentStageIndex: 0,
    backgroundTasks: [],
    activeTaskId: "",
    hideTimer: null,
    pointerOnTrigger: false
  };

  const trigger = createTrigger();
  const modal = createModal();
  loadRememberedGenerationPath();

  document.addEventListener("mousemove", handleMouseMove, true);
  document.addEventListener("scroll", () => hideTrigger(), true);
  window.addEventListener("resize", () => {
    hideTrigger();
    if (modal.mask.dataset.open === "true") {
      positionFloatingWindow(modal.modalWindow);
    }
  });

  function handleMouseMove(event) {
    if (modal.mask.dataset.open === "true") {
      return;
    }

    if (event.target === trigger || trigger.contains(event.target)) {
      return;
    }

    const target = findCandidateImageFromTarget(event.target);
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
    button.innerHTML = `
      <span class="xhs-replicator-trigger-icon" aria-hidden="true">
        <svg viewBox="0 0 16 16" focusable="false">
          <path d="M8 1.7 9.4 5l3.6 1.3-3.6 1.3L8 11 6.6 7.6 3 6.3 6.6 5 8 1.7Z"></path>
          <path d="M12.4 9.5 13 11l1.5.6-1.5.6-.6 1.5-.6-1.5-1.5-.6 1.5-.6.6-1.5Z"></path>
        </svg>
      </span>
      <span>AI复刻</span>
    `;
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
        <div class="xhs-replicator-window-bar" data-role="drag-handle">
          <div class="xhs-replicator-window-nav">
            <button class="xhs-replicator-window-close" type="button" data-role="close-window" aria-label="关闭">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6.5 6.5 17.5 17.5M17.5 6.5 6.5 17.5"></path>
              </svg>
            </button>
            <button class="xhs-replicator-window-back" type="button" data-role="result-back" aria-label="返回编辑">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="m14.5 6-6 6 6 6"></path>
              </svg>
            </button>
          </div>
          <button class="xhs-replicator-window-title" type="button" data-role="open-settings" aria-label="打开 AIC 任务中心">AIC</button>
        </div>
        <div class="xhs-replicator-panel">
          <section class="xhs-replicator-preview">
            <div class="xhs-replicator-preview-inner">
              <div class="xhs-replicator-preview-card">
                <img alt="参考图预览" />
              </div>
            </div>
          </section>
          <section class="xhs-replicator-form">
            <div class="xhs-replicator-form-card" data-role="form-view">
              <div class="xhs-replicator-hero">
                <div class="xhs-replicator-row xhs-replicator-asset-row">
                  <input id="xhs-replicator-product" class="xhs-replicator-product-input" type="file" accept="image/*" />
                  <div class="xhs-replicator-upload-card" data-role="upload-card" tabindex="0">
                    <div class="xhs-replicator-upload-plus">添加商品素材</div>
                  </div>
                  <div class="xhs-replicator-product-chip" data-role="product-chip" tabindex="0" aria-label="替换商品素材" hidden>
                    <span class="xhs-replicator-product-card-layer is-left" aria-hidden="true"></span>
                    <span class="xhs-replicator-product-card-layer is-right" aria-hidden="true"></span>
                    <div class="xhs-replicator-product-card-front">
                      <img class="xhs-replicator-product-thumb" data-role="product-thumb" alt="商品缩略图" />
                    </div>
                    <div class="xhs-replicator-product-actions">
                      <button class="xhs-replicator-inline-action" type="button" data-role="replace-product">替换</button>
                      <button class="xhs-replicator-inline-action" type="button" data-role="remove-product">删除</button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="xhs-replicator-editor-surface">
                <div class="xhs-replicator-composer">
                  <textarea id="xhs-replicator-notes" aria-label="补充要求" placeholder="描述你还想调整的细节…"></textarea>
                </div>
                <div class="xhs-replicator-control-dock">
                  <div class="xhs-replicator-quick-controls">
                    <button class="xhs-replicator-kind-trigger" type="button" data-role="kind-trigger" aria-expanded="false">
                      <span data-role="kind-label">服装</span>
                    </button>
                    <div class="xhs-replicator-kind-popover" data-role="kind-popover" hidden>
                      <button class="xhs-replicator-path-chip" type="button" data-path="apparel">服装</button>
                      <button class="xhs-replicator-path-chip" type="button" data-path="non_apparel">其他</button>
                    </div>
                  </div>
                  <div class="xhs-replicator-actions">
                    <button class="xhs-replicator-options-button" type="button" data-role="open-options" aria-label="打开设置" aria-expanded="false">
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M4 7h6m4 0h6M12 4v6M4 17h10m4 0h2M16 14v6"></path>
                      </svg>
                    </button>
                    <button class="xhs-replicator-button" data-variant="primary" data-role="generate" aria-label="生成复刻">生成</button>
                  </div>
                  <div class="xhs-replicator-options-popover" data-role="options-popover" hidden>
                    <div class="xhs-replicator-option-group">
                      <span class="xhs-replicator-option-label">比例</span>
                      <div class="xhs-replicator-option-grid" data-role="aspect-options">
                        <button type="button" data-setting="imageAspectRatio" data-value="follow">智能</button>
                        <button type="button" data-setting="imageAspectRatio" data-value="1:1">1:1</button>
                        <button type="button" data-setting="imageAspectRatio" data-value="3:4">3:4</button>
                        <button type="button" data-setting="imageAspectRatio" data-value="4:3">4:3</button>
                        <button type="button" data-setting="imageAspectRatio" data-value="2:3">2:3</button>
                        <button type="button" data-setting="imageAspectRatio" data-value="3:2">3:2</button>
                        <button type="button" data-setting="imageAspectRatio" data-value="9:16">9:16</button>
                        <button type="button" data-setting="imageAspectRatio" data-value="16:9">16:9</button>
                      </div>
                    </div>
                    <div class="xhs-replicator-option-group">
                      <span class="xhs-replicator-option-label">分辨率</span>
                      <div class="xhs-replicator-option-grid is-resolution" data-role="resolution-options">
                        <button type="button" data-setting="imageResolution" data-value="1k">1K</button>
                        <button type="button" data-setting="imageResolution" data-value="2k">2K</button>
                        <button type="button" data-setting="imageResolution" data-value="4k">4K</button>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="xhs-replicator-form-status" data-role="form-status"></div>
              </div>
            </div>
            <div class="xhs-replicator-task-view" data-role="task-view" hidden>
              <div class="xhs-replicator-task-header">
                <button class="xhs-replicator-task-back" type="button" data-role="task-back" aria-label="返回配置">←</button>
                <div>
                  <div class="xhs-replicator-task-title" data-role="task-title">正在复刻</div>
                </div>
              </div>
              <div class="xhs-replicator-status"></div>
              <div class="xhs-replicator-progress" hidden>
                <span class="xhs-replicator-progress-spinner" aria-hidden="true"></span>
                <div class="xhs-replicator-progress-label">正在分析参考图</div>
              </div>
              <button class="xhs-replicator-background-run" type="button" data-role="background-run" hidden>
                后台运行
              </button>
              <div class="xhs-replicator-result" hidden>
                <div class="xhs-replicator-result-card">
                  <img alt="复刻结果" />
                  <button class="xhs-replicator-result-download" type="button" data-role="download" aria-label="下载图片">
                    <svg viewBox="0 0 20 20" aria-hidden="true">
                      <path d="M10 3v9m0 0 3.2-3.2M10 12 6.8 8.8M4 14.5v1.2c0 .7.6 1.3 1.3 1.3h9.4c.7 0 1.3-.6 1.3-1.3v-1.2"></path>
                    </svg>
                    <span>下载</span>
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
        <div class="xhs-replicator-lightbox" data-role="result-lightbox" hidden>
          <button class="xhs-replicator-lightbox-close" type="button" data-role="close-lightbox" aria-label="关闭大图">×</button>
          <img alt="复刻结果大图" />
        </div>
      </div>
    `;

    const previewImage = mask.querySelector(".xhs-replicator-preview img");
    const modalWindow = mask.querySelector(".xhs-replicator-modal");
    const dragHandle = mask.querySelector('[data-role="drag-handle"]');
    const closeButton = mask.querySelector('[data-role="close-window"]');
    const settingsButton = mask.querySelector('[data-role="open-settings"]');
    const optionsButton = mask.querySelector('[data-role="open-options"]');
    const productInput = mask.querySelector("#xhs-replicator-product");
    const uploadCard = mask.querySelector('[data-role="upload-card"]');
    const productChip = mask.querySelector('[data-role="product-chip"]');
    const productThumb = mask.querySelector('[data-role="product-thumb"]');
    const pathButtons = Array.from(mask.querySelectorAll(".xhs-replicator-path-chip"));
    const kindTrigger = mask.querySelector('[data-role="kind-trigger"]');
    const kindLabel = mask.querySelector('[data-role="kind-label"]');
    const kindPopover = mask.querySelector('[data-role="kind-popover"]');
    const optionsPopover = mask.querySelector('[data-role="options-popover"]');
    const optionChoices = Array.from(optionsPopover.querySelectorAll("[data-setting][data-value]"));
    const notesInput = mask.querySelector("#xhs-replicator-notes");
    const quickControls = mask.querySelector(".xhs-replicator-quick-controls");
    const facePolicy = mask.querySelector('[data-role="face-policy"]');
    const status = mask.querySelector(".xhs-replicator-status");
    const progressWrap = mask.querySelector(".xhs-replicator-progress");
    const progressLabel = mask.querySelector(".xhs-replicator-progress-label");
    const resultWrap = mask.querySelector(".xhs-replicator-result");
    const debugText = mask.querySelector(".xhs-replicator-debug-text");
    const resultImage = mask.querySelector(".xhs-replicator-result img");
    const lightbox = mask.querySelector('[data-role="result-lightbox"]');
    const lightboxImage = lightbox.querySelector("img");
    const lightboxClose = mask.querySelector('[data-role="close-lightbox"]');
    const timing = mask.querySelector('[data-role="timing"]');
    const generateButton = mask.querySelector('[data-role="generate"]');
    const formStatus = mask.querySelector('[data-role="form-status"]');
    const formSection = mask.querySelector(".xhs-replicator-form");
    const formView = mask.querySelector('[data-role="form-view"]');
    const taskView = mask.querySelector('[data-role="task-view"]');
    const taskBack = mask.querySelector('[data-role="task-back"]');
    const resultBack = mask.querySelector('[data-role="result-back"]');
    const backgroundRunButton = mask.querySelector('[data-role="background-run"]');
    const taskTitle = mask.querySelector('[data-role="task-title"]');
    const replaceProductButton = mask.querySelector('[data-role="replace-product"]');
    const removeProductButton = mask.querySelector('[data-role="remove-product"]');

    const closeKindPicker = () => {
      kindPopover.hidden = true;
      kindTrigger.setAttribute("aria-expanded", "false");
    };
    const closeOptionsPicker = () => {
      optionsPopover.hidden = true;
      optionsButton.setAttribute("aria-expanded", "false");
    };
    const syncOptionsPicker = async () => {
      const settings = await getLocalTestSettings();
      const selected = {
        imageAspectRatio: String(settings.imageAspectRatio || "follow").toLowerCase(),
        imageResolution: normalizeImageResolution(settings.imageResolution)
      };
      optionChoices.forEach((button) => {
        button.classList.toggle("is-active", selected[button.dataset.setting] === button.dataset.value);
      });
    };
    const closeResultLightbox = () => {
      lightbox.hidden = true;
      lightboxImage.removeAttribute("src");
    };
    const openResultLightbox = () => {
      if (!state.generatedImageUrl) {
        return;
      }
      lightboxImage.src = state.generatedImageUrl;
      lightbox.hidden = false;
    };

    closeButton.addEventListener("click", closeModal);
    optionsButton.addEventListener("click", async () => {
      const shouldOpen = optionsPopover.hidden;
      closeKindPicker();
      optionsPopover.hidden = !shouldOpen;
      optionsButton.setAttribute("aria-expanded", String(shouldOpen));
      if (!shouldOpen) {
        return;
      }
      try {
        await syncOptionsPicker();
      } catch (error) {
        closeOptionsPicker();
        formStatus.textContent = `设置加载失败：${error instanceof Error ? error.message : String(error)}`;
      }
    });
    optionChoices.forEach((button) => {
      button.addEventListener("click", async () => {
        const setting = button.dataset.setting;
        const value = button.dataset.value;
        optionChoices
          .filter((choice) => choice.dataset.setting === setting)
          .forEach((choice) => choice.classList.toggle("is-active", choice === button));
        try {
          await saveQuickSetting(setting, value);
          formStatus.textContent = "";
        } catch (error) {
          await syncOptionsPicker().catch(() => {});
          formStatus.textContent = `设置保存失败：${error instanceof Error ? error.message : String(error)}`;
        }
      });
    });
    settingsButton.addEventListener("click", async () => {
      try {
        const response = await chrome.runtime.sendMessage({ type: "open-options-page" });
        if (!response?.ok) {
          throw new Error(response?.error || "打开失败");
        }
      } catch (error) {
        showReplicatorToast("暂时无法打开 AIC 页面");
      }
    });
    taskBack.addEventListener("click", () => {
      showFormView(formView, taskView);
    });
    resultBack.addEventListener("click", () => {
      resultWrap.hidden = true;
      showFormView(formView, taskView);
    });
    backgroundRunButton.addEventListener("click", () => {
      closeModal();
      showReplicatorToast("任务已转入后台，可在 AIC 页面查看");
    });
    dragHandle.addEventListener("pointerdown", (event) => {
      beginFloatingDrag(event, modalWindow);
    });
    kindTrigger.addEventListener("click", () => {
      const shouldOpen = kindPopover.hidden;
      kindPopover.hidden = !shouldOpen;
      kindTrigger.setAttribute("aria-expanded", String(shouldOpen));
    });
    document.addEventListener("pointerdown", (event) => {
      if (!kindPopover.hidden && !quickControls.contains(event.target)) {
        closeKindPicker();
      }
      if (!optionsPopover.hidden && !optionsPopover.contains(event.target) && !optionsButton.contains(event.target)) {
        closeOptionsPicker();
      }
    }, true);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeKindPicker();
        closeOptionsPicker();
        closeResultLightbox();
      }
    }, true);

    resultImage.tabIndex = 0;
    resultImage.setAttribute("role", "button");
    resultImage.setAttribute("aria-label", "全屏查看生成图片");
    resultImage.addEventListener("click", openResultLightbox);
    resultImage.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openResultLightbox();
      }
    });
    lightboxClose.addEventListener("click", closeResultLightbox);
    lightbox.addEventListener("click", (event) => {
      if (event.target === lightbox) {
        closeResultLightbox();
      }
    });

    const downloadButton = mask.querySelector('[data-role="download"]');
    downloadButton.addEventListener("click", async () => {
      if (!state.generatedImageUrl) {
        return;
      }
      const filename = `commerce-replica-${Date.now()}.png`;
      const label = downloadButton.querySelector("span");
      try {
        const response = await chrome.runtime.sendMessage({
          type: "download-image",
          payload: {
            url: state.generatedImageUrl,
            filename
          }
        });
        label.textContent = response?.ok ? "已打开" : "下载失败";
      } catch (error) {
        label.textContent = "下载失败";
      }
      window.setTimeout(() => {
        label.textContent = "下载";
      }, 1600);
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
    productChip.addEventListener("click", (event) => {
      if (!event.target.closest("button")) {
        productInput.click();
      }
    });
    productChip.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        productInput.click();
      }
    });
    removeProductButton.addEventListener("click", () => {
      clearProductSelection({
        productInput,
        productThumb,
        uploadCard,
        productChip,
        modalWindow
      });
      setGenerationPath(pathButtons, state.generationPath || "apparel", state.generationPathSource || "memory");
    });

    productInput.addEventListener("change", async () => {
      const file = productInput.files?.[0];
      if (!file) {
        clearProductSelection({
          productInput,
          productThumb,
          uploadCard,
          productChip,
          modalWindow
        });
        setGenerationPath(pathButtons, state.generationPath || "apparel", state.generationPathSource || "memory");
        return;
      }

      try {
        state.classificationJobId += 1;
        state.productImageDataUrl = await readFileAsDataUrl(file);
        state.productFileName = file.name;
        productThumb.src = state.productImageDataUrl;
        uploadCard.hidden = true;
        productChip.hidden = false;
        modalWindow.dataset.hasProduct = "true";
        setGenerationPath(pathButtons, state.generationPath || "apparel", state.generationPathSource || "memory");
        formStatus.textContent = "";
      } catch (error) {
        clearProductSelection({
          productInput,
          productThumb,
          uploadCard,
          productChip,
          modalWindow
        });
        formStatus.textContent = `商品图片读取失败：${error instanceof Error ? error.message : String(error)}`;
      }
    });

    pathButtons.forEach((button) => {
      button.addEventListener("click", () => {
        setGenerationPath(pathButtons, button.dataset.path || "", "manual");
        kindLabel.textContent = button.dataset.path === "non_apparel" ? "其他" : "服装";
        closeKindPicker();
        saveRememberedGenerationPath(state.generationPath);
        updateFacePolicyVisibility(facePolicy);
        formStatus.textContent = "";
      });
    });

    function updateAicTaskCount() {
      const pendingCount = state.backgroundTasks.filter((task) => task.status === "running").length;
      settingsButton.dataset.taskCount = pendingCount ? String(pendingCount) : "";
      settingsButton.classList.toggle("has-active-tasks", pendingCount > 0);
      settingsButton.setAttribute(
        "aria-label",
        pendingCount ? `打开 AIC 任务中心，${pendingCount} 个正在运行` : "打开 AIC 任务中心"
      );
    }

    function renderTask(task) {
      if (!task || state.activeTaskId !== task.id) {
        return;
      }
      resultWrap.hidden = true;
      status.textContent = "";
      backgroundRunButton.hidden = task.status !== "running";
      if (task.status === "running") {
        modalWindow.dataset.view = "loading";
        progressWrap.hidden = false;
        progressLabel.textContent = task.stageLabel || "正在分析参考图";
        taskTitle.textContent = "正在复刻";
        taskBack.disabled = false;
        return;
      }
      progressWrap.hidden = true;
      if (task.status === "done") {
        state.generatedImageUrl = task.result.imageUrl;
        state.analysisPrompt = task.result.analysisPrompt || "";
        state.imageRequestDebug = task.result.imageRequestDebug || null;
        resultImage.src = task.result.imageUrl;
        resultWrap.hidden = false;
        modalWindow.dataset.view = "result";
        taskTitle.textContent = "复刻完成";
        return;
      }
      modalWindow.dataset.view = "error";
      taskTitle.textContent = "生成失败";
      status.textContent = "生成暂时失败，可在 AIC 生成记录中重试。";
    }

    async function pollTaskProgress(task) {
      if (!task?.progressId || task.status !== "running") {
        return;
      }
      try {
        const response = await fetch(`http://127.0.0.1:8787/progress/${encodeURIComponent(task.progressId)}`);
        if (!response.ok) {
          return;
        }
        const data = await response.json();
        if (Array.isArray(data.steps) && data.steps.length) {
          const index = Math.max(0, Math.min(Number(data.activeIndex || 0), data.steps.length - 1));
          const nextStageLabel = data.status === "done" ? "生成完成" : `正在${data.steps[index].title}`;
          const stageChanged = task.stageLabel !== nextStageLabel;
          task.stageLabel = nextStageLabel;
          if (state.activeTaskId === task.id && modalWindow.dataset.view === "loading") {
            progressLabel.textContent = task.stageLabel;
          }
          if (stageChanged) {
            saveGenerationRecord({
              id: task.id,
              status: "running",
              stageLabel: task.stageLabel
            });
          }
        }
      } catch (error) {
        // Progress is best-effort; the generation request remains authoritative.
      }
    }

    async function runGenerationTask(task, payload) {
      task.pollTimer = window.setInterval(() => pollTaskProgress(task), 900);
      pollTaskProgress(task);
      try {
        await saveGenerationRecord({
          id: task.id,
          createdAt: task.createdAt,
          status: "running",
          stageLabel: task.stageLabel,
          referenceImageUrl: payload.imageUrl,
          productFileName: payload.productFileName,
          generationPath: payload.generationPath,
          faceIdentityMode: payload.faceIdentityMode,
          userPrompt: payload.userPrompt,
          imageModel: payload.imageModelOverride,
          imageSize: payload.referenceAspectRatio
        });
        const processedProduct = await prepareProductImageForGeneration(
          payload.originalProductImageDataUrl,
          payload.generationPath,
          payload.faceIdentityMode === "regenerate"
        );
        const productThumbDataUrl = await createHistoryThumbnail(payload.originalProductImageDataUrl);
        await saveGenerationRecord({
          id: task.id,
          productImageDataUrl: productThumbDataUrl
        });
        const response = await replicateImageDirectly({
          ...payload,
          productImageDataUrl: processedProduct.dataUrl,
          progressId: task.progressId
        });
        if (!response?.ok) {
          throw new Error(response?.error || "请求失败");
        }
        task.status = "done";
        task.stageLabel = "生成完成";
        task.result = response.result;
        const resultThumbDataUrl = await createHistoryThumbnail(response.result.imageUrl, {
          maxSide: 720,
          quality: 0.78
        });
        await saveGenerationRecord({
          id: task.id,
          status: "done",
          stageLabel: "生成完成",
          imageUrl: response.result.imageUrl,
          resultImageDataUrl: resultThumbDataUrl,
          prompt: response.result.prompt || "",
          referenceImageUrl: payload.imageUrl,
          productImageDataUrl: productThumbDataUrl,
          productFileName: payload.productFileName,
          productSubjectHint: "",
          generationPath: response.result.generationPath || payload.generationPath,
          faceIdentityMode: payload.faceIdentityMode,
          userPrompt: payload.userPrompt,
          imageModel: payload.imageModelOverride,
          imageSize: response.result.imageSize || payload.referenceAspectRatio,
          imageResolution: response.result.imageResolution || "1k"
        });
      } catch (error) {
        task.status = "error";
        task.stageLabel = "生成失败";
        task.error = error instanceof Error ? error.message : String(error);
        await saveGenerationRecord({
          id: task.id,
          status: "error",
          stageLabel: "生成失败",
          error: task.error
        });
      } finally {
        if (task.pollTimer) {
          window.clearInterval(task.pollTimer);
          task.pollTimer = null;
        }
        updateAicTaskCount();
        if (state.activeTaskId === task.id && !taskView.hidden) {
          renderTask(task);
        }
      }
    }

    generateButton.addEventListener("click", () => {
      if (!state.currentImageUrl) {
        formStatus.textContent = "没有拿到参考图地址，请重新 hover 一次图片。";
        return;
      }
      if (!state.productImageDataUrl) {
        formStatus.textContent = "请先上传你自己的商品图片。";
        return;
      }
      if (!state.generationPath) {
        formStatus.textContent = "请选择商品类型。";
        return;
      }

      formStatus.textContent = "";
      const progressId = createProgressId();
      const task = {
        id: progressId,
        progressId,
        title: `AI复刻 ${state.backgroundTasks.length + 1}`,
        createdAt: new Date().toISOString(),
        status: "running",
        stageLabel: "正在分析参考图",
        referenceImageUrl: state.currentImageUrl,
        result: null,
        error: "",
        pollTimer: null
      };
      const payload = {
        imageUrl: state.currentImageUrl,
        originalProductImageDataUrl: state.productImageDataUrl,
        productFileName: state.productFileName,
        productSubjectHint: "",
        generationPath: state.generationPath,
        faceIdentityMode: state.faceIdentityMode,
        userPrompt: notesInput.value.trim(),
        referenceAspectRatio: getReferenceAspectRatio(),
        imageModelOverride: state.imageModel
      };
      state.backgroundTasks.unshift(task);
      state.activeTaskId = task.id;
      updateAicTaskCount();
      showTaskView(formView, taskView);
      renderTask(task);
      runGenerationTask(task, payload);
    });

    document.documentElement.appendChild(mask);
    return {
      mask,
      modalWindow,
      previewImage,
      productInput,
      uploadCard,
      productChip,
      productThumb,
      pathButtons,
      notesInput,
      facePolicy,
      status,
      progressWrap,
      progressLabel,
      formSection,
      formStatus,
      formView,
      taskView,
      taskBack,
      taskTitle,
      resultWrap,
      debugText,
      resultImage,
      lightbox,
      lightboxImage,
      timing
    };
  }

  function openModal() {
    if (!state.currentImageUrl) {
      return;
    }
    modal.previewImage.src = state.currentImageUrl;
    modal.notesInput.value = "";
    modal.status.textContent = "";
    modal.formStatus.textContent = "";
    showFormView(modal.formView, modal.taskView);
    stopProgress(modal.progressWrap, modal.progressLabel);
    if (state.productImageDataUrl) {
      modal.productThumb.src = state.productImageDataUrl;
      modal.uploadCard.hidden = true;
      modal.productChip.hidden = false;
      modal.modalWindow.dataset.hasProduct = "true";
    } else {
      clearProductSelection({
        productInput: modal.productInput,
        productThumb: modal.productThumb,
        uploadCard: modal.uploadCard,
        productChip: modal.productChip,
        modalWindow: modal.modalWindow
      });
    }
    setGenerationPath(modal.pathButtons, state.generationPath || "apparel", state.generationPathSource || "memory");
    updateFacePolicyVisibility(modal.facePolicy);
    modal.resultWrap.hidden = true;
    if (modal.debugText) {
      modal.debugText.textContent = "";
    }
    renderTiming(modal.timing, []);
    modal.resultImage.removeAttribute("src");
    modal.lightbox.hidden = true;
    modal.lightboxImage.removeAttribute("src");
    const anchorRect = trigger.getBoundingClientRect();
    const imageRect = state.currentImage?.getBoundingClientRect?.() || null;
    hideTrigger();
    modal.mask.dataset.open = "true";
    modal.mask.style.display = "block";
    positionFloatingWindow(modal.modalWindow, { anchorRect, imageRect });
    modal.formSection.scrollTop = 0;
  }

  function closeModal() {
    modal.lightbox.hidden = true;
    modal.lightboxImage.removeAttribute("src");
    modal.mask.dataset.open = "false";
    modal.mask.style.display = "";
  }

  function showTaskView(formView, taskView) {
    formView.hidden = true;
    taskView.hidden = false;
    taskView.closest(".xhs-replicator-modal")?.setAttribute("data-view", "loading");
  }

  function showFormView(formView, taskView) {
    formView.hidden = false;
    taskView.hidden = true;
    taskView.closest(".xhs-replicator-modal")?.setAttribute("data-view", "form");
  }

  function showReplicatorToast(message) {
    document.querySelector(".xhs-replicator-toast")?.remove();
    const toast = document.createElement("div");
    toast.className = "xhs-replicator-toast";
    toast.textContent = message;
    document.documentElement.appendChild(toast);
    window.requestAnimationFrame(() => toast.classList.add("is-visible"));
    window.setTimeout(() => {
      toast.classList.remove("is-visible");
      window.setTimeout(() => toast.remove(), 180);
    }, 2400);
  }

  function positionFloatingWindow(modalWindow, { anchorRect = null, imageRect = null } = {}) {
    const margin = 20;
    const rect = modalWindow.getBoundingClientRect();
    const width = rect.width || Math.min(400, window.innerWidth - margin * 2);
    const height = rect.height || width;
    if (anchorRect && imageRect) {
      // Prefer a nearby edge position with the least possible overlap on the source image.
      const gap = 12;
      const candidates = [
        { x: imageRect.right + gap, y: anchorRect.top },
        { x: imageRect.left - width - gap, y: anchorRect.top },
        { x: anchorRect.right - width, y: imageRect.bottom + gap },
        { x: anchorRect.right - width, y: imageRect.top - height - gap }
      ];
      const anchorX = anchorRect.left + anchorRect.width / 2;
      const anchorY = anchorRect.top + anchorRect.height / 2;
      const ranked = candidates.map((candidate) => {
        const clamped = clampFloatingPosition(candidate.x, candidate.y, width, height);
        const modalRect = {
          left: clamped.x,
          top: clamped.y,
          right: clamped.x + width,
          bottom: clamped.y + height
        };
        const overlapWidth = Math.max(0, Math.min(modalRect.right, imageRect.right) - Math.max(modalRect.left, imageRect.left));
        const overlapHeight = Math.max(0, Math.min(modalRect.bottom, imageRect.bottom) - Math.max(modalRect.top, imageRect.top));
        const overlapArea = overlapWidth * overlapHeight;
        const distance = Math.hypot(clamped.x - anchorX, clamped.y - anchorY);
        return { ...clamped, score: overlapArea * 1000 + distance };
      });
      ranked.sort((a, b) => a.score - b.score);
      state.floatingX = ranked[0].x;
      state.floatingY = ranked[0].y;
    } else if (state.floatingX === null || state.floatingY === null) {
      state.floatingX = Math.max(margin, window.innerWidth - width - margin);
      state.floatingY = Math.max(margin, Math.min(88, window.innerHeight - height - margin));
    }
    const position = clampFloatingPosition(state.floatingX, state.floatingY, width, height);
    state.floatingX = position.x;
    state.floatingY = position.y;
    modalWindow.style.left = `${position.x}px`;
    modalWindow.style.top = `${position.y}px`;
  }

  function beginFloatingDrag(event, modalWindow) {
    if (event.button !== 0 || event.target.closest("button, input, select, textarea, summary, a")) {
      return;
    }
    event.preventDefault();
    const rect = modalWindow.getBoundingClientRect();
    const offsetX = event.clientX - rect.left;
    const offsetY = event.clientY - rect.top;
    event.currentTarget?.setPointerCapture?.(event.pointerId);
    modalWindow.dataset.dragging = "true";

    const handleMove = (moveEvent) => {
      const next = clampFloatingPosition(
        moveEvent.clientX - offsetX,
        moveEvent.clientY - offsetY,
        rect.width,
        rect.height
      );
      state.floatingX = next.x;
      state.floatingY = next.y;
      modalWindow.style.left = `${next.x}px`;
      modalWindow.style.top = `${next.y}px`;
    };

    const handleEnd = () => {
      modalWindow.dataset.dragging = "false";
      window.removeEventListener("pointermove", handleMove, true);
      window.removeEventListener("pointerup", handleEnd, true);
      window.removeEventListener("pointercancel", handleEnd, true);
    };

    window.addEventListener("pointermove", handleMove, true);
    window.addEventListener("pointerup", handleEnd, true);
    window.addEventListener("pointercancel", handleEnd, true);
  }

  function clampFloatingPosition(x, y, width, height) {
    const margin = 12;
    const maxX = Math.max(margin, window.innerWidth - width - margin);
    const maxY = Math.max(margin, window.innerHeight - height - margin);
    return {
      x: Math.min(Math.max(margin, x), maxX),
      y: Math.min(Math.max(margin, y), maxY)
    };
  }

  function placeTrigger(image) {
    const rect = image.getBoundingClientRect();
    const inset = 12;
    trigger.style.display = "inline-flex";
    const triggerWidth = trigger.offsetWidth || 92;
    const triggerHeight = trigger.offsetHeight || 36;
    const left = rect.right - triggerWidth - inset;
    const top = rect.top + inset;
    trigger.style.left = `${Math.max(inset, Math.min(left, window.innerWidth - triggerWidth - inset))}px`;
    trigger.style.top = `${Math.max(inset, Math.min(top, window.innerHeight - triggerHeight - inset))}px`;
  }

  function hideTrigger() {
    clearHideTrigger();
    trigger.style.display = "none";
  }

  function clearProductSelection({ productInput, productThumb, uploadCard, productChip, modalWindow }) {
    state.classificationJobId += 1;
    state.productImageDataUrl = "";
    state.productFileName = "";
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
    if (modalWindow) {
      delete modalWindow.dataset.hasProduct;
    }
  }

  function setGenerationPath(pathButtons, nextPath, source = "") {
    state.generationPath = nextPath;
    state.generationPathSource = nextPath ? source : "";
    pathButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.path === nextPath);
    });
    const modalRoot = pathButtons[0]?.closest(".xhs-replicator-modal");
    const pathLabel = modalRoot?.querySelector('[data-role="kind-label"]');
    if (pathLabel) {
      pathLabel.textContent = nextPath === "non_apparel" ? "其他" : "服装";
    }
  }

  function updateFacePolicyVisibility(container) {
    if (!container) {
      return;
    }
    container.hidden = state.generationPath !== "apparel";
  }

  function normalizeFaceIdentityMode(value) {
    return value === "preserve_reference" ? "preserve_reference" : "regenerate";
  }

  async function loadRememberedGenerationPath() {
    try {
      const storage = await chrome.storage.local.get([PRODUCT_KIND_KEY]);
      const remembered = normalizeGenerationPath(storage?.[PRODUCT_KIND_KEY]);
      if (remembered) {
        setGenerationPath(modal.pathButtons, remembered, "memory");
      } else {
        setGenerationPath(modal.pathButtons, state.generationPath, "memory");
      }
      updateFacePolicyVisibility(modal.facePolicy);
    } catch (error) {
      setGenerationPath(modal.pathButtons, state.generationPath, "memory");
      updateFacePolicyVisibility(modal.facePolicy);
    }
  }

  async function saveRememberedGenerationPath(path) {
    const normalized = normalizeGenerationPath(path);
    if (!normalized) {
      return;
    }
    try {
      await chrome.storage.local.set({ [PRODUCT_KIND_KEY]: normalized });
    } catch (error) {
      console.warn("[Commerce Replicator] 保存商品主体偏好失败", error);
    }
  }

  function normalizeGenerationPath(path) {
    return path === "apparel" || path === "non_apparel" ? path : "";
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

  function findCandidateImageFromTarget(target) {
    if (!(target instanceof Element)) {
      return null;
    }

    const directImage = target.closest("img");
    if (directImage instanceof HTMLImageElement && isCandidateImage(directImage)) {
      return directImage;
    }

    const card = target.closest(
      [
        "[data-note-id]",
        ".note-item",
        ".feeds-page .note-item",
        ".explore-feed .note-item",
        ".cover",
        "a[href*='/explore/']",
        "a[href*='/discovery/item']"
      ].join(",")
    );
    if (!card) {
      return null;
    }

    return pickBestCandidateImage(Array.from(card.querySelectorAll("img")));
  }

  function pickBestCandidateImage(images) {
    let best = null;
    let bestArea = 0;
    for (const image of images) {
      if (!(image instanceof HTMLImageElement) || !isCandidateImage(image)) {
        continue;
      }
      const rect = image.getBoundingClientRect();
      const area = Math.max(0, rect.width) * Math.max(0, rect.height);
      if (area > bestArea) {
        best = image;
        bestArea = area;
      }
    }
    return best;
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

  async function prepareProductImageForGeneration(dataUrl, generationPath, shouldMaskFaces) {
    const prepared = shouldMaskFaces
      ? await maskFacesInImage(dataUrl, {
          preservePeripheralProducts: generationPath === "non_apparel"
        })
      : { dataUrl, masked: false, faceCount: 0 };
    return {
      ...prepared,
      dataUrl: await normalizeProductReferenceResolution(prepared.dataUrl)
    };
  }

  async function normalizeProductReferenceResolution(dataUrl) {
    if (!isDataUrl(dataUrl)) {
      return dataUrl;
    }
    try {
      const image = await loadImage(dataUrl);
      const width = image.naturalWidth || image.width;
      const height = image.naturalHeight || image.height;
      const compactCanvas = createCompactWhiteBackgroundProductCanvas(image, width, height);
      if (compactCanvas) {
        return compactCanvas.toDataURL("image/jpeg", 0.96);
      }
      const longestSide = Math.max(width, height);
      if (!longestSide || longestSide >= 1024) {
        return dataUrl;
      }
      const scale = 1024 / longestSide;
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(width * scale));
      canvas.height = Math.max(1, Math.round(height * scale));
      const context = canvas.getContext("2d");
      context.imageSmoothingEnabled = true;
      context.imageSmoothingQuality = "high";
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL("image/jpeg", 0.94);
    } catch (error) {
      return dataUrl;
    }
  }

  function createCompactWhiteBackgroundProductCanvas(image, width, height) {
    const source = document.createElement("canvas");
    source.width = width;
    source.height = height;
    const context = source.getContext("2d", { willReadFrequently: true });
    context.drawImage(image, 0, 0, width, height);
    const pixels = context.getImageData(0, 0, width, height).data;
    const sampleInset = Math.max(1, Math.round(Math.min(width, height) * 0.03));
    const corners = [
      [sampleInset, sampleInset],
      [width - sampleInset - 1, sampleInset],
      [sampleInset, height - sampleInset - 1],
      [width - sampleInset - 1, height - sampleInset - 1]
    ];
    const whiteCorners = corners.filter(([x, y]) => {
      const offset = (y * width + x) * 4;
      return pixels[offset] >= 238 && pixels[offset + 1] >= 238 && pixels[offset + 2] >= 238;
    }).length;
    if (whiteCorners < 3) {
      return null;
    }

    const rowCounts = new Array(height).fill(0);
    const rowThreshold = Math.max(2, Math.round(width * 0.01));
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        const offset = (y * width + x) * 4;
        const isForeground =
          pixels[offset + 3] > 24 &&
          (pixels[offset] < 238 || pixels[offset + 1] < 238 || pixels[offset + 2] < 238);
        if (isForeground) {
          rowCounts[y] += 1;
        }
      }
    }

    const spans = [];
    const bridgeGap = Math.max(4, Math.round(height * 0.025));
    let start = -1;
    let lastActive = -1;
    for (let y = 0; y < height; y += 1) {
      if (rowCounts[y] >= rowThreshold) {
        if (start < 0) {
          start = y;
        }
        lastActive = y;
      } else if (start >= 0 && y - lastActive > bridgeGap) {
        spans.push([start, lastActive]);
        start = -1;
        lastActive = -1;
      }
    }
    if (start >= 0) {
      spans.push([start, lastActive]);
    }

    const minPixels = Math.max(80, Math.round(width * height * 0.0012));
    const boxes = spans.map(([top, bottom]) => {
      let left = width;
      let right = -1;
      let count = 0;
      for (let y = top; y <= bottom; y += 1) {
        for (let x = 0; x < width; x += 1) {
          const offset = (y * width + x) * 4;
          const isForeground =
            pixels[offset + 3] > 24 &&
            (pixels[offset] < 238 || pixels[offset + 1] < 238 || pixels[offset + 2] < 238);
          if (isForeground) {
            left = Math.min(left, x);
            right = Math.max(right, x);
            count += 1;
          }
        }
      }
      return { left, right, top, bottom, count };
    }).filter((box) =>
      box.right >= box.left &&
      box.count >= minPixels &&
      box.right - box.left + 1 >= width * 0.08 &&
      box.bottom - box.top + 1 >= height * 0.04
    );
    if (!boxes.length || boxes.length > 6) {
      return null;
    }

    const selected = boxes
      .sort((a, b) => b.count - a.count)
      .slice(0, 4)
      .sort((a, b) => a.top - b.top);
    const output = document.createElement("canvas");
    output.width = 1024;
    output.height = 1024;
    const outputContext = output.getContext("2d");
    outputContext.fillStyle = "#ffffff";
    outputContext.fillRect(0, 0, output.width, output.height);
    outputContext.imageSmoothingEnabled = true;
    outputContext.imageSmoothingQuality = "high";
    const slotHeight = output.height / selected.length;
    const slotPadding = 44;
    selected.forEach((box, index) => {
      const padX = Math.max(3, Math.round((box.right - box.left + 1) * 0.08));
      const padY = Math.max(3, Math.round((box.bottom - box.top + 1) * 0.08));
      const sourceX = Math.max(0, box.left - padX);
      const sourceY = Math.max(0, box.top - padY);
      const sourceRight = Math.min(width, box.right + padX + 1);
      const sourceBottom = Math.min(height, box.bottom + padY + 1);
      const sourceWidth = sourceRight - sourceX;
      const sourceHeight = sourceBottom - sourceY;
      const scale = Math.min(
        (output.width - slotPadding * 2) / sourceWidth,
        (slotHeight - slotPadding * 2) / sourceHeight
      );
      const targetWidth = Math.max(1, Math.round(sourceWidth * scale));
      const targetHeight = Math.max(1, Math.round(sourceHeight * scale));
      const targetX = Math.round((output.width - targetWidth) / 2);
      const targetY = Math.round(index * slotHeight + (slotHeight - targetHeight) / 2);
      outputContext.drawImage(
        source,
        sourceX,
        sourceY,
        sourceWidth,
        sourceHeight,
        targetX,
        targetY,
        targetWidth,
        targetHeight
      );
    });
    return output;
  }

  async function maskFacesInImage(dataUrl, { preservePeripheralProducts = false } = {}) {
    if (!isDataUrl(dataUrl)) {
      return { dataUrl, masked: false, faceCount: 0 };
    }

    try {
      const image = await loadImage(dataUrl);
      const width = image.naturalWidth || image.width;
      const height = image.naturalHeight || image.height;
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      context.drawImage(image, 0, 0, width, height);

      const faces = await detectProductFaces(canvas, dataUrl, width, height);
      if (!Array.isArray(faces) || faces.length === 0) {
        return { dataUrl, masked: false, faceCount: 0 };
      }

      faces.forEach((face) => {
        const box = expandFaceBox(face.boundingBox, width, height, preservePeripheralProducts);
        pixelateRegion(context, box);
        context.save();
        context.fillStyle = "rgba(26, 26, 28, 0.74)";
        context.fillRect(box.x, box.y, box.width, box.height);
        context.strokeStyle = "rgba(255, 255, 255, 0.52)";
        context.lineWidth = Math.max(2, Math.round(Math.min(width, height) * 0.004));
        context.strokeRect(box.x, box.y, box.width, box.height);
        context.restore();
      });

      return {
        dataUrl: canvas.toDataURL("image/jpeg", 0.92),
        masked: true,
        faceCount: faces.length
      };
    } catch (error) {
      console.warn("[Commerce Replicator] 商品图人脸遮挡失败，已继续使用原图", error);
      return { dataUrl, masked: false, faceCount: 0 };
    }
  }

  async function detectProductFaces(canvas, dataUrl, width, height) {
    const FaceDetectorConstructor = window.FaceDetector || globalThis.FaceDetector;
    if (FaceDetectorConstructor) {
      const detector = new FaceDetectorConstructor({
        fastMode: true,
        maxDetectedFaces: 8
      });
      return detector.detect(canvas);
    }
    const faces = await detectProductFacesWithBackend(dataUrl);
    return faces.map((face) => ({
      boundingBox: {
        x: face.x * width,
        y: face.y * height,
        width: face.width * width,
        height: face.height * height
      }
    }));
  }

  async function detectProductFacesWithBackend(dataUrl) {
    try {
      const settings = await getLocalTestSettings();
      const response = await fetch(`${settings.backendBaseUrl.replace(/\/+$/, "")}/detect-faces`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          productImageDataUrl: dataUrl,
          visionModel: settings.visionModel
        })
      });
      if (!response.ok) {
        return [];
      }
      const data = await response.json();
      return Array.isArray(data?.faces) ? data.faces.filter(isNormalizedFaceBox) : [];
    } catch (error) {
      console.warn("[Commerce Replicator] 后端人脸定位失败，已继续使用原图", error);
      return [];
    }
  }

  function isNormalizedFaceBox(face) {
    if (!face || typeof face !== "object") {
      return false;
    }
    return ["x", "y", "width", "height"].every((key) => {
      const value = Number(face[key]);
      return Number.isFinite(value) && value >= 0 && value <= 1;
    });
  }

  function expandFaceBox(boundingBox, imageWidth, imageHeight, preservePeripheralProducts = false) {
    const source = boundingBox || {};
    const x = Number(source.x) || 0;
    const y = Number(source.y) || 0;
    const width = Number(source.width) || 0;
    const height = Number(source.height) || 0;
    if (preservePeripheralProducts) {
      const insetX = width * 0.14;
      const insetTop = height * 0.04;
      const insetBottom = height * 0.08;
      const nextX = Math.max(0, Math.floor(x + insetX));
      const nextY = Math.max(0, Math.floor(y + insetTop));
      const nextRight = Math.min(imageWidth, Math.ceil(x + width - insetX));
      const nextBottom = Math.min(imageHeight, Math.ceil(y + height - insetBottom));
      return {
        x: nextX,
        y: nextY,
        width: Math.max(1, nextRight - nextX),
        height: Math.max(1, nextBottom - nextY)
      };
    }
    const padX = width * 0.32;
    const padTop = height * 0.28;
    const padBottom = height * 0.42;
    const nextX = Math.max(0, Math.floor(x - padX));
    const nextY = Math.max(0, Math.floor(y - padTop));
    const nextRight = Math.min(imageWidth, Math.ceil(x + width + padX));
    const nextBottom = Math.min(imageHeight, Math.ceil(y + height + padBottom));
    return {
      x: nextX,
      y: nextY,
      width: Math.max(1, nextRight - nextX),
      height: Math.max(1, nextBottom - nextY)
    };
  }

  function pixelateRegion(context, box) {
    const sampleWidth = Math.max(1, Math.round(box.width / 12));
    const sampleHeight = Math.max(1, Math.round(box.height / 12));
    const sampleCanvas = document.createElement("canvas");
    sampleCanvas.width = sampleWidth;
    sampleCanvas.height = sampleHeight;
    const sampleContext = sampleCanvas.getContext("2d");
    sampleContext.imageSmoothingEnabled = true;
    sampleContext.drawImage(
      context.canvas,
      box.x,
      box.y,
      box.width,
      box.height,
      0,
      0,
      sampleWidth,
      sampleHeight
    );
    context.save();
    context.imageSmoothingEnabled = false;
    context.drawImage(sampleCanvas, 0, 0, sampleWidth, sampleHeight, box.x, box.y, box.width, box.height);
    context.restore();
  }

  async function replicateImageDirectly(payload) {
    const settings = await getLocalTestSettings();
    const imageSize = resolveConfiguredAspectRatio(
      settings.imageAspectRatio,
      payload.referenceAspectRatio
    );
    const imageResolution = normalizeImageResolution(settings.imageResolution);
    const requestBody = {
      imageUrl: payload.imageUrl,
      productImageDataUrl: payload.productImageDataUrl,
      productFileName: payload.productFileName || "",
      productSubjectHint: payload.productSubjectHint || "",
      generationPath: payload.generationPath || "",
      faceIdentityMode: normalizeFaceIdentityMode(payload.faceIdentityMode),
      progressId: payload.progressId || "",
      userPrompt: payload.userPrompt || "",
      model: payload.imageModelOverride || settings.model,
      visionModel: settings.visionModel,
      nonApparelPrompt: settings.nonApparelPrompt,
      apparelFinalPrompt: settings.apparelFinalPrompt,
      defaultUserPrompt: settings.defaultUserPrompt,
      imageSize,
      responseDataPath: settings.responseDataPath,
      extraBody: buildGenerationExtraBody(settings)
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
        faceIdentityMode: normalizeFaceIdentityMode(data.faceIdentityMode || payload.faceIdentityMode),
        referenceHasFace: Boolean(data.referenceHasFace),
        analysisPrompt: data.analysisPrompt || "",
        productAnalysisPrompt: data.productAnalysisPrompt || "",
        referenceAnalysisPrompt: data.referenceAnalysisPrompt || "",
        imageSize,
        imageResolution
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
    const effectiveResponse = await chrome.runtime.sendMessage({ type: "get-effective-settings" });
    if (effectiveResponse?.ok) {
      return effectiveResponse.result || {};
    }
    const defaultsResponse = await chrome.runtime.sendMessage({ type: "get-default-settings" });
    return defaultsResponse?.ok ? defaultsResponse.result || {} : {};
  }

  async function saveQuickSetting(name, value) {
    if (!name || typeof value !== "string") {
      throw new Error("设置项无效");
    }
    const localStorage = await chrome.storage.local.get([SETTINGS_KEY]);
    let savedSettings = localStorage?.[SETTINGS_KEY];
    if (!savedSettings || typeof savedSettings !== "object") {
      const syncStorage = await chrome.storage.sync.get([SETTINGS_KEY]);
      savedSettings = syncStorage?.[SETTINGS_KEY];
    }
    await chrome.storage.local.set({
      [SETTINGS_KEY]: {
        ...(savedSettings && typeof savedSettings === "object" ? savedSettings : {}),
        [name]: value
      }
    });
    await chrome.storage.sync.remove(SETTINGS_KEY);
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

  function buildGenerationExtraBody(settings) {
    return {
      ...parseExtraBody(settings.extraBody),
      dreaminaResolutionType: normalizeImageResolution(settings.imageResolution)
    };
  }

  function normalizeImageResolution(value) {
    const normalized = String(value || "").trim().toLowerCase();
    return ["1k", "2k", "4k"].includes(normalized) ? normalized : "1k";
  }

  function resolveConfiguredAspectRatio(configuredValue, referenceValue) {
    const configured = String(configuredValue || "follow").trim().toLowerCase();
    if (configured !== "follow" && parseRatio(configured)) {
      return configured;
    }
    const reference = String(referenceValue || "").trim().toLowerCase();
    return parseRatio(reference) ? reference : "1:1";
  }

  function formatBackendError(status, text) {
    if (!text) {
      return `复刻失败 (${status})：未知错误`;
    }
    try {
      const parsed = JSON.parse(text);
      const message = parsed?.error || text;
      return `复刻失败 (${status})：${String(message).slice(0, 500)}`;
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
      kimi_non_apparel_prompt: "场景复刻 Prompt",
      kimi_apparel_reference_description: "参考图描述",
      kimi_apparel_final_prompt: "商品融合 Prompt"
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

  function startProgress(progressWrap, progressLabel, generationPath, progressId) {
    stopProgress(progressWrap, progressLabel);
    progressWrap.hidden = false;
    const steps = getProgressSteps(generationPath);
    state.progressSteps = steps;
    state.currentStageIndex = 0;
    renderProgressSteps(0);
    progressLabel.textContent = "正在分析参考图";
    state.progressTimer = window.setInterval(() => {
      pollBackendProgress(progressId, progressLabel);
    }, 900);
    pollBackendProgress(progressId, progressLabel);
  }

  async function pollBackendProgress(progressId, progressLabel) {
    if (!progressId) {
      return;
    }
    try {
      const response = await fetch(`http://127.0.0.1:8787/progress/${encodeURIComponent(progressId)}`);
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      updateProgressFromBackend(data, progressLabel);
    } catch (error) {
      // 进度轮询失败不打断主生成请求，最终错误由主请求展示。
    }
  }

  function updateProgressFromBackend(data, progressLabel) {
    if (!data || !Array.isArray(data.steps) || !data.steps.length) {
      return;
    }
    state.progressSteps = data.steps;
    const index = Math.max(0, Math.min(Number(data.activeIndex || 0), data.steps.length - 1));
    state.currentStageIndex = index;
    const terminalState = data.status === "done" ? "done" : data.status === "error" ? "error" : "";
    renderProgressSteps(index, terminalState);
    progressLabel.textContent = data.status === "done"
      ? "生成完成"
      : `正在${data.steps[index].title}`;
  }

  function finishProgress(progressWrap, progressLabel) {
    clearProgressTimers();
    const steps = state.progressSteps.length ? state.progressSteps : getProgressSteps(state.generationPath);
    state.currentStageIndex = steps.length - 1;
    renderProgressSteps(steps.length - 1, "done");
    progressLabel.textContent = "生成完成";
    progressWrap.hidden = true;
  }

  function stopProgress(progressWrap, progressLabel) {
    clearProgressTimers();
    progressWrap.hidden = true;
    progressLabel.textContent = "正在分析参考图";
    state.progressSteps = [];
    state.currentStageIndex = 0;
    renderProgressSteps(0);
  }

  function failProgress(progressWrap, progressLabel) {
    clearProgressTimers();
    if (!state.progressSteps.length) {
      stopProgress(progressWrap, progressLabel);
      return;
    }
    progressWrap.hidden = false;
    renderProgressSteps(state.currentStageIndex, "error");
    progressLabel.textContent = "生成未完成";
  }

  function clearProgressTimers() {
    if (state.progressTimer) {
      window.clearInterval(state.progressTimer);
      state.progressTimer = null;
    }
  }

  function getProgressSteps(generationPath) {
    return [
      { title: "分析参考图" },
      { title: "生成 Prompt" },
      { title: "生成图片" }
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
            <strong>${escapeHtml(step.title)}</strong>
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
