const DEFAULT_SETTINGS = {
  backendBaseUrl: "http://127.0.0.1:8787",
  proxyToken: "",
  model: "dreamina/image2image:5.0Pro",
  visionModel: "kimi-k2.6",
  nonApparelPrompt:
    "你是一位真实商品摄影与非服饰商品复刻提示词专家。你会同时看到一张参考图和一张商品图。你的任务是把两张图转成一段最终可以直接交给生图模型的中文 prompt，让生图模型生成一张“用户商品主体正确，但摄影语言和参考图高度一致”的真实拍摄效果图片。参考图只负责提供画面模板，你必须像摄影师复盘机位一样，准确识别并继承参考图里的画幅比例、景别、镜头焦段感、相机高度、俯拍/平拍/仰拍程度、镜头向左或向右的水平偏转、画面近端和远端的位置、透视收缩方向、水平线或盒边/桌边的斜率、主体在画面中的位置和占比、主体朝向、主体长轴方向、主体倾斜角度、主体俯仰角度、主体与承载面的接触点、主体是否平放/斜放/竖立/悬浮/倚靠/嵌入卡槽/半露出/叠放/被托起、多个物体之间的前后层级和遮挡关系、主体边缘与画面边界的距离、裁切方式、场景地点、背景元素、承载面材质、时间段、主光方向、光线质感、色温、曝光方式、色彩氛围、景深关系、主体与背景的光影关系，以及画面中原本存在的真实陈列和生活痕迹。最终 prompt 必须明确写出相机视角：例如低角度贴近桌面、从正前方略偏右看向左后方、从上方约 30 度俯视、镜头沿盒子对角线方向拍摄、近处盒沿在画面底部横向穿过、远处盒盖向右上方退去等；不要只写“微距特写、低角度俯拍”这种笼统词。最终 prompt 还必须用具体方位写清楚新商品的摆放姿势：它位于画面哪个区域，长轴或开口朝向哪里，正面/侧面/顶部露出多少，是否贴着、压在、嵌入、悬在、靠着或插入某个承载物，接触点在哪里，阴影落向哪里；如果参考图中原主体有专用托槽、盒垫、支架、桌面边缘、布面褶皱或局部遮挡，必须让新商品占用同一个空间关系。商品图会直接作为后续生图模型的唯一商品参考图，因此最终 prompt 里不要详细描述商品本身的颜色、材质、品牌、logo、文字、纹理、形状、结构、链节、刻字、装饰、边缘、工艺、尺寸等视觉细节，这些交给图像参考通道。你只能极简点明商品品类和融入方式，例如“一枚戒指嵌在盒垫中央的卡槽里，弧面横向朝向镜头，镜头从盒子前下方略偏右的位置沿盒内对角线看过去”“一个包斜靠在桌面右后方”“一瓶香水竖立在原主体落点”。最终输出必须是一整段中文 prompt，直接描述最终生成图片本身：保留参考图的场景、构图、镜头角度、主体摆放姿态、主体朝向、主体落点、前后层级、光影、景别、主体大小和整体气质，画面必须像真实相机拍摄，不要出现 CGI、3D 渲染、插画、海报合成或过度广告精修感。不要输出解释、标题、分析过程、分点或 JSON。",
  apparelFinalPrompt:
    "你是一位真实服饰摄影、穿搭换装与参考图复刻提示词专家。你会看到小红书参考图和用户上传的服饰商品图。你的核心任务是先把小红书参考图转换成具体画面文字，再把用户商品服饰融入这段画面，输出一整段最终成图 prompt。最终 prompt 必须直接描述最终图片本身，像在描述一张已经拍出来的照片，而不是描述任务规则。参考图负责提供完整画面模板和人物模板，你必须具体写出参考图中真实可见的内容：人物形象气质、发型、脸部可见状态、视线、头部倾斜、身体朝向、动作姿态、手臂和手的位置、场景地点、室内/室外环境、背景墙面/镜子/门框/家具/地面/道具、时间段、光线方向和质感、相机或手机拍摄方式、镜面自拍关系、机位高度、俯拍/平拍/仰拍程度、镜头向左或向右的水平偏转、景别、人物在画面中的位置和占比、人物主要位于画面上部/中部/下部还是贯穿全画面、人物头顶/脚底/左右身体边缘距离画面边界的大致比例、人物高度占画面高度的大致比例、画面上下左右留白和主要背景区域的大致比例、画面四边分别裁到人物/服饰/道具哪里、哪些身体部位和服饰部件完整可见/局部可见/完全不可见、人物坐姿/站姿/蹲姿、可见四肢和双脚的方向、肩颈和躯干朝向、手机/包/椅子/凳子等道具与人物的接触关系，以及画面近处和远处的空间层级。最终 prompt 必须保持参考图的人物形象方向、姿势、手势、垂直位置、主体大小、上下留白、左右留白、边界距离和可见范围，不要为了突出服装而自动放大人物、缩小人物、居中人物、移动镜头、扩展画幅、补全身体、补全道具或改变画面重心。无论参考图是不展示脚、不展示腿、不展示下半身、不展示躯干、不展示头部、只露出局部身体、只露出局部商品还是裁掉某个道具，最终 prompt 都必须写成同样的局部可见范围；参考图中完全不可见的身体部位、服饰部件、配饰、道具和背景区域不能出现在最终 prompt 中。商品图只负责提供要替换上身或穿戴的服饰主体本身，最终 prompt 只需要说明商品服饰穿在参考图人物对应部位，并描述它如何贴合参考图人物姿态、肩带/领口/腰线/裙摆/裤脚/袖口与动作和遮挡关系；商品外观细节以商品图为准，不要编造商品图里没有的设计。参考图里人物原本穿着的衣服、鞋帽、包袋和配饰不是本次商品，不能保留或复述参考图原服饰的颜色、图案、数字、logo、文字、玩偶、装饰、面料和款式；参考图原服饰只用于判断身体遮挡、衣物边缘落点、可见范围和裁切位置，最终可见服饰外观必须来自商品图。如果商品图中也出现真人、模特、手臂、脸、身体、发型、妆容、背景、道具或强动作，它们都不是人物模板和画面模板，不能写进最终 prompt，也不能覆盖参考图的人物形象、脸、发型、体态、人物姿势、手部位置、身体朝向、场景、拍摄角度、构图和可见范围；只能从商品图提取服饰本身的款式、廓形、颜色、图案、材质、开合、肩带、领口、袖长、下摆、裤脚、鞋型或帽型等穿着外观。严禁输出“需要保留、必须复刻、参考图负责、商品图负责、不要改变、最终 prompt 必须”等任务说明式句子；严禁只写“保留参考图的场景和姿态”这种空话。你应该输出类似“一张真实手机镜前自拍照片，一名与参考图性别呈现一致的成年人物坐在更衣室浅色墙面前的矮凳上……”这样的具体画面描述。不要擅自改性别、人数、景别、主体大小、坐站关系、镜面自拍方式、人物在画面中的垂直位置、上下留白比例、可见范围或主要道具。画面必须像真实手机或相机拍摄，不要出现 CGI、3D 渲染、插画、海报合成或过度广告精修感。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
  defaultUserPrompt: "",
  imageResolution: "1k",
  imageAspectRatio: "follow",
  responseDataPath: "",
  extraBody: "{}"
};
DEFAULT_SETTINGS.apparelFinalPrompt +=
  "补充硬规则：第二张商品图里只有用户真正要替换到人物身上的服饰主体可以进入最终 prompt。如果用户填写了商品主体说明，必须以该说明锁定单品；如果没有说明，则只选第二张图中最主要、最居中、最像商品展示主体的一件服饰单品。如果第二张商品图是穿搭拆解图、拼贴图、红框标注图或带品牌标注的搭配图，必须优先识别红框/连线/局部放大框所指向的服饰商品，尤其是画面中心人物身上被重点标注的上衣、外套、裤装、裙装或鞋帽；这些标注框和品牌文字本身不能进入最终 prompt。最终 prompt 中人物身上的服饰外观必须来自这个被锁定的商品主体，不能回退保留第一张参考图人物原本穿着的上衣、裤子、裙子、外套、鞋帽、包袋或配饰外观。输出前必须自检：如果最终 prompt 里仍出现第一张参考图原服饰的颜色、图案、文字、logo、材质或款式，而这些不是第二张商品主体，就必须删除并改写为第二张商品主体的外观。第二张商品图中的背景、拍摄场景、墙面、商场、街道、文字标识、模特脸、发型、手势、身体比例、鞋帽、包袋、首饰、腰带、袜子、裤子、裙子、外套或其他搭配件默认全部是干扰，除非它们就是用户指定的商品主体。不能把第二张商品图里的整套穿搭照搬进最终 prompt；只能提取被锁定单品的款式、廓形、颜色、面料、领口、袖口、下摆、开合、图案等必要外观。第一张小红书参考图里的帽子、包袋、鞋子、首饰、腰间外套等穿戴配饰通常也不是本次商品，只用于判断遮挡、动作、边缘落点和裁切范围，不能作为最终外观保留；如果第一张参考图中的手正在拿包、帽子、鞋、饰品等穿戴配饰，最终 prompt 只能保留手臂位置、手型和遮挡关系，不能继续写出那个包、帽子、鞋或饰品本身，除非它就是用户指定商品；只有手机、椅子、桌子、镜子、墙面、地面、门框、栏杆等构成场景或动作关系的非穿戴道具可以按参考图保留。如果第一张参考图是多宫格、拼图或对比图，最终 prompt 应明确描述它是一张同样布局的拼图，并分别复刻各分图的构图、姿势和裁切；不要把多个分图混成单张照片。";
