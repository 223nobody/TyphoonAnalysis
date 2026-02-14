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
    """归一化参数 - 必须与训练时使用的参数完全一致"""
    # 位置特征 Min-Max 归一化参数
    lat_min: float = -90.0
    lat_max: float = 90.0
    lon_min: float = -180.0
    lon_max: float = 180.0
    
    # 强度特征 Z-Score 标准化参数
    pressure_mean: float = 1000.0
    pressure_std: float = 50.0
    wind_mean: float = 20.0
    wind_std: float = 15.0
    
    # 移动速度 Z-Score 标准化参数
    moving_speed_mean: float = 15.0
    moving_speed_std: float = 10.0
    
    # 移动方向 Min-Max 归一化参数 [0, 360] -> [0, 1]
    moving_direction_min: float = 0.0
    moving_direction_max: float = 360.0
    
    # 速度特征 Z-Score 标准化参数
    velocity_mean: float = 0.0
    velocity_std: float = 2.0
    
    # 加速度特征 Z-Score 标准化参数
    acceleration_mean: float = 0.0
    acceleration_std: float = 0.5


# 定义路径数据类型别名
PathData = Union[TyphoonPath, Any]

# 固定的14维特征顺序 - 必须与训练时完全一致
# 优化：添加moving_direction，形成双重方向信息
FEATURE_COLUMNS = [
    'latitude',           # 0: 纬度 [-90, 90]
    'longitude',          # 1: 经度 [-180, 180]
    'center_pressure',    # 2: 中心气压
    'max_wind_speed',     # 3: 最大风速
    'moving_speed',       # 4: 移动速度
    'moving_direction',   # 5: 移动方向 [0-360]
    'hour',               # 6: 小时 [0-23]
    'month',              # 7: 月份 [1-12]
    'velocity_lat',       # 8: 纬度速度
    'velocity_lon',       # 9: 经度速度
    'acceleration_lat',   # 10: 纬度加速度
    'acceleration_lon',   # 11: 经度加速度
    'month_sin',          # 12: 月份正弦编码
    'month_cos',          # 13: 月份余弦编码
]


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
        return cleaned_paths

    def extract_features(
        self,
        paths: List[PathData]
    ) -> pd.DataFrame:
        """
        提取特征

        提取特征:
        - 基础特征: lat, lon, pressure, wind, moving_speed
        - 派生特征: velocity, acceleration
        - 时序特征: month, hour, month_sin, month_cos

        Args:
            paths: 路径数据

        Returns:
            特征DataFrame
        """
        if not paths:
            return pd.DataFrame()

        # 按时间排序
        from ..predictor import normalize_datetime
        sorted_paths = sorted(paths, key=lambda x: normalize_datetime(x.timestamp))

        # 基础数据
        data = []
        for p in sorted_paths:
            # 处理moving_direction：转换为数值，空值或无效值设为None
            moving_dir = p.moving_direction
            if moving_dir is not None and moving_dir != '' and moving_dir != '        ':
                try:
                    moving_dir = float(moving_dir)
                except (ValueError, TypeError):
                    moving_dir = None
            else:
                moving_dir = None
            
            data.append({
                'latitude': p.latitude,
                'longitude': p.longitude,
                'center_pressure': p.center_pressure if p.center_pressure is not None else 1000.0,
                'max_wind_speed': p.max_wind_speed if p.max_wind_speed is not None else 0.0,
                'moving_speed': p.moving_speed if p.moving_speed is not None else 15.0,
                'moving_direction': moving_dir,
                'intensity': p.intensity if p.intensity is not None else 0,
                'timestamp': p.timestamp
            })

        df = pd.DataFrame(data)
        
        # 确保moving_direction是数值类型
        df['moving_direction'] = pd.to_numeric(df['moving_direction'], errors='coerce')

        # 计算速度特征 (度/小时)
        df['velocity_lat'] = df['latitude'].diff() / self.time_interval
        df['velocity_lon'] = df['longitude'].diff() / self.time_interval
        # 第一个点的速度设为与第二个点相同
        if len(df) > 1:
            df.loc[0, 'velocity_lat'] = df.loc[1, 'velocity_lat']
            df.loc[0, 'velocity_lon'] = df.loc[1, 'velocity_lon']
        else:
            df.loc[0, 'velocity_lat'] = 0.0
            df.loc[0, 'velocity_lon'] = 0.0
        df['velocity_lat'] = df['velocity_lat'].fillna(0)
        df['velocity_lon'] = df['velocity_lon'].fillna(0)

        # 计算加速度特征
        df['acceleration_lat'] = df['velocity_lat'].diff() / self.time_interval
        df['acceleration_lon'] = df['velocity_lon'].diff() / self.time_interval
        # 第一个点的加速度设为与第二个点相同
        if len(df) > 1:
            df.loc[0, 'acceleration_lat'] = df.loc[1, 'acceleration_lat']
            df.loc[0, 'acceleration_lon'] = df.loc[1, 'acceleration_lon']
        else:
            df.loc[0, 'acceleration_lat'] = 0.0
            df.loc[0, 'acceleration_lon'] = 0.0
        df['acceleration_lat'] = df['acceleration_lat'].fillna(0)
        df['acceleration_lon'] = df['acceleration_lon'].fillna(0)

        # 处理移动方向：如果缺失，用速度分量计算
        # 方向角度：0度=北，90度=东，180度=南，270度=西
        if df['moving_direction'].isna().any():
            # 用速度分量计算方向 (arctan2返回弧度，转换为度)
            calculated_direction = np.degrees(np.arctan2(df['velocity_lon'], df['velocity_lat']))
            # 转换为 [0, 360) 范围
            calculated_direction = (calculated_direction + 360) % 360
            # 填充缺失值
            df['moving_direction'] = df['moving_direction'].fillna(calculated_direction)
        
        # 处理moving_speed缺失值：用速度分量计算
        if df['moving_speed'].isna().any():
            calculated_speed = np.sqrt(df['velocity_lat']**2 + df['velocity_lon']**2) * 111  # 转换为km/h
            df['moving_speed'] = df['moving_speed'].fillna(calculated_speed)

        # 时序编码
        df['month'] = df['timestamp'].apply(lambda x: x.month)
        df['hour'] = df['timestamp'].apply(lambda x: x.hour)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

        return df

    def normalize(
        self,
        features: pd.DataFrame
    ) -> pd.DataFrame:
        """
        特征归一化

        归一化策略:
        - 位置特征 (lat, lon): Min-Max归一化到 [0, 1]
        - 强度特征 (pressure, wind): Z-Score标准化
        - 时间特征 (hour, month): 除以最大值归一化到 [0, 1]
        - 运动特征 (velocity, acceleration): Z-Score标准化
        - 周期特征 (month_sin, month_cos): 已在 [-1, 1] 范围，无需处理

        Args:
            features: 特征数据

        Returns:
            归一化后的数据
        """
        df = features.copy()

        # 1. 位置特征 Min-Max归一化到 [0, 1]
        df['latitude'] = (df['latitude'] - self.norm_params.lat_min) / \
                         (self.norm_params.lat_max - self.norm_params.lat_min)
        df['longitude'] = (df['longitude'] - self.norm_params.lon_min) / \
                          (self.norm_params.lon_max - self.norm_params.lon_min)

        # 2. 强度特征 Z-Score标准化
        df['center_pressure'] = (df['center_pressure'] - self.norm_params.pressure_mean) / \
                                self.norm_params.pressure_std
        df['max_wind_speed'] = (df['max_wind_speed'] - self.norm_params.wind_mean) / \
                               self.norm_params.wind_std

        # 3. 移动速度 Z-Score标准化
        df['moving_speed'] = (df['moving_speed'] - self.norm_params.moving_speed_mean) / \
                             self.norm_params.moving_speed_std
        
        # 4. 移动方向 Min-Max归一化到 [0, 1]
        df['moving_direction'] = (df['moving_direction'] - self.norm_params.moving_direction_min) / \
                                 (self.norm_params.moving_direction_max - self.norm_params.moving_direction_min)

        # 5. 时间特征归一化到 [0, 1]
        df['hour'] = df['hour'] / 23.0
        df['month'] = (df['month'] - 1) / 11.0  # 1-12 -> 0-1

        # 5. 运动特征 Z-Score标准化
        df['velocity_lat'] = (df['velocity_lat'] - self.norm_params.velocity_mean) / \
                             self.norm_params.velocity_std
        df['velocity_lon'] = (df['velocity_lon'] - self.norm_params.velocity_mean) / \
                             self.norm_params.velocity_std
        df['acceleration_lat'] = (df['acceleration_lat'] - self.norm_params.acceleration_mean) / \
                                 self.norm_params.acceleration_std
        df['acceleration_lon'] = (df['acceleration_lon'] - self.norm_params.acceleration_mean) / \
                                 self.norm_params.acceleration_std

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

        # 反归一化位置 (Min-Max)
        result[..., 0] = result[..., 0] * (self.norm_params.lat_max - self.norm_params.lat_min) + \
                         self.norm_params.lat_min
        result[..., 1] = result[..., 1] * (self.norm_params.lon_max - self.norm_params.lon_min) + \
                         self.norm_params.lon_min

        # 反标准化强度 (Z-Score)
        result[..., 2] = result[..., 2] * self.norm_params.pressure_std + \
                         self.norm_params.pressure_mean
        result[..., 3] = result[..., 3] * self.norm_params.wind_std + \
                         self.norm_params.wind_mean

        return result

    def create_sequences(
        self,
        features: pd.DataFrame,
        use_relative_target: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        构建序列样本

        使用滑动窗口构建训练样本
        
        改进：使用相对位置变化作为目标，而不是绝对位置
        这可以让模型学习移动趋势，而不是记忆绝对位置

        Args:
            features: 特征数据
            use_relative_target: 是否使用相对位置变化作为目标

        Returns:
            (input_sequences, target_sequences)
        """
        # 确保所有特征列都存在，缺失的列用0填充
        for col in FEATURE_COLUMNS:
            if col not in features.columns:
                features[col] = 0.0
        
        # 确保所有特征都是数值类型
        for col in FEATURE_COLUMNS:
            features[col] = pd.to_numeric(features[col], errors='coerce').fillna(0.0)

        # 按固定顺序提取特征
        data = features[FEATURE_COLUMNS].values.astype(np.float32)

        inputs = []
        targets = []

        # 滑动窗口
        total_len = self.sequence_length + self.prediction_steps
        for i in range(len(data) - total_len + 1):
            input_seq = data[i:i + self.sequence_length]
            
            # 获取目标序列（绝对位置）
            target_seq_absolute = data[i + self.sequence_length:i + total_len, :4]
            
            if use_relative_target:
                # 使用相对位置变化作为目标
                # 获取输入序列最后一个点的位置作为参考
                last_input_pos = input_seq[-1, :4]
                
                # 计算相对变化
                target_seq = target_seq_absolute - last_input_pos
                
                # 对于经纬度，限制变化范围（避免异常值）
                # 假设3小时内最大移动5度
                target_seq[:, 0] = np.clip(target_seq[:, 0], -0.028, 0.028)  # lat变化
                target_seq[:, 1] = np.clip(target_seq[:, 1], -0.028, 0.028)  # lon变化
            else:
                target_seq = target_seq_absolute

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
        使用与训练时完全相同的预处理流程

        Args:
            paths: 历史路径数据

        Returns:
            模型输入数组 [1, sequence_length, 14]
        """
        # 1. 特征提取
        features = self.extract_features(paths)
        
        if len(features) == 0:
            logger.warning("特征提取结果为空")
            return np.zeros((1, self.sequence_length, 14), dtype=np.float32)

        # 2. 归一化
        normalized = self.normalize(features)

        # 3. 取最近的时间步（最新的sequence_length个点）
        # 注意：不使用create_sequences，因为那会创建滑动窗口，可能使用旧数据
        recent_data = normalized[FEATURE_COLUMNS].tail(self.sequence_length)
        
        if len(recent_data) < self.sequence_length:
            # 数据不足，填充前面
            padding_len = self.sequence_length - len(recent_data)
            padding = pd.DataFrame([[0.0] * len(FEATURE_COLUMNS)] * padding_len, 
                                   columns=FEATURE_COLUMNS)
            recent_data = pd.concat([padding, recent_data], ignore_index=True)
        
        features_array = recent_data[FEATURE_COLUMNS].values.astype(np.float32)
        
        # 添加batch维度 [1, sequence_length, 14]
        return features_array[np.newaxis, ...]

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
                df[col] = df[col].ffill()
                # 对于结尾的缺失值，使用后向填充
                df[col] = df[col].bfill()

        return df
