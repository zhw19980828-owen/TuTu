# -*- coding: utf-8 -*-

import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from http.client import IncompleteRead, RemoteDisconnected
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def read_local_secret(filename):
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return ""


PORT = int(os.environ.get("PORT", "8787"))
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "") or os.environ.get("ARK_API_KEY", "")
KIMI_API_KEY = (
    os.environ.get("MOONSHOT_API_KEY", "")
    or os.environ.get("KIMI_API_KEY", "")
    or read_local_secret(".kimi_key")
)
PROXY_TOKEN = os.environ.get("PROXY_TOKEN", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
DREAMINA_BIN = os.environ.get("DREAMINA_BIN", os.path.expanduser("~/.local/bin/dreamina"))
DREAMINA_SUPPORTED_RATIOS = {"1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9", "21:9"}
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPTH_GUIDE_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "depth_guide.py")
DEPTH_GUIDE_STRUCTURE = int(os.environ.get("AIC_DEPTH_STRUCTURE", "170"))
DEPTH_GUIDE_DETAIL = int(os.environ.get("AIC_DEPTH_DETAIL", "8"))
DEPTH_GUIDE_SMOOTHING = float(os.environ.get("AIC_DEPTH_SMOOTHING", "8"))
DEPTH_GUIDE_CONTRAST = float(os.environ.get("AIC_DEPTH_CONTRAST", "0.95"))
CANNY_LOW_THRESHOLD = 108
CANNY_HIGH_THRESHOLD = 120
CANNY_MAX_SIDE = 960
GENERATED_IMAGES = {}
GENERATED_IMAGE_ORDER = []
MAX_GENERATED_IMAGES = 20
PROGRESS_JOBS = {}
PROGRESS_JOB_ORDER = []
MAX_PROGRESS_JOBS = 50
APPAREL_FINAL_PROMPT_MIN_CHARS = 700
APPAREL_FINAL_PROMPT_MAX_CHARS = 900
APPAREL_IMAGE_PROMPT_MAX_CHARS = 2100

DEFAULTS = {
    "model": "dreamina/image2image:5.0Pro",
    "visionModel": "kimi-k2.6",
    "nonApparelPrompt": "你是一位真实商品摄影与非服饰商品复刻提示词专家。你会同时看到一张参考图和一张商品图。你的任务是把两张图转成一段最终可以直接交给生图模型的中文 prompt，让生图模型生成一张“用户商品主体正确，但摄影语言和参考图高度一致”的真实拍摄效果图片。参考图只负责提供画面模板，你必须像摄影师复盘机位一样，准确识别并继承参考图里的画幅比例、景别、镜头焦段感、相机高度、俯拍/平拍/仰拍程度、镜头向左或向右的水平偏转、画面近端和远端的位置、透视收缩方向、水平线或盒边/桌边的斜率、主体在画面中的位置和占比、主体朝向、主体长轴方向、主体倾斜角度、主体俯仰角度、主体与承载面的接触点、主体是否平放/斜放/竖立/悬浮/倚靠/嵌入卡槽/半露出/叠放/被托起、多个物体之间的前后层级和遮挡关系、主体边缘与画面边界的距离、裁切方式、场景地点、背景元素、承载面材质、时间段、主光方向、光线质感、色温、曝光方式、色彩氛围、景深关系、主体与背景的光影关系，以及画面中原本存在的真实陈列和生活痕迹。最终 prompt 必须明确写出相机视角：例如低角度贴近桌面、从正前方略偏右看向左后方、从上方约 30 度俯视、镜头沿盒子对角线方向拍摄、近处盒沿在画面底部横向穿过、远处盒盖向右上方退去等；不要只写“微距特写、低角度俯拍”这种笼统词。最终 prompt 还必须用具体方位写清楚新商品的摆放姿势：它位于画面哪个区域，长轴或开口朝向哪里，正面/侧面/顶部露出多少，是否贴着、压在、嵌入、悬在、靠着或插入某个承载物，接触点在哪里，阴影落向哪里；如果参考图中原主体有专用托槽、盒垫、支架、桌面边缘、布面褶皱或局部遮挡，必须让新商品占用同一个空间关系。商品图会直接作为后续生图模型的唯一商品参考图，因此最终 prompt 里不要详细描述商品本身的颜色、材质、品牌、logo、文字、纹理、形状、结构、链节、刻字、装饰、边缘、工艺、尺寸等视觉细节，这些交给图像参考通道。你只能极简点明商品品类和融入方式，例如“一枚戒指嵌在盒垫中央的卡槽里，弧面横向朝向镜头，镜头从盒子前下方略偏右的位置沿盒内对角线看过去”“一个包斜靠在桌面右后方”“一瓶香水竖立在原主体落点”。最终输出必须是一整段中文 prompt，直接描述最终生成图片本身：保留参考图的场景、构图、镜头角度、主体摆放姿态、主体朝向、主体落点、前后层级、光影、景别、主体大小和整体气质，画面必须像真实相机拍摄，不要出现 CGI、3D 渲染、插画、海报合成或过度广告精修感。不要输出解释、标题、分析过程、分点或 JSON。",
    "apparelFinalPrompt": "你是一位真实服饰摄影、穿搭换装与参考图复刻提示词专家。你会看到小红书参考图和用户上传的服饰商品图。你的核心任务是先把小红书参考图转换成具体画面文字，再把用户商品服饰融入这段画面，输出一整段最终成图 prompt。最终 prompt 必须直接描述最终图片本身，像在描述一张已经拍出来的照片，而不是描述任务规则。参考图负责提供完整画面模板和人物模板，你必须具体写出参考图中真实可见的内容：人物形象气质、发型、脸部可见状态、视线、头部倾斜、身体朝向、动作姿态、手臂和手的位置、场景地点、室内/室外环境、背景墙面/镜子/门框/家具/地面/道具、时间段、光线方向和质感、相机或手机拍摄方式、镜面自拍关系、机位高度、俯拍/平拍/仰拍程度、镜头向左或向右的水平偏转、景别、人物在画面中的位置和占比、人物主要位于画面上部/中部/下部还是贯穿全画面、人物头顶/脚底/左右身体边缘距离画面边界的大致比例、人物高度占画面高度的大致比例、画面上下左右留白和主要背景区域的大致比例、画面四边分别裁到人物/服饰/道具哪里、哪些身体部位和服饰部件完整可见/局部可见/完全不可见、人物坐姿/站姿/蹲姿、可见四肢和双脚的方向、肩颈和躯干朝向、手机/包/椅子/凳子等道具与人物的接触关系，以及画面近处和远处的空间层级。最终 prompt 必须保持参考图的人物形象方向、姿势、手势、垂直位置、主体大小、上下留白、左右留白、边界距离和可见范围，不要为了突出服装而自动放大人物、缩小人物、居中人物、移动镜头、扩展画幅、补全身体、补全道具或改变画面重心。无论参考图是不展示脚、不展示腿、不展示下半身、不展示躯干、不展示头部、只露出局部身体、只露出局部商品还是裁掉某个道具，最终 prompt 都必须写成同样的局部可见范围；参考图中完全不可见的身体部位、服饰部件、配饰、道具和背景区域不能出现在最终 prompt 中。商品图只负责提供要替换上身或穿戴的服饰主体本身，最终 prompt 只需要说明商品服饰穿在参考图人物对应部位，并描述它如何贴合参考图人物姿态、肩带/领口/腰线/裙摆/裤脚/袖口与动作和遮挡关系；商品外观细节以商品图为准，不要编造商品图里没有的设计。参考图中只有与商品覆盖区域重叠的旧衣结构需要清除；不在替换区域内的鞋帽、包袋、首饰和场景道具不能一律删除。凡是被手握持、承托或倚靠，遮挡人物主体，或明显决定轮廓与构图的大型道具，都必须保留其品类、尺寸、位置、遮挡和接触关系。参考图旧衣的颜色、图案、logo、文字、装饰、面料和款式不得残留，最终被替换区域的可见服饰外观必须来自商品图。如果商品图中也出现真人、模特、手臂、脸、身体、发型、妆容、背景、道具或强动作，它们都不是人物模板和画面模板，不能写进最终 prompt，也不能覆盖参考图的人物形象、脸、发型、体态、人物姿势、手部位置、身体朝向、场景、拍摄角度、构图和可见范围；只能从商品图提取服饰本身的款式、廓形、颜色、图案、材质、开合、肩带、领口、袖长、下摆、裤脚、鞋型或帽型等穿着外观。严禁输出“需要保留、必须复刻、参考图负责、商品图负责、不要改变、最终 prompt 必须”等任务说明式句子；严禁只写“保留参考图的场景和姿态”这种空话。你应该输出类似“一张真实手机镜前自拍照片，一名与参考图性别呈现一致的成年人物坐在更衣室浅色墙面前的矮凳上……”这样的具体画面描述。不要擅自改性别、人数、景别、主体大小、坐站关系、镜面自拍方式、人物在画面中的垂直位置、上下留白比例、可见范围或主要道具。画面必须像真实手机或相机拍摄，不要出现 CGI、3D 渲染、插画、海报合成或过度广告精修感。不要输出解释、标题、分点或 JSON，只输出一整段最终 prompt。",
    "defaultUserPrompt": "",
    "imageSize": "1:1",
    "responseDataPath": "",
    "extraBody": {"dreaminaResolutionType": "1k"},
}

NON_APPAREL_HUMAN_CARRIER_RULES = (
    "非服装商品可以出现在有人物的画面中，出现人物不等于换装。"
    "若参考图含人物，人物只提供场景中的承载关系：必须保持参考图人物的景别、画面位置、身体朝向、动作、手部位置、四边裁切和可见范围。"
    "先判断目标商品的真实承载方式是耳部佩戴、颈部佩戴、腕部佩戴、肩背、斜挎、手持、握持、放置、倚靠或其他方式；"
    "新商品只替换参考图旧商品所在区域，并保持它与耳垂、颈部、手腕、肩背、手掌或承载面的接触点、遮挡层级、重力方向、相对尺度和朝向。"
    "不得因为画面有人而改成人物换装，也不得继承商品图模特的脸、身体、动作、服饰搭配或背景。"
)

APPAREL_PROMPT_GUARDRAILS = (
    "补充硬规则：第二张商品图里只有用户真正要替换到人物身上的服饰主体可以进入最终 prompt。"
    "以下参考图旧服饰排除规则优先级最高，覆盖此前或用户自定义 SP 中任何保留参考图非目标服饰外观、服饰部件可见性、搭配细节或旧衣结构的要求。"
    "如果用户填写了商品主体说明，必须以该说明锁定单品；如果没有说明，则只选第二张图中最主要、最居中、最像商品展示主体的一件服饰单品。"
    "如果第二张商品图是穿搭拆解图、拼贴图、红框标注图或带品牌标注的搭配图，必须优先识别红框/连线/局部放大框所指向的服饰商品，尤其是画面中心人物身上被重点标注的上衣、外套、裤装、裙装或鞋帽；这些标注框和品牌文字本身不能进入最终 prompt。"
    "如果商品主体说明明确写了套装、组合或同时列出多件服饰，则这些被点名的单品共同构成本次商品主体，必须逐件进入最终 prompt；不得再退化为只选择其中最居中的一件。"
    "必须先判断商品覆盖的身体区域，只替换与商品区域重叠的原服饰：上装只替换上身，裤装或裙装只替换下身，连衣裙或连体服才同时替换上下身，鞋帽与配饰也只替换各自区域。"
    "参考图中的旧服饰只用于判断身体哪些区域被覆盖、人物动作、遮挡、承重点和画面裁切；不得描述或继承其品类、颜色、材质、长度、廓形、领口、肩带、袖型、裁片、开口、图案、文字、Logo 或装饰。"
    "输出前必须自检：商品覆盖区域内不得残留参考图旧商品结构或外观；商品覆盖区域外若需要维持身体覆盖连续性，只能使用无品牌、无图案、结构最简单且低存在感的中性补全，不能复原参考图旧服饰。"
    "第二张商品图中的背景、拍摄场景、墙面、商场、街道、文字标识、模特脸、发型、手势、身体比例、鞋帽、包袋、首饰、腰带、袜子、裤子、裙子、外套或其他搭配件默认全部是干扰，除非它们就是用户指定的商品主体。"
    "不能把第二张商品图里的整套穿搭照搬进最终 prompt；只能提取被锁定单品的款式、廓形、颜色、面料、领口、袖口、下摆、开合、图案等必要外观。"
    "第一张小红书参考图里的帽子、包袋、鞋子、首饰等若不是本次替换商品，但明显影响人物轮廓、动作接触或构图识别，应按参考图保留；它们不能反过来改变新商品结构。"
    "如果参考图中的手正在拿包、帽子、鞋、饰品等非目标物品，必须保留手与该物品的接触点、物品落点和遮挡关系，避免动作因删除道具而改变。"
    "任何占画面宽或高约10%以上、遮挡躯干，或同时与两只手发生接触的非目标物品，都属于标志性构图道具；最终 prompt 必须量化它的外接框、中心、相对人物尺寸和遮挡范围，禁止缩小成普通小配饰、换品类或删除。"
    "如果第一张参考图是多宫格、拼图或对比图，最终 prompt 应明确描述它是一张同样布局的拼图，并分别复刻各分图的构图、姿势和裁切；不要把多个分图混成单张照片。"
)

PRODUCT_STRUCTURE_GUARDRAILS = (
    "商品结构真实性是最高优先级硬约束，覆盖前文任何‘不描述商品结构’的要求。"
    "必须先把商品图中的目标单品逐件分开盘点；拼图、套装图或上下装组合图中的每件单品都要独立识别，绝不能把不同单品的边缘、文字、留白或人体部位融合成一种新结构。"
    "每件商品都必须按固定槽位核对真实可见的结构：品类与件数、领口或腰头、肩部连接点及肩带数量、袖子与袖窿、前后片覆盖范围、门襟或开合、口袋与开孔、下摆或裤脚、拼接线和标识位置。"
    "结构槽位只允许写商品图中直接可见且能沿轮廓连续追踪的内容；被遮挡、像素不足或无法确认时必须按‘不可确认’处理并保持最简单连续面料，禁止按常见款式、人体露肤、文字排版或参考图旧衣进行猜测补全。"
    "必须先根据商品图盘点商品真实存在的结构部件、数量、连接方式、覆盖范围、开口位置和边缘轮廓，并将最具辨识度的结构明确写入最终 prompt。"
    "参考图中被替换旧商品的结构只能用于判断人体姿势、占位、遮挡和裁切，不得保留、拼接、混合或移植到新商品上。"
    "商品覆盖区域按身体区域而不是按单件衣物名称判断：替换上装时，原图上身区域内的旧上衣、旧内搭、背心、吊带、胸衣肩带、旧领口和旧袖片都属于被替换结构，必须一起清除；它们不得以叠穿、露肩、断领或额外肩带形式残留。"
    "商品图中不存在的部件绝对不得出现，包括但不限于吊带、肩带、领子、翻领、袖子、口袋、开叉、镂空、抽绳、纽扣、拉链、装饰带、额外开口或拼接层。"
    "任何绕颈、后颈系带、蝴蝶结、交叉肩带、额外内搭或独立开孔，都必须同时看到清晰连接起点、连续带体和明确终点才允许写入；只看到肩部边缘、颈部留白或模糊细线时一律不得推断存在。"
    "必须把商品真实开口整理成白名单：只允许商品图能直接确认的领口、袖窿、门襟、口袋、开衩或镂空存在；人体皮肤从领口或袖窿露出不等于商品另有开孔。"
    "商品图未确认胸前开洞、背部开洞、腰侧开洞或独立镂空时，最终 prompt 必须明确保持对应面料连续完整，不得根据参考图旧衣露肤区域、人体曲线或姿势创造水滴孔、U形孔、断裂领口或额外肩带。"
    "如果商品是服饰，必须精确写出领口类型、肩部覆盖范围、肩线与袖子的连接、袖长、门襟或开合方式、下摆和可见内外层关系；"
    "例如商品是有完整肩线和短袖的翻领上衣，就不得生成露肩、斜肩、无袖、吊带、额外肩带或断开的领口结构。"
    "如果商品是上装，它必须始终是边界清楚的独立上衣，衣摆与下装在腰胯区域形成明确分界，不得把上衣向下延伸成连衣裙、连体衣或与参考图旧裙摆融为一体。"
    "新商品只覆盖自身对应的身体区域。画内其他身体区域只继承有无独立覆盖、动作、遮挡和裁切关系，不继承参考图旧服饰外观；需要补全时统一使用无品牌、无图案、结构最简单且低存在感的中性搭配。"
    "若商品主体是包含上装与下装的套装，必须同时清空并替换参考图上身和下身的旧服饰，逐件写清新上装与新下装；不得残留参考图原裤子、原裙子、原腰线、原袜口或其他落在商品覆盖区域内的旧结构。"
    "若商品图中的裤装是覆盖脚踝或接近鞋面的全长长裤，必须保持商品原有裤长和裤脚垂落方式；参考图袜子一律不继承，不得为了露出旧袜子而卷起、缩短、束紧或堆叠新裤脚。只有用户明确把袜子列为商品主体时才允许生成袜子。"
    "鞋袜、帽子、包袋、首饰等商品覆盖区域外的搭配件要先做兼容判断，而不是机械保留：仍在画内可见且与新商品覆盖范围不冲突时按参考图保留；若新长裤或长裙已遮住脚踝与袜口，原袜子必须删除。只有不承担动作、遮挡或构图作用的低存在感配饰在明显冲突时才可删除或简化；被手握持、托举、倚靠，遮挡躯干，或占画面宽高约10%以上的标志性道具无论风格是否协调都必须保留，不能缩小、换品类或删除。"
    "人物动作与商品结构冲突时，优先保持商品结构正确，只对局部布料做符合动作的自然褶皱和遮挡，不得改造商品。"
    "商品图中同一个品牌标签、logo、文字贴标、刺绣章或独立徽标在成图中只能出现一次，必须保持原数量、原相对位置和原尺寸关系；禁止复制、堆叠或在领口与胸前重复生成。"
)

SCENE_REPLICATION_GUARDRAILS = (
    "通用画面规则：最终输出是对一张已经拍成的真实照片的客观描述，不是任务指令。"
    "必须高密度锁定画幅、景别、镜头高度、俯仰角、水平偏转、透视方向、主体中心落点、主体占比、四边裁切、留白、遮挡、接触点、背景层级、主光方向和景深。"
    "拍摄设备感与相机姿态是两套独立信息：iPhone、CCD、消费级相机或生活快照都不能被默认解释为平视。必须按参考图单独锁定相机相对人物高度、俯拍或仰拍角度、左右偏转、画面顺逆时针滚转和拍摄距离；任何明显俯拍、仰拍或斜拍都不得归一化成端正平视。"
    "每张参考图都必须估计35mm等效焦距范围并写入最终 prompt；焦距判断必须来自近大远小、边缘拉伸、空间纵深和背景压缩，而不是设备名称。20至24mm广角、26至28mm手机主摄、35至40mm标准广角和50至85mm中长焦必须明确区分，不得统一回退成中长焦人像。"
    "俯仰方向必须先在向上仰拍、水平、向下俯拍三者中单选，再估计角度；不得先看人物姿势后反推镜头。必须分别检查建筑垂直线与消失点、承载面顶面或底面可见量、人物头肩躯干和腿部的近大远小，并写出结论。"
    "俯拍或仰拍都必须至少由两类彼此独立的透视证据共同确认。明显看到头顶平面、近侧上半身明确放大、建筑线向下汇聚、承载面顶面大量暴露可支持俯拍；相机光心低于人物胸口、下巴或手臂底面更可见、近侧腿脚或座椅下沿更突出、空间线条向上收缩可支持仰拍。单独看到地面、完整头顶、楼梯踏面、斜坡、人物前倾、低头、弯腰、坐姿，或人物头部大于被裁切的下肢，都不能证明俯拍。身体姿态与相机姿态必须分开。证据不足时只能写水平机位、0度，不得默认向下0至3度。"
    "最终 prompt 的第一句必须先写构图签名：横竖画幅、景别、人物外接框宽高占比、中心落点、四侧留白和上下边缘裁到哪里；先锁定人物在整张画布中的尺度，再写脸、服饰和背景。人物外接框百分比是目标值而不是可忽略的参考值，宽高误差均不得超过约5个百分点。"
    "景别复刻必须采用‘先搭完整画布，再放入人物’的顺序：先按参考图建立全部背景负空间和地面、海面、墙面、家具等大区域，再把人物缩放并放到结构化外接框内；禁止先生成脸、胸部或商品近景后再向外补背景。"
    "当参考图顶部留白达到约15%、人物高度不超过约82%，或景别属于环境人像、全身、近全身、七分身时，人物必须被视为背景中的较小主体而不是填满画面的主角；宁可牺牲脸部和商品的近景细节，也不能推进镜头。"
    "如果参考图属于环境人像、近全身、七分身或全身，第一句还必须明确写‘不是半身照、不是胸像、不是人物特写’，并写出必须保留的背景负空间；不得因人脸或商品细节丰富而把人物推进镜头。"
    "四边裁切的优先级高于人脸完整度和商品完整度。必须先逐边检查参考图上、下、左、右边缘穿过人物或主体的具体位置，再在最终 prompt 中明确写出。"
    "如果参考图的头顶、额头、眼睛、鼻嘴、下巴、整张脸、腿、脚或商品部分在画外，最终图必须保持同样的不可见范围；不得为了生成完整人脸、完整人体或完整商品而拉远镜头、下移人物、扩展画幅或补出画外内容。"
    "人物动作必须按参考图的身体轴线和关节空间关系复刻，不能只写‘保持原姿势’。最终 prompt 必须具体写出躯干是前倾或后仰、向哪侧倾斜、绕垂直轴向哪侧旋转、肩线哪边高哪边低及斜率、髋部与肩部的扭转关系，以及头部相对躯干的偏转。"
    "对每条可见手臂必须分别写出是画面左侧还是右侧手臂、上臂从肩部指向哪个方向、肘部大致弯曲程度、前臂指向、手是可见还是伸出画外，以及手与手机、镜头或道具的关系。"
    "所有左右方向以最终画面的画面坐标为唯一执行坐标，只允许写画面左侧或画面右侧。禁止出现人物解剖左手、右手、左腿、右腿等第二套左右标签，也禁止括号补充人物解剖左右；禁止把参考动作水平镜像。头部侧倾、躯干侧倾、持手机手、托脸手、支撑手、睁闭眼和道具都必须明确落在画面哪一侧。"
            "判断脸部朝向时必须做画面坐标校验：先估计双眼中点或脸框中心的 x 坐标，再比较鼻尖 x 坐标，并把两个0至1000坐标写入 appearanceLock.directionAudit；鼻尖位于中心左侧才写鼻尖朝画面左侧，位于中心右侧才写鼻尖朝画面右侧。不得凭人物自身左右、发缝、视线或语义猜测朝向。身体侧身方向也必须同时用近侧肩、远侧肩遮挡和鼻尖坐标交叉验证；证据冲突时只写可直接确认的坐标关系，不得猜测。"
    "每张有人物的参考图必须提取至少两条不可互换的画面方向锚点，例如画面左侧闭眼、画面右侧手持包、画面左侧肩更靠近镜头；最终图逐条保持这些锚点，任何一条都不得左右交换。"
    "如果参考图是近距离手持自拍、斜线构图、身体侧倾、单臂伸出画外或非对称姿势，最终图不得自动改成正面站立、躯干竖直、双肩水平、双臂对称、手放身侧、模特展示或标准站姿。"
    "参考图为三分之二侧身或近侧面时，必须额外锁定画面中可见的脸部比例、鼻尖朝向、近侧肩髋、远侧肩髋被遮挡程度以及胸腹侧轮廓；最终 prompt 必须直接写‘保持三分之二侧身/近侧面，禁止转成正面’，不得只写朝向角度后又用正面展示、面对镜头等词覆盖。"
    "换脸只改变人物身份，不等于更换身体。参考图中可见的肤色明度与冷暖、肩宽、胸部相对肩宽与腰宽的前向体积、胸腰比、腰胯宽度、躯干厚度、可见腿长相对躯干的比例、四肢粗细和整体体型轮廓仍属于画面模板，必须保留，不能统一修成纤瘦、平胸、短腿、白皙或标准商业模特体型。"
    "体型只按可见几何关系客观记录，不使用性感、丰满、完美身材等评价词；若参考图胸部体积突出、腰部收窄或可见腿部修长，最终人物必须保持同等级的胸部前向投影、胸腰差和腿身比，服饰只在商品原有覆盖范围和连续面料内随人体自然起伏，不能把身体压平、加宽腰部或缩短双腿。商品结构优先级始终高于体型表现：不得为了突出胸部而降低或扩大领口、拉开门襟、移动肩带锚点、缩窄胸前覆盖、增加露肤或事业线，也不得把高领、圆领、方领或完整胸前面料改成深V、低领、抹胸或文胸式结构。"
    "参考分析中的视觉核心特征属于画面辨识度最高的非身份信息，必须在最终 prompt 前三句内明确出现。若核心特征包含明显胸部前向体积、显著胸腰差、修长腿身比、成熟感或特定身体轴线，不能降级成‘匀称、纤细、标准身材’等平均化描述。"
    "仅当结构化参考分析明确给出 appearanceLock.bustLevel=prominent、bustConfidence=high，且 bustEvidence 至少包含两条彼此独立的身体轮廓证据时，最终 prompt 才必须直接写‘一名25至30岁的成年女性拥有明显丰满的大胸，胸部轮廓饱满突出，胸腰差明显’，不要解释衣料受力，也不要改写成胸部前向体积等分析术语。俯拍近大远小、低领露肤、紧身或宽松衣料、褶皱、单侧侧身轮廓、手臂挤压和裁切放大都不能作为大胸证据；置信度不足或 bustLevel=non_prominent/uncertain 时禁止写大胸、丰满突出或沙漏夸大。"
    "若参考图确实可见事业线，并且商品本身清楚具有足以自然露出该区域的低领或开放领口，才可写‘可见与商品领口自然允许范围一致的事业线’，露肤范围不得超过商品结构；商品结构不支持时只保留体型，不写事业线，不降低领口，不增加开口、吊带或其他结构。"
    "换脸时只改变可识别身份，不改变人物的成人年龄段、视觉成熟度、表情强度、视线关系、嘴部微表情状态和整体角色感；不得把成熟人物自动改成幼态、甜妹、学生感或标准网红脸，也不得反向增龄。"
    "嘴部微表情必须作为非身份硬锁独立记录和执行：写清上下唇是完全闭合、轻触、微张还是明显张开，是否存在唇间缝隙，牙齿或舌头是否可见，画面左侧与右侧嘴角分别上扬、水平、下压或收紧，以及下颌是放松还是轻微绷紧。原图闭唇时禁止自动改成微张嘴、露齿笑、嘟嘴或明显微笑；原图微张时也不得自动闭合。只继承开合、受力和方向，不继承具体唇形、厚度、轮廓或身份特征。"
    "动作复刻不仅要写关节方向，还必须写清手与脸、头发、腰胯、手机、桌面或其他可见物体的接触点，以及哪条肢体在前、哪条在后；不得把交叉、支撑、遮挡或伸出画外的动作改成相邻但不接触的姿势。"
    "人物与承载面的几何关系必须逐段记录：臀、背、左右大腿、左右小腿、左右脚和支撑手分别是压在、贴靠、悬空、垂下、伸出画外还是被遮挡；不得把原本悬空或垂下的腿放到台面上，也不得把原本平放、交叠或由台面承托的腿改成落地、屈膝站立或标准坐姿。"
    "人物姿态类别和承重关系是不可改写的硬约束：站立、坐姿、跪姿、蹲姿、躺姿不得相互替换；坐姿必须保留臀部与原承载面的接触、腿部弯曲及可见支撑点，不能改成站立或悬空。"
    "头部俯仰、左右转动和侧倾必须停留在参考图实际可见范围内，并保持参考图中仍可见的五官数量；不得把轻微抬头夸张成极端后仰、把自然颈部拉伸成不符合人体结构的角度，或让原本可见的眼睛、鼻嘴和脸部整体消失。"
    "如果参考图中某只眼睛可见，最终图必须生成该眼完整、自然且解剖正确的眼球、眼睑和眼周结构；闭眼或眯眼要表现为完整闭合眼睑，不能变成空白、融化、模糊斑块或缺失五官。只有被画面边缘、头发、手、手机或其他实物真实遮挡的五官才可以不可见。"
    "色彩复刻是与构图同等重要的硬约束。最终 prompt 必须具体写出全局白平衡偏冷或偏暖、主要色相偏移、色温与色调关系、饱和度、对比度、黑位深浅、高光是柔和滚降还是明显溢出、阴影偏色、肤色明度和背景颜色的相对关系，以及数码直出、手机 HDR、直闪、胶片或低对比柔化等真实可见的成像质感。"
    "颜色不能只用相对词。最终 prompt 必须同时写绝对色彩锚点：背景究竟是中性灰、蓝灰、青灰、偏绿灰、米黄、暖棕或其他可辨认颜色，人物肤色究竟是冷粉白、中性米白、暖黄或其他基础色，并明确一个禁止出现的错误偏色。中性冷灰不得被放大成蓝色或青色，轻微偏暖不得被放大成橙黄滤镜；但参考图中若墙面、阴影、中性色与肤色共同呈现可见的冷绿、暖红或其他综合色偏，则必须保留其方向和强度，不能自动校正成中性。"
    "判断全局色调时必须按画面面积加权：先看占比最大的墙面、天空、海面、地面或绿植，再用白墙、灰墙、眼白等近中性色校验白平衡；人物皮肤、木桌、阳光斑或单个暖色物体不能代表整张图。若综合色偏只达到轻微程度，最终 prompt 必须写‘整体近中性、仅局部受光略暖/略冷’，禁止写‘全局暖黄偏色’或给整图叠黄色滤镜。"
    "大面积环境区域的固有色必须与全局白平衡分开锁定。参考图出现天空、海面/湖面、地面、墙体、建筑或大面积绿植时，appearanceLock.environmentColorZones 必须逐区记录其画面位置和占比、具体色相、明度、饱和度、区域内部渐变，以及与相邻区域的颜色关系。天空尤其要写清从画面顶部到地平线的颜色变化、云层颜色、太阳或晚霞所在方位和暖色光带范围；水面还要写清它反射天空后的主色和暖冷分区。不得把橙金、粉橙、紫红或深蓝暮色天空概括成‘自然天空’，也不得把黄昏、日落、蓝调时刻或阴天自动改成普通蓝天、灰白天空或其他时间段。"
    "中性色校验必须读取它在照片中的实际像素颜色，而不是因为物体语义上是白墙、灰墙、白栏杆或眼白就默认它中性；若多个白灰黑锚点、皮肤中间调和阴影同时呈同方向的黄绿、暖红、冷绿或蓝灰偏移，这就是需要复刻的相机白平衡或综合色偏。尤其是早期CCD、低动态范围、轻微雾化或自动白平衡漂移的照片，禁止自动校正成现代手机的干净中性色。"
    "场景白平衡与面部基础肤色必须分开描述，不能为了复制暖墙、夕阳、木色或绿植反光而给整张脸叠统一黄色滤镜。非直闪环境中，除非参考图面部本身明确呈黄褐或橄榄色，面部基础肤色保持自然中性并带轻微血色，眼白和牙齿不发黄；暖环境光只允许在受光面、边缘光和阴影反射中局部出现，不能把鼻梁、面中和下颌全部染成橙黄。"
    "遇到暗环境直闪照片，必须使用‘采用昏暗环境用闪光灯拍摄的效果，构图似普通 iPhone 随手拍的视角’这一摄影语义，并继续写清闪光灯接近镜头轴线、人物或近景被瞬间照亮、皮肤和面料出现局部镜面高光、面部阴影被压平、光线快速衰减而远处背景更暗，以及环境灯仍可见的关系；不能改成均匀柔光或棚拍补光。没有暗环境直闪证据时禁止套用这句话。"
    "闪光灯采用严格准入而不是默认补光解释。窗户、玻璃外景、天空、室外绿植、窗边大面积柔和渐变、人物与背景共享同方向受光、自然投影或阳光斑都属于日光证据；只要这些证据能够解释人物高光，就优先判为 diffuse_daylight、direct_sun 或 mixed，不能因为皮肤较白、人物比背景亮、背景偏暗或面部阴影较浅而写闪光灯。"
    "遇到直射阳光，必须描述阳光来自哪一侧、阴影边缘软硬、皮肤和衣物上的高光斑块、亮暗反差及背景受光差异；不能只写‘自然光充足’。"
    "只有闪光置信度为 high，且至少出现三类彼此独立的闪光证据时才允许写闪光灯；其中必须包含一项闪光专属锚点：人物轮廓或鼻颌后方紧贴镜头轴的硬影，或‘近景快速衰减+正面小面积瞬时镜面反光’同时出现。皮肤白、眼神光、人物较亮、背景较暗、黑墙、阴影浅、正面均匀受光均不是闪光专属证据。证据不足或日光与环境光也能解释时一律按无闪光灯处理，并明确禁止近轴直闪、填充闪光、贴轴硬影或把人物整体打亮。"
    "背景主色必须按参考图记录其色相、明度、饱和度及相对人物的冷暖和亮暗关系，不得自动中和、提亮或换成更干净的商业背景色。"
    "暗色真实场景不能被简化为纯黑无缝背景：只要仍能看到墙面颗粒、接缝、划痕、风化、栏杆、锈迹、门窗、地面交界或环境灯，就必须逐项保留其低对比材质与空间层级，并明确不是摄影棚黑幕、无缝纸或纯色棚拍背景；欠曝只降低细节对比，不能删除环境结构。"
    "对比度与色温分开锁定。必须记录黑位深浅、阴影是否抬起、中间调明暗、高光是否柔和滚降或溢出、明暗跨度是低/中/高；参考图是低对比、灰阶柔和或阴影有细节时，禁止生成深黑硬阴影、过亮皮肤和商业人像式高反差。"
    "真实拍摄感必须拆成可观察的成像特征：保留参考图对应的镜头透视、边缘清晰度变化、轻微传感器噪点或压缩痕迹、高光滚降或局部溢出、阴影细节和景深过渡；皮肤要有自然毛孔、细小纹理、绒毛、局部血色和不均匀反光，禁止蜡像皮肤、瓷娃娃脸、过度磨皮、过分对称五官、均匀塑料质感、虚假的全画面锐利或影棚级完美布光。"
    "日常照片的人脸与皮肤必须保持自然半哑光：额头、鼻梁、面颊只能在符合光源的位置出现有限高光，不能整张脸均匀油亮、发黄发橙或像涂蜡；头发、皮肤、墙面和衣物的锐度与纹理不能同样完美，禁止生成式过锐、过度平滑渐变和商业人像式精修。"
    "如果参考图呈手机日常快照，最终 prompt 必须明确写‘普通 iPhone 原相机实拍的日常生活快照，画面随性，非摆拍、非精心构图或打光’，并保留与参考图一致的非均匀光线、自动曝光、局部白平衡波动、边缘数码锐化、压缩或轻微运动模糊。"
    "只有结构化分析给出至少两条可见 CCD 证据时，才把设备感明确写成‘早期老旧 CCD 或消费级数码相机的生活抓拍质感’，并按证据补充有限动态范围、轻微过曝或高光生硬截断、暗部彩色噪点、低像素压缩、偏硬数码锐化、轻微色偏或直闪衰减；不得把所有生活照都泛化成 CCD，也不得把 CCD 写成复古滤镜、胶片颗粒或专业棚拍。"
    "外景真实感必须来自物理层次而非‘高清写实’标签：远景对比度随空气距离自然下降，天空、地面和绿植存在不规则色差与受光差，叶片不能重复复制或统一荧光绿，阴影遵循同一主光方向并包含环境反射，发丝和衣摆只在参考图有风时自然扰动；不得自动添加大光圈虚化、青橙电影调色、均匀皮肤补光或过度通透的广告滤镜。"
    "禁止在最终 prompt 中加入 8K、4K、超高清、极致细节、大师杰作、电影级、视觉冲击、高级感、完美脸、完美身材、专业级打光等会把日常照片推成 AI 写真的质量堆词，除非这些特征就是参考图中可直接观察到的拍摄形式。"
    "真实感不等于随意添加污点或噪声，只能复刻参考图中实际可见或与其拍摄设备一致的自然瑕疵；如果参考图本身清晰干净，也要保持真实皮肤、自然光学层次和非生成式的细节分布。"
    "不能只写‘温暖色调’、‘清新感’、‘高级感’或‘真实质感’这类空泛词；必须用可观察的色彩、明暗和层次关系表达。"
    "只写画面内真实可见的内容；不得补全画外的身体、商品部件、道具或背景，不得为了突出商品而改变构图重心。"
    "不主动改造场景、增加道具、换地点、换时间或升级成影棚大片；生成模型只可在纹理、光影边缘和局部细节上自然产生差异。"
    "参考图中的轮播圆点、进度条、页码、播放控件、状态栏、应用水印、截图文字、白色画布、边框和上下黑白留边都属于查看器或截图界面，不属于被拍摄场景；分析、最终 prompt 和成图必须全部忽略，绝不能作为生活快照瑕疵复制。"
    "不要出现‘符合电商投放’、‘高级商业感’、‘宣传海报’、‘爆款’或其他营销结论，除非画面本身确实如此。"
)

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

            if self.path == "/detect-faces":
                result = detect_faces_endpoint(body)
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
        if not KIMI_API_KEY:
            error = Exception("Kimi API Key 缺失，请在项目根目录写入 .kimi_key。")
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


