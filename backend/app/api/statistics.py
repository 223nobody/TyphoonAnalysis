"""
统计分析API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.typhoon import Typhoon, TyphoonPath
from pydantic import BaseModel

router = APIRouter(prefix="/statistics", tags=["统计分析"])


# ========== 响应模型 ==========
class YearlyStatItem(BaseModel):
    """年度统计项"""
    year: int
    count: int
    intensity_distribution: dict
    avg_max_wind_speed: Optional[float] = None
    avg_center_pressure: Optional[float] = None


class YearlyStatResponse(BaseModel):
    """年度统计响应"""
    success: bool = True
    summary: dict
    yearly_data: List[YearlyStatItem]


class IntensityStatResponse(BaseModel):
    """强度统计响应"""
    success: bool = True
    intensity_distribution: dict
    wind_speed_ranges: dict
    pressure_ranges: dict


class ComparisonRequest(BaseModel):
    """对比请求"""
    typhoon_ids: List[str]
    metrics: Optional[List[str]] = ["path", "intensity", "speed"]


class TyphoonComparisonItem(BaseModel):
    """台风对比项"""
    typhoon_id: str
    typhoon_name: str
    typhoon_name_cn: Optional[str] = None
    year: int
    max_intensity: Optional[str] = None
    max_wind_speed: Optional[float] = None
    min_pressure: Optional[float] = None
    path_length_km: Optional[float] = None
    duration_hours: Optional[float] = None
    avg_moving_speed: Optional[float] = None


class ComparisonResponse(BaseModel):
    """对比响应"""
    success: bool = True
    typhoons: List[TyphoonComparisonItem]


# ========== API端点 ==========

@router.get("/yearly", response_model=YearlyStatResponse)
async def get_yearly_statistics(
    start_year: int = Query(..., ge=2000, le=2030, description="起始年份"),
    end_year: int = Query(..., ge=2000, le=2030, description="结束年份"),
    db: AsyncSession = Depends(get_db)
):
    """
    年度台风统计
    
    统计指定年份范围内的台风数据，包括：
    - 每年台风数量
    - 强度分布
    - 平均风速和气压
    """
    if start_year > end_year:
        raise HTTPException(status_code=400, detail="起始年份不能大于结束年份")
    
    yearly_data = []
    total_typhoons = 0
    
    for year in range(start_year, end_year + 1):
        # 查询该年份的所有台风
        typhoon_query = select(Typhoon).where(Typhoon.year == year)
        typhoon_result = await db.execute(typhoon_query)
        typhoons = typhoon_result.scalars().all()
        
        year_count = len(typhoons)
        total_typhoons += year_count
        
        if year_count == 0:
            continue
        
        # 统计强度分布
        intensity_dist = {}
        typhoon_ids = [t.typhoon_id for t in typhoons]
        
        # 查询路径数据以获取强度信息
        path_query = select(TyphoonPath).where(
            TyphoonPath.typhoon_id.in_(typhoon_ids)
        )
        path_result = await db.execute(path_query)
        paths = path_result.scalars().all()
        
        # 统计强度分布
        for path in paths:
            intensity = path.intensity or "未知"
            intensity_dist[intensity] = intensity_dist.get(intensity, 0) + 1
        
        # 计算平均风速和气压
        wind_speeds = [p.max_wind_speed for p in paths if p.max_wind_speed]
        pressures = [p.center_pressure for p in paths if p.center_pressure]
        
        avg_wind = sum(wind_speeds) / len(wind_speeds) if wind_speeds else None
        avg_pressure = sum(pressures) / len(pressures) if pressures else None
        
        yearly_data.append(YearlyStatItem(
            year=year,
            count=year_count,
            intensity_distribution=intensity_dist,
            avg_max_wind_speed=round(avg_wind, 2) if avg_wind else None,
            avg_center_pressure=round(avg_pressure, 2) if avg_pressure else None
        ))
    
    # 计算汇总信息
    years_count = end_year - start_year + 1
    avg_per_year = total_typhoons / years_count if years_count > 0 else 0

    max_year_data = max(yearly_data, key=lambda x: x.count) if yearly_data else None
    min_year_data = min(yearly_data, key=lambda x: x.count) if yearly_data else None

    summary = {
        "total_typhoons": total_typhoons,
        "avg_per_year": round(avg_per_year, 2),
        "max_year": max_year_data.year if max_year_data else None,
        "max_count": max_year_data.count if max_year_data else 0,
        "min_year": min_year_data.year if min_year_data else None,
        "min_count": min_year_data.count if min_year_data else 0
    }
    
    return YearlyStatResponse(
        success=True,
        summary=summary,
        yearly_data=yearly_data
    )


@router.get("/intensity", response_model=IntensityStatResponse)
async def get_intensity_statistics(
    year: Optional[int] = Query(None, ge=2000, le=2030, description="年份（可选）"),
    typhoon_id: Optional[str] = Query(None, description="台风编号（可选）"),
    db: AsyncSession = Depends(get_db)
):
    """
    强度分布统计

    统计台风强度分布、风速范围、气压范围
    可以按年份或单个台风进行统计
    """
    # 构建查询条件
    query = select(TyphoonPath)

    if typhoon_id:
        # 单个台风统计
        query = query.where(TyphoonPath.typhoon_id == typhoon_id)
    elif year:
        # 按年份统计，需要先获取该年份的台风ID列表
        typhoon_query = select(Typhoon.typhoon_id).where(Typhoon.year == year)
        typhoon_result = await db.execute(typhoon_query)
        typhoon_ids = [row[0] for row in typhoon_result.all()]

        if not typhoon_ids:
            return IntensityStatResponse(
                success=True,
                intensity_distribution={},
                wind_speed_ranges={},
                pressure_ranges={}
            )

        query = query.where(TyphoonPath.typhoon_id.in_(typhoon_ids))

    # 执行查询
    result = await db.execute(query)
    paths = result.scalars().all()

    if not paths:
        return IntensityStatResponse(
            success=True,
            intensity_distribution={},
            wind_speed_ranges={},
            pressure_ranges={}
        )

    # 统计强度分布
    intensity_dist = {}
    for path in paths:
        intensity = path.intensity or "未知"
        intensity_dist[intensity] = intensity_dist.get(intensity, 0) + 1

    # 统计风速范围
    wind_speed_ranges = {
        "0-20m/s": 0,
        "20-30m/s": 0,
        "30-40m/s": 0,
        "40-50m/s": 0,
        "50+m/s": 0
    }

    for path in paths:
        if path.max_wind_speed:
            ws = path.max_wind_speed
            if ws < 20:
                wind_speed_ranges["0-20m/s"] += 1
            elif ws < 30:
                wind_speed_ranges["20-30m/s"] += 1
            elif ws < 40:
                wind_speed_ranges["30-40m/s"] += 1
            elif ws < 50:
                wind_speed_ranges["40-50m/s"] += 1
            else:
                wind_speed_ranges["50+m/s"] += 1

    # 统计气压范围
    pressure_ranges = {
        "1000-990hPa": 0,
        "990-980hPa": 0,
        "980-970hPa": 0,
        "970-960hPa": 0,
        "<960hPa": 0
    }

    for path in paths:
        if path.center_pressure:
            p = path.center_pressure
            if p >= 990:
                pressure_ranges["1000-990hPa"] += 1
            elif p >= 980:
                pressure_ranges["990-980hPa"] += 1
            elif p >= 970:
                pressure_ranges["980-970hPa"] += 1
            elif p >= 960:
                pressure_ranges["970-960hPa"] += 1
            else:
                pressure_ranges["<960hPa"] += 1

    return IntensityStatResponse(
        success=True,
        intensity_distribution=intensity_dist,
        wind_speed_ranges=wind_speed_ranges,
        pressure_ranges=pressure_ranges
    )


@router.post("/comparison", response_model=ComparisonResponse)
async def compare_typhoons(
    request: ComparisonRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    多台风对比分析

    对比多个台风的关键指标：
    - 最大强度
    - 最大风速
    - 最低气压
    - 路径长度
    - 持续时间
    - 平均移动速度
    """
    if not request.typhoon_ids:
        raise HTTPException(status_code=400, detail="台风编号列表不能为空")

    if len(request.typhoon_ids) > 10:
        raise HTTPException(status_code=400, detail="最多只能对比10个台风")

    comparison_items = []

    for typhoon_id in request.typhoon_ids:
        # 查询台风基本信息
        typhoon_query = select(Typhoon).where(Typhoon.typhoon_id == typhoon_id)
        typhoon_result = await db.execute(typhoon_query)
        typhoon = typhoon_result.scalar_one_or_none()

        if not typhoon:
            continue

        # 查询路径数据
        path_query = select(TyphoonPath).where(
            TyphoonPath.typhoon_id == typhoon_id
        ).order_by(TyphoonPath.timestamp)
        path_result = await db.execute(path_query)
        paths = path_result.scalars().all()

        if not paths:
            comparison_items.append(TyphoonComparisonItem(
                typhoon_id=typhoon_id,
                typhoon_name=typhoon.typhoon_name,
                typhoon_name_cn=typhoon.typhoon_name_cn,
                year=typhoon.year
            ))
            continue

        # 计算统计指标
        max_wind_speed = max([p.max_wind_speed for p in paths if p.max_wind_speed], default=None)
        min_pressure = min([p.center_pressure for p in paths if p.center_pressure], default=None)

        # 找出最强强度
        intensity_order = ["超强台风", "强台风", "台风", "强热带风暴", "热带风暴", "热带低压"]
        max_intensity = None
        for intensity in intensity_order:
            if any(p.intensity == intensity for p in paths):
                max_intensity = intensity
                break

        # 计算路径长度（简化计算，使用经纬度差值估算）
        path_length_km = None
        if len(paths) > 1:
            total_distance = 0
            for i in range(len(paths) - 1):
                lat1, lon1 = paths[i].latitude, paths[i].longitude
                lat2, lon2 = paths[i + 1].latitude, paths[i + 1].longitude
                # 简化距离计算（实际应使用Haversine公式）
                distance = ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5 * 111  # 约111km/度
                total_distance += distance
            path_length_km = round(total_distance, 2)

        # 计算持续时间
        duration_hours = None
        if len(paths) > 1:
            start_time = paths[0].timestamp
            end_time = paths[-1].timestamp
            duration = end_time - start_time
            duration_hours = round(duration.total_seconds() / 3600, 2)

        # 计算平均移动速度
        avg_moving_speed = None
        moving_speeds = [p.moving_speed for p in paths if p.moving_speed]
        if moving_speeds:
            avg_moving_speed = round(sum(moving_speeds) / len(moving_speeds), 2)

        comparison_items.append(TyphoonComparisonItem(
            typhoon_id=typhoon_id,
            typhoon_name=typhoon.typhoon_name,
            typhoon_name_cn=typhoon.typhoon_name_cn,
            year=typhoon.year,
            max_intensity=max_intensity,
            max_wind_speed=max_wind_speed,
            min_pressure=min_pressure,
            path_length_km=path_length_km,
            duration_hours=duration_hours,
            avg_moving_speed=avg_moving_speed
        ))

    return ComparisonResponse(
        success=True,
        typhoons=comparison_items
    )

