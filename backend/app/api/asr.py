"""
ASR 语音识别 API 路由
集成 Qwen3-ASR 模型到 FastAPI
支持本地模型部署
"""
import os
import tempfile
import torch
import re
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import opencc
from pathlib import Path


# 中文数字转阿拉伯数字的映射
CN_NUMBERS = {
    '零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    '百': 100, '千': 1000, '万': 10000, '亿': 100000000
}


def chinese_to_number(cn_str):
    """
    将中文数字字符串转换为阿拉伯数字
    例如："二零零零" -> 2000, "一百二十三" -> 123
    """
    if not cn_str:
        return None
    
    # 处理纯单个数字的情况（如"二"）
    if len(cn_str) == 1 and cn_str in CN_NUMBERS:
        return CN_NUMBERS[cn_str]
    
    # 处理年份格式（如"二零零零"）- 纯数字字符序列
    if all(c in '零〇一二三四五六七八九' for c in cn_str):
        result = ''
        for c in cn_str:
            if c in CN_NUMBERS:
                result += str(CN_NUMBERS[c])
        return int(result) if result else None
    
    # 处理复杂数字（如"一百二十三"）
    # 使用更简单的算法：从左到右解析
    result = 0
    current_section = 0  # 当前段（万以下）
    current_num = 0  # 当前数字
    
    for i, char in enumerate(cn_str):
        if char not in CN_NUMBERS:
            continue
        
        digit = CN_NUMBERS[char]
        
        if digit >= 10:  # 是单位（十、百、千、万、亿）
            if current_num == 0:
                current_num = 1  # 处理"十"、"百"前面没有数字的情况
            
            if digit >= 10000:  # 万、亿
                current_section += current_num
                result += current_section * digit
                current_section = 0
                current_num = 0
            else:  # 十、百、千
                current_section += current_num * digit
                current_num = 0
        else:  # 是数字
            current_num = current_num * 10 + digit if current_num > 0 else digit
    
    # 加上最后剩余的数字
    result += current_section + current_num
    
    return result if result > 0 else None


def convert_chinese_numbers_in_text(text):
    """
    在文本中查找并转换中文数字为阿拉伯数字
    例如："二零零零年有哪些台风？" -> "2000年有哪些台风？"
    """
    if not text:
        return text
    
    # 匹配中文数字序列（包括零一二三四五六七八九十百千万亿两〇）
    # 优先匹配年份格式（连续的数字字符）
    year_pattern = r'[零〇一二三四五六七八九]{2,}'
    
    def replace_year(match):
        cn_num = match.group()
        try:
            num = chinese_to_number(cn_num)
            if num is not None:
                return str(num)
        except:
            pass
        return cn_num
    
    # 先转换年份格式的数字
    text = re.sub(year_pattern, replace_year, text)
    
    # 匹配复杂中文数字（如"一百二十三"）
    # 匹配模式：数字+单位+数字... 或 单位+数字...
    complex_pattern = r'(?:[一二两三四五六七八九]?[十百千万亿])+[一二两三四五六七八九]?|[一二两三四五六七八九][十百千万亿]'
    
    def replace_complex(match):
        cn_num = match.group()
        # 避免重复转换已经转换过的数字
        if cn_num.isdigit():
            return cn_num
        try:
            num = chinese_to_number(cn_num)
            if num is not None:
                return str(num)
        except:
            pass
        return cn_num
    
    text = re.sub(complex_pattern, replace_complex, text)
    
    # 匹配单个中文数字（如"第三号"中的"三"）
    # 使用负向前瞻和负向后瞻，避免重复替换已经转换过的数字
    single_pattern = r'(?<![零〇一二两三四五六七八九])[一二两三四五六七八九](?![零〇一二两三四五六七八九])'
    
    def replace_single(match):
        cn_num = match.group()
        try:
            num = chinese_to_number(cn_num)
            if num is not None and num < 10:  # 只转换个位数
                return str(num)
        except:
            pass
        return cn_num
    
    text = re.sub(single_pattern, replace_single, text)
    
    return text

logger = logging.getLogger(__name__)

# 创建繁体转简体转换器
converter = opencc.OpenCC('t2s')  # 繁体转简体

router = APIRouter(prefix="/asr", tags=["语音识别"])

# 全局 ASR 模型实例
asr_model = None

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'ogg', 'webm'}

# 默认本地模型路径
DEFAULT_LOCAL_MODEL_PATH = Path(__file__).parent.parent.parent / "data" / "asr_model" / "Qwen3-ASR-0.6B"


