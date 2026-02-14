"""
预测API路由
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from datetime import datetime, timedelta
from pathlib import Path

from app.core.database import get_db

logger = logging.getLogger(__name__)
from app.core.config import settings
from app.models.typhoon import Prediction, TyphoonPath, Typhoon
from app.schemas.typhoon import PredictionCreate, PredictionResponse
from app.services.prediction import TyphoonPredictor
from app.services.prediction.utils.typhoon_id_utils import (
    normalize_typhoon_id,
    try_normalize_typhoon_id,
    is_valid_typhoon_id
)

router = APIRouter(prefix="/predictions", tags=["预测"])

# 全局预测器实例
_predictor: Optional[TyphoonPredictor] = None


def get_predictor() -> TyphoonPredictor:
    """获取或初始化预测器实例（单例模式）"""
    global _predictor
    if _predictor is None:
        # 模型路径 - 使用V3版本模型（添加moving_direction特征）
        model_path = Path(__file__).parent.parent.parent / "training" / "models" / "best_model.pth"
        
        use_relative_target = True  # V3模型使用相对位置变化
        
        if model_path.exists():
            logger.info(f"使用V3模型: {model_path}, use_relative_target={use_relative_target}")
        else:
            logger.warning(f"未找到V3模型文件: {model_path}，将使用降级策略")
            model_path = None
        
        _predictor = TyphoonPredictor(
            model_path=str(model_path) if model_path else None,
            device="cuda",
            sequence_length=12,
            prediction_steps=8,
            use_relative_target=use_relative_target
        )
    return _predictor


def _get_typhoon_id_query_filter(typhoon_id: str):
    """
    生成台风编号查询条件，同时匹配4位和6位格式
    
    Args:
        typhoon_id: 原始台风编号
        
    Returns:
        SQLAlchemy查询条件
    """
    try:
        # 标准化为6位格式
        normalized_id = normalize_typhoon_id(typhoon_id)
        # 同时匹配6位和4位格式
        return or_(
            TyphoonPath.typhoon_id == normalized_id,
            TyphoonPath.typhoon_id == normalized_id[2:]  # 4位格式
        )
    except ValueError:
        # 如果转换失败，直接使用原始值查询
        return TyphoonPath.typhoon_id == typhoon_id


@router.post("/path", response_model=List[PredictionResponse])
async def predict_path(
    typhoon_id: str = Body(..., description="台风编号（支持4位格式如2601或6位格式如202601）"),
    forecast_hours: int = Body(24, description="预报时效（小时）"),
    use_ensemble: bool = Body(False, description="是否使用集合预测"),
    db: AsyncSession = Depends(get_db)
):
    """
    台风路径预测
    
    Args:
        typhoon_id: 台风编号（支持4位格式如2601或6位格式如202601）
        forecast_hours: 预报时效（12/24/48/72/120小时）
        use_ensemble: 是否使用集合预测（提高准确性）
        
    Returns:
        List[PredictionResponse]: 预测结果列表
    """
    # 验证并标准化台风编号
    if not is_valid_typhoon_id(typhoon_id):
        raise HTTPException(
            status_code=400,
            detail=f"台风编号格式无效: {typhoon_id}，应为4位（如2601）或6位（如202601）数字"
        )
    
    # 标准化为6位格式用于存储
    normalized_id = normalize_typhoon_id(typhoon_id)
    
    # 获取历史路径数据（同时匹配4位和6位格式）
    query = select(TyphoonPath).where(
        _get_typhoon_id_query_filter(typhoon_id)
    ).order_by(TyphoonPath.timestamp)
    
    result = await db.execute(query)
    paths = result.scalars().all()
    
    if len(paths) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"历史数据不足，台风 {typhoon_id} 至少需要3个时间点，当前只有 {len(paths)} 个"
        )
    
    # 调用预测模型
    try:
        predictor = get_predictor()
        
        # 获取台风名称 - 从Typhoon表查询
        typhoon_name = None
        if paths:
            # 查询台风基本信息表获取名称
            typhoon_query = select(Typhoon).where(
                or_(
                    Typhoon.typhoon_id == normalized_id,
                    Typhoon.typhoon_id == normalized_id[2:]
                )
            )
            typhoon_result = await db.execute(typhoon_query)
            typhoon_info = typhoon_result.scalar_one_or_none()
            if typhoon_info:
                typhoon_name = typhoon_info.typhoon_name or typhoon_info.typhoon_name_cn
        
        # 执行预测
        prediction_result = await predictor.predict(
            historical_paths=paths,
            forecast_hours=forecast_hours,
            typhoon_id=normalized_id,  # 使用标准化ID
            typhoon_name=typhoon_name
        )
        
        # 保存预测结果到数据库
        db_predictions = []
        for point in prediction_result.predictions:
            db_pred = Prediction(
                typhoon_id=normalized_id,  # 使用标准化ID存储
                typhoon_name=typhoon_name,
                prediction_type="path",
                forecast_hours=forecast_hours,
                forecast_time=point.forecast_time,
                predicted_latitude=point.latitude,
                predicted_longitude=point.longitude,
                predicted_pressure=point.center_pressure,
                predicted_wind_speed=point.max_wind_speed,
                prediction_model=prediction_result.model_used,
                confidence=point.confidence,
                input_data={
                    "history_count": len(paths),
                    "base_time": prediction_result.base_time.isoformat(),
                    "overall_confidence": prediction_result.overall_confidence,
                    "is_fallback": prediction_result.is_fallback,
                    "original_typhoon_id": typhoon_id  # 保存原始ID
                }
            )
            db.add(db_pred)
            db_predictions.append(db_pred)
        
        await db.commit()
        
        # 刷新以获取ID
        for pred in db_predictions:
            await db.refresh(pred)
        
        return db_predictions
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@router.post("/intensity", response_model=List[PredictionResponse])
async def predict_intensity(
    typhoon_id: str = Body(..., description="台风编号（支持4位格式如2601或6位格式如202601）"),
    forecast_hours: int = Body(24, description="预报时效（小时）"),
    db: AsyncSession = Depends(get_db)
):
    """
    台风强度预测
    
    Args:
        typhoon_id: 台风编号（支持4位格式如2601或6位格式如202601）
        forecast_hours: 预报时效（12/24/48/72/120小时）
        
    Returns:
        List[PredictionResponse]: 预测结果列表（包含气压和风速预测）
    """
    # 验证并标准化台风编号
    if not is_valid_typhoon_id(typhoon_id):
        raise HTTPException(
            status_code=400,
            detail=f"台风编号格式无效: {typhoon_id}，应为4位（如2601）或6位（如202601）数字"
        )
    
    # 标准化为6位格式用于存储
    normalized_id = normalize_typhoon_id(typhoon_id)
    
    # 获取历史路径数据
    query = select(TyphoonPath).where(
        _get_typhoon_id_query_filter(typhoon_id)
    ).order_by(TyphoonPath.timestamp)
    
    result = await db.execute(query)
    paths = result.scalars().all()
    
    if len(paths) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"历史数据不足，台风 {typhoon_id} 至少需要3个时间点，当前只有 {len(paths)} 个"
        )
    
    # 调用预测模型
    try:
        predictor = get_predictor()
        
        # 获取台风名称 - 从Typhoon表查询
        typhoon_name = None
        if paths:
            # 查询台风基本信息表获取名称
            typhoon_query = select(Typhoon).where(
                or_(
                    Typhoon.typhoon_id == normalized_id,
                    Typhoon.typhoon_id == normalized_id[2:]
                )
            )
            typhoon_result = await db.execute(typhoon_query)
            typhoon_info = typhoon_result.scalar_one_or_none()
            if typhoon_info:
                typhoon_name = typhoon_info.typhoon_name or typhoon_info.typhoon_name_cn
        
        # 执行强度预测
        prediction_result = await predictor.predict_intensity(
            historical_paths=paths,
            forecast_hours=forecast_hours,
            typhoon_id=normalized_id,
            typhoon_name=typhoon_name
        )
        
        # 保存预测结果到数据库
        db_predictions = []
        for point in prediction_result.predictions:
            db_pred = Prediction(
                typhoon_id=normalized_id,
                typhoon_name=typhoon_name,
                prediction_type="intensity",
                forecast_hours=forecast_hours,
                forecast_time=point.forecast_time,
                predicted_latitude=point.latitude,
                predicted_longitude=point.longitude,
                predicted_pressure=point.center_pressure,
                predicted_wind_speed=point.max_wind_speed,
                prediction_model=prediction_result.model_used,
                confidence=point.confidence,
                input_data={
                    "history_count": len(paths),
                    "base_time": prediction_result.base_time.isoformat(),
                    "overall_confidence": prediction_result.overall_confidence,
                    "is_fallback": prediction_result.is_fallback,
                    "original_typhoon_id": typhoon_id
                }
            )
            db.add(db_pred)
            db_predictions.append(db_pred)
        
        await db.commit()
        
        # 刷新以获取ID
        for pred in db_predictions:
            await db.refresh(pred)
        
        return db_predictions
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@router.post("/batch", response_model=List[PredictionResponse])
async def predict_batch(
    typhoon_ids: List[str] = Body(..., description="台风编号列表（支持4位或6位格式）"),
    forecast_hours: int = Body(24, description="预报时效（小时）"),
    db: AsyncSession = Depends(get_db)
):
    """
    批量台风预测
    
    Args:
        typhoon_ids: 台风编号列表（支持4位格式如2601或6位格式如202601）
        forecast_hours: 预报时效（小时）
        
    Returns:
        List[PredictionResponse]: 所有台风的预测结果列表
    """
    all_predictions = []
    
    for typhoon_id in typhoon_ids:
        # 验证台风编号
        if not is_valid_typhoon_id(typhoon_id):
            continue
        
        try:
            normalized_id = normalize_typhoon_id(typhoon_id)
            
            # 获取历史路径数据
            query = select(TyphoonPath).where(
                _get_typhoon_id_query_filter(typhoon_id)
            ).order_by(TyphoonPath.timestamp)
            
            result = await db.execute(query)
            paths = result.scalars().all()
            
            if len(paths) < 3:
                continue
            
            predictor = get_predictor()
            
            # 获取台风名称 - 从Typhoon表查询
            typhoon_name = None
            if paths:
                # 查询台风基本信息表获取名称
                typhoon_query = select(Typhoon).where(
                    or_(
                        Typhoon.typhoon_id == normalized_id,
                        Typhoon.typhoon_id == normalized_id[2:]
                    )
                )
                typhoon_result = await db.execute(typhoon_query)
                typhoon_info = typhoon_result.scalar_one_or_none()
                if typhoon_info:
                    typhoon_name = typhoon_info.typhoon_name or typhoon_info.typhoon_name_cn
            
            # 执行预测
            prediction_result = await predictor.predict(
                historical_paths=paths,
                forecast_hours=forecast_hours,
                typhoon_id=normalized_id,
                typhoon_name=typhoon_name
            )
            
            # 保存预测结果
            for point in prediction_result.predictions:
                db_pred = Prediction(
                    typhoon_id=normalized_id,
                    typhoon_name=typhoon_name,
                    prediction_type="path",
                    forecast_hours=forecast_hours,
                    forecast_time=point.forecast_time,
                    predicted_latitude=point.latitude,
                    predicted_longitude=point.longitude,
                    predicted_pressure=point.center_pressure,
                    predicted_wind_speed=point.max_wind_speed,
                    prediction_model=prediction_result.model_used,
                    confidence=point.confidence,
                    input_data={
                        "history_count": len(paths),
                        "base_time": prediction_result.base_time.isoformat(),
                        "overall_confidence": prediction_result.overall_confidence,
                        "is_fallback": prediction_result.is_fallback,
                        "original_typhoon_id": typhoon_id
                    }
                )
                db.add(db_pred)
                all_predictions.append(db_pred)
                
        except Exception as e:
            # 记录错误但继续处理其他台风
            logger.warning(f"预测台风 {typhoon_id} 失败: {e}")
            continue
    
    if not all_predictions:
        raise HTTPException(status_code=400, detail="所有台风预测失败，请检查台风编号和数据")
    
    await db.commit()
    
    # 刷新以获取ID
    for pred in all_predictions:
        await db.refresh(pred)
    
    return all_predictions


@router.get("/{typhoon_id}", response_model=List[PredictionResponse])
async def get_predictions(
    typhoon_id: str,
    prediction_type: Optional[str] = Query(None, description="预测类型筛选(path/intensity)"),
    limit: int = Query(100, description="返回记录数量限制"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取台风的预测记录
    
    Args:
        typhoon_id: 台风编号（支持4位或6位格式）
        prediction_type: 预测类型筛选（可选：path/intensity）
        limit: 返回记录数量限制
        
    Returns:
        List[PredictionResponse]: 预测记录列表
    """
    # 验证台风编号
    if not is_valid_typhoon_id(typhoon_id):
        raise HTTPException(
            status_code=400,
            detail=f"台风编号格式无效: {typhoon_id}"
        )
    
    normalized_id = normalize_typhoon_id(typhoon_id)
    
    # 同时查询6位和4位格式的记录
    query = select(Prediction).where(
        or_(
            Prediction.typhoon_id == normalized_id,
            Prediction.typhoon_id == normalized_id[2:],
            Prediction.typhoon_id == typhoon_id
        )
    )
    
    # 添加类型筛选
    if prediction_type:
        query = query.where(Prediction.prediction_type == prediction_type)
    
    query = query.order_by(desc(Prediction.created_at)).limit(limit)
    
    result = await db.execute(query)
    predictions = result.scalars().all()
    
    return predictions


