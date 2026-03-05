"""
知识图谱查询引擎
提供台风数据的智能检索和查询功能

功能:
1. 精确查询 - 根据台风编号、名称精确查找
2. 模糊查询 - 支持名称模糊匹配
3. 相似性查询 - 查找路径相似的台风
4. 时序查询 - 按年份、月份等时间维度查询
5. 全文检索 - 使用Neo4j全文索引

严格按照知识图谱开发文档定义的节点类型和关系类型:
节点类型: Typhoon, PathPoint, Location, Time, Intensity
关系类型: HAS_PATH_POINT, NEXT, OCCURRED_IN, LANDED_AT, INTENSIFIED_TO, WEAKENED_TO
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from loguru import logger

from app.core.neo4j_client import neo4j_client
from app.core.config import settings
from app.models.knowledge_graph import (
    NodeType,
    RelationshipType,
    NODE_TYPE_CONFIG,
    RELATIONSHIP_TYPE_CONFIG
)


class QueryType(Enum):
    """查询类型枚举"""
    EXACT = "exact"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    SIMILARITY = "similarity"
    TEMPORAL = "temporal"


@dataclass
class SearchResult:
    """搜索结果数据类"""
    typhoon_id: str
    name_cn: str
    name_en: str
    year: int
    score: float
    max_wind_speed: float
    total_path_points: int
    matched_fields: Dict[str, Any]
    related_typhoons: List[str]


class KnowledgeGraphQueryEngine:
    """
    知识图谱查询引擎
    提供统一的台风数据检索接口
    """

    def __init__(self):
        self.default_limit = 20
        self.max_limit = 100

    async def search(
        self,
        query: str,
        query_type: QueryType = None,
        filters: Dict = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        统一搜索入口

        Args:
            query: 搜索查询字符串
            query_type: 查询类型，None时自动判断
            filters: 过滤条件（年份、地点等）
            limit: 返回结果数量限制

        Returns:
            List[SearchResult]: 搜索结果列表
        """
        filters = filters or {}
        limit = min(limit, self.max_limit)

        if query_type is None:
            query_type = self._detect_query_type(query)

        logger.info(f"执行搜索: type={query_type.value}, query={query}, filters={filters}")

        try:
            if query_type == QueryType.EXACT:
                results = await self._exact_search(query, filters, limit)
            elif query_type == QueryType.FUZZY:
                results = await self._fuzzy_search(query, filters, limit)
            elif query_type == QueryType.SIMILARITY:
                results = await self._similarity_search(query, filters, limit)
            elif query_type == QueryType.TEMPORAL:
                results = await self._temporal_search(query, filters, limit)
            else:
                results = await self._smart_search(query, filters, limit)

            return results

        except Exception as e:
            logger.error(f"搜索执行失败: {e}")
            return []

    def _detect_query_type(self, query: str) -> QueryType:
        """
        自动检测查询类型

        Args:
            query: 查询字符串

        Returns:
            QueryType: 检测到的查询类型
        """
        query = query.strip()

        if query.isdigit():
            if len(query) == 6:
                return QueryType.EXACT
            elif len(query) == 4:
                return QueryType.TEMPORAL

        if "年" in query or "year" in query.lower():
            return QueryType.TEMPORAL

        return QueryType.FUZZY

    async def _exact_search(
        self,
        query: str,
        filters: Dict,
        limit: int
    ) -> List[SearchResult]:
        """
        精确查询 - 根据台风编号或名称精确匹配
        使用知识图谱定义的节点属性进行查询
        """
        cypher = """
            MATCH (t:Typhoon)
            WHERE t.typhoon_id = $query
               OR t.name_cn = $query
               OR t.name_en = $query
            """

        where_conditions = []
        if filters.get("year"):
            where_conditions.append("t.year = $year")
        if filters.get("min_wind_speed"):
            where_conditions.append("t.max_wind_speed >= $min_wind_speed")

        if where_conditions:
            cypher += " AND " + " AND ".join(where_conditions)

        cypher += """
            OPTIONAL MATCH (t)-[:LANDED_AT]->(l:Location)
            RETURN t.typhoon_id as typhoon_id,
                   t.name_cn as name_cn,
                   t.name_en as name_en,
                   t.year as year,
                   t.max_wind_speed as max_wind_speed,
                   t.total_path_points as total_path_points,
                   collect(DISTINCT l.name) as landfall_locations
            LIMIT $limit
        """

        params = {
            "query": query,
            "limit": limit,
            **filters
        }

        results = await neo4j_client.run(cypher, params)
        return self._transform_results(results, score=1.0)

    async def _fuzzy_search(
        self,
        query: str,
        filters: Dict,
        limit: int
    ) -> List[SearchResult]:
        """
        模糊查询 - 支持名称的部分匹配
        """
        cypher = """
            MATCH (t:Typhoon)
            WHERE t.name_cn CONTAINS $query
               OR t.name_en CONTAINS $query
               OR t.typhoon_id CONTAINS $query
            """

        if filters.get("year"):
            cypher += " AND t.year = $year"
        if filters.get("min_wind_speed"):
            cypher += " AND t.max_wind_speed >= $min_wind_speed"

        cypher += """
            OPTIONAL MATCH (t)-[:LANDED_AT]->(l:Location)
            RETURN t.typhoon_id as typhoon_id,
                   t.name_cn as name_cn,
                   t.name_en as name_en,
                   t.year as year,
                   t.max_wind_speed as max_wind_speed,
                   t.total_path_points as total_path_points,
                   collect(DISTINCT l.name) as landfall_locations
            ORDER BY t.year DESC
            LIMIT $limit
        """

        params = {
            "query": query,
            "limit": limit,
            **filters
        }

        results = await neo4j_client.run(cypher, params)
        return self._transform_results(results, score=0.8)

    async def _similarity_search(
        self,
        query: str,
        filters: Dict,
        limit: int
    ) -> List[SearchResult]:
        """
        相似性查询 - 查找与指定台风路径相似的台风
        使用知识图谱定义的 HAS_PATH_POINT 关系查询路径
        """
        typhoon_id = query.strip()

        cypher = """
            MATCH (ref:Typhoon {typhoon_id: $typhoon_id})-[:HAS_PATH_POINT]->(rp:PathPoint)
            WITH ref, collect({lat: rp.lat, lon: rp.lon, seq: rp.sequence}) as ref_path,
                 count(rp) as ref_path_length

            MATCH (t:Typhoon)-[:HAS_PATH_POINT]->(p:PathPoint)
            WHERE t <> ref
            """

        if filters.get("year"):
            cypher += " AND t.year = $year"

        cypher += """
            WITH ref, ref_path, ref_path_length, t,
                 collect({lat: p.lat, lon: p.lon, seq: p.sequence}) as path,
                 count(p) as path_length
            WHERE path_length >= 10

            WITH ref, t, ref_path, path,
                 sqrt((ref_path[0].lat - path[0].lat)^2 + (ref_path[0].lon - path[0].lon)^2) as start_distance,
                 reduce(s = 0.0, i in range(0, size(ref_path)-1) |
                     s + CASE WHEN i < size(path)
                         THEN (ref_path[i].lat - path[i].lat)^2 + (ref_path[i].lon - path[i].lon)^2
                         ELSE 0 END
                 ) as path_distance

            WITH t,
                 1.0 / (1.0 + start_distance * 0.1) * 0.3 +
                 1.0 / (1.0 + sqrt(path_distance) * 0.01) * 0.7 as similarity_score

            WHERE similarity_score >= $min_similarity

            RETURN t.typhoon_id as typhoon_id,
                   t.name_cn as name_cn,
                   t.name_en as name_en,
                   t.year as year,
                   t.max_wind_speed as max_wind_speed,
                   t.total_path_points as total_path_points,
                   similarity_score as score
            ORDER BY similarity_score DESC
            LIMIT $limit
        """

        params = {
            "typhoon_id": typhoon_id,
            "limit": limit,
            "min_similarity": filters.get("min_similarity", 0.5)
        }

        results = await neo4j_client.run(cypher, params)
        return self._transform_similarity_results(results)

    async def _temporal_search(
        self,
        query: str,
        filters: Dict,
        limit: int
    ) -> List[SearchResult]:
        """
        时序查询 - 按时间维度查询台风
        使用知识图谱定义的 OCCURRED_IN 关系查询时间节点
        """
        import re
        year_match = re.search(r'\d{4}', query)
        year = int(year_match.group()) if year_match else filters.get("year")

        cypher = """
            MATCH (t:Typhoon)-[:OCCURRED_IN]->(tm:Time)
            WHERE 1=1
            """

        params = {"limit": limit}

        if year:
            cypher += " AND tm.year = $year"
            params["year"] = year

        if filters.get("month"):
            cypher += " AND tm.month = $month"
            params["month"] = filters["month"]

        if filters.get("is_peak_season") is not None:
            cypher += " AND tm.is_peak_season = $is_peak_season"
            params["is_peak_season"] = filters["is_peak_season"]

        cypher += """
            OPTIONAL MATCH (t)-[:LANDED_AT]->(l:Location)
            RETURN t.typhoon_id as typhoon_id,
                   t.name_cn as name_cn,
                   t.name_en as name_en,
                   t.year as year,
                   t.max_wind_speed as max_wind_speed,
                   t.total_path_points as total_path_points,
                   collect(DISTINCT l.name) as landfall_locations
            ORDER BY t.year DESC
            LIMIT $limit
        """

        results = await neo4j_client.run(cypher, params)
        return self._transform_results(results, score=0.9)

    async def _smart_search(
        self,
        query: str,
        filters: Dict,
        limit: int
    ) -> List[SearchResult]:
        """
        智能搜索 - 结合多种查询策略
        """
        exact_results = await self._exact_search(query, filters, limit)
        if exact_results:
            return exact_results

        fuzzy_results = await self._fuzzy_search(query, filters, limit)
        if fuzzy_results:
            return fuzzy_results

        return await self._fulltext_search(query, filters, limit)

    async def _fulltext_search(
        self,
        query: str,
        filters: Dict,
        limit: int
    ) -> List[SearchResult]:
        """
        全文检索 - 使用Neo4j全文索引
        """
        try:
            cypher = """
                CALL db.index.fulltext.queryNodes("typhoonSearch", $query)
                YIELD node, score
                WHERE node:Typhoon OR node:Location
                """

            if filters.get("year"):
                cypher += " AND node.year = $year"

            cypher += """
                WITH node, score
                MATCH (t:Typhoon)
                WHERE t = node OR (node:Location AND (t)-[:LANDED_AT]->(node))
                RETURN DISTINCT t.typhoon_id as typhoon_id,
                       t.name_cn as name_cn,
                       t.name_en as name_en,
                       t.year as year,
                       t.max_wind_speed as max_wind_speed,
                       t.total_path_points as total_path_points,
                       score
                ORDER BY score DESC
                LIMIT $limit
            """

            params = {
                "query": query,
                "limit": limit,
                **filters
            }

            results = await neo4j_client.run(cypher, params)
            return self._transform_fulltext_results(results)

        except Exception as e:
            logger.warning(f"全文检索失败: {e}，回退到模糊查询")
            return await self._fuzzy_search(query, filters, limit)

    async def find_similar_path_typhoons(
        self,
        typhoon_id: str,
        location: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        查找路径相似的台风 - 基于路径几何相似度
        使用知识图谱定义的 HAS_PATH_POINT 和 LANDED_AT 关系

        Args:
            typhoon_id: 参考台风编号
            location: 可选的登陆地点过滤
            limit: 返回结果数量

        Returns:
            List[Dict]: 相似台风列表
        """
        cypher = """
            MATCH (ref:Typhoon {typhoon_id: $typhoon_id})-[:HAS_PATH_POINT]->(rp:PathPoint)
            WITH ref, collect({lat: rp.lat, lon: rp.lon, seq: rp.sequence}) as ref_path

            MATCH (t:Typhoon)-[:HAS_PATH_POINT]->(p:PathPoint)
            WHERE t <> ref
            """

        if location:
            cypher += " AND (t)-[:LANDED_AT]->(:Location {name: $location})"

        cypher += """
            WITH ref, ref_path, t,
                 collect({lat: p.lat, lon: p.lon, seq: p.sequence}) as path,
                 count(p) as path_length
            WHERE path_length >= 10

            WITH ref, t, ref_path, path,
                 reduce(s = 0.0, i in range(0, size(ref_path)-1) |
                     s + CASE WHEN i < size(path)
                         THEN (ref_path[i].lat - path[i].lat)^2 + (ref_path[i].lon - path[i].lon)^2
                         ELSE 0 END
                 ) as distance

            RETURN t.typhoon_id as typhoon_id,
                   t.name_cn as name_cn,
                   t.name_en as name_en,
                   t.year as year,
                   t.max_wind_speed as max_wind_speed,
                   1.0 / (1.0 + sqrt(distance)) as similarity_score
            ORDER BY similarity_score DESC
            LIMIT $limit
        """

        params = {
            "typhoon_id": typhoon_id,
            "location": location,
            "limit": limit
        }

        return await neo4j_client.run(cypher, params)

    async def get_typhoon_details(self, typhoon_id: str) -> Optional[Dict]:
        """
        获取台风详细信息
        使用知识图谱定义的所有关系获取完整信息

        Args:
            typhoon_id: 台风编号

        Returns:
            Optional[Dict]: 台风详细信息
        """
        cypher = """
            MATCH (t:Typhoon {typhoon_id: $typhoon_id})
            OPTIONAL MATCH (t)-[:OCCURRED_IN]->(tm:Time)
            OPTIONAL MATCH (t)-[:LANDED_AT]->(l:Location)
            OPTIONAL MATCH (t)-[:INTENSIFIED_TO]->(i:Intensity)
            OPTIONAL MATCH (t)-[:WEAKENED_TO]->(i2:Intensity)
            OPTIONAL MATCH (t)-[:HAS_PATH_POINT]->(p:PathPoint)
            RETURN t.typhoon_id as typhoon_id,
                   t.name_cn as name_cn,
                   t.name_en as name_en,
                   t.year as year,
                   t.max_wind_speed as max_wind_speed,
                   t.min_pressure as min_pressure,
                   t.total_path_points as total_path_points,
                   t.duration_hours as duration_hours,
                   t.start_lat as start_lat,
                   t.start_lon as start_lon,
                   t.end_lat as end_lat,
                   t.end_lon as end_lon,
                   tm.is_peak_season as is_peak_season,
                   collect(DISTINCT l.name) as landfall_locations,
                   coalesce(i.level, i2.level) as intensity_level,
                   coalesce(i.name_cn, i2.name_cn) as intensity_name,
                   collect(p {.*}) as path_points
        """

        results = await neo4j_client.run(cypher, {"typhoon_id": typhoon_id})
        return results[0] if results else None

    async def get_typhoon_path(self, typhoon_id: str) -> List[Dict]:
        """
        获取台风路径数据
        使用知识图谱定义的 HAS_PATH_POINT 关系

        Args:
            typhoon_id: 台风编号

        Returns:
            List[Dict]: 按序列排序的路径点列表
        """
        cypher = """
            MATCH (t:Typhoon {typhoon_id: $typhoon_id})-[:HAS_PATH_POINT]->(p:PathPoint)
            RETURN p.sequence as sequence,
                   p.lat as lat,
                   p.lon as lon,
                   p.timestamp as timestamp,
                   p.pressure as pressure,
                   p.wind_speed as wind_speed,
                   p.moving_direction as moving_direction,
                   p.moving_speed as moving_speed,
                   p.intensity as intensity
            ORDER BY p.sequence
        """

        return await neo4j_client.run(cypher, {"typhoon_id": typhoon_id})

    async def temporal_query(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        location: Optional[str] = None,
        intensity: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        时序查询 - 多维度时间查询
        使用知识图谱定义的关系进行查询

        Args:
            year: 年份
            month: 月份
            location: 登陆地点
            intensity: 强度等级
            limit: 返回数量

        Returns:
            List[Dict]: 查询结果
        """
        conditions = []
        params = {"limit": limit}

        cypher = """
            MATCH (t:Typhoon)-[:OCCURRED_IN]->(y:Time)
            OPTIONAL MATCH (t)-[:LANDED_AT]->(l:Location)
            OPTIONAL MATCH (t)-[:INTENSIFIED_TO]->(i:Intensity)
            OPTIONAL MATCH (t)-[:WEAKENED_TO]->(i2:Intensity)
            WHERE 1=1
            """

        if year:
            cypher += " AND y.year = $year"
            params["year"] = year

        if month:
            cypher += " AND y.month = $month"
            params["month"] = month

        if location:
            cypher += " AND l.name CONTAINS $location"
            params["location"] = location

        if intensity:
            cypher += " AND i.level = $intensity"
            params["intensity"] = intensity

        cypher += """
            RETURN t.typhoon_id as typhoon_id,
                   t.name_cn as name_cn,
                   t.year as year,
                   t.max_wind_speed as max_wind_speed,
                   collect(DISTINCT l.name) as landfall_locations,
                   i.name_cn as intensity
            ORDER BY t.year DESC
            LIMIT $limit
        """

        return await neo4j_client.run(cypher, params)

    def _transform_results(self, results: List[Dict], score: float) -> List[SearchResult]:
        """转换查询结果为SearchResult对象"""
        search_results = []
        for r in results:
            search_results.append(SearchResult(
                typhoon_id=r.get("typhoon_id", ""),
                name_cn=r.get("name_cn", ""),
                name_en=r.get("name_en", ""),
                year=r.get("year", 0),
                score=score,
                max_wind_speed=r.get("max_wind_speed", 0.0),
                total_path_points=r.get("total_path_points", 0),
                matched_fields={"landfall_locations": r.get("landfall_locations", [])},
                related_typhoons=[]
            ))
        return search_results

    def _transform_similarity_results(self, results: List[Dict]) -> List[SearchResult]:
        """转换相似性查询结果"""
        search_results = []
        for r in results:
            search_results.append(SearchResult(
                typhoon_id=r.get("typhoon_id", ""),
                name_cn=r.get("name_cn", ""),
                name_en=r.get("name_en", ""),
                year=r.get("year", 0),
                score=r.get("similarity_score", 0.0),
                max_wind_speed=r.get("max_wind_speed", 0.0),
                total_path_points=r.get("total_path_points", 0),
                matched_fields={},
                related_typhoons=[]
            ))
        return search_results

    def _transform_fulltext_results(self, results: List[Dict]) -> List[SearchResult]:
        """转换全文检索结果"""
        search_results = []
        for r in results:
            search_results.append(SearchResult(
                typhoon_id=r.get("typhoon_id", ""),
                name_cn=r.get("name_cn", ""),
                name_en=r.get("name_en", ""),
                year=r.get("year", 0),
                score=r.get("score", 0.0),
                max_wind_speed=r.get("max_wind_speed", 0.0),
                total_path_points=r.get("total_path_points", 0),
                matched_fields={},
                related_typhoons=[]
            ))
        return search_results


query_engine = KnowledgeGraphQueryEngine()
