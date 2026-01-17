"""
OpenCV传统图像处理模块
基于传统计算机视觉方法进行台风图像分析
无需训练数据，可独立运行
"""
import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# 尝试导入OpenCV，如果未安装则记录警告
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("⚠️ OpenCV未安装，传统图像处理功能将受限")


class OpenCVAnalyzer:
    """
    基于OpenCV的传统图像处理分析器
    
    功能：
    1. 台风中心粗定位（基于图像二值化和轮廓检测）
    2. 台风眼检测（基于圆形度筛选）
    3. 强度估算（基于云顶温度、纹理特征、对流强度）
    4. 螺旋结构分析（基于极坐标转换和FFT）
    """
    
    def __init__(self):
        """初始化分析器"""
        if not OPENCV_AVAILABLE:
            raise ImportError("OpenCV未安装，请运行: pip install opencv-python")
    
    def analyze(self, img: Image.Image, image_type: str = "infrared") -> Dict[str, Any]:
        """
        完整分析流程
        
        Args:
            img: PIL图像对象
            image_type: 图像类型（infrared=红外图, visible=可见光图）
        
        Returns:
            分析结果字典
        """
        try:
            # 转换为OpenCV格式（灰度图）
            img_array = np.array(img.convert('L'))
            
            # 1. 检测台风中心
            center_x, center_y, center_confidence = self.detect_center(img_array, image_type)
            
            # 2. 估算强度
            intensity_level, intensity_confidence = self.estimate_intensity(img_array)
            
            # 3. 检测台风眼
            eye_detected, eye_diameter = self.detect_eye(img_array, center_x, center_y)
            
            # 4. 分析螺旋结构
            spiral_score = self.analyze_spiral_structure(img_array, center_x, center_y)
            
            # 组装结果
            result = {
                "method": "opencv",
                "center": {
                    "pixel_x": int(center_x) if center_x is not None else None,
                    "pixel_y": int(center_y) if center_y is not None else None,
                    "confidence": float(center_confidence)
                },
                "intensity": {
                    "level": intensity_level,
                    "confidence": float(intensity_confidence)
                },
                "eye": {
                    "detected": eye_detected,
                    "diameter_km": float(eye_diameter) if eye_diameter else None
                },
                "structure": {
                    "spiral_score": float(spiral_score)
                }
            }
            
            logger.info(f"✅ OpenCV分析完成: 中心=({center_x}, {center_y}), 强度={intensity_level}")
            return result
        
        except Exception as e:
            logger.error(f"❌ OpenCV分析失败: {e}", exc_info=True)
            raise
    
    def detect_center(
        self, 
        img: np.ndarray, 
        image_type: str = "infrared"
    ) -> Tuple[Optional[float], Optional[float], float]:
        """
        检测台风中心位置
        
        原理：红外图中，台风眼是最暗的区域（云顶温度最低）
        
        Args:
            img: 灰度图像数组
            image_type: 图像类型
        
        Returns:
            (center_x, center_y, confidence)
        """
        try:
            # 预处理：高斯模糊去噪
            img_blur = cv2.GaussianBlur(img, (5, 5), 0)
            
            # 二值化：提取最暗区域（台风眼）
            if image_type == "infrared":
                # 红外图：台风眼是最暗的区域
                _, binary = cv2.threshold(img_blur, 50, 255, cv2.THRESH_BINARY_INV)
            else:
                # 可见光图：台风眼是最亮的区域
                _, binary = cv2.threshold(img_blur, 200, 255, cv2.THRESH_BINARY)
            
            # 形态学操作：去除噪点
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            
            # 查找轮廓
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                logger.warning("⚠️ 未检测到台风中心候选区域")
                return None, None, 0.0
            
            # 找到最圆的区域（台风眼通常是圆形）
            best_contour = None
            best_circularity = 0
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 100:  # 过滤小区域
                    continue
                
                perimeter = cv2.arcLength(contour, True)
                if perimeter == 0:
                    continue
                
                # 圆形度 = 4π * 面积 / 周长²
                # 完美圆形的圆形度为1
                circularity = 4 * np.pi * area / (perimeter ** 2)
                
                if circularity > best_circularity:
                    best_circularity = circularity
                    best_contour = contour

            if best_contour is None:
                logger.warning("⚠️ 未找到符合条件的台风中心")
                return None, None, 0.0

            # 计算中心点
            M = cv2.moments(best_contour)
            if M["m00"] == 0:
                return None, None, 0.0

            center_x = M["m10"] / M["m00"]
            center_y = M["m01"] / M["m00"]

            # 置信度基于圆形度
            confidence = min(best_circularity, 1.0)

            return center_x, center_y, confidence

        except Exception as e:
            logger.error(f"❌ 台风中心检测失败: {e}", exc_info=True)
            return None, None, 0.0

    def estimate_intensity(self, img: np.ndarray) -> Tuple[str, float]:
        """
        估算台风强度

        基于：
        1. 云顶温度（图像亮度）
        2. 云层组织程度（纹理复杂度）
        3. 对流强度（梯度强度）

        Args:
            img: 灰度图像数组

        Returns:
            (intensity_level, confidence)
        """
        try:
            # 计算图像统计特征
            mean_intensity = np.mean(img)
            std_intensity = np.std(img)

            # 计算纹理特征
            texture_score = self._calculate_texture(img)

            # 计算对流强度
            convection_score = self._calculate_convection(img)

            # 综合评分
            total_score = (
                (255 - mean_intensity) / 255 * 0.4 +  # 云顶温度权重40%
                texture_score * 0.3 +                   # 纹理权重30%
                convection_score * 0.3                  # 对流权重30%
            )

            # 强度分级（中国标准）
            if total_score > 0.8:
                return "超强台风", 0.85
            elif total_score > 0.7:
                return "强台风", 0.80
            elif total_score > 0.6:
                return "台风", 0.75
            elif total_score > 0.5:
                return "强热带风暴", 0.70
            elif total_score > 0.4:
                return "热带风暴", 0.65
            else:
                return "热带低压", 0.60

        except Exception as e:
            logger.error(f"❌ 强度估算失败: {e}", exc_info=True)
            return "未知", 0.0

    def detect_eye(
        self,
        img: np.ndarray,
        center_x: Optional[float],
        center_y: Optional[float]
    ) -> Tuple[bool, Optional[float]]:
        """
        检测台风眼

        Args:
            img: 灰度图像数组
            center_x: 台风中心X坐标
            center_y: 台风中心Y坐标

        Returns:
            (是否检测到台风眼, 台风眼直径(km))
        """
        if center_x is None or center_y is None:
            return False, None

        try:
            # 提取中心区域（100x100像素）
            cx, cy = int(center_x), int(center_y)
            roi_size = 50

            if (cy - roi_size < 0 or cy + roi_size >= img.shape[0] or
                cx - roi_size < 0 or cx + roi_size >= img.shape[1]):
                return False, None

            roi = img[cy-roi_size:cy+roi_size, cx-roi_size:cx+roi_size]

            # 台风眼特征：中心区域明显比周围暗
            center_mean = np.mean(roi[40:60, 40:60])  # 中心20x20区域
            surround_mean = np.mean(roi)  # 整个ROI

            # 如果中心比周围暗30%以上，认为存在台风眼
            if center_mean < surround_mean * 0.7:
                # 估算台风眼直径（假设1像素=4km）
                eye_diameter_pixels = roi_size * 0.4  # 粗略估计
                eye_diameter_km = eye_diameter_pixels * 4
                return True, eye_diameter_km

            return False, None

        except Exception as e:
            logger.error(f"❌ 台风眼检测失败: {e}", exc_info=True)
            return False, None

    def analyze_spiral_structure(
        self,
        img: np.ndarray,
        center_x: Optional[float],
        center_y: Optional[float]
    ) -> float:
        """
        分析螺旋结构

        Args:
            img: 灰度图像数组
            center_x: 台风中心X坐标
            center_y: 台风中心Y坐标

        Returns:
            螺旋结构评分（0-1）
        """
        if center_x is None or center_y is None:
            return 0.0

        try:
            # 转换到极坐标
            h, w = img.shape
            y, x = np.ogrid[:h, :w]

            # 计算相对于中心的角度和半径
            dx = x - center_x
            dy = y - center_y
            radius = np.sqrt(dx**2 + dy**2)

            # 分析不同半径上的强度变化
            max_radius = min(h, w) // 2
            spiral_scores = []

            for r in range(50, max_radius, 50):
                # 提取该半径上的像素
                mask = (radius >= r-10) & (radius < r+10)
                if not np.any(mask):
                    continue

                intensities = img[mask]

                # 计算强度变化的标准差（螺旋结构应该有周期性变化）
                if len(intensities) > 10:
                    score = np.std(intensities) / 255.0
                    spiral_scores.append(score)

            if not spiral_scores:
                return 0.0

            return float(np.mean(spiral_scores))

        except Exception as e:
            logger.error(f"❌ 螺旋结构分析失败: {e}", exc_info=True)
            return 0.0

    def _calculate_texture(self, img: np.ndarray) -> float:
        """计算纹理复杂度"""
        try:
            # 使用Sobel算子计算梯度
            sobelx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
            gradient = np.sqrt(sobelx**2 + sobely**2)

            # 归一化纹理分数
            texture_score = np.mean(gradient) / 255.0
            return float(texture_score)
        except Exception as e:
            logger.error(f"❌ 纹理计算失败: {e}", exc_info=True)
            return 0.0

    def _calculate_convection(self, img: np.ndarray) -> float:
        """计算对流强度"""
        try:
            # 使用Laplacian算子检测对流活动
            laplacian = cv2.Laplacian(img, cv2.CV_64F)
            convection_score = np.std(laplacian) / 255.0
            return float(convection_score)
        except Exception as e:
            logger.error(f"❌ 对流强度计算失败: {e}", exc_info=True)
            return 0.0

