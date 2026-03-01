"""
知识图谱 API 路由
提供台风知识图谱的检索和分析接口

接口列表:
- POST /kg/search - 智能搜索
- POST /kg/similar - 查找相似台风
- GET /kg/typhoon/{typhoon_id} - 获取台风详情
- GET /kg/typhoon/{typhoon_id}/path - 获取台风路径
- GET /kg/typhoon/{typhoon_id}/relationships - 获取关系网络
- GET /kg/statistics/yearly - 年度统计
- GET /kg/statistics/intensity - 强度分布统计
- POST /kg/compare - 对比多个台风
- GET /kg/config - 获取图谱配置信息
- GET /kg/health - 健康检查
"""
import logging
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field, field_validator

# 配置日志
logger = logging.getLogger(__name__)

from app.services.knowledge_graph import (
    KnowledgeGraphQueryEngine,
    QueryType,
    TyphoonSimilarityCalculator
)
from app.core.neo4j_client import neo4j_client
from app.models.knowledge_graph import (
    NodeType,
    RelationshipType,
    GraphNode,
    GraphLink,
    GraphData,
    NODE_TYPE_CONFIG,
    RELATIONSHIP_TYPE_CONFIG,
    get_node_id,
    detect_node_type,
    IntensityLevel,
    INTENSITY_LEVELS
)

router = APIRouter(prefix="/kg", tags=["Knowledge Graph"])

query_engine = KnowledgeGraphQueryEngine()
similarity_calculator = TyphoonSimilarityCalculator()


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索查询", min_length=1, max_length=100)
    query_type: Optional[Literal["exact", "fuzzy", "similarity", "temporal"]] = Field(
        default=None, description="查询类型，不传则自动判断"
    )
    year: Optional[int] = Field(default=None, ge=1949, le=2100, description="过滤年份")
    location: Optional[str] = Field(default=None, max_length=50, description="过滤地点")
    limit: int = Field(default=20, ge=1, le=100, description="返回数量限制")


class SearchResponse(BaseModel):
    """搜索响应模型"""
    typhoon_id: str = Field(..., description="台风编号")
    name_cn: str = Field(default="", description="中文名称")
    name_en: str = Field(default="", description="英文名称")
    year: int = Field(..., description="年份")
    score: float = Field(..., ge=0, le=1, description="匹配得分")
    max_wind_speed: float = Field(default=0.0, ge=0, description="最大风速(m/s)")
    total_path_points: int = Field(default=0, ge=0, description="路径点总数")
    landfall_locations: List[str] = Field(default_factory=list, description="登陆地点列表")


class SimilarityRequest(BaseModel):
    """相似性查询请求模型"""
    typhoon_id: str = Field(..., description="参考台风编号")
    location: Optional[str] = Field(default=None, max_length=50, description="限定登陆地点")
    min_similarity: float = Field(default=0.5, ge=0, le=1, description="最小相似度")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量")

    @field_validator('typhoon_id')
    @classmethod
    def validate_typhoon_id(cls, v: str) -> str:
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError('台风编号必须是6位数字（YYYYMM格式）')
        return v


class SimilarityResponse(BaseModel):
    """相似性查询响应模型"""
    typhoon_id: str = Field(..., description="台风编号")
    name_cn: str = Field(default="", description="中文名称")
    name_en: str = Field(default="", description="英文名称")
    year: int = Field(..., description="年份")
    max_wind_speed: float = Field(default=0.0, ge=0, description="最大风速(m/s)")
    similarity_score: float = Field(..., ge=0, le=1, description="相似度得分")


class TyphoonDetailResponse(BaseModel):
    """台风详情响应模型"""
    typhoon_id: str = Field(..., description="台风编号")
    name_cn: str = Field(default="", description="中文名称")
    name_en: str = Field(default="", description="英文名称")
    year: int = Field(..., description="年份")
    max_wind_speed: float = Field(default=0.0, ge=0, description="最大风速(m/s)")
    min_pressure: float = Field(default=9999.0, ge=0, description="最低气压(hPa)")
    total_path_points: int = Field(default=0, ge=0, description="路径点总数")
    duration_hours: int = Field(default=0, ge=0, description="持续时长(小时)")
    start_lat: float = Field(default=0.0, ge=-90, le=90, description="起始纬度")
    start_lon: float = Field(default=0.0, ge=-180, le=180, description="起始经度")
    end_lat: float = Field(default=0.0, ge=-90, le=90, description="结束纬度")
    end_lon: float = Field(default=0.0, ge=-180, le=180, description="结束经度")
    is_peak_season: bool = Field(default=False, description="是否台风高发期")
    landfall_locations: List[str] = Field(default_factory=list, description="登陆地点列表")
    intensity_level: Optional[str] = Field(default=None, description="强度等级代码")
    intensity_name: Optional[str] = Field(default=None, description="强度等级名称")


