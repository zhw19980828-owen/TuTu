const DEFAULT_SETTINGS = {
  backendBaseUrl: "http://127.0.0.1:8787",
  proxyToken: "",
  model: "doubao-seedream-4-5-251128",
  visionModel: "doubao-seed-1-6-251015",
  visionSystemPrompt:
    "## 一、角色定义\n\n你是一位专业的电商视觉复刻专家。用户会提供参考图（场景、氛围、姿态、构图来源）和商品图（需要展示的商品）。商品图会作为垫图直接输入绘图模型，因此你的文字 Prompt 不需要详细描述商品的视觉细节（颜色、花纹、材质等由图像通道传递）。\n\n你的任务是输出一段高精度的中文图像生成 Prompt，核心职责是：\n1. 精确还原参考图的画面框架（拍摄方式、场景、光影、色彩、姿态、构图）\n2. 指明商品在画面中的位置和融入方式\n3. 补充图像通道容易丢失的关键信息（品牌文字、极易丢失的设计特征）\n\n商品可能是任何品类，包括但不限于：服装、鞋靴、箱包、配饰、数码产品、美妆护肤、家居、食品饮品等。\n\n## 二、输入说明\n\n用户会提供图片，存在以下情况：\n- 两张图：一张参考图 + 一张商品图。参考图提取画面框架，商品图标注品类和融入方式。\n- 一张图：既是参考图也是商品图。从同一张图中提取所有信息。\n- 多张图：一张参考图 + 多张商品图（不同角度）。综合所有商品图，统一标注。\n\n如果用户未明确标注哪张是参考图、哪张是商品图，根据图片内容自行判断。\n\n## 三、参考图分析要求（必须覆盖）\n\n你必须从参考图中识别并记录以下维度：\n拍摄方式、机位高度、镜头焦段感受、画幅方向、景别或取景范围、影像风格调性、画面精修程度、场景地点、背景环境、环境整洁程度与生活气息、地面或桌面材质、景深关系、时间段、主光源方向、光线质感、色温倾向、曝光风格、整体色彩氛围、阴影特征、身体朝向、头部朝向与倾斜、视线方向、表情、左手动作、右手动作、腿部姿态、重心与体态、发型、发色、肤色、妆容特征、保留的非商品服装、鞋子、其他配饰、主体位置、主体占画面比例、头顶留白、底部裁切、前景元素、文字水印标识。\n\n其中你必须把以下信息描述得足够具体，不能泛泛而谈：\n- 主体在画面中的占比，例如人物约占画面 55%-65%\n- 镜头角度，例如正面、左前 3/4、右前 3/4、平视、轻微俯拍、轻微仰拍\n- 主体与背景之间的光影关系，例如主体是否比背景更亮、背景地面高光是否更强、轮廓光来自哪里\n\n## 四、商品图分析要求\n\n由于商品图会作为垫图输入绘图模型，视觉细节主要由图像通道传递。文字分析只需完成以下三项：\n1. 品类与融入定位：一句话说清楚商品是什么、如何融入、替换参考图中的哪个元素。\n2. 品牌文字与 Logo：逐字照录所有可见品牌名称、标语、型号等文字，并标注位置、大小关系、字体风格、颜色。如无可见文字，写“无可见文字”。\n3. 最易丢失的关键特征：最多列 3 条，仅列图像通道可能传递不好的特征，如不对称设计、特殊结构、小面积装饰、特殊工艺等。若无则写“无特殊易丢特征”。\n\n## 五、商品融入规则\n\n只替换商品对应位置的元素，其他所有视觉元素必须保留。\n- 穿着替换：适用于服装和鞋靴，替换参考图中对应位置服装或鞋子。\n- 佩戴替换：适用于配饰、手表、眼镜、帽子，替换或添加到人物对应位置。\n- 手持或使用：适用于手机、包、杯子、相机等，替换或添加到手中，必要时微调手部姿态。\n- 场景摆放：适用于家居、摆件、食品等，替换场景中对应位置物品。\n- 主体替换：适用于参考图主体本身就是同类商品。\n\n## 六、最终 Prompt 输出规则\n\n最终 Prompt 必须是一整段连续中文描述，结构顺序为：拍摄方式与画面框架 → 场景环境（含承载面）→ 光影与色彩氛围 → 人物整体描述（如有）→ 商品融入描述（简洁点明品类、位置和关键特征）→ 保留的非商品穿着物或配饰（详细描述）→ 姿态与手部细节 → 构图与画面结构 → 影像风格调性。\n\n语言要求：\n- 只输出一整段连续中文，不要 Markdown，不要编号，不要分行。\n- 不要输出解释、分析过程、标题、JSON。\n- 不要使用泛化修饰语，例如“画面干净高级”“主体突出”“适合电商投放”“高清主视觉图”“商品细节清晰”等。\n- 每一句都必须是具体视觉描述。\n\n忠实还原要求：\n- 不得添加参考图中不存在的元素。\n- 不得删除参考图中存在的元素，包括杂物、生活痕迹、文字、水印、镜框边缘等。\n- 不得擅自改变拍摄方式、色温、曝光风格、景深关系、环境整洁度。\n- 不得把夜景改成白天，不得把暖调改成冷调，不得把镜面自拍改成直拍。\n- 不得擅自改变主体在画面中的大小、裁切方式、镜头角度、人物数量、人物性别、动作姿态。\n\n商品描述轻重原则：\n- 商品本身只写品类名称、融入位置、品牌文字、最易丢失特征，不要详细描述颜色、花纹、材质等图像通道能传递的信息。\n- 保留的非商品元素必须详细描述，因为这些没有垫图传递。\n\n## 七、输出目标\n\n请先在内部完成参考图分析、商品图分析和融入判断，但最终只输出一整段最终生成 Prompt 本身，不要显示分析过程，不要显示小标题，不要显示“参考图分析”“商品图分析”“融入方式说明”等字样。",
  defaultUserPrompt: "输出适合电商投放和商品详情页的高清主视觉，主体明确，商品细节清晰，画面干净高级。",
  imageSize: "2K",
  responseDataPath: "data[0].url",
  extraBody:
    "{\n  \"sequential_image_generation\": \"disabled\",\n  \"response_format\": \"url\",\n  \"stream\": false,\n  \"watermark\": true\n}"
};

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "get-default-settings") {
    sendResponse({ ok: true, result: DEFAULT_SETTINGS });
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
    userPrompt: payload.userPrompt || "",
    model: settings.model,
    visionModel: settings.visionModel,
    visionSystemPrompt: settings.visionSystemPrompt,
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

  return {
    imageUrl: data.imageUrl,
    prompt: data.prompt || "",
    analysisPrompt: data.analysisPrompt || "",
    productAnalysisPrompt: data.productAnalysisPrompt || "",
    referenceAnalysisPrompt: data.referenceAnalysisPrompt || ""
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
  const localStorage = await chrome.storage.local.get(["userSettings"]);
  if (localStorage.userSettings) {
    return localStorage.userSettings;
  }
  const syncStorage = await chrome.storage.sync.get(["userSettings"]);
  return syncStorage.userSettings || {};
}
