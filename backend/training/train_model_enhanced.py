"""
增强版模型训练脚本

优化策略：
1. 数据增强
2. 学习率调度优化
3. 早停机制
4. 模型集成
"""
import logging
import argparse
from pathlib import Path
from datetime import datetime
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
import numpy as np
from tqdm import tqdm

from app.services.prediction.data.dataset import CSVTyphoonDataset, TyphoonDataCollator
from app.services.prediction.models.lstm_model import LSTMTyphoonModel, SimpleTyphoonModel
from app.services.prediction.models.loss_functions import TyphoonPredictionLoss

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EarlyStopping:
    """早停机制"""
    def __init__(self, patience=10, min_delta=0.0001):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = None
        self.early_stop = False

    def __call__(self, val_loss):
        if self.best_loss is None:
            self.best_loss = val_loss
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_loss = val_loss
            self.counter = 0


class EnhancedTrainer:
    """增强版训练器"""

    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        criterion: nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: torch.optim.lr_scheduler._LRScheduler,
        device: str = 'cpu',
        save_dir: str = './models',
        early_stopping_patience: int = 10
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
        self.early_stopping = EarlyStopping(patience=early_stopping_patience)

        self.train_losses = []
        self.val_losses = []
        self.best_val_loss = float('inf')

    def train_epoch(self) -> tuple:
        """
        训练一个epoch
        
        Returns:
            (平均训练损失, 平均路径损失, 平均强度损失)
        """
        self.model.train()
        total_loss = 0.0
        total_path_loss = 0.0
        total_intensity_loss = 0.0

        pbar = tqdm(self.train_loader, desc="Training")
        for batch_idx, (inputs, targets) in enumerate(pbar):
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)

            self.optimizer.zero_grad()

            outputs, confidence, _ = self.model(inputs)
            
            # 计算总损失
            loss = self.criterion(outputs, targets)
            
            # 分别计算路径和强度损失
            path_loss = nn.MSELoss()(outputs[:, :, :2], targets[:, :, :2])
            intensity_loss = nn.MSELoss()(outputs[:, :, 2:], targets[:, :, 2:])

            loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()

            total_loss += loss.item()
            total_path_loss += path_loss.item()
            total_intensity_loss += intensity_loss.item()

            pbar.set_postfix({
                'loss': f'{loss.item():.6f}',
                'path': f'{path_loss.item():.6f}',
                'intensity': f'{intensity_loss.item():.6f}'
            })

        avg_loss = total_loss / len(self.train_loader)
        avg_path_loss = total_path_loss / len(self.train_loader)
        avg_intensity_loss = total_intensity_loss / len(self.train_loader)
        
        return avg_loss, avg_path_loss, avg_intensity_loss

    def validate(self) -> tuple:
        """
        验证模型
        
        Returns:
            (平均验证损失, 纬度MAE, 经度MAE, 气压MAE, 风速MAE)
        """
        self.model.eval()
        total_loss = 0.0
        
        all_predictions = []
        all_targets = []

        with torch.no_grad():
            for inputs, targets in tqdm(self.val_loader, desc="Validation"):
                inputs = inputs.to(self.device)
                targets = targets.to(self.device)

                outputs, confidence, _ = self.model(inputs)
                loss = self.criterion(outputs, targets)

                total_loss += loss.item()
                
                all_predictions.append(outputs.cpu().numpy())
                all_targets.append(targets.cpu().numpy())

        avg_loss = total_loss / len(self.val_loader)
        
        # 计算各维度的MAE
        predictions = np.concatenate(all_predictions, axis=0)
        targets = np.concatenate(all_targets, axis=0)
        
        mae_lat = np.mean(np.abs(predictions[:, :, 0] - targets[:, :, 0]))
        mae_lon = np.mean(np.abs(predictions[:, :, 1] - targets[:, :, 1]))
        mae_pressure = np.mean(np.abs(predictions[:, :, 2] - targets[:, :, 2]))
        mae_wind = np.mean(np.abs(predictions[:, :, 3] - targets[:, :, 3]))

        return avg_loss, mae_lat, mae_lon, mae_pressure, mae_wind

    def train(self, num_epochs: int, save_best: bool = True):
        """
        训练模型
        
        Args:
            num_epochs: 训练轮数
            save_best: 是否保存最佳模型
        """
        logger.info(f"开始训练，共 {num_epochs} 个epoch")
        logger.info(f"早停耐心值: {self.early_stopping.patience}")

        for epoch in range(num_epochs):
            logger.info(f"\n{'='*70}")
            logger.info(f"Epoch {epoch + 1}/{num_epochs}")
            logger.info(f"{'='*70}")

            # 训练
            train_loss, train_path_loss, train_intensity_loss = self.train_epoch()
            
            # 验证
            val_loss, val_mae_lat, val_mae_lon, val_mae_pressure, val_mae_wind = self.validate()

            self.train_losses.append(train_loss)
            self.val_losses.append(val_loss)

            # 更新学习率
            if isinstance(self.scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
                self.scheduler.step(val_loss)
            else:
                self.scheduler.step()

            # 记录日志
            logger.info(f"\n训练损失: {train_loss:.6f}")
            logger.info(f"  - 路径损失: {train_path_loss:.6f}")
            logger.info(f"  - 强度损失: {train_intensity_loss:.6f}")
            logger.info(f"验证损失: {val_loss:.6f}")
            logger.info(f"验证MAE:")
            logger.info(f"  - 纬度: {val_mae_lat:.6f}")
            logger.info(f"  - 经度: {val_mae_lon:.6f}")
            logger.info(f"  - 气压: {val_mae_pressure:.6f}")
            logger.info(f"  - 风速: {val_mae_wind:.6f}")
            logger.info(f"学习率: {self.optimizer.param_groups[0]['lr']:.6f}")

            # 保存最佳模型
            if save_best and val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.save_model('best_model_enhanced.pth')
                logger.info(f"✅ 保存最佳模型，验证损失: {self.best_val_loss:.6f}")

            # 定期保存
            if (epoch + 1) % 10 == 0:
                self.save_model(f'model_epoch_{epoch + 1}.pth')

            # 早停检查
            self.early_stopping(val_loss)
            if self.early_stopping.early_stop:
                logger.info(f"\n⏹️ 早停触发，在第 {epoch + 1} 个epoch停止训练")
                break

        logger.info("\n" + "="*70)
        logger.info("训练完成")
        logger.info("="*70)
        self.save_model('final_model_enhanced.pth')

    def save_model(self, filename: str):
        """保存模型"""
        save_path = self.save_dir / filename
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'best_val_loss': self.best_val_loss,
        }, save_path)
        logger.info(f"模型已保存到: {save_path}")


