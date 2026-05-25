# -*- coding: utf-8 -*-

import base64
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PORT = int(os.environ.get("PORT", "8787"))
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "") or os.environ.get("ARK_API_KEY", "")
PROXY_TOKEN = os.environ.get("PROXY_TOKEN", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULTS = {
    "model": "openai/gpt-5.4-image-2",
    "visionModel": "moonshotai/kimi-k2.6",
    "nonApparelPrompt": "你是一位电商静物与非服饰商品复刻提示词专家。你会同时看到一张参考图和一张商品图。你的任务是把两张图转成一段最终可以直接交给生图模型的中文 prompt，让生图模型生成一张“用户商品主体正确，但摄影语言和参考图高度一致”的新图片。参考图只负责提供画面模板，你必须准确识别并继承参考图里的拍摄方式、画幅比例、景别、镜头角度、机位高低、焦段感、主体在画面中的位置和占比、主体朝向、主体倾斜角度、主体俯仰角度、主体与承载面的接触点、主体是否平放/斜放/竖立/悬浮/倚靠、多个物体之间的前后层级和遮挡关系、主体边缘与画面边界的距离、裁切方式、场景地点、背景元素、承载面材质、时间段、主光方向、光线质感、色温、曝光方式、色彩氛围、景深关系、主体与背景的光影关系，以及画面中原本存在的真实陈列和生活痕迹。商品图会直接作为后续生图模型的唯一商品参考图，因此最终 prompt 里不要详细描述商品本身的颜色、材质、品牌、logo、文字、纹理、形状、结构、链节、刻字、装饰、边缘、工艺、尺寸等视觉细节，这些交给图像参考通道。你只能极简点明商品品类和融入方式，例如“一枚戒指作为主体”“一个包放在桌面中央”“一瓶香水替换原主体”。最终输出必须是一整段中文 prompt，直接描述最终生成图片本身：保留参考图的场景、构图、镜头角度、主体摆放姿态、主体朝向、主体落点、前后层级、光影、景别、主体大小和整体气质，让商品图中的商品作为新主体出现在相同视觉框架里。不要输出解释、标题、分析过程、分点或 JSON。",
    "apparelPortraitPrompt": "你是一位电商服饰模特设定提示词专家。你会看到一张参考图，这张图只用来生成一张新的模特人像垫图，后续再把用户的服饰商品替换上去。你的任务是只根据参考图输出一整段中文生图 prompt，用于先生成一张与参考图人物气质、性别、年龄感、脸型、发型长度、发色、妆容浓度、视线方向、头部倾斜、身体朝向、动作姿态、镜头角度、景别、主体占比、裁切方式、场景地点、时间段、背景布局、色彩氛围、光影关系都尽量相似的模特人像图片。你必须保留参考图的人像出镜形式和构图骨架，但要让模特穿着尽量简洁、干净、贴身、低干扰的基础内搭或无明显设计感的占位服装，避免外套、复杂印花、大面积文字、夸张配饰和抢主体的服装细节，以便后续服饰替换。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
    "apparelFinalPrompt": "你是一位电商服饰换装复刻提示词专家。你会看到参考图、生成的人像垫图和用户的商品图。参考图只负责提供场景模板，你必须继承参考图里的时间段、天气、场景地点、背景布局、机位、镜头角度、景别、主体占比、裁切方式、人物姿态、手部位置、视线方向、光影关系和整体营销氛围。生成的人像垫图是最终模特基础，你必须尽量保留它的人脸、发型、体态、肢体关系和取景裁切。商品图只负责提供要替换上身的服饰主体，商品图会在后续生成阶段作为参考图输入，因此你不需要冗长描述基础颜色和大体轮廓，只需要在容易丢失时补充品牌文字、logo、领口结构、袖型、纽扣排布、特殊拼接、不对称设计、特殊面料工艺等关键特征。你的任务是输出一整段最终给生图模型使用的中文 prompt，要求把商品服饰自然穿在模特对应部位，保持参考图的构图骨架和动作，不要擅自改性别、改人数、改景别、改主体大小，也不要把服饰替换成完全不同的穿法。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
    "defaultUserPrompt": "输出适合电商投放和商品详情页的高清主视觉，主体明确，商品细节清晰，画面干净高级。",
    "imageSize": "2K",
    "responseDataPath": "",
    "extraBody": {},
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
            self._assert_api_key()
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
            payload = {"error": str(error)}
            image_request_debug = getattr(error, "image_request_debug", None)
            if image_request_debug:
                payload["imageRequestDebug"] = image_request_debug
            vision_debug = getattr(error, "vision_debug", None)
            if vision_debug:
                payload["visionDebug"] = vision_debug
            self._send_json(status, payload)

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

    def _assert_api_key(self):
        if not OPENROUTER_API_KEY:
            error = Exception("OPENROUTER_API_KEY is missing.")
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
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
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
    try:
        result_image_url, image_request_debug = generate_image(
            prompt, settings, [product_data_url]
        )
    except Exception as error:
        debug = build_image_request_debug_from_values(
            settings["model"], build_image_config(settings["imageSize"]).get("image_config", {}), prompt, [product_data_url]
        )
        attach_debug_to_error(error, debug)
        raise
    return {
        "imageUrl": result_image_url,
        "referenceAnalysisPrompt": "",
        "productAnalysisPrompt": "",
        "analysisPrompt": "",
        "prompt": prompt,
        "imageRequestDebug": image_request_debug,
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
        portrait_image_url, _ = generate_image(portrait_prompt, settings, [])

    final_prompt = compose_apparel_final_prompt(
        reference_data_url,
        product_data_url,
        portrait_image_url,
        reference_has_face,
        settings,
    )
    # Final image generation only keeps the user product image as the direct image reference.
    # The reference image and generated portrait only contribute through prompt construction.
    try:
        result_image_url, image_request_debug = generate_image(
            final_prompt, settings, [product_data_url]
        )
    except Exception as error:
        debug = build_image_request_debug_from_values(
            settings["model"], build_image_config(settings["imageSize"]).get("image_config", {}), final_prompt, [product_data_url]
        )
        attach_debug_to_error(error, debug)
        raise
    return {
        "imageUrl": result_image_url,
        "referenceAnalysisPrompt": "",
        "productAnalysisPrompt": "",
        "analysisPrompt": "",
        "prompt": final_prompt,
        "imageRequestDebug": image_request_debug,
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
    text, raw_response = call_vision_model_with_debug(
        model=settings["visionModel"],
        instructions=settings["nonApparelPrompt"],
        content=[
            {"type": "input_image", "image_url": reference_data_url},
            {"type": "input_image", "image_url": product_data_url},
            {
                "type": "input_text",
                "text": (
                    "第一张图是参考图，只负责提供最终生成图的场景、构图、光影、景别、主体占比和整体视觉气质。"
                    "第二张图是商品图，只负责提供最终要生成出来的非服饰商品主体，并且会直接作为生图模型的商品参考图。"
                    "你的输出必须是最终成图的中文描述，不要说“参考图里”“商品图里”，而要直接描述最终图片本身。"
                    "最终图片必须是：用户商品在视觉上成为新的主体，但整个画面的场景、机位、镜头、背景、时间段、光影关系、陈列方式、主体大小、主体落点、主体朝向、主体倾斜角度、主体与承载面的接触方式、前后层级和遮挡关系都尽量接近参考图。"
                    "请特别关注参考图中主体是平放、斜放、竖立、倚靠、悬浮、叠放还是局部被裁切，以及主体中心位于画面哪个区域、长轴朝向哪个方向。"
                    "不要在 prompt 里描述商品图中商品的颜色、材质、品牌、logo、文字、纹理、形状、结构、刻字、装饰、工艺等细节。商品细节由图像参考输入承担。"
                    "你只需要用一句话说明商品品类和融入方式，例如一枚戒指作为主体、一只包放在桌面中央、一瓶香水替换原主体。"
                    f"{build_subject_hint_text(subject_hint)}"
                    f"用户补充要求：{user_prompt}"
                    "输出格式必须严格为：FINAL_PROMPT: 后面接一整段最终给生图模型使用的中文 prompt。"
                    "不要输出分析、推理、解释、标题、清单、Markdown 或 JSON。"
                ),
            },
        ],
        temperature=0.2,
        max_output_tokens=1200,
    )
    prompt = extract_final_prompt_text(text)
    if not prompt:
        return build_non_apparel_safe_fallback(subject_hint, user_prompt)
    return prompt


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
                    "输出格式必须严格为：FINAL_PROMPT: 后面接一整段最终给生图模型使用的中文 prompt。"
                    "不要输出分析、推理、解释、标题、清单、Markdown 或 JSON。"
                ),
            },
        ],
        temperature=0.2,
        max_output_tokens=1000,
    )
    return extract_final_prompt_text(text) or build_apparel_portrait_fallback(user_prompt)


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
                + "输出格式必须严格为：FINAL_PROMPT: 后面接一整段最终给生图模型使用的中文 prompt。"
                + "不要输出分析、推理、解释、标题、清单、Markdown 或 JSON。"
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
    return extract_final_prompt_text(text) or build_apparel_final_fallback(subject_hint, user_prompt, reference_has_face)


