"""
应用配置模块
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置类"""

    # 应用基础配置
    APP_NAME: str = "台风分析系统"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SECRET_KEY: str = Field(..., min_length=32)

    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./typhoon_analysis.db"

    # AI服务提供商选择
    AI_PROVIDER: str = Field(default="", description="AI服务提供商，可选值: qwen, deepseek, glm")

    # 统一AI API配置（aiping.cn）
    AI_API_KEY: str = Field(..., description="统一AI API密钥（用于DeepSeek、Qwen和GLM）")
    AI_API_BASE_URL: str = Field(default="https://aiping.cn/api/v1", description="统一AI API基础URL")

    # AI模型名称配置
    DEEPSEEK_MODEL: str = Field(default="", description="DeepSeek模型名称")
    QWEN_TEXT_MODEL: str = Field(default="", description="Qwen文本生成模型")
    QWEN_VL_MODEL: str = Field(default="", description="Qwen视觉理解模型")
    GLM_MODEL: str = Field(default="", description="GLM模型名称")

    # AI通用配置
    AI_TIMEOUT: int = 120  # 增加超时时间以支持更长内容生成
    AI_MAX_TOKENS: int = 3000

    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://localhost:5173",
    ]

    # CMA爬虫配置
    CMA_BASE_URL: str = "https://typhoon.nmc.cn"
    CMA_TYPHOON_LIST_URL: str = "https://typhoon.nmc.cn/weatherservice/typhoon/jsons"
    CRAWLER_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # 定时爬取配置
    CRAWLER_ENABLED: bool = True  # 是否启用自动爬取
    CRAWLER_INTERVAL_MINUTES: int = 10  # 爬取间隔时间（分钟）
    CRAWLER_START_ON_STARTUP: bool = True  # 是否在项目启动时立即执行一次爬取

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # 数据存储路径
    DATA_DIR: str = "./data"
    IMAGES_DIR: str = "./data/images"
    MODELS_DIR: str = "./data/models"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()


