"""
增强版知识图谱检索模块
实现多维度关联查询，包括台风基本信息、历史数据、气象参数等知识节点的深度关联
"""

from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import deque, defaultdict
import asyncio
from loguru import logger

from .typhoon_intent_recognizer import (
    TyphoonQueryAnalysis, 
    TyphoonIntentType,
    TyphoonEntityType
)


@dataclass
class RetrievalResult:
    """检索结果"""
    nodes: List[Dict]
    relationships: List[Dict]
    relevance_scores: Dict[str, float]
    retrieval_paths: List[List[str]]
    metadata: Dict = field(default_factory=dict)
    seed_entities: List[Dict] = field(default_factory=list)  # 识别的种子实体


@dataclass
class RetrievalConfig:
    """检索配置"""
    max_depth: int = 3
    max_nodes: int = 200  # 增大至200，支持更多种子节点
    max_relationships: int = 400  # 相应增大至400
    min_relevance_score: float = 0.3
    enable_multi_hop: bool = True
    prioritize_typhoon_nodes: bool = True
    include_path_points: bool = True
    include_historical_similar: bool = False
    max_seeds: int = 50  # 最大种子实体数量


class EnhancedGraphRetriever:
    """增强版知识图谱检索器"""
    
    # 关系类型权重配置
    RELATIONSHIP_WEIGHTS = {
        # 核心关系 - 高权重
        "HAS_PATH_POINT": 1.0,
        "LANDED_AT": 1.0,
        "AFFECTED_AREA": 0.9,

        # 时间空间关系（AFFECTED_AREA 已包含经过附近的语义，PASSED_NEAR 已移除）
        "OCCURRED_IN": 0.8,
        "GENERATED_AT": 0.8,
        "DISSIPATED_AT": 0.8,

        # 强度变化关系（INTENSIFIED_TO 和 WEAKENED_TO 包含达到强度的语义）
        "INTENSIFIED_TO": 0.85,
        "WEAKENED_TO": 0.85,
        "HAS_INTENSITY": 0.7,

        # 路径顺序关系
        "NEXT": 0.6,

        # 相似性关系
        "SIMILAR_TO": 0.5,
    }
    
    # 属性相关性权重
    ATTRIBUTE_RELEVANCE = {
        # 基础信息
        "name_cn": 1.0,
        "name_en": 0.9,
        "typhoon_id": 1.0,
        "year": 0.9,
        
        # 强度信息
        "max_wind_speed": 0.95,
        "min_pressure": 0.95,
        "peak_intensity": 0.9,
        "power": 0.85,
        
        # 时间信息
        "start_time": 0.9,
        "end_time": 0.9,
        "duration_hours": 0.85,
        
        # 位置信息
        "start_lat": 0.8,
        "start_lon": 0.8,
        "end_lat": 0.8,
        "end_lon": 0.8,
        
        # 路径信息
        "total_path_points": 0.7,
        "total_distance_km": 0.7,
        "avg_moving_speed": 0.75,
        
        # 登陆信息
        "landfall_count": 0.85,
    }
    
    # 意图到关系类型的映射
    INTENT_RELATION_MAPPING = {
        TyphoonIntentType.BASIC_INFO: ["OCCURRED_IN", "GENERATED_AT", "DISSIPATED_AT"],
        TyphoonIntentType.PATH_QUERY: ["HAS_PATH_POINT", "NEXT", "AFFECTED_AREA", "LANDED_AT"],
        TyphoonIntentType.INTENSITY_QUERY: ["INTENSIFIED_TO", "WEAKENED_TO", "HAS_INTENSITY"],
        TyphoonIntentType.TIME_QUERY: ["OCCURRED_IN", "GENERATED_AT", "DISSIPATED_AT"],
        TyphoonIntentType.LANDFALL_QUERY: ["LANDED_AT", "AFFECTED_AREA"],
        TyphoonIntentType.IMPACT_QUERY: ["AFFECTED_AREA", "LANDED_AT"],
        TyphoonIntentType.AFFECTED_AREA_QUERY: ["AFFECTED_AREA", "LANDED_AT"],
        TyphoonIntentType.PREDICTION_QUERY: ["HAS_PATH_POINT", "SIMILAR_TO"],
        TyphoonIntentType.COMPARISON_QUERY: ["SIMILAR_TO", "HAS_PATH_POINT", "INTENSIFIED_TO", "WEAKENED_TO"],
        TyphoonIntentType.SIMILAR_QUERY: ["SIMILAR_TO"],
        TyphoonIntentType.STATISTICS_QUERY: ["OCCURRED_IN", "LANDED_AT", "INTENSIFIED_TO", "WEAKENED_TO"],
        TyphoonIntentType.RANKING_QUERY: ["INTENSIFIED_TO", "WEAKENED_TO", "OCCURRED_IN"],
    }
    
    def __init__(self, neo4j_client):
        self.neo4j = neo4j_client
    
    async def retrieve(
        self,
        query_analysis: TyphoonQueryAnalysis,
        config: Optional[RetrievalConfig] = None
    ) -> RetrievalResult:
        """
        执行增强版检索 - 全局协调的分层检索策略
        
        检索策略：
        1. 收集所有种子节点
        2. 统一进行分层检索：先所有种子的depth=1，再所有种子的depth=2
        3. 全局控制直到达到max_nodes个节点
        
        Args:
            query_analysis: 查询分析结果
            config: 检索配置
            
        Returns:
            RetrievalResult: 检索结果
        """
        config = config or RetrievalConfig()
        
        # 1. 确定种子实体（传入配置）
        seed_entities = await self._identify_seed_entities(query_analysis, config)
        
        if not seed_entities:
            return RetrievalResult(
                nodes=[], 
                relationships=[], 
                relevance_scores={}, 
                retrieval_paths=[]
            )
        
        # 2. 根据意图优化检索配置
        optimized_config = self._optimize_config(query_analysis, config)
        
        # 3. 执行全局协调的分层检索
        all_nodes, all_relationships, retrieval_paths = await self._traverse_all_seeds_layered(
            seed_entities, query_analysis, optimized_config
        )
        
        # 4. 计算相关性分数
        relevance_scores = self._calculate_relevance_scores(
            all_nodes, all_relationships, query_analysis
        )
        
        # 5. 根据相关性过滤和排序
        filtered_nodes = self._filter_by_relevance(
            all_nodes, relevance_scores, optimized_config.min_relevance_score
        )
        
        # 6. 限制结果数量
        final_nodes = self._limit_results(
            filtered_nodes, relevance_scores, optimized_config.max_nodes
        )
        
        final_relationships = self._filter_relationships(
            all_relationships, final_nodes, optimized_config.max_relationships
        )
        
        return RetrievalResult(
            nodes=list(final_nodes.values()),
            relationships=list(final_relationships.values()),
            relevance_scores=relevance_scores,
            retrieval_paths=retrieval_paths,
            metadata={
                "seed_count": len(seed_entities),
                "node_count": len(final_nodes),
                "relationship_count": len(final_relationships),
                "total_nodes_before_filter": len(all_nodes),
                "total_relationships_before_filter": len(all_relationships),
                "config": {
                    "max_depth": optimized_config.max_depth,
                    "max_nodes": optimized_config.max_nodes,
                    "min_relevance_score": optimized_config.min_relevance_score,
                }
            },
            seed_entities=seed_entities  # 返回识别的种子实体
        )
    
    async def _traverse_all_seeds_layered(
        self,
        seed_entities: List[Dict],
        query_analysis: TyphoonQueryAnalysis,
        config: RetrievalConfig
    ) -> Tuple[Dict[str, Dict], Dict[str, Dict], List[List[str]]]:
        """
        全局协调的分层检索 - 所有种子统一分层检索
        
        策略：
        1. 先添加所有种子节点（depth=0）
        2. 统一检索所有种子的depth=1节点
        3. 统一检索所有种子的depth=2节点
        4. 直到达到max_nodes限制
        """
        all_nodes = {}
        all_relationships = {}
        paths = []
        
        # 添加所有种子节点（depth=0）
        seed_ids = set()
        for seed in seed_entities:
            seed_id = seed["id"]
            seed_ids.add(seed_id)
            if seed_id not in all_nodes:
                seed_node = await self._get_node_details(seed_id)
                if seed_node:
                    all_nodes[seed_id] = seed_node
                    logger.debug(f"添加种子节点: {seed_id}")
        
        # 按深度分层检索 - 全局协调
        current_depth_nodes = seed_ids.copy()  # 当前深度的所有节点
        visited_nodes = seed_ids.copy()  # 已访问的所有节点
        
        for depth in range(config.max_depth):
            if not current_depth_nodes or len(all_nodes) >= config.max_nodes:
                break
            next_depth_nodes = set()  # 下一层的所有节点
            
            # 遍历当前深度的所有节点（来自所有种子）
            for current_id in current_depth_nodes:
                if len(all_nodes) >= config.max_nodes:
                    logger.info(f"达到最大节点数限制: {config.max_nodes}")
                    break
                
                # 获取邻居
                neighbors = await self._get_neighbors(
                    current_id, 
                    query_analysis,
                    config
                )
                
                for neighbor in neighbors:
                    neighbor_id = neighbor["id"]
                    rel_type = neighbor.get("relationship_type", "")
                    rel_key = f"{current_id}-{rel_type}-{neighbor_id}"
                    
                    # 添加关系
                    if rel_key not in all_relationships:
                        all_relationships[rel_key] = {
                            "source": current_id,
                            "target": neighbor_id,
                            "type": rel_type,
                            "properties": neighbor.get("rel_properties", {}),
                            "weight": self.RELATIONSHIP_WEIGHTS.get(rel_type, 0.5)
                        }
                    
                    # 添加节点
                    if neighbor_id not in all_nodes:
                        all_nodes[neighbor_id] = {
                            "id": neighbor_id,
                            "type": neighbor.get("node_type", "Unknown"),
                            "properties": neighbor.get("node_properties", {})
                        }
                    
                    # 如果节点未访问过，加入下一层
                    if neighbor_id not in visited_nodes and len(visited_nodes) < config.max_nodes:
                        visited_nodes.add(neighbor_id)
                        next_depth_nodes.add(neighbor_id)
                        
                        # 记录路径
                        paths.append([current_id, neighbor_id])
            
            # 更新当前深度节点为下一层节点
            current_depth_nodes = next_depth_nodes
        return all_nodes, all_relationships, paths
    
    async def _identify_seed_entities(
        self, 
        query_analysis: TyphoonQueryAnalysis,
        config: Optional[RetrievalConfig] = None
    ) -> List[Dict]:
        """识别种子实体"""
        config = config or RetrievalConfig()
        max_seeds = config.max_seeds
        seeds = []
        
        # 1. 从台风名称获取
        typhoon_names = [
            e for e in query_analysis.entities 
            if e.entity_type == TyphoonEntityType.TYPHOON_NAME
        ]
        
        for entity in typhoon_names:
            typhoon_data = await self._get_typhoon_by_name(entity.value)
            if typhoon_data:
                seeds.append({
                    "id": typhoon_data["typhoon_id"],
                    "type": "Typhoon",
                    "name": entity.value,
                    "confidence": entity.confidence,
                    "source": "name"
                })
        
        # 2. 从台风编号获取
        typhoon_ids = [
            e for e in query_analysis.entities 
            if e.entity_type == TyphoonEntityType.TYPHOON_ID
        ]
        
        for entity in typhoon_ids:
            typhoon_data = await self._get_typhoon_by_id(entity.value)
            if typhoon_data:
                seeds.append({
                    "id": entity.value,
                    "type": "Typhoon",
                    "name": typhoon_data.get("name_cn", entity.value),
                    "confidence": entity.confidence,
                    "source": "id"
                })
        
        # 3. 从年份获取（如果是年份查询）
        years = [
            e for e in query_analysis.entities 
            if e.entity_type == TyphoonEntityType.YEAR
        ]
        
        if years and not typhoon_names and not typhoon_ids:
            # 年份查询，获取该年份的所有台风，使用配置的最大种子数
            for entity in years:
                year_typhoons = await self._get_typhoons_by_year(entity.value)
                for typhoon in year_typhoons[:max_seeds]:  # 使用配置的最大种子数
                    seeds.append({
                        "id": typhoon["typhoon_id"],
                        "type": "Typhoon",
                        "name": typhoon.get("name_cn", typhoon["typhoon_id"]),
                        "confidence": entity.confidence * 0.9,
                        "source": "year",
                        "year": entity.value
                    })
        
        # 4. 从地理位置获取
        locations = [
            e for e in query_analysis.entities 
            if e.entity_type == TyphoonEntityType.LOCATION
        ]
        
        for entity in locations:
            # 查找影响该地区的台风
            affected_typhoons = await self._get_typhoons_by_location(entity.value)
            for typhoon in affected_typhoons[:max_seeds]:  # 使用配置的最大种子数
                if not any(s["id"] == typhoon["typhoon_id"] for s in seeds):
                    seeds.append({
                        "id": typhoon["typhoon_id"],
                        "type": "Typhoon",
                        "name": typhoon.get("name_cn", typhoon["typhoon_id"]),
                        "confidence": entity.confidence * 0.8,
                        "source": "location",
                        "location": entity.value
                    })
        
        # 去重并排序
        seen_ids = set()
        unique_seeds = []
        for seed in sorted(seeds, key=lambda x: x["confidence"], reverse=True):
            if seed["id"] not in seen_ids:
                seen_ids.add(seed["id"])
                unique_seeds.append(seed)
        
        return unique_seeds[:max_seeds]  # 使用配置的最大种子数
    
    async def _traverse_from_seed(
        self,
        seed: Dict,
        query_analysis: TyphoonQueryAnalysis,
        config: RetrievalConfig
    ) -> Tuple[Dict[str, Dict], Dict[str, Dict], List[List[str]]]:
        """从种子实体开始分层遍历 - 先检索depth=1的所有节点，再检索depth=2"""
        nodes = {}
        relationships = {}
        paths = []
        
        # 添加种子节点（depth=0）
        seed_node = await self._get_node_details(seed["id"])
        if seed_node:
                    nodes[seed["id"]] = seed_node
        
        # 按深度分层检索
        current_depth_nodes = {seed["id"]}  # 当前深度的节点
        visited = {seed["id"]}  # 已访问节点
        
        for depth in range(config.max_depth):
            if not current_depth_nodes or len(nodes) >= config.max_nodes:
                break
            next_depth_nodes = set()  # 下一层的节点
            
            # 遍历当前深度的所有节点
            for current_id in current_depth_nodes:
                if len(nodes) >= config.max_nodes:
                    break
                
                # 获取邻居
                neighbors = await self._get_neighbors(
                    current_id, 
                    query_analysis,
                    config
                )
                
                for neighbor in neighbors:
                    neighbor_id = neighbor["id"]
                    rel_type = neighbor.get("relationship_type", "")
                    rel_key = f"{current_id}-{rel_type}-{neighbor_id}"
                    
                    # 添加关系
                    if rel_key not in relationships:
                        relationships[rel_key] = {
                            "source": current_id,
                            "target": neighbor_id,
                            "type": rel_type,
                            "properties": neighbor.get("rel_properties", {}),
                            "weight": self.RELATIONSHIP_WEIGHTS.get(rel_type, 0.5)
                        }
                    
                    # 添加节点
                    if neighbor_id not in nodes:
                        nodes[neighbor_id] = {
                            "id": neighbor_id,
                            "type": neighbor.get("node_type", "Unknown"),
                            "properties": neighbor.get("node_properties", {})
                        }
                    
                    # 如果节点未访问过，加入下一层
                    if neighbor_id not in visited and len(visited) < config.max_nodes:
                        visited.add(neighbor_id)
                        next_depth_nodes.add(neighbor_id)
                        
                        # 记录路径
                        paths.append([seed["id"], current_id, neighbor_id])
            
            # 更新当前深度节点为下一层节点
            current_depth_nodes = next_depth_nodes
        return nodes, relationships, paths
    
    async def _get_neighbors(
        self,
        node_id: str,
        query_analysis: TyphoonQueryAnalysis,
        config: RetrievalConfig
    ) -> List[Dict]:
        """获取节点的邻居"""
        # 根据意图确定优先关系类型
        priority_relations = self.INTENT_RELATION_MAPPING.get(
            query_analysis.intent.intent_type, 
            []
        )
        
        # 构建查询
        if priority_relations:
            rel_filter = "OR".join([f" type(r) = '{rel}' " for rel in priority_relations])
            rel_filter = f"AND ({rel_filter})"
        else:
            rel_filter = ""
        
        query = f"""
        MATCH (start)
        WHERE (start:Typhoon AND start.typhoon_id = $node_id)
           OR (start:Location AND start.name = $node_id)
           OR elementId(start) = $node_id
        WITH start
        OPTIONAL MATCH (start)-[r]-(n)
        WHERE 1=1 {rel_filter}
        WITH start, r, n
        LIMIT 50
        RETURN 
            CASE 
                WHEN n:Typhoon THEN n.typhoon_id
                WHEN n:Location THEN n.name
                WHEN n:PathPoint THEN elementId(n)
                WHEN n:Time THEN toString(n.year)
                WHEN n:Intensity THEN n.level
                ELSE elementId(n)
            END as neighbor_id,
            labels(n)[0] as neighbor_type,
            properties(n) as neighbor_props,
            type(r) as rel_type,
            properties(r) as rel_props,
            CASE 
                WHEN startNode(r) = start THEN 
                    CASE 
                        WHEN start:Typhoon THEN start.typhoon_id
                        WHEN start:Location THEN start.name
                        ELSE elementId(start)
                    END
                ELSE CASE 
                    WHEN startNode(r):Typhoon THEN startNode(r).typhoon_id
                    WHEN startNode(r):Location THEN startNode(r).name
                    ELSE elementId(startNode(r))
                END
            END as source_id,
            CASE 
                WHEN endNode(r) = start THEN 
                    CASE 
                        WHEN start:Typhoon THEN start.typhoon_id
                        WHEN start:Location THEN start.name
                        ELSE elementId(start)
                    END
                ELSE CASE 
                    WHEN endNode(r):Typhoon THEN endNode(r).typhoon_id
                    WHEN endNode(r):Location THEN endNode(r).name
                    ELSE elementId(endNode(r))
                END
            END as target_id
        """
        
        try:
            result = await self.neo4j.run(query, {"node_id": node_id})
            
            neighbors = []
            for record in result:
                neighbor_id = record.get("neighbor_id")
                if neighbor_id:
                    neighbors.append({
                        "id": neighbor_id,
                        "node_type": record.get("neighbor_type"),
                        "node_properties": record.get("neighbor_props", {}),
                        "relationship_type": record.get("rel_type"),
                        "rel_properties": record.get("rel_props", {}),
                        "source_id": record.get("source_id"),
                        "target_id": record.get("target_id")
                    })
            
            return neighbors
            
        except Exception:
            return []
    
    def _calculate_relevance_scores(
        self,
        nodes: Dict[str, Dict],
        relationships: Dict[str, Dict],
        query_analysis: TyphoonQueryAnalysis
    ) -> Dict[str, float]:
        """计算节点相关性分数"""
        scores = {}
        
        # 意图相关的属性
        intent_attrs = self._get_intent_attributes(query_analysis.intent.intent_type)
        
        for node_id, node_data in nodes.items():
            score = 0.0
            node_type = node_data.get("type", "")
            properties = node_data.get("properties", {})
            
            # 1. 节点类型权重
            if node_type == "Typhoon":
                score += 1.0
            elif node_type == "PathPoint":
                score += 0.6
            elif node_type == "Location":
                score += 0.7
            elif node_type == "Intensity":
                score += 0.8
            
            # 2. 属性相关性
            for attr, value in properties.items():
                attr_weight = self.ATTRIBUTE_RELEVANCE.get(attr, 0.5)
                
                # 如果属性与意图相关，增加权重
                if attr in intent_attrs:
                    attr_weight *= 1.5
                
                # 检查属性值是否匹配查询中的实体
                for entity in query_analysis.entities:
                    if str(value) == entity.value or str(value) == entity.normalized_value:
                        attr_weight *= 2.0
                
                score += attr_weight * 0.1
            
            # 3. 关系权重
            for rel_key, rel_data in relationships.items():
                if rel_data["source"] == node_id or rel_data["target"] == node_id:
                    score += rel_data.get("weight", 0.5) * 0.2
            
            scores[node_id] = min(score, 2.0)  # 上限2.0
        
        return scores
    
    def _filter_by_relevance(
        self,
        nodes: Dict[str, Dict],
        scores: Dict[str, float],
        min_score: float
    ) -> Dict[str, Dict]:
        """根据相关性过滤节点"""
        filtered = {}
        for node_id, node_data in nodes.items():
            score = scores.get(node_id, 0)
            if score >= min_score:
                node_data["relevance_score"] = score
                filtered[node_id] = node_data
        return filtered
    
    def _limit_results(
        self,
        nodes: Dict[str, Dict],
        scores: Dict[str, float],
        max_nodes: int
    ) -> Dict[str, Dict]:
        """限制结果数量"""
        # 按分数排序
        sorted_nodes = sorted(
            nodes.items(),
            key=lambda x: scores.get(x[0], 0),
            reverse=True
        )
        
        # 取前N个
        limited = dict(sorted_nodes[:max_nodes])
        return limited
    
    def _filter_relationships(
        self,
        relationships: Dict[str, Dict],
        nodes: Dict[str, Dict],
        max_relationships: int
    ) -> Dict[str, Dict]:
        """过滤关系（只保留相关节点之间的关系）"""
        node_ids = set(nodes.keys())
        filtered = {}
        
        for rel_key, rel_data in relationships.items():
            if rel_data["source"] in node_ids and rel_data["target"] in node_ids:
                filtered[rel_key] = rel_data
        
        # 按权重排序并限制数量
        sorted_rels = sorted(
            filtered.items(),
            key=lambda x: x[1].get("weight", 0),
            reverse=True
        )
        
        return dict(sorted_rels[:max_relationships])
    
    def _optimize_config(
        self,
        query_analysis: TyphoonQueryAnalysis,
        base_config: RetrievalConfig
    ) -> RetrievalConfig:
        """根据查询优化配置"""
        config = RetrievalConfig(
            max_depth=base_config.max_depth,
            max_nodes=base_config.max_nodes,
            max_relationships=base_config.max_relationships,
            min_relevance_score=base_config.min_relevance_score,
            enable_multi_hop=base_config.enable_multi_hop,
            max_seeds=base_config.max_seeds,
        )
        
        intent_type = query_analysis.intent.intent_type
        
        # 根据意图调整配置
        if intent_type == TyphoonIntentType.PATH_QUERY:
            config.max_depth = 3  # 路径需要更深遍历
            config.max_nodes = 200  # 路径点较多
            config.max_relationships = 400
            config.include_path_points = True
        elif intent_type == TyphoonIntentType.COMPARISON_QUERY:
            config.max_depth = 2
            config.max_nodes = 200  # 多个台风对比需要更多节点
            config.max_relationships = 400
            config.max_seeds = 50  # 支持更多种子
        elif intent_type == TyphoonIntentType.STATISTICS_QUERY:
            config.max_depth = 1
            config.max_nodes = 300  # 统计查询需要更多节点
            config.max_relationships = 500
            config.max_seeds = 50  # 支持更多种子
            config.min_relevance_score = 0.2  # 降低阈值
        elif intent_type == TyphoonIntentType.BASIC_INFO:
            config.max_depth = 1
            config.max_nodes = 50  # 基本信息较少
            config.max_relationships = 100
        elif intent_type == TyphoonIntentType.UNKNOWN:
            # 未知意图（如年份查询），使用较大配置
            config.max_depth = 2
            config.max_nodes = 200
            config.max_relationships = 400
            config.max_seeds = 50
        
        return config
    
    def _get_intent_attributes(self, intent_type: TyphoonIntentType) -> List[str]:
        """获取意图相关的属性"""
        attr_mapping = {
            TyphoonIntentType.BASIC_INFO: ["name_cn", "name_en", "typhoon_id", "year"],
            TyphoonIntentType.PATH_QUERY: ["lat", "lon", "moving_speed", "moving_direction"],
            TyphoonIntentType.INTENSITY_QUERY: ["max_wind_speed", "min_pressure", "peak_intensity"],
            TyphoonIntentType.TIME_QUERY: ["start_time", "end_time", "duration_hours"],
            TyphoonIntentType.LANDFALL_QUERY: ["landfall_count", "land_time"],
            TyphoonIntentType.IMPACT_QUERY: ["affected_area", "damage"],
        }
        return attr_mapping.get(intent_type, [])
    
    # Neo4j查询方法
    async def _get_typhoon_by_name(self, name: str) -> Optional[Dict]:
        """通过名称获取台风"""
        query = """
        MATCH (t:Typhoon)
        WHERE t.name_cn = $name OR t.name_en = $name
        RETURN t as typhoon
        LIMIT 1
        """
        try:
            result = await self.neo4j.run(query, {"name": name})
            for record in result:
                return dict(record["typhoon"])
            return None
        except Exception:
            return None
    
    async def _get_typhoon_by_id(self, typhoon_id: str) -> Optional[Dict]:
        """通过ID获取台风"""
        query = """
        MATCH (t:Typhoon {typhoon_id: $typhoon_id})
        RETURN t as typhoon
        """
        try:
            result = await self.neo4j.run(query, {"typhoon_id": typhoon_id})
            for record in result:
                return dict(record["typhoon"])
            return None
        except Exception:
            return None
    
    async def _get_typhoons_by_year(self, year: str) -> List[Dict]:
        """获取某年的所有台风"""
        query = """
        MATCH (t:Typhoon {year: $year})
        RETURN t as typhoon
        ORDER BY t.max_wind_speed DESC
        LIMIT 50
        """
        try:
            result = await self.neo4j.run(query, {"year": int(year)})
            return [dict(record["typhoon"]) for record in result]
        except Exception:
            return []
    
    async def _get_typhoons_by_location(self, location: str) -> List[Dict]:
        """获取影响某地区的台风"""
        query = """
        MATCH (t:Typhoon)-[:AFFECTED_AREA|LANDED_AT]->(l:Location)
        WHERE l.name CONTAINS $location
        RETURN DISTINCT t as typhoon
        ORDER BY t.year DESC
        LIMIT 20
        """
        try:
            result = await self.neo4j.run(query, {"location": location})
            return [dict(record["typhoon"]) for record in result]
        except Exception:
            return []
    
    async def _get_node_details(self, node_id: str) -> Optional[Dict]:
        """获取节点详情"""
        query = """
        MATCH (n)
        WHERE (n:Typhoon AND n.typhoon_id = $node_id)
           OR (n:Location AND n.name = $node_id)
           OR elementId(n) = $node_id
        RETURN 
            CASE 
                WHEN n:Typhoon THEN n.typhoon_id
                WHEN n:Location THEN n.name
                ELSE elementId(n)
            END as id,
            labels(n)[0] as type,
            properties(n) as properties
        LIMIT 1
        """
        try:
            result = await self.neo4j.run(query, {"node_id": node_id})
            for record in result:
                return {
                    "id": record["id"],
                    "type": record["type"],
                    "properties": record["properties"]
                }
            return None
        except Exception:
            return None


# 辅助函数
def create_enhanced_retriever(neo4j_client) -> EnhancedGraphRetriever:
    """创建增强版检索器"""
    return EnhancedGraphRetriever(neo4j_client)
