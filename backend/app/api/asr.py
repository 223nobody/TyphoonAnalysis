"""
ASR 语音识别 API 路由
集成 Qwen3-ASR 模型到 FastAPI
"""
import os
import tempfile
import torch
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import opencc

logger = logging.getLogger(__name__)

# 创建繁体转简体转换器
converter = opencc.OpenCC('t2s')  # 繁体转简体

router = APIRouter(prefix="/asr", tags=["语音识别"])

# 全局 ASR 模型实例
asr_model = None

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'ogg', 'webm'}

# 设置 HuggingFace 镜像源（国内加速）
def setup_hf_mirror():
    """配置 HuggingFace 国内镜像"""
    # 优先使用环境变量设置的镜像
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
            # 设置国内镜像
            setup_hf_mirror()

            from qwen_asr import Qwen3ASRModel

            # 检测 GPU 可用性
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"使用设备: {device}")

            # 使用 0.6B 模型以适配 4GB 显存
            logger.info("使用 Qwen3-ASR-0.6B 模型 (适合 4GB 显存)")
            asr_model = Qwen3ASRModel.from_pretrained(
                "Qwen/Qwen3-ASR-0.6B",
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
