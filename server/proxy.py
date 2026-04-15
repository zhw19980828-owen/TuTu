# -*- coding: utf-8 -*-

import base64
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PORT = int(os.environ.get("PORT", "8787"))
ARK_API_KEY = os.environ.get("ARK_API_KEY", "")
PROXY_TOKEN = os.environ.get("PROXY_TOKEN", "")

DEFAULTS = {
    "model": "doubao-seedream-4-5-251128",
    "visionModel": "doubao-seed-1-6-251015",
    "visionSystemPrompt": "## 一、角色定义\n\n你是一位专业的电商视觉复刻专家。用户会提供参考图（场景、氛围、姿态、构图来源）和商品图（需要展示的商品）。商品图会作为垫图直接输入绘图模型，因此你的文字 Prompt 不需要详细描述商品的视觉细节（颜色、花纹、材质等由图像通道传递）。\n\n你的任务是输出一段高精度的中文图像生成 Prompt，核心职责是：\n1. 精确还原参考图的画面框架（拍摄方式、场景、光影、色彩、姿态、构图）\n2. 指明商品在画面中的位置和融入方式\n3. 补充图像通道容易丢失的关键信息（品牌文字、极易丢失的设计特征）\n\n商品可能是任何品类，包括但不限于：服装、鞋靴、箱包、配饰、数码产品、美妆护肤、家居、食品饮品等。\n\n## 二、输入说明\n\n用户会提供图片，存在以下情况：\n- 两张图：一张参考图 + 一张商品图。参考图提取画面框架，商品图标注品类和融入方式。\n- 一张图：既是参考图也是商品图。从同一张图中提取所有信息。\n- 多张图：一张参考图 + 多张商品图（不同角度）。综合所有商品图，统一标注。\n\n如果用户未明确标注哪张是参考图、哪张是商品图，根据图片内容自行判断。\n\n## 三、参考图分析要求（必须覆盖）\n\n你必须从参考图中识别并记录以下维度：\n拍摄方式、机位高度、镜头焦段感受、画幅方向、景别或取景范围、影像风格调性、画面精修程度、场景地点、背景环境、环境整洁程度与生活气息、地面或桌面材质、景深关系、时间段、主光源方向、光线质感、色温倾向、曝光风格、整体色彩氛围、阴影特征、身体朝向、头部朝向与倾斜、视线方向、表情、左手动作、右手动作、腿部姿态、重心与体态、发型、发色、肤色、妆容特征、保留的非商品服装、鞋子、其他配饰、主体位置、主体占画面比例、头顶留白、底部裁切、前景元素、文字水印标识。\n\n其中你必须把以下信息描述得足够具体，不能泛泛而谈：\n- 主体在画面中的占比，例如人物约占画面 55%-65%\n- 镜头角度，例如正面、左前 3/4、右前 3/4、平视、轻微俯拍、轻微仰拍\n- 主体与背景之间的光影关系，例如主体是否比背景更亮、背景地面高光是否更强、轮廓光来自哪里\n\n## 四、商品图分析要求\n\n由于商品图会作为垫图输入绘图模型，视觉细节主要由图像通道传递。文字分析只需完成以下三项：\n1. 品类与融入定位：一句话说清楚商品是什么、如何融入、替换参考图中的哪个元素。\n2. 品牌文字与 Logo：逐字照录所有可见品牌名称、标语、型号等文字，并标注位置、大小关系、字体风格、颜色。如无可见文字，写“无可见文字”。\n3. 最易丢失的关键特征：最多列 3 条，仅列图像通道可能传递不好的特征，如不对称设计、特殊结构、小面积装饰、特殊工艺等。若无则写“无特殊易丢特征”。\n\n## 五、商品融入规则\n\n只替换商品对应位置的元素，其他所有视觉元素必须保留。\n- 穿着替换：适用于服装和鞋靴，替换参考图中对应位置服装或鞋子。\n- 佩戴替换：适用于配饰、手表、眼镜、帽子，替换或添加到人物对应位置。\n- 手持或使用：适用于手机、包、杯子、相机等，替换或添加到手中，必要时微调手部姿态。\n- 场景摆放：适用于家居、摆件、食品等，替换场景中对应位置物品。\n- 主体替换：适用于参考图主体本身就是同类商品。\n\n## 六、最终 Prompt 输出规则\n\n最终 Prompt 必须是一整段连续中文描述，结构顺序为：拍摄方式与画面框架 → 场景环境（含承载面）→ 光影与色彩氛围 → 人物整体描述（如有）→ 商品融入描述（简洁点明品类、位置和关键特征）→ 保留的非商品穿着物或配饰（详细描述）→ 姿态与手部细节 → 构图与画面结构 → 影像风格调性。\n\n语言要求：\n- 只输出一整段连续中文，不要 Markdown，不要编号，不要分行。\n- 不要输出解释、分析过程、标题、JSON。\n- 不要使用泛化修饰语，例如“画面干净高级”“主体突出”“适合电商投放”“高清主视觉图”“商品细节清晰”等。\n- 每一句都必须是具体视觉描述。\n\n忠实还原要求：\n- 不得添加参考图中不存在的元素。\n- 不得删除参考图中存在的元素，包括杂物、生活痕迹、文字、水印、镜框边缘等。\n- 不得擅自改变拍摄方式、色温、曝光风格、景深关系、环境整洁度。\n- 不得把夜景改成白天，不得把暖调改成冷调，不得把镜面自拍改成直拍。\n- 不得擅自改变主体在画面中的大小、裁切方式、镜头角度、人物数量、人物性别、动作姿态。\n\n商品描述轻重原则：\n- 商品本身只写品类名称、融入位置、品牌文字、最易丢失特征，不要详细描述颜色、花纹、材质等图像通道能传递的信息。\n- 保留的非商品元素必须详细描述，因为这些没有垫图传递。\n\n## 七、输出目标\n\n请先在内部完成参考图分析、商品图分析和融入判断，但最终只输出一整段最终生成 Prompt 本身，不要显示分析过程，不要显示小标题，不要显示“参考图分析”“商品图分析”“融入方式说明”等字样。",
    "promptTemplate": "你现在要生成一张电商营销图，并且必须高度遵循参考图的视觉骨架。用户上传的商品图既是商品信息来源，也是主体一致性的强参考输入，生成时必须尽量保持商品图中的款式、材质、颜色、图案、结构、轮廓和关键细节一致。必须优先保留参考图里的时间段、场景地点、背景环境、明暗关系、色彩氛围、画幅比例、镜头远近、镜头角度、机位角度、景别、主体在画面中的精确占比、人物是否出镜、人物数量、人物呈现性别、年龄感、发型长度、动作姿态、手部位置、视线方向、裁切方式和大致构图，只把原图中的展示主体替换成用户上传的商品。必须尽量保持和参考图一致的纵横比例、取景范围和主体大小，不要擅自把主体拍得更近或更远，不要把半身改成特写，也不要把原本占比较小的主体放大成满屏。输出时请把主体占比描述得更细，例如人物约占画面 55%-65%、头顶留白多少、肩部和腰部裁切在哪里；请把镜头角度描述得更细，例如平视、轻微俯拍、轻微仰拍、正面、左前 3/4 侧、右前 3/4 侧。若参考图中是单个女性模特，就继续保持单个女性模特；若是单个男性模特，就继续保持单个男性模特；不要擅自改性别、改人数、改出镜方式。若商品属于服饰类，必须把商品穿在模特对应部位，尽量保持原姿态、原机位、原裁切和原氛围，只替换衣服本身；若参考图是静物特写，就继续保留静物特写和布景逻辑。商品必须成为视觉中心，并忠实体现商品图里的款式、材质、颜色、轮廓和关键细节。不要擅自改成白天或晴天，不要擅自改变动作和机位，不要替换成完全不同的背景。附加要求：{userPrompt}",
    "defaultUserPrompt": "输出适合电商投放和商品详情页的高清主视觉，主体明确，商品细节清晰，画面干净高级。",
    "imageSize": "2K",
    "responseDataPath": "data[0].url",
    "extraBody": {
        "sequential_image_generation": "disabled",
        "response_format": "url",
        "stream": False,
        "watermark": True,
    },
}


class ProxyHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"ok": True})
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        try:
            if self.path != "/replicate":
                self._send_json(404, {"error": "Not found"})
                return

            self._authorize()
            self._assert_ark_key()
            body = self._read_json_body()
            result = replicate(body)
            self._send_json(200, result)
        except Exception as error:
            status = getattr(error, "status_code", 500)
            self._send_json(status, {"error": str(error)})

    def log_message(self, format, *args):
        return

    def _authorize(self):
        if not PROXY_TOKEN:
            return
        provided = self.headers.get("X-Proxy-Token-B64", "")
        decoded = decode_proxy_token(provided)
        if decoded != PROXY_TOKEN:
            error = Exception("Proxy token invalid.")
            error.status_code = 401
            raise error

    def _assert_ark_key(self):
        if not ARK_API_KEY:
            error = Exception("ARK_API_KEY is missing.")
            error.status_code = 500
            raise error

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            return json.loads(raw or "{}")
        except json.JSONDecodeError:
            error = Exception("Invalid JSON body.")
            error.status_code = 400
            raise error

    def _send_json(self, status_code, payload):
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Proxy-Token-B64")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")


def replicate(body):
    image_url = body.get("imageUrl", "")
    product_image_data_url = body.get("productImageDataUrl", "")
    product_subject_hint = body.get("productSubjectHint", "")
    if not image_url:
        error = Exception("imageUrl is required.")
        error.status_code = 400
        raise error
    if not product_image_data_url:
        error = Exception("productImageDataUrl is required.")
        error.status_code = 400
        raise error

    settings = {
        "model": body.get("model") or DEFAULTS["model"],
        "visionModel": body.get("visionModel") or DEFAULTS["visionModel"],
        "visionSystemPrompt": body.get("visionSystemPrompt")
        or DEFAULTS["visionSystemPrompt"],
        "promptTemplate": body.get("promptTemplate") or DEFAULTS["promptTemplate"],
        "defaultUserPrompt": body.get("defaultUserPrompt")
        or DEFAULTS["defaultUserPrompt"],
        "imageSize": body.get("imageSize") or DEFAULTS["imageSize"],
        "responseDataPath": body.get("responseDataPath")
        or DEFAULTS["responseDataPath"],
        "extraBody": body.get("extraBody")
        if isinstance(body.get("extraBody"), dict)
        else DEFAULTS["extraBody"],
        "userPrompt": body.get("userPrompt") or DEFAULTS["defaultUserPrompt"],
        "productSubjectHint": product_subject_hint.strip(),
        "productReferenceImage": product_image_data_url,
    }

    reference_data_url = convert_image_url_to_data_url(image_url)
    product_data_url = normalize_data_url(product_image_data_url)
    prompt = compose_final_prompt(reference_data_url, product_data_url, settings)
    result_image_url = generate_image(prompt, settings)

    return {
        "imageUrl": result_image_url,
        "referenceAnalysisPrompt": "",
        "productAnalysisPrompt": "",
        "analysisPrompt": "",
        "prompt": prompt,
    }


