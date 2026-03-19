"""
语义搜索模块
基于向量嵌入的实体语义搜索
支持本地模型部署
"""

import os
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging
import asyncio
from functools import lru_cache

from loguru import logger

# 设置国内镜像源（可选）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None  # type: ignore
    logger.warning("sentence-transformers 未安装，将使用基于规则的回退方案")


@dataclass
class SemanticEntity:
    """语义实体"""
    entity_id: str
    entity_type: str
    entity_name: str
    description: str
    embedding: Optional[np.ndarray] = None
    score: float = 0.0
    properties: Dict = None


class EmbeddingService:
    """嵌入服务 - 支持本地模型部署"""
    
    # 使用轻量级多语言模型
    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # 本地模型路径
    LOCAL_MODEL_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "data", "sentence_model",
        "models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2",
        "snapshots"
    )
    
    def __init__(self, model_name: Optional[str] = None, local_path: Optional[str] = None, auto_load: bool = True):
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model = None
        self._embedding_cache = {}
        self._model_loaded = False

        # 优先使用指定的本地路径，否则使用默认路径
        if local_path:
            self.local_model_path = local_path
        else:
            self.local_model_path = self._find_local_model()

        # 自动加载模型（如果找到本地模型）
        if auto_load and self.local_model_path:
            self._load_model()
        
    def _find_local_model(self) -> Optional[str]:
        """查找本地模型路径"""
        try:
            if os.path.exists(self.LOCAL_MODEL_PATH):
                # 查找 snapshots 下的子目录
                snapshots = os.listdir(self.LOCAL_MODEL_PATH)
                if snapshots:
                    model_path = os.path.join(self.LOCAL_MODEL_PATH, snapshots[0])
                    if os.path.exists(os.path.join(model_path, "model.safetensors")):
                        logger.info(f"找到本地模型: {model_path}")
                        return model_path
        except Exception as e:
            logger.debug(f"查找本地模型失败: {e}")
        return None
        
    def _load_model(self):
        """懒加载模型 - 优先使用本地模型"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return None
            
        if self._model is None:
            try:
                # 优先加载本地模型
                if self.local_model_path and os.path.exists(self.local_model_path):
                    logger.info(f"加载本地模型: {self.local_model_path}")
                    self._model = SentenceTransformer(
                        self.local_model_path,
                        device='cpu'
                    )
                    self._model_loaded = True
                    logger.info("本地模型加载完成")
                else:
                    # 在线下载
                    logger.info(f"本地模型未找到，下载模型: {self.model_name}")
                    logger.info("使用国内镜像源: https://hf-mirror.com")
                    
                    cache_dir = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                        "data", "sentence_model"
                    )
                    
                    self._model = SentenceTransformer(
                        self.model_name,
                        device='cpu',
                        cache_folder=cache_dir
                    )
                    self._model_loaded = True
                    logger.info("模型下载并加载完成")
                    
                    # 更新本地路径
                    self.local_model_path = self._find_local_model()
                    
            except Exception as e:
                logger.error(f"加载嵌入模型失败: {e}")
                self._model = None
        return self._model
    
    async def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """获取文本的嵌入向量"""
        if not text:
            return None
            
        # 检查缓存
        cache_key = hash(text)
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        model = self._load_model()
        if model is None:
            return None
        
        try:
            # 在线程池中运行同步模型推理
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                lambda: model.encode(text, convert_to_numpy=True, show_progress_bar=False)
            )
            
            # 缓存结果
            self._embedding_cache[cache_key] = embedding
            return embedding
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {e}")
            return None
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """批量获取嵌入向量"""
        if not texts:
            return []
        
        model = self._load_model()
        if model is None:
            return [None] * len(texts)
        
        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: model.encode(texts, convert_to_numpy=True, show_progress_bar=False, batch_size=32)
            )
            return list(embeddings)
        except Exception as e:
            logger.error(f"批量生成嵌入向量失败: {e}")
            return [None] * len(texts)
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """计算两个嵌入向量的余弦相似度"""
        if embedding1 is None or embedding2 is None:
            return 0.0
        
        try:
            # 归一化向量
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # 计算余弦相似度
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            
            # 转换为 0-1 范围
            return float((similarity + 1) / 2)
        except Exception as e:
            logger.error(f"计算相似度失败: {e}")
            return 0.0
    
    def is_available(self) -> bool:
        """检查嵌入服务是否可用"""
        return self._model_loaded
    
    def get_model_info(self) -> Dict:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "local_path": self.local_model_path,
            "is_loaded": self._model_loaded,
            "cache_size": len(self._embedding_cache)
        }


class SemanticEntitySearch:
    """语义实体搜索"""
    
    def __init__(self, neo4j_client, embedding_service: Optional[EmbeddingService] = None):
        self.neo4j = neo4j_client
        self.embedding_service = embedding_service or EmbeddingService()
        self._entity_cache = {}
        self._cache_initialized = False
        self._use_semantic = True  # 是否启用语义搜索
    
    async def initialize_cache(self):
        """初始化实体缓存（预加载所有台风实体）"""
        if self._cache_initialized:
            return
        
        # 检查嵌入服务是否可用
        if not self.embedding_service.is_available():
            logger.warning("嵌入服务不可用，将仅使用关键词匹配")
            self._use_semantic = False
            return
        
        try:
            logger.info("初始化语义搜索缓存...")
            
            # 获取所有台风实体
            query = """
            MATCH (t:Typhoon)
            RETURN t.typhoon_id as id,
                   t.name_cn as name_cn,
                   t.name_en as name_en,
                   t.year as year,
                   t.max_wind_speed as max_wind_speed,
                   t.min_pressure as min_pressure,
                   t.peak_intensity as peak_intensity
            LIMIT 1000
            """
            
            result = await self.neo4j.run(query)
            
            entities = []
            descriptions = []
            
            for record in result:
                # 构建实体描述文本
                desc_parts = []
                name = record.get("name_cn") or record.get("name_en") or record.get("id")
                desc_parts.append(f"台风{name}")
                
                if record.get("year"):
                    desc_parts.append(f"发生在{record['year']}年")
                if record.get("max_wind_speed"):
                    desc_parts.append(f"最大风速{record['max_wind_speed']}米每秒")
                if record.get("min_pressure"):
                    desc_parts.append(f"最低气压{record['min_pressure']}百帕")
                if record.get("peak_intensity"):
                    desc_parts.append(f"最高强度为{record['peak_intensity']}")
                
                description = "。".join(desc_parts)
                
                entity = SemanticEntity(
                    entity_id=record.get("id"),
                    entity_type="Typhoon",
                    entity_name=name,
                    description=description,
                    properties=dict(record)
                )
                
                entities.append(entity)
                descriptions.append(description)
            
            # 批量生成嵌入向量
            logger.info(f"为 {len(descriptions)} 个实体生成嵌入向量...")
            embeddings = await self.embedding_service.get_embeddings_batch(descriptions)
            
            # 存储到缓存
            for entity, embedding in zip(entities, embeddings):
                if embedding is not None:
                    entity.embedding = embedding
                    self._entity_cache[entity.entity_id] = entity
            
            self._cache_initialized = True
            logger.info(f"语义搜索缓存初始化完成，共 {len(self._entity_cache)} 个实体")
            
        except Exception as e:
            logger.error(f"初始化语义搜索缓存失败: {e}")
            self._use_semantic = False
    
    async def search(
        self, 
        query: str, 
        top_k: int = 10,
        min_score: float = 0.3
    ) -> List[SemanticEntity]:
        """
        语义搜索实体
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            min_score: 最小相似度阈值
            
        Returns:
            语义实体列表
        """
        # 如果语义搜索不可用，返回空列表
        if not self._use_semantic:
            return []
        
        # 确保缓存已初始化
        if not self._cache_initialized:
            await self.initialize_cache()
        
        if not self._entity_cache:
            logger.warning("实体缓存为空，无法进行语义搜索")
            return []
        
        # 获取查询的嵌入向量
        query_embedding = await self.embedding_service.get_embedding(query)
        if query_embedding is None:
            logger.warning("无法生成查询的嵌入向量")
            return []
        
        # 计算与所有实体的相似度
        scored_entities = []
        for entity in self._entity_cache.values():
            if entity.embedding is not None:
                similarity = self.embedding_service.compute_similarity(
                    query_embedding, entity.embedding
                )
                if similarity >= min_score:
                    entity.score = similarity
                    scored_entities.append(entity)
        
        # 按相似度排序并返回前k个
        scored_entities.sort(key=lambda x: x.score, reverse=True)
        return scored_entities[:top_k]
    
    async def search_with_keywords(
        self,
        query: str,
        keywords: List[str],
        top_k: int = 10,
        semantic_weight: float = 0.6
    ) -> List[SemanticEntity]:
        """
        混合搜索：结合语义搜索和关键词匹配
        
        Args:
            query: 查询文本
            keywords: 关键词列表
            top_k: 返回结果数量
            semantic_weight: 语义相似度权重 (0-1)
            
        Returns:
            语义实体列表
        """
        # 获取语义搜索结果
        semantic_results = await self.search(query, top_k=top_k * 2)
        
        # 计算混合分数
        for entity in semantic_results:
            # 关键词匹配分数
            keyword_score = 0.0
            entity_text = entity.description.lower()
            for keyword in keywords:
                if keyword.lower() in entity_text:
                    keyword_score += 0.2  # 每个匹配关键词加0.2分
            keyword_score = min(keyword_score, 1.0)  # 上限1.0
            
            # 混合分数
            entity.score = (
                semantic_weight * entity.score + 
                (1 - semantic_weight) * keyword_score
            )
        
        # 重新排序
        semantic_results.sort(key=lambda x: x.score, reverse=True)
        return semantic_results[:top_k]
    
    def is_available(self) -> bool:
        """检查语义搜索是否可用"""
        return self._use_semantic and self.embedding_service.is_available()
    
    def get_service_info(self) -> Dict:
        """获取服务信息"""
        return {
            "semantic_available": self.is_available(),
            "cache_initialized": self._cache_initialized,
            "entity_count": len(self._entity_cache),
            "model_info": self.embedding_service.get_model_info()
        }


# 全局实例
embedding_service = EmbeddingService()
