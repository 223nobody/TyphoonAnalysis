"""
定时任务调度器 - 自动爬取台风数据
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.typhoon import Typhoon, TyphoonPath, CrawlerLog
from app.services.crawler.cma_crawler import cma_crawler
from app.services.scheduler.active_typhoon_task import fetch_active_typhoon_task

logger = logging.getLogger(__name__)

# 创建调度器实例
scheduler = AsyncIOScheduler()


async def fetch_and_update_typhoons():
    """
    定时爬取任务：获取活跃台风并更新数据库
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. 爬取活跃台风列表
            typhoons = await cma_crawler.get_active_typhoons()

            if not typhoons:
                logger.warning("未获取到活跃台风数据")
                # 记录日志
                log = CrawlerLog(
                    task_type="scheduled_fetch",
                    status="success",
                    message="未获取到活跃台风",
                    data_count=0
                )
                db.add(log)
                await db.commit()
                return

            # 2. 获取数据库中所有台风的ID
            query = select(Typhoon.typhoon_id)
            result = await db.execute(query)
            existing_ids = set(result.scalars().all())

            # 3. 处理爬取到的台风数据
            new_count = 0
            updated_count = 0
            new_typhoon_ids = []  # 记录新插入的台风ID，用于后续爬取路径

            for typhoon_data in typhoons:
                typhoon_id = typhoon_data["typhoon_id"]
                typhoon_status = typhoon_data["status"]  # 获取爬虫返回的状态值

                if typhoon_id in existing_ids:
                    # 台风已存在，更新status
                    query = select(Typhoon).where(Typhoon.typhoon_id == typhoon_id)
                    result = await db.execute(query)
                    existing = result.scalar_one_or_none()

                    if existing and existing.status != typhoon_status:
                        existing.status = typhoon_status
                        updated_count += 1
                else:
                    # 新台风，插入数据库
                    new_typhoon = Typhoon(**typhoon_data)
                    db.add(new_typhoon)
                    new_count += 1
                    new_typhoon_ids.append(typhoon_id)

            # 4. 提交台风基本信息的更改
            await db.commit()

            # 5. 爬取新台风的路径数据
            path_count = 0
            if new_typhoon_ids:
                for typhoon_id in new_typhoon_ids:
                    try:
                        paths = await cma_crawler.get_typhoon_path(typhoon_id)

                        if not paths:
                            logger.warning(f"台风 {typhoon_id} 没有路径数据")
                            continue

                        # 插入路径数据到数据库
                        inserted_count = 0
                        skipped_count = 0

                        for path_data in paths:
                            try:
                                # 检查路径点是否已存在（避免重复插入）
                                existing_path_query = select(TyphoonPath).where(
                                    TyphoonPath.typhoon_id == path_data["typhoon_id"],
                                    TyphoonPath.timestamp == path_data["timestamp"]
                                )
                                existing_path_result = await db.execute(existing_path_query)
                                existing_path = existing_path_result.scalar_one_or_none()

                                if existing_path:
                                    skipped_count += 1
                                    continue

                                # 创建路径对象并插入
                                new_path = TyphoonPath(**path_data)
                                db.add(new_path)
                                inserted_count += 1
                                path_count += 1

                            except Exception as path_error:
                                logger.error(f"插入路径点失败: {path_error}")
                                continue

                    except Exception as e:
                        logger.error(f"爬取台风 {typhoon_id} 路径数据失败: {e}")
                        continue

                # 提交路径数据
                try:
                    await db.commit()
                except Exception as commit_error:
                    logger.error(f"提交路径数据失败: {commit_error}")
                    await db.rollback()
                    path_count = 0

            # 6. 记录成功日志
            log = CrawlerLog(
                task_type="scheduled_fetch",
                status="success",
                message=f"成功爬取 {len(typhoons)} 个台风，新增 {new_count} 个，更新 {updated_count} 个，插入 {path_count} 个路径点",
                data_count=len(typhoons)
            )
            db.add(log)
            await db.commit()

        except Exception as e:
            logger.error(f"❌ 定时爬取任务失败: {e}", exc_info=True)

            # 记录错误日志
            try:
                log = CrawlerLog(
                    task_type="scheduled_fetch",
                    status="failed",
                    message="定时爬取失败",
                    error_message=str(e)
                )
                db.add(log)
                await db.commit()
            except Exception as log_error:
                logger.error(f"记录错误日志失败: {log_error}")


def start_scheduler():
    """
    启动定时任务调度器
    """
    if not settings.CRAWLER_ENABLED:
        logger.info("定时爬取功能已禁用（CRAWLER_ENABLED=False）")
        return

    # 添加定时任务：台风基本信息爬取
    scheduler.add_job(
        fetch_and_update_typhoons,
        trigger=IntervalTrigger(minutes=settings.CRAWLER_INTERVAL_MINUTES),
        id="typhoon_crawler",
        name="台风数据定时爬取",
        replace_existing=True
    )

    # 添加定时任务：活跃台风数据爬取（每10分钟执行一次）
    scheduler.add_job(
        fetch_active_typhoon_task,
        trigger=IntervalTrigger(minutes=10),
        id="active_typhoon_crawler",
        name="活跃台风数据定时爬取",
        replace_existing=True
    )

    # 启动调度器
    scheduler.start()
    logger.info("✅ 定时任务调度器已启动")

    # 如果配置了启动时执行，则立即执行一次
    if settings.CRAWLER_START_ON_STARTUP:
        scheduler.add_job(
            fetch_and_update_typhoons,
            trigger='date',
            run_date=datetime.now(),
            id="startup_crawler",
            name="启动时爬取",
            replace_existing=True
        )

        # 启动时也执行一次活跃台风爬取
        scheduler.add_job(
            fetch_active_typhoon_task,
            trigger='date',
            run_date=datetime.now(),
            id="startup_active_typhoon_crawler",
            name="启动时活跃台风爬取",
            replace_existing=True
        )


def shutdown_scheduler():
    """
    关闭定时任务调度器
    """
    if scheduler.running:
        logger.info("正在关闭定时任务调度器...")
        scheduler.shutdown(wait=True)
        logger.info("✅ 定时任务调度器已关闭")