def call_vision_model(model, instructions, content, temperature, max_output_tokens):
    text, _ = call_vision_model_with_debug(
        model=model,
        instructions=instructions,
        content=content,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
    return text


def call_vision_model_with_debug(model, instructions, content, temperature, max_output_tokens):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": openrouter_content(content)},
        ],
        "temperature": temperature,
        "max_tokens": max_output_tokens,
        "reasoning": {"effort": "none", "exclude": True},
    }
    data = post_json(OPENROUTER_URL, payload)
    return extract_response_text(data), data


def generate_image(prompt, settings, reference_images):
    content = [{"type": "text", "text": prompt}]
    for ref in reference_images:
        if isinstance(ref, str) and ref:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": ref},
                }
            )

    payload = {
        "model": settings["model"],
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
        "stream": False,
        **build_image_config(settings["imageSize"]),
        **settings["extraBody"],
    }

    image_request_debug = build_image_request_debug(payload, reference_images)
    data = post_json(OPENROUTER_URL, payload)
    value = extract_image_output(data)
    if not isinstance(value, str) or not value:
        raise Exception("生图成功，但没有在 OpenRouter 响应里拿到图片结果。")
    return value, image_request_debug


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
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "http://127.0.0.1:8787",
            "X-Title": "Commerce Creative Replicator",
        },
        method="POST",
    )
    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        text = error.read().decode("utf-8", errors="ignore")
        raise Exception(format_openrouter_error(error.code, text))
    except URLError as error:
        raise Exception(f"OpenRouter 请求失败: {error.reason}")


