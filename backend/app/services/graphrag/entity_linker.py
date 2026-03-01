"""
实体链接服务
将自然语言查询中的提及映射到知识图谱中的实体
支持语义搜索和传统关键词匹配
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

from loguru import logger

from .semantic_search import SemanticEntitySearch, SemanticEntity


@dataclass
class LinkedEntity:
    """链接的实体"""
    mention: str  # 查询中的提及文本
    entity_id: str  # 图谱中的实体ID
    entity_type: str  # 实体类型
    entity_name: str  # 实体名称
    score: float  # 匹配分数 (0-1)
    properties: Dict  # 实体属性
    match_type: str = "keyword"  # 匹配类型: keyword, semantic, hybrid


class EntityLinker:
    """实体链接器 - 增强版（支持语义搜索）"""
    
    # 台风相关实体类型
    TYPHOON_TYPES = ["Typhoon", "PathPoint"]
    LOCATION_TYPES = ["Location"]
    TIME_TYPES = ["Time"]
    INTENSITY_TYPES = ["Intensity"]
    
    # 常见台风名称列表（用于精确匹配）
    COMMON_TYPHOON_NAMES = [
        # 2025-2026年台风
        "天琴", "凤凰", "海鸥", "风神", "娜基莉", "夏浪", "麦德姆", "博罗依",
        "浣熊", "桦加沙", "米娜", "塔巴", "琵琶", "蓝湖", "剑鱼", "玲玲",
        "杨柳", "白鹿", "罗莎", "竹节草", "范斯高", "韦帕", "百合", "丹娜丝",
        "木恩", "圣帕", "蝴蝶", "洛鞍", "银杏", "桃芝", "万宜", "天兔",
        # 历史著名台风
        "龙王", "山竹", "利奇马", "烟花", "灿都", "查特安", "榕树", "艾利", "桑达",
        "圆规", "南川", "玛瑙", "妮亚图", "雷伊", "舒力基", "彩云", "小熊",
        "查帕卡", "卢碧", "银河", "妮妲", "奥麦斯", "康森", "灿鸿", "浪卡",
        "莫拉菲", "天鹅", "艾莎尼", "环高", "科罗旺", "杜鹃", "纳莎", "纳沙"
    ]
    
    # 地理关键词映射
    LOCATION_KEYWORDS = {
        "广东": "广东", "福建": "福建", "浙江": "浙江", "海南": "海南",
        "台湾": "台湾", "香港": "香港", "澳门": "澳门", "广西": "广西",
        "江苏": "江苏", "上海": "上海", "山东": "山东", "辽宁": "辽宁",
        "河北": "河北", "天津": "天津", "江西": "江西", "湖南": "湖南",
        "湖北": "湖北", "安徽": "安徽", "河南": "河南",
        # 主要城市
        "广州": "广州", "深圳": "深圳", "珠海": "珠海", "汕头": "汕头",
        "湛江": "湛江", "江门": "江门", "茂名": "茂名", "阳江": "阳江",
        "韶关": "韶关", "惠州": "惠州",
        "厦门": "厦门", "福州": "福州", "泉州": "泉州", "漳州": "漳州",
        "宁德": "宁德", "莆田": "莆田", "龙岩": "龙岩",
        "杭州": "杭州", "宁波": "宁波", "温州": "温州", "台州": "台州",
        "舟山": "舟山", "嘉兴": "嘉兴", "绍兴": "绍兴",
        "海口": "海口", "三亚": "三亚", "三沙": "三沙", "儋州": "儋州",
        "文昌": "文昌", "琼海": "琼海",
        "台北": "台北", "高雄": "高雄", "台中": "台中", "花莲": "花莲",
        "台南": "台南", "基隆": "基隆",
        "南京": "南京", "苏州": "苏州", "无锡": "无锡", "常州": "常州",
        "南通": "南通",
        "青岛": "青岛", "烟台": "烟台", "威海": "威海", "日照": "日照",
        "潍坊": "潍坊",
    }
    
    # 强度等级关键词
    INTENSITY_KEYWORDS = {
        "热带低压": ["TD"],
        "热带风暴": ["TS"],
        "强热带风暴": ["STS"],
        "台风": ["TY"],
        "强台风": ["STY"],
        "超强台风": ["SuperTY"],
    }
    
    # 语义查询意图映射
    QUERY_INTENT_PATTERNS = {
        "strongest": {
            "patterns": ["最强", "最大风速", "最高强度", "最强台风"],
            "semantic_queries": ["风速最高的台风", "强度最大的台风", "最强台风"],
            "attributes": ["max_wind_speed", "peak_intensity"]
        },
        "weakest": {
            "patterns": ["最弱", "最小风速", "最低强度"],
            "semantic_queries": ["风速最低的台风", "强度最小的台风"],
            "attributes": ["max_wind_speed", "peak_intensity"]
        },
        "recent": {
            "patterns": ["最近", "最新", "近年"],
            "semantic_queries": ["最近发生的台风", "最新的台风"],
            "attributes": ["year", "start_time"]
        },
        "landfall": {
            "patterns": ["登陆", "登陆地点", "登陆时间"],
            "semantic_queries": ["登陆的台风", "登陆地点"],
            "attributes": ["landed_at", "land_time"]
        },
        "impact": {
            "patterns": ["影响", "受灾", "损失", "伤亡"],
            "semantic_queries": ["造成影响的台风", "影响地区的台风"],
            "attributes": ["affected_area", "damage"]
        },
        "comparison": {
            "patterns": ["对比", "比较", "vs", "和.*相比", "哪个更"],
            "semantic_queries": ["台风对比", "台风比较"],
            "attributes": ["max_wind_speed", "peak_intensity", "duration"]
        }
    }
    
    def __init__(self, neo4j_client, enable_semantic_search: bool = True):
        """
        初始化实体链接器
        
        Args:
            neo4j_client: Neo4j数据库客户端
            enable_semantic_search: 是否启用语义搜索
        """
        self.neo4j = neo4j_client
        self.enable_semantic_search = enable_semantic_search
        
        # 初始化语义搜索（如果启用）
        self.semantic_search = None
        if enable_semantic_search:
            try:
                self.semantic_search = SemanticEntitySearch(neo4j_client)
                logger.info("语义搜索已启用")
            except Exception as e:
                logger.warning(f"语义搜索初始化失败: {e}，将使用关键词匹配")
                self.enable_semantic_search = False
    
    async def link_entities(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        top_k: int = 20,
        use_semantic: bool = True
    ) -> List[LinkedEntity]:
        """
        将查询中的实体提及链接到知识图谱（增强版）
        
        Args:
            query: 用户查询
            entity_types: 限制的实体类型
            top_k: 返回的最大实体数
            use_semantic: 是否使用语义搜索
            
        Returns:
            链接的实体列表
        """
        linked_entities = []
        
        # 1. 分析查询意图
        query_intent = self._analyze_query_intent(query)
        logger.info(f"查询意图分析: {query_intent}")
        
        # 2. 提取查询中的候选提及
        mentions = self._extract_mentions(query)
        logger.info(f"提取到 {len(mentions)} 个候选提及: {mentions}")
        
        # 检测是否为年份查询（包含4位年份数字）
        year_pattern = r'\b(19|20)\d{2}\b'
        year_match = re.search(year_pattern, query)
        is_year_query = year_match is not None
        target_year = int(year_match.group(0)) if year_match else None
        
        logger.info(f"年份查询检测: query='{query}', is_year_query={is_year_query}, target_year={target_year}")
        
        # 3. 对每个提及进行实体链接
        # 年份查询时，只处理年份提及，忽略其他提及（如"台风"、"年出现了哪些"）
        if is_year_query:
            # 只处理年份提及
            year_mentions = [m for m in mentions if m.isdigit() and len(m) == 4]
            for mention in year_mentions:
                entities = await self._link_mention(
                    mention,
                    entity_types=entity_types,
                    top_k=100  # 获取该年份所有台风
                )
                linked_entities.extend(entities)
            logger.info(f"年份查询模式：只处理年份提及 {year_mentions}，找到 {len(linked_entities)} 个实体")
        else:
            # 非年份查询，正常处理所有提及
            for mention in mentions:
                mention_top_k = 100 if (mention.isdigit() and len(mention) == 4) else 5
                entities = await self._link_mention(
                    mention,
                    entity_types=entity_types,
                    top_k=mention_top_k
                )
                linked_entities.extend(entities)
        
        # 4. 语义搜索（如果启用且需要）
        # 年份查询时禁用语义搜索，避免混入其他年份的台风
        if use_semantic and self.enable_semantic_search and self.semantic_search and not is_year_query:
            semantic_entities = await self._semantic_entity_search(
                query, query_intent, mentions, top_k=top_k
            )
            linked_entities.extend(semantic_entities)
        
        # 5. 年份查询时，过滤掉非目标年份的台风
        if is_year_query and target_year:
            linked_entities = [
                e for e in linked_entities 
                if e.entity_type != "Typhoon" or e.properties.get("year") == target_year
            ]
            logger.info(f"年份查询过滤：只保留{target_year}年的台风，剩余{len(linked_entities)}个实体")
        
        # 6. 去重并按分数排序
        seen_ids = set()
        unique_entities = []
        for entity in sorted(linked_entities, key=lambda x: x.score, reverse=True):
            if entity.entity_id not in seen_ids:
                seen_ids.add(entity.entity_id)
                unique_entities.append(entity)
        
        # 7. 如果提及链接结果较少，尝试全文搜索补充
        if len(unique_entities) < 2:
            additional = await self._fuzzy_search(query, entity_types, top_k - len(unique_entities))
            for entity in additional:
                if entity.entity_id not in seen_ids:
                    unique_entities.append(entity)
        
        return unique_entities[:top_k]
    
    def _analyze_query_intent(self, query: str) -> Dict:
        """
        分析查询意图
        
        Args:
            query: 用户查询
            
        Returns:
            查询意图信息
        """
        intent_info = {
            "primary_intent": None,
            "semantic_queries": [],
            "attributes": [],
            "confidence": 0.0
        }
        
        for intent_name, intent_data in self.QUERY_INTENT_PATTERNS.items():
            for pattern in intent_data["patterns"]:
                if re.search(pattern, query):
                    intent_info["primary_intent"] = intent_name
                    intent_info["semantic_queries"] = intent_data["semantic_queries"]
                    intent_info["attributes"] = intent_data["attributes"]
                    intent_info["confidence"] = 0.8
                    return intent_info
        
        return intent_info
    
    async def _semantic_entity_search(
        self,
        query: str,
        query_intent: Dict,
        mentions: List[str],
        top_k: int = 10
    ) -> List[LinkedEntity]:
        """
        执行语义实体搜索
        
        Args:
            query: 原始查询
            query_intent: 查询意图
            mentions: 提取的关键词
            top_k: 返回数量
            
        Returns:
            链接的实体列表
        """
        if not self.semantic_search:
            return []
        
        linked_entities = []
        
        # 构建语义查询
        semantic_queries = []
        
        # 基于意图的语义查询
        if query_intent.get("semantic_queries"):
            semantic_queries.extend(query_intent["semantic_queries"])
        
        # 原始查询也作为语义查询
        semantic_queries.append(query)
        
        # 对每个语义查询进行搜索
        seen_ids = set()
        for semantic_query in semantic_queries:
            try:
                results = await self.semantic_search.search_with_keywords(
                    query=semantic_query,
                    keywords=mentions,
                    top_k=top_k,
                    semantic_weight=0.7
                )
                
                for result in results:
                    if result.entity_id not in seen_ids:
                        seen_ids.add(result.entity_id)
                        linked_entities.append(LinkedEntity(
                            mention=semantic_query,
                            entity_id=result.entity_id,
                            entity_type=result.entity_type,
                            entity_name=result.entity_name,
                            score=result.score * 0.95,  # 语义搜索分数稍微降权
                            properties=result.properties or {},
                            match_type="semantic"
                        ))
            except Exception as e:
                logger.error(f"语义搜索失败: {e}")
        
        return linked_entities
    
    def _extract_mentions(self, query: str) -> List[str]:
        """
        从查询中提取候选实体提及（增强版）
        
        Args:
            query: 用户查询
            
        Returns:
            提及列表
        """
        mentions = []
        
        # 1. 提取引号中的内容
        quoted_pattern = r'["\']([^"\']{2,20})["\']'
        mentions.extend(re.findall(quoted_pattern, query))
        
        # 2. 提取中文台风名称（XX台风 或 台风XX）
        # 格式1: XX台风（如：龙王台风）
        typhoon_pattern1 = r'([\u4e00-\u9fa5]{2,6})(?=台风|飓风|气旋)'
        for match in re.finditer(typhoon_pattern1, query):
            name = match.group(1)
            exclude_words = {"这个", "那个", "什么", "哪个", "一个", "热带", "强热带"}
            if name not in exclude_words and len(name) >= 2:
                mentions.append(name)
        
        # 格式2: 台风XX（如：台风龙王）
        for name in self.COMMON_TYPHOON_NAMES:
            if f"台风{name}" in query or f"飓风{name}" in query or f"气旋{name}" in query:
                if name not in mentions:
                    mentions.append(name)
        
        # 3. 提取台风编号（6位数字）
        id_pattern = r'\b(19|20)(\d{2})(0[1-9]|1[0-2])\b'
        for match in re.finditer(id_pattern, query):
            mentions.append(match.group(0))
        
        # 4. 提取年份（支持1960-2035年）
        year_pattern = r'(?:^|[^0-9])(19[6-9]\d|20[0-3]\d)(?:[^0-9]|$)'
        for match in re.finditer(year_pattern, query):
            year_str = match.group(1)
            year = int(year_str)
            if 1960 <= year <= 2035:
                mentions.append(year_str)
        
        # 5. 提取地理位置
        for location, normalized in self.LOCATION_KEYWORDS.items():
            if location in query:
                mentions.append(normalized)
        
        # 6. 提取强度等级
        for intensity in self.INTENSITY_KEYWORDS.keys():
            if intensity in query:
                mentions.append(intensity)
        
        return list(set(mentions))  # 去重
    
    async def _link_mention(
        self, 
        mention: str, 
        entity_types: Optional[List[str]] = None,
        top_k: int = 2
    ) -> List[LinkedEntity]:
        """
        将单个提及链接到实体
        
        Args:
            mention: 提及文本
            entity_types: 实体类型限制
            top_k: 返回数量
            
        Returns:
            链接的实体列表
        """
        entities = []
        
        # 判断提及类型并选择查询策略
        if mention.isdigit() and len(mention) == 6:
            # 台风编号
            entities = await self._search_by_typhoon_id(mention)
        elif mention.isdigit() and len(mention) == 4:
            # 年份 - 使用更大的limit来获取该年份所有台风
            entities = await self._search_by_year(mention, limit=top_k)
        elif mention in self.LOCATION_KEYWORDS.values():
            # 地理位置
            entities = await self._search_by_location(mention)
        elif mention in self.INTENSITY_KEYWORDS:
            # 强度等级
            entities = await self._search_by_intensity(mention)
        else:
            # 通用名称搜索
            entities = await self._search_by_name(mention, entity_types, top_k)
        
        return entities
    
    async def _search_by_typhoon_id(self, typhoon_id: str) -> List[LinkedEntity]:
        """通过台风编号搜索"""
        query = """
        MATCH (t:Typhoon {typhoon_id: $typhoon_id})
        RETURN t as entity, 'Typhoon' as type, 0.95 as score
        LIMIT 1
        """
        
        try:
            result = await self.neo4j.run(query, {"typhoon_id": typhoon_id})
            entities = []
            for record in result:
                entity_data = record["entity"]
                entities.append(LinkedEntity(
                    mention=typhoon_id,
                    entity_id=typhoon_id,
                    entity_type="Typhoon",
                    entity_name=entity_data.get("name_cn") or entity_data.get("name_en") or typhoon_id,
                    score=record["score"],
                    properties=dict(entity_data),
                    match_type="keyword"
                ))
            return entities
        except Exception as e:
            logger.error(f"通过编号搜索台风失败: {e}")
            return []
    
    async def _search_by_year(self, year: str, limit: int = 100) -> List[LinkedEntity]:
        """通过年份搜索 - 返回该年份的所有台风
        
        直接使用 Typhoon 节点的 year 属性查询，而不是通过 OCCURRED_IN 关系到 Time 节点
        """
        query = """
        MATCH (t:Typhoon {year: $year})
        RETURN t as entity, 'Typhoon' as type, 0.95 as score
        ORDER BY t.max_wind_speed DESC
        LIMIT $limit
        """

        try:
            result = await self.neo4j.run(query, {"year": int(year), "limit": limit})
            entities = []
            for record in result:
                entity_data = record["entity"]
                typhoon_id = entity_data.get("typhoon_id", "")
                entities.append(LinkedEntity(
                    mention=year,
                    entity_id=typhoon_id,
                    entity_type="Typhoon",
                    entity_name=entity_data.get("name_cn") or entity_data.get("name_en") or typhoon_id,
                    score=record["score"],
                    properties=dict(entity_data),
                    match_type="keyword"
                ))

            logger.info(f"年份 {year} 查询到 {len(entities)} 个台风")
            return entities
        except Exception as e:
            logger.error(f"通过年份搜索失败: {e}")
            return []
    
    async def _search_by_location(self, location: str) -> List[LinkedEntity]:
        """通过地理位置搜索"""
        query = """
        MATCH (l:Location)
        WHERE l.name CONTAINS $location
        RETURN l as entity, 'Location' as type, 
               CASE WHEN l.name = $location THEN 0.95 ELSE 0.8 END as score
        LIMIT 1
        """
        
        try:
            result = await self.neo4j.run(query, {"location": location})
            entities = []
            for record in result:
                entity_data = record["entity"]
                entities.append(LinkedEntity(
                    mention=location,
                    entity_id=f"loc_{entity_data.get('name')}",
                    entity_type="Location",
                    entity_name=entity_data.get("name"),
                    score=record["score"],
                    properties=dict(entity_data),
                    match_type="keyword"
                ))
            return entities
        except Exception as e:
            logger.error(f"通过地理位置搜索失败: {e}")
            return []
    
    async def _search_by_intensity(self, intensity: str) -> List[LinkedEntity]:
        """通过强度等级搜索"""
        codes = self.INTENSITY_KEYWORDS.get(intensity, [])
        if not codes:
            return []
        
        query = """
        MATCH (i:Intensity)
        WHERE i.level IN $codes OR i.name_cn = $intensity
        RETURN i as entity, 'Intensity' as type, 0.9 as score
        LIMIT 1
        """
        
        try:
            result = await self.neo4j.run(query, {"codes": codes, "intensity": intensity})
            entities = []
            for record in result:
                entity_data = record["entity"]
                entities.append(LinkedEntity(
                    mention=intensity,
                    entity_id=f"intensity_{entity_data.get('level')}",
                    entity_type="Intensity",
                    entity_name=entity_data.get("name_cn"),
                    score=record["score"],
                    properties=dict(entity_data),
                    match_type="keyword"
                ))
            return entities
        except Exception as e:
            logger.error(f"通过强度搜索失败: {e}")
            return []
    
    async def _search_by_name(
        self, 
        name: str, 
        entity_types: Optional[List[str]] = None,
        top_k: int = 2
    ) -> List[LinkedEntity]:
        """通过名称搜索（支持模糊匹配）"""
        # 构建类型过滤
        type_filter = ""
        if entity_types:
            type_list = "|".join(f":{t}" for t in entity_types)
            type_filter = f"WHERE node:{type_list}"
        
        query = f"""
        MATCH (node)
        {type_filter}
        WHERE (node:Typhoon AND (node.name_cn CONTAINS $name OR node.name_en CONTAINS $name))
           OR (node:Location AND node.name CONTAINS $name)
        RETURN node as entity, labels(node)[0] as type,
               CASE 
                   WHEN node.name_cn = $name OR node.name = $name THEN 0.95
                   WHEN node.name_cn STARTS WITH $name OR node.name STARTS WITH $name THEN 0.85
                   ELSE 0.7
               END as score
        ORDER BY score DESC
        LIMIT $limit
        """
        
        try:
            result = await self.neo4j.run(query, {"name": name, "limit": top_k})
            entities = []
            for record in result:
                entity_data = record["entity"]
                entity_type = record["type"]
                
                # 确定实体ID和名称
                if entity_type == "Typhoon":
                    entity_id = entity_data.get("typhoon_id")
                    entity_name = entity_data.get("name_cn") or entity_data.get("name_en") or entity_id
                elif entity_type == "Location":
                    entity_id = f"loc_{entity_data.get('name')}"
                    entity_name = entity_data.get("name")
                else:
                    entity_id = str(entity_data.get("id", ""))
                    entity_name = entity_data.get("name", entity_id)
                
                entities.append(LinkedEntity(
                    mention=name,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    entity_name=entity_name,
                    score=record["score"],
                    properties=dict(entity_data),
                    match_type="keyword"
                ))
            return entities
        except Exception as e:
            logger.error(f"通过名称搜索失败: {e}")
            return []
    
    async def _fuzzy_search(
        self, 
        query: str, 
        entity_types: Optional[List[str]] = None,
        limit: int = 3
    ) -> List[LinkedEntity]:
        """
        全文模糊搜索（当精确匹配不足时使用）
        """
        search_query = """
        MATCH (node:Typhoon)
        WHERE node.name_cn CONTAINS $query 
           OR node.name_en CONTAINS $query
           OR node.typhoon_id CONTAINS $query
        RETURN node as entity, 'Typhoon' as type, 0.6 as score
        LIMIT $limit
        """
        
        try:
            result = await self.neo4j.run(search_query, {"query": query[:10], "limit": limit})
            entities = []
            for record in result:
                entity_data = record["entity"]
                entity_id = entity_data.get("typhoon_id")
                entity_name = entity_data.get("name_cn") or entity_data.get("name_en") or entity_id
                
                entities.append(LinkedEntity(
                    mention=query,
                    entity_id=entity_id,
                    entity_type="Typhoon",
                    entity_name=entity_name,
                    score=record["score"],
                    properties=dict(entity_data),
                    match_type="keyword"
                ))
            return entities
        except Exception as e:
            logger.error(f"模糊搜索失败: {e}")
            return []
