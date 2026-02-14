"""
高级预测功能模块

提供任意起点预测和滚动预测功能
"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import torch
import copy

from app.models.typhoon import TyphoonPath
from .predictor import TyphoonPredictor, PredictionResult, PredictedPoint, PathData
from .data.preprocessor import DataPreprocessor

logger = logging.getLogger(__name__)


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
class RollingPredictionConfig:
    """滚动预测配置"""
    initial_forecast_hours: int = 48  # 初始预测时长
    update_interval_hours: int = 6    # 更新间隔（每6小时更新一次）
    max_iterations: int = 10          # 最大滚动次数
    confidence_threshold: float = 0.5  # 置信度阈值，低于此值停止滚动


@dataclass
class ArbitraryStartPoint:
    """任意起点数据类"""
    timestamp: datetime
    latitude: float
    longitude: float
    center_pressure: Optional[float] = None
    max_wind_speed: Optional[float] = None
    
    def to_path_data(self) -> PathData:
        """转换为PathData格式"""
        class MockPathData:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        return MockPathData(
            timestamp=self.timestamp,
            latitude=self.latitude,
            longitude=self.longitude,
            center_pressure=self.center_pressure,
            max_wind_speed=self.max_wind_speed,
            typhoon_id="",
            moving_speed=None,
            moving_direction=None,
            intensity=None
        )


class AdvancedTyphoonPredictor(TyphoonPredictor):
    """
    高级台风预测器
    
    扩展功能:
    1. 任意起点预测 - 从指定时间和位置开始预测
    2. 滚动预测 - 持续更新预测结果
    """

    async def predict_from_arbitrary_start(
        self,
        historical_paths: List[PathData],
        start_point: ArbitraryStartPoint,
        forecast_hours: int = 48,
        typhoon_id: str = "",
        typhoon_name: Optional[str] = None,
        include_history: bool = True
    ) -> PredictionResult:
        """
        从任意起点进行预测
        
        原理:
        1. 使用历史数据构建模型输入序列
        2. 将起点作为序列的最后一个点
        3. 基于这个序列预测未来路径
        
        Args:
            historical_paths: 历史路径数据（用于构建输入特征）
            start_point: 预测起点（时间、位置、强度）
            forecast_hours: 预报时效
            typhoon_id: 台风编号
            typhoon_name: 台风名称
            include_history: 是否在结果中包含历史路径
            
        Returns:
            PredictionResult: 预测结果
        """
        logger.info(f"执行任意起点预测，起点时间: {start_point.timestamp}")
        
        # 1. 准备扩展的历史数据（包含起点）
        extended_paths = self._prepare_extended_paths(
            historical_paths, 
            start_point,
            include_history=include_history
        )
        
        # 2. 验证数据
        if len(extended_paths) < 3:
            raise ValueError("数据不足，需要至少3个时间点（包括起点）")
        
        # 3. 使用基础预测方法
        result = await self.predict(
            historical_paths=extended_paths,
            forecast_hours=forecast_hours,
            typhoon_id=typhoon_id,
            typhoon_name=typhoon_name
        )
        
        # 4. 如果模型预测失败（验证不通过等），使用降级策略
        if result is None:
            logger.warning("模型预测失败，使用降级策略进行任意起点预测")
            result = await self._fallback_prediction(
                historical_paths=extended_paths,
                forecast_hours=forecast_hours,
                typhoon_id=typhoon_id,
                typhoon_name=typhoon_name
            )
        
        # 5. 调整预测结果的base_time为指定的起点时间
        result.base_time = start_point.timestamp
        
        # 6. 重新计算预测点的时间（每3小时一个点）
        interval_hours = 3
        for i, point in enumerate(result.predictions):
            point.forecast_time = start_point.timestamp + timedelta(hours=interval_hours * (i + 1))
        
        # 7. 标记为任意起点预测
        result.model_used = f"{result.model_used}-ArbitraryStart"
        
        return result

    def _prepare_extended_paths(
        self,
        historical_paths: List[PathData],
        start_point: ArbitraryStartPoint,
        include_history: bool = True
    ) -> List[PathData]:
        """
        准备扩展的路径数据
        
        策略:
        - 如果历史数据足够（>= sequence_length），截取最近的序列
        - 如果历史数据不足，用起点填充
        - 将起点作为最后一个点
        """
        # 标准化起点时间
        start_timestamp = normalize_datetime(start_point.timestamp)
        
        # 按时间排序历史数据
        sorted_history = sorted(historical_paths, key=lambda x: normalize_datetime(x.timestamp))
        
        # 过滤掉起点之后的数据（标准化时间后比较）
        history_before_start = [
            p for p in sorted_history 
            if normalize_datetime(p.timestamp) <= start_timestamp
        ]
        
        # 创建起点的PathData
        start_path = start_point.to_path_data()
        
        if not history_before_start:
            # 没有历史数据，使用起点重复填充
            logger.warning("没有可用的历史数据，使用起点填充")
            extended = [copy.deepcopy(start_path) for _ in range(self.sequence_length)]
            # 调整时间使其形成序列（保持与起点相同的时区）
            for i, path in enumerate(extended):
                path.timestamp = start_timestamp - timedelta(hours=6 * (len(extended) - i - 1))
            return extended
        
        # 合并历史数据和起点
        extended = history_before_start + [start_path]
        
        # 如果数据太多，截取最近的 sequence_length 个
        if len(extended) > self.sequence_length:
            extended = extended[-self.sequence_length:]
        
        # 如果数据不足，向前填充
        # 确保填充后的时间跨度至少为12小时（满足验证要求）
        min_required_span_hours = 12
        while len(extended) < self.sequence_length:
            # 复制第一个点并调整时间
            first_point = extended[0]
            filler = copy.deepcopy(first_point)
            # 标准化时间后进行计算
            first_timestamp = normalize_datetime(first_point.timestamp)
            filler.timestamp = first_timestamp - timedelta(hours=6)
            extended.insert(0, filler)
        
        # 额外检查：确保时间跨度至少为12小时
        if extended:
            first_time = normalize_datetime(extended[0].timestamp)
            last_time = normalize_datetime(extended[-1].timestamp)
            current_span = (last_time - first_time).total_seconds() / 3600
            if current_span < min_required_span_hours:
                # 需要额外填充以满足时间跨度要求
                additional_points_needed = int((min_required_span_hours - current_span) / 6) + 1
                for i in range(additional_points_needed):
                    first_point = extended[0]
                    filler = copy.deepcopy(first_point)
                    first_timestamp = normalize_datetime(first_point.timestamp)
                    filler.timestamp = first_timestamp - timedelta(hours=6)
                    extended.insert(0, filler)
        
        return extended

    async def rolling_prediction(
        self,
        initial_paths: List[PathData],
        config: RollingPredictionConfig,
        typhoon_id: str = "",
        typhoon_name: Optional[str] = None
    ) -> List[PredictionResult]:
        """
        滚动预测
        
        原理:
        1. 基于当前数据进行初始预测
        2. 模拟时间推移，将预测结果作为新的"观测"数据
        3. 重新进行预测
        4. 重复直到达到最大迭代次数或置信度低于阈值
        
        应用场景:
        - 评估预测稳定性
        - 模拟实时更新场景
        - 长期趋势分析
        
        Args:
            initial_paths: 初始历史路径数据
            config: 滚动预测配置
            typhoon_id: 台风编号
            typhoon_name: 台风名称
            
        Returns:
            List[PredictionResult]: 每次迭代的预测结果列表
        """
        results = []
        current_paths = list(initial_paths)
        current_time = max(normalize_datetime(p.timestamp) for p in initial_paths)
        
        for iteration in range(config.max_iterations):
            # 1. 执行预测
            result = await self.predict(
                historical_paths=current_paths,
                forecast_hours=config.initial_forecast_hours,
                typhoon_id=typhoon_id,
                typhoon_name=typhoon_name
            )
            
            # 2. 检查置信度
            if result.overall_confidence < config.confidence_threshold:
                logger.warning(f"置信度 {result.overall_confidence:.2f} 低于阈值，停止滚动")
                break
            
            # 3. 保存结果
            results.append(result)
            
            # 4. 模拟时间推移，更新数据
            current_time += timedelta(hours=config.update_interval_hours)
            
            # 5. 将预测结果中的对应时间点作为新的"观测"数据
            new_observation = self._extract_prediction_at_time(
                result, 
                current_time
            )
            
            if new_observation is None:
                break
            
            # 6. 更新当前路径数据
            current_paths.append(new_observation)
            
            # 7. 保持数据长度在合理范围内（避免无限增长）
            if len(current_paths) > self.sequence_length * 2:
                current_paths = current_paths[-self.sequence_length:]
        
        return results

    def _extract_prediction_at_time(
        self,
        prediction_result: PredictionResult,
        target_time: datetime
    ) -> Optional[PathData]:
        """
        从预测结果中提取指定时间的预测点作为观测数据
        """
        # 标准化目标时间
        normalized_target = normalize_datetime(target_time)
        
        for point in prediction_result.predictions:
            # 标准化预测点时间
            normalized_forecast = normalize_datetime(point.forecast_time)
            # 允许5分钟的误差
            time_diff = abs((normalized_forecast - normalized_target).total_seconds())
            if time_diff < 300:  # 5分钟 = 300秒
                # 转换为PathData
                class MockPathData:
                    def __init__(self, **kwargs):
                        for k, v in kwargs.items():
                            setattr(self, k, v)
                
                return MockPathData(
                    timestamp=point.forecast_time,
                    latitude=point.latitude,
                    longitude=point.longitude,
                    center_pressure=point.center_pressure,
                    max_wind_speed=point.max_wind_speed,
                    typhoon_id=prediction_result.typhoon_id,
                    moving_speed=None,
                    moving_direction=None,
                    intensity=None
                )
        
        return None

    async def predict_with_virtual_observations(
        self,
        historical_paths: List[PathData],
        virtual_observations: List[ArbitraryStartPoint],
        forecast_hours: int = 48,
        typhoon_id: str = "",
        typhoon_name: Optional[str] = None
    ) -> PredictionResult:
        """
        基于虚拟观测点进行预测
        
        应用场景:
        - 假设情景分析（"如果台风转向..."）
        - 多机构预报对比
        - 人工干预预测
        
        Args:
            historical_paths: 真实历史路径数据
            virtual_observations: 虚拟观测点列表（将替代真实数据）
            forecast_hours: 预报时效
            typhoon_id: 台风编号
            typhoon_name: 台风名称
            
        Returns:
            PredictionResult: 预测结果
        """
        # 将虚拟观测点转换为PathData
        virtual_paths = [vo.to_path_data() for vo in virtual_observations]
        
        # 合并真实历史和虚拟观测点
        # 策略：用虚拟观测点替换对应时间的真实数据
        combined_paths = self._merge_virtual_observations(
            historical_paths, 
            virtual_paths
        )
        
        # 执行预测
        result = await self.predict(
            historical_paths=combined_paths,
            forecast_hours=forecast_hours,
            typhoon_id=typhoon_id,
            typhoon_name=typhoon_name
        )
        
        result.model_used = f"{result.model_used}-VirtualObs"
        return result

    def _merge_virtual_observations(
        self,
        historical_paths: List[PathData],
        virtual_paths: List[PathData]
    ) -> List[PathData]:
        """
        合并真实历史和虚拟观测点
        
        策略：虚拟观测点优先级高于真实数据
        """
        # 创建时间到虚拟观测点的映射
        virtual_map = {}
        for vp in virtual_paths:
            key = vp.timestamp.strftime("%Y-%m-%d %H:%M")
            virtual_map[key] = vp
        
        # 过滤掉与虚拟观测点冲突的真实数据
        filtered_history = [
            hp for hp in historical_paths
            if hp.timestamp.strftime("%Y-%m-%d %H:%M") not in virtual_map
        ]
        
        # 合并并排序
        combined = filtered_history + virtual_paths
        combined.sort(key=lambda x: x.timestamp)
        
        return combined


# 便捷函数
async def predict_from_arbitrary_start(
    historical_paths: List[PathData],
    start_time: datetime,
    start_latitude: float,
    start_longitude: float,
    start_pressure: Optional[float] = None,
    start_wind_speed: Optional[float] = None,
    forecast_hours: int = 48,
    typhoon_id: str = "",
    typhoon_name: Optional[str] = None,
    model_path: Optional[str] = None
) -> PredictionResult:
    """
    便捷函数：从任意起点预测
    
    示例:
        result = await predict_from_arbitrary_start(
            historical_paths=paths,
            start_time=datetime(2026, 1, 15, 12, 0),
            start_latitude=20.5,
            start_longitude=125.8,
            forecast_hours=72
        )
    """
    predictor = AdvancedTyphoonPredictor(model_path=model_path)
    
    start_point = ArbitraryStartPoint(
        timestamp=start_time,
        latitude=start_latitude,
        longitude=start_longitude,
        center_pressure=start_pressure,
        max_wind_speed=start_wind_speed
    )
    
    return await predictor.predict_from_arbitrary_start(
        historical_paths=historical_paths,
        start_point=start_point,
        forecast_hours=forecast_hours,
        typhoon_id=typhoon_id,
        typhoon_name=typhoon_name
    )


async def rolling_prediction(
    initial_paths: List[PathData],
    initial_forecast_hours: int = 48,
    update_interval_hours: int = 6,
    max_iterations: int = 10,
    typhoon_id: str = "",
    typhoon_name: Optional[str] = None,
    model_path: Optional[str] = None
) -> List[PredictionResult]:
    """
    便捷函数：滚动预测
    
    示例:
        results = await rolling_prediction(
            initial_paths=paths,
            initial_forecast_hours=48,
            update_interval_hours=6,
            max_iterations=5
        )
    """
    predictor = AdvancedTyphoonPredictor(model_path=model_path)
    
    config = RollingPredictionConfig(
        initial_forecast_hours=initial_forecast_hours,
        update_interval_hours=update_interval_hours,
        max_iterations=max_iterations
    )
    
    return await predictor.rolling_prediction(
        initial_paths=initial_paths,
        config=config,
        typhoon_id=typhoon_id,
        typhoon_name=typhoon_name
    )
