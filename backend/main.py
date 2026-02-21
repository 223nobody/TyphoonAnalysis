"""
FastAPI主应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from loguru import logger

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api import typhoon, prediction, analysis, report, crawler, statistics, export, alert, ai_agent, auth, user_stats, asr
from app.api.v1 import images, video_analysis
from app.services.scheduler import start_scheduler, shutdown_scheduler


# 配置日志
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("正在启动台风分析系统...")

    # 初始化数据库
    await init_db()
    logger.info("数据库初始化完成")

    # 检查 ASR 配置
    logger.info("正在检查 ASR 语音识别配置...")
    try:
        from app.core.config import settings
        if settings.NLS_APPKEY:
            logger.info("阿里云 NLS 语音识别配置已设置")
        else:
            logger.warning("阿里云 NLS AppKey 未配置，语音识别功能将不可用")
    except Exception as e:
        logger.warning(f"ASR 配置检查失败: {e}")

    # 启动定时任务调度器（会自动执行启动时完整爬取）
    start_scheduler()

    logger.info(f"应用启动成功，监听 {settings.HOST}:{settings.PORT}")

    yield

    # 关闭时执行
    logger.info("正在关闭应用...")

    # 关闭定时任务调度器
    shutdown_scheduler()

    # 关闭数据库连接
    await close_db()

    logger.info("应用已关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于FastAPI + AI大模型的智能台风分析系统",
    lifespan=lifespan,
    # 配置 Swagger UI 使用国内可访问的 CDN
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai",
        "tryItOutEnabled": True,
    },
)

# 配置CORS - 允许所有来源（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=False,  # 当allow_origins为*时，必须设置为False
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
    expose_headers=["*"],  # 暴露所有响应头
)


# 注册路由
app.include_router(typhoon.router, prefix="/api")
app.include_router(prediction.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(crawler.router, prefix="/api")
app.include_router(statistics.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(alert.router, prefix="/api")
app.include_router(ai_agent.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(user_stats.router, prefix="/api")
app.include_router(asr.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(video_analysis.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "台风分析系统API",
        "version": settings.APP_VERSION,
        "description": "基于FastAPI + AI大模型的智能台风分析系统",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """健康检查 - 返回服务状态和版本信息"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": "台风分析系统API"
    }
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

