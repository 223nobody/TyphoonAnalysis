"""
模型评估脚本

用于评估训练好的模型性能，检查置信度和预测效果
"""
import logging
import argparse
from pathlib import Path
import torch
import numpy as np
from torch.utils.data import DataLoader

from app.services.prediction.data.dataset import CSVTyphoonDataset, TyphoonDataCollator
from app.services.prediction.models.lstm_model import LSTMTyphoonModel
from app.services.prediction.models.loss_functions import TyphoonPredictionLoss
from app.services.prediction.data.preprocessor import DataPreprocessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def evaluate_model(model_path: str, device: str = 'cpu'):
    """
    评估模型性能
    
    Args:
        model_path: 模型文件路径
        device: 计算设备
    """
    logger.info("=" * 70)
    logger.info("模型评估")
    logger.info("=" * 70)
    
    device = torch.device(device if torch.cuda.is_available() else 'cpu')
    logger.info(f"使用设备: {device}")
    
    # 1. 加载模型
    logger.info(f"\n加载模型: {model_path}")
    try:
        checkpoint = torch.load(model_path, map_location=device)
        
        # 检查保存的内容
        logger.info(f"检查点内容: {list(checkpoint.keys())}")
        
        if 'train_losses' in checkpoint:
            logger.info(f"训练损失历史: {checkpoint['train_losses']}")
        if 'val_losses' in checkpoint:
            logger.info(f"验证损失历史: {checkpoint['val_losses']}")
            
    except Exception as e:
        logger.error(f"加载模型失败: {e}")
        return
    
    # 2. 创建验证数据集
    logger.info("\n创建验证数据集...")
    try:
        val_dataset = CSVTyphoonDataset(
            start_year=2018,  # 使用2018-2020年作为验证集
            end_year=2020,
            sequence_length=12,
            prediction_steps=8
        )
        
        if len(val_dataset) == 0:
            logger.error("验证数据集为空")
            return
            
        logger.info(f"验证数据集大小: {len(val_dataset)} 个样本")
        
    except Exception as e:
        logger.error(f"创建数据集失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 创建数据加载器
    val_loader = DataLoader(
        val_dataset,
        batch_size=32,
        shuffle=False,
        collate_fn=TyphoonDataCollator(),
        num_workers=0
    )
    
    # 4. 初始化模型
    logger.info("\n初始化模型...")
    model = LSTMTyphoonModel(
        input_size=10,
        hidden_size=128,
        num_layers=3,
        output_size=4,
        prediction_steps=8,
        dropout=0.2,
        attention_heads=8
    ).to(device)
    
    # 加载模型权重
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
        logger.info("✅ 模型权重加载成功")
    else:
        logger.warning("⚠️ 检查点中没有模型权重")
        return
    
    model.eval()
    
    # 5. 评估模型
    logger.info("\n开始评估...")
    criterion = TyphoonPredictionLoss(
        path_weight=1.0,
        intensity_weight=0.5,
        physics_weight=0.3
    )
    
    total_loss = 0.0
    total_samples = 0
    all_predictions = []
    all_targets = []
    
    with torch.no_grad():
        for batch_idx, (inputs, targets) in enumerate(val_loader):
            inputs = inputs.to(device)
            targets = targets.to(device)
            
            # 前向传播
            outputs, confidence, _ = model(inputs)
            
            # 计算损失
            loss = criterion(outputs, targets)
            
            # 检查是否有NaN
            if torch.isnan(loss):
                logger.warning(f"批次 {batch_idx}: 损失为NaN，跳过")
                continue
            
            total_loss += loss.item() * inputs.size(0)
            total_samples += inputs.size(0)
            
            # 保存预测和目标
            all_predictions.append(outputs.cpu().numpy())
            all_targets.append(targets.cpu().numpy())
            
            if batch_idx % 10 == 0:
                logger.info(f"批次 {batch_idx}/{len(val_loader)}, 损失: {loss.item():.6f}")
    
    # 6. 计算平均损失
    if total_samples > 0:
        avg_loss = total_loss / total_samples
        logger.info(f"\n✅ 评估完成")
        logger.info(f"平均验证损失: {avg_loss:.6f}")
        logger.info(f"有效样本数: {total_samples}")
    else:
        logger.error("❌ 没有有效样本，无法计算损失")
        return
    
    # 7. 分析预测结果
    if all_predictions and all_targets:
        predictions = np.concatenate(all_predictions, axis=0)
        targets = np.concatenate(all_targets, axis=0)
        
        logger.info("\n" + "=" * 70)
        logger.info("预测结果分析")
        logger.info("=" * 70)
        
        # 计算各维度的MAE
        mae_lat = np.mean(np.abs(predictions[:, :, 0] - targets[:, :, 0]))
        mae_lon = np.mean(np.abs(predictions[:, :, 1] - targets[:, :, 1]))
        mae_pressure = np.mean(np.abs(predictions[:, :, 2] - targets[:, :, 2]))
        mae_wind = np.mean(np.abs(predictions[:, :, 3] - targets[:, :, 3]))
        
        logger.info(f"\n平均绝对误差 (MAE):")
        logger.info(f"  纬度: {mae_lat:.4f}°")
        logger.info(f"  经度: {mae_lon:.4f}°")
        logger.info(f"  气压: {mae_pressure:.2f} hPa")
        logger.info(f"  风速: {mae_wind:.2f} m/s")
        
        # 计算RMSE
        rmse_lat = np.sqrt(np.mean((predictions[:, :, 0] - targets[:, :, 0])**2))
        rmse_lon = np.sqrt(np.mean((predictions[:, :, 1] - targets[:, :, 1])**2))
        
        logger.info(f"\n均方根误差 (RMSE):")
        logger.info(f"  纬度: {rmse_lat:.4f}°")
        logger.info(f"  经度: {rmse_lon:.4f}°")
        
        # 分析预测值范围
        logger.info(f"\n预测值统计:")
        logger.info(f"  纬度范围: [{predictions[:, :, 0].min():.2f}, {predictions[:, :, 0].max():.2f}]")
        logger.info(f"  经度范围: [{predictions[:, :, 1].min():.2f}, {predictions[:, :, 1].max():.2f}]")
        logger.info(f"  气压范围: [{predictions[:, :, 2].min():.2f}, {predictions[:, :, 2].max():.2f}]")
        logger.info(f"  风速范围: [{predictions[:, :, 3].min():.2f}, {predictions[:, :, 3].max():.2f}]")
        
        # 检查是否有异常值
        if np.isnan(predictions).any():
            logger.warning(f"⚠️ 预测结果中包含 {np.isnan(predictions).sum()} 个NaN值")
        if np.isinf(predictions).any():
            logger.warning(f"⚠️ 预测结果中包含 {np.isinf(predictions).sum()} 个Inf值")
    
    logger.info("\n" + "=" * 70)
    logger.info("评估完成")
    logger.info("=" * 70)


def main():
    parser = argparse.ArgumentParser(description='模型评估')
    parser.add_argument('--model-path', type=str, default='./models/final_model.pth',
                        help='模型文件路径')
    parser.add_argument('--device', type=str, default='cuda',
                        help='设备 (cpu/cuda)')
    
    args = parser.parse_args()
    
    evaluate_model(args.model_path, args.device)


if __name__ == '__main__':
    main()
