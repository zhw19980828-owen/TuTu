const DEFAULT_SETTINGS = {
  backendBaseUrl: "http://127.0.0.1:8787",
  proxyToken: "",
  model: "openai/gpt-5.4-image-2",
  visionModel: "moonshotai/kimi-k2.6",
  nonApparelPrompt:
    "你是一位电商静物与非服饰商品复刻提示词专家。你会同时看到一张参考图和一张商品图。你的任务是把两张图转成一段最终可以直接交给生图模型的中文 prompt，让生图模型生成一张“用户商品主体正确，但摄影语言和参考图高度一致”的新图片。参考图只负责提供画面模板，你必须准确识别并继承参考图里的拍摄方式、画幅比例、景别、镜头角度、机位高低、焦段感、主体在画面中的位置和占比、主体朝向、主体倾斜角度、主体俯仰角度、主体与承载面的接触点、主体是否平放/斜放/竖立/悬浮/倚靠、多个物体之间的前后层级和遮挡关系、主体边缘与画面边界的距离、裁切方式、场景地点、背景元素、承载面材质、时间段、主光方向、光线质感、色温、曝光方式、色彩氛围、景深关系、主体与背景的光影关系，以及画面中原本存在的真实陈列和生活痕迹。商品图会直接作为后续生图模型的唯一商品参考图，因此最终 prompt 里不要详细描述商品本身的颜色、材质、品牌、logo、文字、纹理、形状、结构、链节、刻字、装饰、边缘、工艺、尺寸等视觉细节，这些交给图像参考通道。你只能极简点明商品品类和融入方式，例如“一枚戒指作为主体”“一个包放在桌面中央”“一瓶香水替换原主体”。最终输出必须是一整段中文 prompt，直接描述最终生成图片本身：保留参考图的场景、构图、镜头角度、主体摆放姿态、主体朝向、主体落点、前后层级、光影、景别、主体大小和整体气质，让商品图中的商品作为新主体出现在相同视觉框架里。不要输出解释、标题、分析过程、分点或 JSON。",
  apparelPortraitPrompt:
    "你是一位电商服饰模特设定提示词专家。你会看到一张参考图，这张图只用来生成一张新的模特人像垫图，后续再把用户的服饰商品替换上去。你的任务是只根据参考图输出一整段中文生图 prompt，用于先生成一张与参考图人物气质、性别、年龄感、脸型、发型长度、发色、妆容浓度、视线方向、头部倾斜、身体朝向、动作姿态、镜头角度、景别、主体占比、裁切方式、场景地点、时间段、背景布局、色彩氛围、光影关系都尽量相似的模特人像图片。你必须保留参考图的人像出镜形式和构图骨架，但要让模特穿着尽量简洁、干净、贴身、低干扰的基础内搭或无明显设计感的占位服装，避免外套、复杂印花、大面积文字、夸张配饰和抢主体的服装细节，以便后续服饰替换。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
  apparelFinalPrompt:
    "你是一位电商服饰换装复刻提示词专家。你会看到参考图、生成的人像垫图和用户的商品图。参考图只负责提供场景模板，你必须继承参考图里的时间段、天气、场景地点、背景布局、机位、镜头角度、景别、主体占比、裁切方式、人物姿态、手部位置、视线方向、光影关系和整体营销氛围。生成的人像垫图是最终模特基础，你必须尽量保留它的人脸、发型、体态、肢体关系和取景裁切。商品图只负责提供要替换上身的服饰主体，商品图会在后续生成阶段作为参考图输入，因此你不需要冗长描述基础颜色和大体轮廓，只需要在容易丢失时补充品牌文字、logo、领口结构、袖型、纽扣排布、特殊拼接、不对称设计、特殊面料工艺等关键特征。你的任务是输出一整段最终给生图模型使用的中文 prompt，要求把商品服饰自然穿在模特对应部位，保持参考图的构图骨架和动作，不要擅自改性别、改人数、改景别、改主体大小，也不要把服饰替换成完全不同的穿法。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
  defaultUserPrompt: "输出适合电商投放和商品详情页的高清主视觉，主体明确，商品细节清晰，画面干净高级。",
  imageSize: "2K",
  responseDataPath: "",
  extraBody: "{}"
};
const SETTINGS_KEY = "userSettings";
const GENERATION_RECORDS_KEY = "generationRecords";
const MAX_GENERATION_RECORDS = 120;
const LEGACY_MODEL_MAP = {
  "doubao-seedream-4-5-251128": DEFAULT_SETTINGS.model,
  "doubao-seed-1-6-251015": DEFAULT_SETTINGS.visionModel
};

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "get-default-settings") {
    sendResponse({ ok: true, result: DEFAULT_SETTINGS });
    return true;
  }

  if (message?.type === "get-generation-records") {
    getGenerationRecords()
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) =>
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : String(error)
        })
      );
    return true;
  }

  if (message?.type === "replicate-image") {
    handleReplicateImage(message.payload)
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) =>
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : String(error)
        })
      );
    return true;
  }

  if (message?.type === "classify-product") {
    handleClassifyProduct(message.payload)
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) =>
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : String(error)
        })
      );
    return true;
  }

  if (message?.type === "download-image") {
    chrome.downloads.download(
      {
        url: message.payload.url,
        filename: message.payload.filename,
        saveAs: true
      },
      () => {
        if (chrome.runtime.lastError) {
          sendResponse({ ok: false, error: chrome.runtime.lastError.message });
          return;
        }
        sendResponse({ ok: true });
      }
    );
    return true;
  }

  if (message?.type === "open-options-page") {
    chrome.runtime.openOptionsPage();
    sendResponse({ ok: true });
    return true;
  }

  return false;
});