def extract_response_text(data):
    choices = data.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    for key in ("content", "reasoning_content", "reasoning", "output_text"):
        text = extract_text_value(message.get(key))
        if text:
            return text
    return ""


def extract_text_value(value):
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        for key in ("text", "content", "value", "output_text"):
            text = extract_text_value(value.get(key))
            if text:
                return text
    if isinstance(value, list):
        parts = []
        for item in value:
            text = extract_text_value(item)
            if text:
                parts.append(text)
        if parts:
            return "\n".join(parts)
    return ""


def extract_final_prompt_text(text):
    if not isinstance(text, str):
        return ""
    cleaned = strip_code_fences(text).strip()
    if not cleaned:
        return ""

    markers = (
        "FINAL_PROMPT:",
        "FINAL_PROMPT：",
        "最终生成 Prompt：",
        "最终生成 Prompt:",
        "最终生成Prompt：",
        "最终生成Prompt:",
        "最终 Prompt：",
        "最终 Prompt:",
        "最终prompt：",
        "最终prompt:",
    )
    for marker in markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[1].strip()
            break

    cleaned = strip_code_fences(cleaned).strip()
    cleaned = cleaned.lstrip("：: \n\t")
    if cleaned.startswith(("\"", "'")) and cleaned.endswith(("\"", "'")):
        cleaned = cleaned[1:-1].strip()
    return cleaned


def extract_image_output(data):
    choices = data.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    for image in message.get("images", []):
        if not isinstance(image, dict):
            continue
        image_url = image.get("image_url") or image.get("imageUrl") or {}
        if isinstance(image_url, dict):
            value = image_url.get("url")
            if isinstance(value, str) and value:
                return value
            b64_value = image_url.get("b64_json") or image_url.get("b64")
            if isinstance(b64_value, str) and b64_value:
                return f"data:image/png;base64,{b64_value}"
        if isinstance(image.get("url"), str) and image.get("url"):
            return image.get("url")
        b64_value = image.get("b64_json") or image.get("b64")
        if isinstance(b64_value, str) and b64_value:
            return f"data:image/png;base64,{b64_value}"
    if isinstance(message.get("content"), list):
        for item in message.get("content", []):
            if not isinstance(item, dict):
                continue
            image_url = item.get("image_url") or item.get("imageUrl") or {}
            if isinstance(image_url, dict):
                value = image_url.get("url")
                if isinstance(value, str) and value:
                    return value
                b64_value = image_url.get("b64_json") or image_url.get("b64")
                if isinstance(b64_value, str) and b64_value:
                    return f"data:image/png;base64,{b64_value}"
    return ""


def build_image_config(image_size):
    image_size_value = normalize_image_size_value(image_size)
    config = {}
    if image_size_value:
        config["image_config"] = image_size_value
    return config


def normalize_image_size_value(image_size):
    if not isinstance(image_size, str):
        return {}
    normalized = image_size.strip()
    if not normalized:
        return {}
    if normalized in ("1K", "2K", "4K", "512", "1024", "1536", "2048", "4096"):
        return {"image_size": normalized}
    ratio = parse_ratio_or_dimensions(normalized)
    if ratio:
        return {"aspect_ratio": ratio}
    return {"image_size": normalized}


def build_image_request_debug(payload, reference_images):
    return build_image_request_debug_from_values(
        payload.get("model"),
        payload.get("image_config", {}),
        extract_prompt_from_payload(payload),
        reference_images,
        payload.get("modalities", []),
    )


