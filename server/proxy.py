# -*- coding: utf-8 -*-

import base64
import json
import os
import time
import uuid
from http.client import IncompleteRead, RemoteDisconnected
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PORT = int(os.environ.get("PORT", "8787"))
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "") or os.environ.get("ARK_API_KEY", "")
PROXY_TOKEN = os.environ.get("PROXY_TOKEN", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GENERATED_IMAGES = {}
GENERATED_IMAGE_ORDER = []
MAX_GENERATED_IMAGES = 20
PROGRESS_JOBS = {}
PROGRESS_JOB_ORDER = []
MAX_PROGRESS_JOBS = 50

DEFAULTS = {
    "model": "openai/gpt-5.4-image-2",
    "visionModel": "moonshotai/kimi-k2.6",
    "nonApparelPrompt": "你是一位真实商品摄影与非服饰商品复刻提示词专家。你会同时看到一张参考图和一张商品图。你的任务是把两张图转成一段最终可以直接交给生图模型的中文 prompt，让生图模型生成一张“用户商品主体正确，但摄影语言和参考图高度一致”的真实拍摄效果图片。参考图只负责提供画面模板，你必须像摄影师复盘机位一样，准确识别并继承参考图里的画幅比例、景别、镜头焦段感、相机高度、俯拍/平拍/仰拍程度、镜头向左或向右的水平偏转、画面近端和远端的位置、透视收缩方向、水平线或盒边/桌边的斜率、主体在画面中的位置和占比、主体朝向、主体长轴方向、主体倾斜角度、主体俯仰角度、主体与承载面的接触点、主体是否平放/斜放/竖立/悬浮/倚靠/嵌入卡槽/半露出/叠放/被托起、多个物体之间的前后层级和遮挡关系、主体边缘与画面边界的距离、裁切方式、场景地点、背景元素、承载面材质、时间段、主光方向、光线质感、色温、曝光方式、色彩氛围、景深关系、主体与背景的光影关系，以及画面中原本存在的真实陈列和生活痕迹。最终 prompt 必须明确写出相机视角：例如低角度贴近桌面、从正前方略偏右看向左后方、从上方约 30 度俯视、镜头沿盒子对角线方向拍摄、近处盒沿在画面底部横向穿过、远处盒盖向右上方退去等；不要只写“微距特写、低角度俯拍”这种笼统词。最终 prompt 还必须用具体方位写清楚新商品的摆放姿势：它位于画面哪个区域，长轴或开口朝向哪里，正面/侧面/顶部露出多少，是否贴着、压在、嵌入、悬在、靠着或插入某个承载物，接触点在哪里，阴影落向哪里；如果参考图中原主体有专用托槽、盒垫、支架、桌面边缘、布面褶皱或局部遮挡，必须让新商品占用同一个空间关系。商品图会直接作为后续生图模型的唯一商品参考图，因此最终 prompt 里不要详细描述商品本身的颜色、材质、品牌、logo、文字、纹理、形状、结构、链节、刻字、装饰、边缘、工艺、尺寸等视觉细节，这些交给图像参考通道。你只能极简点明商品品类和融入方式，例如“一枚戒指嵌在盒垫中央的卡槽里，弧面横向朝向镜头，镜头从盒子前下方略偏右的位置沿盒内对角线看过去”“一个包斜靠在桌面右后方”“一瓶香水竖立在原主体落点”。最终输出必须是一整段中文 prompt，直接描述最终生成图片本身：保留参考图的场景、构图、镜头角度、主体摆放姿态、主体朝向、主体落点、前后层级、光影、景别、主体大小和整体气质，画面必须像真实相机拍摄，不要出现 CGI、3D 渲染、插画、海报合成或过度广告精修感。不要输出解释、标题、分析过程、分点或 JSON。",
    "apparelFinalPrompt": "你是一位真实服饰摄影、穿搭换装与参考图复刻提示词专家。你会看到小红书参考图和用户上传的服饰商品图。你的核心任务是先把小红书参考图转换成具体画面文字，再把用户商品服饰融入这段画面，输出一整段最终成图 prompt。最终 prompt 必须直接描述最终图片本身，像在描述一张已经拍出来的照片，而不是描述任务规则。参考图负责提供完整画面模板和人物模板，你必须具体写出参考图中真实可见的内容：人物形象气质、发型、脸部可见状态、视线、头部倾斜、身体朝向、动作姿态、手臂和手的位置、场景地点、室内/室外环境、背景墙面/镜子/门框/家具/地面/道具、时间段、光线方向和质感、相机或手机拍摄方式、镜面自拍关系、机位高度、俯拍/平拍/仰拍程度、镜头向左或向右的水平偏转、景别、人物在画面中的位置和占比、人物主要位于画面上部/中部/下部还是贯穿全画面、人物头顶/脚底/左右身体边缘距离画面边界的大致比例、人物高度占画面高度的大致比例、画面上下左右留白和主要背景区域的大致比例、画面四边分别裁到人物/服饰/道具哪里、哪些身体部位和服饰部件完整可见/局部可见/完全不可见、人物坐姿/站姿/蹲姿、可见四肢和双脚的方向、肩颈和躯干朝向、手机/包/椅子/凳子等道具与人物的接触关系，以及画面近处和远处的空间层级。最终 prompt 必须保持参考图的人物形象方向、姿势、手势、垂直位置、主体大小、上下留白、左右留白、边界距离和可见范围，不要为了突出服装而自动放大人物、缩小人物、居中人物、移动镜头、扩展画幅、补全身体、补全道具或改变画面重心。无论参考图是不展示脚、不展示腿、不展示下半身、不展示躯干、不展示头部、只露出局部身体、只露出局部商品还是裁掉某个道具，最终 prompt 都必须写成同样的局部可见范围；参考图中完全不可见的身体部位、服饰部件、配饰、道具和背景区域不能出现在最终 prompt 中。商品图只负责提供要替换上身或穿戴的服饰主体本身，最终 prompt 只需要说明商品服饰穿在参考图人物对应部位，并描述它如何贴合参考图人物姿态、肩带/领口/腰线/裙摆/裤脚/袖口与动作和遮挡关系；商品外观细节以商品图为准，不要编造商品图里没有的设计。参考图里人物原本穿着的衣服、鞋帽、包袋和配饰不是本次商品，不能保留或复述参考图原服饰的颜色、图案、数字、logo、文字、玩偶、装饰、面料和款式；参考图原服饰只用于判断身体遮挡、衣物边缘落点、可见范围和裁切位置，最终可见服饰外观必须来自商品图。如果商品图中也出现真人、模特、手臂、脸、身体、发型、妆容、背景、道具或强动作，它们都不是人物模板和画面模板，不能写进最终 prompt，也不能覆盖参考图的人物形象、脸、发型、体态、人物姿势、手部位置、身体朝向、场景、拍摄角度、构图和可见范围；只能从商品图提取服饰本身的款式、廓形、颜色、图案、材质、开合、肩带、领口、袖长、下摆、裤脚、鞋型或帽型等穿着外观。严禁输出“需要保留、必须复刻、参考图负责、商品图负责、不要改变、最终 prompt 必须”等任务说明式句子；严禁只写“保留参考图的场景和姿态”这种空话。你应该输出类似“一张真实手机镜前自拍照片，年轻女性坐在更衣室浅色墙面前的矮凳上……”这样的具体画面描述。不要擅自改性别、人数、景别、主体大小、坐站关系、镜面自拍方式、人物在画面中的垂直位置、上下留白比例、可见范围或主要道具。画面必须像真实手机或相机拍摄，不要出现 CGI、3D 渲染、插画、海报合成或过度广告精修感。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
    "defaultUserPrompt": "",
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
        if self.path.startswith("/progress/"):
            self._send_progress()
            return
        if self.path.startswith("/generated/"):
            self._send_generated_image()
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

    def _send_generated_image(self):
        image_id = self.path.rsplit("/", 1)[-1].split("?", 1)[0]
        item = GENERATED_IMAGES.get(image_id)
        if not item:
            self._send_json(404, {"error": "Generated image not found"})
            return
        raw = item["raw"]
        self.send_response(200)
        self._set_cors_headers()
        self.send_header("Content-Type", item["content_type"])
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_progress(self):
        progress_id = self.path.rsplit("/", 1)[-1].split("?", 1)[0]
        item = PROGRESS_JOBS.get(progress_id)
        if not item:
            self._send_json(404, {"error": "Progress not found"})
            return
        self._send_json(200, item)

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
    init_progress(settings, body.get("progressId"), body.get("generationPath"))
    reference_data_url = convert_image_url_to_data_url(image_url)
    product_data_url = normalize_data_url(product_image_data_url)

    generation_path = normalize_generation_path(body.get("generationPath"))
    if not generation_path:
        generation_path, _ = classify_product_kind(product_data_url, settings)
    settings["generationPath"] = generation_path
    init_progress(settings, settings.get("progressId"), generation_path)

    try:
        if generation_path == "apparel":
            result = replicate_apparel(reference_data_url, product_data_url, settings, generation_path)
        else:
            result = replicate_non_apparel(reference_data_url, product_data_url, settings, generation_path)
        set_progress(settings, 999, "生成完成", status="done")
        return result
    except Exception:
        set_progress(settings, None, "生成失败", status="error")
        raise


def build_settings(body):
    return {
        "model": body.get("model") or DEFAULTS["model"],
        "visionModel": body.get("visionModel") or DEFAULTS["visionModel"],
        "nonApparelPrompt": body.get("nonApparelPrompt") or DEFAULTS["nonApparelPrompt"],
        "apparelFinalPrompt": body.get("apparelFinalPrompt") or DEFAULTS["apparelFinalPrompt"],
        "defaultUserPrompt": body.get("defaultUserPrompt") or DEFAULTS["defaultUserPrompt"],
        "imageSize": body.get("imageSize") or DEFAULTS["imageSize"],
        "responseDataPath": body.get("responseDataPath") or DEFAULTS["responseDataPath"],
        "extraBody": body.get("extraBody")
        if isinstance(body.get("extraBody"), dict)
        else DEFAULTS["extraBody"],
        "userPrompt": body.get("userPrompt") or DEFAULTS["defaultUserPrompt"],
        "productSubjectHint": (body.get("productSubjectHint") or "").strip(),
        "timings": [],
        "progressId": body.get("progressId") or "",
        "generationPath": normalize_generation_path(body.get("generationPath")),
    }


def replicate_non_apparel(reference_data_url, product_data_url, settings, generation_path):
    set_progress(settings, 0, "正在分析参考图并融合商品约束")
    prompt = compose_non_apparel_prompt(reference_data_url, product_data_url, settings)
    set_progress(settings, 1, "Prompt 已生成，正在调用生图模型")
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
        "timings": settings["timings"],
        "referenceHasFace": False,
        "generationPath": generation_path,
    }


def replicate_apparel(reference_data_url, product_data_url, settings, generation_path):
    set_progress(settings, 0, "正在分析参考图")
    reference_analysis = analyze_apparel_reference(reference_data_url, settings)
    set_progress(settings, 1, "参考图分析完成")
    reference_has_face = reference_analysis["hasFace"]
    face_reason = reference_analysis["reason"]
    reference_description = reference_analysis["referenceDescription"]
    set_progress(settings, 1, "正在融合参考图和商品服饰约束")
    final_prompt = compose_apparel_final_prompt(
        reference_data_url,
        product_data_url,
        reference_has_face,
        reference_description,
        settings,
    )
    set_progress(settings, 2, "最终 Prompt 已生成，正在调用生图模型")
    final_reference_images = [product_data_url]
    final_image_prompt = (
        f"{final_prompt}"
        " 直接参考输入中的图片只有用户上传的服饰商品图，只作为服饰外观参考，必须把这件商品服饰穿到 prompt 描述的人物对应部位。"
        "不要把商品图里的人物、手臂、脸、发型、身体比例、背景、道具或强动作当成最终人物形象和姿势；"
        "最终人物形象、姿势、手势、场景、机位和构图只能来自文字 prompt 中对小红书参考图的描述。"
    )
    try:
        result_image_url, image_request_debug = generate_image(
            final_image_prompt, settings, final_reference_images
        )
    except Exception as error:
        debug = build_image_request_debug_from_values(
            settings["model"], build_image_config(settings["imageSize"]).get("image_config", {}), final_image_prompt, final_reference_images
        )
        attach_debug_to_error(error, debug)
        raise
    return {
        "imageUrl": result_image_url,
        "referenceAnalysisPrompt": reference_description,
        "productAnalysisPrompt": "",
        "analysisPrompt": "",
        "prompt": final_prompt,
        "imageRequestDebug": image_request_debug,
        "timings": settings["timings"],
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
        timings=settings.get("timings"),
        timing_label="kimi_product_classification",
    )
    data = parse_json_text(text)
    product_kind = normalize_generation_path(data.get("productKind"))
    if not product_kind:
        lowered = text.lower()
        product_kind = "apparel" if "apparel" in lowered else "non_apparel"
    if not product_kind:
        product_kind = "non_apparel"
    return product_kind, str(data.get("reason") or "").strip()


def analyze_apparel_reference(reference_data_url, settings):
    text = call_vision_model(
        model=settings["visionModel"],
        instructions=(
            "你是一位小红书服饰参考图分析助手。你只分析这一张参考图，并输出 JSON。"
            "你需要同时判断图中是否有清晰、足够大、适合在最终图里作为人物形象参考的人脸，"
            "并把参考图中真实可见的画面转成一整段中文描述，用于后续复刻拍摄场景、构图、机位和人物姿态。"
            "画面描述必须具体包含场景地点、背景墙面/镜子/门框/家具/地面/道具、手机或镜面自拍关系、"
            "人物位置和占比、人物主要处于画面的上部/中部/下部还是贯穿全画面、人物头顶和脚底到画面边界的距离、人物高度占画面高度的大致比例、"
            "画面上下左右留白和主要背景区域比例、画面四边分别裁到人物/服饰/道具哪里、哪些身体部位和服饰部件完整可见/局部可见/完全不可见、坐姿或站姿、四肢摆放、手和手机/包/椅子等道具关系、拍摄角度、光线、色温和真实拍摄质感。"
            "只输出 JSON，不要 Markdown。"
        ),
        content=[
            {"type": "input_image", "image_url": reference_data_url},
            {
                "type": "input_text",
                "text": (
                    "请输出 JSON："
                    "{\"hasFace\": boolean, \"reason\": \"人脸判断原因\", \"referenceDescription\": \"参考图具体画面描述\"}。"
                    "hasFace 只有当真人脸部清晰、足够大、五官大部分可辨认、适合最终图沿用人物形象时才为 true；"
                    "如果脸太小、严重遮挡、背脸、极端模糊、插画或海报里的脸，都为 false。"
                ),
            },
        ],
        temperature=0,
        max_output_tokens=1100,
        timings=settings.get("timings"),
        timing_label="kimi_apparel_reference_analysis",
    )
    data = parse_json_text(text)
    has_face = bool(data.get("hasFace"))
    if not isinstance(data.get("hasFace"), bool):
        lowered = text.lower()
        has_face = '"hasface": true' in lowered or '"hasface":true' in lowered
    reference_description = str(data.get("referenceDescription") or "").strip()
    if not reference_description:
        reference_description = extract_reference_description_text(text)
    return {
        "hasFace": has_face,
        "reason": str(data.get("reason") or "").strip(),
        "referenceDescription": reference_description,
    }


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
        timings=settings.get("timings"),
        timing_label="kimi_non_apparel_prompt",
    )
    prompt = extract_final_prompt_text(text)
    if not prompt:
        return build_non_apparel_safe_fallback(subject_hint, user_prompt)
    return prompt