class PathPointResponse(BaseModel):
    """路径点响应模型"""
    sequence: int = Field(..., ge=1, description="序列号")
    lat: float = Field(..., ge=-90, le=90, description="纬度")
    lon: float = Field(..., ge=-180, le=180, description="经度")
    timestamp: Optional[str] = Field(default=None, description="时间戳")
    pressure: Optional[float] = Field(default=None, ge=0, description="中心气压(hPa)")
    wind_speed: Optional[float] = Field(default=None, ge=0, description="最大风速(m/s)")
    moving_direction: Optional[str] = Field(default=None, description="移动方向")
    moving_speed: Optional[float] = Field(default=None, ge=0, description="移动速度(km/h)")
    intensity: Optional[str] = Field(default=None, description="强度等级")


class CompareRequest(BaseModel):
    """对比请求模型"""
    typhoon_ids: List[str] = Field(..., min_length=2, max_length=5, description="要对比的台风编号列表")

    @field_validator('typhoon_ids')
    @classmethod
    def validate_typhoon_ids(cls, v: List[str]) -> List[str]:
        for tid in v:
            if not tid or len(tid) != 6 or not tid.isdigit():
                raise ValueError(f'台风编号必须是6位数字（YYYYMM格式），无效编号: {tid}')
        return v


class CompareTyphoonData(BaseModel):
    """对比台风数据模型"""
    typhoon_id: str = Field(..., description="台风编号")
    name_cn: str = Field(default="", description="中文名称")
    year: int = Field(..., description="年份")
    max_wind_speed: float = Field(default=0.0, ge=0, description="最大风速(m/s)")
    total_path_points: int = Field(default=0, ge=0, description="路径点总数")
    duration_hours: int = Field(default=0, ge=0, description="持续时长(小时)")
    intensity: Optional[str] = Field(default=None, description="强度等级名称")


class CompareResponse(BaseModel):
    """对比响应模型"""
    typhoons: List[CompareTyphoonData] = Field(..., description="台风数据列表")
    similarity_matrix: List[List[float]] = Field(..., description="相似度矩阵")


class YearlyStatistics(BaseModel):
    """年度统计响应模型"""
    year: int = Field(..., description="年份")
    total_typhoons: int = Field(default=0, ge=0, description="台风总数")
    total_landfalls: int = Field(default=0, ge=0, description="登陆总数")
    avg_max_wind: float = Field(default=0.0, ge=0, description="平均最大风速(m/s)")
    strongest_wind: float = Field(default=0.0, ge=0, description="最强风速(m/s)")
    strongest_typhoon: Optional[str] = Field(default=None, description="最强台风名称")


class IntensityDistributionItem(BaseModel):
    """强度分布项模型"""
    level: str = Field(..., description="强度等级代码")
    name: str = Field(..., description="强度等级名称")
    count: int = Field(default=0, ge=0, description="台风数量")
    avg_wind_speed: float = Field(default=0.0, ge=0, description="平均风速(m/s)")


class IntensityStatisticsResponse(BaseModel):
    """强度统计响应模型"""
    year: Optional[int] = Field(default=None, description="筛选年份")
    distribution: List[IntensityDistributionItem] = Field(default_factory=list, description="强度分布")


class NodeTypeConfig(BaseModel):
    """节点类型配置模型"""
    type: str = Field(..., description="节点类型代码")
    label: str = Field(..., description="节点类型名称")
    color: str = Field(..., description="节点颜色")
    symbol_size: int = Field(..., ge=10, le=100, description="节点大小")


class RelationshipTypeConfig(BaseModel):
    """关系类型配置模型"""
    type: str = Field(..., description="关系类型代码")
    label: str = Field(..., description="关系类型名称")
    color: str = Field(..., description="关系颜色")
    description: str = Field(default="", description="关系描述")


class GraphConfigResponse(BaseModel):
    """图谱配置响应模型"""
    node_types: List[NodeTypeConfig] = Field(..., description="节点类型配置列表")
    relationship_types: List[RelationshipTypeConfig] = Field(..., description="关系类型配置列表")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    neo4j_connected: bool = Field(default=False, description="Neo4j连接状态")
    database_info: Optional[Dict[str, Any]] = Field(default=None, description="数据库信息")
    statistics: Optional[Dict[str, int]] = Field(default=None, description="统计信息")
    error: Optional[str] = Field(default=None, description="错误信息")


