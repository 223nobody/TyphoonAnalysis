"""
视频分析API路由 - 合并表设计
提供视频上传并分析、查询等功能
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
import logging

from app.core.database import get_db
from app.models.video import VideoAnalysisResult
from app.services.video.video_service import VideoService

router = APIRouter(prefix="/video-analysis", tags=["视频分析"])
logger = logging.getLogger(__name__)


# ========== 请求/响应模型 ==========

class VideoAnalysisResponse:
    """视频分析响应模型"""
    success: bool
    analysis_id: int
    analysis_type: str
    status: str
    frame_count: int
    ai_analysis: Optional[Dict[str, Any]]
    processing_time: Optional[float]
    error: Optional[str]


class AnalysisStatusResponse:
    """分析状态响应模型"""
    analysis_id: int
    filename: str
    status: str
    analysis_type: str
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    created_at: Optional[str]
    processing_time: Optional[float]


# ========== API端点 ==========

@router.post("/analyze")
async def analyze_video(
    file: UploadFile = File(...),
    analysis_type: str = Form("comprehensive"),
    extract_frames: bool = Form(True),
    frame_interval: int = Form(5),
    db: AsyncSession = Depends(get_db)
):
    """
    上传视频并立即分析（合并上传和分析流程）

    Args:
        file: 视频文件
        analysis_type: 分析类型（comprehensive/tracking/intensity/structure）
        extract_frames: 是否提取关键帧
        frame_interval: 帧提取间隔（秒）
        db: 数据库会话

    Returns:
        分析结果
    """
    try:
        # 验证文件类型
        allowed_types = [
            'video/mp4', 'video/avi', 'video/x-msvideo', 'video/quicktime',
            'video/mov', 'video/x-matroska', 'video/webm', 'video/x-flv', 'video/x-ms-wmv'
        ]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file.content_type}"
            )

        # 验证文件大小（最大500MB）
        max_size = 500 * 1024 * 1024  # 500MB
        file_data = await file.read()
        if len(file_data) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制（最大500MB）"
            )

        # 上传并分析视频
        service = VideoService(db)
        result = await service.upload_and_analyze(
            filename=file.filename,
            file_data=file_data,
            file_type=file.content_type,
            analysis_type=analysis_type,
            extract_frames=extract_frames,
            frame_interval=frame_interval
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "分析失败")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"视频分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/status/{analysis_id}")
async def get_analysis_status(
    analysis_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取分析状态

    Args:
        analysis_id: 分析记录ID
        db: 数据库会话

    Returns:
        分析状态和结果
    """
    try:
        service = VideoService(db)
        status = await service.get_analysis_status(analysis_id)

        if not status:
            raise HTTPException(status_code=404, detail="分析记录不存在")

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分析状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/")
async def list_analyses(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    获取分析记录列表

    Args:
        limit: 返回数量限制
        offset: 偏移量
        db: 数据库会话

    Returns:
        分析记录列表
    """
    try:
        service = VideoService(db)
        result = await service.list_analyses(limit=limit, offset=offset)

        return {
            "success": True,
            **result
        }

    except Exception as e:
        logger.error(f"获取分析列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除分析记录及其关联文件

    Args:
        analysis_id: 分析记录ID
        db: 数据库会话

    Returns:
        删除结果
    """
    try:
        service = VideoService(db)
        success = await service.delete_analysis(analysis_id)

        if not success:
            raise HTTPException(status_code=404, detail="分析记录不存在")

        return {
            "success": True,
            "message": "分析记录删除成功",
            "analysis_id": analysis_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除分析记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
