"""
知识图谱数据模型定义
严格按照知识图谱开发文档定义节点类型、关系类型及其属性

节点类型:
- Typhoon: 台风节点
- PathPoint: 路径点节点
- Location: 地理位置节点
- Time: 时间节点
- Intensity: 强度等级节点

关系类型:
- HAS_PATH_POINT: 台风-路径点关系
- NEXT: 路径点顺序关系
- OCCURRED_IN: 台风-时间关系
- LANDED_AT: 台风-地点关系
- REACHED_INTENSITY: 台风-强度关系
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from dataclasses import dataclass


class NodeType(str, Enum):
    """知识图谱节点类型枚举"""
    TYPHOON = "Typhoon"
    PATH_POINT = "PathPoint"
    LOCATION = "Location"
    TIME = "Time"
    INTENSITY = "Intensity"


class RelationshipType(str, Enum):
    """知识图谱关系类型枚举"""
    # 基础关系
    HAS_PATH_POINT = "HAS_PATH_POINT"
    NEXT = "NEXT"
    OCCURRED_IN = "OCCURRED_IN"
    LANDED_AT = "LANDED_AT"
    REACHED_INTENSITY = "REACHED_INTENSITY"

    # 扩展关系 - 台风生命周期
    GENERATED_AT = "GENERATED_AT"  # 生成位置
    DISSIPATED_AT = "DISSIPATED_AT"  # 消散位置

    # 扩展关系 - 强度变化
    INTENSIFIED_TO = "INTENSIFIED_TO"  # 增强到某强度
    WEAKENED_TO = "WEAKENED_TO"  # 减弱到某强度

    # 扩展关系 - 相似性
    SIMILAR_TO = "SIMILAR_TO"  # 相似台风

    # 扩展关系 - 地理影响
    AFFECTED_AREA = "AFFECTED_AREA"  # 影响区域
    PASSED_NEAR = "PASSED_NEAR"  # 经过附近


class IntensityLevel(str, Enum):
    """台风强度等级枚举"""
    TD = "TD"
    TS = "TS"
    STS = "STS"
    TY = "TY"
    STY = "STY"
    SUPER_TY = "SuperTY"


INTENSITY_LEVELS = {
    IntensityLevel.TD: {"name_cn": "热带低压", "wind_speed_min": 10.8, "wind_speed_max": 17.1},
    IntensityLevel.TS: {"name_cn": "热带风暴", "wind_speed_min": 17.2, "wind_speed_max": 24.4},
    IntensityLevel.STS: {"name_cn": "强热带风暴", "wind_speed_min": 24.5, "wind_speed_max": 32.6},
    IntensityLevel.TY: {"name_cn": "台风", "wind_speed_min": 32.7, "wind_speed_max": 41.4},
    IntensityLevel.STY: {"name_cn": "强台风", "wind_speed_min": 41.5, "wind_speed_max": 50.9},
    IntensityLevel.SUPER_TY: {"name_cn": "超强台风", "wind_speed_min": 51.0, "wind_speed_max": 999.0},
}


class TyphoonProperties(BaseModel):
    """台风节点属性模型 - 严格按照开发方案文档定义"""
    # 基础信息
    typhoon_id: str = Field(..., description="台风编号（唯一标识，格式YYYYMM）")
    name_cn: str = Field(default="", description="中文名称（来自CSV: ty_name_ch）")
    name_en: str = Field(default="", description="英文名称（来自CSV: ty_name_en）")
    year: int = Field(..., ge=1949, le=2100, description="年份（来自CSV: ty_code前4位）")

    # 强度统计（从所有路径点计算）
    max_wind_speed: float = Field(default=0.0, ge=0, description="最大风速 m/s（来自CSV: max_wind_speed最大值）")
    min_pressure: float = Field(default=9999.0, ge=0, description="最低气压 hPa（来自CSV: center_pressure最小值）")
    max_power: Optional[int] = Field(default=None, ge=0, le=17, description="最高风力等级（来自CSV: power最大值）")
    peak_intensity: Optional[str] = Field(default=None, description="峰值强度等级（根据max_wind_speed计算）")

    # 路径统计（计算得出）
    total_path_points: int = Field(default=0, ge=0, description="路径点总数")
    duration_hours: int = Field(default=0, ge=0, description="持续时长（小时）")

    # 生成位置（第一个路径点）
    start_lat: float = Field(default=0.0, ge=-90, le=90, description="起始纬度")
    start_lon: float = Field(default=0.0, ge=-180, le=180, description="起始经度")
    end_lat: float = Field(default=0.0, ge=-90, le=90, description="结束纬度")
    end_lon: float = Field(default=0.0, ge=-180, le=180, description="结束经度")

    # 移动统计（从路径点计算）
    avg_moving_speed: Optional[float] = Field(default=None, ge=0, description="平均移动速度 km/h")
    max_moving_speed: Optional[float] = Field(default=None, ge=0, description="最大移动速度 km/h")
    total_distance_km: Optional[float] = Field(default=None, ge=0, description="总移动距离 km（计算得出）")

    # 登陆信息（从登陆数据关联）
    landfall_count: Optional[int] = Field(default=None, ge=0, description="登陆次数")

    # 时间信息（从路径点提取）
    start_time: Optional[datetime] = Field(default=None, description="生成时间（第一个路径点）")
    end_time: Optional[datetime] = Field(default=None, description="消散时间（最后一个路径点）")

    @field_validator('typhoon_id')
    @classmethod
    def validate_typhoon_id(cls, v: str) -> str:
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError('台风编号必须是6位数字（YYYYMM格式）')
        return v


class PathPointProperties(BaseModel):
    """路径点节点属性模型 - 严格按照开发方案文档定义"""
    # 关联信息
    typhoon_id: str = Field(..., description="台风编号（来自CSV: ty_code）")
    sequence: int = Field(..., ge=1, description="序列号（按时间排序生成）")

    # 位置信息（来自CSV: latitude, longitude）
    lat: float = Field(..., ge=-90, le=90, description="纬度")
    lon: float = Field(..., ge=-180, le=180, description="经度")
    location: Optional[str] = Field(default=None, description="Neo4j空间点类型WKT格式")

    # 时间信息（来自CSV: timestamp）
    timestamp: Optional[datetime] = Field(default=None, description="观测时间戳")
    hour_of_year: Optional[int] = Field(default=None, ge=0, le=8784, description="年内小时数（用于时序分析）")

    # 强度信息（来自CSV: center_pressure, max_wind_speed, intensity, power）
    pressure: Optional[float] = Field(default=None, ge=0, description="中心气压 hPa")
    wind_speed: Optional[float] = Field(default=None, ge=0, description="最大风速 m/s")
    intensity: Optional[str] = Field(default=None, description="强度等级中文名（来自CSV: intensity）")
    intensity_level: Optional[str] = Field(default=None, description="强度等级代码（TD/TS/STS/TY/STY/SuperTY）")
    power: Optional[int] = Field(default=None, ge=0, le=17, description="风力等级（0-17级，来自CSV: power）")

    # 移动信息（来自CSV: moving_direction, moving_speed）
    moving_direction: Optional[str] = Field(default=None, description="移动方向（N/NE/E/SE/S/SW/W/NW）")
    moving_speed: Optional[float] = Field(default=None, ge=0, description="移动速度 km/h")

    # 衍生计算属性
    distance_from_genesis: Optional[float] = Field(default=None, ge=0, description="距生成点距离 km")
    distance_to_next: Optional[float] = Field(default=None, ge=0, description="到下一个路径点距离 km")
    pressure_trend: Optional[float] = Field(default=None, description="气压变化趋势 hPa/6h")


class LocationProperties(BaseModel):
    """地理位置节点属性模型 - 严格按照开发方案文档定义"""
    # 基础信息
    name: str = Field(..., description="地点名称（来自CSV: land_address）")

    # 地理坐标（来自CSV: land_lat, land_lng）
    lat: float = Field(..., ge=-90, le=90, description="纬度")
    lon: float = Field(..., ge=-180, le=180, description="经度")
    location: Optional[str] = Field(default=None, description="Neo4j空间点类型WKT格式")

    # 强度信息（来自CSV: land_strong）
    intensity: Optional[str] = Field(default=None, description="登陆时强度中文")

    # 描述信息（来自CSV: land_info）
    description: Optional[str] = Field(default=None, description="描述信息")

    type: str = Field(default="city", description="类型(city/province/country)")


class TimeProperties(BaseModel):
    """时间节点属性模型 - 严格按照开发方案文档定义"""
    # 基础信息
    year: int = Field(..., ge=1949, le=2100, description="年份（来自CSV: timestamp）")

    # 统计信息（计算得出）
    total_typhoons: Optional[int] = Field(default=None, ge=0, description="该年台风总数")
    total_landfalls: Optional[int] = Field(default=None, ge=0, description="该年登陆次数")
    strongest_typhoon_id: Optional[str] = Field(default=None, description="最强台风编号")
    strongest_wind_speed: Optional[float] = Field(default=None, ge=0, description="最强台风的最大风速 m/s")
    strongest_intensity_level: Optional[str] = Field(default=None, description="最强台风等级")

    is_peak_season: bool = Field(default=False, description="是否台风高发期(7-9月)")


class IntensityProperties(BaseModel):
    """强度等级节点属性模型 - 静态定义，不包含时间信息"""
    # 基础信息
    level: IntensityLevel = Field(..., description="等级代码")
    name_cn: str = Field(..., description="中文名称")

    # 风速范围
    wind_speed_min: float = Field(..., ge=0, description="最小风速 m/s")
    wind_speed_max: float = Field(..., ge=0, description="最大风速 m/s")
    # 注意：时间信息存储在 REACHED_INTENSITY 关系上，因为每个台风达到强度的时间不同


class GraphNode(BaseModel):
    """图谱节点统一模型"""
    id: str = Field(..., description="节点唯一标识")
    labels: List[str] = Field(..., description="节点标签列表")
    properties: Dict[str, Any] = Field(default_factory=dict, description="节点属性")

    def get_primary_label(self) -> str:
        """获取主标签"""
        return self.labels[0] if self.labels else "Unknown"


class GraphLink(BaseModel):
    """图谱关系统一模型"""
    source: str = Field(..., description="源节点ID")
    target: str = Field(..., description="目标节点ID")
    type: RelationshipType = Field(..., description="关系类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")


class SimilarityRelationshipProperties(BaseModel):
    """相似性关系属性模型"""
    similarity_score: float = Field(..., ge=0, le=1, description="相似度分数(0-1)")
    path_similarity: float = Field(default=0, ge=0, le=1, description="路径形状相似度")
    genesis_similarity: float = Field(default=0, ge=0, le=1, description="生成位置相似度")
    intensity_similarity: float = Field(default=0, ge=0, le=1, description="强度变化相似度")
    temporal_similarity: float = Field(default=0, ge=0, le=1, description="时间模式相似度")
    calculated_at: datetime = Field(default_factory=datetime.now, description="计算时间")


class LifecycleRelationshipProperties(BaseModel):
    """生命周期关系属性模型"""
    timestamp: datetime = Field(..., description="时间戳")
    lat: float = Field(..., ge=-90, le=90, description="纬度")
    lon: float = Field(..., ge=-180, le=180, description="经度")
    description: Optional[str] = Field(default=None, description="描述")


class IntensityChangeProperties(BaseModel):
    """强度变化关系属性模型"""
    from_level: str = Field(..., description="原强度等级")
    to_level: str = Field(..., description="目标强度等级")
    change_time: datetime = Field(..., description="变化时间")
    wind_speed_change: Optional[float] = Field(default=None, description="风速变化")
    pressure_change: Optional[float] = Field(default=None, description="气压变化")


class GeographicRelationshipProperties(BaseModel):
    """地理关系属性模型"""
    min_distance_km: float = Field(..., ge=0, description="最小距离(公里)")
    passed_at: Optional[datetime] = Field(default=None, description="经过时间")
    impact_level: Optional[str] = Field(default=None, description="影响级别(low/medium/high)")


class GraphData(BaseModel):
    """图谱数据统一模型"""
    typhoon_id: str = Field(..., description="中心台风编号")
    nodes: List[GraphNode] = Field(default_factory=list, description="节点列表")
    links: List[GraphLink] = Field(default_factory=list, description="关系列表")


NODE_TYPE_CONFIG = {
    NodeType.TYPHOON: {
        "label": "台风",
        "color": "#ff6b6b",
        "symbol_size": 60,
        "id_field": "typhoon_id",
        "display_field": "name_cn"
    },
    NodeType.PATH_POINT: {
        "label": "路径点",
        "color": "#4ecdc4",
        "symbol_size": 30,
        "id_field": "typhoon_id",
        "display_field": "sequence"
    },
    NodeType.LOCATION: {
        "label": "地理位置",
        "color": "#45b7d1",
        "symbol_size": 45,
        "id_field": "name",
        "display_field": "name"
    },
    NodeType.TIME: {
        "label": "时间",
        "color": "#96ceb4",
        "symbol_size": 40,
        "id_field": "year",
        "display_field": "year"
    },
    NodeType.INTENSITY: {
        "label": "强度等级",
        "color": "#ffeaa7",
        "symbol_size": 45,
        "id_field": "level",
        "display_field": "name_cn"
    }
}


RELATIONSHIP_TYPE_CONFIG = {
    # 基础关系
    RelationshipType.HAS_PATH_POINT: {
        "label": "拥有路径点",
        "color": "#ff6b6b",
        "description": "台风与路径点之间的关系"
    },
    RelationshipType.NEXT: {
        "label": "路径顺序",
        "color": "#4ecdc4",
        "description": "路径点之间的顺序关系"
    },
    RelationshipType.OCCURRED_IN: {
        "label": "发生时间",
        "color": "#45b7d1",
        "description": "台风与时间节点的关系"
    },
    RelationshipType.LANDED_AT: {
        "label": "登陆地点",
        "color": "#96ceb4",
        "description": "台风与登陆地点的关系"
    },
    RelationshipType.REACHED_INTENSITY: {
        "label": "达到强度",
        "color": "#ffeaa7",
        "description": "台风与强度等级的关系"
    },
    # 扩展关系 - 台风生命周期
    RelationshipType.GENERATED_AT: {
        "label": "生成于",
        "color": "#74b9ff",
        "description": "台风生成位置"
    },
    RelationshipType.DISSIPATED_AT: {
        "label": "消散于",
        "color": "#a29bfe",
        "description": "台风消散位置"
    },
    # 扩展关系 - 强度变化
    RelationshipType.INTENSIFIED_TO: {
        "label": "增强为",
        "color": "#fd79a8",
        "description": "台风强度增强"
    },
    RelationshipType.WEAKENED_TO: {
        "label": "减弱为",
        "color": "#fdcb6e",
        "description": "台风强度减弱"
    },
    # 扩展关系 - 相似性
    RelationshipType.SIMILAR_TO: {
        "label": "相似于",
        "color": "#6c5ce7",
        "description": "台风相似性关系"
    },
    # 扩展关系 - 地理影响
    RelationshipType.AFFECTED_AREA: {
        "label": "影响区域",
        "color": "#e17055",
        "description": "台风影响的地理区域"
    },
    RelationshipType.PASSED_NEAR: {
        "label": "经过附近",
        "color": "#00b894",
        "description": "台风经过某地附近"
    }
}


def get_node_id(node_type: NodeType, properties: Dict[str, Any]) -> str:
    """
    根据节点类型和属性生成唯一节点ID

    Args:
        node_type: 节点类型
        properties: 节点属性字典

    Returns:
        str: 节点唯一标识
    """
    if node_type == NodeType.TYPHOON:
        return properties.get("typhoon_id", "")
    elif node_type == NodeType.PATH_POINT:
        typhoon_id = properties.get("typhoon_id", "unknown")
        sequence = properties.get("sequence", 0)
        return f"{typhoon_id}_pp_{sequence}"
    elif node_type == NodeType.LOCATION:
        name = properties.get("name", "unknown")
        return f"location_{name}"
    elif node_type == NodeType.TIME:
        year = properties.get("year", 0)
        return f"time_{year}"
    elif node_type == NodeType.INTENSITY:
        level = properties.get("level", "unknown")
        return f"intensity_{level}"
    return str(id(properties))


def detect_node_type(properties: Dict[str, Any]) -> NodeType:
    """
    根据属性自动检测节点类型

    Args:
        properties: 节点属性字典

    Returns:
        NodeType: 检测到的节点类型
    """
    if "typhoon_id" in properties and "name_cn" in properties:
        return NodeType.TYPHOON
    elif "sequence" in properties and "lat" in properties:
        return NodeType.PATH_POINT
    elif "name" in properties and "lat" in properties and "lon" in properties:
        if "type" in properties:
            return NodeType.LOCATION
    if "year" in properties and "is_peak_season" in properties:
        return NodeType.TIME
    elif "level" in properties and "wind_speed_min" in properties:
        return NodeType.INTENSITY
    return NodeType.TYPHOON


def validate_relationship(
    source_type: NodeType,
    target_type: NodeType,
    relationship_type: RelationshipType
) -> bool:
    """
    验证关系类型是否合法

    Args:
        source_type: 源节点类型
        target_type: 目标节点类型
        relationship_type: 关系类型

    Returns:
        bool: 关系是否合法
    """
    valid_relationships = {
        # 基础关系
        (NodeType.TYPHOON, NodeType.PATH_POINT, RelationshipType.HAS_PATH_POINT),
        (NodeType.PATH_POINT, NodeType.PATH_POINT, RelationshipType.NEXT),
        (NodeType.TYPHOON, NodeType.TIME, RelationshipType.OCCURRED_IN),
        (NodeType.TYPHOON, NodeType.LOCATION, RelationshipType.LANDED_AT),
        (NodeType.TYPHOON, NodeType.INTENSITY, RelationshipType.REACHED_INTENSITY),
        # 扩展关系 - 台风生命周期
        (NodeType.TYPHOON, NodeType.LOCATION, RelationshipType.GENERATED_AT),
        (NodeType.TYPHOON, NodeType.LOCATION, RelationshipType.DISSIPATED_AT),
        # 扩展关系 - 强度变化
        (NodeType.TYPHOON, NodeType.INTENSITY, RelationshipType.INTENSIFIED_TO),
        (NodeType.TYPHOON, NodeType.INTENSITY, RelationshipType.WEAKENED_TO),
        # 扩展关系 - 相似性
        (NodeType.TYPHOON, NodeType.TYPHOON, RelationshipType.SIMILAR_TO),
        # 扩展关系 - 地理影响
        (NodeType.TYPHOON, NodeType.LOCATION, RelationshipType.AFFECTED_AREA),
        (NodeType.TYPHOON, NodeType.LOCATION, RelationshipType.PASSED_NEAR),
    }
    return (source_type, target_type, relationship_type) in valid_relationships
