const http = require("node:http");
const { URL } = require("node:url");

const PORT = Number(process.env.PORT || 8787);
const ARK_API_KEY = process.env.ARK_API_KEY || "";
const PROXY_TOKEN = process.env.PROXY_TOKEN || "";

const DEFAULTS = {
  model: "doubao-seedream-4-5-251128",
  visionModel: "doubao-seed-1-6-251015",
  visionSystemPrompt:
    "你是一个专业的图片拆解与复刻提示词助手。你的任务不是评价图片，而是把图片内容还原成适合文生图复刻的中文描述。请重点提取主体、场景、构图、镜头视角、景别、动作姿态、服装妆造、材质纹理、色彩关系、光线、氛围、风格、清晰度、细节密度。输出必须是可直接用于生图的中文 prompt，不要加解释，不要分点，不要说“这张图里”。",
  promptTemplate:
    "请根据下面这段图片内容描述，生成一张高度还原原图气质和视觉效果的新图片。请尽量保留主体、构图、镜头视角、景别、色彩关系、光线氛围、材质细节与整体风格。图片描述：{analysisPrompt}。附加要求：{userPrompt}",
  defaultUserPrompt: "尽量和原图一致，提升清晰度与质感。",
  imageSize: "2K",
  responseDataPath: "data[0].url",
  extraBody: {
    sequential_image_generation: "disabled",
    response_format: "url",
    stream: false,
    watermark: true
  }
};

const server = http.createServer(async (req, res) => {
  try {
    setCorsHeaders(res);

    if (req.method === "OPTIONS") {
      res.writeHead(204);
      res.end();
      return;
    }

    if (req.url === "/health") {
      sendJson(res, 200, { ok: true });
      return;
    }

    if (req.method === "POST" && req.url === "/replicate") {
      authorize(req);
      assertArkKey();

      const body = await readJson(req);
      const result = await replicate(body);
      sendJson(res, 200, result);
      return;
    }

    sendJson(res, 404, { error: "Not found" });
  } catch (error) {
    sendJson(res, error.statusCode || 500, {
      error: error instanceof Error ? error.message : String(error)
    });
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Proxy server listening on http://127.0.0.1:${PORT}`);
});

function authorize(req) {
  if (!PROXY_TOKEN) {
    return;
  }
  const provided = req.headers["x-proxy-token"];
  if (provided !== PROXY_TOKEN) {
    const error = new Error("Proxy token invalid.");
    error.statusCode = 401;
    throw error;
  }
}

function assertArkKey() {
  if (!ARK_API_KEY) {
    const error = new Error("ARK_API_KEY is missing.");
    error.statusCode = 500;
    throw error;
  }
}

async function replicate(body) {
  if (!body?.imageUrl) {
    const error = new Error("imageUrl is required.");
    error.statusCode = 400;
    throw error;
  }

  const merged = {
    model: body.model || DEFAULTS.model,
    visionModel: body.visionModel || DEFAULTS.visionModel,
    visionSystemPrompt: body.visionSystemPrompt || DEFAULTS.visionSystemPrompt,
    promptTemplate: body.promptTemplate || DEFAULTS.promptTemplate,
    defaultUserPrompt: body.defaultUserPrompt || DEFAULTS.defaultUserPrompt,
    imageSize: body.imageSize || DEFAULTS.imageSize,
    responseDataPath: body.responseDataPath || DEFAULTS.responseDataPath,
    extraBody: body.extraBody && typeof body.extraBody === "object" ? body.extraBody : DEFAULTS.extraBody
  };

  const dataUrl = await convertImageUrlToDataUrl(body.imageUrl);
  const analysisPrompt = await analyzeImage(dataUrl, merged);
  const prompt = buildPrompt(
    merged.promptTemplate,
    analysisPrompt,
    merged.defaultUserPrompt
  );
  const imageUrl = await generateImage(prompt, merged);

  return {
    imageUrl,
    analysisPrompt,
    prompt
  };
}

async function analyzeImage(dataUrl, settings) {
  const response = await fetch("https://ark.cn-beijing.volces.com/api/v3/responses", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ARK_API_KEY}`
    },
    body: JSON.stringify({
      model: settings.visionModel,
      instructions: settings.visionSystemPrompt,
      input: [
        {
          role: "user",
          content: [
            {
              type: "input_image",
              image_url: dataUrl
            },
            {
              type: "input_text",
              text:
                "请把这张图片还原成适合文生图复刻的中文 prompt，尽可能保留主体、场景、构图、视角、服装、色彩、光线、氛围、风格和关键细节。"
            }
          ]
        }
      ],
      temperature: 0.2,
      max_output_tokens: 900
    })
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`识图失败 (${response.status})：${text.slice(0, 400)}`);
  }

  const data = await response.json();
  const text = extractResponseText(data);
  if (!text) {
    throw new Error("识图成功，但没有拿到文本描述。");
  }
  return text;
}

async function generateImage(prompt, settings) {
  const response = await fetch("https://ark.cn-beijing.volces.com/api/v3/images/generations", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ARK_API_KEY}`
    },
    body: JSON.stringify({
      model: settings.model,
      prompt,
      size: settings.imageSize,
      ...settings.extraBody
    })
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`生图失败 (${response.status})：${text.slice(0, 400)}`);
  }

  const data = await response.json();
  const value = readByPath(data, settings.responseDataPath);
  if (!value || typeof value !== "string") {
    throw new Error("生图成功，但没有在配置路径上找到图片结果。");
  }
  return value.startsWith("http") ? value : `data:image/png;base64,${value}`;
}

async function convertImageUrlToDataUrl(imageUrl) {
  const response = await fetch(imageUrl);
  if (!response.ok) {
    throw new Error(`下载原图失败 (${response.status})`);
  }
  const arrayBuffer = await response.arrayBuffer();
  const mimeType = response.headers.get("content-type") || "image/png";
  const base64 = Buffer.from(arrayBuffer).toString("base64");
  return `data:${mimeType};base64,${base64}`;
}

function buildPrompt(template, analysisPrompt, userPrompt) {
  return template
    .replaceAll("{analysisPrompt}", analysisPrompt || "")
    .replaceAll("{userPrompt}", userPrompt || "");
}

function extractResponseText(data) {
  if (typeof data?.output_text === "string" && data.output_text.trim()) {
    return data.output_text.trim();
  }

  const output = Array.isArray(data?.output) ? data.output : [];
  for (const item of output) {
    const contents = Array.isArray(item?.content) ? item.content : [];
    for (const content of contents) {
      if (typeof content?.text === "string" && content.text.trim()) {
        return content.text.trim();
      }
    }
  }
  return "";
}

function readByPath(source, path) {
  return path.split(".").reduce((current, segment) => {
    if (current == null) {
      return undefined;
    }
    const match = segment.match(/^([^[\]]+)\[(\d+)\]$/);
    if (match) {
      return current?.[match[1]]?.[Number(match[2])];
    }
    return current?.[segment];
  }, source);
}

function setCorsHeaders(res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, X-Proxy-Token");
  res.setHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
}

function sendJson(res, status, payload) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(payload));
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.setEncoding("utf8");
    req.on("data", (chunk) => {
      raw += chunk;
    });
    req.on("end", () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch (error) {
        reject(new Error("Invalid JSON body."));
      }
    });
    req.on("error", reject);
  });
}
