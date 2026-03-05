"""
GraphRAG主引擎 - 台风领域增强版
整合实体链接、子图遍历、质量评估和上下文生成
支持语义搜索、多跳推理、意图识别和动态Prompt构建
"""

from typing import List, Dict, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
import logging
from collections import deque

from loguru import logger

from .entity_linker import EntityLinker, LinkedEntity
from .semantic_search import SemanticEntitySearch
from .typhoon_intent_recognizer import (
    TyphoonIntentRecognizer, 
    TyphoonQueryAnalysis,
    TyphoonIntentType,
    intent_recognizer
)
from .prompt_builder import TyphoonPromptBuilder, prompt_builder
from .enhanced_retriever import EnhancedGraphRetriever, RetrievalConfig
from .relevance_ranker import RelevanceRanker, RankingConfig, create_ranker


@dataclass
class GraphRAGResult:
    """GraphRAG检索结果"""
    query: str
    seed_entities: List[LinkedEntity]
    subgraph: Dict  # 子图数据
    context_text: str
    context_structured: Dict
    quality_score: float
    quality_level: str  # "high", "medium", "low"
    traversal_stats: Dict
    reasoning_paths: List[Dict] = field(default_factory=list)
    quality_result: Dict = field(default_factory=dict)
    search_metadata: Dict = field(default_factory=dict)  # 搜索元数据
    # 新增字段
    query_analysis: Optional[TyphoonQueryAnalysis] = None
    prompt_info: Optional[Dict] = None
    ranked_results: Optional[List[Dict]] = None


@dataclass
class TraversalConfig:
    """子图遍历配置"""
    max_depth: int = 2  # 最大遍历深度
    max_nodes: int = 100  # 最大节点数
    max_relationships: int = 200  # 最大关系数
    relationship_types: Optional[List[str]] = None  # 关系类型过滤
    min_relationship_weight: float = 0.0  # 最小关系权重
    include_community_info: bool = True  # 是否包含社区信息
    enable_multi_hop: bool = True  # 是否启用多跳推理


