"""
台风数据API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.typhoon import Typhoon, TyphoonPath
from app.schemas.typhoon import (
    TyphoonCreate, TyphoonResponse, TyphoonListResponse,
    TyphoonPathCreate, TyphoonPathResponse, TyphoonPathListResponse
)

router = APIRouter(prefix="/typhoons", tags=["台风数据"])


# 添加兼容路由（前端使用的旧路径）
@router.get("/list", response_model=TyphoonListResponse)
async def get_typhoons_list(
    year: Optional[int] = Query(None, description="年份"),
    status: Optional[int] = Query(None, description="状态：0=stop, 1=active"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取台风列表（兼容旧路径）"""
    return await get_typhoons(year, status, skip, limit, db)


@router.get("", response_model=TyphoonListResponse)
async def get_typhoons(
    year: Optional[int] = Query(None, description="年份"),
    status: Optional[int] = Query(None, description="状态：0=stop, 1=active"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取台风列表（按typhoon_id降序排序）"""
    query = select(Typhoon)

    if year:
        query = query.where(Typhoon.year == year)
    if status is not None:
        query = query.where(Typhoon.status == status)

    # 按typhoon_id降序排序（较大的ID在前面）
    query = query.order_by(desc(Typhoon.typhoon_id)).offset(skip).limit(limit)

    result = await db.execute(query)
    typhoons = result.scalars().all()

    # 获取总数
    count_query = select(Typhoon)
    if year:
        count_query = count_query.where(Typhoon.year == year)
    if status is not None:
        count_query = count_query.where(Typhoon.status == status)

    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return TyphoonListResponse(total=total, items=typhoons)


@router.get("/{typhoon_id}", response_model=TyphoonResponse)
async def get_typhoon(
    typhoon_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取台风详情"""
    query = select(Typhoon).where(Typhoon.typhoon_id == typhoon_id)
    result = await db.execute(query)
    typhoon = result.scalar_one_or_none()
    
    if not typhoon:
        raise HTTPException(status_code=404, detail="台风不存在")
    
    return typhoon


@router.post("", response_model=TyphoonResponse)
async def create_typhoon(
    typhoon: TyphoonCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建台风记录"""
    # 检查是否已存在
    query = select(Typhoon).where(Typhoon.typhoon_id == typhoon.typhoon_id)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="台风编号已存在")
    
    db_typhoon = Typhoon(**typhoon.model_dump())
    db.add(db_typhoon)
    await db.commit()
    await db.refresh(db_typhoon)
    
    return db_typhoon


@router.get("/{typhoon_id}/path", response_model=TyphoonPathListResponse)
async def get_typhoon_path(
    typhoon_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db)
):
    """获取台风路径数据（按timestamp升序排序）"""
    query = select(TyphoonPath).where(
        TyphoonPath.typhoon_id == typhoon_id
    ).order_by(TyphoonPath.timestamp.asc()).offset(skip).limit(limit)

    result = await db.execute(query)
    paths = result.scalars().all()

    # 获取总数
    count_query = select(TyphoonPath).where(TyphoonPath.typhoon_id == typhoon_id)
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return TyphoonPathListResponse(total=total, items=paths)


@router.post("/{typhoon_id}/path", response_model=TyphoonPathResponse)
async def create_typhoon_path(
    typhoon_id: str,
    path: TyphoonPathCreate,
    db: AsyncSession = Depends(get_db)
):
    """添加台风路径点"""
    # 确保typhoon_id一致
    path.typhoon_id = typhoon_id
    
    db_path = TyphoonPath(**path.model_dump())
    db.add(db_path)
    await db.commit()
    await db.refresh(db_path)
    
    return db_path


@router.post("/batch/paths")
async def create_batch_paths(
    paths: List[TyphoonPathCreate],
    db: AsyncSession = Depends(get_db)
):
    """批量添加台风路径数据"""
    db_paths = [TyphoonPath(**path.model_dump()) for path in paths]
    db.add_all(db_paths)
    await db.commit()
    
    return {"success": True, "count": len(db_paths)}

