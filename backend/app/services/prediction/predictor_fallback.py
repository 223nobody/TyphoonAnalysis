"""
预测器降级实现

当PyTorch不可用时，提供基于线性外推的降级预测功能
"""
import logging
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

from app.models.typhoon import TyphoonPath

logger = logging.getLogger(__name__)


@dataclass
class PredictedPoint:
    """预测点数据类"""
    forecast_time: datetime
    latitude: float
    longitude: float
    center_pressure: Optional[float]
    max_wind_speed: Optional[float]
    confidence: float


@dataclass
class PredictionResult:
    """预测结果数据类"""
    typhoon_id: str
    typhoon_name: Optional[str]
    forecast_hours: int
    base_time: datetime
    predictions: List[PredictedPoint]
    overall_confidence: float
    model_used: str
    is_fallback: bool = True


class TyphoonPredictor:
    """
    台风预测器 (降级实现)

    当深度学习模型不可用时，使用线性外推进行预测
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
        sequence_length: int = 12,
        prediction_steps: int = 8,
        use_simple_model: bool = False
    ):
        """
        初始化预测器 (降级模式)

        Args:
            model_path: 模型权重文件路径 (降级模式下忽略)
            device: 计算设备 (降级模式下忽略)
            sequence_length: 输入序列长度
            prediction_steps: 预测步数
            use_simple_model: 是否使用简化模型 (降级模式下忽略)
        """
        self.sequence_length = sequence_length
        self.prediction_steps = prediction_steps
        logger.info("预测器初始化完成 (降级模式 - 线性外推)")

    async def predict(
        self,
        historical_paths: List[TyphoonPath],
        forecast_hours: int = 48,
        typhoon_id: str = "",
        typhoon_name: Optional[str] = None
    ) -> PredictionResult:
        """
        执行台风路径预测 (线性外推)

        Args:
            historical_paths: 历史路径数据列表
            forecast_hours: 预报时效
            typhoon_id: 台风编号
            typhoon_name: 台风名称

        Returns:
            PredictionResult: 预测结果
        """
        # 验证输入
        if len(historical_paths) < 3:
            raise ValueError("历史数据不足，至少需要3个观测点")

        # 计算平均移动趋势
        recent_paths = sorted(historical_paths, key=lambda x: x.timestamp)[-5:]

        lat_diffs = np.diff([p.latitude for p in recent_paths])
        lon_diffs = np.diff([p.longitude for p in recent_paths])

        avg_lat_change = np.mean(lat_diffs) if len(lat_diffs) > 0 else 0
        avg_lon_change = np.mean(lon_diffs) if len(lon_diffs) > 0 else 0

        # 计算强度趋势
        pressures = [p.center_pressure for p in recent_paths if p.center_pressure is not None]
        winds = [p.max_wind_speed for p in recent_paths if p.max_wind_speed is not None]

        avg_pressure_change = np.diff(pressures).mean() if len(pressures) > 1 else 0
        avg_wind_change = np.diff(winds).mean() if len(winds) > 1 else 0

        # 生成预测点
        last_point = recent_paths[-1]
        base_time = last_point.timestamp

        predictions = []
        num_points = forecast_hours // 6

        for i in range(1, num_points + 1):
            forecast_time = base_time + timedelta(hours=6 * i)

            pred_lat = last_point.latitude + avg_lat_change * i
            pred_lon = last_point.longitude + avg_lon_change * i

            # 强度预测
            pred_pressure = None
            pred_wind = None
            if last_point.center_pressure is not None:
                pred_pressure = last_point.center_pressure + avg_pressure_change * i
            if last_point.max_wind_speed is not None:
                pred_wind = max(0, last_point.max_wind_speed + avg_wind_change * i)

            # 置信度随时间递减
            conf = max(0.3, 0.7 - i * 0.05)

            point = PredictedPoint(
                forecast_time=forecast_time,
                latitude=pred_lat,
                longitude=pred_lon,
                center_pressure=pred_pressure,
                max_wind_speed=pred_wind,
                confidence=conf
            )
            predictions.append(point)

        return PredictionResult(
            typhoon_id=typhoon_id,
            typhoon_name=typhoon_name,
            forecast_hours=forecast_hours,
            base_time=base_time,
            predictions=predictions,
            overall_confidence=0.5,
            model_used="LinearFallback",
            is_fallback=True
        )

    async def predict_intensity(
        self,
        historical_paths: List[TyphoonPath],
        forecast_hours: int = 48,
        typhoon_id: str = "",
        typhoon_name: Optional[str] = None
    ) -> PredictionResult:
        """
        执行台风强度预测

        复用路径预测的结果
        """
        return await self.predict(
            historical_paths, forecast_hours, typhoon_id, typhoon_name
        )
