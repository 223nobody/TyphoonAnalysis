"""
数据库模型 - 台风数据
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class Typhoon(Base):
    """台风基本信息表"""
    __tablename__ = "typhoons"

    id = Column(Integer, primary_key=True, index=True)
    typhoon_id = Column(String(50), unique=True, index=True, nullable=False, comment="台风编号")
    typhoon_name = Column(String(100), nullable=False, comment="台风名称（英文）")
    typhoon_name_cn = Column(String(100), comment="台风名称（中文）")
    year = Column(Integer, index=True, comment="年份")
    status = Column(Integer, default=0, comment="状态：0=stop, 1=active")


class TyphoonPath(Base):
    """台风路径数据表"""
    __tablename__ = "typhoon_paths"

    id = Column(Integer, primary_key=True, index=True)
    typhoon_id = Column(String(50), index=True, nullable=False, comment="台风编号")
    timestamp = Column(DateTime, nullable=False, comment="时间戳")
    latitude = Column(Float, nullable=False, comment="纬度")
    longitude = Column(Float, nullable=False, comment="经度")
    center_pressure = Column(Float, comment="中心气压(hPa)")
    max_wind_speed = Column(Float, comment="最大风速(m/s)")
    moving_speed = Column(Float, comment="移动速度(km/h)")
    moving_direction = Column(String(50), comment="移动方向")
    intensity = Column(String(50), comment="强度等级")


class Prediction(Base):
    """预测记录表"""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    typhoon_id = Column(String(50), index=True, nullable=False)
    typhoon_name = Column(String(100))
    prediction_type = Column(String(50), comment="预测类型：path/intensity")
    forecast_hours = Column(Integer, comment="预报时效(小时)")
    forecast_time = Column(DateTime, comment="预报时间")
    predicted_latitude = Column(Float)
    predicted_longitude = Column(Float)
    predicted_pressure = Column(Float)
    predicted_wind_speed = Column(Float)
    prediction_model = Column(String(100), comment="使用的模型")
    confidence = Column(Float, comment="置信度")
    input_data = Column(JSON, comment="输入数据")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ImageAnalysis(Base):
    """图像分析记录表"""
    __tablename__ = "image_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    typhoon_id = Column(String(50), index=True)
    typhoon_name = Column(String(100))
    image_url = Column(String(500))
    image_path = Column(String(500))
    analysis_result = Column(Text, comment="分析结果文本")
    extracted_data = Column(JSON, comment="提取的结构化数据")
    model_used = Column(String(100), comment="使用的AI模型")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Report(Base):
    """报告记录表"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    typhoon_id = Column(String(50), index=True, nullable=False)
    typhoon_name = Column(String(100))
    report_type = Column(String(50), comment="报告类型：comprehensive/prediction/impact")
    report_content = Column(Text, comment="报告内容")
    model_used = Column(String(100), comment="使用的AI模型")
    related_prediction_id = Column(Integer, comment="关联的预测ID")
    related_analysis_id = Column(Integer, comment="关联的分析ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CrawlerLog(Base):
    """爬虫日志表"""
    __tablename__ = "crawler_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(50), comment="任务类型")
    status = Column(String(50), comment="状态：success/failed")
    message = Column(Text, comment="日志消息")
    data_count = Column(Integer, comment="爬取数据条数")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

