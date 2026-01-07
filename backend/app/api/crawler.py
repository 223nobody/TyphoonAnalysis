"""
爬虫API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.typhoon import Typhoon, TyphoonPath, CrawlerLog
from app.services.crawler.cma_crawler import cma_crawler

router = APIRouter(prefix="/crawler", tags=["爬虫"])


@router.post("/fetch-active-typhoons")
async def fetch_active_typhoons(db: AsyncSession = Depends(get_db)):
    """
    爬取当前活跃的台风列表
    
    从中国气象局台风网获取当前活跃的台风信息
    
    Returns:
        dict: 爬取结果统计
    """
    try:
        # 爬取台风列表
        typhoons = await cma_crawler.get_active_typhoons()
        
        saved_count = 0
        updated_count = 0
        
        for typhoon_data in typhoons:
            # 检查是否已存在
            query = select(Typhoon).where(
                Typhoon.typhoon_id == typhoon_data["typhoon_id"]
            )
            result = await db.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                # 更新状态
                existing.status = typhoon_data["status"]
                updated_count += 1
            else:
                # 创建新记录
                db_typhoon = Typhoon(**typhoon_data)
                db.add(db_typhoon)
                saved_count += 1
        
        await db.commit()
        
        # 记录日志
        log = CrawlerLog(
            task_type="fetch_active_typhoons",
            status="success",
            message=f"成功爬取 {len(typhoons)} 个台风",
            data_count=len(typhoons)
        )
        db.add(log)
        await db.commit()
        
        return {
            "success": True,
            "total": len(typhoons),
            "saved": saved_count,
            "updated": updated_count
        }
        
    except Exception as e:
        # 记录错误日志
        log = CrawlerLog(
            task_type="fetch_active_typhoons",
            status="failed",
            message="爬取失败",
            error_message=str(e)
        )
        db.add(log)
        await db.commit()
        
        raise HTTPException(status_code=500, detail=f"爬取失败: {str(e)}")


@router.post("/fetch-typhoon-path/{typhoon_id}")
async def fetch_typhoon_path(
    typhoon_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    爬取指定台风的路径数据
    
    Args:
        typhoon_id: 台风编号
        
    Returns:
        dict: 爬取结果统计
    """
    try:
        # 爬取路径数据
        paths = await cma_crawler.get_typhoon_path(typhoon_id)
        
        if not paths:
            raise HTTPException(status_code=404, detail="未找到路径数据")
        
        # 保存到数据库
        saved_count = 0
        for path_data in paths:
            db_path = TyphoonPath(**path_data)
            db.add(db_path)
            saved_count += 1
        
        await db.commit()
        
        # 记录日志
        log = CrawlerLog(
            task_type="fetch_typhoon_path",
            status="success",
            message=f"成功爬取台风 {typhoon_id} 的路径数据",
            data_count=len(paths)
        )
        db.add(log)
        await db.commit()
        
        return {
            "success": True,
            "typhoon_id": typhoon_id,
            "path_count": len(paths),
            "saved": saved_count
        }
        
    except Exception as e:
        # 记录错误日志
        log = CrawlerLog(
            task_type="fetch_typhoon_path",
            status="failed",
            message=f"爬取台风 {typhoon_id} 路径失败",
            error_message=str(e)
        )
        db.add(log)
        await db.commit()
        
        raise HTTPException(status_code=500, detail=f"爬取失败: {str(e)}")


@router.get("/logs")
async def get_crawler_logs(
    limit: int = Query(default=50, ge=1, le=100, description="返回的日志数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取爬虫日志

    Args:
        limit: 返回的日志数量，默认50条，最多100条

    Returns:
        list: 爬虫日志列表
    """
    try:
        # 查询最近的日志
        query = select(CrawlerLog).order_by(CrawlerLog.created_at.desc()).limit(limit)
        result = await db.execute(query)
        logs = result.scalars().all()

        # 转换为字典列表
        log_list = []
        for log in logs:
            log_list.append({
                "id": log.id,
                "task_type": log.task_type,
                "status": log.status,
                "message": log.message,
                "data_count": log.data_count,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None
            })

        return log_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")


@router.get("/status")
async def get_crawler_status(db: AsyncSession = Depends(get_db)):
    """
    获取爬虫状态

    Returns:
        dict: 爬虫状态信息
    """
    try:
        # 获取最近一条日志
        query = select(CrawlerLog).order_by(CrawlerLog.created_at.desc()).limit(1)
        result = await db.execute(query)
        latest_log = result.scalar_one_or_none()

        if not latest_log:
            return {
                "status": "idle",
                "message": "暂无爬虫记录"
            }

        return {
            "status": latest_log.status,
            "task_type": latest_log.task_type,
            "message": latest_log.message,
            "data_count": latest_log.data_count,
            "error_message": latest_log.error_message,
            "created_at": latest_log.created_at.isoformat() if latest_log.created_at else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")