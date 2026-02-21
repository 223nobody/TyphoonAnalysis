"""
ASR 语音识别 API 路由
集成阿里云 NLS (智能语音交互) API
支持实时语音识别
"""
import os
import tempfile
import json
import time
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from datetime import datetime
import logging
import opencc

from app.core.config import settings

logger = logging.getLogger(__name__)

# 创建繁体转简体转换器
converter = opencc.OpenCC('t2s')

router = APIRouter(prefix="/asr", tags=["语音识别"])

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'pcm', 'm4a', 'ogg', 'webm'}


def get_nls_token():
    """获取阿里云 NLS Token"""
    try:
        from nls.token import getToken
        
        access_key_id = settings.NLS_ACCESS_KEY_ID or settings.OSS_ACCESS_KEY_ID
        access_key_secret = settings.NLS_ACCESS_KEY_SECRET or settings.OSS_ACCESS_KEY_SECRET
        
        if not access_key_id or not access_key_secret:
            raise ValueError("阿里云 AccessKey 未配置")
        
        return getToken(access_key_id, access_key_secret)
    except Exception as e:
        logger.error(f"获取 NLS Token 失败: {str(e)}")
        raise


class AliyunASR:
    """阿里云 NLS 语音识别封装类"""
    
    def __init__(self):
        self.appkey = settings.NLS_APPKEY
        self.url = settings.NLS_URL
        self.token = None
        self.result_text = ""
        self.is_completed = False
        self.error_message = None
    
    def on_start(self, message, *args):
        """识别开始回调"""
        try:
            msg_json = json.loads(message)
            if 'header' in msg_json:
                status = msg_json['header'].get('status', 0)
                if status != 20000000:
                    status_text = msg_json['header'].get('status_text', '')
                    logger.error(f"语音识别启动异常: [{status}] {status_text}")
                    self.error_message = f"[{status}] {status_text}"
        except Exception:
            pass
    
    def on_sentence_end(self, message, *args):
        """句子结束识别回调 - 保存完整的句子结果"""
        try:
            result = json.loads(message)
            if 'payload' in result:
                payload = result['payload']
                if 'result' in payload:
                    self.result_text = payload['result']
        except Exception:
            pass
    
    def on_completed(self, message, *args):
        """识别完成回调"""
        self.is_completed = True
    
    def on_error(self, message, *args):
        """错误回调"""
        try:
            error_json = json.loads(message)
            if 'header' in error_json:
                status_text = error_json['header'].get('status_text', '')
                status = error_json['header'].get('status', '')
                self.error_message = f"[{status}] {status_text}"
            else:
                self.error_message = message
        except:
            self.error_message = message
    
    def recognize(self, audio_path: str, audio_format: str = "pcm", sample_rate: int = 16000) -> str:
        """识别音频文件"""
        from nls import NlsSpeechTranscriber
        
        self.token = get_nls_token()
        
        sr = NlsSpeechTranscriber(
            url=self.url,
            token=self.token,
            appkey=self.appkey,
            on_start=self.on_start,
            on_sentence_end=self.on_sentence_end,
            on_completed=self.on_completed,
            on_error=self.on_error
        )
        
        try:
            sr.start(
                aformat=audio_format,
                sample_rate=sample_rate,
                enable_intermediate_result=False,
                enable_punctuation_prediction=True,
                enable_inverse_text_normalization=True,
                timeout=10
            )
        except Exception as e:
            error_detail = self.error_message if self.error_message else str(e)
            raise Exception(f"语音识别启动失败: {error_detail}")
        
        try:
            # 使用更大的块大小提高速度
            chunk_size = 3200
            
            with open(audio_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    sr.send_audio(chunk)
                    time.sleep(0.01)
            
            # 等待数据被处理
            time.sleep(0.5)
            
            sr.stop(timeout=30)
            
            # 等待识别完成
            wait_time = 0
            while not self.is_completed and wait_time < 30:
                time.sleep(0.1)
                wait_time += 0.1
            
            if not self.is_completed:
                raise Exception("语音识别超时")
            
            return self.result_text
            
        except Exception as e:
            raise


def convert_to_pcm(input_path: str, output_path: str) -> tuple:
    """将音频文件转换为 PCM 格式"""
    try:
        from pydub import AudioSegment
        
        ext = input_path.lower().split('.')[-1]
        
        if ext == 'wav':
            audio = AudioSegment.from_wav(input_path)
        elif ext == 'mp3':
            audio = AudioSegment.from_mp3(input_path)
        elif ext in ['m4a', 'mp4']:
            audio = AudioSegment.from_file(input_path, format='mp4')
        elif ext == 'ogg':
            audio = AudioSegment.from_ogg(input_path)
        elif ext == 'flac':
            audio = AudioSegment.from_file(input_path, format='flac')
        elif ext == 'webm':
            audio = AudioSegment.from_file(input_path, format='webm')
        else:
            audio = AudioSegment.from_file(input_path)
        
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(16000)
        audio = audio.set_sample_width(2)
        audio.export(output_path, format='raw')
        
        return output_path, 16000
        
    except ImportError:
        raise Exception("pydub 未安装，请运行: pip install pydub")
    except Exception as e:
        raise Exception(f"音频格式转换失败: {str(e)}")


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(..., description="音频文件"),
    language: str = Form(None, description="语言代码")
):
    """语音识别接口"""
    start_time = datetime.now()

    ext = audio.filename.lower().rsplit('.', 1)[-1] if '.' in audio.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式，请上传: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    temp_path = os.path.join(
        tempfile.gettempdir(),
        f"asr_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{audio.filename}"
    )
    pcm_path = temp_path + ".pcm"

    try:
        content = await audio.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        pcm_path, sample_rate = convert_to_pcm(temp_path, pcm_path)

        asr = AliyunASR()
        text = asr.recognize(pcm_path, audio_format="pcm", sample_rate=sample_rate)

        text = converter.convert(text)

        processing_time = (datetime.now() - start_time).total_seconds()

        return {
            "success": True,
            "text": text,
            "language": language or "auto",
            "processing_time": processing_time
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")

    finally:
        for path in [temp_path, pcm_path]:
            if os.path.exists(path):
                os.remove(path)


@router.get("/health")
async def health_check():
    """ASR 服务健康检查"""
    config_complete = bool(
        settings.NLS_APPKEY and 
        (settings.NLS_ACCESS_KEY_ID or settings.OSS_ACCESS_KEY_ID) and
        (settings.NLS_ACCESS_KEY_SECRET or settings.OSS_ACCESS_KEY_SECRET)
    )
    
    return {
        "status": "healthy" if config_complete else "config_incomplete",
        "service": "阿里云NLS语音识别",
        "config_complete": config_complete
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
