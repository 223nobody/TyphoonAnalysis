"""
台风相似性计算模块
基于DTW（动态时间规整）算法和多种特征计算台风相似度

特征权重:
- 路径形状: 40% (基于DTW算法)
- 生成位置: 25% (基于Haversine距离)
- 强度变化: 20% (基于风速曲线相似度)
- 时间模式: 10% (基于月份)
- 移动速度: 5% (基于平均速度)
"""
import numpy as np
from typing import List, Tuple, Dict, Optional
from math import radians, sin, cos, sqrt, atan2

from loguru import logger

from app.core.neo4j_client import neo4j_client


class TyphoonSimilarityCalculator:
    """
    台风相似性计算器
    综合多种特征计算台风之间的相似度
    """

    def __init__(self):
        # 特征权重配置 - 严格按照开发方案文档
        self.feature_weights = {
            "path_shape": 0.40,      # 路径形状（最重要）
            "genesis_location": 0.25, # 生成位置
            "intensity_profile": 0.20, # 强度变化
            "temporal_pattern": 0.10,  # 时间模式
            "movement_speed": 0.05     # 移动速度
        }

        # 相似度阈值
        self.similarity_threshold = 0.6

    async def calculate_similarity(
        self,
        typhoon_a_id: str,
        typhoon_b_id: str
    ) -> Dict:
        """
        计算两个台风的综合相似度

        Args:
            typhoon_a_id: 台风A编号
            typhoon_b_id: 台风B编号

        Returns:
            Dict: 包含综合相似度和各特征相似度的字典
        """
        try:
            # 从Neo4j获取台风特征数据
            data_a = await self._get_typhoon_features(typhoon_a_id)
            data_b = await self._get_typhoon_features(typhoon_b_id)

            if not data_a or not data_b:
                return {
                    "similarity": 0.0,
                    "error": "无法获取台风数据",
                    "details": {}
                }

            # 计算各特征相似度
            scores = {}

            # 1. 路径形状相似度（基于欧氏距离简化版）
            scores["path_shape"] = self._path_similarity(
                data_a["path"], data_b["path"]
            )

            # 2. 生成位置相似度
            scores["genesis_location"] = self._location_similarity(
                data_a["genesis"], data_b["genesis"]
            )

            # 3. 强度变化相似度
            scores["intensity_profile"] = self._intensity_similarity(
                data_a["intensities"], data_b["intensities"]
            )

            # 4. 时间模式相似度
            scores["temporal_pattern"] = self._temporal_similarity(
                data_a["month"], data_b["month"]
            )

            # 5. 移动速度相似度
            scores["movement_speed"] = self._speed_similarity(
                data_a["speeds"], data_b["speeds"]
            )

            # 加权综合
            total_score = sum(
                scores[k] * self.feature_weights[k]
                for k in scores
            )

            return {
                "similarity": round(total_score, 4),
                "is_similar": total_score >= self.similarity_threshold,
                "details": {
                    feature: {
                        "score": round(score, 4),
                        "weight": self.feature_weights[feature]
                    }
                    for feature, score in scores.items()
                },
                "typhoon_a": {
                    "id": typhoon_a_id,
                    "name": data_a.get("name_cn", ""),
                    "year": data_a.get("year", 0)
                },
                "typhoon_b": {
                    "id": typhoon_b_id,
                    "name": data_b.get("name_cn", ""),
                    "year": data_b.get("year", 0)
                }
            }

        except Exception as e:
            logger.error(f"计算相似度失败 [{typhoon_a_id} vs {typhoon_b_id}]: {e}")
            return {
                "similarity": 0.0,
                "error": str(e),
                "details": {}
            }

    async def find_similar_typhoons(
        self,
        typhoon_id: str,
        limit: int = 10,
        min_similarity: float = 0.6
    ) -> List[Dict]:
        """
        查找与指定台风相似的台风列表

        Args:
            typhoon_id: 参考台风编号
            limit: 返回结果数量
            min_similarity: 最小相似度阈值

        Returns:
            List[Dict]: 相似台风列表
        """
        try:
            # 获取参考台风数据
            ref_data = await self._get_typhoon_features(typhoon_id)
            if not ref_data:
                return []

            # 获取候选台风（同一年份或相邻年份）
            candidate_ids = await self._get_candidate_typhoons(
                typhoon_id,
                ref_data["year"],
                year_range=5  # 前后5年
            )

            # 计算相似度
            similar_typhoons = []
            for candidate_id in candidate_ids:
                if candidate_id == typhoon_id:
                    continue

                similarity_result = await self.calculate_similarity(
                    typhoon_id, candidate_id
                )

                if similarity_result["similarity"] >= min_similarity:
                    similar_typhoons.append({
                        "typhoon_id": candidate_id,
                        **similarity_result
                    })

            # 按相似度排序
            similar_typhoons.sort(
                key=lambda x: x["similarity"],
                reverse=True
            )

            return similar_typhoons[:limit]

        except Exception as e:
            logger.error(f"查找相似台风失败 [{typhoon_id}]: {e}")
            return []

    def _extract_month_from_timestamp(self, timestamp) -> int:
        """从时间戳中提取月份"""
        if not timestamp:
            return 0
        try:
            timestamp_str = str(timestamp)
            if len(timestamp_str) >= 7:
                return int(timestamp_str[5:7])
        except (ValueError, IndexError):
            pass
        return 0

    async def _get_typhoon_features(self, typhoon_id: str) -> Optional[Dict]:
        """
        从Neo4j获取台风特征数据

        Args:
            typhoon_id: 台风编号

        Returns:
            Optional[Dict]: 台风特征数据
        """
        cypher = """
            MATCH (t:Typhoon {typhoon_id: $typhoon_id})-[:HAS_PATH_POINT]->(p:PathPoint)
            WITH t, p
            ORDER BY p.sequence
            RETURN t.typhoon_id as id,
                   t.name_cn as name_cn,
                   t.year as year,
                   collect({
                       lat: p.lat,
                       lon: p.lon,
                       wind: p.wind_speed,
                       pressure: p.pressure,
                       speed: p.moving_speed,
                       timestamp: p.timestamp
                   }) as path_points
        """

        try:
            result = await neo4j_client.run(cypher, {"typhoon_id": typhoon_id})
            if not result:
                return None

            data = result[0]
            path_points = data["path_points"]

            if not path_points:
                return None

            return {
                "id": data["id"],
                "name_cn": data["name_cn"],
                "year": data["year"],
                "month": self._extract_month_from_timestamp(path_points[0].get("timestamp")),
                "genesis": (path_points[0]["lat"], path_points[0]["lon"]),
                "path": [
                    (p["lat"], p["lon"])
                    for p in path_points
                    if p["lat"] is not None and p["lon"] is not None
                ],
                "intensities": [p["wind"] for p in path_points if p["wind"] is not None],
                "speeds": [p["speed"] for p in path_points if p["speed"] is not None]
            }

        except Exception as e:
            logger.error(f"获取台风特征失败 [{typhoon_id}]: {e}")
            return None

    async def _get_candidate_typhoons(
        self,
        exclude_id: str,
        year: int,
        year_range: int = 5
    ) -> List[str]:
        """
        获取候选台风列表

        Args:
            exclude_id: 排除的台风编号
            year: 参考年份
            year_range: 年份范围

        Returns:
            List[str]: 候选台风编号列表
        """
        cypher = """
            MATCH (t:Typhoon)-[:OCCURRED_IN]->(tm:Time)
            WHERE t.typhoon_id <> $exclude_id
              AND tm.year >= $min_year
              AND tm.year <= $max_year
            RETURN t.typhoon_id as typhoon_id
            LIMIT 100
        """

        params = {
            "exclude_id": exclude_id,
            "min_year": year - year_range,
            "max_year": year + year_range
        }

        try:
            result = await neo4j_client.run(cypher, params)
            return [r["typhoon_id"] for r in result]
        except Exception as e:
            logger.error(f"获取候选台风失败: {e}")
            return []

    def _path_similarity(
        self,
        path_a: List[Tuple[float, float]],
        path_b: List[Tuple[float, float]]
    ) -> float:
        """
        计算路径形状相似度（简化版DTW）

        Args:
            path_a: 台风A的路径点列表 [(lat, lon), ...]
            path_b: 台风B的路径点列表 [(lat, lon), ...]

        Returns:
            float: 相似度 (0-1)
        """
        if not path_a or not path_b:
            return 0.0

        # 归一化路径长度
        min_len = min(len(path_a), len(path_b))
        if min_len < 2:
            return 0.0

        # 采样到相同长度进行比较
        path_a_sampled = self._resample_path(path_a, min_len)
        path_b_sampled = self._resample_path(path_b, min_len)

        # 计算欧氏距离
        total_distance = 0.0
        for (lat1, lon1), (lat2, lon2) in zip(path_a_sampled, path_b_sampled):
            # 使用简化的距离计算（不考虑地球曲率）
            distance = sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)
            total_distance += distance

        avg_distance = total_distance / min_len

        # 转换为相似度（距离越小越相似）
        # 使用sigmoid函数映射
        similarity = 1 / (1 + avg_distance * 0.5)

        return min(1.0, max(0.0, similarity))

    def _resample_path(
        self,
        path: List[Tuple[float, float]],
        target_length: int
    ) -> List[Tuple[float, float]]:
        """
        重采样路径到指定长度

        Args:
            path: 原始路径
            target_length: 目标长度

        Returns:
            List[Tuple[float, float]]: 重采样后的路径
        """
        if len(path) == target_length:
            return path

        if len(path) < target_length:
            # 插值
            result = []
            ratio = (len(path) - 1) / (target_length - 1)
            for i in range(target_length):
                idx = i * ratio
                idx_low = int(idx)
                idx_high = min(idx_low + 1, len(path) - 1)
                weight = idx - idx_low

                lat = path[idx_low][0] * (1 - weight) + path[idx_high][0] * weight
                lon = path[idx_low][1] * (1 - weight) + path[idx_high][1] * weight
                result.append((lat, lon))
            return result
        else:
            # 降采样
            indices = np.linspace(0, len(path) - 1, target_length, dtype=int)
            return [path[i] for i in indices]

    def _location_similarity(
        self,
        loc_a: Tuple[float, float],
        loc_b: Tuple[float, float]
    ) -> float:
        """
        计算地理位置相似度（Haversine距离）

        Args:
            loc_a: 位置A (lat, lon)
            loc_b: 位置B (lat, lon)

        Returns:
            float: 相似度 (0-1)
        """
        if not loc_a or not loc_b:
            return 0.0

        lat1, lon1 = map(radians, loc_a)
        lat2, lon2 = map(radians, loc_b)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = 6371 * c  # 地球半径km

        # 转换为相似度（2000km内认为有相似性）
        similarity = max(0, 1 - distance / 2000)

        return similarity

    def _intensity_similarity(
        self,
        intensities_a: List[float],
        intensities_b: List[float]
    ) -> float:
        """
        计算强度变化相似度

        Args:
            intensities_a: 台风A的风速序列
            intensities_b: 台风B的风速序列

        Returns:
            float: 相似度 (0-1)
        """
        if not intensities_a or not intensities_b:
            return 0.0

        # 归一化到相同长度
        min_len = min(len(intensities_a), len(intensities_b))
        if min_len < 2:
            return 0.0

        a_sampled = intensities_a[:min_len]
        b_sampled = intensities_b[:min_len]

        # 计算皮尔逊相关系数
        try:
            mean_a = sum(a_sampled) / len(a_sampled)
            mean_b = sum(b_sampled) / len(b_sampled)

            numerator = sum((a - mean_a) * (b - mean_b) for a, b in zip(a_sampled, b_sampled))
            denom_a = sqrt(sum((a - mean_a)**2 for a in a_sampled))
            denom_b = sqrt(sum((b - mean_b)**2 for b in b_sampled))

            if denom_a == 0 or denom_b == 0:
                return 0.0

            correlation = numerator / (denom_a * denom_b)

            # 将相关系数映射到0-1
            return (correlation + 1) / 2

        except:
            return 0.0

    def _temporal_similarity(self, month_a: int, month_b: int) -> float:
        """
        计算时间模式相似度

        Args:
            month_a: 台风A的发生月份
            month_b: 台风B的发生月份

        Returns:
            float: 相似度 (0-1)
        """
        if month_a == 0 or month_b == 0:
            return 0.5  # 未知月份给中等相似度

        # 计算月份差（考虑跨年）
        diff = abs(month_a - month_b)
        diff = min(diff, 12 - diff)

        # 月份差越小越相似
        similarity = 1 - diff / 6  # 6个月差为0相似度

        return max(0, similarity)

    def _speed_similarity(
        self,
        speeds_a: List[float],
        speeds_b: List[float]
    ) -> float:
        """
        计算移动速度相似度

        Args:
            speeds_a: 台风A的速度序列
            speeds_b: 台风B的速度序列

        Returns:
            float: 相似度 (0-1)
        """
        if not speeds_a or not speeds_b:
            return 0.0

        # 计算平均速度
        avg_a = sum(speeds_a) / len(speeds_a)
        avg_b = sum(speeds_b) / len(speeds_b)

        # 速度越接近越相似
        max_speed = max(avg_a, avg_b, 1)  # 避免除零
        diff = abs(avg_a - avg_b)

        similarity = 1 - diff / max_speed

        return max(0, min(1, similarity))


# 全局相似性计算器实例
similarity_calculator = TyphoonSimilarityCalculator()
