"""
台风数据API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import datetime
import logging

from app.core.database import get_db
from app.models.typhoon import Typhoon, TyphoonPath, ActiveTyphoonForecast
from app.schemas.typhoon import (
    TyphoonCreate, TyphoonResponse, TyphoonListResponse,
    TyphoonPathCreate, TyphoonPathResponse, TyphoonPathListResponse
)

router = APIRouter(prefix="/typhoons", tags=["台风数据"])
logger = logging.getLogger(__name__)


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



# ========== 动态路由（必须在具体路由之后定义）==========

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
    """
    获取台风路径数据（按timestamp升序排序）

    统一从 typhoon_paths 表查询所有台风路径数据
    """
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


# ==================== 活跃台风预报数据接口 ====================

class ForecastPointResponse(BaseModel):
    """预报点响应模型"""
    forecast_time: datetime
    forecast_agency: str
    latitude: float
    longitude: float
    center_pressure: Optional[float] = None
    max_wind_speed: Optional[float] = None
    power_level: Optional[int] = None
    intensity: Optional[str] = None

    class Config:
        from_attributes = True


class ForecastPathResponse(BaseModel):
    """预报路径响应模型（按机构分组）"""
    agency: str
    color: str  # 前端显示颜色
    points: List[ForecastPointResponse]


@router.get("/{typhoon_id}/forecast", response_model=List[ForecastPathResponse])
async def get_typhoon_forecast(
    typhoon_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取台风预报路径数据（按预报机构分组）

    数据清洗策略：
    1. 对于有base_time的机构：只返回最新base_time的预报数据
    2. 对于base_time为NULL的机构：返回所有数据（如中国香港）
    3. 对于中国的预报数据：只返回未来的预报点（forecast_time > 最新实时时间）
    """
    from sqlalchemy import func, and_

    # 1. 获取台风的最新实时位置时间点（用于过滤中国的历史预报数据）
    latest_time_query = select(func.max(TyphoonPath.timestamp)).where(
        TyphoonPath.typhoon_id == typhoon_id
    )
    latest_time_result = await db.execute(latest_time_query)
    latest_real_time = latest_time_result.scalar()

    if not latest_real_time:
        logger.warning(f"台风 {typhoon_id} 没有实时路径数据")

    # 2. 获取所有机构列表
    agencies_query = select(ActiveTyphoonForecast.forecast_agency).where(
        ActiveTyphoonForecast.typhoon_id == typhoon_id
    ).distinct()
    agencies_result = await db.execute(agencies_query)
    all_agencies = [row[0] for row in agencies_result.all()]

    if not all_agencies:
        logger.warning(f"台风 {typhoon_id} 没有预报数据")
        return []

    # 3. 子查询：获取每个机构的最新base_time（仅针对有base_time的记录）
    subquery = select(
        ActiveTyphoonForecast.forecast_agency,
        func.max(ActiveTyphoonForecast.base_time).label('max_base_time')
    ).where(
        and_(
            ActiveTyphoonForecast.typhoon_id == typhoon_id,
            ActiveTyphoonForecast.base_time.isnot(None)
        )
    ).group_by(ActiveTyphoonForecast.forecast_agency).subquery()

    # 4. 主查询：分两种情况获取数据
    # 情况A：有base_time的机构，只取最新base_time的数据
    query_with_base_time = select(ActiveTyphoonForecast).join(
        subquery,
        and_(
            ActiveTyphoonForecast.forecast_agency == subquery.c.forecast_agency,
            ActiveTyphoonForecast.base_time == subquery.c.max_base_time
        )
    ).where(
        ActiveTyphoonForecast.typhoon_id == typhoon_id
    )

    # 情况B：base_time为NULL的机构（如中国香港），取所有数据
    query_without_base_time = select(ActiveTyphoonForecast).where(
        and_(
            ActiveTyphoonForecast.typhoon_id == typhoon_id,
            ActiveTyphoonForecast.base_time.is_(None)
        )
    )

    # 执行两个查询
    result_with_base_time = await db.execute(query_with_base_time)
    forecasts_with_base_time = result_with_base_time.scalars().all()

    result_without_base_time = await db.execute(query_without_base_time)
    forecasts_without_base_time = result_without_base_time.scalars().all()

    # 合并结果
    all_forecasts = list(forecasts_with_base_time) + list(forecasts_without_base_time)

    if not all_forecasts:
        logger.warning(f"台风 {typhoon_id} 没有符合条件的预报数据")
        return []

    # 5. 数据清洗：过滤中国的历史预报数据
    cleaned_forecasts = []
    china_filtered_count = 0

    for forecast in all_forecasts:
        # 对于中国的预报数据，只保留未来的预报点
        if forecast.forecast_agency == "中国" and latest_real_time:
            if forecast.forecast_time > latest_real_time:
                cleaned_forecasts.append(forecast)
            else:
                china_filtered_count += 1
        else:
            # 其他机构的数据保持不变
            cleaned_forecasts.append(forecast)

    # 6. 按预报机构分组
    agency_map = {}
    for forecast in cleaned_forecasts:
        agency = forecast.forecast_agency
        if agency not in agency_map:
            agency_map[agency] = []
        agency_map[agency].append(forecast)

    # 按forecast_time排序
    for agency in agency_map:
        agency_map[agency].sort(key=lambda x: x.forecast_time)

    # 定义预报机构颜色（优化配色方案，提高对比度和可读性）
    agency_colors = {
        "中国": "#DC2626",      # 红色系（更柔和的红色）
        "日本": "#2563EB",      # 蓝色系（更鲜明的蓝色）
        "美国": "#16A34A",      # 绿色系（更深的绿色）
        "中国台湾": "#9333EA",  # 紫色系（更鲜明的紫色）
        "中国香港": "#EA580C",  # 橙色系（更鲜明的橙色）
    }

    # 构建响应数据
    response = []
    for agency, points in agency_map.items():
        if not points:
            continue
        response.append(ForecastPathResponse(
            agency=agency,
            color=agency_colors.get(agency, "#808080"),
            points=[ForecastPointResponse.model_validate(p) for p in points]
        ))

    return response

