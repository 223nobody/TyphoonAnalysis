"""
深度学习图像分析模块
基于ResNet50迁移学习进行台风图像分析
阶段1：预留接口，返回空结果（模型未训练）
阶段3：加载训练好的模型进行推理
"""
import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
from PIL import Image
from pathlib import Path

logger = logging.getLogger(__name__)

# 尝试导入PyTorch，如果未安装则记录警告
try:
    import torch
    import torchvision.transforms as transforms
    from torchvision import models
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    logger.warning("⚠️ PyTorch未安装，深度学习功能将不可用")


class DLAnalyzer:
    """
    基于深度学习的台风图像分析器
    
    功能：
    1. 台风中心精确定位（回归任务）
    2. 强度等级分类（6分类：TD/TS/STS/TY/STY/Super TY）
    3. 模型推理接口
    
    模型架构：
    - 骨干网络：ResNet50（ImageNet预训练）
    - 任务1：中心定位 - 回归头（输出2个值：x, y坐标）
    - 任务2：强度分类 - 分类头（输出6个类别概率）
    """
    
    # 强度等级定义（中国标准）
    INTENSITY_CLASSES = [
        "热带低压",      # 0: TD (Tropical Depression)
        "热带风暴",      # 1: TS (Tropical Storm)
        "强热带风暴",    # 2: STS (Severe Tropical Storm)
        "台风",          # 3: TY (Typhoon)
        "强台风",        # 4: STY (Strong Typhoon)
        "超强台风"       # 5: Super TY (Super Typhoon)
    ]
    
    def __init__(self, model_dir: str = "data/models"):
        """
        初始化分析器
        
        Args:
            model_dir: 模型文件存储目录
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # 模型状态
        self.center_model = None
        self.intensity_model = None
        self.models_loaded = False
        
        # 图像预处理转换
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ]) if PYTORCH_AVAILABLE else None
        
        # 尝试加载模型
        if PYTORCH_AVAILABLE:
            self._load_models()
    
    def _load_models(self):
        """加载训练好的模型"""
        try:
            center_model_path = self.model_dir / "typhoon_center_resnet50.pth"
            intensity_model_path = self.model_dir / "typhoon_intensity_resnet50.pth"
            
            # 检查模型文件是否存在
            if center_model_path.exists():
                self.center_model = torch.load(center_model_path, map_location='cpu')
                self.center_model.eval()
                logger.info(f"✅ 中心定位模型加载成功: {center_model_path}")
            else:
                logger.warning(f"⚠️ 中心定位模型不存在: {center_model_path}")
            
            if intensity_model_path.exists():
                self.intensity_model = torch.load(intensity_model_path, map_location='cpu')
                self.intensity_model.eval()
                logger.info(f"✅ 强度分类模型加载成功: {intensity_model_path}")
            else:
                logger.warning(f"⚠️ 强度分类模型不存在: {intensity_model_path}")
            
            self.models_loaded = (self.center_model is not None or 
                                 self.intensity_model is not None)
        
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}", exc_info=True)
            self.models_loaded = False
    
    def analyze(self, img: Image.Image) -> Dict[str, Any]:
        """
        完整分析流程
        
        Args:
            img: PIL图像对象
        
        Returns:
            分析结果字典
        """
        if not PYTORCH_AVAILABLE:
            logger.warning("⚠️ PyTorch未安装，返回空结果")
            return self._empty_result()
        
        if not self.models_loaded:
            logger.warning("⚠️ 模型未加载，返回空结果")
            return self._empty_result()
        
        try:
            # 预处理图像
            img_tensor = self._preprocess_image(img)
            
            # 1. 台风中心定位
            center_x, center_y, center_confidence = self._predict_center(img_tensor)
            
            # 2. 强度分类
            intensity_level, intensity_confidence = self._predict_intensity(img_tensor)
            
            # 组装结果
            result = {
                "method": "deep_learning",
                "model": "ResNet50",
                "center": {
                    "pixel_x": int(center_x) if center_x is not None else None,
                    "pixel_y": int(center_y) if center_y is not None else None,
                    "confidence": float(center_confidence)
                },
                "intensity": {
                    "level": intensity_level,
                    "confidence": float(intensity_confidence)
                }
            }
            
            logger.info(f"✅ 深度学习分析完成: 中心=({center_x}, {center_y}), 强度={intensity_level}")
            return result
        
        except Exception as e:
            logger.error(f"❌ 深度学习分析失败: {e}", exc_info=True)
            return self._empty_result()
    
    def _preprocess_image(self, img: Image.Image) -> torch.Tensor:
        """
        预处理图像
        
        Args:
            img: PIL图像对象
        
        Returns:
            预处理后的张量
        """
        # 转换为RGB（如果是灰度图）
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 应用转换
        img_tensor = self.transform(img)
        
        # 添加batch维度
        img_tensor = img_tensor.unsqueeze(0)
        
        return img_tensor
    
    def _predict_center(
        self, 
        img_tensor: torch.Tensor
    ) -> Tuple[Optional[float], Optional[float], float]:
        """
        预测台风中心位置
        
        Args:
            img_tensor: 预处理后的图像张量
        
        Returns:
            (center_x, center_y, confidence)
        """
        if self.center_model is None:
            return None, None, 0.0
        
        try:
            with torch.no_grad():
                # 模型推理
                output = self.center_model(img_tensor)
                
                # 输出格式：[batch_size, 2] -> [x, y]
                center_x = float(output[0, 0].item())
                center_y = float(output[0, 1].item())
                
                # 置信度（可以基于模型输出的方差或其他指标）
                confidence = 0.95  # 简化处理，实际应该从模型输出计算
                
                return center_x, center_y, confidence
        
        except Exception as e:
            logger.error(f"❌ 中心定位预测失败: {e}", exc_info=True)
            return None, None, 0.0
    
    def _predict_intensity(self, img_tensor: torch.Tensor) -> Tuple[str, float]:
        """
        预测台风强度等级
        
        Args:
            img_tensor: 预处理后的图像张量
        
        Returns:
            (intensity_level, confidence)
        """
        if self.intensity_model is None:
            return "未知", 0.0
        
        try:
            with torch.no_grad():
                # 模型推理
                output = self.intensity_model(img_tensor)
                
                # 输出格式：[batch_size, 6] -> 6个类别的概率
                probabilities = torch.softmax(output, dim=1)
                
                # 获取最高概率的类别
                confidence, predicted_class = torch.max(probabilities, dim=1)
                
                intensity_level = self.INTENSITY_CLASSES[predicted_class.item()]
                confidence_value = float(confidence.item())
                
                return intensity_level, confidence_value
        
        except Exception as e:
            logger.error(f"❌ 强度分类预测失败: {e}", exc_info=True)
            return "未知", 0.0
    
    def _empty_result(self) -> Dict[str, Any]:
        """
        返回空结果（模型未加载时）
        
        Returns:
            空结果字典
        """
        return {
            "method": "deep_learning",
            "model": "ResNet50",
            "status": "model_not_loaded",
            "center": {
                "pixel_x": None,
                "pixel_y": None,
                "confidence": 0.0
            },
            "intensity": {
                "level": "未知",
                "confidence": 0.0
            }
        }