def compose_apparel_final_prompt(
    reference_data_url,
    product_data_url,
    reference_has_face,
    reference_description,
    settings,
):
    subject_hint = settings.get("productSubjectHint", "")
    user_prompt = settings.get("userPrompt", "").strip() or DEFAULTS["defaultUserPrompt"]
    content = [{"type": "input_image", "image_url": reference_data_url}]
    content.append({"type": "input_image", "image_url": product_data_url})
    content.append(
        {
            "type": "input_text",
            "text": (
                "第一张图是用户在小红书想复刻的参考图，必须先把这张参考图转成具体画面描述，再写成最终成图 prompt。"
                + "第二张图是用户上传的服饰商品图，只用于识别服饰本身。"
                + (
                    "参考图里有人脸，所以最终图必须尽量沿用第一张参考图里的人物形象、脸部可见状态、发型、气质、体态、动作和裁切。"
                    if reference_has_face
                    else "参考图里没有可用人脸，因此最终图不需要强求脸部一致，但仍必须沿用第一张参考图的人物姿态、身体朝向、裁切、场景和构图。"
                )
                + "第一张参考图里人物原本穿着的衣服、鞋帽、包袋和配饰不是本次要生成的商品，不能把参考图原服饰的颜色、图案、数字、logo、文字、玩偶、装饰、面料和款式写进最终 prompt；参考图原服饰只允许用于判断身体遮挡、领口/袖口/下摆落点、衣物与手臂/包/头发的接触关系、可见范围和裁切位置。"
                + "最终画面中所有需要替换或新增的服饰外观，都必须来自第二张商品图；如果最终 prompt 描述了参考图原服饰外观，就会导致错误。"
                + "服饰商品图如果包含真人、模特、手臂动作、手部位置、脸、发型、妆容、身体比例、背景、道具、拍摄角度或构图，这些都不能作为最终画面的人物形象、姿势和场景依据；只提取服饰本身的款式、廓形、颜色、图案、材质、开合、肩带、领口、袖长、下摆、裤脚、鞋型或帽型，并让服饰服从第一张参考图里的动作、手势、遮挡和裁切关系。"
                + "最终 prompt 必须明确写出画面四边裁到哪里，以及哪些身体部位、服饰部件、配饰、道具或背景区域是完整可见、局部可见或完全不可见；第一张参考图中完全不可见的内容不要写进最终画面描述，也不要让生图模型补全这些画外内容。"
                + f"参考图画面描述：{reference_description or '请直接根据第一张参考图写出具体画面描述。'}"
                + build_subject_hint_text(subject_hint)
                + f"用户补充要求：{user_prompt}"
                + "请输出最终图片本身的画面描述，不要输出任务说明。不能出现“需要、必须、参考图、商品图、保留、复刻、不要改变、最终 prompt”等指令口吻词。"
                + "必须把参考图中真实看见的场景和姿态具体写出来，例如更衣室镜前自拍、坐在矮凳上、浅色墙面和木质门框、腿部交叠方向、手机遮住脸部等；如果图中不是这些元素，就按实际图像写。"
                + "输出格式必须严格为：FINAL_PROMPT: 后面接一整段最终给生图模型使用的中文画面描述。"
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
        timings=settings.get("timings"),
        timing_label="kimi_apparel_final_prompt",
    )
    return extract_final_prompt_text(text) or build_apparel_final_fallback(
        subject_hint,
        user_prompt,
        reference_has_face,
        reference_description,
    )


def call_vision_model(
    model,
    instructions,
    content,
    temperature,
    max_output_tokens,
    timings=None,
    timing_label="vision_model",
):
    text, _ = call_vision_model_with_debug(
        model=model,
        instructions=instructions,
        content=content,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        timings=timings,
        timing_label=timing_label,
    )
    return text


def call_vision_model_with_debug(
    model,
    instructions,
    content,
    temperature,
    max_output_tokens,
    timings=None,
    timing_label="vision_model",
):
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
    started_at = time.monotonic()
    data = post_json(OPENROUTER_URL, payload)
    append_timing(timings, timing_label, model, started_at)
    return extract_response_text(data), data


def generate_image(prompt, settings, reference_images, localize_output=True):
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
        "modalities": ["image"],
        "stream": False,
        **build_image_config(settings["imageSize"]),
        **settings["extraBody"],
    }

    image_request_debug = build_image_request_debug(payload, reference_images)
    started_at = time.monotonic()
    data = post_json(OPENROUTER_URL, payload)
    append_timing(settings.get("timings"), "image_generation", settings["model"], started_at)
    value = extract_image_output(data)
    if not isinstance(value, str) or not value:
        raise Exception("生图成功，但没有在 OpenRouter 响应里拿到图片结果。")
    if localize_output:
        value = store_generated_image_if_needed(value)
    return value, image_request_debug


def append_timing(timings, label, model, started_at):
    if not isinstance(timings, list):
        return
    timings.append(
        {
            "label": label,
            "model": model,
            "elapsedMs": int(round((time.monotonic() - started_at) * 1000)),
        }
    )


def init_progress(settings, progress_id, generation_path):
    if not progress_id:
        return
    generation_path = normalize_generation_path(generation_path) or settings.get("generationPath") or ""
    steps = progress_steps_for_path(generation_path)
    if not steps:
        return
    if progress_id not in PROGRESS_JOBS:
        PROGRESS_JOB_ORDER.append(progress_id)
    PROGRESS_JOBS[progress_id] = {
        "ok": True,
        "id": progress_id,
        "status": "running",
        "generationPath": generation_path,
        "activeIndex": 0,
        "message": steps[0]["title"],
        "steps": steps,
        "updatedAt": time.time(),
    }
    while len(PROGRESS_JOB_ORDER) > MAX_PROGRESS_JOBS:
        stale_id = PROGRESS_JOB_ORDER.pop(0)
        PROGRESS_JOBS.pop(stale_id, None)


def set_progress(settings, active_index, message, status="running"):
    progress_id = settings.get("progressId")
    if not progress_id:
        return
    item = PROGRESS_JOBS.get(progress_id)
    if not item:
        init_progress(settings, progress_id, settings.get("generationPath"))
        item = PROGRESS_JOBS.get(progress_id)
    if not item:
        return
    steps = item.get("steps") or []
    if active_index == 999:
        active_index = max(0, len(steps) - 1)
    elif active_index is None:
        active_index = int(item.get("activeIndex") or 0)
    else:
        active_index = max(0, min(int(active_index), max(0, len(steps) - 1)))
    item.update(
        {
            "status": status,
            "activeIndex": active_index,
            "message": message,
            "updatedAt": time.time(),
        }
    )


def progress_steps_for_path(generation_path):
    if generation_path == "apparel":
        return [
            {
                "title": "分析参考图",
                "detail": "Kimi 读取小红书参考图，提取人物形象、场景、姿势和构图。",
                "progress": 25,
            },
            {
                "title": "融合服饰约束",
                "detail": "Kimi 写最终服饰换装 Prompt，商品图只提供服饰外观。",
                "progress": 55,
            },
            {
                "title": "生成最终图片",
                "detail": "最终 Prompt 返回后，参考图约束人物和场景，商品图只约束服饰。",
                "progress": 88,
            },
        ]
    if generation_path == "non_apparel":
        return [
            {
                "title": "生成复刻 Prompt",
                "detail": "Kimi 分析参考图的场景、机位、光线和商品摆放关系。",
                "progress": 35,
            },
            {
                "title": "生成最终图片",
                "detail": "Prompt 返回后，调用生图模型输出结果图。",
                "progress": 84,
            },
        ]
    return []


def store_generated_image_if_needed(value):
    if not isinstance(value, str) or not value.startswith("data:"):
        return value
    header, separator, encoded = value.partition(",")
    if not separator:
        return value
    content_type = header.split(";", 1)[0].replace("data:", "") or "image/png"
    try:
        raw = base64.b64decode(encoded.encode("ascii"))
    except Exception:
        return value
    image_id = f"{uuid.uuid4().hex}.png"
    GENERATED_IMAGES[image_id] = {
        "content_type": content_type,
        "raw": raw,
        "created_at": time.monotonic(),
    }
    GENERATED_IMAGE_ORDER.append(image_id)
    while len(GENERATED_IMAGE_ORDER) > MAX_GENERATED_IMAGES:
        stale_id = GENERATED_IMAGE_ORDER.pop(0)
        GENERATED_IMAGES.pop(stale_id, None)
    return f"http://127.0.0.1:{PORT}/generated/{image_id}"


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
    raw_body = json.dumps(payload).encode("utf-8")
    last_error = None
    for attempt in range(3):
        request = Request(
            url,
            data=raw_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "http://127.0.0.1:8787",
                "X-Title": "Commerce Creative Replicator",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            text = error.read().decode("utf-8", errors="ignore")
            raise Exception(format_openrouter_error(error.code, text))
        except (IncompleteRead, RemoteDisconnected, TimeoutError) as error:
            last_error = error
        except URLError as error:
            last_error = error
        if attempt < 2:
            time.sleep(1.5 * (attempt + 1))
    raise Exception(format_transient_openrouter_error(last_error))


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


def extract_reference_description_text(text):
    if not isinstance(text, str):
        return ""
    cleaned = strip_code_fences(text).strip()
    markers = (
        "REFERENCE_DESCRIPTION:",
        "REFERENCE_DESCRIPTION：",
        "参考图画面描述：",
        "参考图画面描述:",
        "画面描述：",
        "画面描述:",
    )
    for marker in markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[1].strip()
            break
    return strip_code_fences(cleaned).strip()


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
            "如果你继续用当前生图模型，建议先改成纯文生图；"
            "如果你要保留商品参考图和换装链路，建议换一个更适合 image-to-image 的生图模型。"
        )
    return f"OpenRouter 请求失败 ({status_code})：{detail}"


def format_transient_openrouter_error(error):
    if isinstance(error, IncompleteRead):
        return (
            "OpenRouter 响应读取中断，已自动重试但仍未完成。"
            f"最后一次只读取到 {len(error.partial or b'')} bytes。请稍后再试。"
        )
    if isinstance(error, URLError):
        return f"OpenRouter 网络连接不稳定，已自动重试但仍失败：{error.reason}"
    if error:
        return f"OpenRouter 网络连接不稳定，已自动重试但仍失败：{error}"
    return "OpenRouter 网络连接不稳定，已自动重试但仍失败。"


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


def build_apparel_final_fallback(
    subject_hint,
    user_prompt,
    reference_has_face,
    reference_description="",
):
    portrait_text = (
        "尽量沿用参考图里的脸、发型、体态、人物姿势、手势和裁切方式，"
        if reference_has_face
        else "沿用参考图里的人物姿态、身体朝向、手势、裁切和构图，"
    )
    subject_text = f"商品主体是{subject_hint}。" if subject_hint else "商品主体以商品图为准。"
    reference_text = (
        f"{reference_description}"
        if reference_description
        else (
            "一张真实服饰穿搭照片，人物处在参考图相同的场景、背景、机位、景别、姿态、裁切和光线关系中。"
        )
    )
    return (
        f"{reference_text}"
        f"{portrait_text}"
        "把用户上传的服饰自然穿在参考图人物对应部位，让领口、肩带、袖口、腰线、裙摆、裤脚等跟随参考图人物动作和遮挡关系，只替换服饰主体。商品图如果包含人物、脸、发型、身体、背景、道具或强动作，只取服饰外观，不取商品图人物形象和姿势。"
        f"{subject_text}"
        f"附加要求：{user_prompt}"
    )


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ProxyHandler)
    print(f"Proxy server listening on http://127.0.0.1:{PORT}")
    server.serve_forever()
