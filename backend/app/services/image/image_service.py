"""
图像分析服务
提供图像上传、结构化分析、few-shot AI 报告生成与结果持久化
"""
import io
import json
import logging
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image import TyphoonImage
from app.models.image_analysis import ImageAnalysisResult
from app.services.ai.qwen_image_service import qwen_image_service

from .dl_analyzer import DLAnalyzer, PYTORCH_AVAILABLE
from .fusion_analyzer import FusionAnalyzer
from .opencv_analyzer import OPENCV_AVAILABLE, OpenCVAnalyzer

logger = logging.getLogger(__name__)


class DuplicateImageError(ValueError):
    """重复上传同名图片时抛出的异常"""


class ImageAnalysisService:
    """
    图像分析服务类

    支持：
    - basic: 基础统计分析
    - advanced: 高级特征提取
    - opencv: 传统视觉分析
    - fusion: OpenCV + 深度学习融合
    - hybrid_ai: 结构化结果 + few-shot 通义千问报告
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.base_dir = Path(__file__).resolve().parents[3]
        self.save_dir = self.base_dir / "data" / "images"
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.opencv_analyzer = None
        self.dl_analyzer = None
        self.fusion_analyzer = None
        self.qwen_image_service = qwen_image_service

        if OPENCV_AVAILABLE:
            try:
                self.opencv_analyzer = OpenCVAnalyzer()
                logger.info("✅ OpenCV分析器初始化成功")
            except Exception as exc:
                logger.warning("⚠️ OpenCV分析器初始化失败: %s", exc)
        else:
            logger.warning("⚠️ OpenCV未安装，传统图像处理功能不可用")

        if PYTORCH_AVAILABLE:
            try:
                self.dl_analyzer = DLAnalyzer()
                logger.info("✅ 深度学习分析器初始化成功")
            except Exception as exc:
                logger.warning("⚠️ 深度学习分析器初始化失败: %s", exc)
        else:
            logger.warning("⚠️ PyTorch未安装，深度学习功能不可用")

        try:
            self.fusion_analyzer = FusionAnalyzer()
            logger.info("✅ 决策融合分析器初始化成功")
        except Exception as exc:
            logger.warning("⚠️ 决策融合分析器初始化失败: %s", exc)

    async def save_image(
        self,
        filename: str,
        content: bytes,
        typhoon_id: Optional[str] = None,
        image_type: str = "satellite",
        source: Optional[str] = None,
    ) -> TyphoonImage:
        """保存图像到数据库和文件系统"""
        try:
            safe_filename = Path(filename or "").name.strip()
            if not safe_filename:
                raise ValueError("上传的文件名无效")

            existing_image = await self.get_image_by_filename(safe_filename)
            if existing_image:
                raise DuplicateImageError(
                    f"图片 {safe_filename} 已上传（ID: {existing_image.id}），同一图片无需重复上传"
                )

            img = Image.open(io.BytesIO(content))
            width, height = img.size
            img_format = img.format

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = self.save_dir / image_type / f"{timestamp}_{safe_filename}"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)

            image_record = TyphoonImage(
                typhoon_id=typhoon_id,
                filename=safe_filename,
                image_type=image_type,
                source=source,
                file_path=str(file_path),
                file_size=len(content),
                width=width,
                height=height,
                format=img_format.lower() if img_format else None,
                upload_time=datetime.now(),
            )

            self.db.add(image_record)
            await self.db.commit()
            await self.db.refresh(image_record)

            logger.info("✅ 图像保存成功: %s (ID: %s)", safe_filename, image_record.id)
            return image_record
        except DuplicateImageError:
            await self.db.rollback()
            raise
        except Exception as exc:
            logger.error("❌ 图像保存失败: %s - %s", filename, exc, exc_info=True)
            await self.db.rollback()
            raise

    async def get_image(self, image_id: int) -> Optional[TyphoonImage]:
        query = select(TyphoonImage).where(TyphoonImage.id == image_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_image_by_filename(self, filename: str) -> Optional[TyphoonImage]:
        query = select(TyphoonImage).where(TyphoonImage.filename == filename)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_typhoon_images(
        self,
        typhoon_id: str,
        image_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[TyphoonImage]:
        query = select(TyphoonImage).where(TyphoonImage.typhoon_id == typhoon_id)
        if image_type:
            query = query.where(TyphoonImage.image_type == image_type)
        query = query.order_by(TyphoonImage.upload_time.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def analyze_image(
        self,
        image: TyphoonImage,
        analysis_type: str = "hybrid_ai",
        image_type: str = "visible",
    ) -> Dict[str, Any]:
        """分析图像并持久化分析结果"""
        start_time = datetime.now()
        analysis_record = await self._create_analysis_record(image.id, analysis_type)

        try:
            img_path = Path(image.file_path)
            if not img_path.exists():
                raise FileNotFoundError(f"图像文件不存在: {img_path}")

            img = Image.open(img_path)

            if analysis_type == "basic":
                result = await self._basic_analysis(img)
            elif analysis_type == "advanced":
                result = await self._advanced_analysis(img)
            elif analysis_type == "opencv":
                result = await self._opencv_analysis(img, image_type)
            elif analysis_type == "fusion":
                result = await self._fusion_analysis(img, image_type)
            elif analysis_type == "hybrid_ai":
                result = await self._hybrid_ai_analysis(img, img_path, image_type)
            else:
                raise ValueError(f"不支持的分析类型: {analysis_type}")

            result = self._attach_image_context(result, image, img, image_type)
            processing_time = (datetime.now() - start_time).total_seconds()
            result["analysis_id"] = analysis_record.id
            result["status"] = "completed"
            result["processing_time"] = processing_time
            result["analysis_type"] = analysis_type
            result["analyzed_at"] = datetime.now().isoformat()

            await self._complete_analysis_record(analysis_record, result)
            logger.info(
                "✅ 图像分析完成: image_id=%s, analysis_id=%s, 类型=%s, 耗时=%.2fs",
                image.id,
                analysis_record.id,
                analysis_type,
                processing_time,
            )
            return result
        except Exception as exc:
            logger.error("❌ 图像分析失败: %s", exc, exc_info=True)
            await self._fail_analysis_record(
                analysis_record,
                error_message=str(exc),
                processing_time=(datetime.now() - start_time).total_seconds(),
            )
            raise

    async def _create_analysis_record(
        self,
        image_id: int,
        analysis_type: str,
    ) -> ImageAnalysisResult:
        record = ImageAnalysisResult(
            image_id=image_id,
            analysis_type=analysis_type,
            status="processing",
            analyzed_at=datetime.now(),
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def _complete_analysis_record(
        self,
        record: ImageAnalysisResult,
        result: Dict[str, Any],
    ) -> None:
        stored_result = deepcopy(result)
        stored_result.pop("ai_report", None)
        stored_result.pop("summary", None)
        stored_result.pop("risk_flags", None)
        stored_result.pop("fewshot_examples_used", None)
        stored_result.pop("model_used", None)
        stored_result.pop("status", None)

        record.status = "completed"
        record.method = result.get("method")
        record.result_data = json.dumps(stored_result, ensure_ascii=False)
        record.confidence = result.get("confidence")
        record.summary = result.get("summary")
        record.ai_report = result.get("ai_report")
        record.consistency_score = result.get("consistency_score")
        record.risk_flags = json.dumps(result.get("risk_flags", []), ensure_ascii=False)
        record.fewshot_examples = json.dumps(
            result.get("fewshot_examples_used", []),
            ensure_ascii=False,
        )
        record.ai_model = result.get("model_used")
        record.processing_time = result.get("processing_time")
        record.error_message = None
        record.analyzed_at = datetime.now()

        await self.db.commit()
        await self.db.refresh(record)

    async def _fail_analysis_record(
        self,
        record: ImageAnalysisResult,
        error_message: str,
        processing_time: float,
    ) -> None:
        record.status = "failed"
        record.error_message = error_message
        record.processing_time = processing_time
        record.analyzed_at = datetime.now()
        await self.db.commit()

    async def _opencv_analysis(self, img: Image.Image, image_type: str) -> Dict[str, Any]:
        if self.opencv_analyzer is None:
            raise RuntimeError("OpenCV分析器未初始化，请安装 opencv-python")

        result = self.opencv_analyzer.analyze(img, image_type)
        result.setdefault("method", "opencv")
        return result

    async def _fusion_analysis(self, img: Image.Image, image_type: str) -> Dict[str, Any]:
        try:
            opencv_result: Dict[str, Any]
            if self.opencv_analyzer is not None:
                try:
                    opencv_result = self.opencv_analyzer.analyze(img, image_type)
                    logger.info("✅ OpenCV分析完成")
                except Exception as exc:
                    logger.warning("⚠️ OpenCV分析失败: %s", exc)
                    opencv_result = {"method": "opencv", "error": str(exc)}
            else:
                opencv_result = {"method": "opencv", "status": "unavailable"}

            dl_result: Dict[str, Any]
            if self.dl_analyzer is not None:
                try:
                    dl_result = self.dl_analyzer.analyze(img)
                    logger.info("✅ 深度学习分析完成")
                except Exception as exc:
                    logger.warning("⚠️ 深度学习分析失败: %s", exc)
                    dl_result = {"method": "deep_learning", "error": str(exc)}
            else:
                dl_result = {"method": "deep_learning", "status": "unavailable"}

            if self.fusion_analyzer is not None:
                try:
                    fused_result = self.fusion_analyzer.fuse(opencv_result, dl_result)
                    fused_result["opencv_result"] = opencv_result
                    fused_result["dl_result"] = dl_result
                    return fused_result
                except Exception as exc:
                    logger.warning("⚠️ 决策融合失败，回退到 OpenCV: %s", exc)

            fallback = dict(opencv_result)
            fallback["opencv_result"] = opencv_result
            fallback["dl_result"] = dl_result
            return fallback
        except Exception as exc:
            logger.error("❌ 混合方案分析失败: %s", exc, exc_info=True)
            raise

    async def _hybrid_ai_analysis(
        self,
        img: Image.Image,
        img_path: Path,
        image_type: str,
    ) -> Dict[str, Any]:
        structured_result = await self._fusion_analysis(img, image_type)

        ai_result = await self.qwen_image_service.analyze_image(
            image_path=str(img_path),
            image_type=image_type,
            structured_result=structured_result,
        )

        result = deepcopy(structured_result)
        result["method"] = "hybrid_ai"
        result["model_used"] = ai_result.get("model_used")
        result["fewshot_examples_used"] = ai_result.get("fewshot_examples_used", [])
        result["risk_flags"] = []

        if ai_result.get("success"):
            ai_consistency = ai_result.get("consistency_score")
            fallback_consistency = result.get("confidence", 0.0)
            result["summary"] = ai_result.get("summary")
            result["ai_report"] = ai_result.get("markdown_report")
            result["consistency_score"] = (
                ai_consistency
                if isinstance(ai_consistency, (int, float))
                else fallback_consistency
            )
            result["risk_flags"].extend(ai_result.get("risk_flags", []))
            result.setdefault("details", {})
            result["details"]["ai_result"] = {
                "overall_assessment": ai_result.get("overall_assessment"),
                "eye_detected": ai_result.get("eye_detected"),
                "eye_position_description": ai_result.get("eye_position_description"),
                "eye_confidence": ai_result.get("eye_confidence"),
                "eye_evidence": ai_result.get("eye_evidence", []),
                "center_location_hint": ai_result.get("center_location_hint"),
                "intensity_assessment": ai_result.get("intensity_assessment"),
                "organization_assessment": ai_result.get("organization_assessment"),
                "development_stage": ai_result.get("development_stage"),
                "cloud_system_description": ai_result.get("cloud_system_description"),
                "analysis_highlights": ai_result.get("analysis_highlights", []),
                "analysis_limitations": ai_result.get("analysis_limitations", []),
                "fewshot_examples_used": ai_result.get("fewshot_examples_used", []),
            }

            if (
                isinstance(ai_result.get("eye_detected"), bool)
                and result.get("eye")
                and ai_result.get("eye_detected") != result["eye"].get("detected")
            ):
                result["risk_flags"].append("AI 判读与结构化结果在台风眼判断上存在差异")

            if (
                isinstance(result.get("consistency_score"), (int, float))
                and result["consistency_score"] < 0.65
            ):
                result["risk_flags"].append("AI 判读与结构化结果一致性较低，建议人工复核")
        else:
            result["summary"] = "AI 报告生成失败，已返回基础结构化分析结果。"
            result["ai_report"] = (
                "## 图像分析说明\n"
                f"- AI 报告生成失败：{ai_result.get('error', '未知错误')}\n"
                "- 当前结果主要来自本地结构化分析，可作为辅助判读依据。"
            )
            result["consistency_score"] = result.get("confidence", 0.0)
            result["risk_flags"].append("AI 报告生成失败，当前结果主要依赖本地结构化分析")

        if not result["fewshot_examples_used"]:
            result["risk_flags"].append("未加载到 few-shot 标注样例，AI 判读仅使用目标图和结构化结果")

        if self.dl_analyzer is None or not getattr(self.dl_analyzer, "models_loaded", False):
            result["risk_flags"].append("深度学习模型未加载，结构化结果主要依赖 OpenCV 与融合策略")

        return result

    def _attach_image_context(
        self,
        result: Dict[str, Any],
        image: TyphoonImage,
        img: Image.Image,
        image_type: str,
    ) -> Dict[str, Any]:
        details = result.setdefault("details", {})
        details["image_metadata"] = {
            "filename": image.filename,
            "image_type": image_type,
            "stored_image_type": image.image_type,
            "format": image.format or (img.format.lower() if img.format else None),
            "width": image.width or img.width,
            "height": image.height or img.height,
            "file_size": image.file_size,
            "mode": img.mode,
            "bands": list(img.getbands()),
            "upload_time": image.upload_time.isoformat() if image.upload_time else None,
        }
        details["visual_metrics"] = self._build_visual_metrics(img)

        if result.get("opencv_result") is not None:
            details.setdefault("opencv_result", result.get("opencv_result"))
        if result.get("dl_result") is not None:
            details.setdefault("dl_result", result.get("dl_result"))
        if result.get("components") is not None:
            details.setdefault("components", result.get("components"))

        return result

    def _build_visual_metrics(self, img: Image.Image) -> Dict[str, Any]:
        img_array = np.array(img)
        return {
            "brightness": float(np.mean(img_array)),
            "contrast": float(np.std(img_array)),
            "sharpness": self._calculate_sharpness(img_array),
            "texture": self._calculate_texture(img_array),
            "cloud_coverage": self._estimate_cloud_coverage(img_array),
            "min_intensity": int(np.min(img_array)),
            "max_intensity": int(np.max(img_array)),
            "dynamic_range": int(np.max(img_array) - np.min(img_array)),
        }

    async def _basic_analysis(self, img: Image.Image) -> Dict[str, Any]:
        img_array = np.array(img)
        return {
            "type": "basic",
            "method": "basic",
            "dimensions": {
                "width": img.width,
                "height": img.height,
                "channels": len(img.getbands()),
            },
            "statistics": {
                "mean": float(np.mean(img_array)),
                "std": float(np.std(img_array)),
                "min": int(np.min(img_array)),
                "max": int(np.max(img_array)),
            },
            "color_info": {
                "mode": img.mode,
                "bands": img.getbands(),
            },
            "confidence": 1.0,
        }

    async def _advanced_analysis(self, img: Image.Image) -> Dict[str, Any]:
        img_array = np.array(img)
        return {
            "type": "advanced",
            "method": "advanced",
            "features": {
                "brightness": float(np.mean(img_array)),
                "contrast": float(np.std(img_array)),
                "sharpness": self._calculate_sharpness(img_array),
                "texture": self._calculate_texture(img_array),
            },
            "cloud_coverage": self._estimate_cloud_coverage(img_array),
            "intensity_distribution": self._analyze_intensity_distribution(img_array),
            "confidence": 0.85,
        }

    def _calculate_sharpness(self, img_array: np.ndarray) -> float:
        gray = np.mean(img_array, axis=2) if len(img_array.shape) == 3 else img_array
        return float(np.std(gray))

    def _calculate_texture(self, img_array: np.ndarray) -> float:
        gray = np.mean(img_array, axis=2) if len(img_array.shape) == 3 else img_array
        return float(np.std(np.diff(gray, axis=0)) + np.std(np.diff(gray, axis=1)))

    def _estimate_cloud_coverage(self, img_array: np.ndarray) -> float:
        brightness = np.mean(img_array, axis=2) if len(img_array.shape) == 3 else img_array
        cloud_pixels = np.sum(brightness > 128)
        total_pixels = brightness.size
        return float(cloud_pixels / total_pixels)

    def _analyze_intensity_distribution(self, img_array: np.ndarray) -> Dict[str, Any]:
        intensity = np.mean(img_array, axis=2) if len(img_array.shape) == 3 else img_array
        hist, bins = np.histogram(intensity, bins=10)
        return {
            "histogram": hist.tolist(),
            "bins": bins.tolist(),
            "peak_intensity": float(bins[np.argmax(hist)]),
        }

    async def delete_image(self, image_id: int) -> bool:
        try:
            image = await self.get_image(image_id)
            if not image:
                return False

            result_query = select(ImageAnalysisResult).where(ImageAnalysisResult.image_id == image_id)
            result_rows = await self.db.execute(result_query)
            for analysis_result in result_rows.scalars().all():
                await self.db.delete(analysis_result)

            if image.file_path:
                file_path = Path(image.file_path)
                if file_path.exists():
                    file_path.unlink()

            await self.db.delete(image)
            await self.db.commit()
            logger.info("✅ 图像删除成功: ID=%s", image_id)
            return True
        except Exception as exc:
            logger.error("❌ 图像删除失败: %s", exc, exc_info=True)
            await self.db.rollback()
            return False
