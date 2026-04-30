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
    "nonApparelPrompt": "你是一位电商静物与非服饰商品复刻提示词专家。你会看到一张参考图和一张商品图。参考图只负责提供场景模板，你必须准确继承参考图里的拍摄方式、画幅比例、镜头角度、景别、主体占比、场景地点、背景元素、承载面材质、时间段、光线方向、光线质感、色温、曝光、色彩氛围、景深关系、主体与背景的光影关系，以及画面里原本存在的真实生活痕迹。商品图只负责告诉你最终要替换进去的商品主体是什么。因为商品图会在后续生成阶段作为参考图输入，所以你不需要重复描述商品的大面积颜色、基础材质和大轮廓，只需要在容易丢失时补充品牌文字、logo 位置、特殊结构、小面积装饰、异形轮廓、特殊开合方式等高辨识度信息。你的任务是输出一整段最终给生图模型使用的中文 prompt，要求只替换参考图里的主体商品或摆件，不改变参考图的场景骨架、机位、取景范围、主体大小、裁切方式和光影关系，不要擅自添加参考图里没有的新道具，不要输出解释、标题、分点或 JSON。",
    "apparelPortraitPrompt": "你是一位电商服饰模特设定提示词专家。你会看到一张参考图，这张图只用来生成一张新的模特人像垫图，后续再把用户的服饰商品替换上去。你的任务是只根据参考图输出一整段中文生图 prompt，用于先生成一张与参考图人物气质、性别、年龄感、脸型、发型长度、发色、妆容浓度、视线方向、头部倾斜、身体朝向、动作姿态、镜头角度、景别、主体占比、裁切方式、场景地点、时间段、背景布局、色彩氛围、光影关系都尽量相似的模特人像图片。你必须保留参考图的人像出镜形式和构图骨架，但要让模特穿着尽量简洁、干净、贴身、低干扰的基础内搭或无明显设计感的占位服装，避免外套、复杂印花、大面积文字、夸张配饰和抢主体的服装细节，以便后续服饰替换。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
    "apparelFinalPrompt": "你是一位电商服饰换装复刻提示词专家。你会看到参考图、生成的人像垫图和用户的商品图。参考图只负责提供场景模板，你必须继承参考图里的时间段、天气、场景地点、背景布局、机位、镜头角度、景别、主体占比、裁切方式、人物姿态、手部位置、视线方向、光影关系和整体营销氛围。生成的人像垫图是最终模特基础，你必须尽量保留它的人脸、发型、体态、肢体关系和取景裁切。商品图只负责提供要替换上身的服饰主体，商品图会在后续生成阶段作为参考图输入，因此你不需要冗长描述基础颜色和大体轮廓，只需要在容易丢失时补充品牌文字、logo、领口结构、袖型、纽扣排布、特殊拼接、不对称设计、特殊面料工艺等关键特征。你的任务是输出一整段最终给生图模型使用的中文 prompt，要求把商品服饰自然穿在模特对应部位，保持参考图的构图骨架和动作，不要擅自改性别、改人数、改景别、改主体大小，也不要把服饰替换成完全不同的穿法。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
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

PRODUCT_KIND_PROMPT = (
    "你是一位电商商品路径分类助手。你会看到一张商品图，只需要判断这张图的主要商品更适合走“服饰”还是“非服饰”生成链路。"
    "服饰包括上衣、裤子、裙子、外套、内衣、鞋靴、帽子等穿在人体上的商品；"
    "非服饰包括戒指、项链、耳饰、手表、箱包、美妆、家居、数码、食品、摆件等。"
    "只输出一个 JSON，对象里必须包含 productKind 和 reason 两个字段。"
    "productKind 只能是 apparel 或 non_apparel。"
)

REFERENCE_FACE_PROMPT = (
    "你是一位电商参考图结构识别助手。你会看到一张参考图，只需要判断参考图里是否存在清晰、足够大、可用于后续服饰复刻的人脸。"
    "只有当画面中出现真人面部，并且脸部不是过小、不是严重遮挡、不是背脸、不是极端模糊、不是插画或雕塑、五官至少大部分可辨认时，才可以判定为 true。"
    "如果只是有人体但看不清脸，或者脸太小、侧背严重、戴口罩遮住大部分五官、被头发或道具遮挡、只是海报或印花上的脸，都必须判定为 false。"
    "请只输出一个 JSON，对象里必须包含 hasFace 和 reason 两个字段。"
    "hasFace 只能是 true 或 false。"
)


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
            self._authorize()
            self._assert_ark_key()
            body = self._read_json_body()

            if self.path == "/replicate":
                result = replicate(body)
                self._send_json(200, result)
                return

            if self.path == "/classify-product":
                result = classify_product_endpoint(body)
                self._send_json(200, result)
                return

            self._send_json(404, {"error": "Not found"})
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


