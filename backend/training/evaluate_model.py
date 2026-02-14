"""
模型评估脚本

评估训练好的模型在测试集上的性能
"""
import argparse
import logging
from pathlib import Path

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from tqdm import tqdm

from train_standalone import TransformerLSTMModel, TyphoonDataset, collate_fn
from torch.utils.data import DataLoader, random_split

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def evaluate_model(model, test_loader, device):
    """
    评估模型性能
    
    Returns:
        dict: 包含各项评估指标
    """
    model.eval()
    
    all_predictions = []
    all_targets = []
    all_confidences = []
    
    with torch.no_grad():
        for inputs, targets in tqdm(test_loader, desc="评估中"):
            inputs = inputs.to(device)
            targets = targets.to(device)
            
            pred_mean, pred_std, confidence = model(inputs)
            
            all_predictions.append(pred_mean.cpu().numpy())
            all_targets.append(targets.cpu().numpy())
            all_confidences.append(confidence.cpu().numpy())
    
    # 合并所有批次
    predictions = np.concatenate(all_predictions, axis=0)
    targets = np.concatenate(all_targets, axis=0)
    confidences = np.concatenate(all_confidences, axis=0)
    
    # 计算各项误差指标
    # 纬度误差
    lat_errors = np.abs(predictions[:, :, 0] - targets[:, :, 0])
    lat_mae = np.mean(lat_errors)
    lat_rmse = np.sqrt(np.mean(lat_errors ** 2))
    
    # 经度误差
    lon_errors = np.abs(predictions[:, :, 1] - targets[:, :, 1])
    lon_mae = np.mean(lon_errors)
    lon_rmse = np.sqrt(np.mean(lon_errors ** 2))
    
    # 气压误差
    pressure_errors = np.abs(predictions[:, :, 2] - targets[:, :, 2])
    pressure_mae = np.mean(pressure_errors)
    
    # 风速误差
    wind_errors = np.abs(predictions[:, :, 3] - targets[:, :, 3])
    wind_mae = np.mean(wind_errors)
    
    # 路径误差（欧氏距离）
    path_errors = np.sqrt(lat_errors ** 2 + lon_errors ** 2)
    path_mae = np.mean(path_errors)
    path_rmse = np.sqrt(np.mean(path_errors ** 2))
    
    # 按预测时间步分析
    time_step_errors = []
    for t in range(predictions.shape[1]):
        step_error = np.mean(path_errors[:, t])
        time_step_errors.append(step_error)
    
    # 置信度统计
    avg_confidence = np.mean(confidences)
    confidence_std = np.std(confidences)
    
    return {
        'lat_mae': lat_mae,
        'lat_rmse': lat_rmse,
        'lon_mae': lon_mae,
        'lon_rmse': lon_rmse,
        'pressure_mae': pressure_mae,
        'wind_mae': wind_mae,
        'path_mae': path_mae,
        'path_rmse': path_rmse,
        'time_step_errors': time_step_errors,
        'avg_confidence': avg_confidence,
        'confidence_std': confidence_std,
    }