class GraphRAGEngine:
    """GraphRAG主引擎 - 台风领域增强版"""
    
    def __init__(
        self, 
        neo4j_client, 
        enable_semantic_search: bool = True,
        enable_intent_recognition: bool = True,
        enable_enhanced_retrieval: bool = True,
        enable_ranking: bool = True
    ):
        """
        初始化GraphRAG引擎
        
        Args:
            neo4j_client: Neo4j数据库客户端
            enable_semantic_search: 是否启用语义搜索
            enable_intent_recognition: 是否启用意图识别
            enable_enhanced_retrieval: 是否启用增强检索
            enable_ranking: 是否启用相关性排序
        """
        self.neo4j = neo4j_client
        self.entity_linker = EntityLinker(neo4j_client, enable_semantic_search)
        self.semantic_search = SemanticEntitySearch(neo4j_client) if enable_semantic_search else None
        
        # 新增模块
        self.intent_recognizer = intent_recognizer if enable_intent_recognition else None
        self.prompt_builder = prompt_builder
        self.enhanced_retriever = EnhancedGraphRetriever(neo4j_client) if enable_enhanced_retrieval else None
        self.ranker = create_ranker() if enable_ranking else None
        
        # 配置
        self.enable_semantic_search = enable_semantic_search
        self.enable_intent_recognition = enable_intent_recognition
        self.enable_enhanced_retrieval = enable_enhanced_retrieval
        self.enable_ranking = enable_ranking
    
    async def local_search(
        self,
        query: str,
        max_depth: int = 2,
        max_nodes: int = 100,
        relationship_types: Optional[List[str]] = None,
        include_paths: bool = True,
        enable_quality_check: bool = True,
        use_semantic: bool = True,
        use_intent_recognition: bool = True,
        use_enhanced_retrieval: bool = True
    ) -> GraphRAGResult:
        """
        执行GraphRAG LocalSearch（台风领域增强版）
        
        Args:
            query: 用户查询
            max_depth: 遍历深度
            max_nodes: 最大节点数
            relationship_types: 关系类型过滤
            include_paths: 是否包含路径信息
            enable_quality_check: 是否启用质量评估
            use_semantic: 是否使用语义搜索
            use_intent_recognition: 是否使用意图识别
            use_enhanced_retrieval: 是否使用增强检索
            
        Returns:
            GraphRAG检索结果
        """
        # ========== 阶段1: 意图识别与实体抽取 ==========
        query_analysis = None
        if use_intent_recognition and self.intent_recognizer:
            query_analysis = self.intent_recognizer.analyze(query)
        
        # ========== 阶段2: 实体链接 ==========
        seed_entities = await self.entity_linker.link_entities(
            query,
            top_k=35,
            use_semantic=use_semantic
        )
        
        if not seed_entities:
            return self._create_empty_result(query, query_analysis)
        
        # ========== 阶段3: 知识图谱检索 ==========
        # 用于上下文生成的种子实体（优先使用增强检索器识别的种子）
        context_seed_entities = seed_entities
        
        if use_enhanced_retrieval and self.enhanced_retriever and query_analysis:
            # 使用增强检索器
            retrieval_config = RetrievalConfig(
                max_depth=max_depth,
                max_nodes=max_nodes,
                max_relationships=max_nodes * 2
            )
            
            retrieval_result = await self.enhanced_retriever.retrieve(
                query_analysis,
                retrieval_config
            )
            
            subgraph = {
                "nodes": retrieval_result.nodes,
                "relationships": retrieval_result.relationships,
                "stats": retrieval_result.metadata
            }

            # 使用增强检索器的种子实体生成上下文（确保一致性）
            if retrieval_result.seed_entities:
                # 将增强检索器的种子实体转换为LinkedEntity格式
                context_seed_entities = self._convert_to_linked_entities(
                    retrieval_result.seed_entities, seed_entities
                )
        else:
            # 使用传统检索
            traversal_config = TraversalConfig(
                max_depth=max_depth,
                max_nodes=max_nodes,
                max_relationships=max_nodes * 2,
                relationship_types=relationship_types,
                enable_multi_hop=True
            )
            
            subgraph = await self._traverse_subgraph_enhanced(
                seed_entities,
                traversal_config
            )
        
        # ========== 阶段4: 相关性排序 ==========
        ranked_results = None
        if self.ranker and query_analysis:
            ranking_config = RankingConfig(
                max_results=max_nodes
            )
            
            ranked_results = self.ranker.rank_results(
                subgraph.get("nodes", []),
                subgraph.get("relationships", []),
                query_analysis,
                ranking_config
            )
            
            pass
        
        # ========== 阶段5: 质量评估 ==========
        quality_result = self._assess_quality(subgraph, context_seed_entities, query_analysis)
        
        # ========== 阶段6: 上下文生成 ==========
        context_text = self._generate_context_text_enhanced(
            subgraph, context_seed_entities, query_analysis, ranked_results
        )
        context_structured = self._generate_context_structured_enhanced(
            subgraph, ranked_results
        )
        
        # ========== 阶段7: 推理路径生成 ==========
        reasoning_paths = []
        if include_paths:
            reasoning_paths = await self._generate_reasoning_paths_enhanced(
                context_seed_entities, subgraph, query
            )
        
        # ========== 阶段8: Prompt构建 ==========
        prompt_info = None
        if query_analysis:
            prompt_info = self.prompt_builder.build_prompt(
                query_analysis,
                context_text
            )
        
        # ========== 阶段9: 元数据收集 ==========
        search_metadata = {
            "semantic_search_enabled": use_semantic and self.semantic_search is not None,
            "intent_recognition_enabled": use_intent_recognition and self.intent_recognizer is not None,
            "enhanced_retrieval_enabled": use_enhanced_retrieval and self.enhanced_retriever is not None,
            "ranking_enabled": self.ranker is not None,
            "seed_entity_types": list(set(e.entity_type for e in seed_entities)),
            "match_types": list(set(e.match_type for e in seed_entities)),
            "traversal_depth": max_depth,
            "query_length": len(query),
        }
        
        if query_analysis:
            search_metadata.update({
                "detected_intent": query_analysis.intent.intent_type.value,
                "intent_confidence": query_analysis.intent.confidence,
                "detected_entities": [
                    {"type": e.entity_type.value, "value": e.value}
                    for e in query_analysis.entities
                ],
                "query_type": query_analysis.query_type,
            })
        
        # 构建结果
        result = GraphRAGResult(
            query=query,
            seed_entities=seed_entities,
            subgraph=subgraph,
            context_text=context_text,
            context_structured=context_structured,
            quality_score=quality_result["score"],
            quality_level=quality_result["level"],
            traversal_stats=subgraph.get("stats", {}),
            reasoning_paths=reasoning_paths,
            quality_result=quality_result,
            search_metadata=search_metadata,
            query_analysis=query_analysis,
            prompt_info=prompt_info,
            ranked_results=[
                {
                    "node_id": r.node_id,
                    "relevance_score": r.relevance_score,
                    "quality_score": r.quality_score,
                    "final_score": r.final_score,
                    "explanation": self.ranker.get_explanation(r, query_analysis) if self.ranker else ""
                }
                for r in (ranked_results or [])
            ]
        )
        
        return result
    
    async def query_with_intent(
        self,
        query: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        带意图识别的完整查询流程
        
        Args:
            query: 用户查询
            **kwargs: 其他参数
            
        Returns:
            包含查询结果和Prompt的完整响应
        """
        # 执行检索
        result = await self.local_search(
            query,
            use_intent_recognition=True,
            use_enhanced_retrieval=True,
            **kwargs
        )
        
        # 构建响应
        response = {
            "query": query,
            "intent": {
                "type": result.query_analysis.intent.intent_type.value if result.query_analysis else "unknown",
                "confidence": result.query_analysis.intent.confidence if result.query_analysis else 0,
                "entities": [
                    {"type": e.entity_type.value, "value": e.value}
                    for e in (result.query_analysis.entities if result.query_analysis else [])
                ]
            },
            "context": result.context_text,
            "context_structured": result.context_structured,
            "quality": {
                "score": result.quality_score,
                "level": result.quality_level,
                "details": result.quality_result
            },
            "prompt": result.prompt_info,
            "metadata": result.search_metadata,
        }
        
        return response
    
    async def _traverse_subgraph_enhanced(
        self,
        seed_entities: List[LinkedEntity],
        config: TraversalConfig
    ) -> Dict:
        """增强版子图遍历 - 分层检索：先检索depth=1的所有节点，再检索depth=2"""
        # 获取种子实体ID（优先使用台风实体）
        seed_ids = [e.entity_id for e in seed_entities if e.entity_type == "Typhoon"]
        if not seed_ids:
            seed_ids = [e.entity_id for e in seed_entities]
        
        all_nodes = {}
        all_relationships = {}
        
        # 添加种子节点（depth=0）
        seed_nodes = await self._get_seed_nodes_info(seed_ids)
        for node in seed_nodes:
            node_id = node.get("id")
            if node_id:
                all_nodes[node_id] = node
        
        # 按深度分层检索
        current_depth_nodes = set(seed_ids)  # 当前深度的节点
        visited_nodes = set(seed_ids)  # 已访问节点
        
        for depth in range(config.max_depth):
            if not current_depth_nodes or len(all_nodes) >= config.max_nodes:
                break
            next_depth_nodes = set()  # 下一层的节点
            
            # 遍历当前深度的所有节点
            for current_id in current_depth_nodes:
                if len(all_nodes) >= config.max_nodes:
                    break
                
                neighbors = await self._get_node_neighbors(
                    current_id,
                    config.relationship_types,
                    config.max_nodes - len(all_nodes)
                )
                
                # 添加节点
                for node in neighbors.get("nodes", []):
                    node_id = node.get("id")
                    if node_id and node_id not in all_nodes:
                        all_nodes[node_id] = node
                        
                        # 如果节点未访问过，加入下一层
                        if node_id not in visited_nodes:
                            visited_nodes.add(node_id)
                            next_depth_nodes.add(node_id)
                
                # 添加关系
                for rel in neighbors.get("relationships", []):
                    rel_key = f"{rel.get('source')}-{rel.get('type')}-{rel.get('target')}"
                    if rel_key not in all_relationships:
                        all_relationships[rel_key] = rel
            
            # 更新当前深度节点为下一层节点
            current_depth_nodes = next_depth_nodes
        
        relationships_list = list(all_relationships.values())[:config.max_relationships]
        
        return {
            "nodes": list(all_nodes.values()),
            "relationships": relationships_list,
            "stats": {
                "node_count": len(all_nodes),
                "relationship_count": len(relationships_list),
                "seed_count": len(seed_entities),
                "traversal_depth": config.max_depth,
                "traversal_strategy": "layered"  # 标记使用分层检索策略
            }
        }
    
    VALID_RELATIONSHIP_TYPES = {
        "LANDED_AT", "AFFECTED_AREA", "HAS_PATH_POINT",
        "OCCURRED_IN", "GENERATED_AT", "DISSIPATED_AT", "INTENSIFIED_TO",
        "WEAKENED_TO", "SIMILAR_TO", "NEXT", "HAS_INTENSITY"
        # PASSED_NEAR 已移除，AFFECTED_AREA 已包含经过附近的语义
    }
    
    async def _get_node_neighbors(
        self,
        node_id: str,
        relationship_types: Optional[List[str]],
        limit: int
    ) -> Dict:
        """获取节点的邻居"""
        validated_rel_types = []
        if relationship_types:
            for rt in relationship_types:
                if rt in self.VALID_RELATIONSHIP_TYPES:
                    validated_rel_types.append(rt)
                else:
                    pass
        
        rel_filter = ""
        if validated_rel_types:
            rel_types_str = ", ".join(f"'{rt}'" for rt in validated_rel_types)
            rel_filter = f"AND type(r) IN [{rel_types_str}]"
        
        query = """
        MATCH (start)
        WHERE (start:Typhoon AND start.typhoon_id = $node_id)
           OR (start:Location AND start.name = $node_id)
           OR (start:Time AND (start.year = $node_id OR toString(start.year) = $node_id))
           OR (start:Intensity AND start.level = $node_id)
           OR elementId(start) = $node_id
        WITH start
        OPTIONAL MATCH (start)-[r]-(n)
        WHERE 1=1 """ + rel_filter + """
        WITH start, r, n
        LIMIT $limit
        RETURN 
            CASE 
                WHEN start:Typhoon THEN start.typhoon_id
                WHEN start:Location THEN start.name
                WHEN start:Time THEN toString(start.year)
                WHEN start:Intensity THEN start.level
                ELSE elementId(start)
            END as start_id,
            CASE 
                WHEN n:Typhoon THEN n.typhoon_id
                WHEN n:Location THEN coalesce(n.name, 'loc_' + elementId(n))
                WHEN n:Time THEN coalesce(toString(n.year), 'time_' + elementId(n))
                WHEN n:Intensity THEN coalesce(n.level, 'intensity_' + elementId(n))
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
                        WHEN start:Time THEN toString(start.year)
                        ELSE elementId(start)
                    END
                ELSE CASE 
                    WHEN startNode(r):Typhoon THEN startNode(r).typhoon_id
                    WHEN startNode(r):Location THEN coalesce(startNode(r).name, 'loc_' + elementId(startNode(r)))
                    WHEN startNode(r):Time THEN coalesce(toString(startNode(r).year), 'time_' + elementId(startNode(r)))
                    ELSE elementId(startNode(r))
                END
            END as source_id,
            CASE 
                WHEN endNode(r) = start THEN 
                    CASE 
                        WHEN start:Typhoon THEN start.typhoon_id
                        WHEN start:Location THEN start.name
                        WHEN start:Time THEN toString(start.year)
                        ELSE elementId(start)
                    END
                ELSE CASE 
                    WHEN endNode(r):Typhoon THEN endNode(r).typhoon_id
                    WHEN endNode(r):Location THEN coalesce(endNode(r).name, 'loc_' + elementId(endNode(r)))
                    WHEN endNode(r):Time THEN coalesce(toString(endNode(r).year), 'time_' + elementId(endNode(r)))
                    ELSE elementId(endNode(r))
                END
            END as target_id
        """
        
        try:
            result = await self.neo4j.run(query, {"node_id": node_id, "limit": limit})
            
            nodes = []
            relationships = []
            seen_nodes = set()
            
            for record in result:
                neighbor_id = record.get("neighbor_id")
                if neighbor_id and neighbor_id not in seen_nodes:
                    nodes.append({
                        "id": neighbor_id,
                        "type": record.get("neighbor_type"),
                        "properties": record.get("neighbor_props", {})
                    })
                    seen_nodes.add(neighbor_id)
                
                rel_type = record.get("rel_type")
                if rel_type:
                    relationships.append({
                        "source": record.get("source_id"),
                        "target": record.get("target_id"),
                        "type": rel_type,
                        "properties": record.get("rel_props", {})
                    })
            
            return {"nodes": nodes, "relationships": relationships}
            
        except Exception:
            return {"nodes": [], "relationships": []}
    
    async def _get_seed_nodes_info(self, seed_ids: List[str]) -> List[Dict]:
        """获取种子节点的完整信息"""
        if not seed_ids:
            return []
        
        query = """
        MATCH (t:Typhoon)
        WHERE t.typhoon_id IN $seed_ids
        RETURN {
            id: t.typhoon_id,
            type: 'Typhoon',
            properties: properties(t)
        } as node
        """
        
        try:
            result = await self.neo4j.run(query, {"seed_ids": seed_ids})
            return [record["node"] for record in result if record.get("node")]
        except Exception:
            return []
    
    def _assess_quality(
        self, 
        subgraph: Dict, 
        seed_entities: List[LinkedEntity],
        query_analysis: Optional[TyphoonQueryAnalysis] = None
    ) -> Dict:
        """评估检索结果质量（增强版）"""
        nodes = subgraph.get("nodes", [])
        relationships = subgraph.get("relationships", [])
        
        # 1. 节点数量评分
        node_count = len(nodes)
        if 10 <= node_count <= 50:
            node_score = 1.0
        elif 5 <= node_count < 10:
            node_score = 0.7
        elif 50 < node_count <= 100:
            node_score = 0.8
        elif node_count < 5:
            node_score = 0.3
        else:
            node_score = 0.5
        
        # 2. 关系丰富度评分
        if node_count > 0:
            density = len(relationships) / node_count
            if 2 <= density <= 5:
                rel_score = 1.0
            elif 1 <= density < 2:
                rel_score = 0.7
            elif density > 5:
                rel_score = 0.8
            else:
                rel_score = 0.4
        else:
            rel_score = 0.0
        
        # 3. 种子匹配度
        if seed_entities:
            avg_confidence = sum(e.score for e in seed_entities) / len(seed_entities)
            seed_score = avg_confidence
        else:
            seed_score = 0.0
        
        # 4. 类型多样性
        types = set(node.get("type") for node in nodes)
        if len(types) >= 4:
            diversity_score = 1.0
        elif len(types) >= 2:
            diversity_score = 0.7
        else:
            diversity_score = 0.4
        
        # 5. 属性完整度
        if nodes:
            total_attr_score = 0
            for node in nodes:
                if node.get("type") == "Typhoon":
                    props = node.get("properties", {})
                    required = ["name_cn", "year", "max_wind_speed"]
                    present = sum(1 for attr in required if props.get(attr))
                    total_attr_score += present / len(required)
                else:
                    total_attr_score += 0.5
            attr_score = total_attr_score / len(nodes)
        else:
            attr_score = 0.0
        
        # 6. 语义匹配比例
        semantic_ratio = 0.0
        if seed_entities:
            semantic_count = sum(1 for e in seed_entities if e.match_type == "semantic")
            semantic_ratio = semantic_count / len(seed_entities)
        
        # 7. 意图匹配度（新增）
        intent_score = 0.5
        if query_analysis:
            intent_score = query_analysis.intent.confidence
        
        # 计算总分
        weights = {
            "node_count": 0.15,
            "relationship_richness": 0.15,
            "seed_match": 0.15,
            "type_diversity": 0.10,
            "attribute_completeness": 0.10,
            "semantic_match": 0.10,
            "intent_match": 0.15,  # 新增意图匹配权重
            "completeness": 0.10
        }
        
        total_score = (
            node_score * weights["node_count"] +
            rel_score * weights["relationship_richness"] +
            seed_score * weights["seed_match"] +
            diversity_score * weights["type_diversity"] +
            attr_score * weights["attribute_completeness"] +
            semantic_ratio * weights["semantic_match"] +
            intent_score * weights["intent_match"] +
            min(node_count / 50, 1.0) * weights["completeness"]
        )
        
        if total_score >= 0.7:
            level = "high"
        elif total_score >= 0.4:
            level = "medium"
        else:
            level = "low"
        
        return {
            "score": round(total_score, 2),
            "level": level,
            "factors": {
                "node_count": round(node_score, 2),
                "relationship_richness": round(rel_score, 2),
                "seed_match": round(seed_score, 2),
                "type_diversity": round(diversity_score, 2),
                "attribute_completeness": round(attr_score, 2),
                "semantic_match": round(semantic_ratio, 2),
                "intent_match": round(intent_score, 2)
            }
        }
    
    def _generate_context_text_enhanced(
        self, 
        subgraph: Dict, 
        seed_entities: List[LinkedEntity],
        query_analysis: Optional[TyphoonQueryAnalysis] = None,
        ranked_results: Optional[List] = None
    ) -> str:
        """生成增强版文本上下文"""
        parts = []
        nodes = subgraph.get("nodes", [])
        relationships = subgraph.get("relationships", [])
        
        # 优先使用排序后的结果
        if ranked_results:
            top_node_ids = {r.node_id for r in ranked_results[:30]}
            nodes = [n for n in nodes if n.get("id") in top_node_ids]
        
        typhoon_seed_entities = [
            e for e in seed_entities 
            if e.entity_type == "Typhoon" and e.entity_name != "台风"
        ]
        
        typhoon_props_map = {}
        for node in nodes:
            if node.get("type") == "Typhoon":
                typhoon_props_map[node.get("id")] = node.get("properties", {})
        
        # 添加意图信息
        if query_analysis:
            parts.append(f"【查询意图】{query_analysis.intent.intent_type.value} "
                        f"(置信度: {query_analysis.intent.confidence:.2f})")
            parts.append("")
        
        # 台风实体详细信息
        if typhoon_seed_entities:
            years = [e.properties.get("year") for e in typhoon_seed_entities if e.properties.get("year")]
            
            is_year_query = False
            target_year = None
            if len(typhoon_seed_entities) > 3:
                from collections import Counter
                year_counts = Counter(years)
                if year_counts:
                    most_common_year, count = year_counts.most_common(1)[0]
                    if count / len(typhoon_seed_entities) > 0.5:
                        is_year_query = True
                        target_year = most_common_year
                        typhoon_seed_entities = [
                            e for e in typhoon_seed_entities 
                            if e.properties.get("year") == target_year
                        ]
            
            display_count = len(typhoon_seed_entities) if is_year_query else min(len(typhoon_seed_entities), 5)
            
            if is_year_query:
                parts.append(f"根据知识图谱检索，{years[0]}年共有{len(typhoon_seed_entities)}个台风：")
            else:
                parts.append(f"根据知识图谱检索，找到{len(typhoon_seed_entities)}个相关台风：")
            parts.append("")
            
            for entity in typhoon_seed_entities[:display_count]:
                node_props = typhoon_props_map.get(entity.entity_id, entity.properties)
                
                name = entity.entity_name
                year = node_props.get("year", "")
                typhoon_id = node_props.get("typhoon_id", entity.entity_id)
                
                parts.append(f"【{name}】（编号：{typhoon_id}）")
                if year:
                    parts.append(f"- 年份：{year}年")
                if node_props.get("max_wind_speed"):
                    parts.append(f"- 最大风速：{node_props['max_wind_speed']} m/s")
                if node_props.get("min_pressure"):
                    parts.append(f"- 最低气压：{node_props['min_pressure']} hPa")
                if node_props.get("peak_intensity"):
                    parts.append(f"- 最高强度：{node_props['peak_intensity']}")
                if node_props.get("duration_hours"):
                    parts.append(f"- 持续时间：{node_props['duration_hours']} 小时")
                if node_props.get("start_time"):
                    parts.append(f"- 生成时间：{node_props['start_time']}")
                if node_props.get("end_time"):
                    parts.append(f"- 消散时间：{node_props['end_time']}")
                
                if entity.match_type == "semantic":
                    parts.append(f"- 匹配方式：语义匹配")
                elif entity.match_type == "hybrid":
                    parts.append(f"- 匹配方式：混合匹配")
                
                parts.append("")
            
            if not is_year_query and len(typhoon_seed_entities) > display_count:
                parts.append(f"... 以及其他 {len(typhoon_seed_entities) - display_count} 个台风")
                parts.append("")
        
        # 登陆信息
        landed_rels = [
            r for r in relationships
            if r.get("type") == "LANDED_AT" and not str(r.get("source", "")).isdigit()
        ]
        if landed_rels:
            parts.append("【登陆信息】")
            for rel in landed_rels[:5]:
                props = rel.get("properties", {})
                source = rel.get("source", "")
                target = rel.get("target", "")
                
                if source and not source.startswith("20") and target:
                    land_info = f"- {source} 登陆 {target}"
                    if props.get("land_time"):
                        land_info += f"，时间：{props['land_time']}"
                    if props.get("intensity"):
                        land_info += f"，登陆强度：{props['intensity']}"
                    parts.append(land_info)
            parts.append("")
        
        # 影响地区信息
        affected_rels = [
            r for r in relationships
            if r.get("type") == "AFFECTED_AREA" and not str(r.get("source", "")).isdigit()
        ]
        if affected_rels:
            parts.append("【影响地区】")
            affected_areas = {}
            for rel in affected_rels:
                source = rel.get("source", "")
                target = rel.get("target", "")
                if source and target:
                    if source not in affected_areas:
                        affected_areas[source] = []
                    affected_areas[source].append(target)
            
            for typhoon_name, areas in list(affected_areas.items())[:3]:
                parts.append(f"- {typhoon_name}：{', '.join(areas[:5])}")
            parts.append("")
        
        # 统计信息
        stats = subgraph.get("stats", {})
        parts.append(f"检索统计：知识图谱中包含 {stats.get('node_count', 0)} 个相关实体，"
                    f"{stats.get('relationship_count', 0)} 个关系。")
        
        return "\n".join(parts)
    
    def _generate_context_structured_enhanced(
        self, 
        subgraph: Dict,
        ranked_results: Optional[List] = None
    ) -> Dict:
        """生成增强版结构化上下文"""
        nodes = subgraph.get("nodes", [])
        
        # 优先使用排序后的结果
        if ranked_results:
            top_node_ids = {r.node_id for r in ranked_results[:30]}
            nodes = [n for n in nodes if n.get("id") in top_node_ids]
        
        return {
            "entities": {
                "typhoons": [
                    {
                        "id": n.get("id"),
                        "name": n.get("properties", {}).get("name_cn"),
                        "year": n.get("properties", {}).get("year"),
                        "max_wind_speed": n.get("properties", {}).get("max_wind_speed"),
                        "min_pressure": n.get("properties", {}).get("min_pressure"),
                        "peak_intensity": n.get("properties", {}).get("peak_intensity"),
                    }
                    for n in nodes if n.get("type") == "Typhoon"
                ],
                "locations": [
                    {
                        "id": n.get("id"),
                        "name": n.get("properties", {}).get("name"),
                    }
                    for n in nodes if n.get("type") == "Location"
                ],
                "path_points": [
                    {
                        "id": n.get("id"),
                        "lat": n.get("properties", {}).get("lat"),
                        "lon": n.get("properties", {}).get("lon"),
                        "timestamp": n.get("properties", {}).get("timestamp"),
                    }
                    for n in nodes if n.get("type") == "PathPoint"
                ]
            },
            "relationships": [
                {
                    "source": r.get("source"),
                    "target": r.get("target"),
                    "type": r.get("type"),
                    "properties": r.get("properties", {})
                }
                for r in subgraph.get("relationships", [])
            ],
            "stats": subgraph.get("stats", {}),
            "ranked_results": [
                {
                    "node_id": r.node_id,
                    "final_score": r.final_score,
                    "factors": r.ranking_factors
                }
                for r in (ranked_results or [])
            ] if ranked_results else []
        }
    
    async def _generate_reasoning_paths_enhanced(
        self, 
        seed_entities: List[LinkedEntity], 
        subgraph: Dict,
        query: str
    ) -> List[Dict]:
        """生成增强版推理路径"""
        paths = []
        relationships = subgraph.get("relationships", [])
        
        # 登陆路径
        for seed in seed_entities:
            if seed.entity_type == "Typhoon":
                land_rels = [
                    r for r in relationships
                    if r.get("source") == seed.entity_id and r.get("type") == "LANDED_AT"
                ]
                
                for rel in land_rels:
                    target = rel.get("target")
                    props = rel.get("properties", {})
                    path_desc = f"{seed.entity_name} 登陆 {target}"
                    if props.get("land_time"):
                        path_desc += f"（时间：{props['land_time']}）"
                    
                    paths.append({
                        "path_description": path_desc,
                        "source": seed.entity_id,
                        "target": target,
                        "relationship": "LANDED_AT",
                        "path_type": "landfall"
                    })
        
        # 影响路径
        for seed in seed_entities:
            if seed.entity_type == "Typhoon":
                affected_rels = [
                    r for r in relationships
                    if r.get("source") == seed.entity_id and r.get("type") == "AFFECTED_AREA"
                ]
                
                if affected_rels:
                    targets = [r.get("target") for r in affected_rels[:3]]
                    paths.append({
                        "path_description": f"{seed.entity_name} 影响了 {', '.join(targets)}",
                        "source": seed.entity_id,
                        "targets": targets,
                        "relationship": "AFFECTED_AREA",
                        "path_type": "impact"
                    })
        
        # 强度路径
        for seed in seed_entities:
            if seed.entity_type == "Typhoon":
                intensity_rels = [
                    r for r in relationships
                    if r.get("source") == seed.entity_id and r.get("type") == "HAS_INTENSITY"
                ]
                
                for rel in intensity_rels:
                    target = rel.get("target")
                    props = rel.get("properties", {})
                    if props.get("level"):
                        paths.append({
                            "path_description": f"{seed.entity_name} 强度等级为 {props['level']}",
                            "source": seed.entity_id,
                            "target": target,
                            "relationship": "HAS_INTENSITY",
                            "path_type": "intensity"
                        })
        
        return paths[:10]
    
    def _convert_to_linked_entities(
        self,
        seed_entities: List[Dict],
        original_linked_entities: List[LinkedEntity]
    ) -> List[LinkedEntity]:
        """
        将增强检索器的种子实体转换为LinkedEntity格式
        
        Args:
            seed_entities: 增强检索器识别的种子实体
            original_linked_entities: 原始实体链接器返回的实体（用于获取额外信息）
            
        Returns:
            List[LinkedEntity]: 转换后的LinkedEntity列表
        """
        # 创建原始实体的查找字典
        original_map = {e.entity_id: e for e in original_linked_entities}
        
        linked_entities = []
        for seed in seed_entities:
            seed_id = seed.get("id")
            
            # 如果原始实体中有这个ID，使用原始实体的信息
            if seed_id in original_map:
                original = original_map[seed_id]
                linked_entities.append(LinkedEntity(
                    mention=original.mention,
                    entity_id=seed_id,
                    entity_type=seed.get("type", original.entity_type),
                    entity_name=seed.get("name", original.entity_name),
                    score=seed.get("confidence", original.score),
                    properties=seed.get("properties", original.properties),
                    match_type=seed.get("source", original.match_type)
                ))
            else:
                # 创建新的LinkedEntity
                linked_entities.append(LinkedEntity(
                    mention=seed.get("name", seed_id),
                    entity_id=seed_id,
                    entity_type=seed.get("type", "Typhoon"),
                    entity_name=seed.get("name", seed_id),
                    score=seed.get("confidence", 0.9),
                    properties=seed.get("properties", {}),
                    match_type=seed.get("source", "retrieval")
                ))
        
        return linked_entities
    
    def _create_empty_result(
        self, 
        query: str, 
        query_analysis: Optional[TyphoonQueryAnalysis] = None
    ) -> GraphRAGResult:
        """创建空结果"""
        return GraphRAGResult(
            query=query,
            seed_entities=[],
            subgraph={"nodes": [], "relationships": [], "stats": {"node_count": 0, "relationship_count": 0}},
            context_text="未找到相关实体信息。",
            context_structured={"entities": {}, "relationships": []},
            quality_score=0.0,
            quality_level="low",
            traversal_stats={"node_count": 0, "relationship_count": 0},
            reasoning_paths=[],
            search_metadata={"empty_result": True},
            query_analysis=query_analysis
        )
