"""
Neo4j 图数据库客户端模块
提供异步连接管理和查询执行功能
"""
from neo4j import AsyncGraphDatabase
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from loguru import logger
from datetime import datetime

from app.core.config import settings


def convert_neo4j_types(obj):
    """
    递归转换 Neo4j 特殊类型为 Python 原生类型
    
    Args:
        obj: 要转换的对象
        
    Returns:
        转换后的对象
    """
    if obj is None:
        return None
    
    try:
        from neo4j.time import DateTime, Date, Time
        has_datetime = True
    except ImportError:
        has_datetime = False
        DateTime = Date = Time = None
    
    try:
        from neo4j.time import LocalDateTime, LocalDate, LocalTime
        has_local = True
    except ImportError:
        has_local = False
        LocalDateTime = LocalDate = LocalTime = None
    
    try:
        from neo4j.graph import Node, Relationship, Path
        has_graph = True
    except ImportError:
        has_graph = False
        Node = Relationship = Path = None
    
    if has_datetime:
        if isinstance(obj, DateTime):
            return obj.to_native()
        if isinstance(obj, Date):
            return obj.to_native()
        if isinstance(obj, Time):
            return obj.to_native()
    
    if has_local:
        if isinstance(obj, LocalDateTime):
            return obj.to_native()
        if isinstance(obj, LocalDate):
            return obj.to_native()
        if isinstance(obj, LocalTime):
            return obj.to_native()
    
    if has_graph:
        if isinstance(obj, Node):
            return convert_neo4j_types(dict(obj))
        if isinstance(obj, Relationship):
            return convert_neo4j_types(dict(obj))
        if isinstance(obj, Path):
            return {
                "nodes": [convert_neo4j_types(n) for n in obj.nodes],
                "relationships": [convert_neo4j_types(r) for r in obj.relationships]
            }
    
    if isinstance(obj, dict):
        return {k: convert_neo4j_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_neo4j_types(item) for item in obj]
    else:
        return obj


class Neo4jClient:
    """
    Neo4j 异步客户端
    
    功能：
    1. 异步连接管理
    2. 连接池管理
    3. Cypher查询执行
    4. 事务支持
    5. 自动重连机制
    """
    
    def __init__(self):
        self._driver: Optional[AsyncGraphDatabase.driver] = None
        self._connected = False
    
    async def connect(self) -> bool:
        """
        建立与Neo4j数据库的异步连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self._driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_pool_size=settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
                connection_timeout=settings.NEO4J_CONNECTION_TIMEOUT
            )
            
            # 验证连接
            await self._driver.verify_connectivity()
            self._connected = True
            logger.info(f"✅ Neo4j连接成功: {settings.NEO4J_URI}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Neo4j连接失败: {e}")
            self._connected = False
            return False
    
    async def close(self):
        """关闭Neo4j连接"""
        if self._driver:
            await self._driver.close()
            self._connected = False
            logger.info("Neo4j连接已关闭")
    
    @asynccontextmanager
    async def session(self):
        """
        会话上下文管理器
        
        使用示例:
            async with neo4j_client.session() as session:
                result = await session.run(query, params)
        """
        if not self._connected or not self._driver:
            await self.connect()
        
        async with self._driver.session() as session:
            yield session
    
    async def run(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        执行Cypher查询
        
        Args:
            query: Cypher查询语句
            parameters: 查询参数
            
        Returns:
            List[Dict]: 查询结果列表
            
        Raises:
            Exception: 查询执行失败时抛出异常
        """
        parameters = parameters or {}
        
        try:
            async with self.session() as session:
                result = await session.run(query, parameters)
                records = await result.data()
                return convert_neo4j_types(records)
                
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            logger.error(f"查询: {query[:100]}...")
            raise
    
    async def run_transaction(self, queries: List[tuple]) -> List[List[Dict[str, Any]]]:
        """
        执行事务（多个查询原子执行）
        
        Args:
            queries: 查询列表，每个元素为 (query, parameters) 元组
            
        Returns:
            List[List[Dict]]: 每个查询的结果列表
        """
        results = []
        
        async with self.session() as session:
            async with session.begin_transaction() as tx:
                for query, params in queries:
                    result = await tx.run(query, params or {})
                    records = await result.data()
                    results.append(records)
        
        return results
    
    async def execute_write(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        执行写操作（自动使用写事务）
        
        Args:
            query: Cypher写操作语句
            parameters: 查询参数
            
        Returns:
            List[Dict]: 操作结果
        """
        parameters = parameters or {}
        
        try:
            async with self.session() as session:
                result = await session.execute_write(
                    self._do_write, query, parameters
                )
                return result
        except Exception as e:
            logger.error(f"写操作执行失败: {e}")
            raise
    
    @staticmethod
    async def _do_write(tx, query: str, parameters: Dict[str, Any]):
        """内部写操作执行函数"""
        result = await tx.run(query, parameters)
        return await result.data()
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        测试Neo4j连接状态
        
        Returns:
            Dict: 包含连接状态和数据库信息的字典
        """
        try:
            if not self._connected:
                await self.connect()
            
            # 获取数据库信息
            result = await self.run("CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition")
            
            return {
                "connected": True,
                "uri": settings.NEO4J_URI,
                "database_info": result[0] if result else None
            }
            
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def get_statistics(self) -> Dict[str, int]:
        """
        获取数据库统计信息
        
        Returns:
            Dict: 各类节点和关系的数量统计
        """
        stats = {}
        
        queries = {
            "typhoon_count": "MATCH (t:Typhoon) RETURN count(t) as count",
            "pathpoint_count": "MATCH (p:PathPoint) RETURN count(p) as count",
            "location_count": "MATCH (l:Location) RETURN count(l) as count",
            "time_count": "MATCH (tm:Time) RETURN count(tm) as count",
            "intensity_count": "MATCH (i:Intensity) RETURN count(i) as count",
            "landed_rel_count": "MATCH ()-[r:LANDED_AT]->() RETURN count(r) as count",
            "path_rel_count": "MATCH ()-[r:HAS_PATH_POINT]->() RETURN count(r) as count",
            "next_rel_count": "MATCH ()-[r:NEXT]->() RETURN count(r) as count",
            "occurred_rel_count": "MATCH ()-[r:OCCURRED_IN]->() RETURN count(r) as count"
        }
        
        for key, query in queries.items():
            try:
                result = await self.run(query)
                stats[key] = result[0]["count"] if result else 0
            except Exception as e:
                logger.warning(f"获取统计信息失败 [{key}]: {e}")
                stats[key] = 0
        
        return stats


# 全局客户端实例
neo4j_client = Neo4jClient()


async def get_neo4j_client() -> Neo4jClient:
    """
    获取Neo4j客户端实例（依赖注入用）
    
    Returns:
        Neo4jClient: 全局Neo4j客户端实例
    """
    if not neo4j_client._connected:
        await neo4j_client.connect()
    return neo4j_client