@router.get("/stats/{typhoon_id}")
async def get_prediction_stats(
    typhoon_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取台风预测统计信息
    
    Args:
        typhoon_id: 台风编号（支持4位或6位格式）
        
    Returns:
        dict: 预测统计信息
    """
    # 验证台风编号
    if not is_valid_typhoon_id(typhoon_id):
        raise HTTPException(
            status_code=400,
            detail=f"台风编号格式无效: {typhoon_id}"
        )
    
    normalized_id = normalize_typhoon_id(typhoon_id)
    
    query = select(Prediction).where(
        or_(
            Prediction.typhoon_id == normalized_id,
            Prediction.typhoon_id == normalized_id[2:],
            Prediction.typhoon_id == typhoon_id
        )
    )
    result = await db.execute(query)
    predictions = result.scalars().all()
    
    if not predictions:
        raise HTTPException(status_code=404, detail="未找到该台风的预测记录")
    
    # 计算统计信息
    total_predictions = len(predictions)
    path_predictions = len([p for p in predictions if p.prediction_type == "path"])
    intensity_predictions = len([p for p in predictions if p.prediction_type == "intensity"])
    
    avg_confidence = sum(p.confidence for p in predictions) / total_predictions if predictions else 0
    
    # 按预报时效分组统计
    forecast_hour_counts = {}
    for p in predictions:
        hours = p.forecast_hours
        forecast_hour_counts[hours] = forecast_hour_counts.get(hours, 0) + 1
    
    return {
        "typhoon_id": typhoon_id,
        "normalized_id": normalized_id,
        "total_predictions": total_predictions,
        "path_predictions": path_predictions,
        "intensity_predictions": intensity_predictions,
        "average_confidence": round(avg_confidence, 4),
        "forecast_hour_distribution": forecast_hour_counts,
        "latest_prediction": predictions[0].created_at.isoformat() if predictions else None
    }


@router.delete("/{typhoon_id}")
async def clear_predictions(
    typhoon_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    清除台风的所有预测记录
    
    Args:
        typhoon_id: 台风编号（支持4位或6位格式）
        
    Returns:
        dict: 删除结果
    """
    # 验证台风编号
    if not is_valid_typhoon_id(typhoon_id):
        raise HTTPException(
            status_code=400,
            detail=f"台风编号格式无效: {typhoon_id}"
        )
    
    normalized_id = normalize_typhoon_id(typhoon_id)
    
    query = select(Prediction).where(
        or_(
            Prediction.typhoon_id == normalized_id,
            Prediction.typhoon_id == normalized_id[2:],
            Prediction.typhoon_id == typhoon_id
        )
    )
    result = await db.execute(query)
    predictions = result.scalars().all()
    
    count = len(predictions)
    
    for pred in predictions:
        await db.delete(pred)
    
    await db.commit()
    
    return {
        "typhoon_id": typhoon_id,
        "normalized_id": normalized_id,
        "deleted_count": count,
        "message": f"成功删除 {count} 条预测记录"
    }


# ========== 高级预测功能 ==========

from app.services.prediction.predictor_advanced import (
    AdvancedTyphoonPredictor,
    ArbitraryStartPoint,
    RollingPredictionConfig
)

# 全局高级预测器实例
_advanced_predictor: Optional[AdvancedTyphoonPredictor] = None


def get_advanced_predictor() -> AdvancedTyphoonPredictor:
    """获取或初始化高级预测器实例"""
    global _advanced_predictor
    if _advanced_predictor is None:
        # 模型路径 - 使用V3版本模型（添加moving_direction特征）
        model_path = Path(__file__).parent.parent.parent / "training" / "models" / "best_model.pth"
        
        use_relative_target = True  # V3模型使用相对位置变化
        
        if model_path.exists():
            logger.info(f"高级预测器使用V3模型: {model_path}, use_relative_target={use_relative_target}")
        else:
            logger.warning(f"高级预测器未找到V3模型文件: {model_path}，将使用降级策略")
            model_path = None
        
        _advanced_predictor = AdvancedTyphoonPredictor(
            model_path=str(model_path) if model_path else None,
            device="cuda",
            sequence_length=12,
            prediction_steps=8,
            use_relative_target=use_relative_target
        )
    return _advanced_predictor


@router.post("/arbitrary-start", response_model=List[PredictionResponse])
async def predict_from_arbitrary_start(
    typhoon_id: str = Body(..., description="台风编号（支持4位或6位格式）"),
    start_time: datetime = Body(..., description="预测起点时间（ISO格式）"),
    start_latitude: float = Body(..., description="起点纬度"),
    start_longitude: float = Body(..., description="起点经度"),
    start_pressure: Optional[float] = Body(None, description="起点中心气压（可选）"),
    start_wind_speed: Optional[float] = Body(None, description="起点最大风速（可选）"),
    forecast_hours: int = Body(12, description="预报时效（小时），默认12小时，每3小时一个预测点"),
    db: AsyncSession = Depends(get_db)
):
    """
    从任意起点进行预测
    
    应用场景：
    - 假设情景分析（"如果台风在某时某刻位于某位置..."）
    - 多机构预报对比
    - 人工干预预测
    
    Args:
        typhoon_id: 台风编号
        start_time: 预测起点时间（ISO格式，如2026-01-15T12:00:00）
        start_latitude: 起点纬度
        start_longitude: 起点经度
        start_pressure: 起点中心气压（可选）
        start_wind_speed: 起点最大风速（可选）
        forecast_hours: 预报时效
        
    Returns:
        List[PredictionResponse]: 预测结果列表
    """
    # 验证台风编号
    if not is_valid_typhoon_id(typhoon_id):
        raise HTTPException(
            status_code=400,
            detail=f"台风编号格式无效: {typhoon_id}"
        )
    
    normalized_id = normalize_typhoon_id(typhoon_id)
    
    # 获取历史路径数据
    query = select(TyphoonPath).where(
        _get_typhoon_id_query_filter(typhoon_id)
    ).order_by(TyphoonPath.timestamp)
    
    result = await db.execute(query)
    paths = result.scalars().all()
    
    if len(paths) < 1:
        raise HTTPException(
            status_code=400,
            detail=f"历史数据不足，台风 {typhoon_id} 至少需要1个时间点"
        )
    
    try:
        predictor = get_advanced_predictor()
        
        # 获取台风名称
        typhoon_name = None
        typhoon_query = select(Typhoon).where(
            or_(
                Typhoon.typhoon_id == normalized_id,
                Typhoon.typhoon_id == normalized_id[2:]
            )
        )
        typhoon_result = await db.execute(typhoon_query)
        typhoon_info = typhoon_result.scalar_one_or_none()
        if typhoon_info:
            typhoon_name = typhoon_info.typhoon_name or typhoon_info.typhoon_name_cn
        
        # 创建起点对象
        start_point = ArbitraryStartPoint(
            timestamp=start_time,
            latitude=start_latitude,
            longitude=start_longitude,
            center_pressure=start_pressure,
            max_wind_speed=start_wind_speed
        )
        
        # 执行任意起点预测
        prediction_result = await predictor.predict_from_arbitrary_start(
            historical_paths=paths,
            start_point=start_point,
            forecast_hours=forecast_hours,
            typhoon_id=normalized_id,
            typhoon_name=typhoon_name
        )
        
        # 保存预测结果
        db_predictions = []
        for point in prediction_result.predictions:
            db_pred = Prediction(
                typhoon_id=normalized_id,
                typhoon_name=typhoon_name,
                prediction_type="arbitrary_start",
                forecast_hours=forecast_hours,
                forecast_time=point.forecast_time,
                predicted_latitude=point.latitude,
                predicted_longitude=point.longitude,
                predicted_pressure=point.center_pressure,
                predicted_wind_speed=point.max_wind_speed,
                prediction_model=prediction_result.model_used,
                confidence=point.confidence,
                input_data={
                    "history_count": len(paths),
                    "base_time": prediction_result.base_time.isoformat(),
                    "overall_confidence": prediction_result.overall_confidence,
                    "is_fallback": prediction_result.is_fallback,
                    "original_typhoon_id": typhoon_id,
                    "start_point": {
                        "time": start_time.isoformat(),
                        "latitude": start_latitude,
                        "longitude": start_longitude,
                        "pressure": start_pressure,
                        "wind_speed": start_wind_speed
                    }
                }
            )
            db.add(db_pred)
            db_predictions.append(db_pred)
        
        await db.commit()
        
        for pred in db_predictions:
            await db.refresh(pred)
        
        return db_predictions
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"任意起点预测失败: {str(e)}")