def detect_faces_endpoint(body):
    product_image_data_url = body.get("productImageDataUrl", "")
    if not product_image_data_url:
        error = Exception("productImageDataUrl is required.")
        error.status_code = 400
        raise error

    settings = build_settings(body)
    product_data_url = normalize_data_url(product_image_data_url)
    faces = detect_faces_with_vision(product_data_url, settings)
    return {"faces": faces}


def replicate(body):
    image_url = body.get("imageUrl", "")
    product_image_data_urls = body.get("productImageDataUrls")
    if not isinstance(product_image_data_urls, list):
        product_image_data_urls = []
    product_image_data_urls = [
        item for item in product_image_data_urls if isinstance(item, str) and item.strip()
    ]
    product_image_data_url = body.get("productImageDataUrl", "")
    if not product_image_data_urls and product_image_data_url:
        product_image_data_urls = [product_image_data_url]
    if not image_url:
        error = Exception("imageUrl is required.")
        error.status_code = 400
        raise error
    if not product_image_data_urls:
        error = Exception("productImageDataUrls is required.")
        error.status_code = 400
        raise error

    settings = build_settings(body)
    init_progress(settings, body.get("progressId"), body.get("generationPath"))
    reference_data_url = convert_image_url_to_data_url(image_url)
    supplied_guide = body.get("compositionGuideDataUrl")
    if isinstance(supplied_guide, str) and supplied_guide.strip():
        settings["compositionGuideDataUrl"] = normalize_data_url(supplied_guide)
        settings["compositionGuideType"] = (
            str(body.get("compositionGuideType") or "external").strip().lower()
        )
    else:
        depth_started_at = time.monotonic()
        settings["compositionGuideDataUrl"] = build_depth_composition_guide(reference_data_url)
        settings["compositionGuideType"] = "depth"
        append_timing(
            settings.get("timings"),
            "depth_composition_guide",
            "local/depth-anything-v2-vits-170-8-8-95",
            depth_started_at,
        )
    product_data_urls = [normalize_data_url(item) for item in product_image_data_urls]
    product_data_url = product_data_urls[0]

    generation_path = normalize_generation_path(body.get("generationPath"))
    if not generation_path:
        generation_path, _ = classify_product_kind(product_data_url, settings)
    settings["generationPath"] = generation_path
    init_progress(settings, settings.get("progressId"), generation_path)

    try:
        if generation_path == "apparel":
            result = replicate_apparel(reference_data_url, product_data_urls, settings, generation_path)
        else:
            result = replicate_non_apparel(reference_data_url, product_data_urls, settings, generation_path)
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
        "faceIdentityMode": normalize_face_identity_mode(body.get("faceIdentityMode")),
    }


def replicate_non_apparel(reference_data_url, product_data_urls, settings, generation_path):
    set_progress(settings, 0, "正在分析参考图")
    prompt = compose_non_apparel_prompt(reference_data_url, product_data_urls, settings)
    set_progress(settings, 1, "Prompt 已生成")
    final_reference_images = build_generation_reference_images(product_data_urls, settings)
    final_image_prompt = (
        f"{prompt}"
        " 全局白平衡、冷暖、饱和度、对比、高光阴影和成像质感严格按文字 prompt 执行。"
        "当前输入商品图只提供商品本身的固有外观，不得继承商品图的背景色、环境光、曝光、白平衡、调色滤镜或画面质感。"
        "商品图是商品结构的唯一真值来源：必须保持其部件、数量、连接方式、覆盖范围和边缘轮廓，不得添加商品图中不存在的吊带、肩带、领子、袖子、开口、镂空或其他结构。"
        "参考图旧商品只提供姿势、占位、遮挡和裁切，不得与新商品混合成拼接款。"
        f"{NON_APPAREL_HUMAN_CARRIER_RULES}"
        "文字 prompt 中的躯干倾斜、躯干旋转、肩线斜率、髋肩扭转、左右手臂方向、肘部弯曲和手部出画关系是动作硬约束。"
        "不得把近距离斜向自拍、侧倾躯干或单臂伸出画外的姿势改成正面站立、躯干竖直、双肩水平、双臂对称或标准商品展示姿势。"
        f"{build_composition_guide_rule(len(product_data_urls), settings.get('compositionGuideType'))}"
    )
    set_progress(settings, 2, "正在生成图片")
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
        "referenceAnalysisPrompt": "",
        "productAnalysisPrompt": "",
        "analysisPrompt": "",
        "prompt": prompt,
        "imageRequestDebug": image_request_debug,
        "timings": settings["timings"],
        "referenceHasFace": False,
        "generationPath": generation_path,
    }


