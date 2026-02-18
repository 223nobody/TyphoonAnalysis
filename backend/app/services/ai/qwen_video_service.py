"""
阿里云百炼视频分析服务
基于阿里云百炼大模型平台的视频理解API
文档参考：https://bailian.console.aliyun.com/
"""
import os
import base64
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def check_cv2_available():
    """检查 OpenCV 是否可用"""
    try:
        import cv2
        import numpy as np
        logger.info(f"OpenCV 已加载，版本: {cv2.__version__}")
        return True, cv2, np
    except ImportError as e:
        logger.error(f"OpenCV 未安装: {e}")
        return False, None, None


# 动态检查 OpenCV
CV2_AVAILABLE, cv2, np = check_cv2_available()


class BailianVideoService:
    """阿里云百炼视频分析服务"""
    
    # 支持的视频分析模型
    MODELS = {
        "qwen-vl-max": "qwen-vl-max-latest",  # 通义千问VL Max
        "qwen-vl-plus": "qwen-vl-plus-latest",  # 通义千问VL Plus
    }
    
    def __init__(self):
        # 优先使用 VL 专用 API 密钥，否则使用通用密钥
        self.api_key = settings.AI_API_KEY_VL or settings.AI_API_KEY
        self.base_url = settings.AI_API_BASE_URL_VL or "https://dashscope.aliyuncs.com/api/v1"
        self.model = settings.QWEN_VL_MODEL or self.MODELS.get("qwen-vl-max")
        self.client = httpx.AsyncClient(timeout=300.0)  # 5分钟超时
        self.max_retries = 3  # 最大重试次数
        self.retry_delay = 2  # 重试间隔（秒）
        logger.info(f"百炼视频服务初始化: model={self.model}, base_url={self.base_url}")
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def extract_frames_from_video(
        self, 
        video_path: str, 
        interval: int = 5,
        max_frames: int = 20
    ) -> List[Dict[str, Any]]:
        """
        从视频中提取关键帧
        
        Args:
            video_path: 视频文件路径
            interval: 帧提取间隔（秒）
            max_frames: 最大提取帧数
            
        Returns:
            帧信息列表，包含base64编码的图像
        """
        frames = []
        
        if not CV2_AVAILABLE:
            logger.error("OpenCV未安装，无法提取视频帧")
            return frames
        
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"无法打开视频文件: {video_path}")
                return frames
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            # 计算需要提取的帧位置
            frame_positions = []
            current_time = 0
            while current_time < duration and len(frame_positions) < max_frames:
                frame_pos = int(current_time * fps)
                if frame_pos < total_frames:
                    frame_positions.append((current_time, frame_pos))
                current_time += interval
            
            for timestamp, frame_pos in frame_positions:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
                ret, frame = cap.read()
                
                if ret:
                    # 转换BGR到RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # 压缩图像以减少传输大小
                    max_size = 1024
                    h, w = frame_rgb.shape[:2]
                    if max(h, w) > max_size:
                        scale = max_size / max(h, w)
                        new_w, new_h = int(w * scale), int(h * scale)
                        frame_rgb = cv2.resize(frame_rgb, (new_w, new_h))
                    
                    # 编码为JPEG
                    _, buffer = cv2.imencode('.jpg', cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))
                    img_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    frames.append({
                        "timestamp": timestamp,
                        "frame_number": frame_pos,
                        "image_base64": img_base64,
                        "width": frame_rgb.shape[1],
                        "height": frame_rgb.shape[0]
                    })
            
            cap.release()
            logger.info(f"从视频提取了 {len(frames)} 帧")
            
        except Exception as e:
            logger.error(f"提取视频帧失败: {e}", exc_info=True)
        
        return frames
    
    def _build_analysis_prompt(
        self, 
        analysis_type: str = "comprehensive"
    ) -> str:
        """
        构建分析提示词 - 生成Markdown格式报告
        
        Args:
            analysis_type: 分析类型
            
        Returns:
            提示词字符串
        """
        prompts = {
            "comprehensive": """你是一位资深台风气象分析专家。请对提供的台风视频序列进行专业分析，并以Markdown格式输出分析报告。

【分析任务要求】
1. 台风活动检测：判断是否检测到台风活动
2. 中心位置追踪：识别台风中心位置变化
3. 强度演变分析：评估台风强度的动态变化
4. 结构特征识别：分析台风眼、螺旋云带等结构特征

【输出格式要求】
请使用Markdown格式输出分析报告，包含以下章节：

## 一、台风活动概览
- 是否检测到台风活动
- 台风整体特征描述

## 二、中心位置追踪
- 台风中心位置变化趋势
- 移动方向和速度分析

## 三、强度演变分析
- 强度等级变化（热带低压/热带风暴/台风/强台风/超强台风）
- 强度变化趋势和关键节点

## 四、结构特征分析
- 台风眼检测情况
- 螺旋云带特征
- 整体组织程度

## 五、综合分析结论
- 台风发展态势总结
- 关键发现和建议

【格式规范】
- 使用 ## 作为章节标题
- 使用 ### 作为子章节标题
- 使用 - 表示列表项
- 关键数据使用 **加粗** 标注
- 直接输出Markdown内容，不使用代码块包裹""",

            "tracking": """你是一位专业的台风路径追踪分析师。请对提供的台风视频进行中心位置追踪分析，并以Markdown格式输出分析报告。

【分析任务要求】
1. 逐帧定位台风中心位置
2. 记录中心点移动路径
3. 分析移动方向和速度变化
4. 评估路径特征

【输出格式要求】
请使用Markdown格式输出分析报告，包含以下章节：

## 一、台风追踪概览
- 是否成功追踪到台风
- 追踪帧数和时间跨度

## 二、中心位置变化
- 起始位置和结束位置
- 关键位置节点

## 三、移动特征分析
- 移动方向变化
- 移动速度分析
- 路径特征描述

## 四、追踪结论
- 路径趋势总结
- 关键发现

【格式规范】
- 使用 ## 作为章节标题
- 使用 ### 作为子章节标题
- 使用 - 表示列表项
- 关键数据使用 **加粗** 标注
- 直接输出Markdown内容，不使用代码块包裹""",

            "intensity": """你是一位专业的台风强度评估专家。请对提供的台风视频进行强度演变分析，并以Markdown格式输出分析报告。

【分析任务要求】
1. 按中国气象局标准进行强度分级
2. 识别强度变化的关键时间节点
3. 分析增强/减弱趋势
4. 评估峰值强度

【输出格式要求】
请使用Markdown格式输出分析报告，包含以下章节：

## 一、强度概览
- 台风强度等级范围
- 整体强度趋势

## 二、强度演变时间线
- 各阶段强度等级
- 强度变化关键节点

## 三、峰值强度分析
- 最大强度及出现时间
- 峰值强度特征

## 四、强度变化因素
- 影响强度变化的因素
- 环境条件分析

## 五、强度评估结论
- 强度发展趋势
- 关键发现

【格式规范】
- 使用 ## 作为章节标题
- 使用 ### 作为子章节标题
- 使用 - 表示列表项
- 关键数据使用 **加粗** 标注
- 直接输出Markdown内容，不使用代码块包裹""",

            "structure": """你是一位专业的台风结构分析专家。请对提供的台风视频进行云系结构分析，并以Markdown格式输出分析报告。

【分析任务要求】
1. 台风眼检测和分析
2. 眼墙完整性评估
3. 螺旋云带分析
4. 整体组织结构评估

【输出格式要求】
请使用Markdown格式输出分析报告，包含以下章节：

## 一、结构概览
- 台风整体结构特征
- 组织程度评估

## 二、台风眼分析
- 台风眼检测情况
- 眼的大小、形状、清晰度

## 三、眼墙分析
- 眼墙完整性
- 对流强度分布

## 四、螺旋云带分析
- 螺旋结构清晰度
- 云带条数和组织程度

## 五、结构演变
- 结构随时间的变化
- 关键结构变化节点

## 六、结构分析结论
- 结构特征总结
- 对强度的指示意义

【格式规范】
- 使用 ## 作为章节标题
- 使用 ### 作为子章节标题
- 使用 - 表示列表项
- 关键数据使用 **加粗** 标注
- 直接输出Markdown内容，不使用代码块包裹"""
        }
        
        return prompts.get(analysis_type, prompts["comprehensive"])

    async def analyze_video(
        self,
        video_path: str,
        analysis_type: str = "comprehensive",
        extract_frames: bool = True,
        frame_interval: int = 5,
        max_frames: int = 20
    ) -> Dict[str, Any]:
        """
        分析视频内容
        
        Args:
            video_path: 视频文件路径
            analysis_type: 分析类型
            extract_frames: 是否提取帧
            frame_interval: 帧提取间隔
            max_frames: 最大帧数
            
        Returns:
            分析结果
        """
        start_time = datetime.now()
        
        try:
            # 提取视频帧
            frames = []
            if extract_frames:
                frames = self.extract_frames_from_video(
                    video_path, 
                    interval=frame_interval,
                    max_frames=max_frames
                )
            
            if not frames:
                if not CV2_AVAILABLE:
                    return {
                        "success": False,
                        "error": "OpenCV未安装，无法提取视频帧。请安装 opencv-python: pip install opencv-python",
                        "processing_time": (datetime.now() - start_time).total_seconds()
                    }
                return {
                    "success": False,
                    "error": "无法从视频中提取帧",
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }
            
            # 构建消息内容
            prompt = self._build_analysis_prompt(analysis_type)
            
            # 构建多模态消息（百炼API格式）
            content = [{"type": "text", "text": prompt}]
            
            # 添加图像帧（限制数量以控制token消耗）
            for i, frame in enumerate(frames[:10]):  # 最多10帧
                image_url = f"data:image/jpeg;base64,{frame['image_base64']}"
                content.append({
                    "type": "image",
                    "image": image_url
                })
            
            # 构建请求体（百炼多模态API格式）
            payload = {
                "model": self.model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": content
                        }
                    ]
                },
                "parameters": {
                    "max_tokens": 2000,
                    "temperature": 0.7
                }
            }
            
            # 发送请求（带重试机制）
            api_url = f"{self.base_url}/services/aigc/multimodal-generation/generation"
            logger.info(f"发送视频分析请求到百炼API，模型: {self.model}, URL: {api_url}")
            
            result = await self._make_api_request_with_retry(api_url, payload)
            
            # 解析AI响应（百炼API格式）
            ai_content = ""
            if "output" in result and "choices" in result["output"]:
                ai_content = result["output"]["choices"][0]["message"]["content"]
            elif "choices" in result:
                ai_content = result["choices"][0]["message"]["content"]
            else:
                ai_content = str(result)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "analysis_type": analysis_type,
                "frame_count": len(frames),
                "ai_analysis": {
                    "description": ai_content,
                    "parsed": True
                },
                "raw_response": result,
                "processing_time": processing_time,
                "model_used": self.model
            }
            
        except Exception as e:
            logger.error(f"视频分析失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def _make_api_request_with_retry(
        self,
        api_url: str,
        payload: Dict
    ) -> Dict:
        """
        发送API请求，支持重试机制
        
        Args:
            api_url: API地址
            payload: 请求体
            
        Returns:
            API响应结果
        """
        headers = self._get_headers()
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"百炼API请求 - 第{attempt}次尝试")
                
                response = await self.client.post(
                    api_url,
                    headers=headers,
                    json=payload
                )
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(f"百炼API HTTP错误 - 第{attempt}次尝试: {e.response.status_code}")
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.info(f"等待{wait_time}秒后重试...")
                    import asyncio
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                last_error = e
                logger.error(f"百炼API请求异常 - 第{attempt}次尝试: {e}")
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    import asyncio
                    await asyncio.sleep(wait_time)
        
        # 所有重试都失败
        raise last_error or Exception("百炼API请求失败，已达到最大重试次数")
    
    def _parse_ai_response(self, content) -> Dict[str, Any]:
        """
        解析AI响应内容
        
        Args:
            content: AI响应内容
            
        Returns:
            解析后的数据
        """
        # 如果已经是字典，直接返回
        if isinstance(content, dict):
            return content
        
        # 如果是列表，尝试合并或取第一个元素
        if isinstance(content, list):
            if len(content) == 1 and isinstance(content[0], dict):
                return content[0]
            return {"items": content, "raw_response": content}
        
        # 如果不是字符串，转为字符串
        if not isinstance(content, str):
            content = str(content)
        
        # 直接返回Markdown内容
        return {
            "description": content,
            "parsed": True
        }
    
    async def analyze_single_frame(
        self, 
        image_base64: str, 
        prompt: str = None
    ) -> Dict[str, Any]:
        """
        分析单帧图像
        
        Args:
            image_base64: base64编码的图像
            prompt: 分析提示词
            
        Returns:
            分析结果
        """
        if prompt is None:
            prompt = "分析这张台风卫星图像，识别台风中心位置、强度等级和结构特征。请使用Markdown格式输出分析结果。"
        
        try:
            payload = {
                "model": self.model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image",
                                    "image": f"data:image/jpeg;base64,{image_base64}"
                                }
                            ]
                        }
                    ]
                },
                "parameters": {
                    "max_tokens": 1000,
                    "temperature": 0.7
                }
            }
            
            api_url = f"{self.base_url}/services/aigc/multimodal-generation/generation"
            result = await self._make_api_request_with_retry(api_url, payload)
            
            # 解析响应
            ai_content = ""
            if "output" in result and "choices" in result["output"]:
                ai_content = result["output"]["choices"][0]["message"]["content"]
            elif "choices" in result:
                ai_content = result["choices"][0]["message"]["content"]
            else:
                ai_content = str(result)
            
            return {
                "success": True,
                "content": ai_content,
                "raw_response": result
            }
            
        except Exception as e:
            logger.error(f"单帧分析失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# 全局服务实例
qwen_video_service = BailianVideoService()
