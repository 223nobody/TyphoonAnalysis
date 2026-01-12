"""
实时预警API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.core.database import get_db
from app.models.typhoon import Typhoon, TyphoonPath
from pydantic import BaseModel, Field

router = APIRouter(prefix="/alert", tags=["实时预警"])


# ========== 请求/响应模型 ==========
class AlertRuleConditions(BaseModel):
    """预警规则条件"""
    intensity: Optional[List[str]] = Field(None, description="强度等级列表")
    wind_speed_min: Optional[float] = Field(None, ge=0, description="最小风速(m/s)")
    pressure_max: Optional[float] = Field(None, le=1013, description="最大气压(hPa)")
    distance_to_land_km: Optional[float] = Field(None, ge=0, description="距离陆地距离(km)")


class AlertRuleCreate(BaseModel):
    """创建预警规则请求"""
    rule_name: str = Field(..., min_length=1, max_length=100, description="规则名称")
    conditions: AlertRuleConditions = Field(..., description="预警条件")
    notification_channels: List[str] = Field(default=["system"], description="通知渠道")
    enabled: bool = Field(default=True, description="是否启用")


class AlertRuleResponse(BaseModel):
    """预警规则响应"""
    id: int
    rule_name: str
    conditions: dict
    notification_channels: List[str]
    enabled: bool
    created_at: datetime


class ActiveAlertItem(BaseModel):
    """活跃预警项"""
    typhoon_id: str
    typhoon_name: str
    typhoon_name_cn: Optional[str] = None
    alert_level: str  # 预警级别: 蓝色/黄色/橙色/红色
    alert_reason: str  # 预警原因
    current_intensity: Optional[str] = None
    current_wind_speed: Optional[float] = None
    current_pressure: Optional[float] = None
    latest_position: Optional[dict] = None
    alert_time: datetime


class ActiveAlertResponse(BaseModel):
    """活跃预警响应"""
    success: bool = True
    count: int
    alerts: List[ActiveAlertItem]


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


# ========== 辅助函数 ==========
def determine_alert_level(wind_speed: Optional[float], pressure: Optional[float], intensity: Optional[str]) -> str:
    """
    根据风速、气压、强度判断预警级别
    
    预警级别标准（参考中国气象局标准）：
    - 蓝色预警：热带风暴（风速 17.2-24.4 m/s）
    - 黄色预警：强热带风暴（风速 24.5-32.6 m/s）
    - 橙色预警：台风（风速 32.7-41.4 m/s）
    - 红色预警：强台风及以上（风速 ≥41.5 m/s）
    """
    if intensity in ["超强台风", "强台风"]:
        return "红色"
    elif intensity == "台风":
        return "橙色"
    elif intensity == "强热带风暴":
        return "黄色"
    elif intensity in ["热带风暴", "热带低压"]:
        return "蓝色"
    
    # 根据风速判断
    if wind_speed:
        if wind_speed >= 41.5:
            return "红色"
        elif wind_speed >= 32.7:
            return "橙色"
        elif wind_speed >= 24.5:
            return "黄色"
        elif wind_speed >= 17.2:
            return "蓝色"
    
    # 根据气压判断（辅助）
    if pressure:
        if pressure < 920:
            return "红色"
        elif pressure < 950:
            return "橙色"
        elif pressure < 970:
            return "黄色"
        elif pressure < 990:
            return "蓝色"
    
    return "蓝色"  # 默认蓝色预警


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

@router.get("/active", response_model=ActiveAlertResponse)
async def get_active_alerts(
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前活跃的预警信息
    
    查询所有活跃状态的台风，根据其强度、风速、气压等指标
    自动生成预警信息
    """
    # 查询活跃台风（status=1）
    typhoon_query = select(Typhoon).where(Typhoon.status == 1)
    typhoon_result = await db.execute(typhoon_query)
    active_typhoons = typhoon_result.scalars().all()
    
    alerts = []
    
    for typhoon in active_typhoons:
        # 查询最新路径点
        path_query = select(TyphoonPath).where(
            TyphoonPath.typhoon_id == typhoon.typhoon_id
        ).order_by(desc(TyphoonPath.timestamp)).limit(1)
        path_result = await db.execute(path_query)
        latest_path = path_result.scalar_one_or_none()
        
        if not latest_path:
            continue
        
        # 判断预警级别
        alert_level = determine_alert_level(
            latest_path.max_wind_speed,
            latest_path.center_pressure,
            latest_path.intensity
        )
        
        # 生成预警原因
        typhoon_data = {
            'intensity': latest_path.intensity,
            'wind_speed': latest_path.max_wind_speed,
            'pressure': latest_path.center_pressure
        }
        alert_reason = generate_alert_reason(typhoon_data, alert_level)
        
        # 构建预警项
        alert_item = ActiveAlertItem(
            typhoon_id=typhoon.typhoon_id,
            typhoon_name=typhoon.typhoon_name,
            typhoon_name_cn=typhoon.typhoon_name_cn,
            alert_level=alert_level,
            alert_reason=alert_reason,
            current_intensity=latest_path.intensity,
            current_wind_speed=latest_path.max_wind_speed,
            current_pressure=latest_path.center_pressure,
            latest_position={
                "latitude": latest_path.latitude,
                "longitude": latest_path.longitude,
                "timestamp": str(latest_path.timestamp)
            },
            alert_time=latest_path.timestamp
        )
        
        alerts.append(alert_item)
    
    # 按预警级别排序（红色>橙色>黄色>蓝色）
    level_order = {"红色": 0, "橙色": 1, "黄色": 2, "蓝色": 3}
    alerts.sort(key=lambda x: level_order.get(x.alert_level, 4))
    
    return ActiveAlertResponse(
        success=True,
        count=len(alerts),
        alerts=alerts
    )


