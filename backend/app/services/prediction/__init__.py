"""
智能预测服务模块

提供台风路径和强度的深度学习预测功能
"""

import logging

logger = logging.getLogger(__name__)

# 尝试导入PyTorch相关模块，如果失败则使用降级实现
try:
    import torch
    from .predictor import TyphoonPredictor, PredictionResult, PredictedPoint
    from .models.lstm_model import LSTMTyphoonModel
    from .models.loss_functions import TyphoonPredictionLoss

    __all__ = [
        "TyphoonPredictor",
        "PredictionResult",
        "PredictedPoint",
        "LSTMTyphoonModel",
        "TyphoonPredictionLoss",
    ]
    logger.info("智能预测模块加载成功 (PyTorch模式)")

except ImportError as e:
    logger.warning(f"PyTorch未安装或导入失败: {e}")
    logger.warning("智能预测模块将以降级模式运行")

    # 提供降级实现
    from .predictor_fallback import TyphoonPredictor, PredictionResult, PredictedPoint

    __all__ = [
        "TyphoonPredictor",
        "PredictionResult",
        "PredictedPoint",
    ]
