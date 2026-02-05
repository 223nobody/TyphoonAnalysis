"""
用户统计相关API
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.typhoon import QueryHistory, CollectTyphoon, Report

router = APIRouter(prefix="/user-stats", tags=["用户统计"])
logger = logging.getLogger(__name__)


@router.get("/overview")
async def get_user_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户统计概览：查询次数、收藏台风数、生成报告数"""
    try:
        # 1. 查询总次数
        query_result = await db.execute(
            select(func.count(QueryHistory.id))
            .where(QueryHistory.user_id == current_user.id)
        )
        query_count = query_result.scalar() or 0

        # 2. 收藏台风数
        collect_result = await db.execute(
            select(func.count(CollectTyphoon.id))
            .where(CollectTyphoon.user_id == current_user.id)
        )
        collect_count = collect_result.scalar() or 0

        # 3. 生成报告数
        report_result = await db.execute(
            select(func.count(Report.id))
            .where(Report.user_id == current_user.id)
        )
        report_count = report_result.scalar() or 0

        return {
            "query_count": query_count,
            "collect_count": collect_count,
            "report_count": report_count
        }
    except Exception as e:
        logger.error(f"获取用户统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/query-history")
async def add_query_history(
    typhoon_id: str = Body(..., embed=True, description="台风编号"),
    typhoon_name: str = Body("", embed=True, description="台风名称"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """记录用户查询台风路径的历史"""
    try:
        query_history = QueryHistory(
            user_id=current_user.id,
            typhoon_id=typhoon_id,
            typhoon_name=typhoon_name,
            query_date=datetime.now()
        )
        db.add(query_history)
        await db.commit()

        logger.info(f"用户 {current_user.username} 查询台风 {typhoon_id}")
        return {"success": True, "message": "查询记录已保存"}
    except Exception as e:
        await db.rollback()
        logger.error(f"记录查询历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"记录查询历史失败: {str(e)}")


@router.get("/query-history/by-count")
async def get_query_history_by_count(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户的查询历史，按查询次数降序排列"""
    try:
        query = select(
            QueryHistory.typhoon_id,
            QueryHistory.typhoon_name,
            func.count(QueryHistory.id).label('query_count'),
            func.max(QueryHistory.id).label('id'),
            func.max(QueryHistory.query_date).label('created_at')
        ).where(
            QueryHistory.user_id == current_user.id
        ).group_by(
            QueryHistory.typhoon_id,
            QueryHistory.typhoon_name
        ).order_by(
            func.count(QueryHistory.id).desc()
        ).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        items = [
            {
                "id": row.id,
                "typhoon_id": row.typhoon_id,
                "typhoon_name": row.typhoon_name,
                "query_count": row.query_count,
                "created_at": row.created_at.isoformat() if row.created_at else None
            }
            for row in rows
        ]

        return items
    except Exception as e:
        logger.error(f"获取查询历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取查询历史失败: {str(e)}")


@router.get("/collect-typhoons")
async def get_collect_typhoons(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户收藏的台风列表"""
    try:
        query = select(CollectTyphoon).where(
            CollectTyphoon.user_id == current_user.id
        ).order_by(CollectTyphoon.id.desc())

        result = await db.execute(query)
        favorites = result.scalars().all()

        # 转换为字典列表
        items = [
            {
                "id": f.id,
                "user_id": f.user_id,
                "typhoon_id": f.typhoon_id,
                "typhoon_name": f.typhoon_name
            }
            for f in favorites
        ]

        return items
    except Exception as e:
        logger.error(f"获取收藏列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取收藏列表失败: {str(e)}")


@router.post("/collect-typhoons")
async def add_collect_typhoon(
    typhoon_id: str = Body(..., embed=True, description="台风编号"),
    typhoon_name: str = Body("", embed=True, description="台风名称"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """收藏台风"""
    try:
        # 检查是否已收藏
        query = select(CollectTyphoon).where(
            CollectTyphoon.user_id == current_user.id,
            CollectTyphoon.typhoon_id == typhoon_id
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(status_code=400, detail="已收藏该台风")

        collect = CollectTyphoon(
            user_id=current_user.id,
            typhoon_id=typhoon_id,
            typhoon_name=typhoon_name
        )
        db.add(collect)
        await db.commit()

        logger.info(f"用户 {current_user.username} 收藏台风 {typhoon_id}")
        return {"success": True, "message": "收藏成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"收藏台风失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"收藏失败: {str(e)}")


@router.delete("/collect-typhoons/{typhoon_id}")
async def remove_collect_typhoon(
    typhoon_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """取消收藏台风"""
    try:
        query = select(CollectTyphoon).where(
            CollectTyphoon.user_id == current_user.id,
            CollectTyphoon.typhoon_id == typhoon_id
        )
        result = await db.execute(query)
        collect = result.scalar_one_or_none()

        if not collect:
            raise HTTPException(status_code=404, detail="未收藏该台风")

        await db.delete(collect)
        await db.commit()

        logger.info(f"用户 {current_user.username} 取消收藏台风 {typhoon_id}")
        return {"success": True, "message": "取消收藏成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"取消收藏失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取消收藏失败: {str(e)}")


@router.get("/reports")
async def get_user_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户生成的报告列表"""
    try:
        query = select(Report).where(
            Report.user_id == current_user.id
        ).order_by(Report.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        reports = result.scalars().all()

        # 获取总数
        count_query = select(func.count(Report.id)).where(
            Report.user_id == current_user.id
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # 转换为字典列表
        items = [
            {
                "id": r.id,
                "typhoon_id": r.typhoon_id,
                "typhoon_name": r.typhoon_name,
                "report_type": r.report_type,
                "report_content": r.report_content,
                "model_used": r.model_used,
                "user_id": r.user_id,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in reports
        ]

        return {"total": total, "items": items}
    except Exception as e:
        logger.error(f"获取报告列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取报告列表失败: {str(e)}")
