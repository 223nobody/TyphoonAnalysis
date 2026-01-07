"""
AI服务模块
提供DeepSeek、Qwen和GLM三种AI服务
"""
from app.services.ai.deepseek_service import DeepSeekService, deepseek_service
from app.services.ai.qwen_service import QwenService, qwen_service
from app.services.ai.glm_service import GlmService, glm_service

__all__ = [
    "DeepSeekService",
    "deepseek_service",
    "QwenService",
    "qwen_service",
    "GlmService",
    "glm_service",
]
