"""
图像分析API路由
提供图像上传、分析、查询等功能

重构说明：
- 支持新的分析类型：basic/advanced/opencv/fusion
- 支持图像类型参数：infrared/visible
- 返回详细的分析结果（台风中心、强度、台风眼、螺旋结构等）
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from app.core.database import get_db
from app.models.image import TyphoonImage, ImageAnalysisResult
from app.services.image.image_service import ImageAnalysisService
from app.services.crawler.image_crawler import (
    SatelliteCrawler,
    NWPCrawler,
    EnvironmentCrawler
)

router = APIRouter(prefix="/api/images", tags=["图像分析"])
logger = logging.getLogger(__name__)


# ========== 请求/响应模型 ==========

class ImageAnalysisRequest(BaseModel):
    """图像分析请求模型"""
    analysis_type: str = Field(
        default="fusion",
        description="分析类型：basic/advanced/opencv/fusion"
    )
    image_type: str = Field(
        default="infrared",
        description="图像类型：infrared(红外图)/visible(可见光图)"
    )


class CenterResult(BaseModel):
    """台风中心结果"""
    pixel_x: Optional[float] = Field(None, description="中心X坐标（像素）")
    pixel_y: Optional[float] = Field(None, description="中心Y坐标（像素）")
    confidence: float = Field(0.0, description="置信度")
    method: Optional[str] = Field(None, description="检测方法")


class IntensityResult(BaseModel):
    """强度评估结果"""
    level: str = Field(..., description="强度等级")
    confidence: float = Field(0.0, description="置信度")
    method: Optional[str] = Field(None, description="评估方法")


class EyeResult(BaseModel):
    """台风眼检测结果"""
    detected: bool = Field(False, description="是否检测到台风眼")
    diameter_km: Optional[float] = Field(None, description="台风眼直径（公里）")
    confidence: float = Field(0.0, description="置信度")


class StructureResult(BaseModel):
    """螺旋结构分析结果"""
    spiral_score: float = Field(0.0, description="螺旋结构评分（0-1）")
    organization: Optional[str] = Field(None, description="组织程度")


class ImageAnalysisResponse(BaseModel):
    """图像分析响应模型"""
    success: bool = Field(True, description="是否成功")
    image_id: int = Field(..., description="图像ID")
    analysis_type: str = Field(..., description="分析类型")
    method: str = Field(..., description="分析方法")
    center: Optional[CenterResult] = Field(None, description="台风中心")
    intensity: Optional[IntensityResult] = Field(None, description="强度评估")
    eye: Optional[EyeResult] = Field(None, description="台风眼")
    structure: Optional[StructureResult] = Field(None, description="螺旋结构")
    confidence: float = Field(0.0, description="综合置信度")
    processing_time: float = Field(0.0, description="处理时间（秒）")
    analyzed_at: str = Field(..., description="分析时间")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    typhoon_id: Optional[str] = None,
    image_type: str = "satellite",
    db: AsyncSession = Depends(get_db)
):
    """
    上传台风相关图像

    Args:
        file: 上传的图像文件
        typhoon_id: 台风ID（可选）
        image_type: 图像类型（satellite/nwp/environment/track）
        db: 数据库会话

    Returns:
        上传结果和图像ID
    """
    try:
        # 验证文件类型
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="只支持图像文件")

        # 读取文件内容
        content = await file.read()

        # 保存到数据库
        service = ImageAnalysisService(db)
        image_record = await service.save_image(
            filename=file.filename,
            content=content,
            typhoon_id=typhoon_id,
            image_type=image_type
        )

        return {
            "success": True,
            "message": "图像上传成功",
            "image_id": image_record.id,
            "filename": file.filename,
            "size": len(content),
            "upload_time": image_record.upload_time.isoformat()
        }

    except Exception as e:
        logger.error(f"图像上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"图像上传失败: {str(e)}")


@router.post("/analyze/{image_id}", response_model=ImageAnalysisResponse)
async def analyze_image(
    image_id: int,
    analysis_type: str = Query(
        default="fusion",
        description="分析类型：basic/advanced/opencv/fusion"
    ),
    image_type: str = Query(
        default="infrared",
        description="图像类型：infrared(红外图)/visible(可见光图)"
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    分析指定图像（重构版本）

    Args:
        image_id: 图像ID
        analysis_type: 分析类型
            - basic: 基础统计分析
            - advanced: 高级特征提取
            - opencv: OpenCV传统方法
            - fusion: 混合方案（推荐）⭐
        image_type: 图像类型
            - infrared: 红外卫星云图
            - visible: 可见光卫星云图
        db: 数据库会话

    Returns:
        详细的分析结果
    """
    try:
        service = ImageAnalysisService(db)

        # 获取图像记录
        image = await service.get_image(image_id)
        if not image:
            raise HTTPException(status_code=404, detail="图像不存在")

        # 执行分析
        result = await service.analyze_image(image, analysis_type, image_type)

        # 构建响应
        response = {
            "success": True,
            "image_id": image_id,
            "analysis_type": analysis_type,
            "method": result.get("method", analysis_type),
            "confidence": result.get("confidence", 0.0),
            "processing_time": result.get("processing_time", 0.0),
            "analyzed_at": datetime.now().isoformat()
        }

        # 添加台风中心信息
        if "center" in result:
            center_data = result["center"]
            response["center"] = {
                "pixel_x": center_data.get("pixel_x"),
                "pixel_y": center_data.get("pixel_y"),
                "confidence": center_data.get("confidence", 0.0),
                "method": center_data.get("method")
            }

        # 添加强度信息
        if "intensity" in result:
            intensity_data = result["intensity"]
            response["intensity"] = {
                "level": intensity_data.get("level", "未知"),
                "confidence": intensity_data.get("confidence", 0.0),
                "method": intensity_data.get("method")
            }

        # 添加台风眼信息
        if "eye" in result:
            eye_data = result["eye"]
            response["eye"] = {
                "detected": eye_data.get("detected", False),
                "diameter_km": eye_data.get("diameter_km"),
                "confidence": eye_data.get("confidence", 0.0)
            }

        # 添加螺旋结构信息
        if "structure" in result:
            structure_data = result["structure"]
            response["structure"] = {
                "spiral_score": structure_data.get("spiral_score", 0.0),
                "organization": structure_data.get("organization")
            }

        # 添加详细信息（用于调试和高级用户）
        response["details"] = {
            "components": result.get("components", {}),
            "opencv_result": result.get("opencv_result"),
            "dl_result": result.get("dl_result")
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图像分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"图像分析失败: {str(e)}")


