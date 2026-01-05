"""
报告API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.typhoon import Report, Prediction
from app.schemas.typhoon import ReportCreate, ReportResponse
from app.services.ai.ai_factory import AIServiceFactory
from app.services.ai.qwen_service import qwen_service
from app.services.ai.deepseek_service import deepseek_service

router = APIRouter(prefix="/report", tags=["报告"])


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    typhoon_id: str = Body(..., description="台风编号"),
    typhoon_name: str = Body("", description="台风名称"),
    report_type: str = Body("analysis", description="报告类型"),
    ai_provider: Optional[str] = Body(None, description="AI服务提供商（qwen或deepseek，默认使用配置文件）"),
    include_prediction: bool = Body(True, description="是否包含预测数据"),
    include_analysis: bool = Body(True, description="是否包含分析数据"),
    db: AsyncSession = Depends(get_db)
):
    """
    生成台风分析报告

    支持使用通义千问或DeepSeek模型生成专业的中文台风分析简报

    Args:
        typhoon_id: 台风编号
        typhoon_name: 台风名称
        report_type: 报告类型
        ai_provider: AI服务提供商（qwen或deepseek，默认使用配置文件中的设置）
        include_prediction: 是否包含预测数据
        include_analysis: 是否包含分析数据

    Returns:
        ReportResponse: 生成的报告
    """
    # 获取预测数据
    prediction_data = {}
    prediction_id = None

    if include_prediction:
        query = select(Prediction).where(
            Prediction.typhoon_id == typhoon_id
        ).order_by(desc(Prediction.created_at)).limit(10)

        result = await db.execute(query)
        predictions = result.scalars().all()

        if predictions:
            prediction_id = predictions[0].id
            prediction_data = {
                "predictions": [
                    {
                        "forecast_time": str(p.forecast_time),
                        "latitude": p.predicted_latitude,
                        "longitude": p.predicted_longitude,
                        "pressure": p.predicted_pressure,
                        "wind_speed": p.predicted_wind_speed,
                        "forecast_hours": p.forecast_hours
                    }
                    for p in predictions
                ]
            }

    # 根据参数选择AI服务
    if ai_provider and ai_provider.lower() == "deepseek":
        ai_service = deepseek_service
    elif ai_provider and ai_provider.lower() == "qwen":
        ai_service = qwen_service
    else:
        # 使用配置文件中的默认服务
        ai_service = AIServiceFactory.get_service()

    # 调用AI服务生成报告
    result = await ai_service.generate_typhoon_report(
        typhoon_id=typhoon_id,
        typhoon_name=typhoon_name,
        prediction_data=prediction_data
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"报告生成失败: {result.get('error', '未知错误')}"
        )
    
    # 保存报告
    db_report = Report(
        typhoon_id=typhoon_id,
        typhoon_name=typhoon_name,
        report_type="analysis",
        report_content=result["report_content"],
        related_prediction_id=prediction_id
    )
    
    db.add(db_report)
    await db.commit()
    await db.refresh(db_report)
    
    return db_report


@router.get("", response_model=List[ReportResponse])
async def get_reports(
    typhoon_id: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """获取报告列表"""
    query = select(Report)
    
    if typhoon_id:
        query = query.where(Report.typhoon_id == typhoon_id)
    
    query = query.order_by(desc(Report.created_at)).limit(limit)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取报告详情"""
    query = select(Report).where(Report.id == report_id)
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    return report

