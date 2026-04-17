"""
图像分析结果数据库模型
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ImageAnalysisResult(Base):
    """图像分析结果表"""

    __tablename__ = "image_analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(
        Integer,
        ForeignKey("typhoon_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联图像ID",
    )
    analysis_type = Column(
        String(50),
        nullable=False,
        comment="分析类型：hybrid_ai/fusion/opencv/basic/advanced",
    )
    status = Column(
        String(20),
        default="pending",
        comment="分析状态：pending/processing/completed/failed",
    )
    method = Column(String(50), nullable=True, comment="实际分析方法")
    result_data = Column(Text, nullable=True, comment="结构化结果JSON")
    confidence = Column(Float, nullable=True, comment="综合置信度")
    summary = Column(Text, nullable=True, comment="AI摘要")
    ai_report = Column(Text, nullable=True, comment="AI分析报告Markdown")
    consistency_score = Column(Float, nullable=True, comment="一致性评分")
    risk_flags = Column(Text, nullable=True, comment="风险提示JSON")
    fewshot_examples = Column(Text, nullable=True, comment="使用的few-shot样例JSON")
    ai_model = Column(String(100), nullable=True, comment="使用的视觉模型")
    processing_time = Column(Float, nullable=True, comment="处理耗时（秒）")
    error_message = Column(Text, nullable=True, comment="错误信息")
    analyzed_at = Column(DateTime, default=datetime.now, comment="分析时间")

    image = relationship("TyphoonImage", backref="analysis_results")

    def __repr__(self):
        return (
            f"<ImageAnalysisResult(id={self.id}, image_id={self.image_id}, "
            f"analysis_type={self.analysis_type}, status={self.status})>"
        )