def classify_product_endpoint(body):
    product_image_data_url = body.get("productImageDataUrl", "")
    if not product_image_data_url:
        error = Exception("productImageDataUrl is required.")
        error.status_code = 400
        raise error

    settings = build_settings(body)
    product_data_url = normalize_data_url(product_image_data_url)
    product_kind, reason = classify_product_kind(product_data_url, settings)
    return {"productKind": product_kind, "reason": reason}


def replicate(body):
    image_url = body.get("imageUrl", "")
    product_image_data_url = body.get("productImageDataUrl", "")
    if not image_url:
        error = Exception("imageUrl is required.")
        error.status_code = 400
        raise error
    if not product_image_data_url:
        error = Exception("productImageDataUrl is required.")
        error.status_code = 400
        raise error

    settings = build_settings(body)
    reference_data_url = convert_image_url_to_data_url(image_url)
    product_data_url = normalize_data_url(product_image_data_url)

    generation_path = normalize_generation_path(body.get("generationPath"))
    if not generation_path:
        generation_path, _ = classify_product_kind(product_data_url, settings)

    if generation_path == "apparel":
        return replicate_apparel(reference_data_url, product_data_url, settings, generation_path)
    return replicate_non_apparel(reference_data_url, product_data_url, settings, generation_path)


def build_settings(body):
    return {
        "model": body.get("model") or DEFAULTS["model"],
        "visionModel": body.get("visionModel") or DEFAULTS["visionModel"],
        "nonApparelPrompt": body.get("nonApparelPrompt") or DEFAULTS["nonApparelPrompt"],
        "apparelPortraitPrompt": body.get("apparelPortraitPrompt")
        or DEFAULTS["apparelPortraitPrompt"],
        "apparelFinalPrompt": body.get("apparelFinalPrompt") or DEFAULTS["apparelFinalPrompt"],
        "defaultUserPrompt": body.get("defaultUserPrompt") or DEFAULTS["defaultUserPrompt"],
        "imageSize": body.get("imageSize") or DEFAULTS["imageSize"],
        "responseDataPath": body.get("responseDataPath") or DEFAULTS["responseDataPath"],
        "extraBody": body.get("extraBody")
        if isinstance(body.get("extraBody"), dict)
        else DEFAULTS["extraBody"],
        "userPrompt": body.get("userPrompt") or DEFAULTS["defaultUserPrompt"],
        "productSubjectHint": (body.get("productSubjectHint") or "").strip(),
    }


def replicate_non_apparel(reference_data_url, product_data_url, settings, generation_path):
    prompt = compose_non_apparel_prompt(reference_data_url, product_data_url, settings)
    result_image_url = generate_image(prompt, settings, [product_data_url])
    return {
        "imageUrl": result_image_url,
        "referenceAnalysisPrompt": "",
        "productAnalysisPrompt": "",
        "analysisPrompt": "",
        "prompt": prompt,
        "portraitPrompt": "",
        "portraitImageUrl": "",
        "referenceHasFace": False,
        "generationPath": generation_path,
    }


def replicate_apparel(reference_data_url, product_data_url, settings, generation_path):
    reference_has_face, face_reason = detect_reference_face(reference_data_url, settings)
    portrait_prompt = ""
    portrait_image_url = ""

    if reference_has_face:
        portrait_prompt = compose_apparel_portrait_prompt(reference_data_url, settings)
        portrait_image_url = generate_image(portrait_prompt, settings, [])

    final_prompt = compose_apparel_final_prompt(
        reference_data_url,
        product_data_url,
        portrait_image_url,
        reference_has_face,
        settings,
    )
    reference_images = [product_data_url]
    if portrait_image_url:
        reference_images = [portrait_image_url, product_data_url]

    result_image_url = generate_image(final_prompt, settings, reference_images)
    return {
        "imageUrl": result_image_url,
        "referenceAnalysisPrompt": "",
        "productAnalysisPrompt": "",
        "analysisPrompt": "",
        "prompt": final_prompt,
        "portraitPrompt": portrait_prompt,
        "portraitImageUrl": portrait_image_url,
        "referenceHasFace": reference_has_face,
        "referenceFaceReason": face_reason,
        "generationPath": generation_path,
    }