@router.post("/rules")
async def create_alert_rule(
    rule: AlertRuleCreate
):
    """
    创建预警规则

    注意：当前版本仅支持规则的创建和存储，
    实际的预警触发逻辑需要配合定时任务实现
    """
    # 这里简化实现，仅返回创建成功的响应
    # 实际应用中需要将规则存储到数据库

    return {
        "success": True,
        "rule_id": f"rule_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "message": "预警规则创建成功",
        "rule_name": rule.rule_name,
        "conditions": rule.conditions.model_dump(),
        "enabled": rule.enabled
    }


@router.get("/rules")
async def get_alert_rules(
    enabled: Optional[bool] = Query(None, description="是否启用")
):
    """
    获取预警规则列表

    注意：当前版本返回示例数据
    实际应用中需要从数据库查询
    """
    # 示例规则数据
    sample_rules = [
        {
            "id": 1,
            "rule_name": "强台风预警",
            "conditions": {
                "intensity": ["强台风", "超强台风"],
                "wind_speed_min": 45.0,
                "pressure_max": 960.0
            },
            "notification_channels": ["system", "email"],
            "enabled": True,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": 2,
            "rule_name": "近海台风预警",
            "conditions": {
                "distance_to_land_km": 500,
                "wind_speed_min": 30.0
            },
            "notification_channels": ["system"],
            "enabled": True,
            "created_at": datetime.now().isoformat()
        }
    ]

    if enabled is not None:
        sample_rules = [r for r in sample_rules if r["enabled"] == enabled]

    return {
        "success": True,
        "count": len(sample_rules),
        "rules": sample_rules
    }


@router.get("/history", response_model=AlertHistoryResponse)
async def get_alert_history(
    typhoon_id: Optional[str] = Query(None, description="台风编号"),
    alert_level: Optional[str] = Query(None, description="预警级别"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    limit: int = Query(50, ge=1, le=100, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取预警历史记录

    注意：当前版本基于历史台风数据生成模拟预警记录
    实际应用中应从专门的预警记录表查询
    """
    # 构建查询条件
    typhoon_query = select(Typhoon)

    if typhoon_id:
        typhoon_query = typhoon_query.where(Typhoon.typhoon_id == typhoon_id)

    # 查询历史台风（status=0）
    typhoon_query = typhoon_query.where(Typhoon.status == 0).limit(limit)
    typhoon_result = await db.execute(typhoon_query)
    historical_typhoons = typhoon_result.scalars().all()

    history_items = []

    for typhoon in historical_typhoons:
        # 查询该台风的最强路径点
        path_query = select(TyphoonPath).where(
            TyphoonPath.typhoon_id == typhoon.typhoon_id
        ).order_by(desc(TyphoonPath.max_wind_speed)).limit(1)
        path_result = await db.execute(path_query)
        strongest_path = path_result.scalar_one_or_none()

        if not strongest_path:
            continue

        # 判断预警级别
        alert_level_value = determine_alert_level(
            strongest_path.max_wind_speed,
            strongest_path.center_pressure,
            strongest_path.intensity
        )

        # 如果指定了预警级别筛选
        if alert_level and alert_level_value != alert_level:
            continue

        # 生成预警原因
        typhoon_data = {
            'intensity': strongest_path.intensity,
            'wind_speed': strongest_path.max_wind_speed,
            'pressure': strongest_path.center_pressure
        }
        alert_reason = generate_alert_reason(typhoon_data, alert_level_value)

        # 查询该台风的最后路径点（作为解除时间）
        last_path_query = select(TyphoonPath).where(
            TyphoonPath.typhoon_id == typhoon.typhoon_id
        ).order_by(desc(TyphoonPath.timestamp)).limit(1)
        last_path_result = await db.execute(last_path_query)
        last_path = last_path_result.scalar_one_or_none()

        history_item = AlertHistoryItem(
            id=typhoon.id,
            typhoon_id=typhoon.typhoon_id,
            typhoon_name=f"{typhoon.typhoon_name_cn or typhoon.typhoon_name}",
            alert_level=alert_level_value,
            alert_reason=alert_reason,
            alert_time=strongest_path.timestamp,
            resolved_time=last_path.timestamp if last_path else None,
            status="resolved"
        )

        # 日期筛选
        if start_date and history_item.alert_time < start_date:
            continue
        if end_date and history_item.alert_time > end_date:
            continue

        history_items.append(history_item)

    return AlertHistoryResponse(
        success=True,
        total=len(history_items),
        items=history_items
    )