@router.post("/search", response_model=List[SearchResponse])
async def search_typhoons(request: SearchRequest):
    """
    知识图谱智能搜索

    支持多种查询类型:
    - exact: 精确查询（台风编号、名称）
    - fuzzy: 模糊查询（名称部分匹配）
    - similarity: 相似性查询（查找路径相似的台风）
    - temporal: 时序查询（按年份查询）

    不传 query_type 时自动判断
    """
    query_type = None
    if request.query_type:
        type_map = {
            "exact": QueryType.EXACT,
            "fuzzy": QueryType.FUZZY,
            "similarity": QueryType.SIMILARITY,
            "temporal": QueryType.TEMPORAL
        }
        query_type = type_map.get(request.query_type)

    filters = {}
    if request.year:
        filters["year"] = request.year
    if request.location:
        filters["location"] = request.location

    try:
        results = await query_engine.search(
            query=request.query,
            query_type=query_type,
            filters=filters,
            limit=request.limit
        )

        return [
            SearchResponse(
                typhoon_id=r.typhoon_id,
                name_cn=r.name_cn,
                name_en=r.name_en,
                year=r.year,
                score=r.score,
                max_wind_speed=r.max_wind_speed,
                total_path_points=r.total_path_points,
                landfall_locations=r.matched_fields.get("landfall_locations", [])
            )
            for r in results
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}"
        )


@router.post("/similar", response_model=List[SimilarityResponse])
async def find_similar_typhoons(request: SimilarityRequest):
    """
    查找相似台风

    基于路径几何形状、生成位置、强度变化等特征
    计算台风之间的综合相似度
    """
    try:
        results = await query_engine.find_similar_path_typhoons(
            typhoon_id=request.typhoon_id,
            location=request.location,
            limit=request.limit
        )

        filtered_results = [
            r for r in results
            if r.get("similarity_score", 0) >= request.min_similarity
        ]

        response = []
        for r in filtered_results:
            response.append(SimilarityResponse(
                typhoon_id=r["typhoon_id"],
                name_cn=r.get("name_cn", ""),
                name_en=r.get("name_en", ""),
                year=r.get("year", 0),
                max_wind_speed=r.get("max_wind_speed", 0.0),
                similarity_score=r.get("similarity_score", 0.0)
            ))

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查找相似台风失败: {str(e)}"
        )


@router.get("/typhoon/{typhoon_id}", response_model=TyphoonDetailResponse)
async def get_typhoon_detail(typhoon_id: str):
    """
    获取台风详细信息
    """
    if not typhoon_id or len(typhoon_id) != 6 or not typhoon_id.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="台风编号必须是6位数字（YYYYMM格式）"
        )

    try:
        detail = await query_engine.get_typhoon_details(typhoon_id)

        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"台风 {typhoon_id} 不存在"
            )

        return TyphoonDetailResponse(
            typhoon_id=detail["typhoon_id"],
            name_cn=detail.get("name_cn", ""),
            name_en=detail.get("name_en", ""),
            year=detail.get("year", 0),
            max_wind_speed=detail.get("max_wind_speed", 0.0),
            min_pressure=detail.get("min_pressure", 9999.0),
            total_path_points=detail.get("total_path_points", 0),
            duration_hours=detail.get("duration_hours", 0),
            start_lat=detail.get("start_lat", 0.0),
            start_lon=detail.get("start_lon", 0.0),
            end_lat=detail.get("end_lat", 0.0),
            end_lon=detail.get("end_lon", 0.0),
            is_peak_season=detail.get("is_peak_season", False),
            landfall_locations=detail.get("landfall_locations", []),
            intensity_level=detail.get("intensity_level"),
            intensity_name=detail.get("intensity_name")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取台风详情失败: {str(e)}"
        )


@router.get("/typhoon/{typhoon_id}/path", response_model=List[PathPointResponse])
async def get_typhoon_path(typhoon_id: str):
    """
    获取台风路径数据

    返回按序列排序的路径点列表
    """
    if not typhoon_id or len(typhoon_id) != 6 or not typhoon_id.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="台风编号必须是6位数字（YYYYMM格式）"
        )

    try:
        path = await query_engine.get_typhoon_path(typhoon_id)

        if not path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"台风 {typhoon_id} 的路径数据不存在"
            )

        response = []
        for p in path:
            response.append(PathPointResponse(
                sequence=p["sequence"],
                lat=p["lat"],
                lon=p["lon"],
                timestamp=str(p["timestamp"]) if p.get("timestamp") else None,
                pressure=p.get("pressure"),
                wind_speed=p.get("wind_speed"),
                moving_direction=p.get("moving_direction"),
                moving_speed=p.get("moving_speed"),
                intensity=p.get("intensity")
            ))

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取台风路径失败: {str(e)}"
        )


