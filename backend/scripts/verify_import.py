"""
数据导入验证脚本
验证Neo4j知识图谱的数据完整性和质量

验证内容:
1. 节点数量统计
2. 关系数量统计
3. 数据完整性检查
4. 示例数据验证
5. 关系连通性检查
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 添加backend到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from loguru import logger
from app.core.neo4j_client import neo4j_client


class DataValidator:
    """
    数据验证器
    对导入的数据进行全面的质量和完整性检查
    """

    def __init__(self):
        self.validation_results = {
            "passed": [],
            "warnings": [],
            "errors": []
        }
        self.stats = {}

    async def validate_all(self):
        """
        执行所有验证检查
        """
        logger.info("\n" + "=" * 70)
        logger.info("Neo4j 数据导入验证开始")
        logger.info("=" * 70)

        try:
            # 连接Neo4j
            logger.info("\n[1/6] 连接 Neo4j 数据库...")
            connected = await neo4j_client.connect()
            if not connected:
                raise ConnectionError("无法连接到Neo4j数据库")

            # 执行各项验证
            await self._validate_node_counts()
            await self._validate_relationship_counts()
            await self._validate_data_integrity()
            await self._validate_sample_data()
            await self._validate_connectivity()
            await self._validate_constraints_indexes()

            # 输出验证报告
            self._print_validation_report()

            return len(self.validation_results["errors"]) == 0

        except Exception as e:
            logger.error(f"\n❌ 验证过程出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

        finally:
            await neo4j_client.close()

    async def _validate_node_counts(self):
        """
        验证各类节点的数量
        对比开发方案文档中的预期数量
        """
        logger.info("\n[2/6] 验证节点数量...")

        # 预期数量（根据开发方案文档）
        expected_counts = {
            "Typhoon": {"min": 1500, "max": 3000, "name": "台风节点"},
            "PathPoint": {"min": 400000, "max": 600000, "name": "路径点节点"},
            "Location": {"min": 200, "max": 1000, "name": "地理位置节点"},
            "Time": {"min": 50, "max": 70, "name": "时间节点"},
            "Intensity": {"min": 6, "max": 6, "name": "强度等级节点"}
        }

        for label, expected in expected_counts.items():
            try:
                result = await neo4j_client.run(
                    f"MATCH (n:{label}) RETURN count(n) as count"
                )
                actual_count = result[0]["count"] if result else 0
                self.stats[f"{label}_count"] = actual_count

                # 验证数量是否在预期范围内
                if expected["min"] <= actual_count <= expected["max"]:
                    self.validation_results["passed"].append(
                        f"{expected['name']}: {actual_count:,} (预期: {expected['min']:,}-{expected['max']:,})"
                    )
                    logger.info(f"   ✅ {expected['name']}: {actual_count:,}")
                elif actual_count < expected["min"]:
                    self.validation_results["warnings"].append(
                        f"{expected['name']}数量偏少: {actual_count:,} (预期至少: {expected['min']:,})"
                    )
                    logger.warning(f"   ⚠️  {expected['name']}: {actual_count:,} (偏少)")
                else:
                    self.validation_results["passed"].append(
                        f"{expected['name']}: {actual_count:,} (超出预期范围，但可接受)"
                    )
                    logger.info(f"   ✅ {expected['name']}: {actual_count:,} (超出预期)")

            except Exception as e:
                self.validation_results["errors"].append(
                    f"验证{expected['name']}数量失败: {e}"
                )
                logger.error(f"   ❌ 验证{expected['name']}失败: {e}")

    async def _validate_relationship_counts(self):
        """
        验证各类关系的数量
        """
        logger.info("\n[3/6] 验证关系数量...")

        relationship_checks = [
            {"type": "HAS_PATH_POINT", "name": "台风-路径点关系"},
            {"type": "NEXT", "name": "路径点顺序关系"},
            {"type": "OCCURRED_IN", "name": "台风-时间关系"},
            {"type": "LANDED_AT", "name": "台风-登陆地点关系"},
            # 扩展关系
            {"type": "GENERATED_AT", "name": "生成位置关系"},
            {"type": "DISSIPATED_AT", "name": "消散位置关系"},
            {"type": "INTENSIFIED_TO", "name": "强度增强关系"},
            {"type": "WEAKENED_TO", "name": "强度减弱关系"},
            {"type": "SIMILAR_TO", "name": "相似性关系"},
            {"type": "AFFECTED_AREA", "name": "影响区域关系"},
            {"type": "PASSED_NEAR", "name": "经过附近关系"}
        ]

        for rel in relationship_checks:
            try:
                result = await neo4j_client.run(
                    f"MATCH ()-[r:{rel['type']}]->() RETURN count(r) as count"
                )
                count = result[0]["count"] if result else 0
                self.stats[f"{rel['type']}_count"] = count

                if count > 0:
                    self.validation_results["passed"].append(
                        f"{rel['name']}: {count:,}"
                    )
                    logger.info(f"   ✅ {rel['name']}: {count:,}")
                else:
                    self.validation_results["warnings"].append(
                        f"{rel['name']}数量为0"
                    )
                    logger.warning(f"   ⚠️  {rel['name']}: 0")

            except Exception as e:
                self.validation_results["errors"].append(
                    f"验证{rel['name']}失败: {e}"
                )
                logger.error(f"   ❌ 验证{rel['name']}失败: {e}")

    async def _validate_data_integrity(self):
        """
        验证数据完整性
        检查关键字段是否存在空值或异常值
        """
        logger.info("\n[4/6] 验证数据完整性...")

        integrity_checks = [
            {
                "name": "台风节点关键字段",
                "query": """
                    MATCH (t:Typhoon)
                    WHERE t.typhoon_id IS NULL OR t.name_cn IS NULL OR t.year IS NULL
                    RETURN count(t) as invalid_count
                """
            },
            {
                "name": "路径点坐标完整性",
                "query": """
                    MATCH (p:PathPoint)
                    WHERE p.lat IS NULL OR p.lon IS NULL
                    RETURN count(p) as invalid_count
                """
            },
            {
                "name": "路径点时间戳完整性",
                "query": """
                    MATCH (p:PathPoint)
                    WHERE p.timestamp IS NULL
                    RETURN count(p) as invalid_count
                """
            },
            {
                "name": "孤立台风节点（无路径点）",
                "query": """
                    MATCH (t:Typhoon)
                    WHERE NOT (t)-[:HAS_PATH_POINT]->()
                    RETURN count(t) as invalid_count
                """
            },
            {
                "name": "孤立路径点（无台风关联）",
                "query": """
                    MATCH (p:PathPoint)
                    WHERE NOT ()-[:HAS_PATH_POINT]->(p)
                    RETURN count(p) as invalid_count
                """
            }
        ]

        for check in integrity_checks:
            try:
                result = await neo4j_client.run(check["query"])
                invalid_count = result[0]["invalid_count"] if result else 0

                if invalid_count == 0:
                    self.validation_results["passed"].append(
                        f"{check['name']}: 无异常"
                    )
                    logger.info(f"   ✅ {check['name']}: 通过")
                else:
                    self.validation_results["warnings"].append(
                        f"{check['name']}: 发现 {invalid_count:,} 条异常记录"
                    )
                    logger.warning(f"   ⚠️  {check['name']}: {invalid_count:,} 条异常")

            except Exception as e:
                self.validation_results["errors"].append(
                    f"验证{check['name']}失败: {e}"
                )
                logger.error(f"   ❌ 验证{check['name']}失败: {e}")

    async def _validate_sample_data(self):
        """
        验证示例数据的正确性
        检查特定台风的数据是否完整
        """
        logger.info("\n[5/6] 验证示例数据...")

        # 选择几个示例台风进行详细检查
        sample_typhoons = ["196601", "201001", "202301", "202526"]

        for typhoon_id in sample_typhoons:
            try:
                # 检查台风基本信息
                typhoon_query = """
                    MATCH (t:Typhoon {typhoon_id: $typhoon_id})
                    RETURN t.typhoon_id as id,
                           t.name_cn as name_cn,
                           t.name_en as name_en,
                           t.year as year,
                           t.max_wind_speed as max_wind,
                           t.total_path_points as path_points
                """
                typhoon_result = await neo4j_client.run(typhoon_query, {"typhoon_id": typhoon_id})

                if not typhoon_result:
                    self.validation_results["warnings"].append(
                        f"示例台风 {typhoon_id} 不存在"
                    )
                    logger.warning(f"   ⚠️  台风 {typhoon_id}: 不存在")
                    continue

                typhoon = typhoon_result[0]

                # 检查路径点数量
                path_query = """
                    MATCH (t:Typhoon {typhoon_id: $typhoon_id})-[:HAS_PATH_POINT]->(p:PathPoint)
                    RETURN count(p) as actual_path_points
                """
                path_result = await neo4j_client.run(path_query, {"typhoon_id": typhoon_id})
                actual_paths = path_result[0]["actual_path_points"] if path_result else 0

                # 验证路径点数量是否匹配
                if actual_paths == typhoon["path_points"]:
                    self.validation_results["passed"].append(
                        f"台风 {typhoon_id} ({typhoon['name_cn']}): 路径点数量匹配 ({actual_paths})"
                    )
                    logger.info(f"   ✅ 台风 {typhoon_id} ({typhoon['name_cn']}): {actual_paths} 个路径点")
                else:
                    self.validation_results["warnings"].append(
                        f"台风 {typhoon_id}: 路径点数量不匹配 (记录: {typhoon['path_points']}, 实际: {actual_paths})"
                    )
                    logger.warning(f"   ⚠️  台风 {typhoon_id}: 路径点数量不匹配")

                # 检查关系完整性
                rel_query = """
                    MATCH (t:Typhoon {typhoon_id: $typhoon_id})
                    OPTIONAL MATCH (t)-[:OCCURRED_IN]->(tm:Time)
                    OPTIONAL MATCH (t)-[:INTENSIFIED_TO]->(i:Intensity)
                    OPTIONAL MATCH (t)-[:WEAKENED_TO]->(i2:Intensity)
                    RETURN tm.year as time_year, i.level as intensified_level, i2.level as weakened_level
                """
                rel_result = await neo4j_client.run(rel_query, {"typhoon_id": typhoon_id})

                if rel_result:
                    rel = rel_result[0]
                    intensity_info = rel["intensified_level"] or rel["weakened_level"] or "无强度变化记录"
                    if rel["time_year"]:
                        logger.info(f"      时间关系: {rel['time_year']}, 强度变化: {intensity_info}")

            except Exception as e:
                self.validation_results["errors"].append(
                    f"验证示例台风 {typhoon_id} 失败: {e}"
                )
                logger.error(f"   ❌ 验证台风 {typhoon_id} 失败: {e}")

    async def _validate_connectivity(self):
        """
        验证关系连通性
        检查路径点之间的NEXT关系是否正确建立
        """
        logger.info("\n[6/6] 验证关系连通性...")

        try:
            # 检查NEXT关系的完整性
            next_check_query = """
                MATCH (p:PathPoint)
                WITH p.typhoon_id as typhoon_id, count(p) as total_points
                MATCH (p:PathPoint {typhoon_id: typhoon_id})
                OPTIONAL MATCH (p)-[:NEXT]->(next:PathPoint)
                WITH typhoon_id, total_points,
                     count(CASE WHEN next IS NOT NULL THEN 1 END) as has_next_count
                WHERE total_points > 1
                RETURN count(CASE WHEN has_next_count < total_points - 1 THEN 1 END) as incomplete_typhoons,
                       count(*) as total_checked
            """

            result = await neo4j_client.run(next_check_query)
            if result:
                incomplete = result[0]["incomplete_typhoons"]
                total = result[0]["total_checked"]

                if incomplete == 0:
                    self.validation_results["passed"].append(
                        f"路径连通性: 所有 {total} 个台风的路径点关系完整"
                    )
                    logger.info(f"   ✅ 路径连通性: {total} 个台风通过检查")
                else:
                    self.validation_results["warnings"].append(
                        f"路径连通性: {incomplete}/{total} 个台风存在路径点关系不完整"
                    )
                    logger.warning(f"   ⚠️  路径连通性: {incomplete}/{total} 个台风存在问题")

        except Exception as e:
            self.validation_results["errors"].append(
                f"验证路径连通性失败: {e}"
            )
            logger.error(f"   ❌ 验证路径连通性失败: {e}")

    async def _validate_constraints_indexes(self):
        """
        验证约束和索引是否正确创建
        """
        logger.info("\n[额外检查] 验证约束和索引...")

        try:
            # 检查约束
            constraints = await neo4j_client.run("SHOW CONSTRAINTS")
            constraint_count = len(constraints)

            # 检查索引
            indexes = await neo4j_client.run("SHOW INDEXES")
            index_count = len(indexes)

            logger.info(f"   约束数量: {constraint_count}")
            logger.info(f"   索引数量: {index_count}")

            if constraint_count >= 4:  # 预期至少有4个约束
                self.validation_results["passed"].append(
                    f"约束检查: {constraint_count} 个约束已创建"
                )
            else:
                self.validation_results["warnings"].append(
                    f"约束数量偏少: {constraint_count} (预期至少4个)"
                )

            if index_count >= 8:  # 预期至少有8个索引
                self.validation_results["passed"].append(
                    f"索引检查: {index_count} 个索引已创建"
                )
            else:
                self.validation_results["warnings"].append(
                    f"索引数量偏少: {index_count} (预期至少8个)"
                )

        except Exception as e:
            logger.error(f"   验证约束索引失败: {e}")

    def _print_validation_report(self):
        """
        打印验证报告
        """
        logger.info("\n" + "=" * 70)
        logger.info("数据验证报告")
        logger.info("=" * 70)

        # 通过的检查
        logger.info(f"\n✅ 通过检查 ({len(self.validation_results['passed'])} 项):")
        for item in self.validation_results["passed"]:
            logger.info(f"   • {item}")

        # 警告
        if self.validation_results["warnings"]:
            logger.warning(f"\n⚠️  警告 ({len(self.validation_results['warnings'])} 项):")
            for item in self.validation_results["warnings"]:
                logger.warning(f"   • {item}")

        # 错误
        if self.validation_results["errors"]:
            logger.error(f"\n❌ 错误 ({len(self.validation_results['errors'])} 项):")
            for item in self.validation_results["errors"]:
                logger.error(f"   • {item}")

        # 总体评估
        logger.info("\n" + "=" * 70)
        if len(self.validation_results["errors"]) == 0:
            if len(self.validation_results["warnings"]) == 0:
                logger.info("🎉 所有验证通过！数据质量良好。")
            else:
                logger.info("✅ 验证通过，但存在一些警告，建议检查。")
        else:
            logger.error("❌ 验证未通过，存在严重问题需要修复。")
        logger.info("=" * 70)


async def main():
    """主函数"""
    validator = DataValidator()
    success = await validator.validate_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
