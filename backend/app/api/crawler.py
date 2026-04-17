"""
爬虫 API 路由。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.typhoon import CrawlerLog, TyphoonPath
from app.services.crawler.cma_crawler import cma_crawler
from app.services.scheduler.crawler_executor import (
    fetch_active_typhoon_task,
    run_typhoons_crawler_by_year,
)

router = APIRouter(prefix="/crawler", tags=["爬虫"])


@router.post("/fetch-active-typhoons")
async def fetch_active_typhoons(db: AsyncSession = Depends(get_db)):
    """
    同步当前年份台风基础信息，并刷新活跃台风实时路径和预测路径。
    """
    year = datetime.now().year
    try:
        await run_typhoons_crawler_by_year(year)
        forecast_result = await fetch_active_typhoon_task()

        return {
            "success": True,
            "year": year,
            "message": "当前年份台风与活跃预报同步完成",
            "forecast": forecast_result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/sync-year/{year}")
async def sync_typhoons_by_year(year: int):
    """手动补抓指定年份台风。"""
    try:
        await run_typhoons_crawler_by_year(year)
        return {"success": True, "year": year}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/fetch-typhoon-path/{typhoon_id}")
async def fetch_typhoon_path(
    typhoon_id: str,
    db: AsyncSession = Depends(get_db)
):
    """手动补抓单个台风路径数据。"""
    try:
        paths = await cma_crawler.get_typhoon_path(typhoon_id)
        if not paths:
            raise HTTPException(status_code=404, detail="未找到路径数据")

        saved_count = 0
        updated_count = 0
        for path_data in paths:
            existing_query = select(TyphoonPath).where(
                TyphoonPath.typhoon_id == path_data["typhoon_id"],
                TyphoonPath.timestamp == path_data["timestamp"],
            )
            existing_result = await db.execute(existing_query)
            existing = existing_result.scalar_one_or_none()

            if existing:
                existing.latitude = float(path_data["latitude"])
                existing.longitude = float(path_data["longitude"])
                existing.center_pressure = path_data.get("center_pressure")
                existing.max_wind_speed = path_data.get("max_wind_speed")
                existing.moving_speed = path_data.get("moving_speed")
                existing.moving_direction = path_data.get("moving_direction")
                existing.intensity = path_data.get("intensity")
                updated_count += 1
            else:
                db.add(TyphoonPath(**path_data))
                saved_count += 1

        await db.commit()
        return {
            "success": True,
            "typhoon_id": typhoon_id,
            "path_count": len(paths),
            "saved": saved_count,
            "updated": updated_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"抓取失败: {str(e)}")


@router.get("/logs")
async def get_crawler_logs(
    limit: int = Query(default=50, ge=1, le=100, description="返回的日志数量"),
    db: AsyncSession = Depends(get_db)
):
    """获取最近的爬虫日志。"""
    try:
        query = select(CrawlerLog).order_by(CrawlerLog.created_at.desc()).limit(limit)
        result = await db.execute(query)
        logs = result.scalars().all()

        return [
            {
                "id": log.id,
                "task_type": log.task_type,
                "status": log.status,
                "message": log.message,
                "data_count": log.data_count,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")


@router.get("/status")
async def get_crawler_status(db: AsyncSession = Depends(get_db)):
    """获取最近一次爬虫状态。"""
    try:
        query = select(CrawlerLog).order_by(CrawlerLog.created_at.desc()).limit(1)
        result = await db.execute(query)
        latest_log = result.scalar_one_or_none()

        if not latest_log:
            return {"status": "idle", "message": "暂无爬虫记录"}

        return {
            "status": latest_log.status,
            "task_type": latest_log.task_type,
            "message": latest_log.message,
            "data_count": latest_log.data_count,
            "error_message": latest_log.error_message,
            "created_at": latest_log.created_at.isoformat() if latest_log.created_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")
