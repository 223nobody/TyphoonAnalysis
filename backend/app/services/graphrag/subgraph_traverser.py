"""
子图遍历服务
从种子实体出发遍历局部子图

注：主要功能已集成到graphrag_engine.py中
此文件保留用于未来扩展
"""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SubgraphTraverser:
    """子图遍历器"""
    
    def __init__(self, neo4j_client):
        self.neo4j = neo4j_client
