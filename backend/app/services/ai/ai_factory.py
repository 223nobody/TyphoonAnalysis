"""
AI服务工厂类
根据配置动态选择使用通义千问或DeepSeek服务
"""
import logging
from typing import Dict, Optional

from app.core.config import settings
from app.services.ai.qwen_service import qwen_service
from app.services.ai.deepseek_service import deepseek_service

logger = logging.getLogger(__name__)


class AIServiceFactory:
    """AI服务工厂类"""
    
    @staticmethod
    def get_service():
        """
        根据配置获取AI服务实例
        
        Returns:
            AI服务实例（QwenService 或 DeepSeekService）
        """
        provider = settings.AI_PROVIDER.lower()
        
        if provider == "deepseek":
            logger.info("使用DeepSeek AI服务")
            return deepseek_service
        elif provider == "qwen":
            logger.info("使用通义千问AI服务")
            return qwen_service
        else:
            logger.warning(f"未知的AI服务提供商: {provider}，使用默认的通义千问服务")
            return qwen_service
    
    @staticmethod
    async def analyze_typhoon_image(
        image_path: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Dict:
        """
        分析台风图像（统一接口）
        
        Args:
            image_path: 图片本地路径
            image_url: 图片URL
            
        Returns:
            Dict: 分析结果
        """
        service = AIServiceFactory.get_service()
        return await service.analyze_typhoon_image(
            image_path=image_path,
            image_url=image_url
        )
    
    @staticmethod
    async def generate_typhoon_report(
        typhoon_id: str,
        typhoon_name: str,
        prediction_data: Dict,
        analysis_data: Optional[Dict] = None
    ) -> Dict:
        """
        生成台风报告（统一接口）
        
        Args:
            typhoon_id: 台风编号
            typhoon_name: 台风名称
            prediction_data: 预测数据
            analysis_data: 分析数据
            
        Returns:
            Dict: 报告生成结果
        """
        service = AIServiceFactory.get_service()
        return await service.generate_typhoon_report(
            typhoon_id=typhoon_id,
            typhoon_name=typhoon_name,
            prediction_data=prediction_data,
            analysis_data=analysis_data
        )


# 创建全局工厂实例
ai_factory = AIServiceFactory()

