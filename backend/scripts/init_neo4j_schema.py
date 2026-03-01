"""
Neo4j Schema 初始化脚本
根据开发方案文档创建约束、索引和全文索引
"""
import asyncio
import sys
from pathlib import Path

# 添加backend到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from loguru import logger
from app.core.neo4j_client import neo4j_client


# Schema 定义 - 严格按照开发方案文档
SCHEMA_QUERIES = {
    # ========== 约束 (Constraints) ==========
    "constraints": [
        {
            "name": "typhoon_id_constraint",
            "query": "CREATE CONSTRAINT typhoon_id IF NOT EXISTS FOR (t:Typhoon) REQUIRE t.typhoon_id IS UNIQUE"
        },
        {
            "name": "location_name_constraint",
            "query": "CREATE CONSTRAINT location_name IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE"
        },
        {
            "name": "intensity_level_constraint",
            "query": "CREATE CONSTRAINT intensity_level IF NOT EXISTS FOR (i:Intensity) REQUIRE i.level IS UNIQUE"
        },
        {
            "name": "time_year_constraint",
            "query": "CREATE CONSTRAINT time_year IF NOT EXISTS FOR (tm:Time) REQUIRE tm.year IS UNIQUE"
        }
    ],

    # ========== 索引 (Indexes) ==========
    "indexes": [
        {
            "name": "typhoon_year_index",
            "query": "CREATE INDEX typhoon_year IF NOT EXISTS FOR (t:Typhoon) ON (t.year)"
        },
        {
            "name": "typhoon_name_cn_index",
            "query": "CREATE INDEX typhoon_name_cn IF NOT EXISTS FOR (t:Typhoon) ON (t.name_cn)"
        },
        {
            "name": "typhoon_name_en_index",
            "query": "CREATE INDEX typhoon_name_en IF NOT EXISTS FOR (t:Typhoon) ON (t.name_en)"
        },
        {
            "name": "pathpoint_typhoon_id_index",
            "query": "CREATE INDEX pathpoint_typhoon_id IF NOT EXISTS FOR (p:PathPoint) ON (p.typhoon_id)"
        },
        {
            "name": "pathpoint_timestamp_index",
            "query": "CREATE INDEX pathpoint_timestamp IF NOT EXISTS FOR (p:PathPoint) ON (p.timestamp)"
        },
        {
            "name": "pathpoint_sequence_index",
            "query": "CREATE INDEX pathpoint_sequence IF NOT EXISTS FOR (p:PathPoint) ON (p.typhoon_id, p.sequence)"
        },
        {
            "name": "location_coords_index",
            "query": "CREATE INDEX location_coords IF NOT EXISTS FOR (l:Location) ON (l.lat, l.lon)"
        },
        {
            "name": "typhoon_year_name_composite_index",
            "query": "CREATE INDEX typhoon_year_name IF NOT EXISTS FOR (t:Typhoon) ON (t.year, t.name_cn)"
        }
    ],

    # ========== 全文索引 (Full-text Index) ==========
    "fulltext_indexes": [
        {
            "name": "typhoon_search_fulltext",
            "query": """
            CALL db.index.fulltext.createNodeIndex("typhoonSearch",
                ["Typhoon", "Location"],
                ["name_cn", "name_en", "name"],
                {analyzer: "cjk"}
            )
            """
        }
    ]
}


async def init_constraints():
    """初始化约束"""
    logger.info("=" * 60)
    logger.info("开始创建约束 (Constraints)")
    logger.info("=" * 60)

    for constraint in SCHEMA_QUERIES["constraints"]:
        try:
            await neo4j_client.run(constraint["query"])
            logger.info(f"✅ 约束创建成功: {constraint['name']}")
        except Exception as e:
            if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                logger.info(f"ℹ️ 约束已存在: {constraint['name']}")
            else:
                logger.error(f"❌ 约束创建失败 [{constraint['name']}]: {e}")
                raise


