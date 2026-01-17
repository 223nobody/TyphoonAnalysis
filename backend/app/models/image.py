"""
图像分析相关数据库模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, LargeBinary, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class TyphoonImage(Base):
    """台风图像表"""
    __tablename__ = "typhoon_images"

    id = Column(Integer, primary_key=True, index=True)
    typhoon_id = Column(String(20), index=True, nullable=True, comment="台风ID")
    filename = Column(String(255), nullable=False, comment="文件名")
    image_type = Column(String(50), nullable=False, comment="图像类型：satellite/nwp/environment/track")
    source = Column(String(50), nullable=True, comment="数据源：himawari/fengyun/gfs等")
    file_path = Column(String(500), nullable=True, comment="文件存储路径")
    file_size = Column(Integer, nullable=True, comment="文件大小（字节）")
    image_data = Column(LargeBinary, nullable=True, comment="图像二进制数据（可选）")
    
    # 图像元数据
    width = Column(Integer, nullable=True, comment="图像宽度")
    height = Column(Integer, nullable=True, comment="图像高度")
    format = Column(String(20), nullable=True, comment="图像格式：jpg/png/gif")
    
    # 时间信息
    capture_time = Column(DateTime, nullable=True, comment="图像拍摄时间")
    upload_time = Column(DateTime, default=datetime.now, comment="上传时间")
    
    # 地理信息
    latitude = Column(Float, nullable=True, comment="中心纬度")
    longitude = Column(Float, nullable=True, comment="中心经度")
    coverage_area = Column(String(100), nullable=True, comment="覆盖区域")
    
    # 关联关系
    analysis_results = relationship("ImageAnalysisResult", back_populates="image", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TyphoonImage(id={self.id}, filename={self.filename}, type={self.image_type})>"


class ImageAnalysisResult(Base):
    """图像分析结果表"""
    __tablename__ = "image_analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("typhoon_images.id"), nullable=False, comment="图像ID")
    analysis_type = Column(String(50), nullable=False, comment="分析类型：basic/advanced/ai")
    
    # 分析结果
    result_data = Column(Text, nullable=True, comment="分析结果JSON数据")
    confidence = Column(Float, nullable=True, comment="置信度（0-1）")
    
    # 特征提取结果
    features = Column(Text, nullable=True, comment="提取的特征JSON")
    
    # AI分析结果
    ai_model = Column(String(100), nullable=True, comment="使用的AI模型")
    predictions = Column(Text, nullable=True, comment="AI预测结果JSON")
    
    # 时间信息
    analyzed_at = Column(DateTime, default=datetime.now, comment="分析时间")
    processing_time = Column(Float, nullable=True, comment="处理耗时（秒）")
    
    # 关联关系
    image = relationship("TyphoonImage", back_populates="analysis_results")
    
    def __repr__(self):
        return f"<ImageAnalysisResult(id={self.id}, image_id={self.image_id}, type={self.analysis_type})>"


class ImageCrawlLog(Base):
    """图像爬取日志表"""
    __tablename__ = "image_crawl_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(50), nullable=False, comment="任务类型：satellite/nwp/environment")
    source = Column(String(50), nullable=False, comment="数据源")
    typhoon_id = Column(String(20), nullable=True, comment="台风ID")
    
    # 爬取结果
    status = Column(String(20), nullable=False, comment="状态：success/failed/partial")
    total_count = Column(Integer, default=0, comment="总数")
    success_count = Column(Integer, default=0, comment="成功数")
    failed_count = Column(Integer, default=0, comment="失败数")
    
    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    # 时间信息
    start_time = Column(DateTime, default=datetime.now, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")
    duration = Column(Float, nullable=True, comment="耗时（秒）")
    
    def __repr__(self):
        return f"<ImageCrawlLog(id={self.id}, type={self.task_type}, status={self.status})>"