@router.post("/rolling", response_model=List[List[PredictionResponse]])
async def rolling_prediction(
    typhoon_id: str = Body(..., description="台风编号（支持4位或6位格式）"),
    initial_forecast_hours: int = Body(48, description="初始预报时效（小时）"),
    update_interval_hours: int = Body(6, description="更新间隔（小时）"),
    max_iterations: int = Body(5, description="最大滚动次数"),
    confidence_threshold: float = Body(0.5, description="置信度阈值，低于此值停止滚动"),
    db: AsyncSession = Depends(get_db)
):
    """
    滚动预测
    
    原理：
    1. 基于当前数据进行初始预测
    2. 模拟时间推移，将预测结果作为新的"观测"数据
    3. 重新进行预测
    4. 重复直到达到最大迭代次数或置信度低于阈值
    
    应用场景：
    - 评估预测稳定性
    - 模拟实时更新场景
    - 长期趋势分析
    
    Args:
        typhoon_id: 台风编号
        initial_forecast_hours: 初始预报时效
        update_interval_hours: 更新间隔（小时）
        max_iterations: 最大滚动次数
        confidence_threshold: 置信度阈值
        
    Returns:
        List[List[PredictionResponse]]: 每次迭代的预测结果列表
    """
    # 验证台风编号
    if not is_valid_typhoon_id(typhoon_id):
        raise HTTPException(
            status_code=400,
            detail=f"台风编号格式无效: {typhoon_id}"
        )
    
    normalized_id = normalize_typhoon_id(typhoon_id)
    
    # 获取历史路径数据
    query = select(TyphoonPath).where(
        _get_typhoon_id_query_filter(typhoon_id)
    ).order_by(TyphoonPath.timestamp)
    
    result = await db.execute(query)
    paths = result.scalars().all()
    
    if len(paths) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"历史数据不足，台风 {typhoon_id} 至少需要3个时间点"
        )
    
    try:
        predictor = get_advanced_predictor()
        
        # 获取台风名称
        typhoon_name = None
        typhoon_query = select(Typhoon).where(
            or_(
                Typhoon.typhoon_id == normalized_id,
                Typhoon.typhoon_id == normalized_id[2:]
            )
        )
        typhoon_result = await db.execute(typhoon_query)
        typhoon_info = typhoon_result.scalar_one_or_none()
        if typhoon_info:
            typhoon_name = typhoon_info.typhoon_name or typhoon_info.typhoon_name_cn
        
        # 创建配置
        config = RollingPredictionConfig(
            initial_forecast_hours=initial_forecast_hours,
            update_interval_hours=update_interval_hours,
            max_iterations=max_iterations,
            confidence_threshold=confidence_threshold
        )
        
        # 执行滚动预测
        rolling_results = await predictor.rolling_prediction(
            initial_paths=paths,
            config=config,
            typhoon_id=normalized_id,
            typhoon_name=typhoon_name
        )
        
        # 保存所有迭代的结果
        all_db_predictions = []
        iteration_results = []
        
        for iteration_idx, prediction_result in enumerate(rolling_results):
            iteration_predictions = []
            
            for point in prediction_result.predictions:
                db_pred = Prediction(
                    typhoon_id=normalized_id,
                    typhoon_name=typhoon_name,
                    prediction_type="rolling",
                    forecast_hours=initial_forecast_hours,
                    forecast_time=point.forecast_time,
                    predicted_latitude=point.latitude,
                    predicted_longitude=point.longitude,
                    predicted_pressure=point.center_pressure,
                    predicted_wind_speed=point.max_wind_speed,
                    prediction_model=prediction_result.model_used,
                    confidence=point.confidence,
                    input_data={
                        "history_count": len(paths),
                        "base_time": prediction_result.base_time.isoformat(),
                        "overall_confidence": prediction_result.overall_confidence,
                        "is_fallback": prediction_result.is_fallback,
                        "original_typhoon_id": typhoon_id,
                        "iteration": iteration_idx + 1,
                        "total_iterations": len(rolling_results),
                        "rolling_config": {
                            "initial_forecast_hours": initial_forecast_hours,
                            "update_interval_hours": update_interval_hours,
                            "max_iterations": max_iterations,
                            "confidence_threshold": confidence_threshold
                        }
                    }
                )
                db.add(db_pred)
                iteration_predictions.append(db_pred)
                all_db_predictions.append(db_pred)
            
            iteration_results.append(iteration_predictions)
        
        await db.commit()
        
        for pred in all_db_predictions:
            await db.refresh(pred)
        
        return iteration_results
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"滚动预测失败: {str(e)}")