async def init_indexes():
    """初始化索引"""
    logger.info("=" * 60)
    logger.info("开始创建索引 (Indexes)")
    logger.info("=" * 60)

    for index in SCHEMA_QUERIES["indexes"]:
        try:
            await neo4j_client.run(index["query"])
            logger.info(f"✅ 索引创建成功: {index['name']}")
        except Exception as e:
            if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                logger.info(f"ℹ️ 索引已存在: {index['name']}")
            else:
                logger.error(f"❌ 索引创建失败 [{index['name']}]: {e}")
                raise


async def init_fulltext_indexes():
    """初始化全文索引"""
    logger.info("=" * 60)
    logger.info("开始创建全文索引 (Full-text Indexes)")
    logger.info("=" * 60)

    for ft_index in SCHEMA_QUERIES["fulltext_indexes"]:
        try:
            await neo4j_client.run(ft_index["query"])
            logger.info(f"✅ 全文索引创建成功: {ft_index['name']}")
        except Exception as e:
            error_msg = str(e).lower()
            if "already exists" in error_msg:
                logger.info(f"ℹ️ 全文索引已存在: {ft_index['name']}")
            elif "no procedure" in error_msg:
                logger.warning(f"⚠️ 全文索引功能不可用（可能是社区版）: {ft_index['name']}")
            else:
                logger.error(f"❌ 全文索引创建失败 [{ft_index['name']}]: {e}")
                # 全文索引失败不阻断流程


async def verify_schema():
    """验证Schema创建结果"""
    logger.info("=" * 60)
    logger.info("验证 Schema 创建结果")
    logger.info("=" * 60)

    try:
        # 查询约束
        constraints_result = await neo4j_client.run(
            "SHOW CONSTRAINTS YIELD name, type, entityType, labelsOrTypes, properties"
        )
        logger.info(f"📋 已创建约束数量: {len(constraints_result)}")
        for c in constraints_result:
            logger.info(f"   - {c['name']}: {c['type']} on {c['labelsOrTypes']}.{c['properties']}")

        # 查询索引
        indexes_result = await neo4j_client.run(
            "SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties, state"
        )
        logger.info(f"📇 已创建索引数量: {len(indexes_result)}")
        for idx in indexes_result:
            if idx['state'] == 'ONLINE':
                logger.info(f"   ✅ {idx['name']}: {idx['type']} - ONLINE")
            else:
                logger.warning(f"   ⏳ {idx['name']}: {idx['type']} - {idx['state']}")

        return True

    except Exception as e:
        logger.error(f"Schema验证失败: {e}")
        return False


async def init_schema():
    """
    主函数：初始化Neo4j Schema
    按照开发方案文档创建所有约束和索引
    """
    logger.info("\n" + "=" * 60)
    logger.info("Neo4j Schema 初始化开始")
    logger.info("=" * 60)

    try:
        # 1. 连接Neo4j
        logger.info("\n[1/5] 连接 Neo4j 数据库...")
        connected = await neo4j_client.connect()
        if not connected:
            logger.error("❌ 无法连接到Neo4j数据库，请检查:")
            logger.error("   1. Neo4j服务是否已启动")
            logger.error("   2. 配置是否正确 (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)")
            return False

        # 2. 创建约束
        logger.info("\n[2/5] 创建约束...")
        await init_constraints()

        # 3. 创建索引
        logger.info("\n[3/5] 创建索引...")
        await init_indexes()

        # 4. 创建全文索引
        logger.info("\n[4/5] 创建全文索引...")
        await init_fulltext_indexes()

        # 5. 验证结果
        logger.info("\n[5/5] 验证 Schema...")
        verified = await verify_schema()

        if verified:
            logger.info("\n" + "=" * 60)
            logger.info("✅ Neo4j Schema 初始化完成!")
            logger.info("=" * 60)
            return True
        else:
            logger.warning("⚠️ Schema 验证发现问题")
            return False

    except Exception as e:
        logger.error(f"\n❌ Schema 初始化失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    finally:
        await neo4j_client.close()


if __name__ == "__main__":
    # 运行初始化
    success = asyncio.run(init_schema())
    sys.exit(0 if success else 1)