def get_model_path():
    """
    获取模型路径
    优先级：1. 环境变量 QWEN_ASR_MODEL_PATH > 2. 默认本地路径 > 3. HuggingFace Hub
    """
    # 1. 检查环境变量
    env_path = os.environ.get('QWEN_ASR_MODEL_PATH')
    if env_path and os.path.exists(env_path):
        logger.info(f"使用环境变量指定的模型路径: {env_path}")
        return env_path
    
    # 2. 检查默认本地路径
    if DEFAULT_LOCAL_MODEL_PATH.exists():
        logger.info(f"使用本地模型: {DEFAULT_LOCAL_MODEL_PATH}")
        return str(DEFAULT_LOCAL_MODEL_PATH)
    
    # 3. 使用 HuggingFace Hub
    logger.info("本地模型不存在，将从 HuggingFace Hub 加载")
    return "Qwen/Qwen3-ASR-0.6B"


def setup_hf_mirror():
    """配置 HuggingFace 国内镜像（仅在从 Hub 下载时需要）"""
    if not os.environ.get('HF_ENDPOINT'):
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        logger.info(f"设置 HuggingFace 镜像: {os.environ['HF_ENDPOINT']}")
    else:
        logger.info(f"使用已配置的 HuggingFace 镜像: {os.environ.get('HF_ENDPOINT')}")


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_asr_model():
    """懒加载 ASR 模型"""
    global asr_model
    if asr_model is None:
        logger.info("正在加载 Qwen3-ASR 模型...")
        try:
            from qwen_asr import Qwen3ASRModel

            # 检测 GPU 可用性
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"使用设备: {device}")

            # 获取模型路径
            model_path = get_model_path()
            
            # 如果是 HuggingFace Hub 路径，设置镜像
            if model_path == "Qwen/Qwen3-ASR-0.6B":
                setup_hf_mirror()
                logger.info("使用 Qwen3-ASR-0.6B 模型 (从 HuggingFace Hub 加载)")
            else:
                logger.info(f"使用本地部署的 Qwen3-ASR-0.6B 模型: {model_path}")

            asr_model = Qwen3ASRModel.from_pretrained(
                model_path,
                dtype=torch.bfloat16 if device == "cuda" else torch.float32,
                device_map=device,
                max_inference_batch_size=1,
                max_new_tokens=256,
            )

            logger.info("Qwen3-ASR 模型加载完成")
        except Exception as e:
            logger.error(f"模型加载失败: {str(e)}")
            raise

    return asr_model


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(..., description="音频文件"),
    language: str = Form(None, description="语言代码 (如 'zh', 'en', 'yue')，不传则自动检测")
):
    """
    语音识别接口

    - **audio**: 音频文件 (支持 wav, mp3, flac, m4a, ogg, webm)
    - **language**: 语言代码 (可选, 如 'zh', 'en', 'yue')，不传则自动检测
    """
    start_time = datetime.now()

    # 检查文件扩展名
    if not allowed_file(audio.filename):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式，请上传: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 处理语言参数
    if language == 'auto':
        language = None

    # 保存临时文件
    temp_path = os.path.join(
        tempfile.gettempdir(),
        f"asr_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{audio.filename}"
    )

    try:
        # 保存上传的文件
        content = await audio.read()
        with open(temp_path, "wb") as f:
            f.write(content)
        logger.info(f"音频文件已保存: {temp_path}")

        # 加载模型并识别
        model = get_asr_model()

        logger.info(f"开始识别，语言: {language or '自动检测'}")
        results = model.transcribe(
            audio=temp_path,
            language=language,
        )

        # 获取结果
        result = results[0]
        text = result.text
        detected_language = result.language if hasattr(result, 'language') else 'unknown'
        duration = result.duration if hasattr(result, 'duration') else 0

        # 繁体转简体
        text_simplified = converter.convert(text)
        if text != text_simplified:
            logger.info(f"文本已转换: '{text}' -> '{text_simplified}'")
            text = text_simplified

        # 中文数字转阿拉伯数字
        text_with_numbers = convert_chinese_numbers_in_text(text)
        if text != text_with_numbers:
            logger.info(f"数字已转换: '{text}' -> '{text_with_numbers}'")
            text = text_with_numbers

        processing_time = (datetime.now() - start_time).total_seconds()

        logger.info(f"识别完成，耗时: {processing_time:.2f}s，文本长度: {len(text)}")

        return {
            "success": True,
            "text": text,
            "language": detected_language,
            "duration": duration,
            "processing_time": processing_time
        }

    except Exception as e:
        logger.error(f"识别失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")

    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logger.info(f"临时文件已清理: {temp_path}")


@router.get("/health")
async def health_check():
    """ASR 服务健康检查"""
    return {
        "status": "healthy",
        "model_loaded": asr_model is not None,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
    }


@router.get("/languages")
async def get_supported_languages():
    """获取支持的语言列表"""
    languages = {
        "auto": "自动检测",
        "zh": "中文(普通话)",
        "en": "英语",
        "yue": "粤语",
        "ja": "日语",
        "ko": "韩语",
        "fr": "法语",
        "de": "德语",
        "es": "西班牙语",
        "it": "意大利语",
        "pt": "葡萄牙语",
        "ru": "俄语",
        "ar": "阿拉伯语",
        "th": "泰语",
        "vi": "越南语",
        "id": "印尼语",
    }
    return {
        "success": True,
        "languages": languages
    }