def build_image_request_debug_from_values(
    model, image_config, prompt, reference_images, modalities=None
):
    modalities = modalities if isinstance(modalities, list) else ["image", "text"]
    debug = {
        "model": model,
        "modalities": modalities,
        "imageConfig": image_config,
        "referenceImageCount": len(
            [item for item in reference_images if isinstance(item, str) and item]
        ),
        "referenceImages": [
            summarize_reference_image(item)
            for item in reference_images
            if isinstance(item, str) and item
        ],
        "prompt": prompt,
    }
    return debug


def extract_prompt_from_payload(payload):
    messages = payload.get("messages", [])
    prompt = ""
    if messages and isinstance(messages[0], dict):
        content = messages[0].get("content", [])
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text":
                    prompt = item.get("text", "")
                    break
    return prompt


def summarize_reference_image(value):
    if value.startswith("data:"):
        prefix, _, raw = value.partition(",")
        mime = prefix.split(";")[0].replace("data:", "") or "image/*"
        return {
            "kind": "data_url",
            "mime": mime,
            "bytesApprox": int(len(raw) * 0.75),
            "preview": value[:96] + "..." if len(value) > 96 else value,
        }
    return {
        "kind": "url",
        "preview": value,
    }


def attach_debug_to_error(error, debug):
    try:
        error.image_request_debug = debug
    except Exception:
        pass


def attach_vision_debug_to_error(error, response_data):
    try:
        error.vision_debug = summarize_vision_response(response_data)
    except Exception:
        pass


def summarize_vision_response(response_data):
    if not isinstance(response_data, dict):
        return {"rawType": type(response_data).__name__}
    choices = response_data.get("choices", [])
    summary = {
        "keys": list(response_data.keys()),
        "choicesCount": len(choices) if isinstance(choices, list) else 0,
    }
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content")
        summary["messageKeys"] = list(message.keys()) if isinstance(message, dict) else []
        summary["contentType"] = type(content).__name__
        if isinstance(content, str):
            summary["contentPreview"] = content[:500]
        elif isinstance(content, list):
            summary["contentPreview"] = str(content[:3])[:500]
    return summary


def parse_ratio_or_dimensions(value):
    cleaned = value.strip().lower()
    if ":" in cleaned:
        return cleaned
    if "x" not in cleaned:
        return ""
    left, right = cleaned.split("x", 1)
    try:
        width = int(left)
        height = int(right)
    except ValueError:
        return ""
    if width <= 0 or height <= 0:
        return ""
    return simplify_ratio(width, height)


def simplify_ratio(width, height):
    divisor = gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def openrouter_content(content):
    normalized = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "input_text":
            normalized.append({"type": "text", "text": item.get("text", "")})
            continue
        if item.get("type") == "input_image":
            normalized.append(
                {
                    "type": "image_url",
                    "image_url": {"url": item.get("image_url", "")},
                }
            )
    return normalized


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


def format_openrouter_error(status_code, text):
    detail = text[:400]
    parsed = {}
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = {}

    error_payload = parsed.get("error", {}) if isinstance(parsed, dict) else {}
    message = error_payload.get("message") if isinstance(error_payload, dict) else ""
    if isinstance(message, str) and "violation of provider Terms Of Service" in message:
        return (
            "当前 OpenRouter 图像提供方拒绝了这次请求。"
            "这通常不是代码问题，而是模型提供方不允许当前这类图片编辑/人物换装/参考图改写请求。"
            "如果你继续用 gpt-5.4-image-2，建议先改成纯文生图；"
            "如果你要保留商品参考图和换装链路，建议换一个更适合 image-to-image 的生图模型。"
        )
    return f"OpenRouter 请求失败 ({status_code})：{detail}"


def build_subject_hint_text(subject_hint):
    if not subject_hint:
        return "如果商品图里有其他干扰元素，请优先锁定真正的商品主体。"
    return f"用户额外说明商品主体是：{subject_hint}。识别商品主体时必须优先参考这句说明。"


def build_non_apparel_safe_fallback(subject_hint, user_prompt):
    subject_text = f"商品主体是{subject_hint}。" if subject_hint else "商品主体以商品参考图为准。"
    return (
        "生成一张非服饰商品电商静物图，商品外观完全以输入的商品参考图为准，"
        "不要在文字里重新发明商品的颜色、材质、品牌、logo、文字、纹理、结构或装饰细节。"
        f"{subject_text}"
        "画面需要尽量复刻原网页参考图的摄影语言：保持相同画幅比例、镜头角度、机位高度、景别、主体占比、主体中心落点、"
        "主体朝向、倾斜角度、俯仰关系、主体与承载面的接触方式、前后层级、遮挡关系、边缘裁切、背景环境、承载面材质、"
        "光线方向、色温、曝光、景深、色彩氛围和整体陈列方式。"
        "将商品自然放置在原参考主体所在区域，保持相近的视觉重心和空间关系。"
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