async function handleReplicateImage(payload) {
  const settings = await getEffectiveSettings();
  if (!settings.backendBaseUrl) {
    throw new Error("请先在扩展设置页配置后端地址。");
  }

  const extraBody = parseExtraBody(settings.extraBody);
  const requestBody = {
    imageUrl: payload.imageUrl,
    productImageDataUrl: payload.productImageDataUrl,
    productFileName: payload.productFileName || "",
    productSubjectHint: payload.productSubjectHint || "",
    generationPath: payload.generationPath || "",
    userPrompt: payload.userPrompt || "",
    model: settings.model,
    visionModel: settings.visionModel,
    nonApparelPrompt: settings.nonApparelPrompt,
    apparelPortraitPrompt: settings.apparelPortraitPrompt,
    apparelFinalPrompt: settings.apparelFinalPrompt,
    defaultUserPrompt: settings.defaultUserPrompt,
    imageSize: payload.imageSizeOverride || settings.imageSize,
    responseDataPath: settings.responseDataPath,
    extraBody
  };

  const response = await fetch(joinUrl(settings.backendBaseUrl, "/replicate"), {
    method: "POST",
    headers: buildProxyHeaders(settings.proxyToken),
    body: JSON.stringify(requestBody)
  });

  if (!response.ok) {
    const text = await response.text();
    const parsedError = parseBackendErrorPayload(text);
    const message = parsedError.message;
    const debugText = parsedError.imageRequestDebug
      ? `\n\n发给生图模型的输入：\n${JSON.stringify(parsedError.imageRequestDebug, null, 2)}`
      : "";
    const visionDebugText = parsedError.visionDebug
      ? `\n\n识图模型返回摘要：\n${JSON.stringify(parsedError.visionDebug, null, 2)}`
      : "";
    throw new Error(`复刻失败 (${response.status})：${message.slice(0, 400)}${debugText}${visionDebugText}`);
  }

  const data = await response.json();
  if (!data?.imageUrl) {
    throw new Error("后端返回成功，但没有提供生成图片地址。");
  }

  const result = {
    imageUrl: data.imageUrl,
    prompt: data.prompt || "",
    imageRequestDebug: data.imageRequestDebug || null,
    generationPath: data.generationPath || payload.generationPath || "",
    portraitImageUrl: data.portraitImageUrl || "",
    referenceHasFace: Boolean(data.referenceHasFace),
    analysisPrompt: data.analysisPrompt || "",
    productAnalysisPrompt: data.productAnalysisPrompt || "",
    referenceAnalysisPrompt: data.referenceAnalysisPrompt || ""
  };
  await appendGenerationRecord({
    imageUrl: result.imageUrl,
    prompt: result.prompt,
    referenceImageUrl: payload.imageUrl || "",
    productFileName: payload.productFileName || "",
    productSubjectHint: payload.productSubjectHint || "",
    generationPath: result.generationPath,
    userPrompt: payload.userPrompt || "",
    imageSize: payload.imageSizeOverride || settings.imageSize
  });
  return result;
}