def replicate_apparel(reference_data_url, product_data_urls, settings, generation_path):
    set_progress(settings, 0, "正在分析参考图")
    face_identity_mode = settings.get("faceIdentityMode") or "regenerate"
    reference_analysis = analyze_apparel_reference(reference_data_url, settings, face_identity_mode)
    set_progress(settings, 1, "参考图分析完成")
    reference_has_face = reference_analysis["hasFace"]
    face_reason = reference_analysis["reason"]
    reference_description = reference_analysis["referenceDescription"]
    set_progress(settings, 1, "正在融合参考图和商品服饰约束")
    final_prompt = compose_apparel_final_prompt(
        product_data_urls,
        reference_analysis,
        settings,
        face_identity_mode,
    )
    final_prompt = enforce_flash_exposure_consistency(final_prompt, reference_analysis)
    set_progress(settings, 2, "最终 Prompt 已生成，正在调用生图模型")
    if face_identity_mode == "preserve_reference":
        final_reference_images = build_generation_reference_images(product_data_urls, settings)
        identity_rule = (
            "当前输入图只提供商品外观，不提供人物身份；按主体描述保留原图的成人年龄段、发型轮廓、表情与脸部可见性，"
            "不要学习商品图中的人物。"
        )
    else:
        final_reference_images = build_generation_reference_images(product_data_urls, settings)
        if reference_has_face:
            identity_rule = (
                "当前输入图只提供商品外观，不提供人物身份；生成与参考图和商品图均不同的成年新人脸，"
                "只更换具体五官与身份，不改变主体描述中的肤色、视觉成熟度、大类外观呈现、体型比例、姿势和构图。"
            )
        else:
            identity_rule = (
                "当前输入图只提供商品外观，不提供人物身份；参考图人脸不可用于身份继承。"
                "严格执行参考图原本的人脸可见范围：脸在画外时不得生成或补全人脸，只露局部时只保留同样局部；"
                "仅当参考分析确认面部确实入画时才生成不同身份的成年新人脸，且不得改变景别、裁切、姿势和构图。"
            )
    bust_execution_rule = build_reference_bust_execution_lock_text(reference_analysis)
    if reference_analysis.get("appearanceLock", {}).get("genderPresentation") == "male":
        bust_execution_rule = ""
    direct_user_prompt = str(settings.get("userPrompt") or "").strip()
    final_image_prompt = build_legacy_apparel_image_prompt(
        final_prompt=final_prompt,
        reference_analysis=reference_analysis,
        bust_execution_rule=bust_execution_rule,
        identity_rule=identity_rule,
        user_prompt=direct_user_prompt,
        product_subject_hint=str(settings.get("productSubjectHint") or "").strip(),
    )
    final_image_prompt += build_composition_guide_rule(
        len(product_data_urls), settings.get("compositionGuideType")
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
        "imagePromptLength": len(final_image_prompt),
        "imageRequestDebug": image_request_debug,
        "timings": settings["timings"],
        "referenceHasFace": reference_has_face,
        "referenceFaceReason": face_reason,
        "referenceLayoutLock": reference_analysis.get("layoutLock") or {},
        "referenceFrameLock": reference_analysis.get("frameLock") or {},
        "referenceAppearanceLock": reference_analysis.get("appearanceLock") or {},
        "referenceCameraLock": reference_analysis.get("cameraLock") or {},
        "faceIdentityMode": face_identity_mode,
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


def detect_faces_with_vision(image_data_url, settings):
    text = call_vision_model(
        model=settings["visionModel"],
        instructions=(
            "你是图片人脸定位助手。你会看到一张商品图，只需要找出图中真人、模特或清晰人像的脸部区域。"
            "返回归一化坐标，坐标范围 0 到 1，x/y 是脸部框左上角，width/height 是脸部框宽高。"
            "只标脸部和少量头发边缘，不要把脖子、衣服、身体或背景纳入框内。"
            "如果没有真人脸、脸太小无法判断、脸被完全遮挡、只有插画/海报/服装印花上的脸，则返回空数组。"
            "只输出 JSON，格式必须是 {\"faces\":[{\"x\":0.1,\"y\":0.1,\"width\":0.2,\"height\":0.2}]}，不要 Markdown。"
        ),
        content=[
            {"type": "input_image", "image_url": image_data_url},
            {"type": "input_text", "text": "请定位这张商品图中的真人或模特脸部区域。只输出 JSON。"},
        ],
        temperature=0,
        max_output_tokens=300,
        timing_label="kimi_product_face_bbox",
    )
    data = parse_json_text(text)
    faces = data.get("faces") if isinstance(data, dict) else []
    if not isinstance(faces, list):
        return []
    cleaned = []
    for face in faces[:8]:
        if not isinstance(face, dict):
            continue
        try:
            x = clamp_float(face.get("x"), 0, 1)
            y = clamp_float(face.get("y"), 0, 1)
            width = clamp_float(face.get("width"), 0, 1)
            height = clamp_float(face.get("height"), 0, 1)
        except (TypeError, ValueError):
            continue
        if width < 0.015 or height < 0.015:
            continue
        if x + width > 1:
            width = max(0, 1 - x)
        if y + height > 1:
            height = max(0, 1 - y)
        cleaned.append({"x": x, "y": y, "width": width, "height": height})
    return cleaned


def clamp_float(value, minimum, maximum):
    number = float(value)
    return max(minimum, min(maximum, number))


def normalize_text_list(value):
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_text_block(value):
    if isinstance(value, list):
        return "；".join(normalize_text_list(value))
    return str(value or "").strip()


def normalize_box_1000(value):
    if not isinstance(value, dict):
        return {}
    try:
        x = int(round(clamp_float(value.get("x", 0), 0, 1000)))
        y = int(round(clamp_float(value.get("y", 0), 0, 1000)))
        width = int(round(clamp_float(value.get("width", 0), 0, 1000 - x)))
        height = int(round(clamp_float(value.get("height", 0), 0, 1000 - y)))
    except (TypeError, ValueError):
        return {}
    if width < 20 or height < 20:
        return {}
    return {"x": x, "y": y, "width": width, "height": height}


def normalize_scale_anchors(value):
    source = value if isinstance(value, dict) else {}
    result = {}
    for key in ("faceBox", "torsoBox"):
        box = normalize_box_1000(source.get(key))
        if box:
            result[key] = box
    for key in (
        "leftShoulderX",
        "rightShoulderX",
        "headTopY",
        "chinY",
        "chestCenterY",
        "waistY",
        "visibleBodyEndY",
    ):
        if key not in source:
            continue
        try:
            result[key] = int(round(clamp_float(source.get(key), 0, 1000)))
        except (TypeError, ValueError):
            continue
    return result


def normalize_reference_frame_lock(value):
    source = value if isinstance(value, dict) else {}
    result = {
        "topEdge": str(source.get("topEdge") or "").strip(),
        "bottomEdge": str(source.get("bottomEdge") or "").strip(),
        "leftEdge": str(source.get("leftEdge") or "").strip(),
        "rightEdge": str(source.get("rightEdge") or "").strip(),
        "topmostPersonPart": str(source.get("topmostPersonPart") or "").strip(),
        "topBlankEvidence": str(source.get("topBlankEvidence") or "").strip(),
        "visiblePersonBox": normalize_box_1000(source.get("visiblePersonBox")),
        "scaleAnchors": normalize_scale_anchors(source.get("scaleAnchors")),
        "visibleBodyParts": normalize_text_list(source.get("visibleBodyParts")),
        "invisibleBodyParts": normalize_text_list(source.get("invisibleBodyParts")),
        "visibleSceneElements": normalize_text_list(source.get("visibleSceneElements")),
        "shotScale": str(source.get("shotScale") or "").strip(),
        "shotScaleClass": normalize_enum(
            source.get("shotScaleClass"),
            {"close_up", "medium", "three_quarter", "near_full", "full", "environmental"},
        ),
        "horizontalPlacementEvidence": str(
            source.get("horizontalPlacementEvidence") or ""
        ).strip(),
        "scalePriorityCue": str(source.get("scalePriorityCue") or "").strip(),
    }
    if "topPersonY" in source:
        try:
            result["topPersonY"] = int(round(clamp_float(source.get("topPersonY"), 0, 1000)))
        except (TypeError, ValueError):
            pass
    box = result.get("visiblePersonBox")
    if isinstance(box, dict) and box:
        center_x = box["x"] + box["width"] / 2
        left_margin = box["x"]
        right_margin = max(0, 1000 - box["x"] - box["width"])
        result["subjectCenterX"] = int(round(center_x))
        if center_x < 460:
            result["horizontalPlacement"] = "left"
        elif center_x > 540:
            result["horizontalPlacement"] = "right"
        else:
            result["horizontalPlacement"] = "center"
        if left_margin - right_margin >= 60:
            result["dominantNegativeSpace"] = "left"
        elif right_margin - left_margin >= 60:
            result["dominantNegativeSpace"] = "right"
        else:
            result["dominantNegativeSpace"] = "balanced"
        edge_contacts = []
        if left_margin <= 20:
            edge_contacts.append("left")
        if right_margin <= 20:
            edge_contacts.append("right")
        if box["y"] <= 20:
            edge_contacts.append("top")
        if 1000 - box["y"] - box["height"] <= 20:
            edge_contacts.append("bottom")
        result["edgeContacts"] = edge_contacts
        box_top = box["y"]
        top_person_y = result.get("topPersonY")
        if not isinstance(top_person_y, int):
            result["topPersonY"] = box_top
        elif abs(top_person_y - box_top) >= 80:
            # When the two independent measurements disagree badly, preserve the
            # larger observed blank area instead of letting the renderer zoom in.
            conservative_top = max(top_person_y, box_top)
            box_bottom = box["y"] + box["height"]
            if conservative_top < box_bottom:
                box["y"] = conservative_top
                box["height"] = box_bottom - conservative_top
                result["topPersonY"] = conservative_top
                cue = result.get("scalePriorityCue") or ""
                result["scalePriorityCue"] = (
                    cue + "；顶部留白双测量冲突时采用较大留白，人物超框时缩小人物并后退镜头"
                ).strip("；")
    return result


def normalize_reference_layout_lock(value, fallback_text=""):
    source = value if isinstance(value, dict) else {}
    layout_type = normalize_enum(source.get("layoutType"), {"single", "grid"})

    def positive_int(raw_value, default=0):
        try:
            return max(0, int(round(float(raw_value))))
        except (TypeError, ValueError):
            return default

    rows = positive_int(source.get("rows"))
    columns = positive_int(source.get("columns"))
    panel_count = positive_int(source.get("panelCount"))
    evidence_text = f"{fallback_text} {json.dumps(source, ensure_ascii=False)}"

    known_grids = (
        (r"(?:四宫格|四格|4格|2\s*[x×X*]\s*2)", 2, 2, 4),
        (r"(?:九宫格|九格|9格|3\s*[x×X*]\s*3)", 3, 3, 9),
        (r"(?:六宫格|六格|6格|2\s*[x×X*]\s*3|3\s*[x×X*]\s*2)", 2, 3, 6),
    )
    if layout_type != "grid":
        for pattern, detected_rows, detected_columns, detected_count in known_grids:
            if re.search(pattern, evidence_text, flags=re.IGNORECASE):
                layout_type = "grid"
                rows = rows or detected_rows
                columns = columns or detected_columns
                panel_count = panel_count or detected_count
                break
    if layout_type != "grid" and re.search(r"多宫格|拼图|对比图|分格", evidence_text):
        layout_type = "grid"

    if layout_type != "grid":
        return {"layoutType": "single"}

    if not panel_count and rows and columns:
        panel_count = rows * columns
    if not rows and not columns and panel_count == 4:
        rows, columns = 2, 2
    elif not rows and not columns and panel_count == 9:
        rows, columns = 3, 3

    panels = []
    raw_panels = source.get("panels")
    if isinstance(raw_panels, list):
        for index, raw_panel in enumerate(raw_panels):
            panel = raw_panel if isinstance(raw_panel, dict) else {"pose": raw_panel}
            normalized = {
                "position": str(panel.get("position") or f"第{index + 1}格").strip(),
                "crop": str(panel.get("crop") or "").strip(),
                "pose": normalize_screen_coordinate_text(panel.get("pose")),
                "subjectPosition": str(panel.get("subjectPosition") or "").strip(),
            }
            if any(normalized.values()):
                panels.append(normalized)

    if not panels:
        position_labels = ("左上格", "右上格", "左下格", "右下格")
        for index, label in enumerate(position_labels):
            match = re.search(
                rf"{label}\s*[：:]\s*(.+?)(?=(?:左上格|右上格|左下格|右下格)\s*[：:]|$)",
                evidence_text,
            )
            if match:
                panels.append(
                    {
                        "position": label,
                        "crop": "",
                        "pose": normalize_screen_coordinate_text(match.group(1).strip("；;，,。 \"{}")),
                        "subjectPosition": "",
                    }
                )
    if not panel_count and panels:
        panel_count = len(panels)

    return {
        "layoutType": "grid",
        "rows": rows,
        "columns": columns,
        "panelCount": panel_count,
        "dividerDescription": str(source.get("dividerDescription") or "").strip(),
        "sharedContinuity": str(source.get("sharedContinuity") or "").strip(),
        "panels": panels,
    }


def reconcile_reference_body_orientation(body_orientation):
    """Turn a visually clear partial profile into an executable near-profile lock."""
    text = str(body_orientation or "").strip()
    if not text or "近侧面" in text:
        return text
    face_match = re.search(r"脸部可见比例约\s*(\d+)%", text)
    face_ratio = int(face_match.group(1)) if face_match else 100
    has_directional_profile = (
        "三分之二侧身" in text
        and "鼻尖朝向画面" in text
        and any(marker in text for marker in ("更靠近镜头", "被遮挡", "部分遮挡"))
    )
    if has_directional_profile and face_ratio <= 75:
        text = text.replace("三分之二侧身", "近侧面")
        text = re.sub(r"偏转约\s*\d+\s*至\s*\d+\s*度", "横转约60至70度", text, count=1)
        text += "；胸腹正面宽度明显压缩，远侧肩髋被近侧身体遮挡，禁止正面化"
    return text


REFERENCE_APPAREL_DETAIL_MARKERS = (
    "待替换商品",
    "原商品",
    "原服饰",
    "旧服饰",
    "旧衣",
    "上衣",
    "内搭",
    "外套",
    "背心",
    "吊带",
    "肩带",
    "领口",
    "衣领",
    "袖口",
    "袖片",
    "下摆",
    "衣摆",
    "裤装",
    "裤腰",
    "裤脚",
    "裙装",
    "裙摆",
    "裁片",
    "拼接",
    "开口",
    "开衩",
    "镂空",
    "门襟",
    "纽扣",
    "拉链",
    "口袋",
    "面料",
    "布料",
    "服装图案",
    "衣物图案",
    "服装文字",
    "衣物文字",
    "服装标签",
    "衣物标签",
    "衣料",
    "低领",
    "高领",
    "圆领",
    "V领",
    "露肩",
    "单肩",
    "无袖",
    "短袖",
    "长袖",
    "收腰",
    "宽松",
    "紧身",
    "褶皱",
    "连衣裙",
    "半身裙",
    "短裤",
    "长裤",
    "服饰颜色",
    "衣服颜色",
    "腰线",
)


def strip_reference_apparel_clauses(value):
    """Remove old-garment clauses while preserving body, action and prop geometry."""
    text = str(value or "").strip()
    if not text or not any(marker in text for marker in REFERENCE_APPAREL_DETAIL_MARKERS):
        return text
    clauses = re.split(r"[，,；;。]+", text)
    kept = [
        clause.strip()
        for clause in clauses
        if clause.strip()
        and not any(marker in clause for marker in REFERENCE_APPAREL_DETAIL_MARKERS)
    ]
    return "，".join(kept)


def sanitize_reference_apparel_list(value, limit=None):
    sanitized = []
    for item in normalize_text_list(value):
        clean = strip_reference_apparel_clauses(item)
        if clean and clean not in sanitized:
            sanitized.append(clean)
    return sanitized[:limit] if isinstance(limit, int) else sanitized


def normalize_non_target_wardrobe_coverage(value):
    """Keep only coarse coverage needed for replacement; never retain old styling details."""
    text = "；".join(normalize_text_list(value))
    if not text:
        return []
    coverage = []
    if any(marker in text for marker in ("上身", "上装", "上衣", "内搭", "外套", "背心", "吊带")):
        coverage.append("上身区域存在独立非目标服饰覆盖")
    if any(marker in text for marker in ("下身", "下装", "裤", "裙")):
        coverage.append("下身区域存在独立非目标服饰覆盖")
    if any(marker in text for marker in ("鞋", "袜", "脚部")):
        coverage.append("脚部区域存在独立非目标服饰覆盖")
    if any(marker in text for marker in ("帽", "头饰")):
        coverage.append("头部区域存在独立非目标配饰覆盖")
    if any(marker in text for marker in ("首饰", "项链", "耳饰", "耳环", "手链", "戒指")):
        coverage.append("身体局部存在独立非目标配饰覆盖")
    return coverage


NON_TARGET_WEARABLE_MARKERS = (
    "鞋",
    "袜",
    "靴",
    "帽",
    "头饰",
    "发饰",
    "包",
    "项链",
    "耳环",
    "耳饰",
    "手链",
    "手镯",
    "戒指",
    "眼镜",
    "墨镜",
    "围巾",
)

NON_TARGET_WEARABLE_FORBIDDEN_MARKERS = (
    "上衣",
    "上装",
    "外套",
    "衬衫",
    "T恤",
    "卫衣",
    "毛衣",
    "针织衫",
    "开衫",
    "夹克",
    "风衣",
    "西装",
    "西服",
    "背心",
    "吊带",
    "打底衫",
    "内搭",
    "套装",
    "连体衣",
    "连体裤",
    "连衣裙",
    "半身裙",
    "裙装",
    "裙子",
    "短裤",
    "长裤",
    "裤装",
    "裤子",
    "下装",
    "衣身",
    "服装主体",
    "旧服饰",
    "裤腰",
    "领口",
    "袖口",
    "肩带",
    "下摆",
)


def sanitize_non_target_wearables(value, limit=8):
    """Keep visible peripheral items without leaking the old target garment."""
    sanitized = []
    for item in normalize_text_list(value):
        for clause in re.split(r"[；;。]+", str(item)):
            clean = clause.strip(" ，,")
            if not clean:
                continue
            if not any(marker in clean for marker in NON_TARGET_WEARABLE_MARKERS):
                continue
            if any(marker in clean for marker in NON_TARGET_WEARABLE_FORBIDDEN_MARKERS):
                continue
            if clean not in sanitized:
                sanitized.append(clean)
    return sanitized[:limit]


def normalize_reference_appearance_lock(value):
    source = value if isinstance(value, dict) else {}
    direction_audit_source = source.get("directionAudit")
    if not isinstance(direction_audit_source, dict):
        direction_audit_source = {}

    def normalize_direction_x(raw_value):
        try:
            return max(0, min(1000, int(round(float(raw_value)))))
        except (TypeError, ValueError):
            return None

    direction_audit = {
        "faceCenterX": normalize_direction_x(direction_audit_source.get("faceCenterX")),
        "noseTipX": normalize_direction_x(direction_audit_source.get("noseTipX")),
        "evidence": str(direction_audit_source.get("evidence") or "").strip(),
    }
    hand_position_audit = []
    raw_hand_audit = source.get("handPositionAudit")
    if isinstance(raw_hand_audit, list):
        for item in raw_hand_audit[:4]:
            if not isinstance(item, dict):
                continue
            center_x = normalize_direction_x(item.get("centerX"))
            center_y = normalize_direction_x(item.get("centerY"))
            if center_x is None:
                continue
            # Screen side is derived from the measured x coordinate, never trusted
            # from a free-form left/right label returned by the vision model.
            screen_side = "left" if center_x < 500 else "right"
            hand_position_audit.append(
                {
                    "screenSide": screen_side,
                    "centerX": center_x,
                    "centerY": center_y,
                    "contact": strip_reference_apparel_clauses(item.get("contact")),
                    "visibility": str(item.get("visibility") or "").strip(),
                    "evidence": strip_reference_apparel_clauses(item.get("evidence")),
                }
            )
    hand_position_audit.sort(key=lambda item: item["centerX"])
    pose_contacts = sanitize_reference_apparel_list(source.get("poseContacts"))
    visual_salience = "、".join(
        sanitize_reference_apparel_list(source.get("visualSalience"))
    )
    bust_level = normalize_enum(
        source.get("bustLevel"), {"prominent", "non_prominent", "uncertain"}, "uncertain"
    )
    bust_confidence = normalize_enum(
        source.get("bustConfidence"), {"high", "medium", "low"}, "low"
    )
    bust_evidence = normalize_text_list(source.get("bustEvidence"))
    body_proportions = strip_reference_apparel_clauses(
        source.get("bodyProportions")
    )
    bust_clause = re.search(r"胸部[^；。]*", body_proportions)
    if bust_level == "prominent" and bust_clause and any(
        qualifier in bust_clause.group(0)
        for qualifier in ("普通", "偏小", "不明显", "不突出", "未显著")
    ):
        bust_level = "non_prominent"
    positive_bust_evidence = sum(
        any(
            marker in item
            for marker in (
                "左右胸部外轮廓",
                "胸部宽度相对腰宽显著",
                "胸部前向体积明显",
                "独立的圆弧",
                "独立圆弧",
                "超出肋骨",
                "超出躯干侧肋线",
                "胸部外轮廓",
                "超出腰宽",
                "侧面弧度独立",
                "弧度独立于衣物",
            )
        )
        for item in bust_evidence
    )
    invalid_bust_evidence = any(
        marker in "；".join(bust_evidence)
        for marker in (
            "低领",
            "露肤",
            "肩带",
            "领口",
            "俯拍",
            "广角",
            "手臂挤压",
            "裁切放大",
            "单侧轮廓",
        )
    )
    if (
        bust_confidence == "high"
        and len(bust_evidence) >= 2
        and positive_bust_evidence >= 2
        and not invalid_bust_evidence
    ):
        bust_level = "prominent"
    if bust_level == "prominent" and (
        bust_confidence != "high" or len(bust_evidence) < 2 or positive_bust_evidence < 2
    ):
        bust_level = "uncertain"
    if bust_level != "prominent":
        body_proportions = re.sub(
            r"胸部.*?(?=(?:[，,](?:胸腰|腰部|腰胯|可见腿|腿部|大腿|小腿))|[；。]|$)",
            "胸部保持参考图可直接确认的自然体积",
            body_proportions,
        )
        visual_salience = "、".join(
            item for item in re.split(r"[、；]", visual_salience) if item and "胸" not in item
        )
    visible_skin_tone = str(source.get("visibleSkinTone") or "").strip()
    gender_presentation = normalize_enum(
        source.get("genderPresentation"), {"male", "female", "uncertain"}, "uncertain"
    )
    if gender_presentation == "uncertain":
        gender_evidence = "；".join(
            str(source.get(key) or "")
            for key in ("subjectPresence", "demographicAppearance")
        )
        male_evidence = any(
            marker in gender_evidence for marker in ("成年男性", "年轻男性", "男性人物", "男士")
        )
        female_evidence = any(
            marker in gender_evidence for marker in ("成年女性", "年轻女性", "女性人物", "女士")
        )
        if male_evidence and not female_evidence:
            gender_presentation = "male"
        elif female_evidence and not male_evidence:
            gender_presentation = "female"
    if gender_presentation == "male":
        # Female apparel photography can otherwise leak bust cues into a male reference.
        bust_level = "non_prominent"
        bust_confidence = "high"
        bust_evidence = []
        body_proportions = re.sub(
            r"胸部.*?(?=(?:[，,](?:胸腰|腰部|腰胯|可见腿|腿部|大腿|小腿))|[；。]|$)",
            "男性胸廓保持参考图可见的自然比例",
            body_proportions,
        )
        visual_salience = "、".join(
            item
            for item in re.split(r"[、；]", visual_salience)
            if item and not any(marker in item for marker in ("胸", "乳", "沙漏"))
        )
    lighting_mode = normalize_enum(
        source.get("lightingMode"),
        {
            "near_axis_flash",
            "fill_flash",
            "direct_sun",
            "diffuse_daylight",
            "mixed",
            "indoor_ambient",
        },
    )
    flash_evidence = normalize_text_list(source.get("flashEvidence"))
    daylight_evidence = normalize_text_list(source.get("daylightEvidence"))
    flash_confidence = normalize_enum(
        source.get("flashConfidence"), {"high", "medium", "low"}, "low"
    )
    lighting_physics_text = str(source.get("lightingPhysics") or "").strip()
    capture_mode_text = str(source.get("captureMode") or "").strip()
    flash_relation_text = "；".join(
        [
            str(source.get("lightingPhysics") or ""),
            str(source.get("mustPreserveLightingCue") or ""),
            str(source.get("backgroundColorRelation") or ""),
            str(source.get("toneProfile") or ""),
            *flash_evidence,
        ]
    )
    daylight_text = "；".join(
        [lighting_physics_text, capture_mode_text, *daylight_evidence]
    )
    axis_shadow = any(
        marker in flash_relation_text
        for marker in (
            "贴轴硬影",
            "贴轴阴影",
            "阴影贴近镜头轴",
            "轮廓后方紧贴",
            "鼻影贴近",
            "颌下阴影贴近",
        )
    )
    rapid_falloff = any(
        marker in flash_relation_text
        for marker in ("快速衰减", "近亮远暗", "从近景向远景衰减", "远景暗一档")
    )
    frontal_specular = any(
        marker in flash_relation_text
        for marker in (
            "瞬时镜面高光",
            "小面积正面反光",
            "点状正面反光",
            "面料点状反光",
            "皮肤点状反光",
        )
    )
    exposure_separation = any(
        marker in flash_relation_text
        for marker in ("人物受光独立于背景", "背景与人物曝光分离", "人物正面瞬间提亮")
    )
    flattened_shadow = any(
        marker in flash_relation_text
        for marker in ("面部阴影被压平", "阴影靠近镜头轴且较平", "正面阴影较平")
    )
    flash_category_count = sum(
        (axis_shadow, rapid_falloff, frontal_specular, exposure_separation, flattened_shadow)
    )
    flash_specific_anchor = axis_shadow or (rapid_falloff and frontal_specular)
    validated_flash = (
        flash_confidence == "high"
        and flash_category_count >= 3
        and flash_specific_anchor
    )
    directional_sun = any(
        marker in daylight_text
        for marker in ("直射阳光", "阳光斑", "树影", "日照硬影", "方向性日照")
    )
    daylight_context = bool(daylight_evidence) or any(
        marker in daylight_text
        for marker in (
            "窗边",
            "窗外",
            "日光",
            "自然光",
            "天光",
            "天空",
            "室外绿植",
            "柔和散射",
            "大面积柔和渐变",
            "人物与背景共享",
        )
    )
    if lighting_mode in {"near_axis_flash", "fill_flash"} and not validated_flash:
        flash_evidence = []
        flash_confidence = "low"
        if directional_sun:
            lighting_mode = "direct_sun"
        elif daylight_context:
            lighting_mode = "diffuse_daylight"
        else:
            lighting_mode = "indoor_ambient"
    elif lighting_mode not in {"near_axis_flash", "fill_flash"}:
        flash_evidence = []
        flash_confidence = "low"
    action_keyframe = strip_reference_apparel_clauses(source.get("actionKeyframe"))
    pose_text = "；".join([action_keyframe, *pose_contacts])
    selfie_relation = str(source.get("selfieRelation") or "").strip()
    capture_type = normalize_enum(
        source.get("captureType"),
        {
            "selfie_visible_phone",
            "selfie_phone_out_of_frame",
            "third_party",
            "timer_or_remote",
            "uncertain",
        },
        "uncertain",
    )
    phone_visible_value = source.get("phoneVisible")
    phone_visible = phone_visible_value if isinstance(phone_visible_value, bool) else None
    both_hands_committed = any(
        marker in pose_text
        for marker in (
            "双手均可见",
            "双手完整可见",
            "两只手均可见",
            "两只手完整可见",
            "双手分别接触",
            "双手握持",
            "双前臂",
        )
    ) or (
        "双手" in pose_text
        and any(marker in pose_text for marker in ("握", "扶", "抓", "举", "压靠", "接触"))
    )
    action_has_phone = any(marker in pose_text for marker in ("手机", "持机", "自拍杆"))
    hidden_phone_conflict = (
        both_hands_committed
        and not action_has_phone
        and (
            capture_type == "selfie_phone_out_of_frame"
            or ("自拍" in selfie_relation and any(marker in selfie_relation for marker in ("未入画", "画外")))
        )
    )
    if hidden_phone_conflict:
        capture_type = "timer_or_remote"
        phone_visible = False
        selfie_relation = "他拍或定时遥控拍摄，手机不入画；双手均严格执行动作关键帧，不得额外分配隐藏持机手"
    elif capture_type in {"third_party", "timer_or_remote"}:
        phone_visible = False if phone_visible is None else phone_visible
        if not selfie_relation or "自拍" in selfie_relation:
            selfie_relation = "他拍或定时遥控拍摄，不得把任一只已执行动作的手改成持机手"

    direction_anchors = sanitize_reference_apparel_list(
        source.get("directionAnchors"), limit=6
    )
    if not direction_anchors:
        for value in (
            str(source.get("bodyOrientation") or "").strip(),
            action_keyframe,
            str(source.get("faceVisibility") or "").strip(),
        ):
            if value and any(marker in value for marker in ("画面左", "画面右")):
                direction_anchors.append(value)
    overlay_noise = (
        "轮播",
        "导航点",
        "导航圆点",
        "指示器",
        "进度条",
        "页码",
        "播放控件",
        "状态栏",
        "应用界面",
        "截图",
        "录屏",
        "水印",
        "小红书",
        "白点",
        "白色画布",
        "白边",
        "黑边",
    )
    snapshot_imperfections = [
        item
        for item in normalize_text_list(source.get("snapshotImperfections"))
        if not any(noise in item for noise in overlay_noise)
    ]
    environment_realism = str(source.get("environmentRealism") or "").strip()
    background_structure_anchors = normalize_text_list(
        source.get("backgroundStructureAnchors")
    )[:5]
    background_forbidden_fallback = str(
        source.get("backgroundForbiddenFallback") or ""
    ).strip()
    background_color_relation = str(source.get("backgroundColorRelation") or "").strip()
    tone_profile = str(source.get("toneProfile") or "").strip()
    global_color_bias = str(source.get("globalColorBias") or "").strip()
    global_color_bias_strength = normalize_enum(
        source.get("globalColorBiasStrength"),
        {"none", "subtle", "moderate", "strong"},
        "subtle" if global_color_bias else "none",
    )
    neutral_anchor_audit = normalize_text_block(source.get("neutralAnchorAudit"))
    capture_mode = str(source.get("captureMode") or "").strip()
    ccd_evidence = normalize_text_list(source.get("ccdEvidence"))
    glow_evidence = normalize_text_list(source.get("glowEvidence"))[:4]
    highlight_behavior = str(source.get("highlightBehavior") or "").strip()

    exposure_evidence = "；".join(
        (
            str(source.get("mustPreserveLightingCue") or ""),
            highlight_behavior,
            *snapshot_imperfections,
        )
    )
    if any(marker in exposure_evidence for marker in ("过曝", "溢出", "曝光上限", "丢失细节")):
        for old in ("高光柔和平滑无溢出", "高光柔和无溢出", "高光无溢出", "无溢出"):
            tone_profile = tone_profile.replace(old, "亮区接近曝光上限并允许局部轻微溢出")
        if "曝光上限" not in tone_profile and "轻微溢出" not in tone_profile:
            tone_profile += "；局部亮区接近曝光上限并允许轻微溢出"
        highlight_behavior = highlight_behavior.replace("无溢出", "局部亮区允许轻微溢出")

    skin_consistency_text = "；".join(
        (
            visible_skin_tone,
            str(source.get("facialSkinRendering") or ""),
            global_color_bias,
            str(source.get("colorAnchor") or ""),
            *flash_evidence,
        )
    )
    if (
        lighting_mode in {"near_axis_flash", "fill_flash"}
        and "冷白" in skin_consistency_text
        and any(marker in visible_skin_tone for marker in ("暖黄偏白", "暖白", "偏黄"))
    ):
        visible_skin_tone = "冷白皮，高明度冷粉白，正面闪光区域明显缺少黄调；环境暖色只能局部反射，不能把面中、颈部和手臂统一染黄"

    # Early CCD white balance casts are easy for the vision model to over-correct as
    # "near neutral". Only strengthen the cast when multiple neutral anchors agree.
    warm_anchor_hits = sum(
        neutral_anchor_audit.count(marker)
        for marker in ("偏暖", "暖白", "暖灰", "米黄", "黄绿")
    )
    cool_green_anchor_hits = neutral_anchor_audit.count("冷绿") + neutral_anchor_audit.count("灰绿")
    if cool_green_anchor_hits >= 2 and "近中性" in global_color_bias:
        global_color_bias = (
            "全局可见轻度冷灰绿色白平衡偏移：白色、浅灰和阴影中性色都带同方向的冷绿，"
            "皮肤仍保留自然血色但受环境影响略偏冷；不得校正成纯净中性或暖黄商业人像色调"
        )
    if (
        "CCD" in capture_mode.upper()
        and len(ccd_evidence) >= 2
        and warm_anchor_hits >= 2
        and "近中性" in global_color_bias
    ):
        global_color_bias = (
            "全局可见轻微暖黄绿白平衡偏移：白色与浅灰中性色也带同方向的米黄至浅黄绿色，"
            "皮肤中间调轻微偏暖，阴影仍保留少量冷灰；这是早期数码相机综合色偏，不得校正成现代手机的干净中性"
        )
    if global_color_bias_strength == "subtle" and any(
        marker in global_color_bias for marker in ("冷绿", "灰绿", "黄绿", "暖红", "蓝灰")
    ):
        global_color_bias += (
            "；该色偏仅为轻微相机白平衡痕迹，大面积白灰区域仍接近中性，"
            "只能局部弱可见，禁止放大成覆盖整图的绿色、黄色、红色或蓝色滤镜"
        )
    dark_environment_details = (
        any(marker in background_color_relation for marker in ("纯黑", "近黑", "黑色墙面", "深色墙面"))
        and any(
            marker in environment_realism
            for marker in (
                "纹理",
                "颗粒",
                "接缝",
                "划痕",
                "风化",
                "栏杆",
                "锈迹",
                "门窗",
                "灯光",
                "地面",
                "墙面",
            )
        )
    )
    if dark_environment_details:
        background_color_relation = background_color_relation.replace("纯黑色墙面", "深黑至炭黑色真实墙面")
        background_color_relation += (
            "；暗部仍保留参考图可见的低对比材质、接缝和环境结构，不是纯色无缝影棚背景"
        )
        tone_profile = tone_profile.replace("黑位深但无细节", "黑位深但保留低对比墙面材质与空间细节")
        if "不是棚拍" not in environment_realism:
            environment_realism += "；必须保持真实场所层级，不得简化成棚拍黑幕或无缝纯色背景"
    return {
        "genderPresentation": gender_presentation,
        "visibleSkinTone": visible_skin_tone,
        "facialSkinRendering": str(source.get("facialSkinRendering") or "").strip(),
        "bodySilhouette": strip_reference_apparel_clauses(
            source.get("bodySilhouette")
        ),
        "bodyProportions": body_proportions,
        "bustLevel": bust_level,
        "bustConfidence": bust_confidence,
        "bustPerspectiveRisk": strip_reference_apparel_clauses(
            source.get("bustPerspectiveRisk")
        ),
        "bustEvidence": sanitize_reference_apparel_list(bust_evidence),
        "visualSalience": visual_salience,
        "subjectPresence": str(source.get("subjectPresence") or "").strip(),
        "mouthMicroExpression": str(source.get("mouthMicroExpression") or "").strip(),
        "demographicAppearance": str(source.get("demographicAppearance") or "").strip(),
        "colorAnchor": str(source.get("colorAnchor") or "").strip(),
        "poseContacts": pose_contacts,
        "bodyOrientation": reconcile_reference_body_orientation(
            str(source.get("bodyOrientation") or "").strip()
        ),
        "directionAudit": direction_audit,
        "handPositionAudit": hand_position_audit,
        "actionKeyframe": action_keyframe,
        "limbTopology": strip_reference_apparel_clauses(
            source.get("limbTopology")
        ),
        "forbiddenPoseFallback": strip_reference_apparel_clauses(
            source.get("forbiddenPoseFallback")
        ),
        "directionAnchors": direction_anchors,
        "captureType": capture_type,
        "phoneVisible": phone_visible,
        "selfieRelation": selfie_relation,
        "foregroundObjectGeometry": strip_reference_apparel_clauses(
            source.get("foregroundObjectGeometry")
        ),
        "nonTargetWardrobe": normalize_non_target_wardrobe_coverage(
            source.get("nonTargetWardrobe")
        ),
        "nonTargetWearables": sanitize_non_target_wearables(
            source.get("nonTargetWearables")
        ),
        "poseSurfaceGeometry": strip_reference_apparel_clauses(
            source.get("poseSurfaceGeometry")
        ),
        "locomotionGeometry": strip_reference_apparel_clauses(
            source.get("locomotionGeometry")
        ),
        "lightingPhysics": str(source.get("lightingPhysics") or "").strip(),
        "lightingMode": lighting_mode,
        "flashEvidence": flash_evidence,
        "flashConfidence": flash_confidence,
        "daylightEvidence": daylight_evidence,
        "mustPreserveLightingCue": str(source.get("mustPreserveLightingCue") or "").strip(),
        "highlightBehavior": highlight_behavior,
        "glowEvidence": glow_evidence,
        "backgroundColorRelation": background_color_relation,
        "globalColorBias": global_color_bias,
        "globalColorBiasStrength": global_color_bias_strength,
        "neutralAnchorAudit": neutral_anchor_audit,
        "toneProfile": tone_profile,
        "faceVisibility": strip_reference_apparel_clauses(
            source.get("faceVisibility")
        ),
        "postureAndSupport": strip_reference_apparel_clauses(
            source.get("postureAndSupport")
        ),
        "headPoseRange": str(source.get("headPoseRange") or "").strip(),
        "captureMode": capture_mode,
        "ccdEvidence": ccd_evidence,
        "captureRealism": str(source.get("captureRealism") or "").strip(),
        "snapshotImperfections": snapshot_imperfections,
        "environmentRealism": environment_realism,
        "backgroundStructureAnchors": background_structure_anchors,
        "backgroundForbiddenFallback": background_forbidden_fallback,
    }


def reconcile_reference_screen_direction(appearance):
    """Derive nose direction from image-plane coordinates instead of semantic left/right."""
    if not isinstance(appearance, dict):
        return appearance
    audit = appearance.get("directionAudit")
    if not isinstance(audit, dict):
        return appearance
    face_center_x = audit.get("faceCenterX")
    nose_tip_x = audit.get("noseTipX")
    if not isinstance(face_center_x, int) or not isinstance(nose_tip_x, int):
        return appearance
    delta = nose_tip_x - face_center_x
    if abs(delta) < 8:
        return appearance

    side = "左" if delta < 0 else "右"
    orientation = str(appearance.get("bodyOrientation") or "")
    orientation = re.sub(r"鼻尖朝(?:向)?画面[左右]侧", f"鼻尖朝画面{side}侧", orientation)
    appearance["bodyOrientation"] = orientation

    anchors = [
        value
        for value in normalize_text_list(appearance.get("directionAnchors"))
        if "鼻尖" not in value
    ]
    anchors.insert(
        0,
        f"脸框中心x={face_center_x}、鼻尖x={nose_tip_x}，鼻尖明确朝画面{side}侧",
    )
    appearance["directionAnchors"] = anchors[:6]
    return appearance


def reconcile_reference_capture_type(appearance, camera):
    """Use camera geometry to recover selfies whose phone sits outside the frame."""
    if not isinstance(appearance, dict) or not isinstance(camera, dict):
        return appearance
    evidence = "；".join(
        str(value or "")
        for value in (
            appearance.get("actionKeyframe"),
            appearance.get("selfieRelation"),
            appearance.get("foregroundObjectGeometry"),
            camera.get("pitch"),
            camera.get("distanceAndLens"),
            camera.get("perspectiveEvidence"),
            camera.get("mustPreserveAngleCue"),
        )
    )
    phone_visible = appearance.get("phoneVisible") is True
    capture_type = str(appearance.get("captureType") or "")
    arm_out_of_frame = any(marker in evidence for marker in ("手臂伸出画外", "前臂伸出画外", "手部伸出画外", "持机手在画外"))
    arm_toward_camera = any(marker in evidence for marker in ("手臂朝镜头", "手臂伸向镜头", "持机侧手臂", "自拍手臂"))
    hidden_selfie_evidence = "自拍臂长" in evidence and arm_out_of_frame and arm_toward_camera
    if not phone_visible and hidden_selfie_evidence and capture_type in {
        "third_party",
        "timer_or_remote",
        "uncertain",
        "",
    }:
        appearance["captureType"] = "selfie_phone_out_of_frame"
        appearance["phoneVisible"] = False
        appearance["selfieRelation"] = (
            "单手臂长自拍，持机侧手臂沿近大远小透视伸向镜头并在画外结束，手机不入画；"
            "另一侧手只执行参考图中可见动作，禁止改成第三方正面拍摄"
        )
    return appearance


def normalize_reference_camera_lock(value):
    source = value if isinstance(value, dict) else {}
    pitch = str(source.get("pitch") or "").strip()
    pitch_direction = normalize_enum(source.get("pitchDirection"), {"up", "level", "down"})
    if not pitch_direction:
        if any(marker in pitch for marker in ("仰拍", "向上")):
            pitch_direction = "up"
        elif any(marker in pitch for marker in ("俯拍", "向下")):
            pitch_direction = "down"
        elif pitch:
            pitch_direction = "level"
    return {
        "cameraHeight": str(source.get("cameraHeight") or "").strip(),
        "pitchDirection": pitch_direction,
        "pitch": pitch,
        "pitchConfidence": normalize_enum(source.get("pitchConfidence"), {"high", "medium", "low"}),
        "pitchVisualStrength": normalize_enum(
            source.get("pitchVisualStrength"), {"strong", "medium", "subtle", "none"}
        ),
        "verticalLineEvidence": str(source.get("verticalLineEvidence") or "").strip(),
        "surfacePlaneEvidence": str(source.get("surfacePlaneEvidence") or "").strip(),
        "bodyPerspectiveEvidence": str(source.get("bodyPerspectiveEvidence") or "").strip(),
        "postureRisk": str(source.get("postureRisk") or "").strip(),
        "mustPreserveAngleCue": str(source.get("mustPreserveAngleCue") or "").strip(),
        "yaw": str(source.get("yaw") or "").strip(),
        "roll": str(source.get("roll") or "").strip(),
        "focalLength35mm": str(source.get("focalLength35mm") or "").strip(),
        "lensClass": normalize_enum(
            source.get("lensClass"), {"ultra_wide", "wide", "standard", "telephoto"}
        ),
        "focalConfidence": normalize_enum(source.get("focalConfidence"), {"high", "medium", "low"}),
        "lensEvidence": str(source.get("lensEvidence") or "").strip(),
        "distanceAndLens": str(source.get("distanceAndLens") or "").strip(),
        "perspectiveEvidence": str(source.get("perspectiveEvidence") or "").strip(),
        "forbiddenFallback": str(source.get("forbiddenFallback") or "").strip(),
    }


def reconcile_reference_camera_lock(camera, frame):
    """Reject pitch estimates that confuse body posture or visible ground with camera pitch."""
    if not isinstance(camera, dict) or not isinstance(frame, dict):
        return camera
    pitch = str(camera.get("pitch") or "")
    direction = str(camera.get("pitchDirection") or "")
    confidence = str(camera.get("pitchConfidence") or "")
    strength = str(camera.get("pitchVisualStrength") or "")
    evidence = "；".join(
        str(camera.get(key) or "")
        for key in (
            "mustPreserveAngleCue",
            "perspectiveEvidence",
            "cameraHeight",
            "verticalLineEvidence",
            "surfacePlaneEvidence",
            "bodyPerspectiveEvidence",
        )
    )
    if direction == "up" or any(marker in pitch for marker in ("仰拍", "向上")):
        camera["pitchDirection"] = "up"
        if not camera.get("forbiddenFallback"):
            camera["forbiddenFallback"] = "禁止改成俯拍或从人物上方向下观察"
        return camera

    if direction == "level" and not any(marker in pitch for marker in ("俯拍", "向下")):
        camera_height = str(camera.get("cameraHeight") or "")
        person_box = frame.get("visiblePersonBox") if isinstance(frame.get("visiblePersonBox"), dict) else {}
        camera_explicitly_below_eyes = any(
            marker in camera_height
            for marker in (
                "低于人物眼睛",
                "眼睛高度略低",
                "眼睛同高或略低",
                "眼睛高度持平或略低",
                "平齐或略低",
                "胸口偏上",
            )
        )
        subject_above_optical_center = (
            isinstance(person_box.get("y"), int)
            and isinstance(person_box.get("height"), int)
            and person_box["y"] + person_box["height"] / 2 < 650
        )
        if camera_explicitly_below_eyes and subject_above_optical_center:
            camera["pitchDirection"] = "up"
            camera["pitch"] = "镜头轴线向上约2至4度的轻微仰拍"
            camera["pitchConfidence"] = "medium"
            camera["pitchVisualStrength"] = "subtle"
            camera["mustPreserveAngleCue"] = (
                "相机光心低于人物眼睛，镜头轻微向上看向脸部；人物前倾只属于姿势，"
                "成图不得出现从头顶向下压缩躯干和腿部的俯拍感"
            )
            camera["forbiddenFallback"] = "禁止改成俯拍、高机位向下观察或平视商品展示照"
            return camera
        camera["pitch"] = pitch or "水平机位，俯仰0度"
        camera["pitchDirection"] = "level"
        return camera

    if direction != "down" and "俯拍" not in pitch and "向下" not in pitch:
        return camera

    bottom_text = "；".join(
        [str(frame.get("bottomEdge") or ""), *normalize_text_list(frame.get("invisibleBodyParts"))]
    )
    lower_body_cropped = any(marker in bottom_text for marker in ("裁切", "不可见", "画外"))
    stair_only_evidence = (
        any(marker in evidence for marker in ("楼梯", "台阶", "踏面", "斜坡"))
        and lower_body_cropped
        and not any(
            marker in evidence
            for marker in ("自拍手臂", "镜头位于头顶", "明显看到头顶", "桌面顶面占画面", "肩部遮挡下半身")
        )
    )
    weak_floor_evidence = (
        strength == "subtle"
        and str(frame.get("shotScaleClass") or "") in {"environmental", "full", "near_full", "three_quarter"}
        and any(marker in evidence for marker in ("地面", "脚部", "脚下"))
        and (
            any(marker in evidence for marker in ("不明显", "基本平行", "无显著", "接近水平"))
            or "相机相对人物眼睛略低" in evidence
        )
        and not any(
            marker in evidence
            for marker in ("自拍手臂形成向下", "桌面顶面占画面", "头顶平面明显暴露")
        )
    )
    positive_pitch_categories = sum(
        (
            any(marker in evidence for marker in ("明显看到头顶", "头顶平面明显暴露", "镜头位于头顶", "相机明显高于")),
            any(marker in evidence for marker in ("近侧手臂明显放大", "近侧肢体明显放大", "肩部明显放大", "自拍手臂形成向下")),
            any(marker in evidence for marker in ("垂直线向下汇聚", "建筑线向下汇聚", "明显向下透视收缩")),
            any(marker in evidence for marker in ("桌面顶面占画面", "承载面顶面明显暴露", "顶面暴露比例明显")),
        )
    )
    posture_risk = str(camera.get("postureRisk") or "")
    posture_confusion = any(
        marker in posture_risk
        for marker in ("前倾", "低头", "弯腰", "坐姿", "屈膝", "姿势不能作为", "身体姿态")
    )
    weak_subtle_pitch = strength in {"subtle", "none"} and positive_pitch_categories < 2
    low_confidence_pitch = confidence in {"", "low"} and positive_pitch_categories < 2
    if stair_only_evidence or weak_floor_evidence or weak_subtle_pitch or low_confidence_pitch or (
        posture_confusion and positive_pitch_categories < 2
    ):
        camera["cameraHeight"] = camera.get("cameraHeight") or "相机约与人物胸口至眼睛之间同高"
        camera["pitchDirection"] = "level"
        camera["pitch"] = "水平机位，俯仰0度；不得保留任何向下观察感"
        camera["pitchConfidence"] = "medium"
        camera["pitchVisualStrength"] = "none"
        if stair_only_evidence:
            camera["mustPreserveAngleCue"] = (
                "楼梯踏面与栏杆的纵深来自楼梯自身高度差，人物仍保持平视侧拍透视，禁止生成明显俯拍或仰拍"
            )
        else:
            camera["mustPreserveAngleCue"] = (
                "建筑垂直线基本平行、人物头肩与躯干无明显近大远小，保持眼平视线；成图不得看见夸张头顶面积或产生向下压缩身体的俯拍感"
            )
        camera["forbiddenFallback"] = "禁止改成俯拍、从人物上方观察或夸张广角透视"
    return camera


def normalize_enum(value, allowed, default=""):
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else default


def build_reference_description_from_fields(data, frame):
    parts = []
    for key in (
        "personDescription",
        "poseDescription",
        "sceneDescription",
        "cameraDescription",
        "colorDescription",
    ):
        value = str(data.get(key) or "").strip() if isinstance(data, dict) else ""
        if value:
            clean = strip_reference_apparel_clauses(value)
            if clean:
                parts.append(clean.rstrip("。"))
    if not parts:
        scene_elements = normalize_text_list(frame.get("visibleSceneElements"))
        if scene_elements:
            parts.append("画内场景包括" + "、".join(scene_elements))
    return "。".join(parts) + ("。" if parts else "")


def remove_reference_product_appearance(value):
    text = strip_reference_apparel_clauses(value)
    if not text:
        return ""
    sentences = []
    current = []
    for character in text:
        current.append(character)
        if character in "。！？\n":
            sentence = "".join(current).strip()
            if sentence and "待替换商品区域" not in sentence and "原商品" not in sentence:
                sentences.append(sentence)
            current = []
    remainder = "".join(current).strip()
    if remainder and "待替换商品区域" not in remainder and "原商品" not in remainder:
        sentences.append(remainder)
    return "".join(sentences).strip()


def build_reference_frame_lock_text(reference_analysis):
    frame = reference_analysis.get("frameLock") if isinstance(reference_analysis, dict) else {}
    if not isinstance(frame, dict):
        return ""
    parts = []
    for label, key in (
        ("上边缘", "topEdge"),
        ("下边缘", "bottomEdge"),
        ("左边缘", "leftEdge"),
        ("右边缘", "rightEdge"),
    ):
        value = str(frame.get(key) or "").strip()
        if value:
            parts.append(f"{label}：{value}")
    top_person_y = frame.get("topPersonY")
    topmost_person_part = str(frame.get("topmostPersonPart") or "").strip()
    top_blank_evidence = str(frame.get("topBlankEvidence") or "").strip()
    if isinstance(top_person_y, int):
        top_blank_ratio = top_person_y / 10
        top_part_text = f"，人物最上方部位是{topmost_person_part}" if topmost_person_part else ""
        parts.append(
            f"顶部人物留白硬锁：画面顶部至人物任意可见像素最上端连续保留约{top_blank_ratio:.1f}%场景空间"
            f"{top_part_text}；这段顶部区域不得出现手指、手臂、头发、头部、服饰或商品"
        )
        if top_blank_evidence:
            parts.append("顶部留白双测量证据：" + top_blank_evidence)
    box = frame.get("visiblePersonBox")
    if isinstance(box, dict) and box:
        left_margin = box["x"] / 10
        top_margin = box["y"] / 10
        width_ratio = box["width"] / 10
        height_ratio = box["height"] / 10
        right_margin = max(0, 1000 - box["x"] - box["width"]) / 10
        bottom_margin = max(0, 1000 - box["y"] - box["height"]) / 10
        center_x = (box["x"] + box["width"] / 2) / 10
        center_y = (box["y"] + box["height"] / 2) / 10
        horizontal_background = max(0, 100 - width_ratio)
        vertical_background = max(0, 100 - height_ratio)
        parts.append(
            "参考图可见人物外接框（画布宽高各按1000计）："
            f"x={box['x']}，y={box['y']}，宽={box['width']}，高={box['height']}"
        )
        parts.append(
            "人物尺度不可改写："
            f"画内可见人物宽度约占画面{width_ratio:.1f}%，高度约占{height_ratio:.1f}%；"
            f"左、右、上、下边距分别约为{left_margin:.1f}%、{right_margin:.1f}%、"
            f"{top_margin:.1f}%、{bottom_margin:.1f}%，禁止放大、缩小、拉远、推进或重新居中"
        )
        placement = str(frame.get("horizontalPlacement") or "").strip()
        negative_space = str(frame.get("dominantNegativeSpace") or "").strip()
        placement_label = {"left": "画面左侧", "center": "画面中央", "right": "画面右侧"}.get(
            placement, "原横向位置"
        )
        negative_space_label = {"left": "画面左侧", "right": "画面右侧"}.get(
            negative_space
        )
        placement_text = (
            f"人物视觉中心固定在整图({center_x:.1f}%,{center_y:.1f}%)，属于{placement_label}构图"
        )
        if placement != "center":
            placement_text += "，这是明确的偏置构图而非居中构图，禁止把脸、胸口或人物外接框移回中轴线"
        if negative_space_label:
            placement_text += f"；主要背景负空间保留在{negative_space_label}"
        parts.append("人物横向落点硬锁：" + placement_text)
        placement_evidence = str(frame.get("horizontalPlacementEvidence") or "").strip()
        if placement_evidence:
            parts.append("横向位置像素证据：" + placement_evidence)
        edge_contacts = set(normalize_text_list(frame.get("edgeContacts")))
        edge_labels = {
            "left": "左边缘",
            "right": "右边缘",
            "top": "上边缘",
            "bottom": "下边缘",
        }
        if edge_contacts:
            parts.append(
                "人物贴边与裁切关系："
                + "、".join(edge_labels[item] for item in ("left", "right", "top", "bottom") if item in edge_contacts)
                + "存在人物像素贴边；必须保留相同贴边或自然裁切，不得为了完整展示人物而向画面中央移动"
            )
        parts.append(
            "镜头距离硬上限："
            f"人物外接框宽度不得超过画面{width_ratio:.1f}%、高度不得超过{height_ratio:.1f}%；"
            f"横向合计至少保留约{horizontal_background:.1f}%背景，纵向合计至少保留约{vertical_background:.1f}%背景；"
            "允许商品在画面中显得较小，但禁止为了看清商品而把人物放大成更近景别"
        )
        if top_margin >= 8:
            parts.append(
                f"画面顶部必须连续保留至少约{top_margin:.1f}%的原场景空间，人物头部不得侵入这段留白"
            )
        if left_margin >= 8:
            parts.append(f"人物左侧必须保留至少约{left_margin:.1f}%的原场景空间")
        if right_margin >= 8:
            parts.append(f"人物右侧必须保留至少约{right_margin:.1f}%的原场景空间")
        if bottom_margin >= 8:
            parts.append(f"人物下方必须保留至少约{bottom_margin:.1f}%的原场景空间")
    anchors = frame.get("scaleAnchors")
    if isinstance(anchors, dict) and anchors:
        anchor_parts = []
        for label, key in (("面部", "faceBox"), ("可见躯干", "torsoBox")):
            anchor_box = anchors.get(key)
            if isinstance(anchor_box, dict) and anchor_box:
                anchor_parts.append(
                    f"{label}框x={anchor_box['x']}、y={anchor_box['y']}、宽={anchor_box['width']}、高={anchor_box['height']}"
                    f"（约占画面宽{anchor_box['width'] / 10:.1f}%、高{anchor_box['height'] / 10:.1f}%）"
                )
        left_shoulder = anchors.get("leftShoulderX")
        right_shoulder = anchors.get("rightShoulderX")
        if isinstance(left_shoulder, int) and isinstance(right_shoulder, int) and right_shoulder > left_shoulder:
            anchor_parts.append(
                f"肩部横向跨度从x={left_shoulder}到x={right_shoulder}，约占画面宽{(right_shoulder - left_shoulder) / 10:.1f}%"
            )
        for label, key in (
            ("头顶", "headTopY"),
            ("下巴", "chinY"),
            ("胸部中心", "chestCenterY"),
            ("腰线", "waistY"),
            ("画内身体终点", "visibleBodyEndY"),
        ):
            value = anchors.get(key)
            if isinstance(value, int):
                anchor_parts.append(f"{label}位于画面高度约{value / 10:.1f}%处")
        if anchor_parts:
            parts.append("局部尺度与纵向落点锚点：" + "，".join(anchor_parts))
            parts.append(
                "镜头距离必须同时匹配面部、肩部和躯干尺度；四肢伸展或道具不得代替主体尺度判断，"
                "局部锚点与整体外接框冲突时，以面部框、躯干框和肩宽保持人物真实大小"
            )
    shot_scale = str(frame.get("shotScale") or "").strip()
    if shot_scale:
        parts.append("景别与人物占比判定：" + shot_scale)
    shot_scale_class = str(frame.get("shotScaleClass") or "").strip()
    if shot_scale_class:
        parts.append("结构化景别等级：" + shot_scale_class)
    scale_priority_cue = str(frame.get("scalePriorityCue") or "").strip()
    if scale_priority_cue:
        parts.append("最能证明景别的人像与背景关系：" + scale_priority_cue)
    visible = normalize_text_list(frame.get("visibleBodyParts"))
    invisible = normalize_text_list(frame.get("invisibleBodyParts"))
    if visible:
        parts.append("画内可见身体范围：" + "、".join(visible))
    if invisible:
        parts.append("画内完全不可见，禁止补出：" + "、".join(invisible))
    top_evidence = " ".join([str(frame.get("topEdge") or "")] + invisible)
    if any(
        keyword in top_evidence
        for keyword in ("头顶", "发顶", "额头", "头部", "脸", "面部", "五官", "眼睛", "鼻", "嘴", "下巴")
    ) and any(
        keyword in top_evidence for keyword in ("不可见", "裁切", "画外")
    ):
        parts.append("画面上边缘必须严格按参考图原位置横切头部或脸部，不得向上扩图、缩小人物或补出原图不可见的发顶、额头、五官和头顶背景留白")
    bottom_evidence = " ".join([str(frame.get("bottomEdge") or "")] + invisible)
    if any(keyword in bottom_evidence for keyword in ("脚", "脚踝")) and any(
        keyword in bottom_evidence for keyword in ("不可见", "裁切", "画外")
    ):
        parts.append("画面下边缘必须按参考图位置横切下肢，禁止补出完整脚部、鞋子或额外地面")
    if any(keyword in " ".join(visible) for keyword in ("腿", "脚踝", "裙摆")):
        parts.append("景别必须覆盖参考图中从上边缘到下肢的全部可见人物范围，禁止改成半身、胸像、上半身或商品特写")
    if not parts:
        return ""
    return "构图硬锁（优先级最高）：" + "；".join(parts) + "。"


def build_reference_camera_lock_text(reference_analysis):
    camera = reference_analysis.get("cameraLock") if isinstance(reference_analysis, dict) else {}
    if not isinstance(camera, dict):
        return ""
    parts = []
    for label, key in (
        ("相机高度", "cameraHeight"),
        ("俯仰方向", "pitchDirection"),
        ("俯仰角", "pitch"),
        ("俯仰置信度", "pitchConfidence"),
        ("俯仰视觉强度", "pitchVisualStrength"),
        ("垂直线与消失点证据", "verticalLineEvidence"),
        ("平面可见证据", "surfacePlaneEvidence"),
        ("人体透视证据", "bodyPerspectiveEvidence"),
        ("姿势干扰排除", "postureRisk"),
        ("必须保留的角度视觉证据", "mustPreserveAngleCue"),
        ("水平偏转", "yaw"),
        ("画面滚转", "roll"),
        ("35mm等效焦距", "focalLength35mm"),
        ("镜头类型", "lensClass"),
        ("焦距判断置信度", "focalConfidence"),
        ("焦距透视证据", "lensEvidence"),
        ("距离与镜头关系", "distanceAndLens"),
        ("透视证据", "perspectiveEvidence"),
        ("禁止回退", "forbiddenFallback"),
    ):
        value = str(camera.get(key) or "").strip()
        if value:
            parts.append(f"{label}：{value}")
    if not parts:
        return ""
    return (
        "机位硬锁（与构图同级，禁止省略或改成默认平视）："
        + "；".join(parts)
        + "。最终 prompt 必须在构图第一句之后立即用一句话写出相机高度、俯仰、水平偏转和画面滚转；"
        "俯拍、仰拍、斜拍、自拍臂长透视均不得归一化为正面平视；"
        "当俯仰视觉强度不是 none 时，最终画面必须能从地面或顶面可见量、头身透视和空间线条中直接看出该方向，不能只有文字标注而视觉仍像平视。"
    )


def build_reference_appearance_lock_text(reference_analysis):
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    if not isinstance(appearance, dict):
        return ""
    parts = []
    for label, key in (
        ("人物性别呈现", "genderPresentation"),
        ("可见肤色", "visibleSkinTone"),
        ("面部肤色与皮肤成像", "facialSkinRendering"),
        ("体型轮廓", "bodySilhouette"),
        ("胸腰腿等可见体型比例", "bodyProportions"),
        ("胸部显著度分级", "bustLevel"),
        ("胸部判断置信度", "bustConfidence"),
        ("胸部判断的透视与服饰干扰", "bustPerspectiveRisk"),
        ("必须优先继承的视觉核心特征", "visualSalience"),
        ("人物成人年龄段与角色感", "subjectPresence"),
        ("嘴部微表情", "mouthMicroExpression"),
        ("人物大类外观呈现", "demographicAppearance"),
        ("面部可见性与双眼状态", "faceVisibility"),
        ("姿态类别与承重支撑", "postureAndSupport"),
        ("身体朝向与侧身程度", "bodyOrientation"),
        ("动作关键帧", "actionKeyframe"),
        ("肢体数量与唯一接触拓扑", "limbTopology"),
        ("禁止回退的错误姿势", "forbiddenPoseFallback"),
        ("拍摄者与持机类型", "captureType"),
        ("自拍与持手机关系", "selfieRelation"),
        ("近镜头或标志性道具的画面几何", "foregroundObjectGeometry"),
        ("身体各段与承载面的几何关系", "poseSurfaceGeometry"),
        ("行走与台阶运动几何", "locomotionGeometry"),
        ("头部角度允许范围", "headPoseRange"),
        ("光线物理特征", "lightingPhysics"),
        ("结构化光型", "lightingMode"),
        ("闪光判断置信度", "flashConfidence"),
        ("必须保留的光线视觉证据", "mustPreserveLightingCue"),
        ("高光边缘、辉光与溢出方式", "highlightBehavior"),
        ("背景颜色关系", "backgroundColorRelation"),
        ("全局综合色偏", "globalColorBias"),
        ("中性色锚点校验", "neutralAnchorAudit"),
        ("对比度与明暗曲线", "toneProfile"),
        ("绝对色彩锚点与禁止偏色", "colorAnchor"),
        ("拍摄模式", "captureMode"),
        ("真实拍摄与成像特征", "captureRealism"),
        ("环境空间的真实成像", "environmentRealism"),
    ):
        value = strip_reference_apparel_clauses(appearance.get(key))
        if value:
            parts.append(f"{label}：{value}")
    contacts = sanitize_reference_apparel_list(appearance.get("poseContacts"))
    if contacts:
        parts.append("动作接触与前后层级：" + "、".join(contacts))
    hand_position_audit = appearance.get("handPositionAudit")
    if isinstance(hand_position_audit, list) and hand_position_audit:
        hand_items = []
        for item in hand_position_audit:
            if not isinstance(item, dict):
                continue
            side = "画面左侧" if item.get("screenSide") == "left" else "画面右侧"
            position = f"中心坐标({item.get('centerX')},{item.get('centerY')})"
            contact = str(item.get("contact") or "").strip()
            visibility = str(item.get("visibility") or "").strip()
            detail = "，".join(value for value in (position, contact, visibility) if value)
            hand_items.append(f"{side}手：{detail}")
        if hand_items:
            parts.append("逐手坐标审计（优先级高于文字方向描述）：" + "；".join(hand_items))
    direction_anchors = sanitize_reference_apparel_list(
        appearance.get("directionAnchors")
    )
    if direction_anchors:
        parts.append("不可互换的画面方向锚点：" + "、".join(direction_anchors))
    snapshot_imperfections = normalize_text_list(appearance.get("snapshotImperfections"))
    if snapshot_imperfections:
        parts.append("生活快照不完美证据：" + "、".join(snapshot_imperfections))
    bust_evidence = sanitize_reference_apparel_list(appearance.get("bustEvidence"))
    if bust_evidence:
        parts.append("胸部显著度的独立轮廓证据：" + "、".join(bust_evidence))
    wardrobe = normalize_text_list(appearance.get("nonTargetWardrobe"))
    if wardrobe:
        parts.append(
            "商品未覆盖区域的粗粒度覆盖关系（不含任何旧服饰外观）："
            + "、".join(wardrobe)
        )
    wearables = sanitize_non_target_wearables(appearance.get("nonTargetWearables"))
    if wearables:
        parts.append(
            "商品未覆盖的可见鞋袜与配饰（保留其实际外观，不属于旧服装主体）："
            + "、".join(wearables)
        )
    flash_evidence = normalize_text_list(appearance.get("flashEvidence"))
    if flash_evidence:
        parts.append("闪光灯像素证据：" + "、".join(flash_evidence))
    daylight_evidence = normalize_text_list(appearance.get("daylightEvidence"))
    if daylight_evidence:
        parts.append("日光与环境光证据：" + "、".join(daylight_evidence))
    ccd_evidence = normalize_text_list(appearance.get("ccdEvidence"))
    if ccd_evidence:
        parts.append("CCD 成像证据：" + "、".join(ccd_evidence))
    if not parts:
        return ""
    return (
        "人物、姿态、光色与真实感硬锁（换脸不得改动这些非身份特征）："
        + "；".join(parts)
        + "。"
    )


def build_reference_frame_execution_lock_text(reference_analysis):
    frame = reference_analysis.get("frameLock") if isinstance(reference_analysis, dict) else {}
    if not isinstance(frame, dict):
        return ""
    parts = []
    shot_scale = str(frame.get("shotScale") or "").strip()
    if shot_scale:
        parts.append(shot_scale)
    box = frame.get("visiblePersonBox")
    if isinstance(box, dict) and box:
        center_x = (box["x"] + box["width"] / 2) / 10
        center_y = (box["y"] + box["height"] / 2) / 10
        placement = str(frame.get("horizontalPlacement") or "").strip()
        negative_space = str(frame.get("dominantNegativeSpace") or "").strip()
        parts.append(
            f"人物连同画内可见四肢的外接框宽约占{box['width'] / 10:.1f}%、高约占{box['height'] / 10:.1f}%"
        )
        parts.append(
            f"左、右边距约{box['x'] / 10:.1f}%、{max(0, 1000 - box['x'] - box['width']) / 10:.1f}%"
        )
        placement_label = {"left": "画面左侧", "center": "画面中央", "right": "画面右侧"}.get(
            placement, "参考图原位置"
        )
        placement_rule = f"人物中心固定在({center_x:.1f}%,{center_y:.1f}%)的{placement_label}"
        if placement != "center":
            placement_rule += "，明确禁止移到画面中央"
        negative_space_label = {"left": "左侧", "right": "右侧"}.get(negative_space)
        if negative_space_label:
            placement_rule += f"，主要背景负空间位于画面{negative_space_label}"
        parts.append(placement_rule)
        edge_contacts = set(normalize_text_list(frame.get("edgeContacts")))
        if edge_contacts:
            edge_labels = {
                "left": "左边缘",
                "right": "右边缘",
                "top": "上边缘",
                "bottom": "下边缘",
            }
            parts.append(
                "人物保持贴近"
                + "、".join(edge_labels[item] for item in ("left", "right", "top", "bottom") if item in edge_contacts)
                + "的原始裁切关系"
            )
    top_person_y = frame.get("topPersonY")
    if isinstance(top_person_y, int):
        parts.append(f"人物任意可见像素上方连续保留约{top_person_y / 10:.1f}%纯场景空间")
    bottom_edge = str(frame.get("bottomEdge") or "").strip()
    if bottom_edge:
        parts.append("下边缘" + bottom_edge)
    if not parts:
        return ""
    return (
        "成图构图与景别执行锁（直接控制最终渲染，不得被服饰细节覆盖）："
        + "；".join(parts)
        + "。即使商品在画面中显得较小，也禁止推进镜头、放大人物、改成更近景别、重新居中或交换左右背景负空间。"
    )


def build_reference_layout_execution_lock_text(reference_analysis):
    layout = reference_analysis.get("layoutLock") if isinstance(reference_analysis, dict) else {}
    if not isinstance(layout, dict) or layout.get("layoutType") != "grid":
        return ""
    rows = layout.get("rows")
    columns = layout.get("columns")
    panel_count = layout.get("panelCount")
    if rows == 2 and columns == 2 and panel_count == 4:
        layout_name = "2×2四宫格"
    elif rows and columns:
        layout_name = f"{rows}×{columns}多宫格"
    elif panel_count:
        layout_name = f"{panel_count}格拼图"
    else:
        layout_name = "多宫格拼图"

    parts = []
    for panel in layout.get("panels") or []:
        if not isinstance(panel, dict):
            continue
        details = [
            str(panel.get("crop") or "").strip(),
            str(panel.get("subjectPosition") or "").strip(),
            normalize_screen_coordinate_text(panel.get("pose")),
        ]
        details = [detail for detail in details if detail]
        if details:
            parts.append(f"{panel.get('position') or '分格'}：{'，'.join(details)}")

    divider = str(layout.get("dividerDescription") or "").strip()
    continuity = str(layout.get("sharedContinuity") or "").strip()
    lock = (
        f"拼图版式最高优先级硬锁：最终输出必须是一张完整的{layout_name}，"
        "各画格边界清楚、尺寸与排列严格沿用参考图；不得生成单张照片，不得只保留其中一格，"
        "不得把多格动作合并成同一个人物姿势。每格都必须使用同一位新人物、同一件用户商品和参考图一致的背景光色，"
        "但分别执行该格自己的构图、裁切、人物位置、表情和动作。"
    )
    if divider:
        lock += f"分隔方式：{divider}。"
    if continuity:
        lock += f"跨格连续性：{continuity}。"
    if parts:
        lock += "逐格执行：" + "；".join(parts) + "。"
    return lock


def build_reference_direction_execution_lock_text(reference_analysis):
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    if not isinstance(appearance, dict):
        return ""
    anchors = normalize_text_list(appearance.get("directionAnchors"))[:6]
    if not anchors:
        return ""
    screen_only_anchors = [normalize_screen_coordinate_text(anchor) for anchor in anchors]
    return (
        "最高优先级画面方向锁：禁止整幅水平镜像或交换左右。"
        + "；".join(screen_only_anchors)
        + "。这些位置以最终成图的画面左侧和画面右侧为准，逐条不可互换。"
    )


def build_reference_pose_execution_lock_text(reference_analysis):
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    if not isinstance(appearance, dict):
        return ""
    values = [
        normalize_screen_coordinate_text(appearance.get("actionKeyframe")),
        normalize_screen_coordinate_text(appearance.get("poseSurfaceGeometry")),
        normalize_screen_coordinate_text(appearance.get("locomotionGeometry")),
        normalize_screen_coordinate_text(appearance.get("forbiddenPoseFallback")),
    ]
    values = [value for value in values if value]
    if not values:
        return ""
    return (
        "最高优先级动作几何锁："
        + "；".join(values)
        + "。肩到肘到手、髋到膝到踝到脚在二维画面中的方向、夹角、终点、交叉遮挡和承载面接触均不可改成默认站姿或默认坐姿；"
        "行走或上下台阶时，行进方向、领先腿/滞后腿、脚掌台阶接触和重心腿均不得重置。"
    )


def normalize_screen_coordinate_text(value):
    """Keep pose directions in image coordinates so anatomy labels cannot mirror them."""
    text = re.sub(
        r"[（(]人物[左右](?:手|臂|肩|髋|腿|膝|脚|眼|耳)[）)]",
        "",
        str(value or ""),
    ).strip()
    text = re.sub(r"[（(][^（）()]{0,20}解剖[^（）()]{0,20}[）)]", "", text)
    body_part_pattern = r"(?:手臂|大腿|小腿|手|臂|肩|髋|腿|膝|脚|眼|耳)"
    text = re.sub(
        rf"(?<!画面)([左右])侧({body_part_pattern})",
        lambda match: f"画面{match.group(1)}侧{match.group(2)}",
        text,
    )

    def clean_screen_segment(match):
        prefix, segment = match.groups()
        segment = re.sub(rf"[左右]({body_part_pattern})", r"\1", segment)
        return prefix + segment

    text = re.sub(r"(画面[左右]侧)([^；。，、]*)", clean_screen_segment, text)
    return text


def build_reference_lighting_execution_lock_text(reference_analysis):
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    if not isinstance(appearance, dict):
        return ""
    mode = str(appearance.get("lightingMode") or "").strip()
    cue = str(appearance.get("mustPreserveLightingCue") or "").strip()
    physics = str(appearance.get("lightingPhysics") or "").strip()
    highlight_behavior = str(appearance.get("highlightBehavior") or "").strip()
    evidence = cue or physics
    highlight_lock = (
        f"高光边缘与扩散必须照参考图执行：{highlight_behavior}；"
        "若存在局部辉光、轻微雾化或高光溢出，成图中必须肉眼可见，不能清理成均匀、锐利、无扩散的商业人像光。"
        if highlight_behavior and not any(marker in highlight_behavior for marker in ("无辉光", "不存在辉光", "无溢出"))
        else ""
    )
    if mode == "direct_sun":
        return (
            "最高优先级光感锁：保留参考图肉眼可见的直射阳光，人物、服饰和背景必须共享同一主光方向，"
            "真实受光面出现与参考图同位置、同范围、同边缘软硬的明亮高光斑，背光面保留方向明确、边缘相对清楚的自然阴影；"
            "脸、颈、手臂和服饰只在实际受光区域变亮，未受光区域不得同步提亮、发黄或被统一美白，禁止改成均匀柔光或棚拍补光。"
            + (f"可见证据：{evidence}。" if evidence else "")
            + highlight_lock
        )
    if mode == "mixed":
        return (
            "最高优先级光感锁：保留参考图直射阳光与环境反射共同存在的混合光，局部阳光斑和方向性阴影必须可见，"
            "环境补光只能抬起暗部，不能把直射光抹平成均匀柔光；皮肤基础色与环境综合色分开执行，"
            "阳光只改变命中区域的亮度和局部色温，不得把整张脸统一染黄。"
            + (f"可见证据：{evidence}。" if evidence else "")
            + highlight_lock
        )
    if mode in {"near_axis_flash", "fill_flash"}:
        return (
            "最高优先级光感锁：闪光灯必须直接可见为近镜头轴的正面瞬间提亮、较平的贴轴阴影和由近到远的亮度衰减，"
            "禁止退化成自然柔光或商业棚拍。"
            + (f"可见证据：{evidence}。" if evidence else "")
            + highlight_lock
        )
    return ""


def build_reference_face_exposure_lock_text(reference_analysis):
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    if not isinstance(appearance, dict):
        return ""
    face_visibility = str(appearance.get("faceVisibility") or "").strip()
    if not face_visibility or any(marker in face_visibility for marker in ("面部不入画", "面部完全不可见")):
        return ""
    skin_tone = str(appearance.get("visibleSkinTone") or "").strip()
    facial_rendering = str(appearance.get("facialSkinRendering") or "").strip()
    background_relation = str(appearance.get("backgroundColorRelation") or "").strip()
    lighting_mode = str(appearance.get("lightingMode") or "").strip()
    if lighting_mode in {"near_axis_flash", "fill_flash"}:
        return ""
    exposure_target = "额头、鼻梁和颧骨高光不过曝，暗部不压黑"
    details = "；".join(value for value in (skin_tone, facial_rendering) if value)
    return (
        "脸部精准曝光：测光优先锁定参考图的面部中间调和肤色明度，"
        + exposure_target
        + "；眼白保持中性，皮肤不被环境色统一染黄或染青，保留自然血色、毛孔和局部纹理；"
        + (f"面部依据：{details}；" if details else "")
        + (f"背景关系仍为：{background_relation}；" if background_relation else "")
        + "不得为了脸部曝光而同步提亮、压暗或虚化背景，也不得改成商业棚拍磨皮人像。"
    )


def enforce_flash_exposure_consistency(prompt, reference_analysis):
    """Remove softer exposure wording that competes with an observed flash look."""
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    if not isinstance(appearance, dict):
        return prompt
    lighting_mode = str(appearance.get("lightingMode") or "").strip()
    skin_tone = str(appearance.get("visibleSkinTone") or "").strip()
    if lighting_mode not in {"near_axis_flash", "fill_flash"} or "冷白皮" not in skin_tone:
        return prompt

    replacements = {
        "人物正面有轻微近轴补光效果": "人物正面有清晰可见的近轴闪光效果",
        "采用轻微正面闪光灯补光": "采用清晰可见的近轴正面闪光灯补光",
        "人物正面略亮于同距离环境": "人物皮肤明显亮于同距离环境",
        "自动曝光使人物略亮于环境": "闪光使人物皮肤明显亮于环境",
        "高光滚降柔和无溢出": "皮肤高光接近曝光上限并有可见的轻微溢出",
        "高光柔和无溢出": "皮肤高光接近曝光上限并有可见的轻微溢出",
        "高光柔和": "皮肤高光接近曝光上限",
    }
    for source, target in replacements.items():
        prompt = prompt.replace(source, target)
    return prompt


def compact_prompt_text(value, max_chars):
    """Normalize and clip a prompt fragment at a sentence boundary."""
    text = re.sub(r"\s+", " ", str(value or "")).strip(" ；。")
    if not text or len(text) <= max_chars:
        return text
    floor = max(1, int(max_chars * 0.62))
    boundary = max(text.rfind(marker, floor, max_chars + 1) for marker in "。；，")
    if boundary < floor:
        boundary = max_chars
    return text[: boundary + 1].rstrip(" ；，。")


def build_core_replication_contract(reference_analysis):
    """Keep every fidelity-critical dimension in the rendered prompt."""
    if not isinstance(reference_analysis, dict):
        return ""
    frame = reference_analysis.get("frameLock")
    camera = reference_analysis.get("cameraLock")
    appearance = reference_analysis.get("appearanceLock")
    frame = frame if isinstance(frame, dict) else {}
    camera = camera if isinstance(camera, dict) else {}
    appearance = appearance if isinstance(appearance, dict) else {}

    slots = []
    box = frame.get("visiblePersonBox")
    composition = []
    if isinstance(box, dict) and all(
        isinstance(box.get(key), int) for key in ("x", "y", "width", "height")
    ):
        right = max(0, 1000 - box["x"] - box["width"])
        bottom = max(0, 1000 - box["y"] - box["height"])
        composition.append(
            f"人物框宽{box['width'] / 10:.1f}%高{box['height'] / 10:.1f}%，"
            f"左上({box['x'] / 10:.1f}%,{box['y'] / 10:.1f}%)，"
            f"右空{right / 10:.1f}%下空{bottom / 10:.1f}%"
        )
    for value in (
        frame.get("shotScaleClass"),
        frame.get("shotScale"),
        frame.get("scalePriorityCue"),
        frame.get("topEdge"),
        frame.get("bottomEdge"),
    ):
        value = compact_prompt_text(value, 54)
        if value:
            composition.append(value)
    if composition:
        slots.append("【构图·景别·人物位置】" + "；".join(composition[:5]))

    camera_values = [
        compact_prompt_text(camera.get(key), limit)
        for key, limit in (
            ("cameraHeight", 46),
            ("pitch", 46),
            ("yaw", 42),
            ("roll", 34),
            ("focalLength35mm", 32),
            ("lensEvidence", 52),
            ("distanceAndLens", 52),
            ("mustPreserveAngleCue", 64),
        )
    ]
    camera_values = [value for value in camera_values if value]
    if camera_values:
        slots.append("【机位·透视】" + "；".join(camera_values))

    action_values = []
    limb_topology = compact_prompt_text(appearance.get("limbTopology"), 100)
    if limb_topology:
        action_values.append(limb_topology)
    action_values.extend(
        value
        for value in (
            compact_prompt_text(
                normalize_screen_coordinate_text(appearance.get("actionKeyframe")), 120
            ),
            compact_prompt_text(
                normalize_screen_coordinate_text(appearance.get("bodyOrientation")), 90
            ),
            compact_prompt_text(appearance.get("postureAndSupport"), 75),
        )
        if value
    )
    contacts = [
        compact_prompt_text(normalize_screen_coordinate_text(value), 78)
        for value in normalize_text_list(appearance.get("poseContacts"))[:4]
    ]
    action_values.extend(value for value in contacts if value)
    hand_audit_values = []
    for item in appearance.get("handPositionAudit") or []:
        if not isinstance(item, dict):
            continue
        center_x = item.get("centerX")
        center_y = item.get("centerY")
        if not isinstance(center_x, int) or not isinstance(center_y, int):
            continue
        side = "画面左侧" if center_x < 500 else "画面右侧"
        details = compact_prompt_text(
            "，".join(
                str(value).strip()
                for value in (
                    item.get("contact"),
                    item.get("visibility"),
                    item.get("evidence"),
                )
                if str(value or "").strip()
            ),
            58,
        )
        audit = f"{side}手心约在({center_x / 10:.1f}%,{center_y / 10:.1f}%)"
        if details:
            audit += "，" + details
        hand_audit_values.append(audit)
    if hand_audit_values:
        action_values.append(
            "逐手坐标审计（坐标优先于其它左右文字）："
            + "；".join(hand_audit_values[:2])
        )
    if action_values:
        slots.append(
            "【动作·肢体拓扑】仅一名人物，人体只有正常两条手臂和两只手；"
            "只生成参考图明确可见的手，画外或遮挡的手不得补出；"
            "每只手唯一对应一条手臂和一个动作接触点，禁止额外手臂、手腕、掌心或手指簇；"
            + "；".join(action_values)
        )

    person_values = [
        compact_prompt_text(appearance.get(key), limit)
        for key, limit in (
            ("subjectPresence", 82),
            ("faceVisibility", 64),
            ("mouthMicroExpression", 82),
            ("headPoseRange", 70),
            ("visibleSkinTone", 68),
            ("bodySilhouette", 62),
        )
    ]
    person_values = [value for value in person_values if value]
    if person_values:
        slots.append("【人物状态·表情】" + "；".join(person_values))

    wearables = sanitize_non_target_wearables(appearance.get("nonTargetWearables"))
    if wearables:
        slots.append(
            "【非替换穿戴物】保留实际品类、颜色、结构和可见位置："
            + "；".join(compact_prompt_text(value, 60) for value in wearables[:4])
            + "；不得省略、改色或默认改成赤脚"
        )

    background_values = [
        compact_prompt_text(value, 68)
        for value in normalize_text_list(appearance.get("backgroundStructureAnchors"))[:4]
    ]
    background_values.extend(
        value
        for value in (
            compact_prompt_text(appearance.get("backgroundColorRelation"), 82),
            compact_prompt_text(appearance.get("environmentRealism"), 78),
            compact_prompt_text(appearance.get("foregroundObjectGeometry"), 110),
        )
        if value
    )
    background_values = [value for value in background_values if value]
    if not background_values:
        fallback_scene = compact_prompt_text(reference_analysis.get("referenceDescription"), 150)
        if fallback_scene:
            background_values.append(fallback_scene)
    if background_values:
        slots.append("【环境·位置·细节】" + "；".join(background_values))

    light_values = [
        compact_prompt_text(appearance.get(key), limit)
        for key, limit in (
            ("lightingPhysics", 105),
            ("mustPreserveLightingCue", 82),
            ("highlightBehavior", 65),
            ("globalColorBias", 82),
            ("toneProfile", 72),
            ("colorAnchor", 80),
        )
    ]
    light_values = [value for value in light_values if value]
    if light_values:
        slots.append("【光线·曝光·色彩】" + "；".join(light_values))

    realism_values = [
        compact_prompt_text(appearance.get(key), limit)
        for key, limit in (("captureMode", 70), ("captureRealism", 105))
    ]
    realism_values.extend(
        compact_prompt_text(value, 58)
        for value in normalize_text_list(appearance.get("snapshotImperfections"))[:3]
    )
    realism_values = [value for value in realism_values if value]
    if realism_values:
        slots.append("【真实成像质感】" + "；".join(realism_values))

    return " ".join(slots)


def extract_pose_clauses(value, keywords, max_chars):
    """Keep pose clauses that contain the requested anatomical evidence."""
    text = re.sub(r"\s+", " ", str(value or "")).strip(" ；。")
    if not text:
        return ""
    clauses = [clause.strip(" ；，。") for clause in re.split(r"[；。]", text)]
    selected = [clause for clause in clauses if any(keyword in clause for keyword in keywords)]
    return compact_prompt_text("；".join(selected), max_chars)


def sanitize_apparel_render_prompt(prompt, reference_analysis):
    """Remove polished-camera language that competes with a casual reference look."""
    text = re.sub(r"\s+", " ", str(prompt or "")).strip()
    replacements = {
        "整体成像干净现代": "普通真实相机直出",
        "成像干净现代": "普通真实相机直出",
        "现代消费级相机直出": "普通消费级相机生活直出",
        "自动曝光准确": "自动曝光遵循参考图并保留轻微自然波动",
        "白平衡稳定": "白平衡遵循参考图",
        "画面中心至边缘清晰度均匀": "中心与边缘清晰度存在轻微自然差异",
        "无明显噪点": "不额外强化噪点",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)

    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    lighting_mode = str(appearance.get("lightingMode") or "") if isinstance(appearance, dict) else ""
    if lighting_mode in {"near_axis_flash", "fill_flash"}:
        flash_replacements = {
            "无高光溢出或数码截断": "受闪光皮肤高光允许轻微溢出但保留五官与纹理",
            "无高光溢出": "受闪光皮肤高光允许轻微溢出",
            "高光不过曝": "皮肤高光接近曝光上限并允许轻微过曝",
            "高光柔和滚降无溢出": "皮肤高光接近曝光上限并有轻微溢出",
        }
        for source, target in flash_replacements.items():
            text = text.replace(source, target)
    return text


def strip_competing_apparel_composition_sentences(prompt):
    """Remove duplicate camera/box numbers after the calibrated render contract."""
    text = re.sub(r"\s+", " ", str(prompt or "")).strip()
    if not text:
        return ""
    conflict_markers = (
        "画面顶部连续",
        "人物连同伸展四肢",
        "人物整体高度",
        "人物高度约占",
        "人物最高点位于",
        "左侧留白",
        "右侧留白",
        "底部留白",
        "相机略高于",
        "相机略低于",
        "相机位于人物",
        "拍摄距离约",
        "近距离自拍臂长",
    )
    sentences = re.split(r"(?<=[。；])", text)
    kept = []
    for sentence in sentences:
        normalized = sentence.strip()
        if not normalized:
            continue
        if any(marker in normalized for marker in conflict_markers):
            continue
        kept.append(normalized)
    return "".join(kept).strip()


def build_compact_reference_render_priority_prefix(reference_analysis):
    """Keep only the highest-value locks ahead of the generated scene prompt."""
    frame = reference_analysis.get("frameLock") if isinstance(reference_analysis, dict) else {}
    camera = reference_analysis.get("cameraLock") if isinstance(reference_analysis, dict) else {}
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    frame = frame if isinstance(frame, dict) else {}
    camera = camera if isinstance(camera, dict) else {}
    appearance = appearance if isinstance(appearance, dict) else {}

    parts = []
    deferred_pose_part = ""
    deferred_color_part = ""
    deferred_background_part = ""
    box = frame.get("visiblePersonBox")
    if isinstance(box, dict) and all(isinstance(box.get(key), int) for key in ("x", "y", "width", "height")):
        left = box["x"] / 10
        top = box["y"] / 10
        width = box["width"] / 10
        height = box["height"] / 10
        right = max(0, 1000 - box["x"] - box["width"]) / 10
        bottom = max(0, 1000 - box["y"] - box["height"]) / 10
        parts.append(
            f"构图锁：人物框宽{width:.1f}%高{height:.1f}%，左上({left:.1f}%,{top:.1f}%)，"
            f"右空{right:.1f}%下空{bottom:.1f}%；误差≤4%，不得推进或改变身体裁切"
        )
        scale_anchors = frame.get("scaleAnchors")
        scale_anchors = scale_anchors if isinstance(scale_anchors, dict) else {}
        face_box = scale_anchors.get("faceBox")
        torso_box = scale_anchors.get("torsoBox")
        scale_parts = []
        if isinstance(face_box, dict) and face_box:
            scale_parts.append(
                f"脸部外框宽{face_box['width'] / 10:.1f}%、高{face_box['height'] / 10:.1f}%"
            )
        if isinstance(torso_box, dict) and torso_box:
            scale_parts.append(
                f"肩至腰胴干框宽{torso_box['width'] / 10:.1f}%、高{torso_box['height'] / 10:.1f}%"
            )
        if scale_parts:
            parts.append("内部尺度：" + "，".join(scale_parts) + "；四肢或道具不改变脸和躯干尺度")
        shot_scale_class = str(frame.get("shotScaleClass") or "").strip()
        if shot_scale_class in {"environmental", "full"} and height <= 75:
            render_height = max(35, height * 0.72)
            render_width = max(15, width * 0.72)
            parts.append(
                f"防自动放大：先按人物宽≤{render_width:.1f}%高≤{render_height:.1f}%渲染，"
                "脚部/身体终点仍落原下边缘"
            )
        elif shot_scale_class in {"near_full", "three_quarter"} and height <= 78:
            render_height = max(42, height * 0.76)
            render_width = max(20, width * 0.76)
            parts.append(
                f"防自动放大：先按人物宽≤{render_width:.1f}%高≤{render_height:.1f}%渲染，"
                "脚部/身体终点仍落原下边缘"
            )
        elif shot_scale_class == "medium" and top >= 20 and height <= 80:
            render_height = max(42, height * 0.75)
            render_width = max(22, width * 0.75)
            parts.append(
                f"防伸手放大：先按人物宽≤{render_width:.1f}%高≤{render_height:.1f}%渲染，"
                "优先服从脸框和躯干框"
            )
    top_person_y = frame.get("topPersonY")
    if isinstance(top_person_y, int) and top_person_y >= 80:
        parts.append(f"顶部{top_person_y / 10:.1f}%只留场景，人物不得进入")

    camera_values = [
        str(camera.get(key) or "").strip()
        for key in ("cameraHeight", "pitch", "yaw", "roll", "focalLength35mm", "distanceAndLens")
    ]
    angle_cue = compact_prompt_text(camera.get("mustPreserveAngleCue"), 42)
    forbidden_camera = compact_prompt_text(camera.get("forbiddenFallback"), 35)
    camera_values = [compact_prompt_text(value, 34) for value in camera_values if value]
    if camera_values:
        camera_part = "机位锁：" + "，".join(camera_values)
        if angle_cue:
            camera_part += "；证据：" + angle_cue
        camera_part += "；禁：" + (forbidden_camera or "默认正面平视")
        parts.append(camera_part)

    skin_tone = compact_prompt_text(appearance.get("visibleSkinTone"), 100)
    global_bias = compact_prompt_text(appearance.get("globalColorBias"), 100)
    tone_profile = compact_prompt_text(appearance.get("toneProfile"), 70)
    if skin_tone or global_bias:
        color_part = "肤色与色调锁："
        if skin_tone:
            color_part += skin_tone
        if global_bias:
            color_part += "；综合色：" + global_bias
        if tone_profile:
            color_part += "；明暗：" + tone_profile
        color_part += "；肤色必须落实到脸、颈和手臂，不得被环境色统一染黄或染青"
        deferred_color_part = color_part

    background_anchors = normalize_text_list(appearance.get("backgroundStructureAnchors"))
    background_anchors.sort(key=lambda value: "镜" not in value)
    background_anchors = [compact_prompt_text(value, 48) for value in background_anchors[:2]]
    background_anchors = [value for value in background_anchors if value]
    if background_anchors:
        background_part = "场景骨架：" + "；".join(background_anchors) + "；位置、尺度和层级不变"
        if any("镜" in value for value in background_anchors):
            background_part += "；镜框、镜面和反射必须入画"
        deferred_background_part = background_part

    pose_specs = [
        (appearance.get("bodyOrientation"), 48),
        (appearance.get("actionKeyframe"), 58),
        (appearance.get("postureAndSupport"), 52),
        (appearance.get("poseSurfaceGeometry"), 58),
        (appearance.get("locomotionGeometry"), 48),
    ]
    pose_specs.extend((value, 38) for value in normalize_text_list(appearance.get("poseContacts"))[:1])
    pose_specs.extend((value, 38) for value in normalize_text_list(appearance.get("directionAnchors"))[:2])
    pose_values = [
        compact_prompt_text(normalize_screen_coordinate_text(value), limit)
        for value, limit in pose_specs
        if value
    ]
    if pose_values:
        deferred_pose_part = "动作方向锁：禁止整幅水平翻转；" + "；".join(pose_values)

    if deferred_background_part:
        parts.append(deferred_background_part)
    if deferred_pose_part:
        parts.append(deferred_pose_part)
    if deferred_color_part:
        parts.append(deferred_color_part)

    lighting_mode = str(appearance.get("lightingMode") or "").strip()
    lighting_cue = compact_prompt_text(appearance.get("mustPreserveLightingCue"), 125)
    if lighting_mode in {"near_axis_flash", "fill_flash"}:
        parts.append(
            "光感锁：近镜头轴闪光直接提亮人物正面，贴轴阴影、皮肤小面积高光和近亮远暗衰减必须肉眼可见；"
            "禁止改成自然柔光或棚拍" + (f"；证据：{lighting_cue}" if lighting_cue else "")
        )
    elif lighting_mode == "direct_sun":
        parts.append(
            "光感锁：保留直射阳光的方向、高光斑和清楚阴影，人物与背景共享同一主光；禁止改成均匀柔光"
            + (f"；证据：{lighting_cue}" if lighting_cue else "")
        )
    elif lighting_mode:
        parts.append("光感锁：" + compact_prompt_text(appearance.get("lightingPhysics") or lighting_cue, 145))

    glow_evidence = [
        compact_prompt_text(value, 70)
        for value in normalize_text_list(appearance.get("glowEvidence"))[:2]
    ]
    glow_evidence = [value for value in glow_evidence if value]
    if glow_evidence:
        parts.append(
            "局部辉光锁：" + "；".join(glow_evidence)
            + "；仅在这些边缘和范围可见，禁止清除，也禁止扩散成全图柔焦"
        )

    imperfections = [
        compact_prompt_text(value, 70)
        for value in normalize_text_list(appearance.get("snapshotImperfections"))[:2]
    ]
    capture_mode = compact_prompt_text(appearance.get("captureMode"), 100)
    if capture_mode or imperfections:
        realism = "真实生活快照，保留普通手机或消费级相机的自然曝光、清晰度和皮肤纹理"
        if imperfections:
            realism += "；保留不完美：" + "、".join(imperfections)
        parts.append(realism)

    if not parts:
        return ""
    return compact_prompt_text("最高优先级执行：" + "；".join(parts), 780)


def build_compact_reference_render_priority_prefix_v2(reference_analysis):
    """Build one non-conflicting render contract for Dreamina."""
    frame = reference_analysis.get("frameLock") if isinstance(reference_analysis, dict) else {}
    camera = reference_analysis.get("cameraLock") if isinstance(reference_analysis, dict) else {}
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    frame = frame if isinstance(frame, dict) else {}
    camera = camera if isinstance(camera, dict) else {}
    appearance = appearance if isinstance(appearance, dict) else {}

    core_contract = build_core_replication_contract(reference_analysis)
    parts = []
    shot_class = str(frame.get("shotScaleClass") or "").strip()
    box = frame.get("visiblePersonBox")
    execution_top = None
    if isinstance(box, dict) and all(isinstance(box.get(key), int) for key in ("x", "y", "width", "height")):
        left, top = box["x"] / 10, box["y"] / 10
        width, height = box["width"] / 10, box["height"] / 10
        bottom = max(0, 1000 - box["y"] - box["height"]) / 10
        scale_factor = 1.0
        if shot_class in {"environmental", "full"} and height <= 82:
            scale_factor = 0.82
        elif shot_class in {"near_full", "three_quarter"} and height <= 82:
            scale_factor = 0.85
        elif shot_class == "medium" and top >= 20 and height <= 80:
            scale_factor = 0.88
        min_width = 15 if shot_class in {"environmental", "full"} else 20
        min_height = 35 if shot_class in {"environmental", "full"} else 42
        render_width = max(min_width, width * scale_factor)
        render_height = max(min_height, height * scale_factor)
        center_x = left + width / 2
        render_left = max(0, min(100 - render_width, center_x - render_width / 2))
        execution_top = max(0, 100 - bottom - render_height)
        render_right = max(0, 100 - render_left - render_width)
        parts.append(
            f"唯一执行构图：人物所有像素限在宽{render_width:.1f}%高{render_height:.1f}%的框内，"
            f"左上({render_left:.1f}%,{execution_top:.1f}%)，右空{render_right:.1f}%下空{bottom:.1f}%；"
            "此数值已校正模型自动放大偏差，忽略后文其他占比数字，不得推进镜头或越框"
        )
        anchors = frame.get("scaleAnchors") if isinstance(frame.get("scaleAnchors"), dict) else {}
        face_box, torso_box = anchors.get("faceBox"), anchors.get("torsoBox")
        scales = []
        if isinstance(face_box, dict) and face_box:
            scales.append(f"脸框{face_box['width'] / 10 * scale_factor:.1f}%×{face_box['height'] / 10 * scale_factor:.1f}%")
        if isinstance(torso_box, dict) and torso_box:
            scales.append(f"躯干框{torso_box['width'] / 10 * scale_factor:.1f}%×{torso_box['height'] / 10 * scale_factor:.1f}%")
        if scales:
            parts.append("内部尺度：" + "，".join(scales) + "，四肢和道具不得放大脸或躯干")

    top_person_y = frame.get("topPersonY")
    if isinstance(top_person_y, int) and top_person_y >= 80:
        top_limit = execution_top if execution_top is not None else top_person_y / 10
        parts.append(f"顶部连续{top_limit:.1f}%只留场景，头发、手、道具和服饰均不得进入")
        if top_limit >= 30 and shot_class in {"environmental", "full", "near_full", "three_quarter"}:
            parts.append("这是背景主导的远景人像：先铺满背景，再把明显较小的人物放入画面下部，禁止顶天立地或商品全身展示构图")

    visible_parts = normalize_text_list(frame.get("visibleBodyParts"))
    bottom_edge = compact_prompt_text(frame.get("bottomEdge"), 62)
    topmost_part = compact_prompt_text(frame.get("topmostPersonPart"), 24)
    visible_evidence = " ".join(visible_parts) + bottom_edge
    has_feet = any(
        marker in visible_evidence
        for marker in ("双脚", "左脚", "右脚", "脚背", "脚趾", "脚尖", "脚踝", "鞋面", "鞋尖", "鞋跟", "鞋子")
    )
    if topmost_part or bottom_edge:
        range_values = []
        if topmost_part:
            range_values.append("人物最高点为" + topmost_part)
        if bottom_edge:
            range_values.append("画内身体终点为" + bottom_edge)
        parts.append(
            "人物展示范围硬锁："
            + "，".join(range_values)
            + "；不得比原图向内裁切，空间不足只能后退镜头并缩小人物，不得改成更紧景别"
        )
    if shot_class in {"full", "near_full"} and has_feet:
        parts.append(
            "脚部终点硬锁：先生成原图已经显示的脚踝、脚或鞋和落地点，再向上完成双腿和身体；"
            + (f"严格沿用原图底边状态“{bottom_edge}”；" if bottom_edge else "")
            + "允许保留原图已有的轻微底边裁切，但不得把裁切上移到脚踝、小腿、膝盖或大腿"
        )

    camera_values = [
        compact_prompt_text(camera.get(key), 32)
        for key in ("cameraHeight", "pitch", "yaw", "roll", "focalLength35mm", "distanceAndLens")
    ]
    camera_values = [value for value in camera_values if value]
    if camera_values:
        angle = compact_prompt_text(camera.get("mustPreserveAngleCue"), 38)
        camera_part = "机位：" + "，".join(camera_values)
        if angle:
            camera_part += "；可见证据：" + angle
        parts.append(camera_part + "；禁止回退为默认正面平视")

    capture_type = str(appearance.get("captureType") or "").strip()
    selfie_relation = compact_prompt_text(
        normalize_screen_coordinate_text(appearance.get("selfieRelation")),
        120,
    )
    if capture_type == "selfie_phone_out_of_frame":
        parts.append(
            "拍摄者硬锁：单手臂长自拍，手机在画外；"
            + (selfie_relation or "持机侧手臂朝镜头延伸并在画外结束，保留近大远小和高机位透视")
            + "；禁止改成第三方普通俯拍或平视人像"
        )
    elif capture_type == "selfie_visible_phone":
        parts.append(
            "拍摄者硬锁：手机入画的自拍；"
            + (selfie_relation or "保留手机、持机手、镜头方向及其对脸和躯干的遮挡")
            + "；禁止改成他拍"
        )

    environment_color_zones = [
        compact_prompt_text(value, 78)
        for value in normalize_text_list(appearance.get("environmentColorZones"))[:3]
        if value
    ]
    if environment_color_zones:
        parts.append(
            "环境区域色硬锁："
            + "；".join(environment_color_zones)
            + "；各区域色相、明度、饱和度、渐变方向和相邻反射均不得互换或中和；"
            "天空不得自动回退为灰白阴天或普通蓝天，水面必须保留天空的实际综合色反射"
        )

    mouth_micro_expression = compact_prompt_text(
        appearance.get("mouthMicroExpression"), 82
    )
    if mouth_micro_expression:
        parts.append(
            "嘴部微表情硬锁："
            + mouth_micro_expression
            + "；开合、唇间缝隙、露齿露舌、画面左右嘴角及下颌受力不变；"
            "禁止自动微笑、张嘴、闭嘴或嘟嘴"
        )

    # Structural relationships must appear before appearance and lighting. The
    # execution contract is clipped, so placing these later silently dropped
    # beds, benches, mirrors, and the scale of held props in complex scenes.
    posture = compact_prompt_text(appearance.get("postureAndSupport"), 72)
    surface_geometry = compact_prompt_text(
        normalize_screen_coordinate_text(appearance.get("poseSurfaceGeometry")),
        150,
    )
    support_audit = "；".join(value for value in (posture, surface_geometry) if value)
    if support_audit and "无承载面" not in support_audit:
        surface_values = [value for value in (posture, surface_geometry) if value]
        parts.append(
            "承载面拓扑硬锁："
            + "；".join(surface_values)
            + "；保持承载面的画内范围，以及臀、背、手、腿、脚与其压靠、悬空、垂落或落地关系；"
            "不得把身体整体位于承载面上的姿势改成仅坐边缘或脚落地，也不得把坐靠改成站立"
        )

    dominant_prop = compact_prompt_text(
        normalize_screen_coordinate_text(appearance.get("foregroundObjectGeometry")),
        170,
    )
    if dominant_prop:
        parts.append(
            "显著物件尺度硬锁："
            + dominant_prop
            + "；保持品类、相对脸部和躯干的尺寸、整图外接框、中心、遮挡与逐手接触；"
            "无论是否为待替换商品，都禁止放大、缩小、替换或删除"
        )

    backgrounds = normalize_text_list(appearance.get("backgroundStructureAnchors"))
    backgrounds.sort(key=lambda value: "镜" not in value)
    backgrounds = [compact_prompt_text(value, 54) for value in backgrounds[:3] if value]
    if backgrounds:
        background_part = "场景骨架必须入画：" + "；".join(backgrounds) + "；位置、尺度和前后层级不变"
        if any("镜" in value for value in backgrounds):
            background_part += "；镜子无论是否自拍，镜框、镜面、支架和反射均须入画，禁改空墙"
        parts.append(background_part)

    lower_body = extract_pose_clauses(
        appearance.get("poseSurfaceGeometry"),
        ("腿", "髋", "膝", "踝", "脚", "臀部", "坐", "躺", "卧", "承载"),
        110,
    )
    contacts = normalize_text_list(appearance.get("poseContacts"))
    pose_specs = []
    if shot_class in {"environmental", "full", "near_full", "three_quarter"} or any(
        marker in posture for marker in ("坐", "躺", "卧", "倚", "趴")
    ):
        pose_specs.extend(((lower_body, 120), (appearance.get("forbiddenPoseFallback"), 70)))
    pose_specs.extend(
        (
            (appearance.get("actionKeyframe"), 82),
            (appearance.get("bodyOrientation"), 42),
        )
    )
    pose_specs.extend((value, 52) for value in contacts[:2])
    pose_specs.extend((value, 32) for value in normalize_text_list(appearance.get("directionAnchors"))[:2])
    pose_values = [
        compact_prompt_text(normalize_screen_coordinate_text(value), limit)
        for value, limit in pose_specs
        if value
    ]
    if pose_values:
        pose_part = "动作与左右：禁止水平翻转；" + "；".join(pose_values)
        if shot_class in {"close_up", "medium"} and any("手" in value for value in pose_values):
            pose_part += "；每只手仅有一个连续手腕、掌心和五指，禁止增生、折断、穿插和反关节"
        parts.append(pose_part)

    hand_audit_values = []
    for item in appearance.get("handPositionAudit") or []:
        if not isinstance(item, dict):
            continue
        center_x = item.get("centerX")
        center_y = item.get("centerY")
        if not isinstance(center_x, int) or not isinstance(center_y, int):
            continue
        side = "画面左侧" if center_x < 500 else "画面右侧"
        details = compact_prompt_text(
            "，".join(
                str(value).strip()
                for value in (
                    item.get("contact"),
                    item.get("visibility"),
                    item.get("evidence"),
                )
                if str(value or "").strip()
            ),
            42,
        )
        value = f"{side}手心({center_x / 10:.1f}%,{center_y / 10:.1f}%)"
        if details:
            value += "，" + details
        hand_audit_values.append(value)
    if hand_audit_values:
        parts.append(
            "逐手坐标硬锁："
            + "；".join(hand_audit_values[:2])
            + "；以横坐标判定画面左右，与其它方向文字冲突时以本项为准，禁止交换两手职责"
        )

    wearables = sanitize_non_target_wearables(appearance.get("nonTargetWearables"))
    if wearables:
        parts.append(
            "非替换穿戴物硬锁："
            + "；".join(compact_prompt_text(value, 52) for value in wearables[:4])
            + "；保留品类、颜色、结构、位置和接触关系，不得省略或默认改成赤脚"
        )

    skin = compact_prompt_text(appearance.get("visibleSkinTone"), 62)
    facial_skin = compact_prompt_text(appearance.get("facialSkinRendering"), 58)
    flash_evidence = normalize_text_list(appearance.get("flashEvidence"))
    lighting_mode = str(appearance.get("lightingMode") or "").strip()
    if lighting_mode not in {"near_axis_flash", "fill_flash"} and not flash_evidence:
        parts.append("曝光：无闪光灯；禁止近轴直闪、填充闪光、贴轴硬影和人物被瞬间整体打亮")

    if skin:
        skin_rule = "肤色曝光硬锁：" + skin + "；肤色明度独立于环境曝光，落实到脸、颈、手臂和画内双腿"
        if "冷白皮" in skin:
            skin_rule += "；以高明度冷粉白面中和中性眼白为锚，无闪光也不得变成米黄、暖黄或普通自然肤色"
        elif "中性白皮" in skin:
            skin_rule += "；不得被环境改成暖黄或冷青"
        if facial_skin:
            skin_rule += "；面部基准：" + facial_skin
        parts.append(skin_rule)

    global_bias = compact_prompt_text(appearance.get("globalColorBias"), 42)
    color_anchor = compact_prompt_text(appearance.get("colorAnchor"), 68)
    tone = compact_prompt_text(appearance.get("toneProfile"), 42)
    if skin or global_bias or color_anchor:
        color_values = [value for value in (global_bias, color_anchor, tone) if value]
        color_rule = "光色硬锁：" + "；".join(color_values)
        parts.append(color_rule + "；脸颈手臂不得被环境统一染黄或染青")

    lighting_mode = str(appearance.get("lightingMode") or "").strip()
    lighting_cue = compact_prompt_text(appearance.get("mustPreserveLightingCue"), 68)
    highlight = compact_prompt_text(appearance.get("highlightBehavior"), 46)
    exposure_evidence = "；".join(
        value
        for value in (
            lighting_cue,
            highlight,
            *normalize_text_list(appearance.get("snapshotImperfections"))[:2],
        )
        if value
    )
    has_large_bright_emitter = any(
        marker in exposure_evidence for marker in ("大面积窗", "发光柜体", "整面灯箱", "灯带", "大面积亮区")
    )
    has_visible_overflow = any(
        marker in exposure_evidence for marker in ("过曝", "明显溢出", "曝光上限", "自发光")
    )
    if lighting_mode == "indoor_ambient" and has_large_bright_emitter and has_visible_overflow:
        parts.append(
            "环境曝光硬锁：暖色室内保持中高明度和抬起的阴影；发光柜体、灯带或大面积亮区接近曝光上限并允许局部轻微溢出，"
            "禁止压暗成灰绿低调环境"
            + (f"；{lighting_cue}" if lighting_cue else "")
        )

    visual_salience = compact_prompt_text(appearance.get("visualSalience"), 125)
    if visual_salience:
        parts.append("画面辨识签名：" + visual_salience)

    lighting_cue = compact_prompt_text(appearance.get("mustPreserveLightingCue"), 70)
    if lighting_mode in {"near_axis_flash", "fill_flash"}:
        parts.append("光感：近轴闪光、贴轴阴影、皮肤小面积高光和近亮远暗必须可见，禁止柔光棚拍" + (f"；{lighting_cue}" if lighting_cue else ""))
    elif lighting_mode == "direct_sun":
        parts.append("光感：保留直射阳光方向、高光斑和清楚阴影，禁止均匀柔光" + (f"；{lighting_cue}" if lighting_cue else ""))
    elif lighting_mode:
        lighting_description = compact_prompt_text(
            appearance.get("lightingPhysics") or lighting_cue,
            90,
        ) or {
            "diffuse_daylight": "自然漫射日光，人物与背景共享同一柔和光向和亮度渐变",
            "mixed": "自然光与场景环境光混合，分别保留实际方向、颜色和影响区域",
            "indoor_ambient": "室内环境光按原方向和色温照亮人物，并保留自然阴影层次",
        }.get(lighting_mode, "场景环境光按参考图方向、颜色和明暗关系作用")
        light_text = "光感：" + lighting_description
        flash_evidence = normalize_text_list(appearance.get("flashEvidence"))
        if not flash_evidence:
            light_text += "；无闪光灯，禁止近轴直闪、填充闪光、贴轴硬影和人物被瞬间整体打亮"
        parts.append(light_text)

    imperfections = [compact_prompt_text(value, 42) for value in normalize_text_list(appearance.get("snapshotImperfections"))[:2]]
    if appearance.get("captureMode") or imperfections:
        parts.append("真实生活快照，保留自然曝光、皮肤纹理和不完美：" + "、".join(imperfections))

    optional_contract = "最高优先级执行：" + "；".join(parts) if parts else ""
    if not optional_contract:
        return compact_prompt_text(core_contract, 1250)

    # Reserve the front of the prompt for calibrated frame/camera execution.
    # Previously the descriptive contract consumed the whole budget and silently
    # dropped the compensation that prevents Dreamina from zooming in.
    execution_contract = compact_prompt_text(optional_contract, 1250)
    remaining = max(0, 1250 - len(execution_contract) - 1)
    descriptive_contract = compact_prompt_text(core_contract, remaining) if remaining else ""
    return " ".join(value for value in (execution_contract, descriptive_contract) if value)


def build_apparel_capture_execution_rule(reference_analysis):
    """Build a compact, non-droppable camera-realism contract for Dreamina."""
    camera = reference_analysis.get("cameraLock") if isinstance(reference_analysis, dict) else {}
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    camera = camera if isinstance(camera, dict) else {}
    appearance = appearance if isinstance(appearance, dict) else {}

    capture_type = str(appearance.get("captureType") or "").strip()
    capture_mode = compact_prompt_text(appearance.get("captureMode"), 58)
    capture_realism = compact_prompt_text(appearance.get("captureRealism"), 92)
    environment_realism = compact_prompt_text(appearance.get("environmentRealism"), 120)
    imperfections = [
        compact_prompt_text(value, 38)
        for value in normalize_text_list(appearance.get("snapshotImperfections"))[:2]
    ]
    imperfections = [value for value in imperfections if value]
    lighting_mode = str(appearance.get("lightingMode") or "").strip()
    ccd_evidence = normalize_text_list(appearance.get("ccdEvidence"))
    daylight_evidence = [
        compact_prompt_text(value, 46)
        for value in normalize_text_list(appearance.get("daylightEvidence"))[:2]
    ]
    daylight_evidence = [value for value in daylight_evidence if value]
    focal = compact_prompt_text(camera.get("focalLength35mm"), 28)

    capture_mode_lower = capture_mode.lower()
    is_phone_capture = (
        "手机" in capture_mode
        or "iphone" in capture_mode_lower
        or capture_type in {"selfie_phone_out_of_frame", "selfie_visible_phone"}
    )
    phone_snapshot_rule = (
        "普通iPhone原相机实拍的日常生活快照，画面随性，非摆拍、非精心构图或打光；"
        "保留手机自动曝光、自动白平衡的轻微局部波动、边缘数码锐化与不均匀清晰度"
    )
    camera_snapshot_rule = (
        "消费级相机直出的真实生活快照，非商业写真；"
        "保留参考图可见的自然曝光波动、镜头边缘软硬变化与不均匀清晰度"
    )
    capture_device_rule = phone_snapshot_rule if is_phone_capture else camera_snapshot_rule

    parts = []
    if capture_type == "selfie_phone_out_of_frame":
        parts.append("画外手机单手臂长自拍，保持自拍近大远小，禁止改成第三方俯拍")
    elif capture_type == "selfie_visible_phone":
        parts.append("手机入画自拍，保持持机手、手机遮挡和镜头方向")
    if focal:
        parts.append(f"35mm等效{focal}的原透视")

    if "CCD" in capture_mode.upper() and len(ccd_evidence) >= 2:
        parts.append("早期老旧CCD生活抓拍，仅保留可见的有限动态范围、压缩、锐化和白平衡漂移")
    elif lighting_mode in {"near_axis_flash", "fill_flash"}:
        parts.append(
            capture_device_rule
            + "；昏暗环境近轴直闪，近亮远暗、贴轴硬影和局部高光按原图出现"
        )
    elif lighting_mode == "direct_sun":
        parts.append(
            capture_device_rule
            + "；直射日光下人物和背景共享同一太阳方向、曝光与白平衡；"
            "保留硬光斑、清楚投影、受光面与背光面的自然亮度差和有限动态范围，绝不补闪"
        )
    elif lighting_mode == "diffuse_daylight":
        parts.append(
            capture_device_rule
            + "；漫射日光下人物和背景共享同一自然天光；"
            "保留环境遮挡造成的缓慢明暗渐变、自然接触阴影和现场综合色，禁止均匀棚拍柔光"
        )
    elif lighting_mode == "mixed":
        parts.append(
            capture_device_rule
            + "；混合自然光下分别保留直射光、天空光和环境反射的方向、颜色与作用区域；"
            "人物必须真实嵌入环境，禁止独立打亮人物或把背景处理成合成布景，绝不补闪"
        )
    elif lighting_mode == "indoor_ambient":
        parts.append(
            capture_device_rule
            + "；室内现场光下人物和空间共享同一光源衰减；"
            "保留现场色温、曝光波动、接触阴影和材质反光，禁止额外人像补光，绝不补闪"
        )
    else:
        parts.append(capture_device_rule)

    if capture_mode:
        parts.append(capture_mode)
    if capture_realism:
        parts.append(capture_realism)
    if environment_realism:
        parts.append("环境成像证据：" + environment_realism)
    if daylight_evidence and lighting_mode not in {"near_axis_flash", "fill_flash"}:
        parts.append("自然光证据必须肉眼可见：" + "、".join(daylight_evidence))
    if imperfections:
        parts.append("保留" + "、".join(imperfections))
    parts.append(
        "人物、商品和背景必须像同一次真实曝光，不得出现人物边缘发亮、背景单独虚化或抠图合成感；"
        "皮肤保留毛孔、绒毛和局部血色，材质保留微小色差，锐度与曝光不完全均匀；"
        "禁止蜡像磨皮、生成式过锐、过度干净的AI质感和广告写真光"
    )
    return "真实成像硬锁：" + "；".join(parts)


def build_bounded_apparel_image_prompt(
    final_prompt,
    reference_analysis,
    bust_execution_rule,
    identity_rule,
    user_prompt="",
    product_subject_hint="",
):
    """Assemble the actual Dreamina prompt under one explicit global budget."""
    layout_lock = build_reference_layout_execution_lock_text(reference_analysis)
    gender_lock = build_reference_gender_execution_lock_text(reference_analysis)
    priority_prefix = build_compact_reference_render_priority_prefix_v2(reference_analysis)
    scene_prompt = strip_competing_apparel_composition_sentences(
        sanitize_apparel_render_prompt(final_prompt, reference_analysis)
    )
    inventory_match = re.search(r"商品清单\s*[：:]\s*([^。]+)", str(final_prompt or ""))
    inventory_text = compact_prompt_text(
        inventory_match.group(1) if inventory_match else product_subject_hint,
        180,
    )
    product_rule = (
        "商品图只提供服饰外观结构，不提供人物、动作、构图、场景或光色；覆盖区清除旧衣，"
        "商品图是服饰结构唯一真值，逐件保持真实领口或腰头、肩部连接点、肩带数量、袖窿袖子、开合、下摆裤脚和标识；"
        "只生成图中可连续确认的结构，不增加绕颈带、后颈系带、交叉肩带、额外内搭、开口或镂空。"
        "商品结构优先级高于体型表现；不得为突出胸部而改变领口高度与形状、肩带锚点、胸前覆盖范围或连续面料。"
    )
    if inventory_text:
        product_rule += (
            f"商品清单硬锁：{inventory_text}；严格按清单实际件数执行。单件商品只清空并替换其覆盖区域；"
            "明确为套装或多件组合时，清单中的每一件才必须同时出现在各自身体区域并逐件清空旧衣；"
            "最终缺少清单中的任一件，或在任一已覆盖区域残留对应旧衣，均判定失败。"
        )
    artifact_rule = "画面铺满画幅，无白黑边、界面、轮播点或水印。"
    frame = reference_analysis.get("frameLock") if isinstance(reference_analysis, dict) else {}
    frame = frame if isinstance(frame, dict) else {}
    top_person_y = frame.get("topPersonY")
    if isinstance(top_person_y, int) and top_person_y >= 80:
        artifact_rule += (
            f"顶部连续{top_person_y / 10:.1f}%只能是原场景背景，"
            "人物最高像素不得越过该线；空间不足时缩小人物并后退镜头。"
        )
    fixed_segments = [
        layout_lock,
        gender_lock,
        product_rule,
        compact_prompt_text(build_reference_body_shape_execution_lock_text(reference_analysis), 320),
        compact_prompt_text(bust_execution_rule, 180),
        compact_prompt_text(identity_rule, 100),
        compact_prompt_text(f"用户补充：{user_prompt}" if user_prompt else "", 80),
        build_apparel_capture_execution_rule(reference_analysis),
        artifact_rule,
    ]
    fixed_segments = [segment for segment in fixed_segments if segment]
    fixed_length = sum(len(segment) for segment in fixed_segments) + len(fixed_segments) + 2
    descriptive_budget = max(0, APPAREL_IMAGE_PROMPT_MAX_CHARS - fixed_length)
    # The structured prefix already contains the visual description. Keep the
    # free-form scene paragraph as a supplement so it cannot crowd out locks.
    scene_budget = min(200, max(140, int(descriptive_budget * 0.12)))
    priority_budget = max(0, descriptive_budget - scene_budget)
    segments = [
        compact_prompt_text(priority_prefix, priority_budget),
        compact_prompt_text(scene_prompt, scene_budget),
        *fixed_segments,
    ]
    prompt = " ".join(segment for segment in segments if segment)
    if len(prompt) > APPAREL_IMAGE_PROMPT_MAX_CHARS:
        overflow = len(prompt) - APPAREL_IMAGE_PROMPT_MAX_CHARS
        segments[1] = compact_prompt_text(scene_prompt, max(80, scene_budget - overflow - 2))
        prompt = " ".join(segment for segment in segments if segment)
    return prompt[:APPAREL_IMAGE_PROMPT_MAX_CHARS]


def build_legacy_apparel_image_prompt(
    final_prompt,
    reference_analysis,
    bust_execution_rule,
    identity_rule,
    user_prompt="",
    product_subject_hint="",
):
    """Restore the pre-fixed-framework Dreamina prompt assembly."""
    layout_lock = build_reference_layout_execution_lock_text(reference_analysis)
    gender_lock = build_reference_gender_execution_lock_text(reference_analysis)
    scene_prompt = sanitize_apparel_render_prompt(final_prompt, reference_analysis)
    priority_prefix = build_reference_render_priority_prefix(reference_analysis)
    inventory_match = re.search(r"商品清单\s*[：:]\s*([^。]+)", str(final_prompt or ""))
    inventory_text = (
        str(inventory_match.group(1)).strip()
        if inventory_match
        else str(product_subject_hint or "").strip()
    )
    product_rule = (
        "商品图只提供服饰外观结构，不提供人物、动作、构图、场景或光色；覆盖区清除旧衣，"
        "商品图是服饰结构唯一真值，严格保持领口、肩带、袖笼、开合、下摆、裤脚和标识；"
        "商品结构优先级高于体型表现，不得为突出胸部而降低或扩大领口、改成深V、移动肩带、缩窄胸前覆盖、增加露肤、事业线、开口或内衣式结构；"
        "参考图的构图、人物外接框、四侧留白、机位和画内身体终点优先于商品完整展示：只在原图可见的身体范围内替换商品，"
        "商品延伸到画外的部分继续留在画外，不得为展示长裙、长裤、下摆或标识而后退镜头、缩小人物、居中人物、补出腿脚或改变裁切。"
        "若标识所在的商品区域在原图可见，必须保持标识的外观、商品内相对位置、尺寸和朝向且不被头发或配饰遮挡；"
        "若该区域本来在画外或被动作遮挡，不得把标识移动到其他位置，也不得为了露出标识改变构图。"
    )
    if inventory_text:
        product_rule += f"商品清单：{inventory_text}。"

    lower_limb_rule = build_legacy_lower_limb_lock(reference_analysis)
    white_balance_rule = build_legacy_white_balance_lock(reference_analysis)
    capture_rule = build_apparel_capture_execution_rule(reference_analysis)
    lighting_rule = build_reference_lighting_execution_lock_text(reference_analysis)
    face_exposure_rule = build_reference_face_exposure_lock_text(reference_analysis)
    realism_priority_rule = (
        "真实拍摄优先级硬锁：最终图必须首先像参考图对应设备在同一现场完成的一次真实拍摄，"
        "保留自然皮肤纹理、局部曝光与白平衡波动、现场光衰减和不均匀清晰度；"
        "禁止AI商业人像、棚拍精修、塑料皮肤、全画面同等锐利和背景合成感。"
    )

    segments = [
        layout_lock,
        realism_priority_rule,
        capture_rule,
        lighting_rule,
        face_exposure_rule,
        gender_lock,
        product_rule,
        build_reference_body_shape_execution_lock_text(reference_analysis),
        bust_execution_rule,
        priority_prefix,
        scene_prompt,
        identity_rule,
        f"用户补充：{user_prompt}" if user_prompt else "",
        lower_limb_rule,
        white_balance_rule,
        "画面铺满画幅，无白黑边、界面、轮播点或水印。",
    ]
    return " ".join(str(segment).strip() for segment in segments if str(segment).strip())


def build_reference_gender_execution_lock_text(reference_analysis):
    """Keep the reference person's visible gender presentation out of product influence."""
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    appearance = appearance if isinstance(appearance, dict) else {}
    gender = normalize_enum(
        appearance.get("genderPresentation"), {"male", "female", "uncertain"}, "uncertain"
    )
    if gender == "male":
        return (
            "人物性别呈现硬锁（最高优先级）：参考图人物明确呈男性，最终图必须仍为男性人物，"
            "保持男性面部、肩颈、胸廓和躯干呈现；不得生成女性人物、女性胸部或女性化身体轮廓。"
            "商品图中的女模特、女款剪裁和女性身体均不提供人物属性，只提供服饰结构。"
        )
    if gender == "female":
        return (
            "人物性别呈现硬锁（最高优先级）：参考图人物明确呈女性，最终图必须仍为女性人物；"
            "商品图中的男模特、男款剪裁和男性身体均不提供人物属性，只提供服饰结构。"
        )
    return ""


def build_legacy_lower_limb_lock(reference_analysis):
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    appearance = appearance if isinstance(appearance, dict) else {}
    geometry = compact_prompt_text(
        normalize_screen_coordinate_text(appearance.get("poseSurfaceGeometry")),
        260,
    )
    posture = compact_prompt_text(
        normalize_screen_coordinate_text(appearance.get("postureAndSupport")),
        130,
    )
    combined = "；".join(value for value in (geometry, posture) if value)
    visible_limb_text = combined
    for invisible_phrase in (
        "双腿不可见",
        "两腿不可见",
        "腿部不可见",
        "双脚不可见",
        "两脚不可见",
        "脚部不可见",
    ):
        visible_limb_text = visible_limb_text.replace(invisible_phrase, "")
    if not combined or not any(
        marker in visible_limb_text
        for marker in ("大腿", "小腿", "膝", "踝", "脚尖", "脚掌", "脚底", "鞋")
    ):
        return ""
    return (
        "下肢拓扑硬锁："
        + combined
        + "。严格保持画面左右两腿从髋到膝、膝到踝或可见终点的方向、间距、交叉或重叠位置、"
        "遮挡前后层级与承重点；脚在画外也不得把可见腿段改成张开、并拢、对称或默认站坐姿。"
    )


def build_legacy_white_balance_lock(reference_analysis):
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    appearance = appearance if isinstance(appearance, dict) else {}
    global_bias = compact_prompt_text(appearance.get("globalColorBias"), 125)
    neutral_audit = compact_prompt_text(appearance.get("neutralAnchorAudit"), 170)
    color_anchor = compact_prompt_text(appearance.get("colorAnchor"), 145)
    skin_tone = compact_prompt_text(appearance.get("visibleSkinTone"), 105)
    if not any((global_bias, neutral_audit, color_anchor, skin_tone)):
        return ""
    details = "；".join(
        value
        for value in (
            f"综合色：{global_bias}" if global_bias else "",
            f"中性色证据：{neutral_audit}" if neutral_audit else "",
            f"颜色锚点：{color_anchor}" if color_anchor else "",
            f"肤色基础：{skin_tone}" if skin_tone else "",
        )
        if value
    )
    return (
        "全局白平衡硬锁："
        + details
        + "。先让画内白、灰、黑和眼白共同呈现参考图实际的综合色偏，再让墙面、天空、木材与肤色服从同一光源；"
        "肤色基础色只能叠加局部受光，不得单独漂白、暖黄化或冷青化，也不得自动校正成商业人像的标准中性白平衡。"
    )


def build_reference_render_priority_prefix(reference_analysis):
    frame = reference_analysis.get("frameLock") if isinstance(reference_analysis, dict) else {}
    camera = reference_analysis.get("cameraLock") if isinstance(reference_analysis, dict) else {}
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    if not isinstance(frame, dict):
        frame = {}
    if not isinstance(camera, dict):
        camera = {}
    if not isinstance(appearance, dict):
        appearance = {}

    parts = []
    posture = str(appearance.get("postureAndSupport") or "").strip()
    box = frame.get("visiblePersonBox")
    top_person_y = frame.get("topPersonY")
    shot_scale_class = str(frame.get("shotScaleClass") or "").strip()
    if isinstance(box, dict) and box:
        left = box["x"] / 10
        top = box["y"] / 10
        width = box["width"] / 10
        height = box["height"] / 10
        right = max(0, 1000 - box["x"] - box["width"]) / 10
        bottom = max(0, 1000 - box["y"] - box["height"]) / 10
        parts.append(
            f"先生成完整背景再放人物：人物外接框宽{width:.1f}%、高{height:.1f}%，"
            f"左上角({left:.1f}%,{top:.1f}%)，右侧留白{right:.1f}%，下方留白{bottom:.1f}%"
        )
        parts.append(
            "把整张画布视为100×100坐标网格，人物所有可见像素必须落入上述外接框；"
            "若人物、脸或商品细节与外接框冲突，只能缩小人物并后退镜头，绝不能放大人物、推进镜头或侵占框外背景"
        )
        center_x = left + width / 2
        center_y = top + height / 2
        placement = str(frame.get("horizontalPlacement") or "").strip()
        negative_space = str(frame.get("dominantNegativeSpace") or "").strip()
        center_label = {
            "left": "偏画面左侧",
            "center": "接近水平居中",
            "right": "偏画面右侧",
        }.get(placement, "保持参考图横向位置")
        placement_rule = f"人物视觉中心固定在整图({center_x:.1f}%,{center_y:.1f}%)，{center_label}，不得横向漂移"
        if placement != "center":
            placement_rule += "；这是有意的偏置构图，禁止把脸、胸口或人物外接框移回画面中轴线"
            render_center_x = center_x - 4 if placement == "left" else center_x + 4
            render_center_x = max(4, min(96, render_center_x))
            placement_rule += (
                f"；为抵消生图模型自动居中的倾向，渲染落点先按水平中心约{render_center_x:.1f}%执行，"
                f"最终视觉验收回到参考图约{center_x:.1f}%"
            )
        negative_space_label = {"left": "左侧", "right": "右侧"}.get(negative_space)
        if negative_space_label:
            placement_rule += f"；画面{negative_space_label}是主要背景负空间，宽度关系不得与另一侧对调"
        parts.append(placement_rule)
        edge_contacts = set(normalize_text_list(frame.get("edgeContacts")))
        if edge_contacts:
            edge_labels = {
                "left": "左边缘",
                "right": "右边缘",
                "top": "上边缘",
                "bottom": "下边缘",
            }
            parts.append(
                "人物贴边裁切硬锁：人物像素贴近"
                + "、".join(edge_labels[item] for item in ("left", "right", "top", "bottom") if item in edge_contacts)
                + "；保持相同贴边或自然出画，禁止为了完整展示人物而向中央挪动或扩展画幅"
            )
        placement_evidence = str(frame.get("horizontalPlacementEvidence") or "").strip()
        if placement_evidence:
            parts.append("横向位置证据：" + placement_evidence)
        is_wide_shot = (
            shot_scale_class in {"environmental", "full", "near_full", "three_quarter"}
            and (height <= 82 or top >= 15)
        )
        if is_wide_shot:
            parts.append(
                "这是背景主导的大景别人像，不是半身照或人物特写；镜头后退并完整保留背景负空间"
            )
            if height <= 70:
                compensated_height = max(35, height * 0.78)
                compensated_top = max(top, 100 - bottom - compensated_height)
                parts.append(
                    f"远景缩小补偿：为抵消生图模型自动放大人物的倾向，实际渲染时人物高度先按不超过{compensated_height:.1f}%执行，"
                    f"人物最高点不得早于画面高度{compensated_top:.1f}%出现，脚底或身体终点仍保持原下边缘位置；"
                    f"最终视觉验收目标仍是参考图人物约{height:.1f}%的尺度和同等背景占比"
                )
            elif height <= 82:
                compensated_height = max(48, height * 0.78)
                compensated_top = max(top, 100 - bottom - compensated_height)
                parts.append(
                    f"近全身缩小补偿：为抵消生图模型自动推进镜头的倾向，实际渲染时人物高度先按不超过{compensated_height:.1f}%执行，"
                    f"人物最高点不得早于画面高度{compensated_top:.1f}%出现，脚底或身体终点仍保持原下边缘位置；"
                    f"最终视觉验收目标仍是参考图人物约{height:.1f}%的尺度，不得变成顶天立地的全身商品展示"
                )
            if 38 <= center_x <= 47 and right - left >= 8:
                compensated_center_x = min(49, center_x + 4)
                parts.append(
                    f"横向漂移补偿：参考图人物视觉中心约在画面{center_x:.1f}%处；为抵消模型继续向画面左侧漂移，"
                    f"渲染放置先按中心约{compensated_center_x:.1f}%执行，最终不得越过参考中心左侧，且必须保留左右背景关系"
                )
        visible_parts = normalize_text_list(frame.get("visibleBodyParts"))
        has_visible_feet = any(
            marker in part
            for part in visible_parts
            for marker in ("双脚", "脚部", "脚掌", "脚底", "鞋头", "鞋跟", "鞋子")
        )
        if bottom <= 2 and has_visible_feet:
            parts.append(
                "下边缘完整脚部硬锁：参考图脚或鞋完整可见并贴近画面下边缘；成图必须完整保留双脚、鞋头、鞋跟和落地点，"
                "不得裁到大腿、膝盖、小腿或脚踝。若商品细节与完整脚部冲突，只能进一步后退镜头并缩小人物"
            )
        if top >= 20 and height <= 80 and "坐" in posture:
            compensated_height = max(45, height - 8)
            parts.append(
                f"坐姿人物压在画面下部，渲染外接框高度不超过{compensated_height:.1f}%，"
                f"上方连续保留至少{top:.1f}%背景，禁止推进成坐姿半身照"
            )
    if isinstance(top_person_y, int) and top_person_y >= 80:
        parts.append(
            f"人物任意像素最早只能从画面高度{top_person_y / 10:.1f}%处开始，上方连续区域只能是背景"
        )

    camera_height = str(camera.get("cameraHeight") or "").strip()
    pitch = str(camera.get("pitch") or "").strip()
    yaw = str(camera.get("yaw") or "").strip()
    roll = str(camera.get("roll") or "").strip()
    focal_length = str(camera.get("focalLength35mm") or "").strip()
    lens_evidence = str(camera.get("lensEvidence") or "").strip()
    distance = str(camera.get("distanceAndLens") or "").strip()
    angle_cue = str(camera.get("mustPreserveAngleCue") or "").strip()
    camera_values = [camera_height, pitch, yaw, roll, focal_length, distance]
    if any(camera_values):
        camera_text = "，".join(value for value in camera_values if value)
        if lens_evidence:
            camera_text += f"，焦距透视证据为{lens_evidence}"
        if angle_cue:
            camera_text += f"，画面必须直接看见{angle_cue}"
        parts.append("机位硬锁：" + camera_text + "；禁止回退成默认正面平视")

    foreground_geometry = str(appearance.get("foregroundObjectGeometry") or "").strip()
    if foreground_geometry:
        parts.append(
            "近镜头物体尺度硬锁："
            + foreground_geometry
            + "；手机、手或道具距镜头更近时必须保持其相对脸部和躯干的放大比例、遮挡面积与接触位置，禁止缩小后贴回人物身体"
        )

    body_orientation = normalize_screen_coordinate_text(appearance.get("bodyOrientation"))
    action_keyframe = normalize_screen_coordinate_text(appearance.get("actionKeyframe"))
    forbidden_pose_fallback = normalize_screen_coordinate_text(
        appearance.get("forbiddenPoseFallback")
    )
    selfie_relation = normalize_screen_coordinate_text(appearance.get("selfieRelation"))
    direction_anchors = [
        normalize_screen_coordinate_text(anchor)
        for anchor in normalize_text_list(appearance.get("directionAnchors"))[:6]
    ]
    if direction_anchors:
        parts.append(
            "画面方向硬锁：最终画面的左侧和右侧不可交换，禁止整幅水平翻转；"
            + "；".join(direction_anchors)
            + "；只使用最终画面的画面坐标，不得追加人物解剖左右标签"
        )
    if body_orientation:
        parts.append("身体朝向硬锁：" + body_orientation + "；侧身或三分之二侧身不得正面化")
        angle_matches = [int(value) for value in re.findall(r"(\d{2})\s*度", body_orientation)]
        is_near_profile = "近侧面" in body_orientation or any(angle >= 45 for angle in angle_matches)
        if is_near_profile:
            observed_angle = max(angle_matches) if angle_matches else 60
            render_angle = min(85, observed_angle + 20)
            parts.append(
                "这是近侧面而不是轻微侧身：胸腹正面宽度必须因透视明显压缩，远侧肩髋被近侧身体遮挡，"
                f"鼻尖保持朝参考方向；为抵消模型自动正面化，渲染时按约{render_angle}度横转身体执行，"
                f"以最终视觉达到参考图约{observed_angle}度侧身为验收目标，禁止双肩和胸口转成面对镜头"
            )
    if action_keyframe or selfie_relation:
        action_parts = [value for value in (action_keyframe, selfie_relation) if value]
        parts.append("动作关键帧：" + "；".join(action_parts))
        if "单手" in selfie_relation:
            parts.append("手机只能由指定的一只手持握，另一只手严格执行原动作；禁止改成双手持手机")
    if forbidden_pose_fallback:
        parts.append("动作禁止回退：" + forbidden_pose_fallback)

    contacts = [
        normalize_screen_coordinate_text(item)
        for item in normalize_text_list(appearance.get("poseContacts"))[:6]
    ]
    surface_geometry = normalize_screen_coordinate_text(appearance.get("poseSurfaceGeometry"))
    locomotion_geometry = normalize_screen_coordinate_text(appearance.get("locomotionGeometry"))
    if posture:
        pose_text = posture
        if contacts:
            pose_text += "；" + "、".join(contacts)
        if surface_geometry:
            pose_text += "；" + surface_geometry
        if locomotion_geometry:
            pose_text += "；" + locomotion_geometry
        parts.append("承重与接触不得镜像：" + pose_text)
    elif locomotion_geometry:
        parts.append("行走与台阶动作硬锁：" + locomotion_geometry)
    if locomotion_geometry:
        parts.append(
            "运动相位优先于商品正面展示：必须保留行进方向、领先腿与滞后腿、脚掌所在台阶和身体侧面轮廓；"
            "宁可只显示服饰的侧面宽度，也不得把行走、上楼或下楼动作转成正面静止站姿"
        )

    body_proportions = str(appearance.get("bodyProportions") or "").strip()
    visual_salience = str(appearance.get("visualSalience") or "").strip()
    if body_proportions or visual_salience:
        parts.append("体型比例：" + "；".join(value for value in (body_proportions, visual_salience) if value))

    lighting_mode = str(appearance.get("lightingMode") or "").strip()
    lighting_cue = str(appearance.get("mustPreserveLightingCue") or "").strip()
    highlight_behavior = str(appearance.get("highlightBehavior") or "").strip()
    flash_skin_tone = str(appearance.get("visibleSkinTone") or "").strip()
    has_cold_white_skin = "冷白皮" in flash_skin_tone
    flash_exposure_cue = (
        "；人物面部、颈部和手臂受近轴闪光形成肉眼可见的微微过曝，约比正常曝光高0.7至1.0EV，呈高明度冷白皮；"
        "背景严格保持参考图原有亮度、综合色和环境灯，不得跟随人物同步提亮或额外压暗；"
        "微微过曝只发生在受闪光照亮的皮肤高光区域，不得抹掉五官、皮肤纹理、服饰结构、图案和面料纹理"
        if has_cold_white_skin
        else ""
    )
    if lighting_mode in {"near_axis_flash", "fill_flash"}:
        if lighting_mode == "near_axis_flash":
            parts.append(
                "采用昏暗环境近镜头轴闪光灯拍摄的普通 iPhone 生活快照：人物正面瞬间提亮，"
                "皮肤和面料有少量点状反光，面部阴影贴近镜头轴，背景至少暗一档但保留环境灯；"
                "禁止自然柔光或棚拍"
                + flash_exposure_cue
                + (f"；{lighting_cue}" if lighting_cue else "")
            )
        else:
            if has_cold_white_skin:
                parts.append(
                    "采用近镜头轴正面闪光灯补光的普通 iPhone 生活快照，闪光曝光强度以人物皮肤高光达到可见的微微过曝为准；"
                    "阴影靠近镜头轴，眼睛、鼻梁、皮肤和面料保留少量正面反光；禁止纯自然柔光或商业棚拍"
                    + flash_exposure_cue
                    + (f"；{lighting_cue}" if lighting_cue else "")
                )
            else:
                parts.append(
                    "采用轻微正面闪光灯补光的 iPhone 生活快照：人物正面略亮于同距离环境，"
                    "眼睛、鼻梁、皮肤或面料有少量正面反光，阴影靠近镜头轴，背景保留原亮度层级；"
                    "禁止纯自然柔光"
                    + (f"；{lighting_cue}" if lighting_cue else "")
                )
    elif lighting_mode == "direct_sun":
        lighting_physics = str(appearance.get("lightingPhysics") or "").strip()
        parts.append(
            "直射阳光必须肉眼可见："
            + (lighting_cue or lighting_physics or "人物与环境具有同方向的硬阴影、局部阳光斑和明显亮暗反差")
            + "；高光只在真实受光面略暖，禁止改成均匀漫射补光"
        )
    if highlight_behavior:
        parts.append(
            "高光形态："
            + highlight_behavior
            + "；局部辉光、轻微雾化、高光溢出或硬边阴影只按参考图可见证据保留，"
            "有则必须在相同区域肉眼可见，无则不得凭空添加"
        )

    global_bias = str(appearance.get("globalColorBias") or "").strip()
    skin_tone = str(appearance.get("visibleSkinTone") or "").strip()
    background_relation = str(appearance.get("backgroundColorRelation") or "").strip()
    color_anchor = str(appearance.get("colorAnchor") or "").strip()
    neutral_anchor_audit = str(appearance.get("neutralAnchorAudit") or "").strip()
    if any((global_bias, skin_tone, background_relation, color_anchor, neutral_anchor_audit)):
        parts.append(
            "颜色硬锁，先背景后肤色："
            + "；".join(
                value
                for value in (
                    f"背景关系{background_relation}" if background_relation else "",
                    f"人物肤色{skin_tone}" if skin_tone else "",
                    f"综合色{global_bias}" if global_bias else "",
                    f"颜色锚点{color_anchor}" if color_anchor else "",
                    f"中性色校验{neutral_anchor_audit}" if neutral_anchor_audit else "",
                )
                if value
            )
            + "；严格保留参考图综合色方向和强度，不得自动中和，也不得增加不存在的黄色、橙红或青绿偏色"
        )
        neutral_check_text = "；".join((global_bias, neutral_anchor_audit, color_anchor))
        if "近中性" in neutral_check_text or "中性" in neutral_check_text:
            parts.append(
                "中性色先验收：白、灰、黑区域先保持中性，再分别添加墙面、木材、阳光或绿植的局部固有色；"
                "局部暖色不得形成覆盖人物、地面和背景的统一黄色滤镜"
            )

    tone_profile = str(appearance.get("toneProfile") or "").strip()
    if tone_profile:
        parts.append("明暗曲线：" + tone_profile + "；禁止自动增加商业人像式高对比")

    capture_mode = str(appearance.get("captureMode") or "").strip()
    capture_realism = str(appearance.get("captureRealism") or "").strip()
    snapshot_imperfections = normalize_text_list(appearance.get("snapshotImperfections"))
    ccd_evidence = normalize_text_list(appearance.get("ccdEvidence"))
    if capture_mode or capture_realism:
        if "CCD" in capture_mode.upper() and len(ccd_evidence) >= 2:
            parts.append(
                "真实拍摄：早期老旧 CCD 或消费级数码相机的生活抓拍质感；"
                + "、".join(ccd_evidence[:4])
                + "；只保留参考图确有的有限动态范围、曝光截断、噪点压缩和数码锐化，禁止改成胶片滤镜或商业精修"
            )
        else:
            parts.append(
                "真实拍摄：普通手机或消费级相机的生活快照，保留自然曝光波动和不均匀清晰度；"
                "皮肤半哑光，禁止蜡像磨皮、生成式过锐和商业精修；"
                "人物姿势、背景整理和光线不得被优化成写真、广告或标准模特展示"
                + (
                    "；至少保留这些可见不完美中的两项：" + "、".join(snapshot_imperfections[:4])
                    if snapshot_imperfections
                    else "；至少保留轻微曝光或白平衡波动、不均匀清晰度、自然背景杂乱中的两项"
                )
            )

    parts.append(
        "成图只包含真实拍摄内容：禁止生成轮播圆点、进度条、页码、播放控件、状态栏、应用水印、截图文字、白色画布、边框或上下黑白留边"
    )

    if not parts:
        return ""
    return "最高优先级取景执行：" + "；".join(parts) + "。"


def build_reference_color_execution_lock_text(reference_analysis):
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    if not isinstance(appearance, dict):
        return ""
    parts = []
    for label, key in (
        ("全局综合色偏", "globalColorBias"),
        ("对比度与明暗曲线", "toneProfile"),
        ("绝对颜色锚点", "colorAnchor"),
        ("皮肤基础色", "visibleSkinTone"),
        ("背景与人物颜色关系", "backgroundColorRelation"),
        ("光型", "lightingMode"),
        ("必须可见的光线证据", "mustPreserveLightingCue"),
        ("高光边缘、辉光与溢出方式", "highlightBehavior"),
        ("光线物理关系", "lightingPhysics"),
        ("中性色锚点校验", "neutralAnchorAudit"),
    ):
        value = str(appearance.get(key) or "").strip()
        if value:
            parts.append(f"{label}：{value}")
    environment_color_zones = [
        compact_prompt_text(value, 100)
        for value in normalize_text_list(appearance.get("environmentColorZones"))[:4]
        if value
    ]
    if environment_color_zones:
        parts.append("环境区域颜色：" + "；".join(environment_color_zones))
    if not parts:
        return ""
    return (
        "成图光色执行锁（禁止被商品图色温或默认人像调色覆盖）："
        + "；".join(parts)
        + "。最终画面必须直接看出参考图的综合色偏、对比度和光型；禁止自动中和参考图已有色偏，也禁止改成参考图没有的暖红人像、青绿色滤镜、硬黑高反差或均匀柔光。"
    )


def build_reference_bust_execution_lock_text(reference_analysis):
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    appearance = appearance if isinstance(appearance, dict) else {}
    level = normalize_enum(
        appearance.get("bustLevel"), {"prominent", "non_prominent", "uncertain"}, "uncertain"
    )
    confidence = normalize_enum(
        appearance.get("bustConfidence"), {"high", "medium", "low"}, "low"
    )
    evidence = normalize_text_list(appearance.get("bustEvidence"))
    positive_markers = (
        "左右胸部外轮廓",
        "胸部宽度相对腰宽显著",
        "胸部前向体积明显",
        "独立的圆弧",
        "独立圆弧",
        "超出肋骨",
        "超出躯干侧肋线",
        "胸部外轮廓",
        "超出腰宽",
        "侧面弧度独立",
        "弧度独立于衣物",
    )
    invalid_markers = (
        "低领",
        "露肤",
        "肩带",
        "领口",
        "俯拍",
        "广角",
        "手臂挤压",
        "裁切放大",
        "单侧轮廓",
    )
    positive_count = sum(any(marker in item for marker in positive_markers) for item in evidence)
    has_invalid_evidence = any(
        marker in "；".join(evidence) for marker in invalid_markers
    )
    verified_prominent = (
        level == "prominent"
        and confidence == "high"
        and len(evidence) >= 2
        and positive_count >= 2
        and not has_invalid_evidence
    )
    if verified_prominent:
        return (
            "体型锁：参考图已由高置信度和至少两条独立身体轮廓证据确认大胸，保持参考图胸部局部体积和胸腰关系；不得缩小成普通或偏小胸部。"
            "大胸只描述胸部局部前向体积，不代表更高体重或更大骨架；不得连带增加肩宽、躯干厚度、上臂围、腰围、胯宽、大腿围或小腿围。"
            "但商品结构优先级高于体型：胸部只能在商品原有领口、肩带锚点、覆盖范围和连续面料内自然呈现，"
            "不得为了突出胸部而降低或扩大领口、改成深V、拉开门襟、移动肩带、缩窄覆盖、增加露肤、事业线、开口或内衣式结构。"
        )
    if level == "non_prominent":
        return "体型执行锁：参考图胸部保持同等的普通或偏小自然体积，禁止放大胸部体积、增强前向突出程度或制造夸张胸腰差。"
    return (
        "体型执行锁：参考图没有同时满足高置信度与多条独立身体轮廓证据，"
        "胸部只保持参考图可直接确认的自然体积，禁止凭空放大胸部、增强前向突出程度或制造夸张胸腰差。"
    )


def build_reference_body_shape_execution_lock_text(reference_analysis):
    """Keep the reference skeleton and limb widths independent from bust volume."""
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    appearance = appearance if isinstance(appearance, dict) else {}
    silhouette = str(appearance.get("bodySilhouette") or "").strip()
    proportions = str(appearance.get("bodyProportions") or "").strip()
    salience = appearance.get("visualSalience")
    if isinstance(salience, list):
        salience = "；".join(str(item).strip() for item in salience if str(item).strip())
    else:
        salience = str(salience or "").strip()

    measured = []
    if silhouette:
        measured.append("骨架轮廓=" + silhouette)
    if proportions:
        measured.append("身体比例=" + proportions)
    if salience:
        measured.append("体型相关视觉重点=" + salience)
    if not measured:
        return (
            "体型骨架硬锁：胸部体积与整体体重、骨架和四肢围度分开执行；"
            "不得因服装版型或胸部描述擅自放大肩宽、躯干厚度、腰胯宽度和四肢围度。"
        )

    slender_markers = (
        "纤细", "偏瘦", "修长", "窄肩", "肩宽偏窄", "躯干薄", "骨架小",
        "四肢细", "手臂细", "大腿细", "小腿细", "腰部明显收窄",
    )
    measured_text = "；".join(measured)
    slender_lock = ""
    if any(marker in measured_text for marker in slender_markers):
        slender_lock = (
            "参考人物属于纤细或偏窄骨架：保持窄肩、薄躯干、细手臂、窄腰、细腿和修长比例；"
            "禁止生成宽肩、粗手臂、厚躯干、宽腰胯、粗腿、壮实或整体丰满体型。"
        )
    return (
        "体型骨架硬锁（独立于服装和胸部局部体积）："
        + measured_text
        + "。"
        + slender_lock
        + "胸部的局部体积不得改变肩宽、胸廓厚度、腰围、胯宽、手臂和腿部围度；"
        "商品贴身或宽松也不得重塑参考人物的骨架、体重感和腿身比例。"
    )


def enforce_apparel_bust_level(prompt, reference_analysis):
    appearance = reference_analysis.get("appearanceLock") if isinstance(reference_analysis, dict) else {}
    level = str(appearance.get("bustLevel") or "uncertain").strip()
    if level == "prominent":
        return prompt
    cleaned = re.sub(
        r"一名25至30岁的成年女性拥有明显丰满的大胸[，,]胸部轮廓饱满突出[，,]胸腰差明显[，,；;。]?",
        "",
        prompt,
    )
    cleaned = cleaned.replace("明显丰满的大胸", "参考图同等的自然胸部体积")
    cleaned = cleaned.replace("丰满突出胸部", "不夸张的自然胸部体积")
    return cleaned.strip()


def strip_viewer_artifacts_from_prompt(prompt):
    """Viewer chrome is not part of the photographed scene."""
    artifact_markers = (
        "轮播圆点",
        "轮播指示",
        "导航点",
        "导航圆点",
        "进度条",
        "页码",
        "播放控件",
        "状态栏",
        "应用水印",
        "截图文字",
        "白色画布",
        "白边",
        "黑边",
    )
    segments = re.split(r"(?<=[。；;])", str(prompt or ""))
    kept = []
    for segment in segments:
        has_artifact = any(marker in segment for marker in artifact_markers)
        is_exclusion = any(marker in segment for marker in ("禁止", "不得", "忽略", "不要出现"))
        if has_artifact and not is_exclusion:
            continue
        kept.append(segment)
    return "".join(kept).strip()


def analyze_apparel_reference(reference_data_url, settings, face_identity_mode="regenerate"):
    identity_analysis_rule = (
        "当前选择不保留原图人脸。画面描述中只能记录脸部是否可见、头部方向、视线方向、表情强度、嘴部开合与受力状态和遮挡关系；"
        "不要描述脸型、眼型、鼻唇、五官比例、妆容特征、神态辨识度或其他可用于还原身份的特征。"
        "但必须客观记录画内可见皮肤的明度和冷暖，以及肩宽、胸部前向体积、胸腰比、腰胯宽度、可见腿长相对躯干的比例、躯干厚度、四肢粗细和整体体型轮廓；这些不是人脸身份信息，后续换脸时仍要保留。"
        "只有当参考图画内确实可见人脸时，后续才生成与原图模特、商品图模特都不同的新人脸；"
        "如果脸部在画外或被边缘裁掉，不得为了生成新人脸而改变景别或扩展画幅。"
        if face_identity_mode != "preserve_reference"
        else "当前选择保留原图人脸，可以记录原图模特的脸型、五官、妆容、发型、表情和脸部遮挡关系。"
    )
    text = call_vision_model(
        model=settings["visionModel"],
        instructions=(
            "你是严格的小红书参考图取证与构图分析助手。当前只有一张参考图，只能记录画面内可直接观察到的像素，禁止推测或补全画外内容。"
            "第一步先判断整张参考图是单张照片还是多宫格拼图。若存在两格或以上独立画格，layoutLock.layoutType 必须为 grid，逐格记录位置、裁切、人物落点和动作；不得把多个画格的人物合成一个 visiblePersonBox 或一个平均姿势。2×2四宫格必须输出 rows=2、columns=2、panelCount=4，并分别记录左上、右上、左下、右下四格。每格 pose 的左右关系必须使用该画格自己的画面左侧/画面右侧坐标。多宫格中同一人物、同一背景、同一服饰与光色的跨格一致性写入 sharedContinuity，分隔线写入 dividerDescription。"
            "先逐边检查画面：上、下、左、右边缘实际穿过什么；人物头顶、脚、腿或躯干被边缘裁掉时，必须写‘不可见’并说明边缘裁到哪里，不能给不存在的头顶留白、脚底距离或完整全身比例。"
            "visiblePersonBox 只框住画内真实可见的人体像素，不得按想象补成完整人体；坐标以整张图宽高各1000计。"
            "必须单独检查人物的横向位置关系，不能只判断人物大小：用 visiblePersonBox 计算人物视觉中心相对画面中轴线的偏移，比较左右背景留白宽度，并检查人物是否贴住或被左、右边缘裁切。frameLock.horizontalPlacementEvidence 必须写清人物中心约在画面宽度百分之几、哪一侧是主要背景负空间，以及哪一侧人物贴边或出画；参考图不是居中构图时，禁止把人脸中心误当整个人物中心，也禁止概括成‘主体居中’。"
            "visiblePersonBox 必须作为最终渲染框而非近似参考：复核人物任意可见像素是否越过框的四边；若商品细节需要更多空间，也只能缩小人物，不得扩大外接框或推进镜头。frameLock.scalePriorityCue 要直接写明‘人物超框时缩小人物并后退镜头’，避免后续优先展示商品而改景别。"
            "必须把顶部人物留白单独复核：从画面第0行向下逐行寻找人物任意可见像素第一次出现的位置，手指、手掌、手臂、头发、头饰、头部和服饰都算人物范围；frameLock.topPersonY 记录这个最上端纵坐标，frameLock.topmostPersonPart 写明首先出现的身体部位。topPersonY 以上才是真正的顶部场景留白，不能用头顶位置代替，也不能忽略上举的手。"
            "输出 JSON 前必须交叉检查 topPersonY 与 visiblePersonBox.y：两者应基本一致；若相差超过30个千分点，重新观察顶部并修正，不得同时输出互相矛盾的留白数值。"
            "frameLock.topBlankEvidence 必须用两个彼此独立的像素锚点复核顶部留白：一是人物最高像素所在行，二是人物最高点相对最近门框、墙缝、镜框、窗框或画面高度中线的位置；明确写出测得的百分比。人物占比还要用最高点、最低点和画内身体终点三者复核，不能只根据脸或躯干大小估计。"
            "frameLock.scaleAnchors 必须独立测量人物局部尺度，不能从 visiblePersonBox 推算：faceBox 框住画内可见脸部轮廓且不包含头发，torsoBox 框住画内可见肩部至腰胯的躯干，左右肩点记录横坐标，头顶、下巴、胸部中心、腰线和画内身体终点记录纵坐标；坐标仍以整张图宽高各1000计。某个锚点确实不可见时省略该字段，不得猜测。"
            "人物有上举、平伸、叉开或出画的四肢时，visiblePersonBox 会被四肢扩大，必须以 faceBox、torsoBox 和肩部跨度共同判断真实镜头距离与人物主体大小；不能因为整体外接框接近就放大脸、肩膀或躯干。"
            "frameLock.shotScale 必须根据可见人物外接框，记录是特写、近景、半身、七分身、近全身或全身，并写出人物高度和宽度约占画面的百分比、四侧边距与可见身体终点；不能只写‘中景’。"
            "frameLock.shotScaleClass 必须严格从 close_up、medium、three_quarter、near_full、full、environmental 中选择一项；frameLock.scalePriorityCue 必须写出最能证明该景别的一个直接像素证据，例如人物外接框比例、顶部负空间、可见身体终点或人物与大面积背景的关系。environmental、full、near_full 和 three_quarter 不得因为商品需要展示而自动升级成更近景别。"
            "personDescription 只记录不涉及身份的性别呈现、年龄段、发型轮廓和体态；appearanceLock.genderPresentation 必须严格从 male、female、uncertain 中选择一项，只依据当前参考图人物的清晰可见性别呈现判断，不得受后续商品图的版型、商品模特或常见营销人群影响。参考图明确为男性时必须选 male，明确为女性时必须选 female，只有像素确实无法确认时才选 uncertain。appearanceLock.subjectPresence 必须记录画面中人物可见的成人年龄段、视觉成熟度、表情强度、视线关系与角色感，只能用成熟/年轻、松弛/紧张、冷静/活泼等非身份描述，不记录可识别五官。appearanceLock.mouthMicroExpression 必须独立记录嘴部当前动作状态：上下唇完全闭合、轻触、微张或明显张开，唇间缝隙是否可见，牙齿与舌头是否可见，画面左侧和画面右侧嘴角分别上扬、水平、下压或收紧，以及下颌放松或轻微绷紧；只能记录状态和方向，不描述唇形、厚度、轮廓或其他身份特征。原图闭唇时必须明确写无唇间缝隙、牙齿与舌头不可见，不能用‘自然表情’概括。appearanceLock.demographicAppearance 只记录像素能够稳定支持的大类外观呈现，例如东亚成年女性、欧美成年女性或无法确认；它不是具体身份，不得写姓名、相似对象或细粒度族裔猜测。换脸时允许生成完全不同的新五官，但不得把参考图清楚可见的大类外观呈现自动改成另一类商业模特。appearanceLock.visibleSkinTone 必须先从‘冷白皮、中性白皮、暖白皮、自然肤色、小麦色、深色肤色’中选择最接近的一档，再记录相对背景的明度和局部色偏；面部在中性或偏冷直闪下呈高明度粉白、明显缺少黄调时应判为冷白皮，不能弱化成中性米白。appearanceLock.facialSkinRendering 必须把场景白平衡与脸部基础肤色分开，记录面中、额头、下颌的基础色是否中性/偏粉/偏黄、环境暖光只影响哪些局部、眼白是否中性，以及毛孔、绒毛、血色和反光是否可见；不得把暖背景直接等同于黄色脸。"
            "appearanceLock.bodySilhouette 只记录肩宽、躯干厚度、四肢粗细和整体体型轮廓；appearanceLock.bodyProportions 必须分别记录胸部相对肩宽与腰宽的前向体积、胸腰差、腰胯宽度、可见腿长相对躯干的比例、大腿和小腿粗细。若胸部体积突出、腰部明显收窄或腿部修长，必须按可见几何关系明确写出，不得用‘身材好、性感、丰满、完美’等评价词，也不得因换装而平均化。appearanceLock.visualSalience 必须选出最影响画面辨识度的2至4项非身份视觉签名，按优先级写清；除构图尺度、体型比例、姿势轴线和角色感外，只要大型包袋、手机、家具或其他道具遮挡躯干、占画面宽高约10%以上，或同时承载双手动作，就必须作为前两项视觉签名，写明品类、相对尺寸、画面位置、遮挡与接触关系。特殊裁切、强烈侧倾和决定空间辨识度的背景结构同样不能降级成普通特征。体型字段严禁写单肩、露肩、吊带、领口、袖子、裙摆、裤装等原服饰结构；"
            "appearanceLock.bustLevel 必须严格从 prominent、non_prominent、uncertain 中选择一项；appearanceLock.bustConfidence 必须从 high、medium、low 中选择。只有去除衣物廓形和透视干扰后，胸部仍相对肩宽与腰宽明确突出、是画面主导几何特征之一，并有至少两条独立身体轮廓证据时，才允许 prominent 且 high。普通、偏小或没有明显强调时选 non_prominent；遮挡严重无法判断时选 uncertain。低领露肤、紧身或宽松衣料、褶皱下垂、俯拍近大远小、自拍广角、手臂挤压、侧身单侧轮廓和裁切放大都只能记入 bustPerspectiveRisk，不能作为 prominent 证据。"
            "appearanceLock.bustEvidence 必须列出独立的身体轮廓像素证据。prominent 至少需要两条彼此独立的证据，例如左右胸部外轮廓均明确超出肋骨线、胸部宽度相对腰宽显著扩大且不是衣物廓形；俯拍近大远小、露肤面积、低领、紧身衣、侧身单侧轮廓、裁切或手臂挤压都不能计入证据。证据不足两条时必须改为 non_prominent 或 uncertain。"
            "poseDescription 必须详细记录自拍关系、躯干前后倾与左右侧倾、躯干旋转、肩线斜率、髋肩扭转、头部方向，并分别记录画面左右两条手臂的上臂方向、肘部弯曲、前臂方向、手部可见性和是否伸出画外。所有左右关系只允许使用最终画面的画面坐标，写成‘画面左侧手臂、画面右侧手臂、画面左侧腿、画面右侧腿’，禁止出现‘左手、右手、左腿、右腿’或括号补充人物解剖左右，避免同一句中两套左右互相冲突。头部侧倾写成‘头顶朝画面左/右偏移’。appearanceLock.directionAnchors 必须提取2至6条不可互换的画面方向锚点，优先选择闭合眼与睁眼、持包手、支撑手、持手机手、近侧肩髋、明显道具、肢体交叉前后等非对称特征；每条都先写画面左侧或画面右侧，最终图任何一条都不得左右交换。appearanceLock.bodyOrientation 必须用正面、三分之二侧身或近侧面加躯干偏转角度、画面哪一侧肩髋更靠近镜头、远侧肩髋被遮挡程度、鼻尖朝向、脸部可见比例和脸部朝向；三分之二侧身或近侧面必须明确写禁止正面化。appearanceLock.actionKeyframe 用一至两句写出最能决定动作的关节和接触关系；appearanceLock.forbiddenPoseFallback 必须根据当前图像写出一个最容易把原动作破坏成默认姿势的具体错误回退，例如把横向并排伸出的双腿改成一腿抬向镜头、把单手自拍改成双手、把侧身改成正面或把支撑手改为悬空，必须同时写清禁止后的正确落点，不得写空泛的‘保持原动作’。actionKeyframe、forbiddenPoseFallback、directionAnchors、poseContacts、postureAndSupport 与 poseSurfaceGeometry 必须逐条交叉校验，同一只画面侧手、同一条画面侧腿的动作、承重点、落点和可见性不得冲突。手与包带或肩部接触时，必须区分肩前、肩顶和颈后：只有手腕与手指确实越过颈部轮廓并位于头颈后方才允许写‘肩后’或‘颈后’；若手指、指节或包带接触点在锁骨、肩峰或肩顶正面可见，必须写肩前可见接触，禁止误写成手伸到颈后。appearanceLock.captureType 必须从 selfie_visible_phone、selfie_phone_out_of_frame、third_party、timer_or_remote、uncertain 中选择，appearanceLock.phoneVisible 必须按像素证据输出布尔值。只有手机可见，或一条手臂明确向镜头延伸且对应手部在画外、透视符合持机时，才允许判断自拍；如果双手均可见或都已有明确动作与接触点，必须判断为他拍或定时遥控，不得再虚构隐藏持机手。appearanceLock.selfieRelation 必须与 captureType、phoneVisible、actionKeyframe 和 poseContacts 完全一致，明确画面哪一侧手持手机、手机是否入画及另一侧手动作；同一只手不得同时持机又抓头发、叉腰、支撑或接触其他物体。appearanceLock.poseContacts 只允许逐条记录手、手臂、脸、头发、腰胯、手机、桌面或场景道具之间的接触点，以及肢体交叉、遮挡和前后层级，严禁在此字段出现原衣服的肩带、领口、袖口、下摆或裤腰；每只可见手还必须写清画面侧、手腕位置、掌心或手背朝向、手指具体接触区域，以及对应手肘位于手的哪一侧和高低关系，只写‘触脸、抚发、叉腰、举手’不合格；"
            "appearanceLock.limbTopology 必须先盘点画内明确可见的手臂数量、手腕数量和手部数量，再按画面左侧/右侧为每只手建立唯一动作和唯一主接触点；必须明确哪些手臂或手在画外、被遮挡或不可见。一名普通人物只有两条手臂和两只手，不得把手指、包带、衣料或反射误认为额外手。limbTopology、actionKeyframe、poseContacts、selfieRelation 必须数量一致且一一对应；如果冲突，必须先修正再输出，禁止留给生图模型自行补全。"
            "appearanceLock.handPositionAudit 必须逐只记录所有可见手的掌心几何中心，centerX、centerY 使用整图0至1000坐标；先定位手的像素中心，再记录该坐标处手的唯一接触动作和可见性，禁止先猜左右再反推坐标。screenSide 必须由 centerX 得出：小于500为画面左侧，大于等于500为画面右侧，并按 centerX 从小到大输出。输出前用该坐标审计 actionKeyframe、poseContacts、limbTopology 和 directionAnchors；若文字左右与坐标冲突，必须按坐标修正文字，不得保留冲突。"
            "输出前必须再次从每侧肩部沿上臂、肘、前臂、手腕一直追踪到指尖，用实际手指像素确认终点和接触物。包带经过肩部或手边不等于手正在握包带；只有手指确实环绕、夹持或压住包带才允许写持包。若手指实际接触另一侧手臂、肩部、头发或脸，必须以该可见接触点为准，禁止被邻近的包带或衣物边缘误导。"
            "appearanceLock.nonTargetWardrobe 只允许记录商品未覆盖的身体区域是否存在独立覆盖，且只能从‘上身区域存在独立非目标服饰覆盖、下身区域存在独立非目标服饰覆盖、脚部区域存在独立非目标服饰覆盖、头部区域存在独立非目标配饰覆盖、身体局部存在独立非目标配饰覆盖’中选择。严禁记录参考图服饰主体的品类、颜色、材质、长度、廓形、裁片、领口、肩带、袖型、开口、图案、文字、Logo 或装饰。appearanceLock.nonTargetWearables 只记录商品主体覆盖区之外仍清楚可见的鞋、袜、靴、帽子、头饰、发饰、包袋、项链、耳饰、手链、戒指、眼镜或围巾；每件单独一项，必须写明准确品类、颜色、结构、画面位置、可见范围及与身体或地面的接触。此字段严禁写入参考图旧上衣、外套、裙装、裤装或连衣裙的任何外观。"
            "appearanceLock.postureAndSupport 必须先用明确类别记录站立、坐姿、跪姿、蹲姿或躺姿，再记录臀部、背部、手、脚、膝盖与墙面、地面、椅子、台阶、沙发等承载面的接触及承重点；坐姿不得只写成躯干动作。appearanceLock.locomotionGeometry 仅在人物行走、上楼或下楼时填写：必须写画面中的行进方向、身体轴线、领先腿和滞后腿各自从髋到膝到脚的二维方向、两脚分别接触哪一级台阶或是否悬空、重心位于哪条腿，以及动作发生在迈步前中后哪个关键帧；静止时输出空字符串。侧身下楼不能概括成站在台阶上，必须以脚掌与不同台阶的接触和身体前移方向作为硬证据。"
            "appearanceLock.poseSurfaceGeometry 必须先记录承载面本身在整图中的外接框、边缘方向和面积占比，再逐段写清臀部、背部、画面左右两条手臂、大腿、小腿、脚和支撑手相对承载面的关系：压在其上、沿其延伸、悬空、垂下、落地、伸出画外或被遮挡。必须明确人物是整体位于承载面上、仅坐靠边缘，还是有身体部位落地；床、长椅、沙发、台面等承载面的品类和人物接触拓扑不得互换。每条可见手臂必须写肩到肘、肘到手在二维画面中指向左上/左下/右上/右下或近水平/近垂直及约多少度；每条可见腿必须写髋到膝、膝到踝、踝到脚尖或画面裁切终点的二维轨迹，明确膝、踝、脚或可见终点位于髋的画面哪一侧、与水平线约多少度。两腿有交叉、重叠或贴近时，必须写交叉或重叠发生在大腿、膝、小腿或脚的哪一段、画面哪条腿遮挡在前、哪条在后、两膝与两踝的间距，以及属于身体接触还是仅二维遮挡；两腿分开时也要写清间距。脚或脚踝在画外不能省略画内可见腿段的交叠、前后层级和裁切终点。不能只写‘向前、向下、自然伸展’等缺少画面方向的三维词。同时记录身体主轴与承载面边缘的夹角。画面看不见的段落写不可见，不得推测。"
            "appearanceLock.foregroundObjectGeometry 记录任何决定构图或动作的显著物体，包括手机、手、包袋、家具和其他道具：只要物体占画面宽或高约10%以上、遮挡人物躯干、被手接触，或明显决定人物动作，即使它不靠近镜头、也不是待替换商品也必须填写。必须先写品类，再写外接框占画面宽高、中心位置、与脸部及躯干的相对尺寸、遮挡面积、每个接触点和近大远小关系；包袋还要写包体宽高分别约为脸宽、脸高或躯干宽的多少倍，禁止只写‘手持包’或大中小等模糊尺寸。手机入画时该字段必填，不能只写‘手持手机’。确实没有显著物体时才输出空字符串。手机未入画也不能直接判为他拍：若画面同时存在自拍臂长透视、高机位向下俯拍、一侧肩臂明显更靠近镜头且对应前臂或手部在画外，必须判为 selfie_phone_out_of_frame；只有两只手都真实可见或都有明确可见接触点时，才允许排除隐藏持机手。"
            "appearanceLock.headPoseRange 必须记录头部俯仰、左右转动和侧倾的大致角度范围，并记录该角度下仍能看见哪些五官；禁止用‘极度后仰’等容易被生成模型放大的词，除非参考图确实达到该程度且人体结构自然。"
            "appearanceLock.faceVisibility 只记录面部是否入画、左右眼分别是睁开、闭合、眯眼还是被何种实物遮挡，以及鼻嘴是否可见；不得记录眼型、脸型、五官比例或其他身份信息。闭眼必须写成完整眼睑闭合，不能写成眼睛消失。"
            "sceneDescription 记录背景和真实可见道具；cameraDescription 记录机位、光线方向、光比和拍摄方式。"
            "只有出现可核验的反射内容，例如人物或空间被镜面对称重复、反射透视与镜框边界同时成立，才允许把亮面、玻璃柜门或黑色竖框判断为镜面。仅看到玻璃、高光、鞋架、陈列柜或竖向黑框时不得猜成镜子。若确认为镜前自拍或大面积镜面，必须在 sceneDescription、selfieRelation 和 backgroundStructureAnchors 中同时记录镜框位置、镜面边界、人物与镜中反射的关系；禁止把真实镜面当成普通墙面或门板忽略。"
            "如果人物从头到双脚或鞋都真实可见，shotScaleClass 必须是 full 或 near_full，visibleBodyParts 必须明确记录双脚/鞋和落地点，bottomEdge 必须说明脚部是否完整；不得改写成半身或七分身。"
            "cameraLock 必须把相机姿态从普通描述中单独提取。第一步先判断相机光心相对人物眼睛、胸口、腰部或地面的高度；第二步把 pitchDirection 严格选为 up、level、down 之一；第三步再写 pitch 的方向与角度。pitchConfidence 必须从 high、medium、low 选择；pitchVisualStrength 从 strong、medium、subtle、none 选择。verticalLineEvidence 单独记录门框、墙线、镜框和空间消失点；surfacePlaneEvidence 单独记录桌面、座面、地面等顶面或底面的可见量；bodyPerspectiveEvidence 单独记录头肩、躯干、腿脚和近侧肢体的近大远小；postureRisk 必须指出人物前倾、低头、弯腰、坐姿或屈膝是否会伪装成俯拍，并明确这些姿势不能作为机位证据。mustPreserveAngleCue 写成图必须肉眼可见的角度证据；yaw 写水平偏转；roll 写画面滚转。"
            "每张图都必须估计35mm等效焦距：focalLength35mm 写可执行范围，例如20至24mm、26至28mm、35至40mm或50至85mm；lensClass 从 ultra_wide、wide、standard、telephoto 中选择；focalConfidence 从 high、medium、low 选择；lensEvidence 必须依据近大远小、边缘拉伸、空间纵深、人物与背景压缩关系和拍摄距离说明判断，不得只凭‘手机拍摄’猜焦距。人物位于画面中央时没有明显边缘拉伸不能排除广角，必须继续看近距离能否同时容纳近全身、地面、墙面和大型环境物，以及近侧腿脚与远侧头肩的尺度差；在有限室内距离仍容纳近全身和大量背景时优先比较20至28mm，而不是自动判成35至40mm。distanceAndLens 同时写主体距离和该焦距带来的视觉效果。广角参考图禁止回退成35至85mm中长焦人像视角；中长焦参考图也不得擅自改成广角。forbiddenFallback 写最不能回退的默认机位与焦距。"
            "俯拍与仰拍都至少需要 verticalLineEvidence、surfacePlaneEvidence、bodyPerspectiveEvidence 中两类独立正向证据。相机低于人物胸口、下巴或手臂底面更可见、近侧腿脚或座椅下沿更突出、空间线条向上收缩支持仰拍；头顶平面明显可见、上半身近大远小、承载面顶面大量暴露、空间线条向下收缩支持俯拍。仅看到地面、完整头顶、楼梯、斜坡、人物前倾、低头、弯腰、坐姿、屈膝或头部大于被裁切下肢，都不能证明俯拍。证据不足必须选 level 并写0度，禁止默认写向下0至3度。若墙线、门框、镜框或海平线基本水平竖直，roll 写0度或不超过1度，不得虚构斜拍。"
            "不得因为画面是 iPhone 随拍或 CCD 抓拍就默认 cameraLock 为平视；设备质感与俯拍、仰拍、斜拍、画面滚转必须按像素证据分别判断。appearanceLock.captureMode 必须从‘暗环境近轴直闪手机快照、自然光手机快照、室内环境光手机快照、早期老旧CCD生活抓拍、现代消费级相机直出、其他’中选择最符合证据的一类并说明依据。只有同时出现至少两类可见证据，例如有限动态范围与高光生硬截断、暗部彩色噪点、低像素压缩或偏硬数码锐化、明显自动白平衡偏移、早期小型传感器直闪衰减，才允许选择早期老旧CCD生活抓拍，并把证据逐条写入 appearanceLock.ccdEvidence；证据不足时 ccdEvidence 输出空数组，不得因为画面低清或有滤镜就猜成 CCD。暗环境直闪时明确记录‘采用昏暗环境用闪光灯拍摄的效果，构图似普通 iPhone 随手拍的视角’，无直闪证据时不得套用。"
            "colorDescription 必须独立记录全局白平衡、冷暖偏色、主要色相、饱和度、对比、黑位、高光、阴影偏色、肤色与背景的相对明度，以及数码直出、HDR、直闪、胶片或柔化等可见成像特征。判断顺序固定为：先列出占画面面积最大的两至三块背景区域及其色相，再用白墙、灰墙、眼白或其他近中性色校验白平衡，最后才判断全局偏色；皮肤、木色、阳光斑和单个暖色物体不能代表全局。appearanceLock.colorAnchor 必须给出可直接执行的绝对颜色锚点：背景主色的具体色名、皮肤基础色、全局色温强度、饱和度等级，以及最终图最需要禁止的错误偏色；必须区分中性灰、蓝灰与青灰，区分冷粉白、中性米白与暖黄，不得只写‘偏冷’或‘偏暖’。综合色偏若只是轻微，写‘整体近中性，局部略暖/略冷’，不得写成‘全局暖黄偏色’。"
            "appearanceLock.globalColorBias 必须服从可见像素而不是默认校正：若大面积背景、阴影和可见中性色共同带同方向的冷绿、黄绿、暖红或蓝灰综合色偏，即使它不自然也要记录并保留；只有近中性色的实际像素确实接近中性时才写整体近中性。不能因为物体语义上是白墙、灰墙、白栏杆或眼白就默认其像素中性；多个中性色锚点、皮肤中间调和阴影都朝同一色相偏移时，必须把该相机白平衡偏移写入 globalColorBias 和 colorAnchor。早期CCD、低动态范围、轻微雾化或自动白平衡漂移不得校正成现代手机的干净中性色。appearanceLock.toneProfile 必须分别记录黑位深浅、阴影细节、中间调亮度、高光滚降或溢出、总体对比度低/中/高及是否有手机HDR压缩；禁止只写‘对比自然’。"
            "appearanceLock.neutralAnchorAudit 必须用一个字符串先列出画内至少两处真正接近中性的锚点及其可见偏色，例如白墙、灰墙、眼白、黑色阴影或金属高光，再给出综合色结论，禁止输出数组。木门、米黄色涂料、肤色、绿植、阳光斑和商品固有色不是中性色锚点。若白灰黑锚点共同呈黄绿、冷绿、暖红或蓝灰偏移，必须把该偏移写入 globalColorBias，不得因为看起来不自然而自动校正；若锚点近中性，则局部木色或米墙不得把整图判成暖黄。neutralAnchorAudit 与 globalColorBias、colorAnchor 冲突时，必须先修正后三者再输出。"
            "appearanceLock.lightingPhysics 必须判断是直闪、直射阳光、柔和散射光还是混合光，并写出主光相对人物来自顶部/前方/侧面/背后的垂直与水平方向、光源颜色、阴影边缘、人物各区域高光与面部阴影、背景衰减关系。若有顶光，必须点名暖色或冷色顶光落在发顶、额头、鼻梁、肩颈、锁骨或服饰上缘中的哪些区域，以及这些区域相对背光面的明确色差和亮度差；不得只写背景灯带或泛化成均匀提亮。直闪要写近镜头轴瞬间照亮、皮肤或面料镜面高光、远景变暗和环境灯残留。只要人物、服饰、台面、水面或背景出现方向一致的局部明亮日照斑、硬边或半硬边投影、树影、强烈镜面高光、亮部接近曝光上限，并与背光面形成明确亮暗分区，就不能判为纯柔和散射光：方向性日照占主导时判 direct_sun，环境反射明显抬起暗部但仍保留阳光斑时判 mixed。水面或浅色石材的强反光不能被误当成均匀柔光。"
            "appearanceLock.highlightBehavior 必须独立记录高光边缘是锐利、半硬还是柔散，是否存在局部辉光、轻微雾化、光晕、高光溢出或数码截断，并点名它发生在人物、衣物或背景的具体区域；没有则明确写无。局部辉光不能被概括成‘光线明亮’，有边界的阳光斑不能被改写成整个人均匀提亮。appearanceLock.mustPreserveLightingCue 必须优先选择一个直接落在人物身上、有明确位置、颜色和边界、可以在成图中肉眼验收的顶光、侧光、轮廓光、局部光斑或投影；只有人物身上确实没有可见方向性证据时才可选择背景光源或闪光衰减。"
            "appearanceLock.lightingMode 必须严格从 near_axis_flash、fill_flash、direct_sun、diffuse_daylight、mixed、indoor_ambient 中选择一项。先填写 daylightEvidence：逐条记录窗户或玻璃外景、天空、室外绿植、窗边大面积柔和亮度渐变、人物与背景共享的主光方向、自然投影、阳光斑或树影；这些证据能解释人物高光时优先判日光。再填写 flashEvidence，且每条必须点明发生位置，只允许记录贴近镜头轴的硬影、近景到远景的快速光衰减、人物正面与背景曝光分离、皮肤或面料小面积瞬时正面镜面反光、面部阴影被近轴光压平。皮肤白、人物比背景亮、黑墙、眼神光、阴影浅或正面受光均匀不能单独进入 flashEvidence。flashConfidence 必须从 high、medium、low 中选择；只有 flashConfidence=high、至少三类独立闪光证据，并且其中包含贴轴硬影，或同时包含快速衰减与正面瞬时镜面反光，才允许选择 near_axis_flash/fill_flash。否则 flashEvidence 必须为空并按 direct_sun、diffuse_daylight、mixed 或 indoor_ambient 解释；有窗边或室外日光证据而无闪光专属锚点时，禁止升级为补闪。方向性日照主导时判 direct_sun；日照与环境反射并存时判 mixed；室内窗边柔光判 diffuse_daylight；纯室内灯光判 indoor_ambient。appearanceLock.mustPreserveLightingCue 必须写出一个成图肉眼可见且可验收的光线证据，不能只写‘自然明亮’。appearanceLock.globalColorBias 必须描述整张画面的总体综合色偏和强度，例如轻微冷绿、近中性略暖、明显暖红；它不能抄局部衣物、绿植或木墙的固有色，也不能把局部反光误写成全局偏色。若最大面积背景与中性色校验接近中性，即使皮肤或木质家具略暖，也必须写‘整体近中性’，不能写全局暖黄。"
            "appearanceLock.backgroundColorRelation 必须记录背景占主导的色相、明度和饱和度，以及它相对肤色和商品区域更冷/更暖、更亮/更暗的关系。"
            "暗色背景必须区分真实场所与棚拍背景：只要画面仍能看见墙面颗粒、接缝、划痕、风化、栏杆、锈迹、门窗、地面交界或环境灯，backgroundColorRelation 和 environmentRealism 就必须逐项保留这些低对比结构，并明确不是无缝黑幕、纯色背景或影棚布景；不得把欠曝写成‘纯黑无细节’。"
            "appearanceLock.captureRealism 必须记录参考图真实可见的拍摄设备感和不完美成像，包括镜头透视、边缘软硬变化、景深过渡、自动曝光与白平衡波动、噪点或压缩、边缘锐化、运动模糊、高光滚降或溢出、阴影细节、皮肤纹理与是否存在磨皮；不得只写‘真实感’。日常照片默认使用自然半哑光皮肤、有限且位置合理的高光、轻微局部色差和不均匀清晰度，禁止写成全脸油亮、瓷白发光、完美对称、全画面同等锐利或商业精修人像。"
            "appearanceLock.snapshotImperfections 必须从参考图中列出2至5条真正属于相机成像或被摄场景、可复制的不完美证据，例如轻微曝光漂移、白平衡偏移、有限动态范围、边缘软化、手持滚转、轻微噪点压缩、背景杂物、非对称裁切或局部运动模糊；不得虚构。轮播圆点、导航点、进度条、页码、播放控件、状态栏、应用水印、截图文字、白色画布、边框和黑白留边一律是查看器界面，不属于场景，不得写入任何字段。日常手机快照若完全没有真实成像瑕疵就继续保持自然，不得拿界面元素凑数。"
            "appearanceLock.environmentRealism 必须记录室内或外景的空间真实性。外景要具体记录远近对比衰减、空气透视、天空/地面/绿植的不规则色差、主光与环境反射、风对发丝和衣摆的真实影响、背景是广景深还是光学虚化；室内则记录墙面、木纹、镜面、家具的非均匀反光和空间光衰减。禁止写‘8K、电影级、大师杰作、高级感、专业级打光’等质量堆词。"
            "所有字段都要具体，colorDescription 不得用‘氛围感’、‘高级感’等空词代替。"
            "所有字段都不能描述参考图人物原服饰的品类、颜色、材质、图案、文字、Logo、领口、肩带、袖型、版型、裁片、开口、裙摆、裤型或装饰。方向锚点、动作关键帧、接触关系、体型证据和场景描述只能引用身体、五官可见状态、肢体、道具、承载面和背景几何，不得用旧服饰边缘作为空间锚点。"
            "referenceDescription 中原商品仍只能抽象成‘待替换商品区域’，仅记录该区域与肩颈、手臂、腰部、头发、手机及画面边界的接触、遮挡和裁切关系。"
            + identity_analysis_rule
            + "输出必须紧凑：每个字符串字段尽量控制在60个中文字内，每个数组最多4项，每项最多45字；不要在多个字段重复同一事实。只输出完整 JSON，不要 Markdown。"
        ),
        content=[
            {"type": "input_image", "image_url": reference_data_url},
            {
                "type": "input_text",
                "text": (
                    "请严格输出 JSON："
                    "{\"hasFace\":boolean,\"reason\":\"人脸判断原因\","
                    "\"layoutLock\":{\"layoutType\":\"single/grid\",\"rows\":0,\"columns\":0,\"panelCount\":0,"
                    "\"dividerDescription\":\"分格线位置、颜色和粗细\",\"sharedContinuity\":\"跨格必须一致的人物、商品、背景和光色\","
                    "\"panels\":[{\"position\":\"左上/右上/左下/右下或第N格\",\"crop\":\"该格景别与四边裁切\","
                    "\"subjectPosition\":\"人物在该格的位置与占比\",\"pose\":\"该格独立动作、表情和接触关系\"}]},"
                    "\"frameLock\":{\"topEdge\":\"上边缘实际裁切\",\"bottomEdge\":\"下边缘实际裁切\","
                    "\"leftEdge\":\"左边缘实际裁切\",\"rightEdge\":\"右边缘实际裁切\","
                    "\"topPersonY\":0,\"topmostPersonPart\":\"最先出现的手指/头发/头部或其他人物部位\","
                    "\"topBlankEvidence\":\"最高人物像素与固定背景锚点共同复核出的顶部留白\","
                    "\"visiblePersonBox\":{\"x\":0,\"y\":0,\"width\":0,\"height\":0},"
                    "\"horizontalPlacementEvidence\":\"人物视觉中心、左右留白差、主要背景负空间及左右贴边裁切证据\","
                    "\"scaleAnchors\":{\"faceBox\":{\"x\":0,\"y\":0,\"width\":0,\"height\":0},"
                    "\"torsoBox\":{\"x\":0,\"y\":0,\"width\":0,\"height\":0},"
                    "\"leftShoulderX\":0,\"rightShoulderX\":0,\"headTopY\":0,\"chinY\":0,"
                    "\"chestCenterY\":0,\"waistY\":0,\"visibleBodyEndY\":0},"
                    "\"visibleBodyParts\":[],\"invisibleBodyParts\":[],\"visibleSceneElements\":[],"
                    "\"shotScale\":\"景别、人物宽高占比、四侧边距和可见身体终点\","
                    "\"shotScaleClass\":\"close_up/medium/three_quarter/near_full/full/environmental\","
                    "\"scalePriorityCue\":\"最能证明景别的直接像素证据\"},"
                    "\"cameraLock\":{\"cameraHeight\":\"相机相对人物的高度\","
                    "\"pitchDirection\":\"up/level/down\",\"pitch\":\"俯拍或仰拍方向及角度\","
                    "\"pitchConfidence\":\"high/medium/low\",\"pitchVisualStrength\":\"strong/medium/subtle/none\","
                    "\"verticalLineEvidence\":\"门框墙线镜框与消失点证据\","
                    "\"surfacePlaneEvidence\":\"顶面底面和承载面可见证据\","
                    "\"bodyPerspectiveEvidence\":\"头肩躯干腿脚近大远小证据\","
                    "\"postureRisk\":\"前倾低头坐姿等姿势干扰及排除结论\","
                    "\"mustPreserveAngleCue\":\"成图必须可见的角度证据\",\"yaw\":\"水平偏左或偏右方向及角度\","
                    "\"roll\":\"画面顺时针或逆时针滚转角度\","
                    "\"focalLength35mm\":\"35mm等效焦距范围\",\"lensClass\":\"ultra_wide/wide/standard/telephoto\","
                    "\"focalConfidence\":\"high/medium/low\",\"lensEvidence\":\"近大远小边缘拉伸与空间压缩证据\","
                    "\"distanceAndLens\":\"拍摄距离与镜头透视\","
                    "\"perspectiveEvidence\":\"支持机位判断的画内透视证据\",\"forbiddenFallback\":\"禁止回退的默认机位\"},"
                    "\"appearanceLock\":{\"genderPresentation\":\"male/female/uncertain\",\"visibleSkinTone\":\"可见皮肤明度与冷暖\","
                    "\"facialSkinRendering\":\"面部基础肤色、环境色影响范围、眼白、毛孔血色与反光\","
                    "\"bodySilhouette\":\"肩宽、躯干厚度、四肢粗细和整体体型\","
                    "\"bodyProportions\":\"胸部前向体积、胸腰比、腰胯宽度、腿身比与腿部粗细\","
                    "\"bustLevel\":\"prominent/non_prominent/uncertain\",\"bustConfidence\":\"high/medium/low\","
                    "\"bustPerspectiveRisk\":\"透视、裁切、姿势与衣料干扰\",\"bustEvidence\":[],"
                    "\"visualSalience\":\"按优先级列出2至4项必须继承的构图、体型、姿势、标志性道具或背景核心特征\","
                    "\"subjectPresence\":\"成人年龄段、视觉成熟度、表情强度、视线关系与非身份角色感\","
                    "\"mouthMicroExpression\":\"上下唇开合与接触、唇间缝隙、牙齿舌头可见性、画面左右嘴角方向及下颌受力\","
                    "\"demographicAppearance\":\"像素可确认的大类外观呈现，无法确认则写无法确认\","
                    "\"faceVisibility\":\"面部入画范围、左右眼状态、鼻嘴可见性及真实遮挡\","
                    "\"postureAndSupport\":\"姿态类别、承载面、臀背手脚膝的接触与承重点\","
                    "\"bodyOrientation\":\"正面/三分之二侧身/近侧面、躯干偏转角、鼻尖朝向、脸部可见比例、近远侧肩髋及遮挡程度\","
                    "\"directionAudit\":{\"faceCenterX\":0,\"noseTipX\":0,\"evidence\":\"双眼中点或脸框中心与鼻尖的画面坐标证据\"},"
                    "\"handPositionAudit\":[{\"screenSide\":\"left/right\",\"centerX\":0,\"centerY\":0,\"contact\":\"该坐标处手的唯一接触动作\",\"visibility\":\"完整/局部/遮挡\",\"evidence\":\"手腕掌心与接触物的像素证据\"}],"
                    "\"actionKeyframe\":\"决定动作的一至两句关节与接触关系\","
                    "\"limbTopology\":\"可见手臂/手腕/手数量，每只手唯一动作与主接触点，画外或遮挡状态\","
                    "\"forbiddenPoseFallback\":\"最可能发生的错误姿势回退及其正确落点\","
                    "\"directionAnchors\":[\"画面左侧/右侧不可互换的非对称锚点\"],"
                    "\"captureType\":\"selfie_visible_phone/selfie_phone_out_of_frame/third_party/timer_or_remote/uncertain\","
                    "\"phoneVisible\":boolean,"
                    "\"selfieRelation\":\"单手/双手/他拍、持手机手、手机是否入画、另一只手动作\","
                    "\"foregroundObjectGeometry\":\"近镜头或显著道具的外接框、中心、相对人物尺度、遮挡、逐手接触点和透视关系，无则为空\","
                    "\"nonTargetWardrobe\":[\"仅输出固定的身体区域独立覆盖关系，不含任何服饰外观\"],"
                    "\"nonTargetWearables\":[\"商品覆盖区外可见的鞋袜或配饰：准确品类、颜色、结构、位置、可见范围与接触\"],"
                    "\"poseSurfaceGeometry\":\"身体各段相对承载面的压靠、悬空、垂下、落地、遮挡及主轴夹角\","
                    "\"locomotionGeometry\":\"行走或上下台阶的方向、领先腿/滞后腿、脚掌台阶接触、重心和动作相位，静止为空\","
                    "\"headPoseRange\":\"头部俯仰转动侧倾角度范围及仍可见五官\","
                    "\"poseContacts\":[],\"lightingPhysics\":\"光型、方向、高光阴影与背景衰减\","
                    "\"lightingMode\":\"near_axis_flash/fill_flash/direct_sun/diffuse_daylight/mixed/indoor_ambient\","
                    "\"flashConfidence\":\"high/medium/low\",\"flashEvidence\":[],\"daylightEvidence\":[],"
                    "\"mustPreserveLightingCue\":\"成图必须可见的一项光线证据\","
                    "\"highlightBehavior\":\"高光边缘、局部辉光、雾化、光晕、溢出或截断及其位置，无则明确写无\","
                    "\"glowEvidence\":[\"局部辉光发生位置、扩散宽度、强弱和范围\"],"
                    "\"backgroundColorRelation\":\"背景主色及其与人物的亮暗冷暖关系\","
                    "\"environmentColorZones\":[\"天空/水面/地面/建筑等大面积区域的位置占比、具体色相明度饱和度、渐变方向和相邻反射关系\"],"
                    "\"globalColorBias\":\"整张画面的综合色偏与强度\","
                    "\"globalColorBiasStrength\":\"none/subtle/moderate/strong\","
                    "\"neutralAnchorAudit\":\"至少两处白灰黑中性色锚点的可见偏色及综合色结论\","
                    "\"toneProfile\":\"黑位、阴影细节、中间调、高光滚降、总体对比度与HDR压缩\","
                    "\"colorAnchor\":\"背景与皮肤绝对色名、色温强度、饱和度等级和禁止出现的错误偏色\","
                    "\"captureMode\":\"暗环境直闪手机快照/自然光手机快照/室内环境光手机快照/早期老旧CCD生活抓拍/现代消费级相机直出/其他及依据\","
                    "\"ccdEvidence\":[\"仅列可见的CCD成像证据，证据不足为空数组\"],"
                    "\"captureRealism\":\"镜头透视、清晰度变化、自动曝光、白平衡波动、噪点压缩、运动模糊、高光阴影和皮肤纹理\","
                    "\"snapshotImperfections\":[\"参考图真实可见的生活快照不完美证据\"],"
                    "\"environmentRealism\":\"空气透视、远近层次、自然纹理色差、环境反射、风与景深真实性\","
                    "\"backgroundStructureAnchors\":[\"不可替换背景结构的位置、尺度、邻接、遮挡与层级\"],"
                    "\"backgroundForbiddenFallback\":\"最容易发生的背景简化错误\"},"
                    "\"personDescription\":\"不涉及身份的人物信息\",\"poseDescription\":\"动作和手势\","
                    "\"sceneDescription\":\"场景与可见道具\",\"cameraDescription\":\"机位、光线方向、光比和拍摄方式\","
                    "\"colorDescription\":\"白平衡、冷暖偏色、主要色相、饱和度、对比、黑位、高光、阴影偏色和成像质感\"}。"
                    "hasFace 只有当真人脸部清晰、足够大、五官大部分可辨认、适合最终图沿用人物形象时才为 true；"
                    "如果脸太小、严重遮挡、背脸、极端模糊、插画或海报里的脸，都为 false。"
                ),
            },
        ],
        temperature=0,
        max_output_tokens=6000,
        timings=settings.get("timings"),
        timing_label="kimi_apparel_reference_analysis",
    )
    data = parse_json_text(text)
    has_face = bool(data.get("hasFace"))
    if not isinstance(data.get("hasFace"), bool):
        lowered = text.lower()
        has_face = '"hasface": true' in lowered or '"hasface":true' in lowered
    fallback_layout_text = json.dumps(data, ensure_ascii=False)
    layout_lock = normalize_reference_layout_lock(data.get("layoutLock"), fallback_layout_text)
    frame_lock = normalize_reference_frame_lock(data.get("frameLock"))
    appearance_lock = normalize_reference_appearance_lock(data.get("appearanceLock"))
    appearance_lock = reconcile_reference_screen_direction(appearance_lock)
    camera_lock = normalize_reference_camera_lock(data.get("cameraLock"))
    camera_lock = reconcile_reference_camera_lock(camera_lock, frame_lock)
    appearance_lock = reconcile_reference_capture_type(appearance_lock, camera_lock)
    reference_description = build_reference_description_from_fields(data, frame_lock)
    if not reference_description:
        reference_description = remove_reference_product_appearance(
            data.get("referenceDescription")
        )
    if not reference_description:
        reference_description = remove_reference_product_appearance(
            extract_reference_description_text(text)
        )
    return {
        "hasFace": has_face,
        "reason": str(data.get("reason") or "").strip(),
        "layoutLock": layout_lock,
        "frameLock": frame_lock,
        "appearanceLock": appearance_lock,
        "cameraLock": camera_lock,
        "referenceDescription": reference_description,
    }


def compose_non_apparel_prompt(reference_data_url, product_data_urls, settings):
    if isinstance(product_data_urls, str):
        product_data_urls = [product_data_urls]
    product_data_urls = [item for item in product_data_urls if isinstance(item, str) and item]
    subject_hint = settings.get("productSubjectHint", "")
    user_prompt = settings.get("userPrompt", "").strip() or DEFAULTS["defaultUserPrompt"]
    text, raw_response = call_vision_model_with_debug(
        model=settings["visionModel"],
        instructions=(
            f"{settings['nonApparelPrompt']}"
            f"{NON_APPAREL_HUMAN_CARRIER_RULES}"
            f"{PRODUCT_STRUCTURE_GUARDRAILS}"
            f"{SCENE_REPLICATION_GUARDRAILS}"
        ),
        content=[
            {"type": "input_image", "image_url": reference_data_url},
            *[
                {"type": "input_image", "image_url": product_data_url}
                for product_data_url in product_data_urls
            ],
            {
                "type": "input_text",
                "text": (
                    "第一张图是参考图，只负责提供最终生成图的场景、构图、光影、景别、主体占比和整体视觉气质。"
                    "第二张以及其后的图都是用户上传的商品素材图，共同提供最终要生成出来的非服饰商品主体，并且都会直接作为生图模型的商品参考图。"
                    "这些商品素材图如果包含模特、人脸、手臂、身体、姿势或拍摄背景，这些全部是干扰，不得影响最终图的人物可见范围、动作、四边裁切、机位和场景。"
                    "你的输出必须是最终成图的中文描述，不要说“参考图里”“商品图里”，而要直接描述最终图片本身。"
                    "最终图片必须是：用户商品在视觉上成为新的主体，但整个画面的场景、机位、镜头、背景、时间段、光影关系、陈列方式、主体大小、主体落点、主体朝向、主体倾斜角度、主体与承载面的接触方式、前后层级和遮挡关系都尽量接近参考图。"
                    "如果参考图中有人物，必须用具体方位描述躯干侧倾和旋转、肩线斜率、髋肩扭转，以及每条手臂的上臂方向、肘部弯曲、前臂方向、手部可见性和出画关系；不得把非对称自拍动作改成正面站立或对称展示姿势。"
                    f"{NON_APPAREL_HUMAN_CARRIER_RULES}"
                    "必须单独用至少两句具体描述参考图的全局色彩与成像质感：白平衡冷暖、主要色相偏移、饱和度、对比和黑位、高光是滚降还是溢出、阴影偏色、肤色或商品与背景的相对明度，以及真实可见的数码直出、手机 HDR、直闪、胶片或柔化特征。"
                    "请特别关注参考图中主体是平放、斜放、竖立、倚靠、悬浮、叠放还是局部被裁切，以及主体中心位于画面哪个区域、长轴朝向哪个方向。"
                    "商品的品类和关键结构必须写清楚：包括真实存在的主要部件、数量、连接关系、覆盖范围、开口和边缘轮廓；同时明确商品图中不存在的结构不能出现。"
                    "商品的精细颜色、材质、品牌、logo、文字、纹理、刻字和工艺可以交给图像参考输入，但不得因此省略会影响商品类型的结构描述。"
                    f"{build_subject_hint_text(subject_hint)}"
                    f"用户补充要求：{user_prompt}"
                    "输出格式必须严格为：FINAL_PROMPT: 后面接一整段最终给生图模型使用的中文 prompt。"
                    "不要输出分析、推理、解释、标题、清单、Markdown 或 JSON。"
                ),
            },
        ],
        temperature=0,
        max_output_tokens=1500,
        timings=settings.get("timings"),
        timing_label="kimi_non_apparel_prompt",
    )
    prompt = extract_final_prompt_text(text)
    if not prompt:
        return build_non_apparel_safe_fallback(subject_hint, user_prompt)
    return prompt


def compose_apparel_final_prompt(
    product_data_urls,
    reference_analysis,
    settings,
    face_identity_mode="regenerate",
):
    if isinstance(product_data_urls, str):
        product_data_urls = [product_data_urls]
    product_data_urls = [item for item in product_data_urls if isinstance(item, str) and item]
    reference_has_face = bool(reference_analysis.get("hasFace"))
    reference_description = str(reference_analysis.get("referenceDescription") or "").strip()
    reference_layout_execution = build_reference_layout_execution_lock_text(reference_analysis)
    reference_frame_lock = build_reference_frame_lock_text(reference_analysis)
    reference_camera_lock = build_reference_camera_lock_text(reference_analysis)
    reference_appearance_lock = build_reference_appearance_lock_text(reference_analysis)
    reference_frame_execution = build_reference_frame_execution_lock_text(reference_analysis)
    reference_color_execution = build_reference_color_execution_lock_text(reference_analysis)
    reference_bust_execution = build_reference_bust_execution_lock_text(reference_analysis)
    subject_hint = settings.get("productSubjectHint", "")
    user_prompt = settings.get("userPrompt", "").strip() or DEFAULTS["defaultUserPrompt"]
    multi_product_rule = ""
    if len(product_data_urls) > 1:
        multi_product_rule = (
            f"本次共有{len(product_data_urls)}张由用户分别导入的商品素材图；默认每张独立素材都是用户有意选择的目标商品，"
            "必须逐张识别、逐件写入最终画面，并按各自对应的身体区域组合穿着。"
            "不得套用单图场景下‘只选择最居中的一件’规则，也不得漏掉其中任一张素材对应的商品。"
        )
    content = [
        *[
            {"type": "input_image", "image_url": product_data_url}
            for product_data_url in product_data_urls
        ],
        {
            "type": "input_text",
            "text": (
                "当前输入图均为用户上传的商品素材图，多张图共同提供商品结构与外观；小红书参考图不在本次图像输入中，它已被上一步转换为下方的场景与构图描述。"
                + multi_product_rule
                + reference_layout_execution
                + "你必须先锁定商品图中真正要替换的商品主体；商品主体既可能是单件，也可能是明确成套出现的多件组合，必须按实际件数逐件写进最终画面。"
                "写最终 prompt 前先在内部完成逐件商品结构白名单：按品类与件数、领口或腰头、肩部连接点与肩带数量、袖窿与袖子、开合与开孔、下摆或裤脚、拼接和标识逐槽核对。只有在商品图中能沿轮廓连续确认的结构才可写入；无法确认就留空，不得根据常见款式补全。"
                "尤其不得把商品图留白、文字、人体皮肤边缘、另一件单品的轮廓或模糊细线误认成绕颈带、后颈系带、蝴蝶结、交叉肩带、额外内搭或镂空。"
                "最终 prompt 必须明确写出该商品的品类、主色、廓形、结构、面料、图案、领口、肩带、袖长、腰线、下摆、裤脚或其他最有辨识度的可见特征；"
                "不能用‘以商品图为准’替代商品外观描述，也不能回退到参考图人物原本穿着的商品。"
                "商品图中可见的品牌标签、logo、文字贴标、刺绣章或独立徽标属于商品结构锚点，不是可省略装饰：最终 prompt 必须写明其外观、所在身体区域、相对领口/门襟/中轴的位置和可见范围。若该商品区域在参考构图中入镜，标识必须保持商品内相对位置、尺寸和朝向并清楚可见；项链、头发、包带或其他非商品配饰与它冲突时，让配饰错开或删除。若标识所在区域本来在画外或被动作遮挡，则维持原裁切或遮挡，禁止把标识移动到其他位置，也禁止为展示标识拉远镜头、缩小或居中人物。"
                "商品图中的模特、脸、发型、性别、姿势、手势、身体比例、背景、道具和搭配品都是干扰，只提取被锁定的商品本身。"
                "appearanceLock.genderPresentation 是不可覆盖的人物硬锁：male 时最终画面必须明确为男性人物并禁止女性身体呈现，female 时最终画面必须明确为女性人物；商品图的模特性别和商品营销人群不得改变该字段。"
                "商品图的白平衡、环境光、肤色、曝光、对比、饱和度、背景色和滤镜同样是干扰，最终画面全局调色只能来自下方参考场景的 colorDescription 和光色硬锁。"
                "商品图中人物的头部和人脸完整度也是干扰；如果参考图上边缘裁掉头部或脸部，最终 prompt 不得补出完整脸部。"
                "构图优先级高于商品完整度：商品图即使展示全身或完整商品，也不得拉远镜头、缩小人物、补出腿脚、鞋子、地面或画外商品部位。"
                "默认换脸只替换身份特征，不能改变参考描述中的可见肤色、肩宽、胸部前向体积、胸腰比、腰胯宽度、腿身比、躯干厚度、四肢粗细、成人年龄段、视觉成熟度和整体角色感；不得把人物自动标准化为纤瘦、平胸、短腿、白皙、幼态或甜妹式商业模特。"
                "默认换脸还必须保留 demographicAppearance 中像素可确认的大类外观呈现；只生成不同五官和不同身份，不得把清楚可见的东亚成年女性自动改成欧美面孔，或反向改成另一类人群。若该字段无法确认，不得自行猜测。"
                "若存在拼图版式硬锁，最终 prompt 必须先完整写拼图布局和逐格执行要求，再写每一格自己的构图与机位；否则最终 prompt 的开头顺序固定为：第一句构图与人物占比，第二句机位硬锁。若人物接触床、长椅、沙发、台面或其他承载面，下一句立即写承载面外接范围及人物整体/局部位于其上的接触拓扑；若 foregroundObjectGeometry 非空，再写显著物件相对脸部和躯干的尺寸、整图外接框、中心、遮挡和逐手接触；随后写背景结构锚点，再写身体朝向与动作关键帧。动作关键帧必须保留结构化分析中的画面侧、手腕位置、掌心或手背朝向、手指接触区域和手肘高低，不能压缩成泛化动作词。只有 appearanceLock.bustLevel=prominent、bustConfidence=high 且 bustEvidence 至少有两条独立轮廓证据时，动作句之后的第一句开头才必须原样写‘一名25至30岁的成年女性拥有明显丰满的大胸，胸部轮廓饱满突出，胸腰差明显’，不要解释衣料受力，不要改写成胸部前向体积等分析语言，也不得用纤细、偏薄或标准身材弱化它；置信度不足或 bustLevel=non_prominent/uncertain 时禁止写大胸、丰满突出或夸张胸腰差。"
                "商品结构句必须写在体型句之前。若参考描述明确可见事业线，且商品自身清楚具有足以自然露出该区域的低领或开放领口，才可写‘可见与商品领口自然允许范围一致的事业线’，且露肤范围不得超过商品图；如果商品结构不允许，只保留体型，不写事业线，不降低领口，不虚构开口、吊带或内衣式结构。"
            "必须把场景白平衡与面部基础肤色分别写清楚：先按画面面积最大的背景区域确定综合色，再用白墙、灰墙或眼白校验白平衡；非直闪时，暖墙、夕阳、木色或绿植反光只能局部影响受光面、边缘光和阴影，不能让整张脸统一发黄发橙；除非参考分析明确如此，面中和眼白应保持自然中性并带轻微血色。若综合色偏只为轻微，写整体近中性和局部冷暖，禁止写全局暖黄滤镜。"
            "appearanceLock.backgroundStructureAnchors 必须列出2至5个不可替换的背景结构锚点，优先选择占画面面积较大、决定空间辨识度的镜子及镜框、床、长椅、沙发、门窗、柱子、栏杆、墙面分缝、台阶、固定家具和明显景深层级；每条都写明画面位置、约占宽高、相邻关系、遮挡与前后层级。大型镜子无论是否用于自拍，都必须记录镜框、镜面边界、支架及反射人物或反射空间，不能只写室内墙面；大型承载面必须记录其外接范围、边缘方向和人物接触区域。appearanceLock.backgroundForbiddenFallback 必须写出本图最容易发生的背景简化错误，例如把大型镜子、床、长椅、门或柱子替换为空墙；不得写空泛的保持背景。"
                "若是镜前自拍，最终 prompt 必须同时写出四类可验收证据：镜框至少三边可见、镜外前景与镜内反射有清楚边界、手机镜头朝镜面、人物只出现在镜面内；禁止改成第三人称他拍、透明玻璃门或普通墙面前站立。"
                "必须先采用 neutralAnchorAudit 校验 globalColorBias 和 colorAnchor：白灰黑锚点共同呈现的轻微黄绿、冷绿、暖红或蓝灰综合色要如实写入；锚点近中性时，木门、米墙、肤色、绿植或阳光斑只能作为局部固有色，不得把整图写成暖黄。"
                "必须把光线写成可执行的物理关系，并严格服从结构化 lightingMode。near_axis_flash/fill_flash 只有 flashConfidence=high 且闪光专属证据通过校验时才可出现；否则最终 prompt 必须明确无闪光灯。窗边、玻璃外景、天空、室外绿植、宽阔柔和亮度渐变或人物与背景共享主光时，按日光或环境光写其方向、软硬、局部高光和自然阴影，禁止因皮肤白、人物较亮或背景偏暗擅自加入直闪、补闪、贴轴硬影和过曝白皮。"
            "必须原样落实 highlightBehavior：参考图存在局部辉光、轻微雾化、光晕、高光溢出或有边界的阳光斑时，写明发生位置、范围和边缘软硬，并要求成图肉眼可见；不得用整个人均匀提亮替代局部光感。"
            "appearanceLock.glowEvidence 必须只记录肉眼可见的局部辉光证据：点名发生在人物轮廓、发丝、皮肤高光、灯源或高反差边缘的哪一侧，写清扩散宽度、强弱和影响范围；若亮边向暗部有柔和扩散、逆光发丝泛光或局部高光轻微溢出，就不能误判为无辉光。没有可见证据时输出空数组，禁止泛化成全图柔焦。"
            "必须准确沿用参考描述中的背景主色、明度、饱和度及其与人物的冷暖和亮暗关系，不能自动换成更明亮或更中性的背景。必须把绝对色彩锚点写入最终 prompt：具体背景色名、皮肤基础色、色温强度、饱和度等级和禁止偏色；中性冷灰不能写成蓝青滤镜，暖环境不能写成整脸橙黄，参考图确有的冷绿或暖红综合色偏也不能被自动中和。"
            "只要 environmentColorZones 非空，最终 prompt 必须逐项写出这些大面积区域的具体颜色和空间范围，不得压缩成‘户外自然光’或‘暖色氛围’。天空必须明确顶部、云层、地平线各自颜色及渐变方向；日落或黄昏必须保留暖橙/粉橙/紫红光带的方位、面积和饱和度，并同步写出水面、建筑或人物边缘实际可见的环境色反射，禁止回退成灰白阴天或普通蓝天。"
            "appearanceLock.globalColorBiasStrength 必须从 none、subtle、moderate、strong 中选择。subtle 只允许表现为中性色上的轻微白平衡痕迹，大面积白灰仍应接近中性，绝不能放大成覆盖整图的绿、黄、红或蓝滤镜；moderate 或 strong 才允许综合色明显主导画面。"
                "必须沿用 toneProfile 的黑位、阴影细节、中间调、高光滚降和总体对比度；低对比参考图不得生成深黑硬阴影、过曝白皮或商业人像高反差。"
                "动作必须落实到每条手臂的关节方向、接触点和前后层级。最终 prompt 只允许使用‘画面左侧/画面右侧’作为执行坐标，禁止再写人物解剖左手、右手、左腿、右腿或括号校验，避免两套左右冲突。第三句动作关键帧之后必须立即写‘禁止整幅水平翻转’，再逐条写入经过净化的 directionAnchors；这些锚点只能描述身体、眼睛可见状态、肢体、道具、承载面和背景几何，禁止出现参考图旧服饰的边缘、领口、肩带、袖口、裁片、开口、下摆、颜色或装饰。侧身朝向、近侧肩髋、头部侧倾、睁闭眼、持手机手、持包手、支撑手、交叉前后和道具位置均不得左右互换。眼睛必须写‘画面左侧眼/画面右侧眼’，不能只写左眼或右眼。手是否贴脸、扶头、叉腰、支撑、交叉或伸出画外都不能省略。"
                "handPositionAudit 是手部方向的最高优先级证据。最终 prompt 必须逐只写清手的画面侧、0至1000中心坐标和该坐标处的唯一接触动作；centerX小于500只能是画面左侧，centerX大于等于500只能是画面右侧。若 actionKeyframe、poseContacts、limbTopology 或 directionAnchors 的文字左右与坐标冲突，必须先按坐标修正后再输出，禁止交换两只手、整图镜像或把托腮手与落膝手互换。"
                "如果 bodyOrientation 是三分之二侧身或近侧面，第三句必须同时写出鼻尖朝向、脸部可见比例、近侧肩髋、远侧肩髋遮挡和胸腹侧轮廓，并原样加入‘保持三分之二侧身/近侧面，禁止转成正面’；后文禁止出现正面展示、正对镜头、双肩平行于画面等冲突词。"
                "当 bodyOrientation 写近侧面或躯干偏转达到45度以上时，统一按近侧面执行：胸腹正面可见宽度必须明显压缩，远侧肩髋被近侧身体遮挡，不能降级成轻微三分之二侧身，更不能转成正面。"
                "生成最终 prompt 前必须做手部占用校验：逐只列出画面左侧手和画面右侧手当前唯一动作；同一只手不得同时持手机又抓头发、叉腰、支撑或接触道具。若双手都可见或都已有明确动作，拍摄方式只能写他拍或定时遥控，禁止推断隐藏持机手。"
                "最终 prompt 必须原样写入 limbTopology 的数量与一一对应关系，并明确‘仅一名人物，只有正常两条手臂和两只手；只生成参考图可见的手；禁止额外手臂、手腕、掌心或手指簇’。若参考图双手共同承担一个道具，必须分别写清两只手的唯一接触区域和承重职责，不得增生第三只手，也不得将其中一只手改成悬空或垂落。"
                "手部动作还必须通过物理可达性校验：每只手只能有一个连续的手腕、掌心和五指，手腕到掌心到指尖的连接顺序自然，所有接触点必须能由同一只手在关节可达范围内完成。若手指细枝与关键接触点冲突，保留关键接触点并简化非关键手指，禁止增生、折断、穿插或反关节。"
                "若 captureType=selfie_phone_out_of_frame，必须明确写成单手臂长自拍：镜头位于伸向画外的持机手前方，保留高机位俯拍、近侧肩臂的透视放大和脸/躯干向画面远处收缩；手机虽不入画，成图仍必须肉眼看出自拍视角，禁止改成第三方在人物正前方拍摄。"
                "必须把 forbiddenPoseFallback 压缩成一句直接放在动作关键帧之后，明确禁止最容易发生的默认姿势及正确落点；例如双腿原本并排横向伸出画面时，必须直接禁止一腿朝镜头抬起、屈膝竖起或双腿落地，而不是只重复‘保持姿势’。"
                "必须逐段原样写入 poseSurfaceGeometry 中的二维肢体轨迹：肩到肘到手、髋到膝到踝到脚尖分别朝画面左上、左下、右上、右下、近水平或近垂直的方向和约角度，以及各终点位于身体轴线哪一侧；两腿或双臂的交叉、重叠、前后层级和间距不得省略。只写‘向前、向下、自然伸展’不合格。还必须保留臀、背、脚和支撑手相对承载面的压靠、悬空、垂下、落地与遮挡关系；不得把斜向画面一侧伸展的双腿改成垂直下落，不得把腿从台面上移到地面，也不得把悬空或垂下的腿放到台面上。"
                "动作信息进入最终 prompt 时必须按景别排序：全身、近全身或坐姿先写臀部承重和髋-膝-踝-脚尖轨迹，再写手指细节；近景和胸像先写手腕-掌心-手指的具体接触点与肘部方位。不得因为文本压缩而删掉当前景别最能决定姿势的这类证据。"
                "姿态类别必须作为最终 prompt 的明确硬约束写出：站立、坐姿、跪姿、蹲姿或躺姿不得互换；坐姿要写清臀部与承载面的接触、承重点和腿部弯曲，不能仅写‘在某处’。"
                "locomotionGeometry 非空时，动作句必须逐字保留行进方向、领先腿/滞后腿、两脚与不同台阶的接触和重心所在腿，并明确是迈步中的动态关键帧；动作真实度优先于商品正面展示，侧身行走、上楼或下楼不得转成正面静止站姿。"
                "头部角度必须使用参考分析给出的有限范围，避免‘极度后仰’等夸张措辞；同时明确该角度下哪些五官仍完整可见。"
                "面部身份可以改变，但面部可见范围、双眼状态和 mouthMicroExpression 不能改变；可见眼睛必须是完整自然的眼球与眼睑，闭眼必须是完整闭合眼睑，不允许写成或生成缺失、空白或模糊。最终 prompt 必须用一句短句明确嘴部开合、唇间缝隙、露齿露舌状态、画面左右嘴角方向和下颌受力；闭唇不得生成微张嘴或露齿笑，微张嘴不得自动闭合。"
            "最终 prompt 第一句必须直接采用构图硬锁中的人物宽高占比、中心落点、四侧边距和画内身体终点，禁止另写一组矛盾的估算值；若是环境人像、近全身、七分身或全身，第一句必须同时写不是半身照、胸像或人物特写，并明确保留背景负空间。"
            "人物外接框四边都按整图坐标验收，目标误差不超过约4个百分点；不只比较人物高度，还要分别比较最左、最右、最高和最低可见像素及可见身体终点。超出容差时必须调整镜头距离和人物位置，不能用改变姿势、裁掉肢体或减少背景结构来凑比例。"
                "把人物外接框当成100×100画布中的禁止越界区域：若脸、人物或商品细节无法在框内同时完整表达，只能整体缩小人物、后退镜头并先保留背景，禁止放大人物、推进镜头、裁掉背景或把商品展示优先于人物占比。"
                "全身或近全身且参考图可见脚部时，最终 prompt 必须写‘双脚、完整鞋面和接地阴影全部入画，下边缘不得切过脚踝或鞋面’；如果画布不足，只能缩小人物和后退镜头，禁止用裁脚或改成半身解决。"
                "最终 prompt 第二句必须完整采用机位硬锁，至少同时写相机相对人物高度、向下俯拍或向上仰拍的方向与角度、镜头水平偏左或偏右、画面顺逆时针滚转，以及自拍臂长或他拍距离。即使某项接近0度也要明确写出，禁止只写‘手机随拍、正面视角、自然角度’。机位句与构图句同级，后文不得用平视、端正、正面展示等词覆盖它。"
                "构图硬锁提供 topPersonY 时，最终 prompt 第一句必须先写‘画面顶部连续保留约X%场景留白，任何手指、手臂、头发、头部或服饰都不得进入’，再描述人物占比；这里的X只能来自 topPersonY，不能改用头顶位置，也不能被上举手臂覆盖。"
                "构图硬锁含局部尺度锚点时，内部必须用面部、肩部和躯干尺度共同判断镜头距离，但最终 prompt 只写一句简洁且无冲突的整体占比。没有明显伸展四肢时，写‘人物整体高度约占画面X%，顶部保留Y%场景空间’；有上举、平伸、叉开或出画的四肢时，必须把所有可见四肢包含在人物整体内，写‘人物连同伸展四肢在内整体高度约占画面X%，人物最高点位于画面高度Y%，上方Y%只有背景’，并按需补充脸宽或肩宽一个最关键尺度。写出顶部留白后，后文不得再说手指、手臂、头发或头部进入这段顶部区域，也不得把同一部位同时写成完整可见和伸出画外。"
                "如果参动作中的手依赖即将被替换区域上的口袋接触，而新商品没有对应口袋，只保留手臂弯曲方向和手在身体侧面的空间位置，改成自然贴靠、被身体遮挡或放入必要的中性搭配口袋；绝不能给新商品虚构口袋。"
                "必须先从商品主体说明和商品图共同列出本次商品包含的全部单品及各自覆盖区域，再读取 nonTargetWardrobe；该字段只表示未覆盖区域是否存在独立服饰，不含任何参考图旧服饰外观。单件商品只替换重叠区域；商品说明明确为套装或同时列出多件时，所有对应身体区域都是商品覆盖区，必须清空该区域旧结构并逐件换成商品图对应单品。只有商品未覆盖区域才进入搭配兼容判断。"
                "最终 prompt 的末句必须写成‘商品清单：共N件，1.品类与关键结构；若有更多单品则按序继续列出。’，N与商品图和商品主体说明一致；单件商品只列一项，多件组合中的上装、下装、外套或其他单品都要单列，不得把多件合并成泛称穿搭，也不得遗漏任一单品。"
                "替换区域必须按身体区域完整清空参考图旧结构，不得叠加、透出或复原任何旧服饰边缘。nonTargetWardrobe 只能决定未覆盖区域是否需要一件中性、低存在感的连续搭配；最终 prompt 严禁描述或恢复参考图旧服饰的品类、颜色、材质、版型、图案、开口、文字、Logo 或装饰。"
                "先读取 nonTargetWearables，再对商品覆盖区域外的鞋袜、帽子、包袋和首饰逐项判断。与新商品物理兼容且在参考图中可见时，必须保留该字段记录的准确品类、颜色、结构、位置、可见范围和接触，不得擅自改成赤脚、无袜或中性替代款；只有新商品实际遮住该物件，或商品结构与其发生明确物理冲突时才允许删除或简化，并要在 prompt 中点明遮挡或冲突原因。此规则只适用于商品主体覆盖区外的鞋袜和配饰，绝不能恢复参考图旧上衣、裙装、裤装或连衣裙外观，也不能改变人物动作、手与道具接触点、脚部落点、裁切和构图。"
                "如果商品图显示的是覆盖脚踝或接近鞋面的全长长裤，最终 prompt 必须明确裤脚保持商品原长自然垂落，删除参考图袜子；不得卷裤脚、缩短裤长、做束口或堆叠裤脚来露出袜子。"
                "如果当前商品是独立上衣，必须保持清楚的上下身分界，不得延伸成连身单品；未覆盖的下身区域如需补全，只生成无品牌、低存在感且不改变动作、裁切和构图的中性搭配，不得根据参考图恢复其具体品类或外观。"
                "真实感必须写成与参考图一致的物理成像：镜头透视、景深和边缘软硬、自动曝光或白平衡波动、噪点或压缩、轻微运动模糊、高光滚降或溢出、阴影细节、皮肤毛孔、绒毛、局部血色与自然反光；皮肤保持自然半哑光，只在真实受光位置出现有限高光，禁止整脸油亮发黄、蜡像磨皮、过度对称或生成式过锐；禁止用‘高清真实’一句带过，也禁止把人物写成完美商业模特或影棚成片。"
                "如果拍摄模式是日常手机快照，最终 prompt 原样写入‘普通 iPhone 原相机实拍的日常生活快照，画面随性，非摆拍、非精心构图或打光’。只有 captureMode 明确为早期老旧CCD生活抓拍且 ccdEvidence 至少两条时，才原样写入‘早期老旧 CCD 或消费级数码相机的生活抓拍质感’，并只补充证据中实际存在的有限动态范围、高光截断、暗部彩色噪点、低像素压缩、偏硬数码锐化、自动白平衡偏移或直闪衰减；禁止泛用 CCD、复古滤镜或胶片颗粒。如果是暗环境直闪，同时使用分析提供的 iPhone 随手拍直闪语义。禁止加入高清人像、8K、4K、超高清、极致细节、大师杰作、电影级、高级感、完美脸、完美身材或专业级打光。"
                "日常手机快照还必须从 snapshotImperfections 中保留至少两条真实可见的不完美证据；不得把人物改成标准模特展示姿势，不得整理掉背景生活痕迹，不得统一锐化、磨皮、虚化背景或改成商业写真光。"
                "foregroundObjectGeometry 非空时必须放在动作句后立即执行，明确显著物体相对脸部与躯干的尺寸、外接框、遮挡面积和逐手接触；禁止把大型包袋缩成普通小包，也禁止把近镜头手机缩小成贴在脸前的小道具。"
                "参考图中的轮播圆点、导航点、进度条、页码、播放控件、状态栏、应用水印、截图文字、白色画布、边框和上下黑白留边全部忽略，最终 prompt 与成图均不得出现。"
                "外景必须保留真实空气透视、远近对比衰减、天空地面与绿植的不规则色差、同一主光方向下的阴影和环境反射；禁止重复叶片、荧光绿植、青橙调色、虚假大光圈、全画面均匀锐化或人物与背景光线互不相干。"
                + build_face_identity_prompt_rule(face_identity_mode, reference_has_face)
                + reference_frame_lock
                + reference_camera_lock
                + reference_appearance_lock
                + reference_frame_execution
                + reference_color_execution
                + reference_bust_execution
                + f"已去除原商品外观的场景与构图描述：{reference_description}"
                + build_subject_hint_text(subject_hint)
                + f"用户补充要求：{user_prompt}"
                + "输出前自检：构图与人物位置、机位与透视、动作与肢体拓扑、人物状态与表情、嘴部微表情、环境位置与细节、光源方向与颜色、人物受光区域、曝光与全局色彩、真实成像质感、商品替换结构是否都有可执行描述；嘴唇开合、唇间缝隙、露齿露舌、画面左右嘴角方向和下颌受力是否与 mouthMicroExpression 一致；handPositionAudit 的每只手是否按centerX落在正确画面侧且接触动作未互换；limbTopology 与动作接触是否一一对应且不会产生额外肢体；参考图可见脚部且 nonTargetWearables 含鞋袜时是否保留准确鞋袜外观而没有变成赤脚；商品清单点名的每件套装单品是否都已写入且对应覆盖区没有残留旧衣；体型是否只在商品原有连续面料内自然呈现，是否错误地为了突出胸部降低或扩大领口、改成深V、移动肩带、缩窄胸前覆盖、增加露肤、事业线、开口或内衣式结构；全长长裤是否保持原长且没有为旧袜子卷短裤脚；单手自拍是否仍只有一只手持手机；近镜头手机是否保持相对人物的放大与遮挡；三分之二侧身或近侧面是否被正面化；人物是否越过外接框或侵占顶部背景；CCD 是否有至少两条像素证据才启用；不得把完整肩线或袖子改成露肩、吊带或额外内搭；neutralAnchorAudit 是否与综合色一致；天空、水面、地面和建筑等 environmentColorZones 是否逐区保留具体颜色、渐变和反射，黄昏是否仍是同一时间段而未回退成蓝天或阴天；顶部、侧面或背后的局部主光是否以正确颜色真实落在头发、脸、肩颈和服饰对应区域；生活快照是否只保留真实相机或场景不完美而未复制任何轮播圆点、进度条、水印、白边或截图界面；构图、机位、景别、顶部负空间、身体朝向、动作接触、体型置信度、背景主色、皮肤基础色和对比曲线是否均与结构化硬锁一致。"
                + "最终 Prompt 控制在700至900个中文字符。每项约束只写一次，不重复构图硬锁、外观硬锁或同义禁止项；必须用紧凑句式完整覆盖构图、机位、动作、商品结构、场景光色和真实成像，删除低价值背景枚举与通用禁止项。长度略有偏差时也不要补写重复内容。"
                + "只输出 FINAL_PROMPT: 后面接一整段最终画面描述，不要输出分析、清单、Markdown 或 JSON。"
            ),
        },
    ]
    instructions = (
        f"{settings['apparelFinalPrompt']}{APPAREL_PROMPT_GUARDRAILS}{PRODUCT_STRUCTURE_GUARDRAILS}"
        f"{SCENE_REPLICATION_GUARDRAILS}"
        f"{build_face_identity_prompt_rule(face_identity_mode, reference_has_face)}"
        f"{reference_layout_execution}"
        f"{reference_frame_lock}"
        f"{reference_camera_lock}"
        f"{reference_appearance_lock}"
        f"{reference_frame_execution}"
        f"{reference_color_execution}"
        f"{reference_bust_execution}"
        "本次调用中唯一的图像输入是商品图，参考图已被转换成去除原商品外观的文字场景描述。如果前文提到第一张或第二张图，以本句对当前输入的定义为准。"
    )
    text = call_vision_model(
        model=settings["visionModel"],
        instructions=instructions,
        content=content,
        temperature=0,
        max_output_tokens=1200,
        timings=settings.get("timings"),
        timing_label="kimi_apparel_final_prompt",
    )
    prompt = extract_final_prompt_text(text)
    prompt = enforce_apparel_bust_level(prompt, reference_analysis)
    prompt = strip_viewer_artifacts_from_prompt(prompt)
    if not prompt:
        raise RuntimeError("Kimi 未返回可用的最终 Prompt")
    return prompt


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
    official_model = normalize_kimi_model(model)
    payload = {
        "model": official_model,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": openrouter_content(content)},
        ],
        "max_tokens": max_output_tokens,
        "thinking": {"type": "disabled"},
    }
    started_at = time.monotonic()
    data = post_json(
        KIMI_URL,
        payload,
        api_key=KIMI_API_KEY,
        provider_name="Kimi",
    )
    append_timing(timings, timing_label, official_model, started_at)
    return extract_response_text(data), data


