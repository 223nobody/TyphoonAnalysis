"""
定时任务调度器 - 自动爬取台风数据
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.typhoon import Typhoon, CrawlerLog
from app.services.crawler.cma_crawler import cma_crawler

logger = logging.getLogger(__name__)

# 创建调度器实例
scheduler = AsyncIOScheduler()


async def fetch_and_update_typhoons():
    """
    定时爬取任务：获取活跃台风并更新数据库
    """
    logger.info("=" * 60)
    logger.info("开始执行定时爬取任务")
    logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            # 1. 爬取活跃台风列表
            logger.info("正在爬取活跃台风列表...")
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
            
            logger.info(f"成功获取 {len(typhoons)} 个活跃台风")
            
            # 2. 获取数据库中所有台风的ID
            query = select(Typhoon.typhoon_id)
            result = await db.execute(query)
            existing_ids = set(result.scalars().all())
            
            logger.info(f"数据库中现有 {len(existing_ids)} 个台风记录")
            
            # 3. 处理爬取到的台风数据
            new_count = 0
            updated_count = 0

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
                        status_text = "active" if typhoon_status == 1 else "stop"
                        logger.info(f"  更新台风状态: {typhoon_data['typhoon_name_cn']} ({typhoon_id}) -> {status_text}")
                else:
                    # 新台风，插入数据库
                    new_typhoon = Typhoon(**typhoon_data)
                    db.add(new_typhoon)
                    new_count += 1
                    logger.info(f"  新增台风: {typhoon_data['typhoon_name_cn']} ({typhoon_id})")
            
            # 4. 提交更改
            await db.commit()
            
            # 5. 记录成功日志
            log = CrawlerLog(
                task_type="scheduled_fetch",
                status="success",
                message=f"成功爬取 {len(typhoons)} 个台风，新增 {new_count} 个，更新 {updated_count} 个",
                data_count=len(typhoons)
            )
            db.add(log)
            await db.commit()
            
            logger.info("-" * 60)
            logger.info(f"✅ 爬取任务完成")
            logger.info(f"   总计: {len(typhoons)} 个台风")
            logger.info(f"   新增: {new_count} 个")
            logger.info(f"   更新: {updated_count} 个")
            logger.info("=" * 60)
            
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
    
    logger.info("=" * 60)
    logger.info("初始化定时任务调度器")
    logger.info(f"爬取间隔: {settings.CRAWLER_INTERVAL_HOURS} 小时")
    logger.info(f"启动时执行: {settings.CRAWLER_START_ON_STARTUP}")
    logger.info("=" * 60)
    
    # 添加定时任务
    scheduler.add_job(
        fetch_and_update_typhoons,
        trigger=IntervalTrigger(hours=settings.CRAWLER_INTERVAL_HOURS),
        id="typhoon_crawler",
        name="台风数据定时爬取",
        replace_existing=True
    )
    
    # 启动调度器
    scheduler.start()
    logger.info("✅ 定时任务调度器已启动")
    
    # 如果配置了启动时执行，则立即执行一次
    if settings.CRAWLER_START_ON_STARTUP:
        logger.info("配置了启动时执行，将在5秒后执行首次爬取...")
        scheduler.add_job(
            fetch_and_update_typhoons,
            trigger='date',
            run_date=datetime.now(),
            id="startup_crawler",
            name="启动时爬取",
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

