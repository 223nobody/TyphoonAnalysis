"""
模型训练脚本

使用CSV数据源训练台风预测模型
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

from app.services.prediction.data.dataset import CSVTyphoonDataset, TyphoonDataCollator
from app.services.prediction.models.lstm_model import LSTMTyphoonModel
from app.services.prediction.models.loss_functions import TyphoonPredictionLoss

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Trainer:
    """
    模型训练器
    """

    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        criterion: nn.Module,
        optimizer: torch.optim.Optimizer,
        device: str = 'cpu',
        save_dir: str = './models'
    ):
        """
        初始化训练器

        Args:
            model: 模型
            train_loader: 训练数据加载器
            val_loader: 验证数据加载器
            criterion: 损失函数
            optimizer: 优化器
            device: 设备
            save_dir: 模型保存目录
        """
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.criterion = criterion
        self.optimizer = optimizer
        self.device = device
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.train_losses = []
        self.val_losses = []

    def train_epoch(self) -> float:
        """
        训练一个epoch

        Returns:
            平均训练损失
        """
        self.model.train()
        total_loss = 0.0

        for batch_idx, (inputs, targets) in enumerate(self.train_loader):
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)

            self.optimizer.zero_grad()

            outputs, _, _ = self.model(inputs)
            loss = self.criterion(outputs, targets)

            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()

            if batch_idx % 100 == 0:
                logger.info(f"Batch {batch_idx}, Loss: {loss.item():.6f}")

        avg_loss = total_loss / len(self.train_loader)
        return avg_loss

    def validate(self) -> float:
        """
        验证模型

        Returns:
            平均验证损失
        """
        self.model.eval()
        total_loss = 0.0

        with torch.no_grad():
            for inputs, targets in self.val_loader:
                inputs = inputs.to(self.device)
                targets = targets.to(self.device)

                outputs, _, _ = self.model(inputs)
                loss = self.criterion(outputs, targets)

                total_loss += loss.item()

        avg_loss = total_loss / len(self.val_loader)
        return avg_loss

    def train(self, num_epochs: int, save_best: bool = True):
        """
        训练模型

        Args:
            num_epochs: 训练轮数
            save_best: 是否保存最佳模型
        """
        best_val_loss = float('inf')

        logger.info(f"开始训练，共 {num_epochs} 个epoch")

        for epoch in range(num_epochs):
            logger.info(f"\nEpoch {epoch + 1}/{num_epochs}")

            train_loss = self.train_epoch()
            val_loss = self.validate()

            self.train_losses.append(train_loss)
            self.val_losses.append(val_loss)

            logger.info(f"训练损失: {train_loss:.6f}, 验证损失: {val_loss:.6f}")

            if save_best and val_loss < best_val_loss:
                best_val_loss = val_loss
                self.save_model('best_model.pth')
                logger.info(f"保存最佳模型，验证损失: {best_val_loss:.6f}")

            if (epoch + 1) % 10 == 0:
                self.save_model(f'model_epoch_{epoch + 1}.pth')

        logger.info("训练完成")
        self.save_model('final_model.pth')

    def save_model(self, filename: str):
        """
        保存模型

        Args:
            filename: 文件名
        """
        save_path = self.save_dir / filename
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
        }, save_path)
        logger.info(f"模型已保存到: {save_path}")


def main():
    parser = argparse.ArgumentParser(description='台风预测模型训练')
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
    parser.add_argument('--batch-size', type=int, default=32,
                        help='批次大小')
    parser.add_argument('--epochs', type=int, default=50,
                        help='训练轮数')
    parser.add_argument('--lr', type=float, default=0.001,
                        help='学习率')
    parser.add_argument('--device', type=str, default='cpu',
                        help='设备 (cpu/cuda)')
    parser.add_argument('--save-dir', type=str, default='./models',
                        help='模型保存目录')
    parser.add_argument('--val-split', type=float, default=0.2,
                        help='验证集比例')

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("台风预测模型训练")
    logger.info("=" * 60)
    logger.info(f"数据源: CSV文件")
    logger.info(f"年份范围: {args.start_year} - {args.end_year}")
    logger.info(f"序列长度: {args.sequence_length}")
    logger.info(f"预测步数: {args.prediction_steps}")
    logger.info(f"批次大小: {args.batch_size}")
    logger.info(f"训练轮数: {args.epochs}")
    logger.info(f"学习率: {args.lr}")
    logger.info(f"设备: {args.device}")
    logger.info("=" * 60)

    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    logger.info(f"使用设备: {device}")

    try:
        logger.info("加载数据集...")
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

        logger.info("初始化模型...")
        model = LSTMTyphoonModel(
            input_size=10,
            hidden_size=128,
            num_layers=3,
            output_size=4,
            prediction_steps=args.prediction_steps,
            dropout=0.2,
            attention_heads=8
        )

        criterion = TyphoonPredictionLoss(
            path_weight=1.0,
            intensity_weight=0.5,
            physics_weight=0.3
        )

        optimizer = torch.optim.Adam(
            model.parameters(),
            lr=args.lr,
            weight_decay=1e-5
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
            device=str(device),
            save_dir=args.save_dir
        )

        logger.info("开始训练...")
        trainer.train(num_epochs=args.epochs)

        logger.info("训练完成！")
        logger.info(f"模型保存在: {args.save_dir}")

    except Exception as e:
        logger.error(f"训练过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
