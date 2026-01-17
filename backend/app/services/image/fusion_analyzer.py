"""
决策融合模块
结合OpenCV传统方法和深度学习结果，提供最终的分析结果
"""
import logging
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class FusionAnalyzer:
    """
    决策融合分析器
    
    功能：
    1. 结合OpenCV和深度学习结果
    2. 加权平均或投票机制
    3. 置信度评估
    4. 异常检测和纠错
    """
    
    def __init__(self):
        """初始化融合分析器"""
        # 权重配置（可根据实际效果调整）
        self.opencv_weight = 0.3  # OpenCV权重
        self.dl_weight = 0.7      # 深度学习权重
        
        # 阈值配置
        self.position_diff_threshold = 50  # 位置差异阈值（像素）
        self.intensity_diff_threshold = 1  # 强度等级差异阈值
    
    def fuse(
        self, 
        opencv_result: Dict[str, Any], 
        dl_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        融合OpenCV和深度学习的分析结果
        
        Args:
            opencv_result: OpenCV分析结果
            dl_result: 深度学习分析结果
        
        Returns:
            融合后的分析结果
        """
        try:
            # 1. 融合台风中心位置
            center = self._fuse_center(
                opencv_result.get("center", {}),
                dl_result.get("center", {})
            )
            
            # 2. 融合强度估算
            intensity = self._fuse_intensity(
                opencv_result.get("intensity", {}),
                dl_result.get("intensity", {})
            )
            
            # 3. 保留OpenCV的台风眼检测结果（深度学习暂不支持）
            eye = opencv_result.get("eye", {})
            
            # 4. 保留OpenCV的螺旋结构分析结果
            structure = opencv_result.get("structure", {})
            
            # 5. 计算综合置信度
            overall_confidence = self._calculate_overall_confidence(
                opencv_result, dl_result, center, intensity
            )
            
            # 组装最终结果
            result = {
                "method": "fusion",
                "components": {
                    "opencv": opencv_result.get("method", "opencv"),
                    "deep_learning": dl_result.get("method", "deep_learning")
                },
                "center": center,
                "intensity": intensity,
                "eye": eye,
                "structure": structure,
                "confidence": overall_confidence,
                "details": {
                    "opencv_result": opencv_result,
                    "dl_result": dl_result
                }
            }
            
            logger.info(
                f"✅ 决策融合完成: "
                f"中心=({center.get('pixel_x')}, {center.get('pixel_y')}), "
                f"强度={intensity.get('level')}, "
                f"置信度={overall_confidence:.2f}"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"❌ 决策融合失败: {e}", exc_info=True)
            # 如果融合失败，返回OpenCV结果作为备选
            return opencv_result
    
    def _fuse_center(
        self, 
        opencv_center: Dict[str, Any], 
        dl_center: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        融合台风中心位置
        
        策略：
        1. 如果两者结果差异<50像素：加权平均（OpenCV 0.3 + DL 0.7）
        2. 如果差异>50像素：选择置信度更高的结果
        3. 如果OpenCV未检测到：使用深度学习结果
        4. 如果深度学习未加载：使用OpenCV结果
        
        Args:
            opencv_center: OpenCV中心检测结果
            dl_center: 深度学习中心检测结果
        
        Returns:
            融合后的中心位置
        """
        opencv_x = opencv_center.get("pixel_x")
        opencv_y = opencv_center.get("pixel_y")
        opencv_conf = opencv_center.get("confidence", 0.0)
        
        dl_x = dl_center.get("pixel_x")
        dl_y = dl_center.get("pixel_y")
        dl_conf = dl_center.get("confidence", 0.0)
        
        # 情况1：OpenCV未检测到，使用深度学习结果
        if opencv_x is None or opencv_y is None:
            if dl_x is not None and dl_y is not None:
                return {
                    "pixel_x": dl_x,
                    "pixel_y": dl_y,
                    "confidence": dl_conf,
                    "method": "deep_learning_only"
                }
            else:
                return {
                    "pixel_x": None,
                    "pixel_y": None,
                    "confidence": 0.0,
                    "method": "none"
                }
        
        # 情况2：深度学习未加载，使用OpenCV结果
        if dl_x is None or dl_y is None or dl_conf == 0.0:
            return {
                "pixel_x": opencv_x,
                "pixel_y": opencv_y,
                "confidence": opencv_conf,
                "method": "opencv_only"
            }
        
        # 情况3：两者都有结果，计算差异
        diff = np.sqrt((opencv_x - dl_x)**2 + (opencv_y - dl_y)**2)
        
        if diff < self.position_diff_threshold:
            # 差异小，加权平均
            fused_x = opencv_x * self.opencv_weight + dl_x * self.dl_weight
            fused_y = opencv_y * self.opencv_weight + dl_y * self.dl_weight
            fused_conf = opencv_conf * self.opencv_weight + dl_conf * self.dl_weight
            
            return {
                "pixel_x": int(fused_x),
                "pixel_y": int(fused_y),
                "confidence": fused_conf,
                "method": "weighted_average",
                "position_diff": float(diff)
            }
        else:
            # 差异大，选择置信度更高的
            if opencv_conf > dl_conf:
                return {
                    "pixel_x": opencv_x,
                    "pixel_y": opencv_y,
                    "confidence": opencv_conf,
                    "method": "opencv_high_confidence",
                    "position_diff": float(diff)
                }
            else:
                return {
                    "pixel_x": dl_x,
                    "pixel_y": dl_y,
                    "confidence": dl_conf,
                    "method": "dl_high_confidence",
                    "position_diff": float(diff)
                }
    
    def _fuse_intensity(
        self, 
        opencv_intensity: Dict[str, Any], 
        dl_intensity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        融合强度估算结果
        
        策略：
        1. 如果两者结果一致：输出该结果
        2. 如果相差1个等级：选择置信度更高的
        3. 如果相差>1个等级：标记为不确定，需人工审核
        
        Args:
            opencv_intensity: OpenCV强度估算结果
            dl_intensity: 深度学习强度估算结果
        
        Returns:
            融合后的强度估算
        """
        # 强度等级映射
        intensity_levels = [
            "热带低压", "热带风暴", "强热带风暴", 
            "台风", "强台风", "超强台风"
        ]
        
        opencv_level = opencv_intensity.get("level", "未知")
        opencv_conf = opencv_intensity.get("confidence", 0.0)
        
        dl_level = dl_intensity.get("level", "未知")
        dl_conf = dl_intensity.get("confidence", 0.0)
        
        # 情况1：深度学习未加载，使用OpenCV结果
        if dl_level == "未知" or dl_conf == 0.0:
            return {
                "level": opencv_level,
                "confidence": opencv_conf,
                "method": "opencv_only"
            }
        
        # 情况2：OpenCV未检测到，使用深度学习结果
        if opencv_level == "未知":
            return {
                "level": dl_level,
                "confidence": dl_conf,
                "method": "deep_learning_only"
            }
        
        # 情况3：两者都有结果，比较等级差异
        try:
            opencv_idx = intensity_levels.index(opencv_level)
            dl_idx = intensity_levels.index(dl_level)
            level_diff = abs(opencv_idx - dl_idx)
            
            if level_diff == 0:
                # 结果一致
                fused_conf = (opencv_conf + dl_conf) / 2
                return {
                    "level": opencv_level,
                    "confidence": fused_conf,
                    "method": "consistent"
                }
            elif level_diff == 1:
                # 相差1个等级，选择置信度更高的
                if opencv_conf > dl_conf:
                    return {
                        "level": opencv_level,
                        "confidence": opencv_conf,
                        "method": "opencv_high_confidence",
                        "level_diff": level_diff
                    }
                else:
                    return {
                        "level": dl_level,
                        "confidence": dl_conf,
                        "method": "dl_high_confidence",
                        "level_diff": level_diff
                    }
            else:
                # 相差>1个等级，标记为不确定
                return {
                    "level": "不确定",
                    "confidence": 0.5,
                    "method": "uncertain",
                    "level_diff": level_diff,
                    "opencv_level": opencv_level,
                    "dl_level": dl_level,
                    "note": "两种方法结果差异较大，建议人工审核"
                }
        
        except ValueError:
            # 等级不在列表中
            return {
                "level": opencv_level,
                "confidence": opencv_conf,
                "method": "opencv_fallback"
            }
    
    def _calculate_overall_confidence(
        self,
        opencv_result: Dict[str, Any],
        dl_result: Dict[str, Any],
        fused_center: Dict[str, Any],
        fused_intensity: Dict[str, Any]
    ) -> float:
        """
        计算综合置信度
        
        Args:
            opencv_result: OpenCV分析结果
            dl_result: 深度学习分析结果
            fused_center: 融合后的中心位置
            fused_intensity: 融合后的强度估算
        
        Returns:
            综合置信度（0-1）
        """
        # 中心位置置信度
        center_conf = fused_center.get("confidence", 0.0)
        
        # 强度估算置信度
        intensity_conf = fused_intensity.get("confidence", 0.0)
        
        # 综合置信度（加权平均）
        overall_conf = center_conf * 0.6 + intensity_conf * 0.4
        
        return float(overall_conf)

