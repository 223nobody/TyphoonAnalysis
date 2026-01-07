"""
预测API路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.typhoon import Prediction, TyphoonPath
from app.schemas.typhoon import PredictionCreate, PredictionResponse
from app.services.ml.lstm_predictor import predict_typhoon_path

router = APIRouter(prefix="/predictions", tags=["预测"])


@router.post("/path", response_model=List[PredictionResponse])
async def predict_path(
    typhoon_id: str = Body(..., description="台风编号"),
    forecast_hours: int = Body(24, description="预报时效（小时）"),
    db: AsyncSession = Depends(get_db)
):
    """
    台风路径预测
    
    Args:
        typhoon_id: 台风编号
        forecast_hours: 预报时效（12/24/48小时）
        
    Returns:
        List[PredictionResponse]: 预测结果列表
    """
    # 获取历史路径数据
    query = select(TyphoonPath).where(
        TyphoonPath.typhoon_id == typhoon_id
    ).order_by(TyphoonPath.timestamp)
    
    result = await db.execute(query)
    paths = result.scalars().all()
    
    if len(paths) < 3:
        raise HTTPException(
            status_code=400,
            detail="历史数据不足，至少需要3个时间点"
        )
    
    # 调用预测模型
    try:
        predictions = await predict_typhoon_path(paths, forecast_hours)
        
        # 保存预测结果到数据库
        db_predictions = []
        for pred in predictions:
            db_pred = Prediction(
                typhoon_id=typhoon_id,
                typhoon_name=paths[0].typhoon_id if paths else None,
                prediction_type="path",
                forecast_hours=forecast_hours,
                forecast_time=pred["timestamp"],
                predicted_latitude=pred["latitude"],
                predicted_longitude=pred["longitude"],
                predicted_pressure=pred.get("center_pressure"),
                predicted_wind_speed=pred.get("max_wind_speed"),
                prediction_model="LSTM",
                confidence=pred.get("confidence", 0.8),
                input_data={"history_count": len(paths)}
            )
            db.add(db_pred)
            db_predictions.append(db_pred)
        
        await db.commit()
        
        # 刷新以获取ID
        for pred in db_predictions:
            await db.refresh(pred)
        
        return db_predictions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@router.get("/{typhoon_id}", response_model=List[PredictionResponse])
async def get_predictions(
    typhoon_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取台风的预测记录"""
    query = select(Prediction).where(
        Prediction.typhoon_id == typhoon_id
    ).order_by(desc(Prediction.created_at)).limit(limit)
    
    result = await db.execute(query)
    predictions = result.scalars().all()
    
    return predictions

