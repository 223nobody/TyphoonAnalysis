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
import pandas as pd
import torch
import torch.nn as nn

from app.models.typhoon import TyphoonPath
from .models.lstm_model import LSTMTyphoonModel, SimpleTyphoonModel
from .models.transformer_lstm_model import TransformerLSTMModel
from .data.preprocessor import DataPreprocessor, NormalizationParams, FEATURE_COLUMNS
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
        use_simple_model: bool = False,
        use_relative_target: bool = True
    ):
        """
        初始化预测器

        Args:
            model_path: 模型权重文件路径
            device: 计算设备 (cpu/cuda)
            sequence_length: 输入序列长度
            prediction_steps: 预测步数
            use_simple_model: 是否使用简化模型
            use_relative_target: 模型是否输出相对位置变化（V2模型）
        """
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.sequence_length = sequence_length
        self.prediction_steps = prediction_steps
        self.model_path = model_path
        self.use_simple_model = use_simple_model
        self.use_relative_target = use_relative_target

        # 初始化预处理器 - 使用与训练时完全相同的参数
        self.preprocessor = DataPreprocessor(
            sequence_length=sequence_length,
            prediction_steps=prediction_steps
        )

        # 初始化模型
        self.model = None
        self.model_loaded = False
        self.model_input_size = 14  # 默认输入维度

        if model_path and Path(model_path).exists():
            self._load_model()
        else:
            logger.warning(f"模型文件不存在: {model_path}，将使用降级策略")

    def _load_model(self):
        """加载模型权重"""
        try:
            # 尝试加载为TransformerLSTMModel（新架构，14维输入）
            self.model = TransformerLSTMModel(
                input_size=14,  # 与预处理输出维度一致
                hidden_size=256,
                num_lstm_layers=2,
                num_transformer_layers=2,
                num_heads=8,
                output_size=4,
                prediction_steps=self.prediction_steps,
                dropout=0.2
            )
            
            # 加载检查点 - PyTorch 2.6+ 需要设置 weights_only=False
            try:
                checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=False)
            except TypeError:
                # 旧版本PyTorch不支持weights_only参数
                checkpoint = torch.load(self.model_path, map_location=self.device)
            
            # 检查检查点内容，提取模型权重
            if isinstance(checkpoint, dict):
                if 'model_state_dict' in checkpoint:
                    state_dict = checkpoint['model_state_dict']
                else:
                    state_dict = checkpoint
            else:
                state_dict = checkpoint
            
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()
            
            self.model_loaded = True
            self.model_input_size = 14  # 标记模型输入维度
            logger.info(f"TransformerLSTM模型加载成功(14维): {self.model_path}")
            
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
            # 3. 数据预处理 - 使用与训练时完全相同的流程
            input_tensor = self._preprocess(historical_paths)
            input_tensor = input_tensor.to(self.device)

            # 4. 模型推理
            with torch.no_grad():
                model_output = self.model(input_tensor)
                
                # TransformerLSTMModel: (mean, std, confidence)
                predictions_mean, predictions_std, confidence = model_output
                predictions = predictions_mean  # 使用均值作为预测值
                model_name = "TransformerLSTM"

            # 5. 结果后处理
            predictions = predictions.cpu().numpy()
            predictions_std = predictions_std.cpu().numpy()
            model_confidence_raw = confidence.cpu().numpy()

            # 计算置信度
            # 基于预测标准差计算置信度
            avg_std = np.mean(predictions_std[0], axis=1)  # [pred_steps]
            normalized_std = np.clip(avg_std / 5.0, 0.0, 1.0)
            confidence_from_std = 1.0 - normalized_std
            
            # 模型输出的置信度
            raw_model_conf = np.clip(model_confidence_raw[0], 0.0, 1.0)
            
            # 组合置信度
            if np.mean(raw_model_conf) < 0.1:
                confidence = confidence_from_std
            else:
                model_weight = np.linspace(0.6, 0.3, len(confidence_from_std))
                std_weight = 1.0 - model_weight
                confidence = std_weight * confidence_from_std + model_weight * raw_model_conf
            
            # 时间衰减
            time_decay = np.exp(-0.05 * np.arange(len(confidence)))
            confidence = confidence * time_decay
            
            # 确保在合理范围 [0.50, 0.95]
            confidence = np.clip(confidence, 0.50, 0.95)

            # 6. 反归一化 - 将归一化后的预测值转换回原始尺度
            predictions_raw = predictions[0]  # [pred_steps, 4]
            
            if self.use_relative_target:
                # V2模型：预测的是相对位置变化，需要转换为绝对位置
                last_path = max(historical_paths, key=lambda x: normalize_datetime(x.timestamp))
                last_lat_norm = (last_path.latitude - self.preprocessor.norm_params.lat_min) / \
                               (self.preprocessor.norm_params.lat_max - self.preprocessor.norm_params.lat_min)
                last_lon_norm = (last_path.longitude - self.preprocessor.norm_params.lon_min) / \
                               (self.preprocessor.norm_params.lon_max - self.preprocessor.norm_params.lon_min)
                
                # 将相对变化转换为绝对位置（在归一化空间）
                predictions_absolute = predictions_raw.copy()
                predictions_absolute[:, 0] = last_lat_norm + predictions_raw[:, 0]  # lat
                predictions_absolute[:, 1] = last_lon_norm + predictions_raw[:, 1]  # lon
                
                # 裁剪到有效范围
                predictions_clipped = np.clip(predictions_absolute, 0.0, 1.0)
            else:
                # V1模型：预测的是绝对位置的归一化值
                predictions_clipped = np.clip(predictions_raw, 0.0, 1.0)
            
            denorm_predictions = self.preprocessor.denormalize(predictions_clipped)
            
            # 7. 后处理平滑 - 使用指数移动平均减少跳动
            denorm_predictions = self._smooth_predictions(denorm_predictions)

            # 7. 构建预测点
            predicted_points = self._build_prediction_points(
                denorm_predictions,
                confidence,
                historical_paths,
                forecast_hours,
                interval_hours=3
            )

            # 8. 构建结果
            result = PredictionResult(
                typhoon_id=typhoon_id,
                typhoon_name=typhoon_name,
                forecast_hours=forecast_hours,
                base_time=normalize_datetime(last_path.timestamp),
                predictions=predicted_points,
                overall_confidence=float(np.mean(confidence)),
                model_used=model_name,
                is_fallback=False
            )

            return result

        except Exception as e:
            logger.error(f"模型预测失败: {e}")
            import traceback
            traceback.print_exc()
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

        # 按时间排序
        sorted_paths = sorted(historical_paths, key=lambda x: normalize_datetime(x.timestamp))
        
        # 检查时间跨度
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
        
        使用与训练时完全相同的预处理流程
        确保训练和预测的一致性

        Args:
            historical_paths: 历史路径数据

        Returns:
            模型输入Tensor [1, sequence_length, 14]
        """
        # 使用预处理器准备输入
        features_array = self.preprocessor.prepare_prediction_input(historical_paths)
        
        # 转换为Tensor
        input_tensor = torch.FloatTensor(features_array)
        
        return input_tensor

    def _build_prediction_points(
        self,
        predictions: np.ndarray,
        confidence: np.ndarray,
        historical_paths: List[PathData],
        forecast_hours: int,
        interval_hours: int = 3
    ) -> List[PredictedPoint]:
        """
        构建预测点列表

        Args:
            predictions: 预测值数组 [pred_steps, 4]
            confidence: 置信度数组 [pred_steps]
            historical_paths: 历史路径数据
            forecast_hours: 预报时效
            interval_hours: 预测点间隔（小时），默认3小时

        Returns:
            预测点列表
        """
        # 获取最后一个观测点的时间
        last_path = max(historical_paths, key=lambda x: normalize_datetime(x.timestamp))
        base_time = normalize_datetime(last_path.timestamp)

        # 计算需要生成的预测点数
        num_points = min(
            len(predictions),
            forecast_hours // interval_hours
        )

        points = []
        for i in range(num_points):
            forecast_time = base_time + timedelta(hours=interval_hours * (i + 1))

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

    def _smooth_predictions(
        self,
        predictions: np.ndarray,
        alpha: float = 0.0
    ) -> np.ndarray:
        """
        预测结果后处理平滑
        
        使用指数移动平均(EMA)减少预测路径的跳动
        
        Args:
            predictions: 预测值数组 [pred_steps, 4] (lat, lon, pressure, wind)
            alpha: 平滑系数，越大越平滑 (0-1)。默认0.0，完全禁用平滑
            
        Returns:
            平滑后的预测值（当alpha=0时返回原始预测值）
        """
        if len(predictions) <= 1:
            return predictions
        
        # alpha=0时完全禁用平滑，直接返回原始预测值
        if alpha == 0.0:
            return predictions.copy()
        
        smoothed = predictions.copy()
        
        # 指数移动平均平滑
        for i in range(1, len(predictions)):
            smoothed[i, :2] = alpha * smoothed[i-1, :2] + (1 - alpha) * predictions[i, :2]
        
        # 二阶平滑 - 只在极端异常时进行平滑（10度/3小时）
        for i in range(2, len(predictions)):
            # 检查加速度是否过大
            velocity_prev = smoothed[i-1, :2] - smoothed[i-2, :2]
            velocity_curr = smoothed[i, :2] - smoothed[i-1, :2]
            acceleration = np.abs(velocity_curr - velocity_prev)
            
            # 极高阈值10度/3小时，只处理极端异常值
            if np.max(acceleration) > 10.0:
                smoothed[i, :2] = 0.5 * (smoothed[i-1, :2] + predictions[i, :2])
        
        return smoothed

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

        # 计算平均移动趋势
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
        interval_hours = 3  # 每3小时一个预测点
        num_points = forecast_hours // interval_hours

        for i in range(1, num_points + 1):
            forecast_time = base_time + timedelta(hours=interval_hours * i)

            # 计算预测步数因子（相对于6小时的步长）
            step_factor = (interval_hours * i) / 6.0
            pred_lat = last_point.latitude + avg_lat_change * step_factor
            pred_lon = last_point.longitude + avg_lon_change * step_factor

            # 强度预测
            pred_pressure = None
            pred_wind = None
            if last_point.center_pressure is not None:
                pred_pressure = last_point.center_pressure + avg_pressure_change * step_factor
            if last_point.max_wind_speed is not None:
                pred_wind = max(0, last_point.max_wind_speed + avg_wind_change * step_factor)

            # 置信度随时间递减
            conf = max(0.4, 0.85 - i * 0.05)

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
