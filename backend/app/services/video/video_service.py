"""
视频分析服务
处理视频上传、存储和分析的完整流程 - 精简字段设计
"""
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.video import VideoAnalysisResult
from app.services.ai.qwen_video_service import qwen_video_service as video_ai_service
from app.core.config import settings

logger = logging.getLogger(__name__)

# 视频存储目录（使用绝对路径）
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
VIDEO_DIR = BASE_DIR / settings.DATA_DIR / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"视频存储目录: {VIDEO_DIR}")


class VideoService:
    """视频服务类 - 精简字段设计"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload_and_analyze(
        self,
        filename: str,
        file_data: bytes,
        file_type: str,
        analysis_type: str = "comprehensive",
        extract_frames: bool = True,
        frame_interval: int = 5
    ) -> Dict[str, Any]:
        """
        上传视频并立即分析

        Args:
            filename: 原始文件名
            file_data: 文件数据
            file_type: 文件类型
            analysis_type: 分析类型
            extract_frames: 是否提取帧
            frame_interval: 帧提取间隔

        Returns:
            分析结果
        """
        start_time = datetime.now()
        file_path = None

        try:
            # 1. 保存文件到磁盘
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{filename}"
            file_path = VIDEO_DIR / unique_filename

            with open(file_path, 'wb') as f:
                f.write(file_data)

            logger.info(f"视频文件已保存: {file_path}, 大小: {len(file_data)} bytes")

            # 2. 创建分析记录
            analysis_result = VideoAnalysisResult(
                filename=unique_filename,
                analysis_type=analysis_type,
                status="processing",
                created_at=datetime.now()
            )
            self.db.add(analysis_result)
            await self.db.commit()
            await self.db.refresh(analysis_result)

            logger.info(f"分析记录已创建: analysis_id={analysis_result.id}")

            # 3. 调用AI服务分析视频
            logger.info(f"开始AI分析: {file_path}")
            async with video_ai_service as service:
                ai_result = await service.analyze_video(
                    video_path=str(file_path),
                    analysis_type=analysis_type,
                    extract_frames=extract_frames,
                    frame_interval=frame_interval
                )

            logger.info(f"AI分析结果: success={ai_result.get('success')}")

            # 4. 更新分析记录
            if not ai_result.get("success"):
                analysis_result.status = "failed"
                analysis_result.error_message = ai_result.get("error", "未知错误")
                analysis_result.processing_time = (datetime.now() - start_time).total_seconds()
                await self.db.commit()

                return {
                    "success": False,
                    "error": ai_result.get("error", "分析失败"),
                    "analysis_id": analysis_result.id
                }

            # 分析成功，更新记录
            ai_analysis = ai_result.get("ai_analysis", {})
            analysis_result.status = "completed"
            analysis_result.ai_analysis = ai_analysis
            analysis_result.frame_count = ai_result.get("frame_count", 0)
            analysis_result.processing_time = (datetime.now() - start_time).total_seconds()
            await self.db.commit()

            return {
                "success": True,
                "analysis_id": analysis_result.id,
                "analysis_type": analysis_type,
                "status": "completed",
                "frame_count": analysis_result.frame_count,
                "ai_analysis": ai_analysis,
                "processing_time": analysis_result.processing_time
            }

        except Exception as e:
            logger.error(f"上传并分析视频失败: {e}", exc_info=True)
            await self.db.rollback()

            # 清理已保存的文件
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"已清理文件: {file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"清理文件失败: {cleanup_error}")

            raise

    async def get_analysis(self, analysis_id: int) -> Optional[VideoAnalysisResult]:
        """
        获取分析记录

        Args:
            analysis_id: 分析记录ID

        Returns:
            分析记录对象
        """
        result = await self.db.execute(
            select(VideoAnalysisResult).where(VideoAnalysisResult.id == analysis_id)
        )
        return result.scalar_one_or_none()

    async def get_analysis_status(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """
        获取分析状态

        Args:
            analysis_id: 分析记录ID

        Returns:
            分析状态
        """
        result = await self.db.execute(
            select(VideoAnalysisResult).where(VideoAnalysisResult.id == analysis_id)
        )
        analysis = result.scalar_one_or_none()

        if not analysis:
            return None

        return {
            "analysis_id": analysis.id,
            "filename": analysis.filename,
            "status": analysis.status,
            "analysis_type": analysis.analysis_type,
            "result": {
                "ai_analysis": analysis.ai_analysis,
                "frame_count": analysis.frame_count
            } if analysis.status == "completed" else None,
            "error": analysis.error_message if analysis.status == "failed" else None,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
            "processing_time": analysis.processing_time
        }

    async def list_analyses(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取分析记录列表

        Args:
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            分析记录列表和总数
        """
        # 获取总数
        count_result = await self.db.execute(
            select(func.count(VideoAnalysisResult.id))
        )
        total = count_result.scalar()

        # 获取列表
        result = await self.db.execute(
            select(VideoAnalysisResult)
            .order_by(VideoAnalysisResult.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        analyses = result.scalars().all()

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "analyses": [
                {
                    "id": a.id,
                    "filename": a.filename,
                    "analysis_type": a.analysis_type,
                    "status": a.status,
                    "frame_count": a.frame_count,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "processing_time": a.processing_time
                }
                for a in analyses
            ]
        }

    async def delete_analysis(self, analysis_id: int) -> bool:
        """
        删除分析记录及其关联文件

        Args:
            analysis_id: 分析记录ID

        Returns:
            是否成功
        """
        try:
            analysis = await self.get_analysis(analysis_id)
            if not analysis:
                return False

            # 删除文件（根据filename拼接路径）
            file_path = VIDEO_DIR / analysis.filename
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"已删除文件: {file_path}")
                except Exception as e:
                    logger.warning(f"删除文件失败: {e}")

            # 删除数据库记录
            await self.db.delete(analysis)
            await self.db.commit()

            logger.info(f"分析记录已删除: analysis_id={analysis_id}")
            return True

        except Exception as e:
            logger.error(f"删除分析记录失败: {e}", exc_info=True)
            await self.db.rollback()
            return False
