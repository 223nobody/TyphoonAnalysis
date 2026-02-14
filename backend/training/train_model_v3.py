"""
台风预测模型训练脚本 V3 - 修复版本

修复内容：
1. 统一预处理逻辑，确保训练和预测一致
2. 修复特征维度问题（14维）
3. 修复归一化参数不一致问题
4. 增加更详细的日志和验证
"""
import logging
import argparse
from pathlib import Path
from datetime import datetime
import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, random_split
import numpy as np
from tqdm import tqdm

from app.services.prediction.data.dataset import CSVTyphoonDataset, TyphoonDataCollator
from app.services.prediction.data.preprocessor import DataPreprocessor, NormalizationParams, FEATURE_COLUMNS
from app.services.prediction.models.transformer_lstm_model import TransformerLSTMModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedLoss(nn.Module):
    """
    增强版损失函数
    
    包含：
    1. 负对数似然损失（概率预测）
    2. 物理约束损失
    3. 时序一致性损失
    4. 置信度校准损失
    """
    
    def __init__(
        self,
        path_weight: float = 1.0,
        intensity_weight: float = 0.5,
        physics_weight: float = 0.3,
        temporal_weight: float = 0.2,
        confidence_weight: float = 0.5
    ):
        super().__init__()
        self.path_weight = path_weight
        self.intensity_weight = intensity_weight
        self.physics_weight = physics_weight
        self.temporal_weight = temporal_weight
        self.confidence_weight = confidence_weight
    
    def forward(self, predictions_mean, predictions_std, confidence, targets):
        """
        计算损失
        
        Args:
            predictions_mean: 预测均值 [batch, pred_steps, 4]
            predictions_std: 预测标准差 [batch, pred_steps, 4]
            confidence: 置信度 [batch, pred_steps]
            targets: 目标值 [batch, pred_steps, 4]
        """
        # 1. 负对数似然损失
        nll_loss = 0.5 * torch.log(2 * np.pi * predictions_std ** 2) + \
                   (targets - predictions_mean) ** 2 / (2 * predictions_std ** 2)
        nll_loss = nll_loss.mean()
        
        # 2. 路径损失（经纬度）- 使用归一化后的值
        path_loss = torch.mean((predictions_mean[:, :, :2] - targets[:, :, :2]) ** 2)
        
        # 3. 强度损失（气压、风速）
        intensity_loss = torch.mean((predictions_mean[:, :, 2:] - targets[:, :, 2:]) ** 2)
        
        # 4. 物理约束损失 - 最大移动速度限制
        pred_lats = predictions_mean[:, :, 0]
        pred_lons = predictions_mean[:, :, 1]
        
        # 计算相邻预测点之间的距离
        lat_diff = torch.diff(pred_lats, dim=1)
        lon_diff = torch.diff(pred_lons, dim=1)
        distance = torch.sqrt(lat_diff ** 2 + lon_diff ** 2)
        
        # 惩罚过大的移动（假设6小时最大移动5度，归一化后约为0.028）
        physics_loss = torch.mean(F.relu(distance - 0.028) ** 2)
        
        # 5. 时序一致性损失 - 多阶平滑约束
        # 5.1 一阶平滑：惩罚速度变化（相邻点差异）
        lat_velocity = torch.diff(pred_lats, dim=1)
        lon_velocity = torch.diff(pred_lons, dim=1)
        first_order_smooth = torch.mean(lat_velocity ** 2) + torch.mean(lon_velocity ** 2)
        
        # 5.2 二阶平滑：惩罚加速度变化（速度的差异）
        if pred_lats.shape[1] > 2:
            lat_acceleration = torch.diff(lat_velocity, dim=1)
            lon_acceleration = torch.diff(lon_velocity, dim=1)
            second_order_smooth = torch.mean(lat_acceleration ** 2) + torch.mean(lon_acceleration ** 2)
        else:
            second_order_smooth = torch.tensor(0.0, device=pred_lats.device)
        
        # 5.3 连续性约束：惩罚与历史趋势的不一致
        # 如果历史数据显示向北移动，预测不应突然大幅向南
        # 这里简化处理，只惩罚大的方向变化
        direction_change = torch.abs(torch.diff(lat_velocity, dim=1)) + \
                          torch.abs(torch.diff(lon_velocity, dim=1))
        continuity_loss = torch.mean(F.relu(direction_change - 0.01))  # 允许小的方向变化
        
        temporal_loss = first_order_smooth + 0.5 * second_order_smooth + continuity_loss
        
        # 6. 置信度校准损失
        with torch.no_grad():
            # 计算每个预测步的实际误差 [batch, pred_steps]
            actual_error = torch.mean((predictions_mean[:, :, :2] - targets[:, :, :2]) ** 2, dim=2)
            # 将误差转换为期望的置信度（误差越小，置信度越高）
            target_confidence = torch.exp(-actual_error * 10)  # 缩放因子10
        
        confidence_loss = F.mse_loss(confidence, target_confidence)
        
        # 总损失
        total_loss = (
            nll_loss +
            self.path_weight * path_loss +
            self.intensity_weight * intensity_loss +
            self.physics_weight * physics_loss +
            self.temporal_weight * temporal_loss +
            self.confidence_weight * confidence_loss
        )
        
        return total_loss, {
            'nll': nll_loss.item(),
            'path': path_loss.item(),
            'intensity': intensity_loss.item(),
            'physics': physics_loss.item(),
            'temporal': temporal_loss.item(),
            'confidence': confidence_loss.item(),
            'total': total_loss.item()
        }