@router.get("/typhoon/{typhoon_id}/relationships", response_model=GraphData)
async def get_typhoon_relationships(
    typhoon_id: str,
    depth: int = Query(default=2, ge=1, le=3, description="关系深度")
):
    """
    获取台风关联网络

    返回台风与其他实体（地点、强度、时间等）的关系网络
    """
    if not typhoon_id or len(typhoon_id) != 6 or not typhoon_id.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="台风编号必须是6位数字（YYYYMM格式）"
        )

    try:
        # 只查询基础关系类型，避免查询可能不存在的扩展关系类型
        # 扩展关系(GENERATED_AT, DISSIPATED_AT等)需要运行 import_full_data.py 才会创建
        base_cypher = """
            MATCH (t:Typhoon {typhoon_id: $typhoon_id})
            // 基础关系 - 这些关系在基础数据导入时就会创建
            OPTIONAL MATCH (t)-[r1:HAS_PATH_POINT]->(pp:PathPoint)
            OPTIONAL MATCH (t)-[r2:LANDED_AT]->(l:Location)
            OPTIONAL MATCH (t)-[r3:REACHED_INTENSITY]->(i:Intensity)
            OPTIONAL MATCH (t)-[r4:OCCURRED_IN]->(tm:Time)
            // 扩展关系 - 使用动态关系类型查询，避免Neo4j警告
            // 生成位置关系 (如果存在)
            OPTIONAL MATCH (t)-[r6]->(gen_loc:Location)
            WHERE type(r6) = 'GENERATED_AT'
            // 消散位置关系 (如果存在)
            OPTIONAL MATCH (t)-[r7]->(dis_loc:Location)
            WHERE type(r7) = 'DISSIPATED_AT'
            // 强度增强关系 (如果存在)
            OPTIONAL MATCH (t)-[r8]->(int_up:Intensity)
            WHERE type(r8) = 'INTENSIFIED_TO'
            // 强度减弱关系 (如果存在)
            OPTIONAL MATCH (t)-[r9]->(int_down:Intensity)
            WHERE type(r9) = 'WEAKENED_TO'
            // 相似性关系 (如果存在)
            OPTIONAL MATCH (t)-[r10]->(sim_t:Typhoon)
            WHERE type(r10) = 'SIMILAR_TO'
            // 影响区域关系 (如果存在)
            OPTIONAL MATCH (t)-[r11]->(aff_loc:Location)
            WHERE type(r11) = 'AFFECTED_AREA'
            // 经过附近关系 (如果存在)
            OPTIONAL MATCH (t)-[r12]->(pass_loc:Location)
            WHERE type(r12) = 'PASSED_NEAR'
        """

        if depth >= 2:
            base_cypher += """
            OPTIONAL MATCH (pp)-[r5:NEXT]->(pp2:PathPoint)
            """
        
        base_cypher += """
            WITH t, pp, l, i, tm, gen_loc, dis_loc, int_up, int_down, sim_t, aff_loc, pass_loc"""
        
        if depth >= 2:
            base_cypher += ", pp2"
        
        base_cypher += """
            RETURN 
                t as typhoon_node,
                // 节点集合
                [p IN collect(DISTINCT pp) WHERE p IS NOT NULL] as path_points,
                [loc IN collect(DISTINCT l) WHERE loc IS NOT NULL] as locations,
                [int IN collect(DISTINCT i) WHERE int IS NOT NULL] as intensities,
                [time IN collect(DISTINCT tm) WHERE time IS NOT NULL] as times,
                [gen IN collect(DISTINCT gen_loc) WHERE gen IS NOT NULL] as gen_locations,
                [dis IN collect(DISTINCT dis_loc) WHERE dis IS NOT NULL] as dis_locations,
                [intu IN collect(DISTINCT int_up) WHERE intu IS NOT NULL] as intensified_ints,
                [intd IN collect(DISTINCT int_down) WHERE intd IS NOT NULL] as weakened_ints,
                [st IN collect(DISTINCT sim_t) WHERE st IS NOT NULL] as similar_typhoons,
                [aff IN collect(DISTINCT aff_loc) WHERE aff IS NOT NULL] as affected_locations,
                [pass IN collect(DISTINCT pass_loc) WHERE pass IS NOT NULL] as passed_locations,
                // 基础关系
                [r IN collect(DISTINCT {start: t.typhoon_id, rel: 'HAS_PATH_POINT', end: CASE WHEN pp IS NOT NULL AND pp.typhoon_id IS NOT NULL AND pp.sequence IS NOT NULL THEN pp.typhoon_id + '_pp_' + pp.sequence ELSE NULL END}) WHERE r.end IS NOT NULL] as has_path_rels,
                [r IN collect(DISTINCT {start: t.typhoon_id, rel: 'LANDED_AT', end: CASE WHEN l IS NOT NULL AND l.name IS NOT NULL THEN 'location_' + l.name ELSE NULL END}) WHERE r.end IS NOT NULL] as landed_rels,
                [r IN collect(DISTINCT {start: t.typhoon_id, rel: 'REACHED_INTENSITY', end: CASE WHEN i IS NOT NULL AND i.level IS NOT NULL THEN 'intensity_' + i.level ELSE NULL END}) WHERE r.end IS NOT NULL] as intensity_rels,
                [r IN collect(DISTINCT {start: t.typhoon_id, rel: 'OCCURRED_IN', end: CASE WHEN tm IS NOT NULL AND tm.year IS NOT NULL THEN 'time_' + tm.year ELSE NULL END}) WHERE r.end IS NOT NULL] as time_rels,
                // 扩展关系 - 生命周期
                [r IN collect(DISTINCT {start: t.typhoon_id, rel: 'GENERATED_AT', end: CASE WHEN gen_loc IS NOT NULL AND gen_loc.name IS NOT NULL THEN 'location_' + gen_loc.name ELSE NULL END}) WHERE r.end IS NOT NULL] as generated_rels,
                [r IN collect(DISTINCT {start: t.typhoon_id, rel: 'DISSIPATED_AT', end: CASE WHEN dis_loc IS NOT NULL AND dis_loc.name IS NOT NULL THEN 'location_' + dis_loc.name ELSE NULL END}) WHERE r.end IS NOT NULL] as dissipated_rels,
                // 扩展关系 - 强度变化
                [r IN collect(DISTINCT {start: t.typhoon_id, rel: 'INTENSIFIED_TO', end: CASE WHEN int_up IS NOT NULL AND int_up.level IS NOT NULL THEN 'intensity_' + int_up.level ELSE NULL END}) WHERE r.end IS NOT NULL] as intensified_rels,
                [r IN collect(DISTINCT {start: t.typhoon_id, rel: 'WEAKENED_TO', end: CASE WHEN int_down IS NOT NULL AND int_down.level IS NOT NULL THEN 'intensity_' + int_down.level ELSE NULL END}) WHERE r.end IS NOT NULL] as weakened_rels,
                // 扩展关系 - 相似性
                [r IN collect(DISTINCT {start: t.typhoon_id, rel: 'SIMILAR_TO', end: CASE WHEN sim_t IS NOT NULL AND sim_t.typhoon_id IS NOT NULL THEN sim_t.typhoon_id ELSE NULL END}) WHERE r.end IS NOT NULL] as similar_rels,
                // 扩展关系 - 地理影响
                [r IN collect(DISTINCT {start: t.typhoon_id, rel: 'AFFECTED_AREA', end: CASE WHEN aff_loc IS NOT NULL AND aff_loc.name IS NOT NULL THEN 'location_' + aff_loc.name ELSE NULL END}) WHERE r.end IS NOT NULL] as affected_rels,
                [r IN collect(DISTINCT {start: t.typhoon_id, rel: 'PASSED_NEAR', end: CASE WHEN pass_loc IS NOT NULL AND pass_loc.name IS NOT NULL THEN 'location_' + pass_loc.name ELSE NULL END}) WHERE r.end IS NOT NULL] as passed_rels
        """

        if depth >= 2:
            base_cypher += """,
                [r IN collect(DISTINCT {start: CASE WHEN pp IS NOT NULL AND pp.typhoon_id IS NOT NULL AND pp.sequence IS NOT NULL THEN pp.typhoon_id + '_pp_' + pp.sequence ELSE NULL END, rel: 'NEXT', end: CASE WHEN pp2 IS NOT NULL AND pp2.typhoon_id IS NOT NULL AND pp2.sequence IS NOT NULL THEN pp2.typhoon_id + '_pp_' + pp2.sequence ELSE NULL END}) WHERE r.start IS NOT NULL AND r.end IS NOT NULL] as next_rels
            """
        else:
            base_cypher += """,
                [] as next_rels
            """

        result = await neo4j_client.run(base_cypher, {"typhoon_id": typhoon_id})

        if not result:
            return GraphData(
                typhoon_id=typhoon_id,
                nodes=[],
                links=[]
            )

        record = result[0]

        nodes: Dict[str, GraphNode] = {}
        links: List[GraphLink] = []
        link_keys = set()

        def add_node(node_data: dict, node_type: NodeType):
            if not node_data or not isinstance(node_data, dict):
                return None
            node_id = get_node_id(node_type, node_data)
            if node_id and node_id not in nodes:
                nodes[node_id] = GraphNode(
                    id=node_id,
                    labels=[node_type.value],
                    properties=node_data
                )
            return node_id

        def add_link(source_id: str, rel_type_str: str, target_id: str):
            if not source_id or not target_id or source_id == target_id:
                return
            link_key = f"{source_id}-{rel_type_str}-{target_id}"
            if link_key not in link_keys:
                try:
                    rel = RelationshipType(rel_type_str)
                    link_keys.add(link_key)
                    links.append(GraphLink(
                        source=source_id,
                        target=target_id,
                        type=rel,
                        properties={}
                    ))
                except ValueError:
                    pass

        typhoon_node = record.get("typhoon_node")
        if typhoon_node:
            add_node(typhoon_node, NodeType.TYPHOON)

        for pp in record.get("path_points", []):
            if pp:
                add_node(pp, NodeType.PATH_POINT)

        for loc in record.get("locations", []):
            if loc:
                add_node(loc, NodeType.LOCATION)

        for intensity in record.get("intensities", []):
            if intensity:
                add_node(intensity, NodeType.INTENSITY)

        for tm in record.get("times", []):
            if tm:
                add_node(tm, NodeType.TIME)

        # 添加新节点类型
        for gen_loc in record.get("gen_locations", []):
            if gen_loc:
                add_node(gen_loc, NodeType.LOCATION)

        for dis_loc in record.get("dis_locations", []):
            if dis_loc:
                add_node(dis_loc, NodeType.LOCATION)

        for sim_t in record.get("similar_typhoons", []):
            if sim_t:
                add_node(sim_t, NodeType.TYPHOON)

        for aff_loc in record.get("affected_locations", []):
            if aff_loc:
                add_node(aff_loc, NodeType.LOCATION)

        for pass_loc in record.get("passed_locations", []):
            if pass_loc:
                add_node(pass_loc, NodeType.LOCATION)

        # 添加基础关系
        for rel_data in record.get("has_path_rels", []):
            if rel_data and rel_data.get("start") and rel_data.get("end"):
                add_link(rel_data["start"], rel_data["rel"], rel_data["end"])

        for rel_data in record.get("landed_rels", []):
            if rel_data and rel_data.get("start") and rel_data.get("end"):
                add_link(rel_data["start"], rel_data["rel"], rel_data["end"])

        for rel_data in record.get("intensity_rels", []):
            if rel_data and rel_data.get("start") and rel_data.get("end"):
                add_link(rel_data["start"], rel_data["rel"], rel_data["end"])

        for rel_data in record.get("time_rels", []):
            if rel_data and rel_data.get("start") and rel_data.get("end"):
                add_link(rel_data["start"], rel_data["rel"], rel_data["end"])

        for rel_data in record.get("next_rels", []):
            if rel_data and rel_data.get("start") and rel_data.get("end"):
                add_link(rel_data["start"], rel_data["rel"], rel_data["end"])

        # 添加扩展关系
        for rel_data in record.get("generated_rels", []):
            if rel_data and rel_data.get("start") and rel_data.get("end"):
                add_link(rel_data["start"], rel_data["rel"], rel_data["end"])

        for rel_data in record.get("dissipated_rels", []):
            if rel_data and rel_data.get("start") and rel_data.get("end"):
                add_link(rel_data["start"], rel_data["rel"], rel_data["end"])

        for rel_data in record.get("intensified_rels", []):
            if rel_data and rel_data.get("start") and rel_data.get("end"):
                add_link(rel_data["start"], rel_data["rel"], rel_data["end"])

        for rel_data in record.get("weakened_rels", []):
            if rel_data and rel_data.get("start") and rel_data.get("end"):
                add_link(rel_data["start"], rel_data["rel"], rel_data["end"])

        for rel_data in record.get("similar_rels", []):
            if rel_data and rel_data.get("start") and rel_data.get("end"):
                add_link(rel_data["start"], rel_data["rel"], rel_data["end"])

        for rel_data in record.get("affected_rels", []):
            if rel_data and rel_data.get("start") and rel_data.get("end"):
                add_link(rel_data["start"], rel_data["rel"], rel_data["end"])

        for rel_data in record.get("passed_rels", []):
            if rel_data and rel_data.get("start") and rel_data.get("end"):
                add_link(rel_data["start"], rel_data["rel"], rel_data["end"])

        return GraphData(
            typhoon_id=typhoon_id,
            nodes=list(nodes.values()),
            links=links
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取关系网络失败: {str(e)}"
        )


