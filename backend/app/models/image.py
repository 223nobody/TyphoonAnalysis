"""
图像分析相关数据库模型
"""
from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, Float
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
    
    def __repr__(self):
        return f"<TyphoonImage(id={self.id}, filename={self.filename}, type={self.image_type})>"