@router.post("/virtual-observations", response_model=List[PredictionResponse])
async def predict_with_virtual_observations(
    typhoon_id: str = Body(..., description="台风编号（支持4位或6位格式）"),
    virtual_observations: List[dict] = Body(..., description="虚拟观测点列表"),
    forecast_hours: int = Body(48, description="预报时效（小时）"),
    db: AsyncSession = Depends(get_db)
):
    """
    基于虚拟观测点进行预测
    
    应用场景：
    - 假设情景分析（"如果台风转向..."）
    - 多机构预报对比
    - 人工干预预测
    
    Args:
        typhoon_id: 台风编号
        virtual_observations: 虚拟观测点列表，每个点包含：
            - timestamp: 时间（ISO格式）
            - latitude: 纬度
            - longitude: 经度
            - center_pressure: 中心气压（可选）
            - max_wind_speed: 最大风速（可选）
        forecast_hours: 预报时效
        
    Returns:
        List[PredictionResponse]: 预测结果列表
    """
    # 验证台风编号
    if not is_valid_typhoon_id(typhoon_id):
        raise HTTPException(
            status_code=400,
            detail=f"台风编号格式无效: {typhoon_id}"
        )
    
    if not virtual_observations or len(virtual_observations) < 1:
        raise HTTPException(
            status_code=400,
            detail="至少需要提供1个虚拟观测点"
        )
    
    normalized_id = normalize_typhoon_id(typhoon_id)
    
    # 获取历史路径数据
    query = select(TyphoonPath).where(
        _get_typhoon_id_query_filter(typhoon_id)
    ).order_by(TyphoonPath.timestamp)
    
    result = await db.execute(query)
    paths = result.scalars().all()
    
    try:
        predictor = get_advanced_predictor()
        
        # 获取台风名称
        typhoon_name = None
        typhoon_query = select(Typhoon).where(
            or_(
                Typhoon.typhoon_id == normalized_id,
                Typhoon.typhoon_id == normalized_id[2:]
            )
        )
        typhoon_result = await db.execute(typhoon_query)
        typhoon_info = typhoon_result.scalar_one_or_none()
        if typhoon_info:
            typhoon_name = typhoon_info.typhoon_name or typhoon_info.typhoon_name_cn
        
        # 转换虚拟观测点
        virtual_points = []
        for obs in virtual_observations:
            try:
                point = ArbitraryStartPoint(
                    timestamp=datetime.fromisoformat(obs["timestamp"].replace('Z', '+00:00')),
                    latitude=float(obs["latitude"]),
                    longitude=float(obs["longitude"]),
                    center_pressure=obs.get("center_pressure"),
                    max_wind_speed=obs.get("max_wind_speed")
                )
                virtual_points.append(point)
            except (KeyError, ValueError) as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"虚拟观测点格式错误: {e}"
                )
        
        # 执行虚拟观测点预测
        prediction_result = await predictor.predict_with_virtual_observations(
            historical_paths=paths,
            virtual_observations=virtual_points,
            forecast_hours=forecast_hours,
            typhoon_id=normalized_id,
            typhoon_name=typhoon_name
        )
        
        # 保存预测结果
        db_predictions = []
        for point in prediction_result.predictions:
            db_pred = Prediction(
                typhoon_id=normalized_id,
                typhoon_name=typhoon_name,
                prediction_type="virtual_obs",
                forecast_hours=forecast_hours,
                forecast_time=point.forecast_time,
                predicted_latitude=point.latitude,
                predicted_longitude=point.longitude,
                predicted_pressure=point.center_pressure,
                predicted_wind_speed=point.max_wind_speed,
                prediction_model=prediction_result.model_used,
                confidence=point.confidence,
                input_data={
                    "history_count": len(paths),
                    "base_time": prediction_result.base_time.isoformat(),
                    "overall_confidence": prediction_result.overall_confidence,
                    "is_fallback": prediction_result.is_fallback,
                    "original_typhoon_id": typhoon_id,
                    "virtual_observations_count": len(virtual_points)
                }
            )
            db.add(db_pred)
            db_predictions.append(db_pred)
        
        await db.commit()
        
        for pred in db_predictions:
            await db.refresh(pred)
        
        return db_predictions
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"虚拟观测点预测失败: {str(e)}")
