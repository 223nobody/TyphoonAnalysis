"""
Pydantic模式 - 台风数据
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TyphoonBase(BaseModel):
    """台风基础模式"""
    typhoon_id: str = Field(..., description="台风编号")
    typhoon_name: str = Field(..., description="台风名称")
    typhoon_name_cn: Optional[str] = None
    year: Optional[int] = None
    status: Optional[int] = 0  # 0=stop, 1=active


class TyphoonCreate(TyphoonBase):
    """创建台风"""
    pass


class TyphoonResponse(TyphoonBase):
    """台风响应"""
    id: int

    class Config:
        from_attributes = True


class TyphoonPathBase(BaseModel):
    """台风路径基础模式"""
    typhoon_id: str
    timestamp: datetime
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    center_pressure: Optional[float] = None
    max_wind_speed: Optional[float] = None
    moving_speed: Optional[float] = None
    moving_direction: Optional[str] = None
    intensity: Optional[str] = None


class TyphoonPathCreate(TyphoonPathBase):
    """创建台风路径"""
    pass


class TyphoonPathResponse(TyphoonPathBase):
    """台风路径响应"""
    id: int

    class Config:
        from_attributes = True


class PredictionBase(BaseModel):
    """预测基础模式"""
    typhoon_id: str
    typhoon_name: Optional[str] = None
    prediction_type: str = "path"
    forecast_hours: int = 24
    forecast_time: Optional[datetime] = None
    predicted_latitude: Optional[float] = None
    predicted_longitude: Optional[float] = None
    predicted_pressure: Optional[float] = None
    predicted_wind_speed: Optional[float] = None
    prediction_model: Optional[str] = None
    confidence: Optional[float] = None


class PredictionCreate(PredictionBase):
    """创建预测"""
    input_data: Optional[dict] = None


class PredictionResponse(PredictionBase):
    """预测响应"""
    id: int
    input_data: Optional[dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ImageAnalysisBase(BaseModel):
    """图像分析基础模式"""
    typhoon_id: Optional[str] = None
    typhoon_name: Optional[str] = None
    image_url: Optional[str] = None
    image_path: Optional[str] = None


class ImageAnalysisCreate(ImageAnalysisBase):
    """创建图像分析"""
    pass


class ImageAnalysisResponse(ImageAnalysisBase):
    """图像分析响应"""
    id: int
    analysis_result: Optional[str] = None
    extracted_data: Optional[dict] = None
    model_used: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ReportBase(BaseModel):
    """报告基础模式"""
    typhoon_id: str
    typhoon_name: Optional[str] = None
    report_type: str = "analysis"


class ReportCreate(ReportBase):
    """创建报告"""
    report_content: str
    related_prediction_id: Optional[int] = None
    related_analysis_id: Optional[int] = None


class ReportResponse(ReportBase):
    """报告响应"""
    id: int
    report_content: str
    related_prediction_id: Optional[int] = None
    related_analysis_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class TyphoonListResponse(BaseModel):
    """台风列表响应"""
    total: int
    items: List[TyphoonResponse]


class TyphoonPathListResponse(BaseModel):
    """台风路径列表响应"""
    total: int
    items: List[TyphoonPathResponse]