class Trainer:
    """模型训练器"""
    
    def __init__(
        self,
        model,
        train_loader,
        val_loader,
        criterion,
        optimizer,
        scheduler,
        device='cpu',
        save_dir='./models',
        early_stopping_patience=15
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.criterion = criterion
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.device = device
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        self.train_losses = []
        self.val_losses = []
        self.best_val_loss = float('inf')
        self.early_stopping_counter = 0
        self.early_stopping_patience = early_stopping_patience
        
        # 记录训练历史
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'val_metrics': [],
            'learning_rate': []
        }
    
    def train_epoch(self):
        """训练一个epoch"""
        self.model.train()
        total_loss = 0
        total_metrics = {
            'nll': 0, 'path': 0, 'intensity': 0,
            'physics': 0, 'temporal': 0, 'confidence': 0
        }
        
        pbar = tqdm(self.train_loader, desc="Training")
        for batch_idx, (inputs, targets) in enumerate(pbar):
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)
            
            self.optimizer.zero_grad()
            
            # 前向传播
            pred_mean, pred_std, confidence = self.model(inputs)
            
            # 计算损失
            loss, metrics = self.criterion(pred_mean, pred_std, confidence, targets)
            
            # 反向传播
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
            for key in total_metrics:
                total_metrics[key] += metrics[key]
            
            pbar.set_postfix({'loss': f'{loss.item():.6f}'})
        
        avg_loss = total_loss / len(self.train_loader)
        avg_metrics = {k: v / len(self.train_loader) for k, v in total_metrics.items()}
        
        return avg_loss, avg_metrics
    
    def validate(self):
        """验证模型"""
        self.model.eval()
        total_loss = 0
        all_predictions = []
        all_targets = []
        all_confidences = []
        
        with torch.no_grad():
            for inputs, targets in tqdm(self.val_loader, desc="Validation"):
                inputs = inputs.to(self.device)
                targets = targets.to(self.device)
                
                pred_mean, pred_std, confidence = self.model(inputs)
                loss, _ = self.criterion(pred_mean, pred_std, confidence, targets)
                
                total_loss += loss.item()
                all_predictions.append(pred_mean.cpu().numpy())
                all_targets.append(targets.cpu().numpy())
                all_confidences.append(confidence.cpu().numpy())
        
        avg_loss = total_loss / len(self.val_loader)
        
        # 计算评估指标
        predictions = np.concatenate(all_predictions, axis=0)
        targets = np.concatenate(all_targets, axis=0)
        confidences = np.concatenate(all_confidences, axis=0)
        
        # 计算MAE（使用归一化后的值）
        mae_lat = np.mean(np.abs(predictions[:, :, 0] - targets[:, :, 0]))
        mae_lon = np.mean(np.abs(predictions[:, :, 1] - targets[:, :, 1]))
        mae_pressure = np.mean(np.abs(predictions[:, :, 2] - targets[:, :, 2]))
        mae_wind = np.mean(np.abs(predictions[:, :, 3] - targets[:, :, 3]))
        avg_confidence = np.mean(confidences)
        
        # 转换为实际度数（近似）
        mae_lat_deg = mae_lat * 180  # 归一化范围是[0,1]，对应实际[-90,90]
        mae_lon_deg = mae_lon * 360  # 归一化范围是[0,1]，对应实际[-180,180]
        
        return avg_loss, {
            'mae_lat': mae_lat,
            'mae_lon': mae_lon,
            'mae_lat_deg': mae_lat_deg,
            'mae_lon_deg': mae_lon_deg,
            'mae_pressure': mae_pressure,
            'mae_wind': mae_wind,
            'avg_confidence': avg_confidence
        }
    
    def train(self, num_epochs):
        """
        训练模型
        
        Args:
            num_epochs: 总训练轮数
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"开始训练，总轮数: {num_epochs}")
        logger.info(f"{'='*70}")
        
        for epoch in range(num_epochs):
            logger.info(f"\nEpoch {epoch + 1}/{num_epochs}")
            
            # 训练
            train_loss, train_metrics = self.train_epoch()
            
            # 验证
            val_loss, val_metrics = self.validate()
            
            # 记录历史
            self.train_losses.append(train_loss)
            self.val_losses.append(val_loss)
            self.history['train_loss'].append(train_loss)
            self.history['val_loss'].append(val_loss)
            self.history['val_metrics'].append(val_metrics)
            self.history['learning_rate'].append(self.optimizer.param_groups[0]['lr'])
            
            # 更新学习率
            if isinstance(self.scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
                self.scheduler.step(val_loss)
            else:
                self.scheduler.step()
            
            # 记录日志
            logger.info(f"训练损失: {train_loss:.6f}")
            logger.info(f"验证损失: {val_loss:.6f}")
            logger.info(f"验证指标: lat={val_metrics['mae_lat_deg']:.2f}°, "
                       f"lon={val_metrics['mae_lon_deg']:.2f}°, "
                       f"pressure={val_metrics['mae_pressure']:.4f}, "
                       f"wind={val_metrics['mae_wind']:.4f}, "
                       f"conf={val_metrics['avg_confidence']:.4f}")
            
            # 保存最佳模型
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.save_model('best_model.pth')
                self.early_stopping_counter = 0
                logger.info(f"✅ 保存最佳模型")
            else:
                self.early_stopping_counter += 1
            
            # 早停检查
            if self.early_stopping_counter >= self.early_stopping_patience:
                logger.info(f"⏹️ 早停触发，连续{self.early_stopping_patience}轮未改善")
                break
            
            # 定期保存
            if (epoch + 1) % 10 == 0:
                self.save_model(f'model_epoch_{epoch + 1}.pth')
        
        logger.info("\n训练完成")
        self.save_model('final_model.pth')
        self.save_history()
    
    def save_model(self, filename):
        """保存模型"""
        save_path = self.save_dir / filename
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'best_val_loss': self.best_val_loss,
            'history': self.history,
            'feature_columns': FEATURE_COLUMNS,
            'normalization_params': {
                'lat_min': -90.0,
                'lat_max': 90.0,
                'lon_min': -180.0,
                'lon_max': 180.0,
                'pressure_mean': 1000.0,
                'pressure_std': 50.0,
                'wind_mean': 20.0,
                'wind_std': 15.0,
            }
        }, save_path)
        logger.info(f"模型已保存到: {save_path}")
    
    def save_history(self):
        """保存训练历史"""
        history_path = self.save_dir / 'training_history.json'
        # 转换numpy类型为Python原生类型
        def convert_to_native(obj):
            if isinstance(obj, dict):
                return {k: convert_to_native(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_native(item) for item in obj]
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        history_native = convert_to_native(self.history)
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history_native, f, indent=2, ensure_ascii=False)
        logger.info(f"训练历史已保存到: {history_path}")


def main():
    parser = argparse.ArgumentParser(description='台风预测模型训练 V3 - 修复版本')
    parser.add_argument('--csv-path', type=str, default=None)
    parser.add_argument('--start-year', type=int, default=2000)
    parser.add_argument('--end-year', type=int, default=2020)
    parser.add_argument('--sequence-length', type=int, default=12)
    parser.add_argument('--prediction-steps', type=int, default=8)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--lr', type=float, default=0.001)
    parser.add_argument('--weight-decay', type=float, default=1e-5)
    parser.add_argument('--device', type=str, default='cuda')
    parser.add_argument('--save-dir', type=str, default='./models')
    parser.add_argument('--val-split', type=float, default=0.2)
    parser.add_argument('--early-stopping', type=int, default=15)
    
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("台风预测模型训练 V3 - 修复版本")
    logger.info("=" * 70)
    logger.info(f"特征维度: {len(FEATURE_COLUMNS)}")
    logger.info(f"特征列表: {FEATURE_COLUMNS}")
    
    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    logger.info(f"使用设备: {device}")
    
    try:
        # 加载数据
        logger.info("\n加载数据集...")
        full_dataset = CSVTyphoonDataset(
            csv_path=args.csv_path,
            sequence_length=args.sequence_length,
            prediction_steps=args.prediction_steps,
            start_year=args.start_year,
            end_year=args.end_year
        )
        
        logger.info(f"数据集大小: {len(full_dataset)} 个样本")
        
        if len(full_dataset) == 0:
            logger.error("数据集为空")
            return
        
        # 划分数据集
        val_size = int(len(full_dataset) * args.val_split)
        train_size = len(full_dataset) - val_size
        
        train_dataset, val_dataset = random_split(
            full_dataset,
            [train_size, val_size],
            generator=torch.Generator().manual_seed(42)
        )
        
        logger.info(f"训练集: {len(train_dataset)}, 验证集: {len(val_dataset)}")
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=args.batch_size,
            shuffle=True,
            collate_fn=TyphoonDataCollator(),
            num_workers=0
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=args.batch_size,
            shuffle=False,
            collate_fn=TyphoonDataCollator(),
            num_workers=0
        )
        
        # 初始化模型
        logger.info("\n初始化模型...")
        model = TransformerLSTMModel(
            input_size=14,  # 14维特征
            hidden_size=256,
            num_lstm_layers=2,
            num_transformer_layers=2,
            num_heads=8,
            output_size=4,
            prediction_steps=args.prediction_steps,
            dropout=0.2
        )
        
        # 统计模型参数量
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        logger.info(f"模型总参数量: {total_params:,}")
        logger.info(f"可训练参数量: {trainable_params:,}")
        
        criterion = EnhancedLoss(
            path_weight=1.0,
            intensity_weight=0.5,
            physics_weight=0.3,
            temporal_weight=0.2,
            confidence_weight=0.5
        )
        
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=args.lr,
            weight_decay=args.weight_decay
        )
        
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode='min',
            factor=0.5,
            patience=5,
            verbose=True
        )
        
        trainer = Trainer(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            criterion=criterion,
            optimizer=optimizer,
            scheduler=scheduler,
            device=str(device),
            save_dir=args.save_dir,
            early_stopping_patience=args.early_stopping
        )
        
        # 开始训练
        logger.info("\n开始训练...")
        trainer.train(num_epochs=args.epochs)
        
        logger.info("\n训练完成！")
        logger.info(f"最佳验证损失: {trainer.best_val_loss:.6f}")
        
    except Exception as e:
        logger.error(f"训练过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