@router.get("/typhoon/{typhoon_id}")
async def get_typhoon_images(
    typhoon_id: str,
    image_type: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定台风的图像列表
    
    Args:
        typhoon_id: 台风ID
        image_type: 图像类型筛选（可选）
        limit: 返回数量限制
        db: 数据库会话
    
    Returns:
        图像列表
    """
    try:
        service = ImageAnalysisService(db)
        images = await service.get_typhoon_images(
            typhoon_id=typhoon_id,
            image_type=image_type,
            limit=limit
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
                    "upload_time": img.upload_time.isoformat(),
                    "file_size": img.file_size,
                    "has_analysis": img.analysis_result is not None
                }
                for img in images
            ]
        }
    
    except Exception as e:
        logger.error(f"获取台风图像失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取图像失败: {str(e)}")


@router.post("/crawl/satellite/{typhoon_id}")
async def crawl_satellite_images(
    typhoon_id: str,
    source: str = "fengyun",
    db: AsyncSession = Depends(get_db)
):
    """
    爬取指定台风的卫星云图
    
    Args:
        typhoon_id: 台风ID
        source: 数据源（himawari/fengyun/goes）
        db: 数据库会话
    
    Returns:
        爬取结果
    """
    try:
        async with SatelliteCrawler() as crawler:
            if source == "himawari":
                images = await crawler.crawl_himawari(typhoon_id)
            elif source == "fengyun":
                images = await crawler.crawl_fengyun(typhoon_id)
            else:
                raise HTTPException(status_code=400, detail=f"不支持的数据源: {source}")
        
        # 保存到数据库
        service = ImageAnalysisService(db)
        saved_count = 0
        for image_path in images:
            try:
                with open(image_path, "rb") as f:
                    content = f.read()
                await service.save_image(
                    filename=image_path.split("/")[-1],
                    content=content,
                    typhoon_id=typhoon_id,
                    image_type="satellite",
                    source=source
                )
                saved_count += 1
            except Exception as e:
                logger.error(f"保存图像失败: {image_path} - {e}")
        
        return {
            "success": True,
            "typhoon_id": typhoon_id,
            "source": source,
            "crawled": len(images),
            "saved": saved_count,
            "message": f"成功爬取并保存 {saved_count} 张卫星云图"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"爬取卫星图像失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"爬取失败: {str(e)}")


@router.get("/analysis/history/{image_id}")
async def get_analysis_history(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取图像的分析历史
    
    Args:
        image_id: 图像ID
        db: 数据库会话
    
    Returns:
        分析历史记录
    """
    try:
        service = ImageAnalysisService(db)
        history = await service.get_analysis_history(image_id)
        
        return {
            "success": True,
            "image_id": image_id,
            "count": len(history),
            "history": [
                {
                    "id": record.id,
                    "analysis_type": record.analysis_type,
                    "result": record.result,
                    "analyzed_at": record.analyzed_at.isoformat()
                }
                for record in history
            ]
        }
    
    except Exception as e:
        logger.error(f"获取分析历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.delete("/{image_id}")
async def delete_image(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除指定图像
    
    Args:
        image_id: 图像ID
        db: 数据库会话
    
    Returns:
        删除结果
    """
    try:
        service = ImageAnalysisService(db)
        success = await service.delete_image(image_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="图像不存在")
        
        return {
            "success": True,
            "message": "图像删除成功",
            "image_id": image_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除图像失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