async function handleClassifyProduct(payload) {
  const settings = await getEffectiveSettings();
  if (!settings.backendBaseUrl) {
    throw new Error("请先在扩展设置页配置后端地址。");
  }
  if (!payload?.productImageDataUrl) {
    throw new Error("缺少商品图。");
  }

  const response = await fetch(joinUrl(settings.backendBaseUrl, "/classify-product"), {
    method: "POST",
    headers: buildProxyHeaders(settings.proxyToken),
    body: JSON.stringify({
      productImageDataUrl: payload.productImageDataUrl,
      visionModel: settings.visionModel
    })
  });

  if (!response.ok) {
    const text = await response.text();
    const parsedError = parseBackendErrorPayload(text);
    const message = parsedError.message;
    throw new Error(`分类失败 (${response.status})：${message.slice(0, 300)}`);
  }

  const data = await response.json();
  return {
    productKind: data.productKind === "apparel" ? "apparel" : "non_apparel",
    reason: data.reason || ""
  };
}

async function getEffectiveSettings() {
  const storage = await getSavedSettings();
  return normalizeSettings({
    ...DEFAULT_SETTINGS,
    ...storage
  });
}

function buildProxyHeaders(proxyToken) {
  const headers = {
    "Content-Type": "application/json"
  };
  if (proxyToken) {
    headers["X-Proxy-Token-B64"] = encodeBase64Utf8(proxyToken);
  }
  return headers;
}

function joinUrl(baseUrl, path) {
  const normalizedBase = baseUrl.replace(/\/+$/, "");
  return `${normalizedBase}${path}`;
}

function parseExtraBody(raw) {
  if (!raw || !raw.trim()) {
    return {};
  }
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (error) {
    throw new Error("extraBody 不是合法 JSON，请到设置页修正后重试。");
  }
}

function parseBackendErrorPayload(text) {
  if (!text) {
    return { message: "未知错误", imageRequestDebug: null, visionDebug: null };
  }
  try {
    const parsed = JSON.parse(text);
    if (parsed && typeof parsed.error === "string" && parsed.error.trim()) {
      return {
        message: parsed.error.trim(),
        imageRequestDebug: parsed.imageRequestDebug || null,
        visionDebug: parsed.visionDebug || null
      };
    }
  } catch (error) {
    // fall through
  }
  return { message: text, imageRequestDebug: null, visionDebug: null };
}

function encodeBase64Utf8(value) {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}

async function getSavedSettings() {
  const localStorage = await chrome.storage.local.get([SETTINGS_KEY]);
  if (localStorage[SETTINGS_KEY]) {
    return normalizeSettings(localStorage[SETTINGS_KEY]);
  }
  const syncStorage = await chrome.storage.sync.get([SETTINGS_KEY]);
  return normalizeSettings(syncStorage[SETTINGS_KEY] || {});
}

function normalizeSettings(settings) {
  if (!settings || typeof settings !== "object") {
    return {};
  }

  const next = { ...settings };
  if (next.model && LEGACY_MODEL_MAP[next.model]) {
    next.model = LEGACY_MODEL_MAP[next.model];
  }
  if (next.visionModel && LEGACY_MODEL_MAP[next.visionModel]) {
    next.visionModel = LEGACY_MODEL_MAP[next.visionModel];
  }
  return next;
}

async function appendGenerationRecord(record) {
  const records = await getGenerationRecords();
  const entry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
    ...record
  };
  const nextRecords = [entry, ...records].slice(0, MAX_GENERATION_RECORDS);
  await chrome.storage.local.set({ [GENERATION_RECORDS_KEY]: nextRecords });
}

async function getGenerationRecords() {
  const storage = await chrome.storage.local.get([GENERATION_RECORDS_KEY]);
  const records = storage[GENERATION_RECORDS_KEY];
  return Array.isArray(records) ? records : [];
}