def compose_final_prompt(reference_data_url, product_data_url, settings):
    subject_hint = settings.get("productSubjectHint", "")
    hint_text = (
        f"用户补充说明商品主体是：{subject_hint}。请在识别商品主体时优先参考这条说明。"
        if subject_hint
        else "如果商品图里有干扰元素，请自行判断真正商品主体。"
    )

    user_prompt = settings.get("userPrompt", "").strip() or DEFAULTS["defaultUserPrompt"]
    payload = {
        "model": settings["visionModel"],
        "instructions": settings["visionSystemPrompt"],
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": reference_data_url},
                    {"type": "input_image", "image_url": product_data_url},
                    {
                        "type": "input_text",
                        "text": (
                            "第一张图是参考图，只负责提供场景、时间、背景、构图、机位、动作、主体占比、光影关系和整体氛围；"
                            "第二张图是用户上传的商品图，既负责告诉你商品主体是什么，也会在后续生成阶段作为主体一致性的强参考输入。"
                            "你的任务不是分开分析，而是直接输出一段最终可用于生图模型的中文 prompt。"
                            "这段 prompt 必须尽量保持参考图的时间段、场景地点、背景环境、光影关系、画幅比例、镜头远近、机位角度、景别、主体在画面中的占比、人物是否出镜、人物数量、人物呈现性别、动作姿态、手部位置、视线方向、裁切方式和大致构图；"
                            "同时把原图主体替换成商品图对应的商品，并忠实保留商品图里的款式、材质、颜色、图案、结构、轮廓和关键细节。"
                            "如果参考图是人物场景且商品属于服饰类，必须保持类似的人物出镜形式和动作，把商品穿在对应部位；"
                            "如果参考图是静物特写，就保留静物布景逻辑，只替换主体商品。"
                            "不要输出解释，不要分点，不要加标题，只输出一整段最终 prompt。"
                            f"{hint_text}"
                            f"用户额外补充要求：{user_prompt}"
                        ),
                    },
                ],
            }
        ],
        "temperature": 0.2,
        "max_output_tokens": 1200,
    }
    data = post_json("https://ark.cn-beijing.volces.com/api/v3/responses", payload)
    output_text = extract_response_text(data)
    if not output_text:
        return build_single_pass_fallback(subject_hint, user_prompt)
    return output_text


