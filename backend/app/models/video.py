"""
视频分析相关数据库模型
精简设计 - 只保留核心字段
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, JSON
from datetime import datetime

from app.core.database import Base


class VideoAnalysisResult(Base):
    """视频分析结果表"""
    __tablename__ = "video_analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    
    # 视频文件信息（精简）
    filename = Column(String(255), nullable=False, comment="存储的文件名")
    
    # 分析任务信息
    analysis_type = Column(String(50), nullable=False, comment="分析类型：comprehensive/tracking/intensity/structure")
    status = Column(String(20), default="pending", comment="分析状态：pending/processing/completed/failed")
    
    # AI分析结果
    ai_analysis = Column(JSON, nullable=True, comment="AI分析结果JSON")
    frame_count = Column(Integer, default=0, comment="提取的帧数")
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    processing_time = Column(Float, nullable=True, comment="处理耗时（秒）")
    
    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    def __repr__(self):
        return f"<VideoAnalysisResult(id={self.id}, filename={self.filename}, status={self.status})>"
