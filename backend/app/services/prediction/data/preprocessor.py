"""
数据预处理器

提供台风数据的清洗、特征工程和归一化功能
"""
import logging
from typing import List, Dict, Any, Tuple, Optional, Union
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from dataclasses import dataclass

from app.models.typhoon import TyphoonPath

logger = logging.getLogger(__name__)


@dataclass
class NormalizationParams:
    """归一化参数"""
    lat_min: float = -90.0
    lat_max: float = 90.0
    lon_min: float = -180.0
    lon_max: float = 180.0
    pressure_mean: float = 1000.0
    pressure_std: float = 50.0
    wind_mean: float = 20.0
    wind_std: float = 15.0


# 定义路径数据类型别名
PathData = Union[TyphoonPath, Any]


class DataPreprocessor:
    """
    台风数据预处理器

    职责:
    1. 数据清洗
    2. 特征工程
    3. 归一化/标准化
    4. 序列构建
    """

    def __init__(
        self,
        sequence_length: int = 12,
        prediction_steps: int = 8,
        time_interval: int = 6,
        norm_params: Optional[NormalizationParams] = None
    ):
        """
        初始化预处理器

        Args:
            sequence_length: 输入序列长度 (时间步数)
            prediction_steps: 预测步数
            time_interval: 时间间隔(小时)
            norm_params: 归一化参数
        """
        self.sequence_length = sequence_length
        self.prediction_steps = prediction_steps
        self.time_interval = time_interval
        self.norm_params = norm_params or NormalizationParams()

    def clean_data(
        self,
        paths: List[PathData]
    ) -> List[PathData]:
        """
        清洗数据

        清洗规则:
        1. 去除经纬度异常值
        2. 去除时间重复点
        3. 按时间排序
        4. 插值填补缺失值

        Args:
            paths: 原始路径数据

        Returns:
            清洗后的路径数据
        """
        if not paths:
            return []

        # 转换为DataFrame便于处理
        df = self._paths_to_dataframe(paths)

        # 1. 去除经纬度异常值
        df = df[
            (df['latitude'].between(-90, 90)) &
            (df['longitude'].between(-180, 180))
        ]

        # 2. 去除时间重复点 (保留第一个)
        df = df.drop_duplicates(subset=['timestamp'], keep='first')

        # 3. 按时间排序
        df = df.sort_values('timestamp').reset_index(drop=True)

        # 4. 检查并处理缺失值
        df = self._handle_missing_values(df)

        # 转换回TyphoonPath列表
        cleaned_paths = self._dataframe_to_paths(df)

        logger.info(f"数据清洗完成: {len(paths)} -> {len(cleaned_paths)}")
        return cleaned_paths

    def extract_features(
        self,
        paths: List[PathData]
    ) -> pd.DataFrame:
        """
        提取特征

        提取特征:
        - 基础特征: lat, lon, pressure, wind
        - 派生特征: velocity, acceleration
        - 时序特征: month, hour encoding

        Args:
            paths: 路径数据

        Returns:
            特征DataFrame
        """
        if not paths:
            return pd.DataFrame()

        # 按时间排序
        sorted_paths = sorted(paths, key=lambda x: x.timestamp)

        # 基础数据
        data = []
        for p in sorted_paths:
            data.append({
                'latitude': p.latitude,
                'longitude': p.longitude,
                'center_pressure': p.center_pressure if p.center_pressure is not None else 1000.0,
                'max_wind_speed': p.max_wind_speed if p.max_wind_speed is not None else 0.0,
                'timestamp': p.timestamp
            })

        df = pd.DataFrame(data)

        # 计算速度特征 (度/小时)
        df['velocity_lat'] = df['latitude'].diff() / self.time_interval
        df['velocity_lon'] = df['longitude'].diff() / self.time_interval
        df['velocity_lat'] = df['velocity_lat'].fillna(0)
        df['velocity_lon'] = df['velocity_lon'].fillna(0)

        # 计算加速度特征
        df['acceleration_lat'] = df['velocity_lat'].diff() / self.time_interval
        df['acceleration_lon'] = df['velocity_lon'].diff() / self.time_interval
        df['acceleration_lat'] = df['acceleration_lat'].fillna(0)
        df['acceleration_lon'] = df['acceleration_lon'].fillna(0)

        # 时序编码
        df['month'] = df['timestamp'].apply(lambda x: x.month)
        df['hour'] = df['timestamp'].apply(lambda x: x.hour)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

        return df

    def normalize(
        self,
        features: pd.DataFrame
    ) -> pd.DataFrame:
        """
        特征归一化

        归一化策略:
        - 位置特征: Min-Max归一化
        - 强度特征: Z-Score标准化

        Args:
            features: 特征数据

        Returns:
            归一化后的数据
        """
        df = features.copy()

        # 位置特征 Min-Max归一化到 [0, 1]
        df['latitude'] = (df['latitude'] - self.norm_params.lat_min) / \
                         (self.norm_params.lat_max - self.norm_params.lat_min)
        df['longitude'] = (df['longitude'] - self.norm_params.lon_min) / \
                          (self.norm_params.lon_max - self.norm_params.lon_min)

        # 强度特征 Z-Score标准化
        df['center_pressure'] = (df['center_pressure'] - self.norm_params.pressure_mean) / \
                                self.norm_params.pressure_std
        df['max_wind_speed'] = (df['max_wind_speed'] - self.norm_params.wind_mean) / \
                               self.norm_params.wind_std

        return df

    def denormalize(
        self,
        normalized: np.ndarray
    ) -> np.ndarray:
        """
        反归一化

        将归一化后的预测值转换回原始尺度

        Args:
            normalized: 归一化数据 [..., 4] (lat, lon, pressure, wind)

        Returns:
            反归一化后的数据
        """
        result = normalized.copy()

        # 反归一化位置
        result[..., 0] = result[..., 0] * (self.norm_params.lat_max - self.norm_params.lat_min) + \
                         self.norm_params.lat_min
        result[..., 1] = result[..., 1] * (self.norm_params.lon_max - self.norm_params.lon_min) + \
                         self.norm_params.lon_min

        # 反标准化强度
        result[..., 2] = result[..., 2] * self.norm_params.pressure_std + \
                         self.norm_params.pressure_mean
        result[..., 3] = result[..., 3] * self.norm_params.wind_std + \
                         self.norm_params.wind_mean

        return result

    def create_sequences(
        self,
        features: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        构建序列样本

        使用滑动窗口构建训练样本

        Args:
            features: 特征数据

        Returns:
            (input_sequences, target_sequences)
        """
        feature_cols = [
            'latitude', 'longitude',
            'center_pressure', 'max_wind_speed',
            'velocity_lat', 'velocity_lon',
            'acceleration_lat', 'acceleration_lon',
            'month_sin', 'month_cos'
        ]

        data = features[feature_cols].values

        inputs = []
        targets = []

        # 滑动窗口
        total_len = self.sequence_length + self.prediction_steps
        for i in range(len(data) - total_len + 1):
            input_seq = data[i:i + self.sequence_length]
            target_seq = data[i + self.sequence_length:i + total_len, :4]  # 只预测前4个特征

            inputs.append(input_seq)
            targets.append(target_seq)

        if not inputs:
            return np.array([]), np.array([])

        return np.array(inputs), np.array(targets)

    def prepare_prediction_input(
        self,
        paths: List[PathData]
    ) -> np.ndarray:
        """
        准备预测输入

        将历史路径数据转换为模型输入格式

        Args:
            paths: 历史路径数据

        Returns:
            模型输入数组 [1, sequence_length, n_features]
        """
        # 特征提取
        features = self.extract_features(paths)

        # 归一化
        normalized = self.normalize(features)

        # 构建序列
        feature_cols = [
            'latitude', 'longitude',
            'center_pressure', 'max_wind_speed',
            'velocity_lat', 'velocity_lon',
            'acceleration_lat', 'acceleration_lon',
            'month_sin', 'month_cos'
        ]

        # 取最近的时间步
        recent_data = normalized[feature_cols].tail(self.sequence_length)

        # 如果数据不足，进行填充
        if len(recent_data) < self.sequence_length:
            padding_len = self.sequence_length - len(recent_data)
            padding = np.zeros((padding_len, len(feature_cols)))
            sequence = np.vstack([padding, recent_data.values])
        else:
            sequence = recent_data.values

        # 添加batch维度
        return sequence[np.newaxis, ...]

    def _paths_to_dataframe(
        self,
        paths: List[PathData]
    ) -> pd.DataFrame:
        """将路径数据列表转换为DataFrame"""
        data = []
        for p in paths:
            data.append({
                'typhoon_id': p.typhoon_id,
                'timestamp': p.timestamp,
                'latitude': p.latitude,
                'longitude': p.longitude,
                'center_pressure': p.center_pressure,
                'max_wind_speed': p.max_wind_speed,
                'moving_speed': p.moving_speed,
                'moving_direction': p.moving_direction,
                'intensity': p.intensity
            })
        return pd.DataFrame(data)

    def _dataframe_to_paths(
        self,
        df: pd.DataFrame
    ) -> List[PathData]:
        """将DataFrame转换为路径数据列表"""
        from .csv_loader import TyphoonPathData

        paths = []
        for _, row in df.iterrows():
            paths.append(TyphoonPathData(
                typhoon_id=row.get('typhoon_id', ''),
                timestamp=row['timestamp'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                center_pressure=row.get('center_pressure'),
                max_wind_speed=row.get('max_wind_speed'),
                moving_speed=row.get('moving_speed'),
                moving_direction=row.get('moving_direction'),
                intensity=row.get('intensity')
            ))
        return paths

    def _handle_missing_values(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """处理缺失值"""
        # 对于气压和风速，使用线性插值
        for col in ['center_pressure', 'max_wind_speed']:
            if col in df.columns:
                df[col] = df[col].interpolate(method='linear')
                # 对于开头的缺失值，使用前向填充
                df[col] = df[col].fillna(method='ffill')
                # 对于结尾的缺失值，使用后向填充
                df[col] = df[col].fillna(method='bfill')

        return df