def classify_product_kind(product_data_url, settings):
    text = call_vision_model(
        model=settings["visionModel"],
        instructions=PRODUCT_KIND_PROMPT,
        content=[
            {"type": "input_image", "image_url": product_data_url},
            {
                "type": "input_text",
                "text": "请判断这张商品图的主要商品应该走服饰还是非服饰路径。只输出 JSON。",
            },
        ],
        temperature=0,
        max_output_tokens=220,
    )
    data = parse_json_text(text)
    product_kind = normalize_generation_path(data.get("productKind"))
    if not product_kind:
        lowered = text.lower()
        product_kind = "apparel" if "apparel" in lowered else "non_apparel"
    if not product_kind:
        product_kind = "non_apparel"
    return product_kind, str(data.get("reason") or "").strip()


def detect_reference_face(reference_data_url, settings):
    text = call_vision_model(
        model=settings["visionModel"],
        instructions=REFERENCE_FACE_PROMPT,
        content=[
            {"type": "input_image", "image_url": reference_data_url},
            {
                "type": "input_text",
                "text": "只判断参考图里是否有清晰、足够大、适合做人像垫图的人脸。只输出 JSON。",
            },
        ],
        temperature=0,
        max_output_tokens=180,
    )
    data = parse_json_text(text)
    has_face = bool(data.get("hasFace"))
    reason = str(data.get("reason") or "").strip()
    if not isinstance(data.get("hasFace"), bool):
        lowered = text.lower()
        has_face = '"hasface": true' in lowered or '"hasface":true' in lowered
    return has_face, reason


def compose_non_apparel_prompt(reference_data_url, product_data_url, settings):
    subject_hint = settings.get("productSubjectHint", "")
    user_prompt = settings.get("userPrompt", "").strip() or DEFAULTS["defaultUserPrompt"]
    text = call_vision_model(
        model=settings["visionModel"],
        instructions=settings["nonApparelPrompt"],
        content=[
            {"type": "input_image", "image_url": reference_data_url},
            {"type": "input_image", "image_url": product_data_url},
            {
                "type": "input_text",
                "text": (
                    "第一张图是参考图，只负责提供场景模板。"
                    "第二张图是商品图，只负责提供最终要替换进去的非服饰商品主体。"
                    f"{build_subject_hint_text(subject_hint)}"
                    f"用户补充要求：{user_prompt}"
                    "请直接输出一整段最终给生图模型使用的中文 prompt。"
                ),
            },
        ],
        temperature=0.2,
        max_output_tokens=1200,
    )
    return text or build_non_apparel_fallback(subject_hint, user_prompt)


def compose_apparel_portrait_prompt(reference_data_url, settings):
    user_prompt = settings.get("userPrompt", "").strip() or DEFAULTS["defaultUserPrompt"]
    text = call_vision_model(
        model=settings["visionModel"],
        instructions=settings["apparelPortraitPrompt"],
        content=[
            {"type": "input_image", "image_url": reference_data_url},
            {
                "type": "input_text",
                "text": (
                    "这张参考图将只用于先生成一张模特人像垫图。"
                    "请保留人物气质、姿态、场景、机位、景别、裁切和光影关系，"
                    "但让模特穿着简洁低干扰的占位基础款，为后续服饰替换留出空间。"
                    f"用户补充要求：{user_prompt}"
                    "请只输出一整段最终给生图模型使用的中文 prompt。"
                ),
            },
        ],
        temperature=0.2,
        max_output_tokens=1000,
    )
    return text or build_apparel_portrait_fallback(user_prompt)


