"""
实时预警API路由 - 基于台风公报数据
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging

from app.core.database import get_db
from app.models.typhoon import Typhoon, TyphoonPath
from app.services.crawler.bulletin_crawler import bulletin_crawler
from pydantic import BaseModel, Field

router = APIRouter(prefix="/alert", tags=["实时预警"])
logger = logging.getLogger(__name__)


# ========== 辅助函数 ==========
def determine_alert_level(wind_speed: Optional[float], pressure: Optional[float], intensity: Optional[str]) -> str:
    """根据风速、气压、强度判断预警级别"""
    if intensity in ["超强台风", "强台风"]:
        return "红色"
    elif intensity == "台风":
        return "橙色"
    elif intensity == "强热带风暴":
        return "黄色"
    elif intensity in ["热带风暴", "热带低压"]:
        return "蓝色"

    if wind_speed:
        if wind_speed >= 41.5:
            return "红色"
        elif wind_speed >= 32.7:
            return "橙色"
        elif wind_speed >= 24.5:
            return "黄色"
        elif wind_speed >= 17.2:
            return "蓝色"

    if pressure:
        if pressure < 920:
            return "红色"
        elif pressure < 950:
            return "橙色"
        elif pressure < 970:
            return "黄色"
        elif pressure < 990:
            return "蓝色"

    return "蓝色"


def generate_alert_reason(typhoon_data: dict, alert_level: str) -> str:
    """生成预警原因描述"""
    reasons = []

    intensity = typhoon_data.get('intensity')
    wind_speed = typhoon_data.get('wind_speed')
    pressure = typhoon_data.get('pressure')

    if intensity:
        reasons.append(f"当前强度为{intensity}")

    if wind_speed:
        reasons.append(f"最大风速达到{wind_speed}m/s")

    if pressure:
        reasons.append(f"中心气压为{pressure}hPa")

    level_desc = {
        "红色": "极强台风活动，请高度警惕",
        "橙色": "强台风活动，请密切关注",
        "黄色": "台风活动加强，请注意防范",
        "蓝色": "台风活动，请保持关注"
    }

    reason = "，".join(reasons)
    if reason:
        reason += "。" + level_desc.get(alert_level, "")
    else:
        reason = level_desc.get(alert_level, "台风活动")

    return reason


# ========== API端点 ==========
class TyphoonBulletinItem(BaseModel):
    """台风公报项"""
    typhoon_name: str = Field(..., description="台风名称")
    typhoon_number: str = Field(..., description="台风编号")
    release_time: str = Field(..., description="发布时间")
    time: str = Field(..., description="观测时间")
    position: str = Field(..., description="中心位置")
    intensity: str = Field(..., description="强度等级")
    max_wind: str = Field(..., description="最大风力")
    center_pressure: str = Field(..., description="中心气压")
    reference_position: str = Field(..., description="参考位置")
    wind_circle: str = Field(..., description="风圈半径")
    forecast: str = Field(..., description="预报结论")
    summary: str = Field(..., description="摘要")
    description: str = Field(..., description="描述")


class ActiveAlertResponse(BaseModel):
    """活跃预警响应"""
    success: bool = True
    has_bulletin: bool = Field(..., description="是否有台风公报")
    bulletin: Optional[TyphoonBulletinItem] = Field(None, description="台风公报信息")
    message: str = Field(default="", description="提示信息")


class AlertHistoryItem(BaseModel):
    """预警历史项"""
    id: int
    typhoon_id: str
    typhoon_name: str
    alert_level: str
    alert_reason: str
    alert_time: datetime
    resolved_time: Optional[datetime] = None
    status: str  # active/resolved


class AlertHistoryResponse(BaseModel):
    """预警历史响应"""
    success: bool = True
    total: int
    items: List[AlertHistoryItem]


# ========== API端点 ==========

@router.get("/active", response_model=ActiveAlertResponse)
async def get_active_alerts():
    """
    获取当前活跃的预警信息（基于台风公报）

    从中国气象局获取最新的台风公报数据，
    不再从数据库分析路径数据
    """
    try:
        # 获取台风公报
        bulletin = bulletin_crawler.get_typhoon_bulletin()

        if not bulletin:
            return ActiveAlertResponse(
                success=True,
                has_bulletin=False,
                bulletin=None,
                message="当前没有活跃的台风"
            )

        # 构建公报响应
        bulletin_item = TyphoonBulletinItem(
            typhoon_name=bulletin.get('typhoon_name', ''),
            typhoon_number=bulletin.get('typhoon_number', ''),
            release_time=bulletin.get('release_time', ''),
            time=bulletin.get('time', ''),
            position=bulletin.get('position', ''),
            intensity=bulletin.get('intensity', ''),
            max_wind=bulletin.get('max_wind', ''),
            center_pressure=bulletin.get('center_pressure', ''),
            reference_position=bulletin.get('reference_position', ''),
            wind_circle=bulletin.get('wind_circle', ''),
            forecast=bulletin.get('forecast', ''),
            summary=bulletin.get('summary', ''),
            description=bulletin.get('description', '')
        )

        return ActiveAlertResponse(
            success=True,
            has_bulletin=True,
            bulletin=bulletin_item,
            message="台风公报已更新"
        )

    except Exception as e:
        logger.error(f"获取台风公报失败: {e}")
        return ActiveAlertResponse(
            success=False,
            has_bulletin=False,
            bulletin=None,
            message=f"获取台风公报失败: {str(e)}"
        )


@router.get("/history", response_model=AlertHistoryResponse)
async def get_alert_history(
    typhoon_id: Optional[str] = Query(None, description="台风编号"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    limit: int = Query(50, ge=1, le=100, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取预警历史记录

    使用模拟数据生成历史预警记录
    """
    try:
        # 查询台风数据用于生成模拟预警
        typhoon_query = select(Typhoon)
        if typhoon_id:
            typhoon_query = typhoon_query.where(Typhoon.typhoon_id == typhoon_id)

        typhoon_result = await db.execute(typhoon_query)
        typhoons = typhoon_result.scalars().all()

        history_items = []
        item_id = 1

        for typhoon in typhoons:
            # 查询该台风的路径点
            path_query = select(TyphoonPath).where(
                TyphoonPath.typhoon_id == typhoon.typhoon_id
            ).order_by(TyphoonPath.timestamp)

            path_result = await db.execute(path_query)
            paths = path_result.scalars().all()

            if not paths:
                continue

            # 为每个台风生成多个预警记录（基于路径点）
            for i, path in enumerate(paths):
                # 只为部分路径点生成预警（避免数据过多）
                if i % 3 != 0:  # 每3个点生成一个预警
                    continue

                # 判断预警级别
                alert_level = determine_alert_level(
                    path.max_wind_speed,
                    path.center_pressure,
                    path.intensity
                )

                # 生成预警原因
                typhoon_data = {
                    'intensity': path.intensity,
                    'wind_speed': path.max_wind_speed,
                    'pressure': path.center_pressure
                }
                alert_reason = generate_alert_reason(typhoon_data, alert_level)

                # 判断状态（最后一个点为active，其他为resolved）
                is_last = (i == len(paths) - 1)
                status = "active" if is_last else "resolved"
                resolved_time = None if is_last else (path.timestamp if path.timestamp else None)

                # 应用日期筛选
                if start_date and path.timestamp and path.timestamp < start_date:
                    continue
                if end_date and path.timestamp and path.timestamp > end_date:
                    continue

                history_item = AlertHistoryItem(
                    id=item_id,
                    typhoon_id=typhoon.typhoon_id,
                    typhoon_name=typhoon.typhoon_name_cn or typhoon.typhoon_name or "未知",
                    alert_level=alert_level,
                    alert_reason=alert_reason,
                    alert_time=path.timestamp if path.timestamp else datetime.now(),
                    resolved_time=resolved_time,
                    status=status
                )
                history_items.append(history_item)
                item_id += 1

                # 达到限制数量则停止
                if len(history_items) >= limit:
                    break

            if len(history_items) >= limit:
                break

        # 按预警时间倒序排列
        history_items.sort(key=lambda x: x.alert_time, reverse=True)

        return AlertHistoryResponse(
            success=True,
            total=len(history_items),
            items=history_items[:limit]
        )

    except Exception as e:
        logger.error(f"获取预警历史失败: {e}")
        return AlertHistoryResponse(
            success=False,
            total=0,
            items=[]
        )


