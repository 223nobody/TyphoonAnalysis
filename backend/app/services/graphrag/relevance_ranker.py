"""
检索结果相关性排序模块
建立检索结果的相关性排序机制，确保返回信息的准确性、丰富性和实用性
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import math
from loguru import logger

from .typhoon_intent_recognizer import (
    TyphoonQueryAnalysis,
    TyphoonIntentType,
    TyphoonEntityType
)


@dataclass
class RankedResult:
    """排序后的结果"""
    node_id: str
    node_data: Dict
    relevance_score: float
    quality_score: float
    diversity_score: float
    final_score: float
    ranking_factors: Dict[str, float] = field(default_factory=dict)


@dataclass
class RankingConfig:
    """排序配置"""
    relevance_weight: float = 0.4
    quality_weight: float = 0.3
    diversity_weight: float = 0.2
    freshness_weight: float = 0.1
    
    min_relevance_threshold: float = 0.3
    max_results: int = 50
    enable_deduplication: bool = True
    prefer_complete_data: bool = True


class RelevanceRanker:
    """相关性排序器"""
    
    # 属性完整性权重
    COMPLETENESS_WEIGHTS = {
        "Typhoon": {
            "name_cn": 1.0,
            "name_en": 0.8,
            "typhoon_id": 1.0,
            "year": 0.9,
            "max_wind_speed": 0.95,
            "min_pressure": 0.95,
            "peak_intensity": 0.9,
            "start_time": 0.85,
            "end_time": 0.85,
            "duration_hours": 0.8,
            "start_lat": 0.7,
            "start_lon": 0.7,
            "landfall_count": 0.75,
        },
        "PathPoint": {
            "lat": 1.0,
            "lon": 1.0,
            "timestamp": 0.9,
            "wind_speed": 0.85,
            "pressure": 0.85,
            "intensity": 0.8,
            "moving_speed": 0.7,
            "moving_direction": 0.7,
        },
        "Location": {
            "name": 1.0,
            "lat": 0.9,
            "lon": 0.9,
            "type": 0.7,
        },
        "Intensity": {
            "level": 1.0,
            "name_cn": 0.9,
            "wind_speed_min": 0.85,
            "wind_speed_max": 0.85,
        },
    }
    
    # 意图到属性的映射（用于相关性计算）
    INTENT_ATTRIBUTE_PRIORITY = {
        TyphoonIntentType.BASIC_INFO: [
            "name_cn", "name_en", "typhoon_id", "year",
            "start_time", "end_time", "duration_hours"
        ],
        TyphoonIntentType.PATH_QUERY: [
            "lat", "lon", "moving_speed", "moving_direction",
            "total_distance_km", "start_lat", "start_lon"
        ],
        TyphoonIntentType.INTENSITY_QUERY: [
            "max_wind_speed", "min_pressure", "peak_intensity",
            "wind_speed", "pressure", "power"
        ],
        TyphoonIntentType.TIME_QUERY: [
            "start_time", "end_time", "duration_hours",
            "timestamp", "year"
        ],
        TyphoonIntentType.LANDFALL_QUERY: [
            "landfall_count", "land_time", "land_intensity",
            "max_wind_speed", "min_pressure"
        ],
        TyphoonIntentType.IMPACT_QUERY: [
            "affected_area", "damage", "casualties",
            "max_wind_speed", "landfall_count"
        ],
        TyphoonIntentType.AFFECTED_AREA_QUERY: [
            "affected_area", "landfall_count", "max_wind_speed"
        ],
        TyphoonIntentType.PREDICTION_QUERY: [
            "current_position", "current_intensity",
            "moving_direction", "moving_speed"
        ],
        TyphoonIntentType.COMPARISON_QUERY: [
            "max_wind_speed", "min_pressure", "duration_hours",
            "total_distance_km", "landfall_count"
        ],
        TyphoonIntentType.STATISTICS_QUERY: [
            "year", "max_wind_speed", "landfall_count",
            "total_typhoons", "peak_intensity"
        ],
        TyphoonIntentType.RANKING_QUERY: [
            "max_wind_speed", "min_pressure", "duration_hours",
            "peak_intensity"
        ],
    }
    
    # 数据质量评分标准
    QUALITY_METRICS = {
        "completeness": 0.35,  # 属性完整度
        "accuracy": 0.25,      # 数据准确性
        "consistency": 0.20,   # 数据一致性
        "timeliness": 0.10,    # 数据时效性
        "source_reliability": 0.10,  # 来源可靠性
    }
    
    def __init__(self):
        pass
    
    def rank_results(
        self,
        nodes: List[Dict],
        relationships: List[Dict],
        query_analysis: TyphoonQueryAnalysis,
        config: Optional[RankingConfig] = None
    ) -> List[RankedResult]:
        """
        对检索结果进行排序
        
        Args:
            nodes: 节点列表
            relationships: 关系列表
            query_analysis: 查询分析结果
            config: 排序配置
            
        Returns:
            List[RankedResult]: 排序后的结果
        """
        config = config or RankingConfig()
        
        pass
        
        # 1. 计算各维度分数
        ranked_results = []
        
        for node in nodes:
            node_id = node.get("id", "")
            
            # 计算相关性分数
            relevance_score = self._calculate_relevance_score(
                node, query_analysis
            )
            
            # 计算质量分数
            quality_score = self._calculate_quality_score(node)
            
            # 计算多样性分数（暂时设为默认值，后续根据整体结果计算）
            diversity_score = 0.5
            
            # 计算时效性分数
            freshness_score = self._calculate_freshness_score(node)
            
            # 计算最终分数
            final_score = (
                relevance_score * config.relevance_weight +
                quality_score * config.quality_weight +
                diversity_score * config.diversity_weight +
                freshness_score * config.freshness_weight
            )
            
            ranked_results.append(RankedResult(
                node_id=node_id,
                node_data=node,
                relevance_score=relevance_score,
                quality_score=quality_score,
                diversity_score=diversity_score,
                final_score=final_score,
                ranking_factors={
                    "relevance": relevance_score,
                    "quality": quality_score,
                    "diversity": diversity_score,
                    "freshness": freshness_score,
                }
            ))
        
        # 2. 计算多样性分数（基于整体结果）
        if config.enable_deduplication:
            ranked_results = self._calculate_diversity_scores(ranked_results)
        
        # 3. 重新计算最终分数（包含多样性）
        for result in ranked_results:
            result.final_score = (
                result.relevance_score * config.relevance_weight +
                result.quality_score * config.quality_weight +
                result.diversity_score * config.diversity_weight +
                self._calculate_freshness_score(result.node_data) * config.freshness_weight
            )
        
        # 4. 过滤低相关性结果
        ranked_results = [
            r for r in ranked_results 
            if r.relevance_score >= config.min_relevance_threshold
        ]
        
        # 5. 按最终分数排序
        ranked_results.sort(key=lambda x: x.final_score, reverse=True)
        
        # 6. 限制结果数量
        final_results = ranked_results[:config.max_results]
        
        pass
        
        return final_results
    
    def _calculate_relevance_score(
        self,
        node: Dict,
        query_analysis: TyphoonQueryAnalysis
    ) -> float:
        """计算相关性分数"""
        score = 0.0
        node_type = node.get("type", "")
        properties = node.get("properties", {})
        
        # 1. 节点类型匹配
        type_scores = {
            "Typhoon": 1.0,
            "PathPoint": 0.6,
            "Location": 0.7,
            "Intensity": 0.75,
            "Time": 0.5,
        }
        score += type_scores.get(node_type, 0.5) * 0.3
        
        # 2. 属性匹配
        intent_attrs = self.INTENT_ATTRIBUTE_PRIORITY.get(
            query_analysis.intent.intent_type, 
            []
        )
        
        attr_score = 0.0
        for attr, value in properties.items():
            base_weight = 0.1
            
            # 如果属性与意图相关，增加权重
            if attr in intent_attrs:
                base_weight *= 2.0
            
            # 检查属性值是否匹配查询实体
            for entity in query_analysis.entities:
                if str(value).lower() == entity.value.lower():
                    base_weight *= 3.0
                elif str(value).lower() in entity.value.lower():
                    base_weight *= 1.5
            
            attr_score += base_weight
        
        score += min(attr_score, 1.0) * 0.4
        
        # 3. 数据完整性匹配
        completeness = self._calculate_completeness(node)
        score += completeness * 0.3
        
        return min(score, 1.0)
    
    def _calculate_quality_score(self, node: Dict) -> float:
        """计算数据质量分数"""
        scores = {}
        
        # 1. 完整性
        scores["completeness"] = self._calculate_completeness(node)
        
        # 2. 准确性（检查数据合理性）
        scores["accuracy"] = self._calculate_accuracy(node)
        
        # 3. 一致性
        scores["consistency"] = self._calculate_consistency(node)
        
        # 4. 时效性
        scores["timeliness"] = self._calculate_timeliness(node)
        
        # 5. 来源可靠性（默认中等）
        scores["source_reliability"] = 0.7
        
        # 加权平均
        total_score = sum(
            scores[metric] * weight 
            for metric, weight in self.QUALITY_METRICS.items()
        )
        
        return min(total_score, 1.0)
    
    def _calculate_completeness(self, node: Dict) -> float:
        """计算属性完整度"""
        node_type = node.get("type", "")
        properties = node.get("properties", {})
        
        expected_attrs = self.COMPLETENESS_WEIGHTS.get(node_type, {})
        if not expected_attrs:
            return 0.5
        
        total_weight = sum(expected_attrs.values())
        actual_weight = 0.0
        
        for attr, weight in expected_attrs.items():
            if attr in properties and properties[attr] is not None:
                # 检查值是否有效
                value = properties[attr]
                if value != "" and value != 0 and value != 9999.0:
                    actual_weight += weight
        
        return actual_weight / total_weight if total_weight > 0 else 0.5
    
    def _calculate_accuracy(self, node: Dict) -> float:
        """计算数据准确性"""
        properties = node.get("properties", {})
        accuracy_checks = []
        
        # 检查风速范围
        if "max_wind_speed" in properties:
            wind_speed = properties["max_wind_speed"]
            if 0 <= wind_speed <= 100:  # 合理范围
                accuracy_checks.append(1.0)
            else:
                accuracy_checks.append(0.3)
        
        # 检查气压范围
        if "min_pressure" in properties:
            pressure = properties["min_pressure"]
            if 800 <= pressure <= 1100:  # 合理范围
                accuracy_checks.append(1.0)
            else:
                accuracy_checks.append(0.3)
        
        # 检查年份
        if "year" in properties:
            year = properties["year"]
            if 1949 <= year <= 2100:  # 合理范围
                accuracy_checks.append(1.0)
            else:
                accuracy_checks.append(0.3)
        
        # 检查坐标
        if "lat" in properties and "lon" in properties:
            lat, lon = properties["lat"], properties["lon"]
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                accuracy_checks.append(1.0)
            else:
                accuracy_checks.append(0.3)
        
        if not accuracy_checks:
            return 0.7  # 默认中等准确性
        
        return sum(accuracy_checks) / len(accuracy_checks)
    
    def _calculate_consistency(self, node: Dict) -> float:
        """计算数据一致性"""
        properties = node.get("properties", {})
        consistency_checks = []
        
        # 检查台风ID和年份是否一致
        if "typhoon_id" in properties and "year" in properties:
            typhoon_id = properties["typhoon_id"]
            year = properties["year"]
            if str(typhoon_id).startswith(str(year)):
                consistency_checks.append(1.0)
            else:
                consistency_checks.append(0.5)
        
        # 检查风速和强度等级是否一致
        if "max_wind_speed" in properties and "peak_intensity" in properties:
            wind_speed = properties["max_wind_speed"]
            intensity = properties["peak_intensity"]
            
            # 简单的一致性检查
            intensity_wind_map = {
                "TD": (10.8, 17.1),
                "TS": (17.2, 24.4),
                "STS": (24.5, 32.6),
                "TY": (32.7, 41.4),
                "STY": (41.5, 50.9),
                "SuperTY": (51.0, 100),
            }
            
            if intensity in intensity_wind_map:
                min_wind, max_wind = intensity_wind_map[intensity]
                if min_wind <= wind_speed <= max_wind:
                    consistency_checks.append(1.0)
                else:
                    consistency_checks.append(0.5)
        
        if not consistency_checks:
            return 0.8  # 默认较高一致性
        
        return sum(consistency_checks) / len(consistency_checks)
    
    def _calculate_timeliness(self, node: Dict) -> float:
        """计算数据时效性"""
        properties = node.get("properties", {})
        
        # 对于历史台风数据，年份越近时效性越高
        if "year" in properties:
            year = properties["year"]
            current_year = 2024  # 可以使用当前实际年份
            
            # 近5年的数据时效性最高
            if current_year - year <= 5:
                return 1.0
            elif current_year - year <= 10:
                return 0.9
            elif current_year - year <= 20:
                return 0.8
            else:
                return 0.7
        
        return 0.8  # 默认时效性
    
    def _calculate_freshness_score(self, node: Dict) -> float:
        """计算新鲜度分数"""
        # 与timeliness类似，但更侧重于最近的数据
        return self._calculate_timeliness(node)
    
    def _calculate_diversity_scores(
        self, 
        results: List[RankedResult]
    ) -> List[RankedResult]:
        """计算多样性分数"""
        if len(results) <= 1:
            return results
        
        # 按类型分组
        type_groups = defaultdict(list)
        for i, result in enumerate(results):
            node_type = result.node_data.get("type", "Unknown")
            type_groups[node_type].append(i)
        
        # 计算每个结果的多样性分数
        for i, result in enumerate(results):
            node_type = result.node_data.get("type", "Unknown")
            
            # 同类型结果越多，多样性分数越低
            same_type_count = len(type_groups[node_type])
            diversity_score = 1.0 / math.sqrt(same_type_count)
            
            # 如果有很多属性匹配，增加多样性
            properties = result.node_data.get("properties", {})
            if len(properties) > 10:
                diversity_score *= 1.2
            
            result.diversity_score = min(diversity_score, 1.0)
        
        return results
    
    def rerank_by_feedback(
        self,
        ranked_results: List[RankedResult],
        feedback: Dict[str, Any]
    ) -> List[RankedResult]:
        """
        根据用户反馈重新排序
        
        Args:
            ranked_results: 已排序的结果
            feedback: 用户反馈信息
            
        Returns:
            List[RankedResult]: 重新排序后的结果
        """
        # 复制结果列表
        results = ranked_results.copy()
        
        # 处理正反馈（用户点击或认可的结果）
        positive_feedback = feedback.get("positive", [])
        for node_id in positive_feedback:
            for result in results:
                if result.node_id == node_id:
                    # 提升分数
                    result.final_score *= 1.2
                    result.ranking_factors["user_feedback"] = 1.0
                    break
        
        # 处理负反馈（用户忽略或否定的结果）
        negative_feedback = feedback.get("negative", [])
        for node_id in negative_feedback:
            for result in results:
                if result.node_id == node_id:
                    # 降低分数
                    result.final_score *= 0.8
                    result.ranking_factors["user_feedback"] = -1.0
                    break
        
        # 重新排序
        results.sort(key=lambda x: x.final_score, reverse=True)
        
        return results
    
    def get_explanation(
        self,
        ranked_result: RankedResult,
        query_analysis: TyphoonQueryAnalysis
    ) -> str:
        """
        获取排序解释
        
        Args:
            ranked_result: 排序结果
            query_analysis: 查询分析
            
        Returns:
            str: 排序解释
        """
        explanations = []
        
        factors = ranked_result.ranking_factors
        
        if factors.get("relevance", 0) > 0.8:
            explanations.append("与查询高度相关")
        elif factors.get("relevance", 0) > 0.5:
            explanations.append("与查询中度相关")
        
        if factors.get("quality", 0) > 0.8:
            explanations.append("数据质量高")
        
        if factors.get("diversity", 0) > 0.7:
            explanations.append("信息类型独特")
        
        node_type = ranked_result.node_data.get("type", "")
        if node_type == "Typhoon":
            explanations.append("台风实体")
        elif node_type == "PathPoint":
            explanations.append("路径点信息")
        elif node_type == "Location":
            explanations.append("地理位置信息")
        
        if not explanations:
            explanations.append("一般相关性")
        
        return "；".join(explanations)


# 辅助函数
def create_ranker() -> RelevanceRanker:
    """创建排序器"""
    return RelevanceRanker()
