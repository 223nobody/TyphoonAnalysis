"""
报告API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.typhoon import Report, Prediction, TyphoonPath, Typhoon
from app.schemas.typhoon import ReportCreate, ReportResponse
from app.services.ai.ai_factory import AIServiceFactory
from app.services.ai.qwen_service import qwen_service
from app.services.ai.deepseek_service import deepseek_service

router = APIRouter(prefix="/report", tags=["报告"])


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    typhoon_id: str = Body(..., description="台风编号"),
    typhoon_name: str = Body("", description="台风名称"),
    report_type: str = Body("comprehensive", description="报告类型：comprehensive/prediction/impact"),
    ai_provider: Optional[str] = Body(None, description="AI服务提供商（qwen或deepseek）"),
    db: AsyncSession = Depends(get_db)
):
    """
    生成台风分析报告（支持三种报告类型）

    报告类型说明：
    - comprehensive: 综合分析报告（基于历史路径数据）
    - prediction: 预测报告（基于预测数据）
    - impact: 影响评估报告（基于历史数据）

    Args:
        typhoon_id: 台风编号
        typhoon_name: 台风名称
        report_type: 报告类型
        ai_provider: AI服务提供商（qwen或deepseek）

    Returns:
        ReportResponse: 生成的报告
    """
    # 1. 查询台风基本信息
    typhoon_query = select(Typhoon).where(Typhoon.typhoon_id == typhoon_id)
    typhoon_result = await db.execute(typhoon_query)
    typhoon = typhoon_result.scalar_one_or_none()

    if not typhoon and not typhoon_name:
        raise HTTPException(status_code=404, detail=f"台风 {typhoon_id} 不存在，且未提供台风名称")

    # 使用数据库中的名称或传入的名称
    final_typhoon_name = typhoon.typhoon_name_cn if typhoon and typhoon.typhoon_name_cn else (typhoon_name or "未知")

    # 2. 根据报告类型准备数据
    historical_data = {}
    prediction_data = {}
    prediction_id = None

    if report_type in ["comprehensive", "impact"]:
        # 综合分析报告和影响评估报告需要历史路径数据
        path_query = select(TyphoonPath).where(
            TyphoonPath.typhoon_id == typhoon_id
        ).order_by(TyphoonPath.timestamp)

        path_result = await db.execute(path_query)
        paths = path_result.scalars().all()

        if paths:
            historical_data = {
                "path_count": len(paths),
                "paths": [
                    {
                        "timestamp": str(p.timestamp),
                        "latitude": p.latitude,
                        "longitude": p.longitude,
                        "center_pressure": p.center_pressure,
                        "max_wind_speed": p.max_wind_speed,
                        "moving_speed": p.moving_speed,
                        "moving_direction": p.moving_direction,
                        "intensity": p.intensity
                    }
                    for p in paths
                ]
            }

    if report_type == "prediction":
        # 预测报告需要预测数据
        pred_query = select(Prediction).where(
            Prediction.typhoon_id == typhoon_id
        ).order_by(desc(Prediction.created_at)).limit(10)

        pred_result = await db.execute(pred_query)
        predictions = pred_result.scalars().all()

        if predictions:
            prediction_id = predictions[0].id
            prediction_data = {
                "prediction_count": len(predictions),
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

    # 3. 选择AI服务
    if ai_provider and ai_provider.lower() == "deepseek":
        ai_service = deepseek_service
    elif ai_provider and ai_provider.lower() == "qwen":
        ai_service = qwen_service
    else:
        ai_service = AIServiceFactory.get_service()

    # 4. 调用AI服务生成报告
    result = await ai_service.generate_typhoon_report(
        typhoon_id=typhoon_id,
        typhoon_name=final_typhoon_name,
        report_type=report_type,
        historical_data=historical_data,
        prediction_data=prediction_data
    )

    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"报告生成失败: {result.get('error', '未知错误')}"
        )

    # 5. 保存报告
    db_report = Report(
        typhoon_id=typhoon_id,
        typhoon_name=final_typhoon_name,
        report_type=report_type,
        report_content=result["report_content"],
        model_used=result.get("model_used", "未知"),
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

