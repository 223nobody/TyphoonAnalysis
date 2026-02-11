"""
选择最佳模型脚本

自动评估所有保存的模型，选择性能最好的一个
"""
import logging
from pathlib import Path
import torch
import numpy as np
from torch.utils.data import DataLoader

from app.services.prediction.data.dataset import CSVTyphoonDataset, TyphoonDataCollator
from app.services.prediction.models.lstm_model import LSTMTyphoonModel
from app.services.prediction.models.loss_functions import TyphoonPredictionLoss

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def evaluate_single_model(model_path: Path, device: torch.device, val_loader: DataLoader) -> dict:
    """评估单个模型"""
    logger.info(f"\n评估模型: {model_path.name}")
    
    try:
        # 加载检查点
        checkpoint = torch.load(model_path, map_location=device)
        
        # 初始化模型
        model = LSTMTyphoonModel(
            input_size=10,
            hidden_size=128,
            num_layers=3,
            output_size=4,
            prediction_steps=8,
            dropout=0.2,
            attention_heads=8
        ).to(device)
        
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            logger.warning(f"⚠️ {model_path.name}: 没有模型权重")
            return None
        
        model.eval()
        
        # 评估
        criterion = TyphoonPredictionLoss()
        total_loss = 0.0
        total_samples = 0
        
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                
                outputs, _, _ = model(inputs)
                loss = criterion(outputs, targets)
                
                if not torch.isnan(loss):
                    total_loss += loss.item() * inputs.size(0)
                    total_samples += inputs.size(0)
        
        if total_samples > 0:
            avg_loss = total_loss / total_samples
            
            # 获取训练历史
            train_losses = checkpoint.get('train_losses', [])
            val_losses = checkpoint.get('val_losses', [])
            
            result = {
                'name': model_path.name,
                'path': str(model_path),
                'val_loss': avg_loss,
                'final_train_loss': train_losses[-1] if train_losses else None,
                'epochs_trained': len(train_losses),
                'total_samples': total_samples
            }
            
            logger.info(f"  ✅ 验证损失: {avg_loss:.6f}")
            logger.info(f"  📊 训练轮数: {result['epochs_trained']}")
            
            return result
        else:
            logger.warning(f"⚠️ {model_path.name}: 没有有效样本")
            return None
            
    except Exception as e:
        logger.error(f"❌ 评估 {model_path.name} 失败: {e}")
        return None


def select_best_model(models_dir: str = './models', device: str = 'cuda'):
    """选择最佳模型"""
    logger.info("=" * 70)
    logger.info("选择最佳模型")
    logger.info("=" * 70)
    
    device = torch.device(device if torch.cuda.is_available() else 'cpu')
    logger.info(f"使用设备: {device}")
    
    # 1. 创建验证数据集
    logger.info("\n创建验证数据集...")
    val_dataset = CSVTyphoonDataset(
        start_year=2018,
        end_year=2020,
        sequence_length=12,
        prediction_steps=8
    )
    
    logger.info(f"验证数据集大小: {len(val_dataset)} 个样本")
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=32,
        shuffle=False,
        collate_fn=TyphoonDataCollator(),
        num_workers=0
    )
    
    # 2. 查找所有模型文件
    models_path = Path(models_dir)
    if not models_path.exists():
        logger.error(f"模型目录不存在: {models_dir}")
        return
    
    model_files = list(models_path.glob('*.pth'))
    if not model_files:
        logger.error(f"没有找到模型文件: {models_dir}")
        return
    
    logger.info(f"\n找到 {len(model_files)} 个模型文件:")
    for f in model_files:
        logger.info(f"  - {f.name}")
    
    # 3. 评估所有模型
    logger.info("\n" + "=" * 70)
    logger.info("开始评估所有模型...")
    logger.info("=" * 70)
    
    results = []
    for model_file in model_files:
        result = evaluate_single_model(model_file, device, val_loader)
        if result:
            results.append(result)
    
    if not results:
        logger.error("❌ 没有模型评估成功")
        return
    
    # 4. 排序并选择最佳模型
    results.sort(key=lambda x: x['val_loss'])
    
    logger.info("\n" + "=" * 70)
    logger.info("评估结果排名")
    logger.info("=" * 70)
    
    for i, result in enumerate(results, 1):
        logger.info(f"\n[{i}] {result['name']}")
        logger.info(f"    验证损失: {result['val_loss']:.6f}")
        logger.info(f"    训练轮数: {result['epochs_trained']}")
        logger.info(f"    最终训练损失: {result['final_train_loss']:.6f}" if result['final_train_loss'] else "    最终训练损失: N/A")
    
    # 5. 推荐最佳模型
    best_model = results[0]
    
    logger.info("\n" + "=" * 70)
    logger.info("🏆 最佳模型推荐")
    logger.info("=" * 70)
    logger.info(f"模型名称: {best_model['name']}")
    logger.info(f"模型路径: {best_model['path']}")
    logger.info(f"验证损失: {best_model['val_loss']:.6f}")
    logger.info(f"训练轮数: {best_model['epochs_trained']}")
    
    # 6. 创建最佳模型链接/副本
    best_model_link = models_path / 'best_model.pth'
    try:
        import shutil
        shutil.copy(best_model['path'], str(best_model_link))
        logger.info(f"\n✅ 最佳模型已复制到: {best_model_link}")
    except Exception as e:
        logger.warning(f"⚠️ 复制最佳模型失败: {e}")
    
    logger.info("\n" + "=" * 70)
    logger.info("使用建议")
    logger.info("=" * 70)
    logger.info(f"在代码中使用最佳模型:")
    logger.info(f"  predictor = TyphoonPredictor(model_path='{best_model['path']}', device='cuda')")
    logger.info(f"\n或者使用快捷方式:")
    logger.info(f"  predictor = TyphoonPredictor(model_path='./models/best_model.pth', device='cuda')")
    
    return best_model


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='选择最佳模型')
    parser.add_argument('--models-dir', type=str, default='./models',
                        help='模型目录路径')
    parser.add_argument('--device', type=str, default='cuda',
                        help='设备 (cpu/cuda)')
    
    args = parser.parse_args()
    
    select_best_model(args.models_dir, args.device)