def compose_apparel_final_prompt(
    reference_data_url,
    product_data_url,
    portrait_image_url,
    reference_has_face,
    settings,
):
    subject_hint = settings.get("productSubjectHint", "")
    user_prompt = settings.get("userPrompt", "").strip() or DEFAULTS["defaultUserPrompt"]
    content = [{"type": "input_image", "image_url": reference_data_url}]
    if portrait_image_url:
        content.append({"type": "input_image", "image_url": portrait_image_url})
    content.append({"type": "input_image", "image_url": product_data_url})
    content.append(
        {
            "type": "input_text",
            "text": (
                "第一张图是参考图，只负责提供场景模板。"
                + (
                    "第二张图是已经生成好的模特人像垫图，必须尽量保留这张图里的脸、头发、体态和裁切；"
                    "第三张图是用户上传的服饰商品图。"
                    if portrait_image_url
                    else "第二张图是用户上传的服饰商品图。"
                )
                + (
                    "参考图里有人脸，所以最终图必须尽量沿用人像垫图作为模特基础。"
                    if reference_has_face
                    else "参考图里没有可用人脸，因此最终图不需要先依赖人像垫图脸部一致性。"
                )
                + build_subject_hint_text(subject_hint)
                + f"用户补充要求：{user_prompt}"
                + "请只输出一整段最终给生图模型使用的中文 prompt。"
            ),
        }
    )
    text = call_vision_model(
        model=settings["visionModel"],
        instructions=settings["apparelFinalPrompt"],
        content=content,
        temperature=0.2,
        max_output_tokens=1400,
    )
    return text or build_apparel_final_fallback(subject_hint, user_prompt, reference_has_face)


def call_vision_model(model, instructions, content, temperature, max_output_tokens):
    payload = {
        "model": model,
        "instructions": instructions,
        "input": [{"role": "user", "content": content}],
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    data = post_json("https://ark.cn-beijing.volces.com/api/v3/responses", payload)
    return extract_response_text(data)


def generate_image(prompt, settings, reference_images):
    payload = {
        "model": settings["model"],
        "prompt": prompt,
        "size": settings["imageSize"],
        **settings["extraBody"],
    }
    normalized_refs = [item for item in reference_images if isinstance(item, str) and item]
    if normalized_refs:
        payload["reference_images"] = normalized_refs
        if len(normalized_refs) == 1:
            payload["image"] = normalized_refs[0]

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


def normalize_generation_path(value):
    if not isinstance(value, str):
        return ""
    normalized = value.strip().lower()
    if normalized in ("apparel", "服饰"):
        return "apparel"
    if normalized in ("non_apparel", "non-apparel", "非服饰"):
        return "non_apparel"
    return ""


def strip_code_fences(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1]
            if "\n" in cleaned:
                cleaned = cleaned.split("\n", 1)[1]
    return cleaned.strip()


def parse_json_text(text):
    cleaned = strip_code_fences(text)
    if not cleaned:
        return {}
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def build_subject_hint_text(subject_hint):
    if not subject_hint:
        return "如果商品图里有其他干扰元素，请优先锁定真正的商品主体。"
    return f"用户额外说明商品主体是：{subject_hint}。识别商品主体时必须优先参考这句说明。"


def build_non_apparel_fallback(subject_hint, user_prompt):
    subject_text = f"商品主体是{subject_hint}。" if subject_hint else "商品主体以商品图为准。"
    return (
        "保留参考图的场景地点、背景元素、承载面材质、时间段、光影关系、镜头角度、景别、构图、裁切方式和主体占比，"
        "只替换其中的主体商品为用户上传的非服饰商品。"
        f"{subject_text}"
        "如果商品图里有品牌文字、特殊结构或小面积装饰，请一并保留。"
        f"附加要求：{user_prompt}"
    )


def build_apparel_portrait_fallback(user_prompt):
    return (
        "生成一张与参考图人物出镜方式、场景、机位、景别、姿态、光影关系和整体氛围尽量一致的模特人像图片，"
        "保留相近的性别、年龄感、发型、表情和裁切方式，"
        "但让模特穿着简洁低干扰的基础占位服装，不要使用复杂印花、大面积文字或抢主体的外搭。"
        f"附加要求：{user_prompt}"
    )


def build_apparel_final_fallback(subject_hint, user_prompt, reference_has_face):
    portrait_text = (
        "尽量沿用生成人像里的脸、发型、体态和裁切方式，"
        if reference_has_face
        else ""
    )
    subject_text = f"商品主体是{subject_hint}。" if subject_hint else "商品主体以商品图为准。"
    return (
        "保留参考图的场景地点、时间段、背景布局、光影关系、镜头角度、景别、主体占比、动作姿态、手部位置和裁切方式，"
        f"{portrait_text}"
        "把用户上传的服饰自然穿在模特对应部位，只替换服饰主体，不改变人物性别、人数和出镜方式。"
        f"{subject_text}"
        f"附加要求：{user_prompt}"
    )


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ProxyHandler)
    print(f"Proxy server listening on http://127.0.0.1:{PORT}")
    server.serve_forever()
