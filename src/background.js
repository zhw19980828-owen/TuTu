const DEFAULT_SETTINGS = {
  backendBaseUrl: "http://127.0.0.1:8787",
  proxyToken: "",
  model: "openai/gpt-5.4-image-2",
  visionModel: "moonshotai/kimi-k2.6",
  nonApparelPrompt:
    "你是一位真实商品摄影与非服饰商品复刻提示词专家。你会同时看到一张参考图和一张商品图。你的任务是把两张图转成一段最终可以直接交给生图模型的中文 prompt，让生图模型生成一张“用户商品主体正确，但摄影语言和参考图高度一致”的真实拍摄效果图片。参考图只负责提供画面模板，你必须像摄影师复盘机位一样，准确识别并继承参考图里的画幅比例、景别、镜头焦段感、相机高度、俯拍/平拍/仰拍程度、镜头向左或向右的水平偏转、画面近端和远端的位置、透视收缩方向、水平线或盒边/桌边的斜率、主体在画面中的位置和占比、主体朝向、主体长轴方向、主体倾斜角度、主体俯仰角度、主体与承载面的接触点、主体是否平放/斜放/竖立/悬浮/倚靠/嵌入卡槽/半露出/叠放/被托起、多个物体之间的前后层级和遮挡关系、主体边缘与画面边界的距离、裁切方式、场景地点、背景元素、承载面材质、时间段、主光方向、光线质感、色温、曝光方式、色彩氛围、景深关系、主体与背景的光影关系，以及画面中原本存在的真实陈列和生活痕迹。最终 prompt 必须明确写出相机视角：例如低角度贴近桌面、从正前方略偏右看向左后方、从上方约 30 度俯视、镜头沿盒子对角线方向拍摄、近处盒沿在画面底部横向穿过、远处盒盖向右上方退去等；不要只写“微距特写、低角度俯拍”这种笼统词。最终 prompt 还必须用具体方位写清楚新商品的摆放姿势：它位于画面哪个区域，长轴或开口朝向哪里，正面/侧面/顶部露出多少，是否贴着、压在、嵌入、悬在、靠着或插入某个承载物，接触点在哪里，阴影落向哪里；如果参考图中原主体有专用托槽、盒垫、支架、桌面边缘、布面褶皱或局部遮挡，必须让新商品占用同一个空间关系。商品图会直接作为后续生图模型的唯一商品参考图，因此最终 prompt 里不要详细描述商品本身的颜色、材质、品牌、logo、文字、纹理、形状、结构、链节、刻字、装饰、边缘、工艺、尺寸等视觉细节，这些交给图像参考通道。你只能极简点明商品品类和融入方式，例如“一枚戒指嵌在盒垫中央的卡槽里，弧面横向朝向镜头，镜头从盒子前下方略偏右的位置沿盒内对角线看过去”“一个包斜靠在桌面右后方”“一瓶香水竖立在原主体落点”。最终输出必须是一整段中文 prompt，直接描述最终生成图片本身：保留参考图的场景、构图、镜头角度、主体摆放姿态、主体朝向、主体落点、前后层级、光影、景别、主体大小和整体气质，画面必须像真实相机拍摄，不要出现 CGI、3D 渲染、插画、海报合成或过度广告精修感。不要输出解释、标题、分析过程、分点或 JSON。",
  apparelPortraitPrompt:
    "你是一位电商服饰模特设定提示词专家。你会看到一张参考图，这张图只用来生成一张新的模特人像垫图，后续再把用户的服饰商品替换上去。你的任务是只根据参考图输出一整段中文生图 prompt，用于先生成一张与参考图人物气质、性别、年龄感、脸型、发型长度、发色、妆容浓度、视线方向、头部倾斜、身体朝向、动作姿态、镜头角度、景别、主体占比、裁切方式、场景地点、时间段、背景布局、色彩氛围、光影关系都尽量相似的模特人像图片。你必须保留参考图的人像出镜形式和构图骨架，但要让模特穿着尽量简洁、干净、贴身、低干扰的基础内搭或无明显设计感的占位服装，避免外套、复杂印花、大面积文字、夸张配饰和抢主体的服装细节，以便后续服饰替换。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
  apparelFinalPrompt:
    "你是一位真实服饰摄影、穿搭换装与参考图复刻提示词专家。你会看到参考图、可能存在的生成人像垫图、以及用户上传的服饰商品图。你的核心任务是先把小红书参考图转换成具体画面文字，再把用户商品服饰融入这段画面，输出一整段最终成图 prompt。最终 prompt 必须直接描述最终图片本身，像在描述一张已经拍出来的照片，而不是描述任务规则。参考图负责提供完整画面模板，你必须具体写出参考图中真实可见的内容：场景地点、室内/室外环境、背景墙面/镜子/门框/家具/地面/道具、时间段、光线方向和质感、相机或手机拍摄方式、镜面自拍关系、机位高度、俯拍/平拍/仰拍程度、镜头向左或向右的水平偏转、景别、人物在画面中的位置和占比、裁切到哪里、人物坐姿/站姿/蹲姿、双腿和双脚的交叠方向、肩颈和躯干朝向、头部倾斜、手臂和手的位置、手机/包/椅子/凳子等道具与人物的接触关系，以及画面近处和远处的空间层级。商品图负责提供要替换上身或穿戴的服饰主体，最终 prompt 只需要说明商品服饰穿在对应部位，并描述它如何贴合参考图人物姿态、肩带/领口/腰线/裙摆/裤脚/袖口与动作和遮挡关系；商品外观细节以商品图为准，不要编造商品图里没有的设计。严禁输出“需要保留、必须复刻、参考图负责、商品图负责、不要改变、最终 prompt 必须”等任务说明式句子；严禁只写“保留参考图的场景和姿态”这种空话。你应该输出类似“一张真实手机镜前自拍照片，年轻女性坐在更衣室浅色墙面前的矮凳上……”这样的具体画面描述。不要擅自改性别、人数、景别、主体大小、坐站关系、镜面自拍方式或主要道具。画面必须像真实手机或相机拍摄，不要出现 CGI、3D 渲染、插画、海报合成或过度广告精修感。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
  defaultUserPrompt: "",
  imageSize: "2K",
  responseDataPath: "",
  extraBody: "{}"
};
const SETTINGS_KEY = "userSettings";
const GENERATION_RECORDS_KEY = "generationRecords";
const MAX_GENERATION_RECORDS = 120;
const LOCAL_TEST_SETTINGS = {
  backendBaseUrl: "http://127.0.0.1:8787",
  proxyToken: "",
  model: DEFAULT_SETTINGS.model,
  visionModel: DEFAULT_SETTINGS.visionModel,
  nonApparelPrompt: DEFAULT_SETTINGS.nonApparelPrompt,
  apparelFinalPrompt: DEFAULT_SETTINGS.apparelFinalPrompt,
  defaultUserPrompt: DEFAULT_SETTINGS.defaultUserPrompt
};
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
    const optionsUrl = chrome.runtime.getURL("src/options.html");
    chrome.tabs.create({ url: optionsUrl }, () => {
      if (chrome.runtime.lastError) {
        sendResponse({ ok: false, error: chrome.runtime.lastError.message });
        return;
      }
      sendResponse({ ok: true });
    });
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
    timings: Array.isArray(data.timings) ? data.timings : [],
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
    ...storage,
    ...LOCAL_TEST_SETTINGS
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
  const records = (await getGenerationRecords()).map(sanitizeGenerationRecord);
  const entry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
    ...sanitizeGenerationRecord(record)
  };
  const nextRecords = [entry, ...records].slice(0, MAX_GENERATION_RECORDS);
  try {
    await chrome.storage.local.set({ [GENERATION_RECORDS_KEY]: nextRecords });
  } catch (error) {
    await chrome.storage.local.set({ [GENERATION_RECORDS_KEY]: [entry] });
  }
}

async function getGenerationRecords() {
  const storage = await chrome.storage.local.get([GENERATION_RECORDS_KEY]);
  const records = storage[GENERATION_RECORDS_KEY];
  return Array.isArray(records) ? records : [];
}

function sanitizeGenerationRecord(record) {
  if (!record || typeof record !== "object") {
    return {};
  }
  const next = { ...record };
  if (isDataUrl(next.imageUrl)) {
    next.imageUrl = "";
    next.imageStoredInline = true;
  }
  if (isDataUrl(next.referenceImageUrl)) {
    next.referenceImageUrl = "";
  }
  if (typeof next.prompt === "string" && next.prompt.length > 1200) {
    next.prompt = `${next.prompt.slice(0, 1200)}...`;
  }
  return next;
}

function isDataUrl(value) {
  return typeof value === "string" && value.startsWith("data:");
}