def generate_image(prompt, settings):
    payload = {
        "model": settings["model"],
        "prompt": prompt,
        "size": settings["imageSize"],
        "image": settings["productReferenceImage"],
        **settings["extraBody"],
    }
    data = post_json("https://ark.cn-beijing.volces.com/api/v3/images/generations", payload)
    value = read_by_path(data, settings["responseDataPath"])
    if not isinstance(value, str) or not value:
        raise Exception("生图成功，但没有在配置路径上找到图片结果。")
    if value.startswith("http"):
        return value
    return f"data:image/png;base64,{value}"


def convert_image_url_to_data_url(image_url):
    request = Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request) as response:
            content_type = response.headers.get("Content-Type", "image/png")
            raw = response.read()
    except HTTPError as error:
        raise Exception(f"下载原图失败 ({error.code})")
    except URLError as error:
        raise Exception(f"下载原图失败: {error.reason}")

    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def post_json(url, payload):
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ARK_API_KEY}",
        },
        method="POST",
    )
    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        text = error.read().decode("utf-8", errors="ignore")
        raise Exception(f"Ark 请求失败 ({error.code})：{text[:400]}")
    except URLError as error:
        raise Exception(f"Ark 请求失败: {error.reason}")

def extract_response_text(data):
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"].strip()

    for item in data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return ""


def decode_proxy_token(value):
    if not value:
        return ""
    try:
        raw = base64.b64decode(value.encode("ascii"))
        return raw.decode("utf-8")
    except Exception:
        return ""


def read_by_path(source, path):
    current = source
    for segment in path.split("."):
        if current is None:
            return None
        if "[" in segment and segment.endswith("]"):
            key, index = segment[:-1].split("[", 1)
            current = current.get(key, [])
            try:
                current = current[int(index)]
            except (ValueError, IndexError, TypeError):
                return None
        else:
            if not isinstance(current, dict):
                return None
            current = current.get(segment)
    return current


def normalize_data_url(value):
    if not isinstance(value, str) or not value.startswith("data:"):
        raise Exception("商品图片格式不正确，请重新上传。")
    return value

def build_single_pass_fallback(subject_hint, user_prompt):
    subject_text = f"商品主体是{subject_hint}。" if subject_hint else "商品主体以商品图为准。"
    return (
        "保留参考图的时间段、场景地点、背景环境、光影关系、构图、机位、动作姿态、"
        "画幅比例与主体占比，只替换展示主体为用户上传的商品。"
        f"{subject_text}"
        "生成时忠实保留商品图里的款式、材质、颜色、结构和关键细节。"
        f"附加要求：{user_prompt}"
    )


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ProxyHandler)
    print(f"Proxy server listening on http://127.0.0.1:{PORT}")
    server.serve_forever()
