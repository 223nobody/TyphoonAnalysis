"""
图像分析服务
提供图像处理、特征提取、AI分析等功能

重构说明：
- 已从通义千问API调用改为混合方案（传统方法 + 迁移学习）
- 集成OpenCV传统图像处理、深度学习模型和决策融合
- 保持API接口兼容性
"""
import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import io

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image
import numpy as np

from app.models.image import TyphoonImage

# 导入新的分析模块
from .opencv_analyzer import OpenCVAnalyzer, OPENCV_AVAILABLE
from .dl_analyzer import DLAnalyzer, PYTORCH_AVAILABLE
from .fusion_analyzer import FusionAnalyzer

logger = logging.getLogger(__name__)


class ImageAnalysisService:
    """
    图像分析服务类

    重构说明：
    - 集成混合方案（OpenCV + 深度学习 + 决策融合）
    - 支持多种分析类型：basic/advanced/opencv/fusion
    - 保持向后兼容性
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.save_dir = Path("data/images")
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # 初始化分析器
        self.opencv_analyzer = None
        self.dl_analyzer = None
        self.fusion_analyzer = None

        # 尝试初始化OpenCV分析器
        if OPENCV_AVAILABLE:
            try:
                self.opencv_analyzer = OpenCVAnalyzer()
                logger.info("✅ OpenCV分析器初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ OpenCV分析器初始化失败: {e}")
        else:
            logger.warning("⚠️ OpenCV未安装，传统图像处理功能不可用")

        # 尝试初始化深度学习分析器
        if PYTORCH_AVAILABLE:
            try:
                self.dl_analyzer = DLAnalyzer()
                logger.info("✅ 深度学习分析器初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ 深度学习分析器初始化失败: {e}")
        else:
            logger.warning("⚠️ PyTorch未安装，深度学习功能不可用")

        # 初始化决策融合分析器
        try:
            self.fusion_analyzer = FusionAnalyzer()
            logger.info("✅ 决策融合分析器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 决策融合分析器初始化失败: {e}")

    async def save_image(
        self,
        filename: str,
        content: bytes,
        typhoon_id: Optional[str] = None,
        image_type: str = "satellite",
        source: Optional[str] = None
    ) -> TyphoonImage:
        """
        保存图像到数据库

        Args:
            filename: 文件名
            content: 图像二进制内容
            typhoon_id: 台风ID
            image_type: 图像类型
            source: 数据源

        Returns:
            图像记录对象
        """
        try:
            # 解析图像元数据
            img = Image.open(io.BytesIO(content))
            width, height = img.size
            img_format = img.format

            # 保存到文件系统
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = self.save_dir / image_type / f"{timestamp}_{filename}"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)

            # 创建数据库记录
            image_record = TyphoonImage(
                typhoon_id=typhoon_id,
                filename=filename,
                image_type=image_type,
                source=source,
                file_path=str(file_path),
                file_size=len(content),
                width=width,
                height=height,
                format=img_format.lower() if img_format else None,
                upload_time=datetime.now()
            )

            self.db.add(image_record)
            await self.db.commit()
            await self.db.refresh(image_record)

            logger.info(f"✅ 图像保存成功: {filename} (ID: {image_record.id})")
            return image_record

        except Exception as e:
            logger.error(f"❌ 图像保存失败: {filename} - {e}", exc_info=True)
            await self.db.rollback()
            raise

    async def get_image(self, image_id: int) -> Optional[TyphoonImage]:
        """
        获取图像记录

        Args:
            image_id: 图像ID

        Returns:
            图像记录对象
        """
        query = select(TyphoonImage).where(TyphoonImage.id == image_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_typhoon_images(
        self,
        typhoon_id: str,
        image_type: Optional[str] = None,
        limit: int = 20
    ) -> List[TyphoonImage]:
        """
        获取指定台风的图像列表

        Args:
            typhoon_id: 台风ID
            image_type: 图像类型筛选
            limit: 返回数量限制

        Returns:
            图像列表
        """
        query = select(TyphoonImage).where(TyphoonImage.typhoon_id == typhoon_id)

        if image_type:
            query = query.where(TyphoonImage.image_type == image_type)

        query = query.order_by(TyphoonImage.upload_time.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def analyze_image(
        self,
        image: TyphoonImage,
        analysis_type: str = "fusion",
        image_type: str = "infrared"
    ) -> Dict[str, Any]:
        """
        分析图像（重构版本）

        Args:
            image: 图像记录对象
            analysis_type: 分析类型
                - basic: 基础统计分析（保持向后兼容）
                - advanced: 高级特征提取（保持向后兼容）
                - opencv: 仅使用OpenCV传统方法
                - fusion: 混合方案（OpenCV + 深度学习 + 决策融合）⭐推荐
            image_type: 图像类型（infrared=红外图, visible=可见光图）

        Returns:
            分析结果字典
        """
        start_time = datetime.now()

        try:
            # 读取图像
            img_path = Path(image.file_path)
            if not img_path.exists():
                raise FileNotFoundError(f"图像文件不存在: {img_path}")

            img = Image.open(img_path)

            # 根据分析类型执行不同的分析
            if analysis_type == "basic":
                result = await self._basic_analysis(img)
            elif analysis_type == "advanced":
                result = await self._advanced_analysis(img)
            elif analysis_type == "opencv":
                result = await self._opencv_analysis(img, image_type)
            elif analysis_type == "fusion":
                result = await self._fusion_analysis(img, image_type)
            else:
                raise ValueError(f"不支持的分析类型: {analysis_type}")

            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            result["processing_time"] = processing_time

            logger.info(f"✅ 图像分析完成: ID={image.id}, 类型={analysis_type}, 耗时={processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"❌ 图像分析失败: {e}", exc_info=True)
            raise

    async def _opencv_analysis(self, img: Image.Image, image_type: str) -> Dict[str, Any]:
        """
        OpenCV传统图像分析

        Args:
            img: PIL图像对象
            image_type: 图像类型

        Returns:
            分析结果
        """
        if self.opencv_analyzer is None:
            raise RuntimeError("OpenCV分析器未初始化，请安装opencv-python")

        try:
            result = self.opencv_analyzer.analyze(img, image_type)
            return result
        except Exception as e:
            logger.error(f"❌ OpenCV分析失败: {e}", exc_info=True)
            raise

    async def _fusion_analysis(self, img: Image.Image, image_type: str) -> Dict[str, Any]:
        """
        混合方案分析（OpenCV + 深度学习 + 决策融合）

        Args:
            img: PIL图像对象
            image_type: 图像类型

        Returns:
            分析结果
        """
        try:
            # 1. OpenCV传统分析
            opencv_result = {}
            if self.opencv_analyzer is not None:
                try:
                    opencv_result = self.opencv_analyzer.analyze(img, image_type)
                    logger.info("✅ OpenCV分析完成")
                except Exception as e:
                    logger.warning(f"⚠️ OpenCV分析失败: {e}")
                    opencv_result = {"method": "opencv", "error": str(e)}
            else:
                logger.warning("⚠️ OpenCV分析器不可用")
                opencv_result = {"method": "opencv", "status": "unavailable"}

            # 2. 深度学习分析
            dl_result = {}
            if self.dl_analyzer is not None:
                try:
                    dl_result = self.dl_analyzer.analyze(img)
                    logger.info("✅ 深度学习分析完成")
                except Exception as e:
                    logger.warning(f"⚠️ 深度学习分析失败: {e}")
                    dl_result = {"method": "deep_learning", "error": str(e)}
            else:
                logger.warning("⚠️ 深度学习分析器不可用")
                dl_result = {"method": "deep_learning", "status": "unavailable"}

            # 3. 决策融合
            if self.fusion_analyzer is not None:
                try:
                    fused_result = self.fusion_analyzer.fuse(opencv_result, dl_result)
                    logger.info("✅ 决策融合完成")
                    return fused_result
                except Exception as e:
                    logger.warning(f"⚠️ 决策融合失败: {e}")
                    # 融合失败，返回OpenCV结果作为备选
                    return opencv_result
            else:
                # 融合分析器不可用，返回OpenCV结果
                return opencv_result

        except Exception as e:
            logger.error(f"❌ 混合方案分析失败: {e}", exc_info=True)
            raise

    async def _basic_analysis(self, img: Image.Image) -> Dict[str, Any]:
        """
        基础图像分析

        Args:
            img: PIL图像对象

        Returns:
            分析结果
        """
        # 转换为numpy数组
        img_array = np.array(img)

        # 基础统计信息
        result = {
            "type": "basic",
            "dimensions": {
                "width": img.width,
                "height": img.height,
                "channels": len(img.getbands())
            },
            "statistics": {
                "mean": float(np.mean(img_array)),
                "std": float(np.std(img_array)),
                "min": int(np.min(img_array)),
                "max": int(np.max(img_array))
            },
            "color_info": {
                "mode": img.mode,
                "bands": img.getbands()
            },
            "confidence": 1.0
        }

        return result

    async def _advanced_analysis(self, img: Image.Image) -> Dict[str, Any]:
        """
        高级图像分析（特征提取）
        保持向后兼容性

        Args:
            img: PIL图像对象

        Returns:
            分析结果
        """
        img_array = np.array(img)

        # 高级特征提取
        result = {
            "type": "advanced",
            "features": {
                "brightness": float(np.mean(img_array)),
                "contrast": float(np.std(img_array)),
                "sharpness": self._calculate_sharpness(img_array),
                "texture": self._calculate_texture(img_array)
            },
            "cloud_coverage": self._estimate_cloud_coverage(img_array),
            "intensity_distribution": self._analyze_intensity_distribution(img_array),
            "confidence": 0.85
        }

        return result

    def _calculate_sharpness(self, img_array: np.ndarray) -> float:
        """计算图像清晰度"""
        # 使用Laplacian算子计算清晰度
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2)
        else:
            gray = img_array

        # 简化计算
        return float(np.std(gray))

    def _calculate_texture(self, img_array: np.ndarray) -> float:
        """计算图像纹理复杂度"""
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2)
        else:
            gray = img_array

        # 简化的纹理计算
        return float(np.std(np.diff(gray, axis=0)) + np.std(np.diff(gray, axis=1)))

    def _estimate_cloud_coverage(self, img_array: np.ndarray) -> float:
        """估算云量覆盖率"""
        # 简化的云量估算（基于亮度阈值）
        if len(img_array.shape) == 3:
            brightness = np.mean(img_array, axis=2)
        else:
            brightness = img_array

        cloud_pixels = np.sum(brightness > 128)
        total_pixels = brightness.size

        return float(cloud_pixels / total_pixels)

    def _analyze_intensity_distribution(self, img_array: np.ndarray) -> Dict[str, Any]:
        """分析强度分布"""
        if len(img_array.shape) == 3:
            intensity = np.mean(img_array, axis=2)
        else:
            intensity = img_array

        hist, bins = np.histogram(intensity, bins=10)

        return {
            "histogram": hist.tolist(),
            "bins": bins.tolist(),
            "peak_intensity": float(bins[np.argmax(hist)])
        }

    async def delete_image(self, image_id: int) -> bool:
        """
        删除图像

        Args:
            image_id: 图像ID

        Returns:
            是否删除成功
        """
        try:
            image = await self.get_image(image_id)
            if not image:
                return False

            # 删除文件
            if image.file_path:
                file_path = Path(image.file_path)
                if file_path.exists():
                    file_path.unlink()

            # 删除数据库记录
            await self.db.delete(image)
            await self.db.commit()

            logger.info(f"✅ 图像删除成功: ID={image_id}")
            return True

        except Exception as e:
            logger.error(f"❌ 图像删除失败: {e}", exc_info=True)
            await self.db.rollback()
            return False