def print_evaluation_results(results):
    """打印评估结果"""
    logger.info("\n" + "="*70)
    logger.info("模型评估结果")
    logger.info("="*70)
    
    logger.info("\n【路径预测误差】")
    logger.info(f"  纬度 MAE: {results['lat_mae']:.4f}°")
    logger.info(f"  纬度 RMSE: {results['lat_rmse']:.4f}°")
    logger.info(f"  经度 MAE: {results['lon_mae']:.4f}°")
    logger.info(f"  经度 RMSE: {results['lon_rmse']:.4f}°")
    logger.info(f"  路径 MAE: {results['path_mae']:.4f}°")
    logger.info(f"  路径 RMSE: {results['path_rmse']:.4f}°")
    
    logger.info("\n【强度预测误差】")
    logger.info(f"  气压 MAE: {results['pressure_mae']:.4f}")
    logger.info(f"  风速 MAE: {results['wind_mae']:.4f}")
    
    logger.info("\n【按预测时间步的路径误差】")
    for i, error in enumerate(results['time_step_errors']):
        hours = (i + 1) * 6  # 每步6小时
        logger.info(f"  {hours}h: {error:.4f}°")
    
    logger.info("\n【置信度统计】")
    logger.info(f"  平均置信度: {results['avg_confidence']:.4f}")
    logger.info(f"  置信度标准差: {results['confidence_std']:.4f}")
    
    logger.info("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(description='模型评估')
    parser.add_argument('--model-path', type=str, required=True, help='模型文件路径')
    parser.add_argument('--csv-path', type=str, required=True, help='测试数据CSV路径')
    parser.add_argument('--start-year', type=int, default=2023, help='测试数据起始年份')
    parser.add_argument('--end-year', type=int, default=2024, help='测试数据结束年份')
    parser.add_argument('--batch-size', type=int, default=32, help='批次大小')
    parser.add_argument('--device', type=str, default='cuda', help='设备')
    
    args = parser.parse_args()
    
    logger.info("="*70)
    logger.info("模型评估")
    logger.info("="*70)
    
    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    logger.info(f"使用设备: {device}")
    
    try:
        # 加载测试数据
        logger.info("\n加载测试数据...")
        test_dataset = TyphoonDataset(
            csv_path=args.csv_path,
            sequence_length=12,
            prediction_steps=8,
            start_year=args.start_year,
            end_year=args.end_year
        )
        
        logger.info(f"测试样本数: {len(test_dataset)}")
        
        if len(test_dataset) == 0:
            logger.error("测试集为空")
            return
        
        test_loader = DataLoader(
            test_dataset,
            batch_size=args.batch_size,
            shuffle=False,
            collate_fn=collate_fn
        )
        
        # 加载模型
        logger.info("\n加载模型...")
        model = TransformerLSTMModel(
            input_size=10,
            hidden_size=256,
            num_lstm_layers=2,
            num_transformer_layers=2,
            num_heads=8,
            output_size=4,
            prediction_steps=8,
            dropout=0.2
        )
        
        checkpoint = torch.load(args.model_path, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        model = model.to(device)
        
        logger.info(f"模型加载成功: {args.model_path}")
        
        # 评估模型
        logger.info("\n开始评估...")
        results = evaluate_model(model, test_loader, device)
        
        # 打印结果
        print_evaluation_results(results)
        
        # 保存评估结果
        output_dir = Path('evaluation_results')
        output_dir.mkdir(exist_ok=True)
        
        results_file = output_dir / f'eval_{args.start_year}_{args.end_year}.txt'
        with open(results_file, 'w') as f:
            f.write("模型评估结果\n")
            f.write("="*70 + "\n\n")
            f.write(f"模型路径: {args.model_path}\n")
            f.write(f"测试数据: {args.csv_path}\n")
            f.write(f"测试年份: {args.start_year}-{args.end_year}\n")
            f.write(f"测试样本数: {len(test_dataset)}\n\n")
            
            f.write("【路径预测误差】\n")
            f.write(f"  纬度 MAE: {results['lat_mae']:.4f}°\n")
            f.write(f"  纬度 RMSE: {results['lat_rmse']:.4f}°\n")
            f.write(f"  经度 MAE: {results['lon_mae']:.4f}°\n")
            f.write(f"  经度 RMSE: {results['lon_rmse']:.4f}°\n")
            f.write(f"  路径 MAE: {results['path_mae']:.4f}°\n")
            f.write(f"  路径 RMSE: {results['path_rmse']:.4f}°\n\n")
            
            f.write("【按预测时间步的路径误差】\n")
            for i, error in enumerate(results['time_step_errors']):
                hours = (i + 1) * 6
                f.write(f"  {hours}h: {error:.4f}°\n")
        
        logger.info(f"\n评估结果已保存到: {results_file}")
        
    except Exception as e:
        logger.error(f"评估过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