@router.get("/statistics/yearly", response_model=YearlyStatistics)
async def get_yearly_statistics(year: int = Query(..., ge=1949, le=2100, description="年份")):
    """
    获取年度统计信息
    """
    try:
        cypher = """
            MATCH (t:Typhoon {year: $year})
            OPTIONAL MATCH (t)-[:LANDED_AT]->(l:Location)
            OPTIONAL MATCH (t)-[:REACHED_INTENSITY]->(i:Intensity)
            RETURN count(t) as total_typhoons,
                   count(l) as total_landfalls,
                   avg(t.max_wind_speed) as avg_max_wind,
                   max(t.max_wind_speed) as strongest_wind,
                   collect(CASE WHEN t.max_wind_speed = max_wind THEN t.name_cn END)[0] as strongest_typhoon
        """

        result = await neo4j_client.run(cypher, {"year": year})

        if not result or result[0]["total_typhoons"] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{year}年没有台风数据"
            )

        data = result[0]

        return YearlyStatistics(
            year=year,
            total_typhoons=data["total_typhoons"],
            total_landfalls=data["total_landfalls"],
            avg_max_wind=round(data["avg_max_wind"] or 0, 2),
            strongest_wind=data["strongest_wind"] or 0,
            strongest_typhoon=data.get("strongest_typhoon")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取年度统计失败: {str(e)}"
        )


