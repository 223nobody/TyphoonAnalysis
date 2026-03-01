"""清理Neo4j数据库"""
import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.neo4j_client import neo4j_client

async def clear_database():
    """清空所有数据"""
    print("正在连接Neo4j...")
    connected = await neo4j_client.connect()
    if not connected:
        print("❌ 连接失败")
        return
    
    print("正在清空数据库...")
    result = await neo4j_client.run("MATCH (n) DETACH DELETE n")
    print("✅ 数据库已清空")
    
    # 统计
    count_result = await neo4j_client.run("MATCH (n) RETURN count(n) as count")
    count = count_result[0]['count'] if count_result else -1
    print(f"当前节点数: {count}")
    
    await neo4j_client.close()

if __name__ == "__main__":
    asyncio.run(clear_database())
