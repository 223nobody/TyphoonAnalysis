"""
数据集模块

提供PyTorch Dataset实现用于模型训练
"""
import logging
from typing import List, Optional, Callable, Tuple, Union
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset

from app.models.typhoon import TyphoonPath
from .preprocessor import DataPreprocessor
from .csv_loader import CSVDataLoader, TyphoonPathData

logger = logging.getLogger(__name__)

# 定义路径数据类型别名
PathData = Union[TyphoonPath, TyphoonPathData]


class TyphoonDataset(Dataset):
    """
    台风路径数据集

    用于训练/验证/测试的数据加载
    """

    def __init__(
        self,
        typhoon_paths: List[PathData],
        sequence_length: int = 12,
        prediction_steps: int = 8,
        transform: Optional[Callable] = None,
        preprocessor: Optional[DataPreprocessor] = None
    ):
        """
        初始化数据集

        Args:
            typhoon_paths: 台风路径数据列表
            sequence_length: 输入序列长度
            prediction_steps: 预测步数
            transform: 数据变换函数
            preprocessor: 数据预处理器
        """
        self.sequence_length = sequence_length
        self.prediction_steps = prediction_steps
        self.transform = transform

        # 初始化预处理器
        self.preprocessor = preprocessor or DataPreprocessor(
            sequence_length=sequence_length,
            prediction_steps=prediction_steps
        )

        # 构建数据集
        self.samples = self._build_samples(typhoon_paths)

        logger.info(f"数据集初始化完成: {len(self.samples)} 个样本")

    def _build_samples(
        self,
        paths: List[PathData]
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        构建训练样本

        Args:
            paths: 台风路径数据

        Returns:
            样本列表 [(input_seq, target_seq), ...]
        """
        if not paths:
            return []

        # 按台风ID分组
        from collections import defaultdict
        grouped_paths = defaultdict(list)
        for p in paths:
            grouped_paths[p.typhoon_id].append(p)

        samples = []

        for typhoon_id, typhoon_paths in grouped_paths.items():
            # 数据清洗
            cleaned_paths = self.preprocessor.clean_data(typhoon_paths)

            if len(cleaned_paths) < self.sequence_length + self.prediction_steps:
                continue

            # 特征提取
            features = self.preprocessor.extract_features(cleaned_paths)

            # 归一化
            normalized = self.preprocessor.normalize(features)

            # 构建序列
            inputs, targets = self.preprocessor.create_sequences(normalized)

            for i in range(len(inputs)):
                samples.append((inputs[i], targets[i]))

        return samples

    def __len__(self) -> int:
        """返回样本数量"""
        return len(self.samples)

    def __getitem__(
        self,
        idx: int
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        获取单个样本

        Args:
            idx: 样本索引

        Returns:
            (input_sequence, target_sequence)
        """
        input_seq, target_seq = self.samples[idx]

        # 转换为Tensor
        input_tensor = torch.FloatTensor(input_seq)
        target_tensor = torch.FloatTensor(target_seq)

        # 应用变换
        if self.transform:
            input_tensor = self.transform(input_tensor)

        return input_tensor, target_tensor


class TyphoonPredictionDataset(Dataset):
    """
    台风预测数据集 (用于推理)

    仅包含输入序列，不包含目标值
    """

    def __init__(
        self,
        typhoon_paths: List[PathData],
        sequence_length: int = 12,
        preprocessor: Optional[DataPreprocessor] = None
    ):
        """
        初始化数据集

        Args:
            typhoon_paths: 台风路径数据
            sequence_length: 输入序列长度
            preprocessor: 数据预处理器
        """
        self.sequence_length = sequence_length
        self.preprocessor = preprocessor or DataPreprocessor(
            sequence_length=sequence_length
        )

        # 准备输入数据
        self.input_data = self.preprocessor.prepare_prediction_input(typhoon_paths)

    def __len__(self) -> int:
        """返回样本数量"""
        return 1  # 预测数据集只有一个样本

    def __getitem__(self, idx: int) -> torch.Tensor:
        """
        获取输入数据

        Args:
            idx: 样本索引 (始终为0)

        Returns:
            输入Tensor [1, sequence_length, n_features]
        """
        return torch.FloatTensor(self.input_data)


class TyphoonDataCollator:
    """
    数据收集器

    用于DataLoader的collate_fn，处理变长序列
    """

    def __call__(
        self,
        batch: List[Tuple[torch.Tensor, torch.Tensor]]
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        收集批次数据

        Args:
            batch: 样本列表

        Returns:
            (input_batch, target_batch)
        """
        inputs = [item[0] for item in batch]
        targets = [item[1] for item in batch]

        # 堆叠成批次
        input_batch = torch.stack(inputs, dim=0)
        target_batch = torch.stack(targets, dim=0)

        return input_batch, target_batch


class CSVTyphoonDataset(Dataset):
    """
    基于CSV文件的台风路径数据集

    直接从CSV文件加载并构建训练样本
    """

    def __init__(
        self,
        csv_path: Optional[Union[str, Path]] = None,
        sequence_length: int = 12,
        prediction_steps: int = 8,
        transform: Optional[Callable] = None,
        preprocessor: Optional[DataPreprocessor] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ):
        """
        初始化CSV数据集

        Args:
            csv_path: CSV文件路径，默认为项目数据目录下的typhoon_paths_1966_2026.csv
            sequence_length: 输入序列长度
            prediction_steps: 预测步数
            transform: 数据变换函数
            preprocessor: 数据预处理器
            start_year: 起始年份（可选）
            end_year: 结束年份（可选）
        """
        self.sequence_length = sequence_length
        self.prediction_steps = prediction_steps
        self.transform = transform

        # 初始化预处理器
        self.preprocessor = preprocessor or DataPreprocessor(
            sequence_length=sequence_length,
            prediction_steps=prediction_steps
        )

        # 从CSV加载数据
        csv_loader = CSVDataLoader(csv_path=csv_path)

        if start_year is not None and end_year is not None:
            typhoon_paths = csv_loader.load_by_year_range(start_year, end_year)
        elif start_year is not None:
            typhoon_paths = csv_loader.load_by_year(start_year)
        else:
            typhoon_paths = csv_loader.load_all()

        logger.info(f"从CSV加载了 {len(typhoon_paths)} 条路径数据")

        # 构建数据集
        self.samples = self._build_samples(typhoon_paths)

        logger.info(f"CSV数据集初始化完成: {len(self.samples)} 个样本")

    def _build_samples(
        self,
        paths: List[TyphoonPath]
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        构建训练样本

        Args:
            paths: 台风路径数据

        Returns:
            样本列表 [(input_seq, target_seq), ...]
        """
        if not paths:
            return []

        # 按台风ID分组
        from collections import defaultdict
        grouped_paths = defaultdict(list)
        for p in paths:
            grouped_paths[p.typhoon_id].append(p)

        samples = []

        for typhoon_id, typhoon_paths in grouped_paths.items():
            # 数据清洗
            cleaned_paths = self.preprocessor.clean_data(typhoon_paths)

            if len(cleaned_paths) < self.sequence_length + self.prediction_steps:
                continue

            # 特征提取
            features = self.preprocessor.extract_features(cleaned_paths)

            # 归一化
            normalized = self.preprocessor.normalize(features)

            # 构建序列
            inputs, targets = self.preprocessor.create_sequences(normalized)

            for i in range(len(inputs)):
                samples.append((inputs[i], targets[i]))

        return samples

    def __len__(self) -> int:
        """返回样本数量"""
        return len(self.samples)

    def __getitem__(
        self,
        idx: int
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        获取单个样本

        Args:
            idx: 样本索引

        Returns:
            (input_sequence, target_sequence)
        """
        input_seq, target_seq = self.samples[idx]

        # 转换为Tensor
        input_tensor = torch.FloatTensor(input_seq)
        target_tensor = torch.FloatTensor(target_seq)

        # 应用变换
        if self.transform:
            input_tensor = self.transform(input_tensor)

        return input_tensor, target_tensor