@router.get("/statistics/intensity", response_model=IntensityStatisticsResponse)
async def get_intensity_statistics(year: Optional[int] = Query(default=None, ge=1949, le=2100, description="年份")):
    """
    获取强度分布统计
    """
    try:
        cypher = """
            MATCH (t:Typhoon)-[:REACHED_INTENSITY]->(i:Intensity)
        """

        if year:
            cypher += " WHERE t.year = $year"

        cypher += """
            RETURN i.level as intensity_level,
                   i.name_cn as intensity_name,
                   count(t) as count,
                   avg(t.max_wind_speed) as avg_wind_speed
            ORDER BY count DESC
        """

        params = {"year": year} if year else {}
        results = await neo4j_client.run(cypher, params)

        distribution = [
            IntensityDistributionItem(
                level=r["intensity_level"],
                name=r["intensity_name"],
                count=r["count"],
                avg_wind_speed=round(r["avg_wind_speed"] or 0, 2)
            )
            for r in results
        ]

        return IntensityStatisticsResponse(
            year=year,
            distribution=distribution
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取强度统计失败: {str(e)}"
        )


@router.post("/compare", response_model=CompareResponse)
async def compare_typhoons(request: CompareRequest):
    """
    对比多个台风

    返回各台风的关键指标对比
    """
    try:
        comparison_data = []

        for typhoon_id in request.typhoon_ids:
            detail = await query_engine.get_typhoon_details(typhoon_id)
            if detail:
                comparison_data.append(CompareTyphoonData(
                    typhoon_id=detail["typhoon_id"],
                    name_cn=detail.get("name_cn", ""),
                    year=detail.get("year", 0),
                    max_wind_speed=detail.get("max_wind_speed", 0.0),
                    total_path_points=detail.get("total_path_points", 0),
                    duration_hours=detail.get("duration_hours", 0),
                    intensity=detail.get("intensity_name")
                ))

        if len(comparison_data) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要2个有效的台风进行对比"
            )

        similarity_matrix = []
        for i, typhoon_a in enumerate(comparison_data):
            row = []
            for j, typhoon_b in enumerate(comparison_data):
                if i == j:
                    row.append(1.0)
                elif i < j:
                    sim_result = await similarity_calculator.calculate_similarity(
                        typhoon_a.typhoon_id,
                        typhoon_b.typhoon_id
                    )
                    row.append(sim_result.get("similarity", 0.0))
                else:
                    row.append(similarity_matrix[j][i])
            similarity_matrix.append(row)

        return CompareResponse(
            typhoons=comparison_data,
            similarity_matrix=similarity_matrix
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"对比台风失败: {str(e)}"
        )


