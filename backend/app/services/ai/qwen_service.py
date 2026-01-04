"""
通义千问AI服务
"""
import asyncio
import base64
import json
import logging
from typing import Dict, Optional
from pathlib import Path
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# DashScope API端点
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"


class QwenService:
    """通义千问服务类"""
    
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.timeout = settings.AI_TIMEOUT
        self.qwen_plus_model = settings.QWEN_PLUS_MODEL
        self.qwen_vl_model = settings.QWEN_VL_MODEL
    
    def _encode_image(self, image_path: str) -> str:
        """
        将图片编码为base64
        
        Args:
            image_path: 图片路径
            
        Returns:
            base64编码的图片字符串
        """
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
                
                # 确定图片类型
                image_ext = Path(image_path).suffix.lower()
                mime_type_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp'
                }
                mime_type = mime_type_map.get(image_ext, 'image/jpeg')
                
                return f"data:{mime_type};base64,{base64_image}"
        
        except Exception as e:
            logger.error(f"图片编码失败: {e}")
            raise
    
    async def analyze_typhoon_image(
        self, 
        image_path: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Dict:
        """
        使用Qwen3-VL分析台风路径预报图
        
        Args:
            image_path: 图片本地路径
            image_url: 图片URL
            
        Returns:
            Dict: 分析结果
        """
        try:
            # 如果提供了URL，直接使用URL；否则使用本地路径
            if image_url:
                image_input = image_url
            elif image_path:
                image_input = self._encode_image(image_path)
            else:
                raise ValueError("必须提供image_path或image_url")
            
            # 构建提示词
            prompt = """请仔细分析这张台风路径预报图，提取以下关键信息并以JSON格式返回：

1. 台风名称（typhoon_name）
2. 台风编号（typhoon_id，如果有）
3. 预报路径节点（forecast_points）：每个节点包含：
   - 时间（timestamp，格式：YYYY-MM-DD HH:MM）
   - 纬度（latitude）
   - 经度（longitude）
   - 中心气压（center_pressure，单位：hPa，如果有）
   - 最大风速（max_wind_speed，单位：m/s，如果有）
   - 强度等级（intensity，如果有）

4. 数据来源机构（data_source，如：CMA、JTWC等）

请以JSON格式返回提取的信息，确保经纬度、时间等数据准确。如果某些信息无法识别，请标记为null。"""
            
            payload = {
                "model": self.qwen_vl_model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"image": image_input},
                                {"text": prompt}
                            ]
                        }
                    ]
                },
                "parameters": {
                    "temperature": 0.1,
                    "max_tokens": 2000
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                endpoint = f"{DASHSCOPE_BASE_URL}/services/aigc/multimodal-generation/generation"
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                # 提取分析结果
                analysis_text = result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # 尝试解析JSON数据
                extracted_data = self._parse_json_from_text(analysis_text)
                
                return {
                    "success": True,
                    "analysis_text": analysis_text,
                    "extracted_data": extracted_data,
                    "model_used": self.qwen_vl_model
                }
        
        except Exception as e:
            logger.error(f"图像分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_text": "",
                "extracted_data": {}
            }
    
    async def generate_typhoon_report(
        self,
        typhoon_id: str,
        typhoon_name: str,
        prediction_data: Dict,
        analysis_data: Optional[Dict] = None
    ) -> Dict:
        """
        使用Qwen-Plus生成台风分析报告
        
        Args:
            typhoon_id: 台风编号
            typhoon_name: 台风名称
            prediction_data: 预测数据
            analysis_data: 分析数据
            
        Returns:
            Dict: 报告生成结果
        """
        try:
            # 构建提示词
            prompt = f"""请基于以下台风信息和预测数据，生成一份专业的中文台风分析简报。

# 台风基本信息
- 台风编号：{typhoon_id}
- 台风名称：{typhoon_name}

# 预测数据
{json.dumps(prediction_data, ensure_ascii=False, indent=2)}

# 分析要求
请生成一份结构化的台风分析简报，包含以下内容：
1. 台风概况（当前状态）
2. 路径趋势分析（基于预测数据）
3. 强度变化预测
4. 预计登陆点与时间（如果有）
5. 影响范围与风险评估
6. 防灾提示与建议

报告要求：
- 语言简洁专业，易于理解
- 数据准确，结论合理
- 突出关键信息（路径、强度、登陆点）
- 提供实用的防灾建议

请直接输出报告内容，不要使用markdown代码块包装。"""
            
            payload = {
                "model": self.qwen_plus_model,
                "input": {
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一位专业的气象分析专家，擅长分析台风路径和强度变化，能够生成清晰、专业、易于理解的台风分析报告。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                },
                "parameters": {
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{DASHSCOPE_BASE_URL}/services/aigc/text-generation/generation",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                # 提取生成的报告内容
                report_content = result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
                
                return {
                    "success": True,
                    "report_content": report_content.strip(),
                    "model_used": self.qwen_plus_model
                }
        
        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "report_content": ""
            }
    
    def _parse_json_from_text(self, text: str) -> Dict:
        """
        从文本中提取JSON数据
        
        Args:
            text: 包含JSON的文本
            
        Returns:
            Dict: 解析后的JSON数据
        """
        try:
            import re
            # 尝试提取JSON代码块
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                return {"raw_text": text}
        except json.JSONDecodeError:
            return {"raw_text": text}


# 创建全局服务实例
qwen_service = QwenService()

