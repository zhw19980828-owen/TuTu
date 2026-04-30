const DEFAULT_SETTINGS = {
  backendBaseUrl: "http://127.0.0.1:8787",
  proxyToken: "",
  model: "doubao-seedream-4-5-251128",
  visionModel: "doubao-seed-1-6-251015",
  nonApparelPrompt:
    "你是一位电商静物与非服饰商品复刻提示词专家。你会看到一张参考图和一张商品图。参考图只负责提供场景模板，你必须准确继承参考图里的拍摄方式、画幅比例、镜头角度、景别、主体占比、场景地点、背景元素、承载面材质、时间段、光线方向、光线质感、色温、曝光、色彩氛围、景深关系、主体与背景的光影关系，以及画面里原本存在的真实生活痕迹。商品图只负责告诉你最终要替换进去的商品主体是什么。因为商品图会在后续生成阶段作为参考图输入，所以你不需要重复描述商品的大面积颜色、基础材质和大轮廓，只需要在容易丢失时补充品牌文字、logo 位置、特殊结构、小面积装饰、异形轮廓、特殊开合方式等高辨识度信息。你的任务是输出一整段最终给生图模型使用的中文 prompt，要求只替换参考图里的主体商品或摆件，不改变参考图的场景骨架、机位、取景范围、主体大小、裁切方式和光影关系，不要擅自添加参考图里没有的新道具，不要输出解释、标题、分点或 JSON。",
  apparelPortraitPrompt:
    "你是一位电商服饰模特设定提示词专家。你会看到一张参考图，这张图只用来生成一张新的模特人像垫图，后续再把用户的服饰商品替换上去。你的任务是只根据参考图输出一整段中文生图 prompt，用于先生成一张与参考图人物气质、性别、年龄感、脸型、发型长度、发色、妆容浓度、视线方向、头部倾斜、身体朝向、动作姿态、镜头角度、景别、主体占比、裁切方式、场景地点、时间段、背景布局、色彩氛围、光影关系都尽量相似的模特人像图片。你必须保留参考图的人像出镜形式和构图骨架，但要让模特穿着尽量简洁、干净、贴身、低干扰的基础内搭或无明显设计感的占位服装，避免外套、复杂印花、大面积文字、夸张配饰和抢主体的服装细节，以便后续服饰替换。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
  apparelFinalPrompt:
    "你是一位电商服饰换装复刻提示词专家。你会看到参考图、生成的人像垫图和用户的商品图。参考图只负责提供场景模板，你必须继承参考图里的时间段、天气、场景地点、背景布局、机位、镜头角度、景别、主体占比、裁切方式、人物姿态、手部位置、视线方向、光影关系和整体营销氛围。生成的人像垫图是最终模特基础，你必须尽量保留它的人脸、发型、体态、肢体关系和取景裁切。商品图只负责提供要替换上身的服饰主体，商品图会在后续生成阶段作为参考图输入，因此你不需要冗长描述基础颜色和大体轮廓，只需要在容易丢失时补充品牌文字、logo、领口结构、袖型、纽扣排布、特殊拼接、不对称设计、特殊面料工艺等关键特征。你的任务是输出一整段最终给生图模型使用的中文 prompt，要求把商品服饰自然穿在模特对应部位，保持参考图的构图骨架和动作，不要擅自改性别、改人数、改景别、改主体大小，也不要把服饰替换成完全不同的穿法。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
  defaultUserPrompt: "输出适合电商投放和商品详情页的高清主视觉，主体明确，商品细节清晰，画面干净高级。",
  imageSize: "2K",
  responseDataPath: "data[0].url",
  extraBody:
    "{\n  \"sequential_image_generation\": \"disabled\",\n  \"response_format\": \"url\",\n  \"stream\": false,\n  \"watermark\": true\n}"
};
const SETTINGS_KEY = "userSettings";
const GENERATION_RECORDS_KEY = "generationRecords";
const MAX_GENERATION_RECORDS = 120;

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
    throw new Error(`复刻失败 (${response.status})：${text.slice(0, 400)}`);
  }

  const data = await response.json();
  if (!data?.imageUrl) {
    throw new Error("后端返回成功，但没有提供生成图片地址。");
  }

  const result = {
    imageUrl: data.imageUrl,
    prompt: data.prompt || "",
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
    throw new Error(`分类失败 (${response.status})：${text.slice(0, 300)}`);
  }

  const data = await response.json();
  return {
    productKind: data.productKind === "apparel" ? "apparel" : "non_apparel",
    reason: data.reason || ""
  };
}

async function getEffectiveSettings() {
  const storage = await getSavedSettings();
  return {
    ...DEFAULT_SETTINGS,
    ...storage
  };
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
    return localStorage[SETTINGS_KEY];
  }
  const syncStorage = await chrome.storage.sync.get([SETTINGS_KEY]);
  return syncStorage[SETTINGS_KEY] || {};
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
