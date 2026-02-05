"""
定时任务调度器 - 自动爬取台风数据
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.services.scheduler.crawler_executor import (
    run_all_crawlers,
    run_typhoons_crawler,
    run_active_typhoon_crawler
)

logger = logging.getLogger(__name__)

# 创建调度器实例
scheduler = AsyncIOScheduler()


def start_scheduler():
    """
    启动定时任务调度器
    """
    if not settings.CRAWLER_ENABLED:
        logger.info("定时爬取功能已禁用（CRAWLER_ENABLED=False）")
        return

    # 添加定时任务：台风基本信息爬取
    scheduler.add_job(
        run_typhoons_crawler,
        trigger=IntervalTrigger(minutes=settings.CRAWLER_INTERVAL_MINUTES),
        id="typhoons_crawler",
        name="台风基本信息定时爬取",
        replace_existing=True
    )

    # 添加定时任务：活跃台风路径数据爬取
    scheduler.add_job(
        run_active_typhoon_crawler,
        trigger=IntervalTrigger(minutes=10),
        id="active_typhoon_crawler",
        name="活跃台风路径定时爬取",
        replace_existing=True
    )

    # 启动调度器
    scheduler.start()
    logger.info(f"定时任务调度器已启动 | 台风爬取间隔:{settings.CRAWLER_INTERVAL_MINUTES}分钟 | 活跃台风爬取间隔:10分钟")

    # 如果配置了启动时执行，则立即执行一次完整爬取
    if settings.CRAWLER_START_ON_STARTUP:
        logger.info("启动时执行完整爬取任务...")
        scheduler.add_job(
            run_all_crawlers,
            trigger='date',
            run_date=datetime.now(),
            id="startup_full_crawl",
            name="启动时完整爬取",
            replace_existing=True
        )
        logger.info("已添加启动时完整爬取任务")


def shutdown_scheduler():
    """
    关闭定时任务调度器
    """
    if scheduler.running:
        logger.info("正在关闭定时任务调度器...")
        scheduler.shutdown(wait=True)
        logger.info("✅ 定时任务调度器已关闭")