@router.get("/config", response_model=GraphConfigResponse)
async def get_graph_config():
    """
    获取知识图谱配置信息

    返回节点类型和关系类型的配置信息，供前端使用
    """
    node_types = [
        NodeTypeConfig(
            type=nt.value,
            label=config["label"],
            color=config["color"],
            symbol_size=config["symbol_size"]
        )
        for nt, config in NODE_TYPE_CONFIG.items()
    ]

    relationship_types = [
        RelationshipTypeConfig(
            type=rt.value,
            label=config["label"],
            color=config["color"],
            description=config["description"]
        )
        for rt, config in RELATIONSHIP_TYPE_CONFIG.items()
    ]

    return GraphConfigResponse(
        node_types=node_types,
        relationship_types=relationship_types
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    知识图谱服务健康检查
    """
    try:
        connected = await neo4j_client.test_connection()

        if connected.get("connected"):
            stats = await neo4j_client.get_statistics()

            return HealthResponse(
                status="healthy",
                neo4j_connected=True,
                database_info=connected.get("database_info"),
                statistics=stats
            )
        else:
            return HealthResponse(
                status="unhealthy",
                neo4j_connected=False,
                error=connected.get("error")
            )

    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            error=str(e)
        )


# ==================== GraphRAG API ====================

from app.services.graphrag import GraphRAGEngine

# 初始化GraphRAG引擎
graphrag_engine = GraphRAGEngine(neo4j_client)


class GraphRAGSearchRequest(BaseModel):
    """GraphRAG搜索请求"""
    query: str = Field(..., description="用户查询")
    max_depth: int = Field(default=2, ge=1, le=4, description="遍历深度")
    max_nodes: int = Field(default=50, ge=10, le=200, description="最大节点数")
    relationship_types: Optional[List[str]] = Field(default=None, description="关系类型过滤")
    include_paths: bool = Field(default=True, description="是否包含路径信息")
    enable_quality_check: bool = Field(default=True, description="是否启用质量评估")
    use_semantic: bool = Field(default=True, description="是否使用语义搜索")


class SeedEntityResponse(BaseModel):
    """种子实体响应"""
    mention: str
    entity_id: str
    entity_type: str
    entity_name: str
    score: float
    match_type: str = Field(default="keyword", description="匹配类型: keyword, semantic, hybrid")


class GraphRAGSearchResponse(BaseModel):
    """GraphRAG搜索响应"""
    query: str
    seed_entities: List[SeedEntityResponse]
    subgraph: Dict[str, Any]
    context_text: str
    context_structured: Dict[str, Any]
    quality_score: float
    quality_level: str
    quality_factors: Dict[str, float]
    traversal_stats: Dict[str, Any]
    reasoning_paths: List[Dict[str, Any]]


@router.post("/graphrag/search", response_model=GraphRAGSearchResponse)
async def graphrag_search(request: GraphRAGSearchRequest):
    """
    GraphRAG LocalSearch 智能检索

    使用GraphRAG技术，基于知识图谱进行局部子图检索，返回结构化的上下文信息
    """
    try:
        result = await graphrag_engine.local_search(
            query=request.query,
            max_depth=request.max_depth,
            max_nodes=request.max_nodes,
            relationship_types=request.relationship_types,
            include_paths=request.include_paths,
            enable_quality_check=request.enable_quality_check,
            use_semantic=request.use_semantic
        )

        # 转换种子实体
        seed_entities = [
            SeedEntityResponse(
                mention=e.mention,
                entity_id=e.entity_id,
                entity_type=e.entity_type,
                entity_name=e.entity_name,
                score=e.score,
                match_type=getattr(e, 'match_type', 'keyword')
            )
            for e in result.seed_entities
        ]

        return GraphRAGSearchResponse(
            query=result.query,
            seed_entities=seed_entities,
            subgraph=result.subgraph,
            context_text=result.context_text,
            context_structured=result.context_structured,
            quality_score=result.quality_score,
            quality_level=result.quality_level,
            quality_factors=result.quality_result.get("factors", {}) if hasattr(result, "quality_result") else {},
            traversal_stats=result.traversal_stats,
            reasoning_paths=result.reasoning_paths
        )

    except Exception as e:
        logger.error(f"GraphRAG搜索失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GraphRAG搜索失败: {str(e)}"
        )