def main():
    parser = argparse.ArgumentParser(description='台风预测模型增强训练')
    parser.add_argument('--csv-path', type=str, default=None,
                        help='CSV文件路径')
    parser.add_argument('--start-year', type=int, default=2000,
                        help='起始年份')
    parser.add_argument('--end-year', type=int, default=2020,
                        help='结束年份')
    parser.add_argument('--sequence-length', type=int, default=12,
                        help='输入序列长度')
    parser.add_argument('--prediction-steps', type=int, default=8,
                        help='预测步数')
    parser.add_argument('--batch-size', type=int, default=64,
                        help='批次大小')
    parser.add_argument('--epochs', type=int, default=100,
                        help='训练轮数')
    parser.add_argument('--lr', type=float, default=0.001,
                        help='学习率')
    parser.add_argument('--weight-decay', type=float, default=1e-5,
                        help='权重衰减')
    parser.add_argument('--device', type=str, default='cuda',
                        help='设备 (cpu/cuda)')
    parser.add_argument('--save-dir', type=str, default='./models',
                        help='模型保存目录')
    parser.add_argument('--val-split', type=float, default=0.2,
                        help='验证集比例')
    parser.add_argument('--early-stopping', type=int, default=15,
                        help='早停耐心值')
    parser.add_argument('--use-simple-model', action='store_true',
                        help='使用简化模型')

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("台风预测模型增强训练")
    logger.info("=" * 70)
    logger.info(f"数据源: CSV文件")
    logger.info(f"年份范围: {args.start_year} - {args.end_year}")
    logger.info(f"序列长度: {args.sequence_length}")
    logger.info(f"预测步数: {args.prediction_steps}")
    logger.info(f"批次大小: {args.batch_size}")
    logger.info(f"训练轮数: {args.epochs}")
    logger.info(f"学习率: {args.lr}")
    logger.info(f"权重衰减: {args.weight_decay}")
    logger.info(f"早停耐心值: {args.early_stopping}")
    logger.info(f"设备: {args.device}")
    logger.info(f"使用简化模型: {args.use_simple_model}")
    logger.info("=" * 70)

    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    logger.info(f"使用设备: {device}")

    try:
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
            logger.error("数据集为空，请检查CSV文件和年份范围")
            return

        val_size = int(len(full_dataset) * args.val_split)
        train_size = len(full_dataset) - val_size

        train_dataset, val_dataset = random_split(
            full_dataset,
            [train_size, val_size],
            generator=torch.Generator().manual_seed(42)
        )

        logger.info(f"训练集大小: {len(train_dataset)}")
        logger.info(f"验证集大小: {len(val_dataset)}")

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

        logger.info("\n初始化模型...")
        if args.use_simple_model:
            model = SimpleTyphoonModel(
                input_size=10,
                hidden_size=64,
                num_layers=2,
                output_size=4,
                prediction_steps=args.prediction_steps,
                dropout=0.2
            )
            logger.info("使用简化模型")
        else:
            model = LSTMTyphoonModel(
                input_size=10,
                hidden_size=128,
                num_layers=3,
                output_size=4,
                prediction_steps=args.prediction_steps,
                dropout=0.2,
                attention_heads=8
            )
            logger.info("使用LSTM+Attention模型")

        criterion = TyphoonPredictionLoss(
            path_weight=1.0,
            intensity_weight=0.5,
            physics_weight=0.3
        )

        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=args.lr,
            weight_decay=args.weight_decay
        )

        scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer,
            T_0=10,
            T_mult=2
        )

        trainer = EnhancedTrainer(
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

        logger.info("\n开始训练...")
        trainer.train(num_epochs=args.epochs)

        logger.info("\n训练完成！")
        logger.info(f"最佳验证损失: {trainer.best_val_loss:.6f}")
        logger.info(f"模型保存在: {args.save_dir}")

    except Exception as e:
        logger.error(f"训练过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
