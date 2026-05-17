"""
应用配置模块
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


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

    # Qwen/GLM 通用AI API配置（aiping.cn）
    AI_API_KEY: str = Field(..., description="通用AI API密钥（用于Qwen和GLM）")
    AI_API_BASE_URL: str = Field(default="https://aiping.cn/api/v1", description="通用AI API基础URL")

    # DeepSeek 专用 API 配置
    DEEPSEEK_API_KEY: str = Field(default="", description="DeepSeek专用API密钥")
    DEEPSEEK_API_BASE_URL: str = Field(default="", description="DeepSeek专用API基础URL")

    # 深度思考模式兼容配置（未配置 DeepSeek 专用配置时使用）
    AI_API_KEY_THINKING: str = Field(default="", description="深度思考模式兼容API密钥")
    AI_API_BASE_URL_THINKING: str = Field(default="", description="深度思考模式兼容API基础URL")

    # 视觉语言模型专用配置
    AI_API_KEY_VL: str = Field(default="", description="视觉语言模型专用API密钥（用于视频/图像分析）")
    AI_API_BASE_URL_VL: str = Field(default="https://dashscope.aliyuncs.com/api/v1", description="视觉语言模型API基础URL")

    # AI模型名称配置
    DEEPSEEK_MODEL: str = Field(default="", description="DeepSeek模型名称（非深度思考模式）")
    DEEPSEEK_MODEL_THINKING: str = Field(default="", description="DeepSeek模型名称（深度思考模式）")
    QWEN_TEXT_MODEL: str = Field(default="", description="Qwen文本生成模型")
    QWEN_VL_MODEL: str = Field(default="qwen-vl-max-latest", description="Qwen视觉语言模型")
    GLM_MODEL: str = Field(default="", description="GLM模型名称")

    # AI调用性能与输出质量配置
    AI_REPORT_MAX_TOKENS: int = Field(default=4096, description="报告生成最大输出Token数")
    AI_REPORT_TIMEOUT: float = Field(default=150.0, description="报告生成请求超时秒数")
    AI_REPORT_MAX_RETRIES: int = Field(default=2, description="报告生成最大重试次数")
    AI_REPORT_RETRY_DELAY: float = Field(default=1.5, description="报告生成重试基础等待秒数")
    AI_REPORT_TEMPERATURE: float = Field(default=0.45, description="报告生成采样温度")
    AI_REPORT_TOP_P: float = Field(default=0.9, description="报告生成top_p")

    AI_CHAT_SIMPLE_MAX_TOKENS: int = Field(default=2400, description="AI客服简单问题最大输出Token数")
    AI_CHAT_COMPLEX_MAX_TOKENS: int = Field(default=4096, description="AI客服复杂问题最大输出Token数")
    AI_CHAT_THINKING_MAX_TOKENS: int = Field(default=6144, description="AI客服深度思考最大输出Token数")
    AI_CHAT_TIMEOUT: float = Field(default=75.0, description="AI客服普通请求超时秒数")
    AI_CHAT_THINKING_TIMEOUT: float = Field(default=180.0, description="AI客服深度思考请求超时秒数")
    AI_CHAT_TEMPERATURE: float = Field(default=0.65, description="AI客服采样温度")
    AI_CHAT_TOP_P: float = Field(default=0.9, description="AI客服top_p")
    AI_CHAT_PRESENCE_PENALTY: float = Field(default=0.05, description="AI客服存在惩罚")
    AI_CHAT_FREQUENCY_PENALTY: float = Field(default=0.1, description="AI客服频率惩罚")

    AI_VL_IMAGE_MAX_TOKENS: int = Field(default=2400, description="图像视觉分析最大输出Token数")
    AI_VL_IMAGE_TIMEOUT: float = Field(default=160.0, description="图像视觉分析请求超时秒数")
    AI_VL_IMAGE_MAX_RETRIES: int = Field(default=2, description="图像视觉分析最大重试次数")
    AI_VL_IMAGE_TEMPERATURE: float = Field(default=0.2, description="图像视觉分析采样温度")
    AI_VL_VIDEO_MAX_TOKENS: int = Field(default=2400, description="视频视觉分析最大输出Token数")
    AI_VL_VIDEO_FRAME_MAX_TOKENS: int = Field(default=1200, description="视频单帧分析最大输出Token数")
    AI_VL_VIDEO_TIMEOUT: float = Field(default=240.0, description="视频视觉分析请求超时秒数")
    AI_VL_VIDEO_MAX_RETRIES: int = Field(default=2, description="视频视觉分析最大重试次数")
    AI_VL_VIDEO_TEMPERATURE: float = Field(default=0.55, description="视频视觉分析采样温度")
    AI_VL_RETRY_DELAY: float = Field(default=1.5, description="视觉分析重试基础等待秒数")


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

    # Neo4j 图数据库配置
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j Bolt连接URI")
    NEO4J_USER: str = Field(default="neo4j", description="Neo4j用户名")
    NEO4J_PASSWORD: str = Field(default="password", description="Neo4j密码")
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = Field(default=50, description="Neo4j连接池大小")
    NEO4J_CONNECTION_TIMEOUT: int = Field(default=30, description="Neo4j连接超时(秒)")

    # 知识图谱配置
    KG_BATCH_SIZE: int = Field(default=500, description="知识图谱批量导入批次大小")
    KG_SIMILARITY_THRESHOLD: float = Field(default=0.7, description="台风相似度阈值")
    KG_MAX_PATH_DEPTH: int = Field(default=3, description="关系查询最大深度")

    # 阿里云OSS配置
    OSS_ACCESS_KEY_ID: str = Field(default="", description="阿里云OSS AccessKey ID")
    OSS_ACCESS_KEY_SECRET: str = Field(default="", description="阿里云OSS AccessKey Secret")
    OSS_BUCKET_NAME: str = Field(default="", description="阿里云OSS Bucket名称")
    OSS_REGION: str = Field(default="", description="阿里云OSS Region（如：oss-cn-wuhan）")
    OSS_ENDPOINT: str = Field(default="", description="阿里云OSS Endpoint（如：oss-cn-wuhan-lr.aliyuncs.com）")

    QWEN_ASR_MODEL_PATH: str = Field(default="", description="本地Qwen ASR模型路径，为空则使用默认路径")

    # 阿里云 NLS 语音识别配置
    NLS_APPKEY: str = Field(default="", description="阿里云NLS语音服务AppKey")
    NLS_ACCESS_KEY_ID: str = Field(default="", description="阿里云NLS语音服务AccessKey ID")
    NLS_ACCESS_KEY_SECRET: str = Field(default="", description="阿里云NLS语音服务AccessKey Secret")

    @field_validator("DEBUG", "CRAWLER_ENABLED", "CRAWLER_START_ON_STARTUP", mode="before")
    @classmethod
    def parse_bool_like_values(cls, value):
        if isinstance(value, bool):
            return value

        if value is None:
            return False

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "n", "off", "release", "prod", "production"}:
                return False

        return value

    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()


