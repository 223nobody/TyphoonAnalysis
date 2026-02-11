"""
损失函数模块

提供台风预测专用的损失函数实现
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class TyphoonPredictionLoss(nn.Module):
    """
    台风预测综合损失函数

    组成:
    1. 路径MSE损失 (经纬度)
    2. 强度MSE损失 (气压、风速)
    3. 物理一致性约束损失
    4. 时间加权 (近期预测权重更高)
    """

    def __init__(
        self,
        path_weight: float = 1.0,
        intensity_weight: float = 0.5,
        physics_weight: float = 0.3,
        time_decay: float = 0.1
    ):
        super().__init__()
        self.path_weight = path_weight
        self.intensity_weight = intensity_weight
        self.physics_weight = physics_weight
        self.time_decay = time_decay

    def forward(
        self,
        pred: torch.Tensor,
        target: torch.Tensor
    ) -> torch.Tensor:
        """
        计算损失

        Args:
            pred: 预测值 [batch, pred_steps, 4]
            target: 目标值 [batch, pred_steps, 4]

        Returns:
            total_loss: 综合损失
        """
        batch_size, pred_steps, _ = pred.shape

        # 时间权重 (指数衰减)
        time_weights = torch.exp(
            -torch.arange(pred_steps, device=pred.device) * self.time_decay
        )
        time_weights = time_weights / time_weights.sum()
        time_weights = time_weights.view(1, pred_steps, 1)

        # 1. 路径损失 (经纬度)
        path_loss = F.mse_loss(
            pred[:, :, :2], target[:, :, :2], reduction='none'
        )
        path_loss = (path_loss * time_weights).mean()

        # 2. 强度损失 (气压、风速)
        intensity_loss = F.mse_loss(
            pred[:, :, 2:], target[:, :, 2:], reduction='none'
        )
        intensity_loss = (intensity_loss * time_weights).mean()

        # 3. 物理一致性损失
        physics_loss = self._physics_constraint_loss(pred)

        # 综合损失
        total_loss = (
            self.path_weight * path_loss +
            self.intensity_weight * intensity_loss +
            self.physics_weight * physics_loss
        )

        return total_loss

    def _physics_constraint_loss(self, pred: torch.Tensor) -> torch.Tensor:
        """
        物理约束损失

        约束:
        1. 台风移动速度上限 (约100km/h)
        2. 气压与风速负相关
        3. 强度变化连续性
        """
        # 计算相邻预测点间的移动速度
        lat_diff = pred[:, 1:, 0] - pred[:, :-1, 0]
        lon_diff = pred[:, 1:, 1] - pred[:, :-1, 1]

        # 简化的速度计算 (归一化后的度/时间步)
        speed = torch.sqrt(lat_diff**2 + lon_diff**2)

        # 速度约束 (惩罚过高的移动速度)
        # 阈值: 约5度/6小时 (约100km/h)
        speed_threshold = 5.0
        speed_violation = torch.relu(speed - speed_threshold)
        speed_loss = speed_violation.mean()

        # 气压-风速相关性约束
        # 在归一化空间中，期望负相关
        pressure = pred[:, :, 2]  # 假设气压已归一化
        wind = pred[:, :, 3]      # 假设风速已归一化

        # 计算批次内相关系数
        p_mean = pressure.mean(dim=0, keepdim=True)
        w_mean = wind.mean(dim=0, keepdim=True)

        p_std = pressure.std(dim=0, keepdim=True) + 1e-8
        w_std = wind.std(dim=0, keepdim=True) + 1e-8

        p_norm = (pressure - p_mean) / p_std
        w_norm = (wind - w_mean) / w_std

        correlation = (p_norm * w_norm).mean(dim=0)

        # 惩罚正相关 (期望负相关)
        correlation_loss = torch.relu(correlation).mean()

        # 强度变化连续性约束
        pressure_diff = torch.abs(pred[:, 1:, 2] - pred[:, :-1, 2])
        wind_diff = torch.abs(pred[:, 1:, 3] - pred[:, :-1, 3])

        # 惩罚剧烈变化
        continuity_loss = torch.relu(pressure_diff - 0.5).mean() + \
                         torch.relu(wind_diff - 0.5).mean()

        return speed_loss + correlation_loss + continuity_loss


class PathPredictionLoss(nn.Module):
    """
    纯路径预测损失函数

    仅关注经纬度预测的准确性
    """

    def __init__(self, time_decay: float = 0.1):
        super().__init__()
        self.time_decay = time_decay

    def forward(
        self,
        pred: torch.Tensor,
        target: torch.Tensor
    ) -> torch.Tensor:
        """
        计算路径损失

        Args:
            pred: 预测路径 [batch, pred_steps, 2] (lat, lon)
            target: 目标路径 [batch, pred_steps, 2]

        Returns:
            loss: 路径损失
        """
        batch_size, pred_steps, _ = pred.shape

        # 时间权重
        time_weights = torch.exp(
            -torch.arange(pred_steps, device=pred.device) * self.time_decay
        )
        time_weights = time_weights / time_weights.sum()
        time_weights = time_weights.view(1, pred_steps, 1)

        # Haversine距离近似 (简化版MSE)
        loss = F.mse_loss(pred, target, reduction='none')
        loss = (loss * time_weights).mean()

        return loss


class IntensityPredictionLoss(nn.Module):
    """
    纯强度预测损失函数

    仅关注气压和风速预测的准确性
    """

    def __init__(
        self,
        pressure_weight: float = 0.5,
        wind_weight: float = 0.5,
        time_decay: float = 0.1
    ):
        super().__init__()
        self.pressure_weight = pressure_weight
        self.wind_weight = wind_weight
        self.time_decay = time_decay

    def forward(
        self,
        pred: torch.Tensor,
        target: torch.Tensor
    ) -> torch.Tensor:
        """
        计算强度损失

        Args:
            pred: 预测强度 [batch, pred_steps, 2] (pressure, wind)
            target: 目标强度 [batch, pred_steps, 2]

        Returns:
            loss: 强度损失
        """
        batch_size, pred_steps, _ = pred.shape

        # 时间权重
        time_weights = torch.exp(
            -torch.arange(pred_steps, device=pred.device) * self.time_decay
        )
        time_weights = time_weights / time_weights.sum()
        time_weights = time_weights.view(1, pred_steps, 1)

        # 气压损失
        pressure_loss = F.mse_loss(
            pred[:, :, 0:1], target[:, :, 0:1], reduction='none'
        )
        pressure_loss = (pressure_loss * time_weights).mean()

        # 风速损失
        wind_loss = F.mse_loss(
            pred[:, :, 1:2], target[:, :, 1:2], reduction='none'
        )
        wind_loss = (wind_loss * time_weights).mean()

        # 加权综合
        total_loss = (
            self.pressure_weight * pressure_loss +
            self.wind_weight * wind_loss
        )

        return total_loss
