"""
预测器主模块

提供台风路径和强度的智能预测功能
"""
import logging
from typing import List, Optional, Tuple, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn

from app.models.typhoon import TyphoonPath
from .models.lstm_model import LSTMTyphoonModel, SimpleTyphoonModel
from .data.preprocessor import DataPreprocessor, NormalizationParams
from .data.csv_loader import CSVDataLoader, TyphoonPathData

logger = logging.getLogger(__name__)

# 定义路径数据类型别名
PathData = Union[TyphoonPath, TyphoonPathData]


def normalize_datetime(dt: datetime) -> datetime:
    """
    标准化时间戳，确保所有时间都是带时区的（aware）
    
    Args:
        dt: 输入时间（可能是naive或aware）
        
    Returns:
        带时区的datetime对象
    """
    if dt is None:
        return None
    
    # 如果已经是aware，直接返回
    if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
        return dt
    
    # 如果是naive，假设为UTC时区
    return dt.replace(tzinfo=timezone.utc)


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
    is_fallback: bool = False


class TyphoonPredictor:
    """
    台风智能预测器

    职责:
    1. 加载和管理预测模型
    2. 执行预测推理
    3. 结果后处理
    4. 异常处理和降级策略
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
        初始化预测器

        Args:
            model_path: 模型权重文件路径
            device: 计算设备 (cpu/cuda)
            sequence_length: 输入序列长度
            prediction_steps: 预测步数
            use_simple_model: 是否使用简化模型
        """
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.sequence_length = sequence_length
        self.prediction_steps = prediction_steps
        self.model_path = model_path
        self.use_simple_model = use_simple_model

        # 初始化预处理器
        self.preprocessor = DataPreprocessor(
            sequence_length=sequence_length,
            prediction_steps=prediction_steps
        )

        # 初始化模型
        self.model = None
        self.model_loaded = False

        if model_path and Path(model_path).exists():
            self._load_model()
        else:
            logger.warning(f"模型文件不存在: {model_path}，将使用降级策略")

    def _load_model(self):
        """加载模型权重"""
        try:
            if self.use_simple_model:
                self.model = SimpleTyphoonModel(
                    prediction_steps=self.prediction_steps
                )
            else:
                self.model = LSTMTyphoonModel(
                    prediction_steps=self.prediction_steps
                )

            # 加载检查点
            checkpoint = torch.load(self.model_path, map_location=self.device)
            
            # 检查检查点内容，提取模型权重
            if isinstance(checkpoint, dict):
                if 'model_state_dict' in checkpoint:
                    state_dict = checkpoint['model_state_dict']
                else:
                    # 如果检查点直接是状态字典
                    state_dict = checkpoint
            else:
                state_dict = checkpoint
            
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()

            self.model_loaded = True
            logger.info(f"模型加载成功: {self.model_path}")

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            self.model_loaded = False

    async def predict(
        self,
        historical_paths: List[PathData],
        forecast_hours: int = 48,
        typhoon_id: str = "",
        typhoon_name: Optional[str] = None
    ) -> PredictionResult:
        """
        执行台风路径预测

        Args:
            historical_paths: 历史路径数据列表
            forecast_hours: 预报时效 (12/24/48/72/120)
            typhoon_id: 台风编号
            typhoon_name: 台风名称

        Returns:
            PredictionResult: 预测结果对象

        Raises:
            InsufficientDataError: 历史数据不足
        """
        # 1. 输入验证
        if not self._validate_input(historical_paths):
            raise ValueError("输入数据验证失败: 历史数据不足或无效")

        # 2. 检查模型状态
        if not self.model_loaded:
            logger.warning("模型未加载，使用降级预测策略")
            return await self._fallback_prediction(
                historical_paths, forecast_hours, typhoon_id, typhoon_name
            )

        try:
            # 3. 数据预处理
            input_tensor = self._preprocess(historical_paths)
            input_tensor = input_tensor.to(self.device)

            # 4. 模型推理
            with torch.no_grad():
                predictions, confidence, _ = self.model(input_tensor)

            # 5. 结果后处理
            predictions = predictions.cpu().numpy()
            confidence = confidence.cpu().numpy()

            # 反归一化
            denorm_predictions = self.preprocessor.denormalize(predictions[0])

            # 6. 构建预测点
            predicted_points = self._build_prediction_points(
                denorm_predictions,
                confidence[0],
                historical_paths,
                forecast_hours
            )

            # 7. 构建结果
            # 使用标准化后的时间进行比较
            last_path = max(historical_paths, key=lambda x: normalize_datetime(x.timestamp))
            result = PredictionResult(
                typhoon_id=typhoon_id,
                typhoon_name=typhoon_name,
                forecast_hours=forecast_hours,
                base_time=normalize_datetime(last_path.timestamp),
                predictions=predicted_points,
                overall_confidence=float(np.mean(confidence)),
                model_used="LSTM",
                is_fallback=False
            )

            return result

        except Exception as e:
            logger.error(f"模型预测失败: {e}，使用降级策略")
            return await self._fallback_prediction(
                historical_paths, forecast_hours, typhoon_id, typhoon_name
            )

    def _validate_input(
        self,
        historical_paths: List[PathData]
    ) -> bool:
        """
        输入数据验证

        验证规则:
        1. 数据点数量 >= 3
        2. 时间跨度 >= 12小时
        3. 数据完整性检查
        """
        if len(historical_paths) < 3:
            logger.warning(f"历史数据不足: {len(historical_paths)} < 3")
            return False

        # 按时间排序（使用标准化后的时间）
        sorted_paths = sorted(historical_paths, key=lambda x: normalize_datetime(x.timestamp))
        
        # 检查时间跨度（使用标准化后的时间）
        first_time = normalize_datetime(sorted_paths[0].timestamp)
        last_time = normalize_datetime(sorted_paths[-1].timestamp)
        time_span = last_time - first_time
        if time_span.total_seconds() < 12 * 3600:
            logger.warning(f"历史时间跨度不足: {time_span} < 12小时")
            return False

        # 检查关键字段
        for path in sorted_paths:
            if path.latitude is None or path.longitude is None:
                logger.warning("存在缺失经纬度的数据点")
                return False

        return True

    def _preprocess(
        self,
        historical_paths: List[PathData]
    ) -> torch.Tensor:
        """
        数据预处理

        Args:
            historical_paths: 历史路径数据

        Returns:
            模型输入Tensor
        """
        # 使用预处理器准备输入
        input_array = self.preprocessor.prepare_prediction_input(historical_paths)

        # 转换为Tensor
        input_tensor = torch.FloatTensor(input_array)

        return input_tensor

    def _build_prediction_points(
        self,
        predictions: np.ndarray,
        confidence: np.ndarray,
        historical_paths: List[PathData],
        forecast_hours: int
    ) -> List[PredictedPoint]:
        """
        构建预测点列表

        Args:
            predictions: 预测值数组 [pred_steps, 4]
            confidence: 置信度数组 [pred_steps]
            historical_paths: 历史路径数据
            forecast_hours: 预报时效

        Returns:
            预测点列表
        """
        # 获取最后一个观测点的时间（使用标准化后的时间进行比较）
        last_path = max(historical_paths, key=lambda x: normalize_datetime(x.timestamp))
        base_time = normalize_datetime(last_path.timestamp)

        # 计算需要生成的预测点数
        num_points = min(
            len(predictions),
            forecast_hours // 6  # 每6小时一个预测点
        )

        points = []
        for i in range(num_points):
            forecast_time = base_time + timedelta(hours=6 * (i + 1))

            point = PredictedPoint(
                forecast_time=forecast_time,
                latitude=float(predictions[i, 0]),
                longitude=float(predictions[i, 1]),
                center_pressure=float(predictions[i, 2]) if predictions[i, 2] > 0 else None,
                max_wind_speed=float(predictions[i, 3]) if predictions[i, 3] > 0 else None,
                confidence=float(confidence[i])
            )
            points.append(point)

        return points

    async def _fallback_prediction(
        self,
        historical_paths: List[PathData],
        forecast_hours: int,
        typhoon_id: str = "",
        typhoon_name: Optional[str] = None
    ) -> PredictionResult:
        """
        降级预测策略 (线性外推)

        当深度学习模型不可用时，使用简单的线性外推
        """
        logger.info("使用线性外推降级预测")

        # 计算平均移动趋势（使用标准化后的时间排序）
        recent_paths = sorted(historical_paths, key=lambda x: normalize_datetime(x.timestamp))[-5:]

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
        base_time = normalize_datetime(last_point.timestamp)

        predictions = []
        num_points = forecast_hours // 6

        for i in range(1, num_points + 1):
            forecast_time = base_time + timedelta(hours=6 * i)

            pred_lat = last_point.latitude + avg_lat_change * i
            pred_lon = last_point.longitude + avg_lon_change * i

            # 强度预测 (简单的线性外推)
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

        目前复用路径预测的结果，提取强度信息
        """
        # 调用路径预测 (包含强度信息)
        result = await self.predict(
            historical_paths, forecast_hours, typhoon_id, typhoon_name
        )

        return result

    async def predict_from_csv(
        self,
        typhoon_id: str,
        forecast_hours: int = 48,
        csv_path: Optional[Union[str, Path]] = None
    ) -> PredictionResult:
        """
        从CSV文件加载台风数据并执行预测

        Args:
            typhoon_id: 台风编号
            forecast_hours: 预报时效
            csv_path: CSV文件路径，默认使用项目默认路径

        Returns:
            PredictionResult: 预测结果对象
        """
        try:
            logger.info(f"从CSV加载台风 {typhoon_id} 的历史数据")

            # 从CSV加载数据
            csv_loader = CSVDataLoader(csv_path=csv_path)
            historical_paths = csv_loader.load_by_typhoon_id(typhoon_id)

            if not historical_paths:
                logger.error(f"CSV中未找到台风 {typhoon_id} 的数据")
                raise ValueError(f"台风 {typhoon_id} 不存在或数据不足")

            # 获取台风名称
            first_path = historical_paths[0]
            typhoon_name = first_path.typhoon_name_en or first_path.typhoon_name_ch

            logger.info(f"加载了 {len(historical_paths)} 条历史路径数据")

            # 执行预测
            result = await self.predict(
                historical_paths=historical_paths,
                forecast_hours=forecast_hours,
                typhoon_id=typhoon_id,
                typhoon_name=typhoon_name
            )

            return result

        except Exception as e:
            logger.error(f"从CSV预测失败: {e}")
            raise


class InsufficientDataError(Exception):
    """输入数据不足异常"""
    pass


class ModelNotLoadedError(Exception):
    """模型未加载异常"""
    pass