def generate_image(prompt, settings, reference_images, localize_output=True):
    if is_dreamina_model(settings.get("model")):
        return generate_image_with_dreamina(prompt, settings, reference_images, localize_output)

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


def is_dreamina_model(model):
    return isinstance(model, str) and model.strip().lower().startswith("dreamina")


def generate_image_with_dreamina(prompt, settings, reference_images, localize_output=True):
    if not os.path.exists(DREAMINA_BIN):
        raise Exception(f"即梦 CLI 未安装或路径不可用：{DREAMINA_BIN}")

    usable_references = [item for item in reference_images if isinstance(item, str) and item]
    if not usable_references:
        raise Exception("即梦 image2image 至少需要一张商品参考图。")

    tmp_dir = tempfile.mkdtemp(prefix="dreamina-")
    try:
        image_paths = [
            write_reference_image_file(item, tmp_dir, index)
            for index, item in enumerate(usable_references)
        ]
        output_dir = os.path.join(tmp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        ratio = resolve_dreamina_ratio(settings.get("imageSize"))
        resolution_type = resolve_dreamina_resolution(settings)
        model_version = resolve_dreamina_model_version(settings)
        poll_seconds = resolve_dreamina_poll_seconds(settings)

        command = [DREAMINA_BIN, "image2image"]
        for image_path in image_paths:
            command.extend(["--images", image_path])
        command.extend(
            [
                "--prompt",
                prompt,
                "--ratio",
                ratio,
                "--resolution_type",
                resolution_type,
                "--model_version",
                model_version,
                "--poll",
                str(poll_seconds),
            ]
        )

        started_at = time.monotonic()
        data = run_dreamina_json(command, timeout=poll_seconds + 60)
        data = wait_for_dreamina_result(data, output_dir, poll_seconds + 420)
        append_timing(settings.get("timings"), "image_generation", settings["model"], started_at)

        image_path = find_dreamina_output_image(data, output_dir)
        if not image_path:
            raise Exception(f"即梦生成成功，但没有找到输出图片：{json.dumps(data, ensure_ascii=False)[:500]}")

        value = store_generated_file(image_path) if localize_output else image_path
        debug = build_dreamina_request_debug(
            settings["model"],
            prompt,
            reference_images,
            ratio,
            resolution_type,
            model_version,
            data,
        )
        return value, debug
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def write_reference_image_file(value, tmp_dir, index):
    raw = b""
    content_type = "image/png"
    if value.startswith("data:"):
        header, separator, encoded = value.partition(",")
        if not separator:
            raise Exception("商品参考图 data URL 格式不正确。")
        content_type = header.split(";", 1)[0].replace("data:", "") or content_type
        raw = base64.b64decode(encoded.encode("ascii"))
    elif value.startswith("http://") or value.startswith("https://"):
        content_type, raw = download_image_bytes(value, "商品参考图")
    elif os.path.exists(value):
        content_type = mimetypes.guess_type(value)[0] or content_type
        with open(value, "rb") as source:
            raw = source.read()
    else:
        raise Exception("商品参考图格式不支持。")

    extension = guess_image_extension(content_type)
    path = os.path.join(tmp_dir, f"reference_{index}{extension}")
    with open(path, "wb") as target:
        target.write(raw)
    return path


def guess_image_extension(content_type):
    if not isinstance(content_type, str):
        return ".png"
    lowered = content_type.split(";", 1)[0].strip().lower()
    if lowered in ("image/jpeg", "image/jpg"):
        return ".jpg"
    if lowered == "image/webp":
        return ".webp"
    if lowered == "image/gif":
        return ".gif"
    return ".png"


def resolve_dreamina_ratio(image_size):
    ratio = parse_ratio_or_dimensions(image_size) if isinstance(image_size, str) else ""
    if ratio in DREAMINA_SUPPORTED_RATIOS:
        return ratio
    return "1:1"


def resolve_dreamina_resolution(settings):
    extra_body = settings.get("extraBody") if isinstance(settings.get("extraBody"), dict) else {}
    value = str(extra_body.get("dreaminaResolutionType") or "").strip().lower()
    if value in ("1.5k", "2k", "4k"):
        return value
    if value == "1k":
        return "1.5k"
    if resolve_dreamina_model_version(settings).lower() == "5.0pro":
        return "1.5k"
    image_size = str(settings.get("imageSize") or "").strip().lower()
    return "4k" if image_size == "4k" else "2k"


def resolve_dreamina_model_version(settings):
    extra_body = settings.get("extraBody") if isinstance(settings.get("extraBody"), dict) else {}
    value = str(extra_body.get("dreaminaModelVersion") or "").strip()
    if value:
        return value
    model = str(settings.get("model") or "")
    for marker in (":", "-", "@"):
        if marker in model:
            candidate = model.rsplit(marker, 1)[-1].strip()
            if candidate.lower() == "5.0pro":
                return "5.0Pro"
            if candidate.replace(".", "", 1).isdigit():
                return candidate
    return "5.0"


def resolve_dreamina_poll_seconds(settings):
    extra_body = settings.get("extraBody") if isinstance(settings.get("extraBody"), dict) else {}
    try:
        value = int(extra_body.get("dreaminaPollSeconds") or 180)
    except (TypeError, ValueError):
        value = 180
    return max(30, min(value, 300))


def run_dreamina_json(command, timeout):
    env = os.environ.copy()
    local_bin = os.path.expanduser("~/.local/bin")
    env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise Exception("即梦 CLI 调用超时，请稍后再试。")

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if result.returncode != 0:
        detail = stderr or stdout or f"exit code {result.returncode}"
        raise Exception(f"即梦 CLI 调用失败：{detail[:800]}")

    data = parse_json_text(stdout)
    if not data:
        raise Exception(f"即梦 CLI 返回无法解析：{(stdout or stderr)[:800]}")
    return data


def dreamina_status(data):
    if not isinstance(data, dict):
        return ""
    candidates = [
        data.get("gen_status"),
        data.get("status"),
        data.get("state"),
        data.get("task_status"),
    ]
    task = data.get("task")
    if isinstance(task, dict):
        candidates.extend([task.get("gen_status"), task.get("status"), task.get("state")])
    for candidate in candidates:
        if candidate is not None and candidate != "":
            return str(candidate).strip().lower()
    return ""


def dreamina_submit_id(data):
    if not isinstance(data, dict):
        return ""
    submit_id = data.get("submit_id") or data.get("submitId")
    task = data.get("task")
    if not submit_id and isinstance(task, dict):
        submit_id = task.get("submit_id") or task.get("submitId")
    return str(submit_id or "")


def dreamina_failure_reason(data):
    if not isinstance(data, dict):
        return ""
    keys = ("fail_reason", "failure_reason", "error", "error_msg", "err_msg", "message", "reason")
    for key in keys:
        value = data.get(key)
        if value:
            return str(value)
    task = data.get("task")
    if isinstance(task, dict):
        for key in keys:
            value = task.get(key)
            if value:
                return str(value)
    return ""


def is_dreamina_success(status):
    return status in ("success", "succeed", "succeeded", "done", "finish", "finished", "45")


def is_dreamina_pending(status):
    return not status or status in (
        "querying",
        "running",
        "processing",
        "pending",
        "queueing",
        "queued",
        "20",
        "30",
        "40",
        "42",
    )


def format_dreamina_failure(data):
    submit_id = dreamina_submit_id(data)
    status = dreamina_status(data) or "unknown"
    reason = dreamina_failure_reason(data) or "任务失败，未返回更具体原因"
    suffix = []
    if submit_id:
        suffix.append(f"submit_id={submit_id}")
    if status:
        suffix.append(f"状态={status}")
    suffix_text = f"（{'，'.join(suffix)}）" if suffix else ""
    return f"即梦生成失败：{reason}{suffix_text}"


def wait_for_dreamina_result(data, output_dir, timeout_seconds):
    status = dreamina_status(data)
    submit_id = dreamina_submit_id(data)
    if is_dreamina_success(status):
        if submit_id:
            return query_dreamina_result(submit_id, output_dir)
        return data
    if not is_dreamina_pending(status):
        raise Exception(format_dreamina_failure(data))
    if not submit_id:
        return data

    deadline = time.monotonic() + timeout_seconds
    last_data = data
    while time.monotonic() < deadline:
        time.sleep(3)
        query_data = query_dreamina_result(submit_id, output_dir)
        last_data = query_data
        status = dreamina_status(query_data)
        if is_dreamina_success(status):
            return query_data
        if not is_dreamina_pending(status):
            raise Exception(format_dreamina_failure(query_data))
    last_status = dreamina_status(last_data) or "unknown"
    raise Exception(f"即梦生成超时，submit_id={submit_id}，最后状态={last_status}。建议稍后重试，或临时切换到 Image2。")


def query_dreamina_result(submit_id, output_dir):
    return run_dreamina_json(
        [
            DREAMINA_BIN,
            "query_result",
            "--submit_id",
            str(submit_id),
            "--download_dir",
            output_dir,
        ],
        timeout=90,
    )


def find_dreamina_output_image(data, output_dir):
    for path in extract_image_paths(data):
        if isinstance(path, str) and os.path.exists(path):
            return path
    for name in os.listdir(output_dir):
        lowered = name.lower()
        if lowered.endswith((".png", ".jpg", ".jpeg", ".webp")):
            return os.path.join(output_dir, name)
    return ""


def extract_image_paths(value):
    paths = []
    if isinstance(value, dict):
        for key, item in value.items():
            lowered_key = str(key).lower()
            if lowered_key in ("path", "local_path", "localpath", "download_path", "downloadpath") and isinstance(item, str):
                paths.append(item)
            else:
                paths.extend(extract_image_paths(item))
    elif isinstance(value, list):
        for item in value:
            paths.extend(extract_image_paths(item))
    return paths


def store_generated_file(path):
    content_type = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as source:
        raw = source.read()
    extension = guess_image_extension(content_type)
    image_id = f"{uuid.uuid4().hex}{extension}"
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


def build_dreamina_request_debug(model, prompt, reference_images, ratio, resolution_type, model_version, response_data):
    return {
        "model": model,
        "provider": "dreamina",
        "ratio": ratio,
        "resolutionType": resolution_type,
        "modelVersion": model_version,
        "referenceImageCount": len(
            [item for item in reference_images if isinstance(item, str) and item]
        ),
        "referenceImages": [
            summarize_reference_image(item)
            for item in reference_images
            if isinstance(item, str) and item
        ],
        "prompt": prompt,
        "response": response_data,
    }


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
    if generation_path in {"apparel", "non_apparel"}:
        return [
            {
                "title": "分析参考图",
                "detail": "读取参考图的场景、构图、动作和光线。",
            },
            {
                "title": "生成 Prompt",
                "detail": "将画面描述与商品约束整理成生图 Prompt。",
            },
            {
                "title": "生成图片",
                "detail": "调用生图模型生成结果。",
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


def build_canny_composition_guide(reference_data_url):
    if not isinstance(reference_data_url, str) or not reference_data_url.startswith("data:"):
        raise Exception("参考图格式不正确，无法生成构图边缘稿。")
    _, separator, encoded = reference_data_url.partition(",")
    if not separator:
        raise Exception("参考图 data URL 格式不正确，无法生成构图边缘稿。")
    try:
        raw = base64.b64decode(encoded.encode("ascii"))
    except Exception as error:
        raise Exception("参考图解码失败，无法生成构图边缘稿。") from error

    ffmpeg_bin = shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")
    if not ffmpeg_bin or not ffprobe_bin:
        raise Exception("本地 Canny 处理需要 ffmpeg，但当前未找到可执行文件。")
    tmp_dir = tempfile.mkdtemp(prefix="aic-canny-")
    try:
        source_path = os.path.join(tmp_dir, "source-image")
        edge_path = os.path.join(tmp_dir, "composition-guide.png")
        with open(source_path, "wb") as handle:
            handle.write(raw)

        probe = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "json",
                source_path,
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if probe.returncode != 0:
            raise Exception(probe.stderr.strip() or "无法读取参考图尺寸。")
        streams = json.loads(probe.stdout or "{}").get("streams") or []
        if not streams:
            raise Exception("无法读取参考图尺寸。")
        width = int(streams[0].get("width") or 0)
        height = int(streams[0].get("height") or 0)
        if width <= 0 or height <= 0:
            raise Exception("参考图尺寸无效。")

        scale = min(1.0, CANNY_MAX_SIDE / max(width, height))
        target_width = max(1, int(round(width * scale)))
        target_height = max(1, int(round(height * scale)))
        low = CANNY_LOW_THRESHOLD / 255.0
        high = CANNY_HIGH_THRESHOLD / 255.0
        video_filter = (
            f"scale={target_width}:{target_height}:flags=lanczos,"
            f"format=gray,edgedetect=low={low:.6f}:high={high:.6f}:mode=wires:planes=y,negate"
        )
        process = subprocess.run(
            [
                ffmpeg_bin,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                source_path,
                "-vf",
                video_filter,
                "-frames:v",
                "1",
                edge_path,
            ],
            capture_output=True,
            text=True,
            timeout=40,
            check=False,
        )
        if process.returncode != 0 or not os.path.exists(edge_path):
            raise Exception(process.stderr.strip() or "Canny 边缘稿生成失败。")
        with open(edge_path, "rb") as handle:
            edge_raw = handle.read()
        return f"data:image/png;base64,{base64.b64encode(edge_raw).decode('ascii')}"
    except Exception as error:
        raise Exception(f"本地构图边缘稿生成失败：{error}") from error
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def first_existing_path(candidates):
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return ""


def resolve_depth_runtime():
    configured_python = os.environ.get("AIC_DEPTH_PYTHON", "").strip()
    configured_model = os.environ.get("AIC_DEPTH_MODEL", "").strip()
    python_bin = first_existing_path(
        [
            configured_python,
            os.path.join(PROJECT_ROOT, "server", ".depth-runtime", "bin", "python"),
            os.path.join(
                PROJECT_ROOT,
                "evaluation",
                "depth-parameter-lab",
                ".runtime",
                "bin",
                "python",
            ),
        ]
    )
    model_path = first_existing_path(
        [
            configured_model,
            os.path.join(PROJECT_ROOT, "server", "models", "depth_anything_v2_vits.onnx"),
            os.path.join(
                PROJECT_ROOT,
                "evaluation",
                "depth-parameter-lab",
                ".cache",
                "depth_anything_v2_vits.onnx",
            ),
        ]
    )
    if not python_bin or not model_path:
        raise Exception(
            "本地深度图组件未安装。请配置 AIC_DEPTH_PYTHON 与 AIC_DEPTH_MODEL 后重启后端。"
        )
    return python_bin, model_path


def build_depth_composition_guide(reference_data_url):
    if not isinstance(reference_data_url, str) or not reference_data_url.startswith("data:"):
        raise Exception("参考图格式不正确，无法生成构图深度图。")
    _, separator, encoded = reference_data_url.partition(",")
    if not separator:
        raise Exception("参考图 data URL 格式不正确，无法生成构图深度图。")
    try:
        raw = base64.b64decode(encoded.encode("ascii"))
    except Exception as error:
        raise Exception("参考图解码失败，无法生成构图深度图。") from error

    python_bin, model_path = resolve_depth_runtime()
    tmp_dir = tempfile.mkdtemp(prefix="aic-depth-")
    try:
        source_path = os.path.join(tmp_dir, "source-image")
        depth_path = os.path.join(tmp_dir, "composition-guide.png")
        with open(source_path, "wb") as handle:
            handle.write(raw)
        process = subprocess.run(
            [
                python_bin,
                DEPTH_GUIDE_SCRIPT,
                "--model",
                model_path,
                "--input",
                source_path,
                "--output",
                depth_path,
                "--structure",
                str(DEPTH_GUIDE_STRUCTURE),
                "--detail",
                str(DEPTH_GUIDE_DETAIL),
                "--smoothing",
                str(DEPTH_GUIDE_SMOOTHING),
                "--contrast",
                str(DEPTH_GUIDE_CONTRAST),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if process.returncode != 0 or not os.path.exists(depth_path):
            detail = process.stderr.strip() or process.stdout.strip() or "深度图生成失败。"
            raise Exception(detail)
        with open(depth_path, "rb") as handle:
            depth_raw = handle.read()
        return f"data:image/png;base64,{base64.b64encode(depth_raw).decode('ascii')}"
    except Exception as error:
        raise Exception(f"本地构图深度图生成失败：{error}") from error
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def build_generation_reference_images(product_data_urls, settings):
    references = [item for item in product_data_urls if isinstance(item, str) and item]
    composition_guide = settings.get("compositionGuideDataUrl")
    if not isinstance(composition_guide, str) or not composition_guide.startswith("data:"):
        raise Exception("构图引导图未生成，无法开始生图。")
    return references + [composition_guide]


def build_composition_guide_rule(product_count, guide_type="canny"):
    if product_count == 1:
        product_scope = "参考图1是商品素材图"
    else:
        product_scope = f"参考图1至参考图{product_count}是用户分别上传的商品素材图"
    guide_index = product_count + 1
    if guide_type == "depth":
        return (
            f" 参考图输入顺序：{product_scope}，是商品品类、件数、结构、颜色、纹理、长度和品牌标识的唯一真值；"
            f"参考图{guide_index}是从场景原图提取的灰度相对深度图，浅色表示更靠近镜头、深色表示更远，"
            "只用于辅助还原前后空间层次、主体位置与占比、四边裁切、留白和主要场景体块，不是商品图，也不提供颜色、材质或人物身份。"
            "人物动作、手势、表情、身体朝向和接触关系以最终文字 prompt 为准；用户补充要求改变动作、删除物体或更换角色时，"
            "该文字要求优先，必须忽略深度图中与之冲突的旧人物或物体体块。"
            "禁止把深度图的灰度、旧衣体积、原人物面貌或模糊边缘生成到最终画面中，也不得让它覆盖商品素材图的真实结构。"
        )
    return (
        f" 参考图输入顺序：{product_scope}，是商品品类、件数、结构、颜色、纹理、长度和品牌标识的唯一真值；"
        f"参考图{guide_index}是从场景原图生成的黑线白底 Canny 构图稿，只用于辅助还原画幅、主体位置与占比、"
        "四边裁切、留白、主要道具落点和场景大结构，不是商品图，也不锁定人物姿势。"
        "人物动作、手势、表情、身体朝向和接触关系以最终文字 prompt 为准；用户补充要求改变动作、删除物体或更换角色时，"
        "该文字要求优先，必须忽略 Canny 构图稿中与之冲突的肢体、物体或人物轮廓。"
        "Canny 构图稿中的白底、黑线、旧衣轮廓、面部线条、文字和残余纹理都不是最终成图内容，"
        "禁止生成线稿效果、旧衣或原人物身份，也不得让它覆盖商品素材图的真实结构。"
    )


def convert_image_url_to_data_url(image_url):
    if isinstance(image_url, str) and image_url.startswith("data:"):
        return normalize_data_url(image_url)
    content_type, raw = download_image_bytes(image_url, "参考图")

    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def download_image_bytes(image_url, label, max_attempts=3):
    last_error = None
    for attempt in range(max_attempts):
        request = Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(request, timeout=60) as response:
                content_type = response.headers.get("Content-Type", "image/png")
                return content_type, response.read()
        except HTTPError as error:
            if error.code < 500 or attempt == max_attempts - 1:
                raise Exception(f"下载{label}失败 ({error.code})")
            last_error = error
        except (URLError, ConnectionResetError, TimeoutError, RemoteDisconnected, IncompleteRead) as error:
            last_error = error
        if attempt < max_attempts - 1:
            time.sleep(1.2 * (attempt + 1))
    raise Exception(f"下载{label}时网络中断，请稍后重试。") from last_error


def post_json(url, payload, api_key=None, provider_name="OpenRouter"):
    raw_body = json.dumps(payload).encode("utf-8")
    last_error = None
    max_attempts = 6 if provider_name == "Kimi" else 3
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key or OPENROUTER_API_KEY}",
    }
    if provider_name == "OpenRouter":
        headers.update(
            {
                "HTTP-Referer": "http://127.0.0.1:8787",
                "X-Title": "Commerce Creative Replicator",
            }
        )
    for attempt in range(max_attempts):
        request = Request(
            url,
            data=raw_body,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            text = error.read().decode("utf-8", errors="ignore")
            if provider_name == "Kimi" and error.code == 429 and attempt < max_attempts - 1:
                retry_after = error.headers.get("Retry-After", "")
                try:
                    delay = max(1.0, float(retry_after))
                except (TypeError, ValueError):
                    delay = 1.5
                time.sleep(delay + (0.25 * attempt))
                continue
            raise Exception(format_provider_error(provider_name, error.code, text))
        except (IncompleteRead, RemoteDisconnected, TimeoutError) as error:
            last_error = error
        except URLError as error:
            last_error = error
        if attempt < max_attempts - 1:
            time.sleep(1.5 * (attempt + 1))
    raise Exception(format_transient_provider_error(provider_name, last_error))


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
    found_marker = False
    for marker in markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[1].strip()
            found_marker = True
            break

    if not found_marker and any(
        marker in cleaned
        for marker in ("<|tool_calls_section_begin|>", "<|tool_call_begin|>", "internally_analyze")
    ):
        return ""

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


def normalize_kimi_model(model):
    value = str(model or "").strip()
    if value.startswith("moonshotai/"):
        value = value.split("/", 1)[1]
    return value or "kimi-k2.6"


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


def normalize_face_identity_mode(value):
    if isinstance(value, str) and value.strip().lower() == "preserve_reference":
        return "preserve_reference"
    return "regenerate"


def build_face_identity_prompt_rule(face_identity_mode, reference_has_face):
    if face_identity_mode == "preserve_reference":
        return (
            "当前选择保留原图人脸。最终 prompt 应保留第一张参考图模特的人脸、发型、妆容、表情和脸部遮挡关系，"
            "但不得引入第二张商品图中的人脸、发型或人物形象。"
        )
    if not reference_has_face:
        return (
            "参考图中没有足够清晰、可用于继承身份的人脸。严格保持参考图原本的脸部可见范围和四边裁切："
            "如果脸部完全在画外就不得生成脸部，如果只露局部就只保留同样的局部，如果脸部可见但过小或模糊就生成新人脸但不改变其大小和清晰度层级。"
            "不得为了展示新人脸而拉远镜头、下移人物、缩小主体或补出头顶上方空间。"
        )
    return (
        "本次人脸规则优先级最高，覆盖前文任何‘沿用参考图人脸’或‘保留人物形象’的旧要求。"
        "当前选择不保留人脸信息。最终 prompt 必须明确是一名全新模特，其人脸与第一张参考图和第二张商品图中的人脸都不同。"
            "只沿用参考图的脸部可见状态、头部角度、视线方向、表情强度、嘴唇开合与嘴角受力状态、发型轮廓与遮挡关系，"
        "不得描述或还原原图的脸型、眼型、鼻唇、五官比例、妆容特征和人物辨识度。"
        "换脸只改变身份特征，不得改变参考图可见肤色、肩宽、胸腰比例、躯干厚度、四肢粗细和整体体型轮廓。"
    )


def strip_code_fences(text):
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def parse_partial_top_level_json(text):
    """Recover complete top-level values when a long model response is truncated."""
    decoder = json.JSONDecoder()
    recovered = {}
    for key in (
        "hasFace",
        "reason",
        "layoutLock",
        "frameLock",
        "cameraLock",
        "appearanceLock",
        "personDescription",
        "poseDescription",
        "sceneDescription",
        "cameraDescription",
        "colorDescription",
    ):
        match = re.search(rf'"{re.escape(key)}"\s*:\s*', text)
        if not match:
            continue
        try:
            value, _ = decoder.raw_decode(text, match.end())
        except (json.JSONDecodeError, TypeError):
            continue
        recovered[key] = value
    return recovered


def parse_json_text(text):
    cleaned = strip_code_fences(text)
    if not cleaned:
        return {}
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # The CLI occasionally writes SQL timing logs before the real JSON. Scan
    # every object boundary and keep the last complete object instead of
    # letting an earlier escaped JSON fragment consume the whole output.
    decoder = json.JSONDecoder()
    candidates = []
    for match in re.finditer(r"\{", cleaned):
        try:
            value, _ = decoder.raw_decode(cleaned, match.start())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(value)
    if candidates:
        return candidates[-1]

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass
    return parse_partial_top_level_json(cleaned)


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


def format_provider_error(provider_name, status_code, text):
    if provider_name == "OpenRouter":
        return format_openrouter_error(status_code, text)
    detail = text[:800]
    try:
        parsed = json.loads(text)
        error_payload = parsed.get("error", {}) if isinstance(parsed, dict) else {}
        message = error_payload.get("message") if isinstance(error_payload, dict) else ""
        code = error_payload.get("code") if isinstance(error_payload, dict) else ""
        if message:
            detail = f"{code}: {message}" if code else message
    except Exception:
        pass
    return f"{provider_name} 请求失败 ({status_code})：{detail}"


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


def format_transient_provider_error(provider_name, error):
    if provider_name == "OpenRouter":
        return format_transient_openrouter_error(error)
    if isinstance(error, IncompleteRead):
        return (
            f"{provider_name} 响应读取中断，已自动重试但仍未完成。"
            f"最后一次只读取到 {len(error.partial or b'')} bytes。请稍后再试。"
        )
    if isinstance(error, URLError):
        return f"{provider_name} 网络连接不稳定，已自动重试但仍失败：{error.reason}"
    if error:
        return f"{provider_name} 网络连接不稳定，已自动重试但仍失败：{error}"
    return f"{provider_name} 网络连接不稳定，已自动重试但仍失败。"


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
    face_identity_mode="regenerate",
):
    portrait_text = build_face_identity_prompt_rule(face_identity_mode, reference_has_face)
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
