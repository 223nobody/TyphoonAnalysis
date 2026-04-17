"""
图像分析 API 路由
提供图像上传、few-shot 混合分析、查询与删除等功能
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.crawler.image_crawler import SatelliteCrawler
from app.services.image.image_service import DuplicateImageError, ImageAnalysisService

router = APIRouter(prefix="/images", tags=["图像分析"])
logger = logging.getLogger(__name__)


class CenterResult(BaseModel):
    pixel_x: Optional[float] = Field(None, description="中心X坐标（像素）")
    pixel_y: Optional[float] = Field(None, description="中心Y坐标（像素）")
    confidence: float = Field(0.0, description="置信度")
    method: Optional[str] = Field(None, description="检测方法")


class IntensityResult(BaseModel):
    level: str = Field(..., description="强度等级")
    confidence: float = Field(0.0, description="置信度")
    method: Optional[str] = Field(None, description="评估方法")


class EyeResult(BaseModel):
    detected: bool = Field(False, description="是否检测到台风眼")
    diameter_km: Optional[float] = Field(None, description="台风眼直径（公里）")
    confidence: float = Field(0.0, description="置信度")


class StructureResult(BaseModel):
    spiral_score: float = Field(0.0, description="螺旋结构评分")
    organization: Optional[str] = Field(None, description="组织程度")


class ImageAnalysisResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    success: bool = Field(True, description="是否成功")
    analysis_id: int = Field(..., description="分析记录ID")
    image_id: int = Field(..., description="图像ID")
    analysis_type: str = Field(..., description="分析类型")
    status: str = Field(..., description="分析状态")
    method: str = Field(..., description="分析方法")
    confidence: float = Field(0.0, description="综合置信度")
    center: Optional[CenterResult] = Field(None, description="台风中心")
    intensity: Optional[IntensityResult] = Field(None, description="强度评估")
    eye: Optional[EyeResult] = Field(None, description="台风眼")
    structure: Optional[StructureResult] = Field(None, description="结构分析")
    summary: Optional[str] = Field(None, description="AI摘要")
    ai_report: Optional[str] = Field(None, description="AI分析报告")
    consistency_score: Optional[float] = Field(None, description="一致性评分")
    risk_flags: List[str] = Field(default_factory=list, description="风险提示")
    fewshot_examples_used: List[str] = Field(
        default_factory=list,
        description="使用的few-shot样例",
    )
    model_used: Optional[str] = Field(None, description="使用的视觉模型")
    processing_time: float = Field(0.0, description="处理时间（秒）")
    analyzed_at: str = Field(..., description="分析时间")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    typhoon_id: Optional[str] = Form(default=None),
    image_type: str = Form(default="satellite"),
    db: AsyncSession = Depends(get_db),
):
    """上传图像文件"""
    try:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="只支持图像文件")

        content = await file.read()
        service = ImageAnalysisService(db)
        image_record = await service.save_image(
            filename=file.filename,
            content=content,
            typhoon_id=typhoon_id,
            image_type=image_type,
        )

        return {
            "success": True,
            "message": "图像上传成功",
            "image_id": image_record.id,
            "filename": image_record.filename,
            "size": len(content),
            "width": image_record.width,
            "height": image_record.height,
            "format": image_record.format,
            "image_type": image_record.image_type,
            "upload_time": image_record.upload_time.isoformat() if image_record.upload_time else None,
        }
    except DuplicateImageError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("图像上传失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"图像上传失败: {str(exc)}")


@router.post("/analyze/{image_id}", response_model=ImageAnalysisResponse)
async def analyze_image(
    image_id: int,
    analysis_type: str = Query(
        default="hybrid_ai",
        description="分析类型：hybrid_ai/fusion/opencv/basic/advanced",
    ),
    image_type: str = Query(
        default="visible",
        description="图像类型：infrared(红外图)/visible(可见光图)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """分析指定图像"""
    try:
        service = ImageAnalysisService(db)
        image = await service.get_image(image_id)
        if not image:
            raise HTTPException(status_code=404, detail="图像不存在")

        result = await service.analyze_image(image, analysis_type, image_type)

        response_details = dict(result.get("details") or {})
        if result.get("components") is not None:
            response_details.setdefault("components", result.get("components"))
        if result.get("opencv_result") is not None:
            response_details.setdefault("opencv_result", result.get("opencv_result"))
        if result.get("dl_result") is not None:
            response_details.setdefault("dl_result", result.get("dl_result"))

        response: Dict[str, Any] = {
            "success": True,
            "analysis_id": result["analysis_id"],
            "image_id": image_id,
            "analysis_type": analysis_type,
            "status": result.get("status", "completed"),
            "method": result.get("method", analysis_type),
            "confidence": result.get("confidence", 0.0),
            "summary": result.get("summary"),
            "ai_report": result.get("ai_report"),
            "consistency_score": result.get("consistency_score"),
            "risk_flags": result.get("risk_flags", []),
            "fewshot_examples_used": result.get("fewshot_examples_used", []),
            "model_used": result.get("model_used"),
            "processing_time": result.get("processing_time", 0.0),
            "analyzed_at": result.get("analyzed_at"),
            "details": response_details or None,
        }

        if "center" in result:
            center_data = result["center"]
            response["center"] = {
                "pixel_x": center_data.get("pixel_x"),
                "pixel_y": center_data.get("pixel_y"),
                "confidence": center_data.get("confidence", 0.0),
                "method": center_data.get("method"),
            }

        if "intensity" in result:
            intensity_data = result["intensity"]
            response["intensity"] = {
                "level": intensity_data.get("level", "未知"),
                "confidence": intensity_data.get("confidence", 0.0),
                "method": intensity_data.get("method"),
            }

        if "eye" in result:
            eye_data = result["eye"]
            response["eye"] = {
                "detected": eye_data.get("detected", False),
                "diameter_km": eye_data.get("diameter_km"),
                "confidence": eye_data.get("confidence", 0.0),
            }

        if "structure" in result:
            structure_data = result["structure"]
            response["structure"] = {
                "spiral_score": structure_data.get("spiral_score", 0.0),
                "organization": structure_data.get("organization"),
            }

        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("图像分析失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"图像分析失败: {str(exc)}")


@router.get("/typhoon/{typhoon_id}")
async def get_typhoon_images(
    typhoon_id: str,
    image_type: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """获取指定台风的图像列表"""
    try:
        service = ImageAnalysisService(db)
        images = await service.get_typhoon_images(
            typhoon_id=typhoon_id,
            image_type=image_type,
            limit=limit,
        )

        return {
            "success": True,
            "typhoon_id": typhoon_id,
            "count": len(images),
            "images": [
                {
                    "id": img.id,
                    "filename": img.filename,
                    "image_type": img.image_type,
                    "upload_time": img.upload_time.isoformat() if img.upload_time else None,
                    "file_size": img.file_size,
                }
                for img in images
            ],
        }
    except Exception as exc:
        logger.error("获取台风图像失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取图像失败: {str(exc)}")


@router.post("/crawl/satellite/{typhoon_id}")
async def crawl_satellite_images(
    typhoon_id: str,
    source: str = "fengyun",
    db: AsyncSession = Depends(get_db),
):
    """爬取指定台风的卫星云图"""
    try:
        async with SatelliteCrawler() as crawler:
            if source == "himawari":
                images = await crawler.crawl_himawari(typhoon_id)
            elif source == "fengyun":
                images = await crawler.crawl_fengyun(typhoon_id)
            else:
                raise HTTPException(status_code=400, detail=f"不支持的数据源: {source}")

        service = ImageAnalysisService(db)
        saved_count = 0
        for image_path in images:
            try:
                with open(image_path, "rb") as file_handle:
                    content = file_handle.read()
                await service.save_image(
                    filename=Path(image_path).name,
                    content=content,
                    typhoon_id=typhoon_id,
                    image_type="satellite",
                    source=source,
                )
                saved_count += 1
            except DuplicateImageError:
                logger.info("跳过重复图像: %s", image_path)
            except Exception as exc:
                logger.error("保存图像失败: %s - %s", image_path, exc)

        return {
            "success": True,
            "typhoon_id": typhoon_id,
            "source": source,
            "crawled": len(images),
            "saved": saved_count,
            "message": f"成功爬取并保存 {saved_count} 张卫星云图",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("爬取卫星图像失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"爬取失败: {str(exc)}")


@router.delete("/{image_id}")
async def delete_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除图像与关联分析结果"""
    try:
        service = ImageAnalysisService(db)
        success = await service.delete_image(image_id)
        if not success:
            raise HTTPException(status_code=404, detail="图像不存在")

        return {
            "success": True,
            "message": "图像删除成功",
            "image_id": image_id,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("删除图像失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(exc)}")
