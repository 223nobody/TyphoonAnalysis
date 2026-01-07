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
from app.api import typhoon, prediction, analysis, report, crawler
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

    # 启动定时任务调度器
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
    lifespan=lifespan
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


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "台风分析系统API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
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