DEFAULT_SETTINGS.apparelFinalPrompt +=
  "人物性别呈现只能由小红书参考图决定，商品图及商品图模特不得改变人物性别。参考图明确为男性时，最终 prompt 必须明确写男性人物并禁止生成女性人物或女性身体轮廓；参考图明确为女性时，最终 prompt 必须明确写女性人物。无法从参考图确认时才不得猜测。";
const SETTINGS_KEY = "userSettings";
const GENERATION_RECORDS_KEY = "generationRecords";
const MAX_GENERATION_RECORDS = 120;
let generationRecordWriteQueue = Promise.resolve();
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
  "dreamina/image2image:5.0": DEFAULT_SETTINGS.model,
  "doubao-seed-1-6-251015": DEFAULT_SETTINGS.visionModel,
  "moonshotai/kimi-k2.6": DEFAULT_SETTINGS.visionModel
};

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "get-default-settings") {
    sendResponse({ ok: true, result: DEFAULT_SETTINGS });
    return true;
  }

  if (message?.type === "get-effective-settings") {
    getEffectiveSettings()
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) =>
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : String(error)
        })
      );
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

  if (message?.type === "save-generation-record") {
    appendGenerationRecord(message.payload || {})
      .then(() => sendResponse({ ok: true }))
      .catch((error) =>
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : String(error)
        })
      );
    return true;
  }

  if (message?.type === "retry-generation-record") {
    retryGenerationRecord(message.payload?.id)
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
    chrome.runtime.openOptionsPage(() => {
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

  const imageSize = resolveConfiguredAspectRatio(
    settings.imageAspectRatio,
    payload.referenceAspectRatio
  );
  const extraBody = buildGenerationExtraBody(settings);
  const requestBody = {
    imageUrl: payload.imageUrl,
    productImageDataUrls: Array.isArray(payload.productImageDataUrls)
      ? payload.productImageDataUrls
      : [],
    productImageDataUrl: payload.productImageDataUrl,
    productFileNames: Array.isArray(payload.productFileNames) ? payload.productFileNames : [],
    productFileName: payload.productFileName || "",
    productSubjectHint: payload.productSubjectHint || "",
    generationPath: payload.generationPath || "",
    faceIdentityMode: payload.faceIdentityMode === "preserve_reference" ? "preserve_reference" : "regenerate",
    userPrompt: payload.userPrompt || "",
    model: payload.imageModelOverride || settings.model,
    visionModel: settings.visionModel,
    nonApparelPrompt: settings.nonApparelPrompt,
    apparelFinalPrompt: settings.apparelFinalPrompt,
    defaultUserPrompt: settings.defaultUserPrompt,
    imageSize,
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
    faceIdentityMode: payload.faceIdentityMode === "preserve_reference" ? "preserve_reference" : "regenerate",
    referenceHasFace: Boolean(data.referenceHasFace),
    analysisPrompt: data.analysisPrompt || "",
    productAnalysisPrompt: data.productAnalysisPrompt || "",
    referenceAnalysisPrompt: data.referenceAnalysisPrompt || ""
  };
  await appendGenerationRecord({
    id: payload.recordId || undefined,
    status: payload.recordId ? "done" : undefined,
    stageLabel: payload.recordId ? "生成完成" : undefined,
    error: payload.recordId ? "" : undefined,
    imageUrl: result.imageUrl,
    prompt: result.prompt,
    referenceImageUrl: payload.imageUrl || "",
    productFileName: payload.productFileName || "",
    productSubjectHint: payload.productSubjectHint || "",
    generationPath: result.generationPath,
    faceIdentityMode: result.faceIdentityMode,
    userPrompt: payload.userPrompt || "",
    imageSize,
    imageResolution: normalizeImageResolution(settings.imageResolution)
  });
  return result;
}

async function retryGenerationRecord(recordId) {
  const id = String(recordId || "").trim();
  const records = await getGenerationRecords();
  const record = records.find((item) => String(item?.id || "") === id);
  if (!record?.referenceImageUrl || !record?.productImageDataUrl) {
    throw new Error("当前记录缺少重试素材，请回到原页面重新发起。");
  }

  await appendGenerationRecord({
    id,
    status: "running",
    stageLabel: "正在重新生成",
    error: "",
    imageUrl: "",
    resultImageDataUrl: ""
  });

  try {
    return await handleReplicateImage({
      recordId: id,
      imageUrl: record.referenceImageUrl,
      productImageDataUrl: record.productImageDataUrl,
      productFileName: record.productFileName || "",
      productSubjectHint: record.productSubjectHint || "",
      generationPath: record.generationPath || "apparel",
      faceIdentityMode: record.faceIdentityMode || "regenerate",
      userPrompt: record.userPrompt || "",
      referenceAspectRatio: record.imageSize || "1:1",
      imageModelOverride: record.imageModel || "",
      progressId: `retry-${id}-${Date.now()}`
    });
  } catch (error) {
    await appendGenerationRecord({
      id,
      status: "error",
      stageLabel: "生成失败",
      error: error instanceof Error ? error.message : String(error)
    });
    throw error;
  }
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
  if (configured !== "follow" && isSupportedAspectRatio(configured)) {
    return configured;
  }
  const reference = String(referenceValue || "").trim().toLowerCase();
  return isSupportedAspectRatio(reference) ? reference : "1:1";
}

function isSupportedAspectRatio(value) {
  return /^(21:9|16:9|3:2|4:3|1:1|3:4|2:3|9:16)$/.test(value);
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
  const legacyImageSize = String(next.imageSize || "").trim().toLowerCase();
  if (!next.imageResolution) {
    next.imageResolution = "1k";
  }
  if (!next.imageAspectRatio) {
    next.imageAspectRatio = isSupportedAspectRatio(legacyImageSize) ? legacyImageSize : "follow";
  }
  return next;
}

function appendGenerationRecord(record) {
  const operation = generationRecordWriteQueue.then(() => writeGenerationRecord(record));
  generationRecordWriteQueue = operation.catch(() => {});
  return operation;
}

async function writeGenerationRecord(record) {
  const records = (await getGenerationRecords()).map(sanitizeGenerationRecord);
  const incoming = sanitizeGenerationRecord(record);
  const recordId = String(incoming.id || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  const existing = records.find((item) => item.id === recordId) || null;
  const entry = {
    ...(existing || {}),
    ...incoming,
    id: recordId,
    createdAt: existing?.createdAt || incoming.createdAt || new Date().toISOString()
  };
  const nextRecords = [entry, ...records.filter((item) => item.id !== recordId)]
    .sort((left, right) => getGenerationRecordTimestamp(right) - getGenerationRecordTimestamp(left))
    .slice(0, MAX_GENERATION_RECORDS);
  try {
    await chrome.storage.local.set({ [GENERATION_RECORDS_KEY]: nextRecords });
  } catch (error) {
    try {
      await chrome.storage.local.set({ [GENERATION_RECORDS_KEY]: [entry] });
    } catch (entryError) {
      const compactEntry = { ...entry, productImageDataUrl: "", resultImageDataUrl: "" };
      await chrome.storage.local.set({ [GENERATION_RECORDS_KEY]: [compactEntry] });
    }
  }
}

function getGenerationRecordTimestamp(record) {
  const value = record?.createdAt;
  const timestamp = typeof value === "number" ? value : Date.parse(value || "");
  return Number.isFinite(timestamp) ? timestamp : 0;
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
  if (typeof next.resultImageDataUrl === "string" && next.resultImageDataUrl.length > 520000) {
    next.resultImageDataUrl = "";
  }
  if (isDataUrl(next.referenceImageUrl)) {
    next.referenceImageUrl = "";
  }
  if (typeof next.productImageDataUrl === "string" && next.productImageDataUrl.length > 280000) {
    next.productImageDataUrl = "";
    next.productImageStoredInline = false;
  }
  if (typeof next.prompt === "string" && next.prompt.length > 1200) {
    next.prompt = `${next.prompt.slice(0, 1200)}...`;
  }
  return next;
}

function isDataUrl(value) {
  return typeof value === "string" && value.startsWith("data:");
}
