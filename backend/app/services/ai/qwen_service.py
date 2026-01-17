"""
通义千问AI服务
"""
import asyncio
import base64
import json
import logging
from typing import Dict, Optional
from pathlib import Path
from io import BytesIO
import httpx
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


class QwenService:
    """通义千问服务类"""

    def __init__(self):
        self.api_key = settings.AI_API_KEY  # 使用统一的API Key
        self.base_url = settings.AI_API_BASE_URL  # 使用统一的Base URL
        self.timeout = settings.AI_TIMEOUT  # 使用配置的超时时间
        self.max_tokens = settings.AI_MAX_TOKENS  # 使用配置的最大token数
        self.qwen_text_model = settings.QWEN_TEXT_MODEL  # 文本生成模型
        self.qwen_vl_model = settings.QWEN_VL_MODEL  # 视觉理解模型
        self.max_retries = 3  # 最大重试次数
        self.retry_delay = 2  # 重试间隔（秒）
    
    async def generate_typhoon_report(
        self,
        typhoon_id: str,
        typhoon_name: str,
        report_type: str = "comprehensive",
        historical_data: Optional[Dict] = None,
        prediction_data: Optional[Dict] = None
    ) -> Dict:
        """
        使用Qwen-Plus生成台风分析报告（支持三种报告类型）

        Args:
            typhoon_id: 台风编号
            typhoon_name: 台风名称
            report_type: 报告类型（comprehensive/prediction/impact）
            historical_data: 历史路径数据（用于综合分析和影响评估）
            prediction_data: 预测数据（用于预测报告）

        Returns:
            Dict: 报告生成结果
        """
        logger.info(f"开始生成台风报告 - 台风ID: {typhoon_id}, 名称: {typhoon_name}, 类型: {report_type}")

        try:
            # 根据报告类型构建不同的提示词
            if report_type == "comprehensive":
                prompt = self._build_comprehensive_prompt(typhoon_id, typhoon_name, historical_data or {})
            elif report_type == "prediction":
                prompt = self._build_prediction_prompt(typhoon_id, typhoon_name, prediction_data or {})
            elif report_type == "impact":
                prompt = self._build_impact_prompt(typhoon_id, typhoon_name, historical_data or {})
            else:
                raise ValueError(f"不支持的报告类型: {report_type}")

            payload = {
                "model": self.qwen_text_model,  # 使用文本生成模型
                "messages": [
                    {
                        "role": "system",
                        "content": "你是气象分析专家，擅长生成详尽专业的台风报告。请使用Markdown格式输出，包括标题（##）、列表（-）、加粗（**）等格式。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "temperature": 0.6,
                "max_tokens": self.max_tokens,  # 使用配置的最大token数（8192）
                "top_p": 0.9,
                "frequency_penalty": 0.3,
                "response_format": {"type": "text"}
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                endpoint = f"{self.base_url}/chat/completions"
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers
                )

                # 确保响应使用 UTF-8 编码
                response.encoding = "utf-8"

                response.raise_for_status()
                result = response.json()

                # 记录API返回结果，便于调试
                logger.info(f"通义千问API返回结果: {json.dumps(result, ensure_ascii=False)[:500]}")

                # 提取生成的报告内容（OpenAI 兼容格式）
                report_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

                logger.info(f"通义千问报告生成成功 - 内容长度: {len(report_content)}")

                return {
                    "success": True,
                    "report_content": report_content.strip(),
                    "model_used": self.qwen_vl_model
                }
        
        except httpx.TimeoutException as e:
            error_msg = f"通义千问API调用超时（超过{self.timeout}秒）: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "report_content": ""
            }
        except httpx.HTTPStatusError as e:
            error_msg = f"通义千问API返回错误状态码 {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "report_content": ""
            }
        except Exception as e:
            error_msg = f"报告生成失败 ({type(e).__name__}): {str(e)}"
            logger.error(error_msg)
            logger.exception("详细错误堆栈:")
            return {
                "success": False,
                "error": error_msg,
                "report_content": ""
            }

    def _build_comprehensive_prompt(self, typhoon_id: str, typhoon_name: str, historical_data: Dict) -> str:
        """构建综合分析报告提示词"""
        return f"""基于历史路径数据生成台风综合分析报告：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史路径数据】
{json.dumps(historical_data, ensure_ascii=False, indent=2)}

【报告格式要求】
## 一、台风生命周期概况
   - 生成时间、消散时间、持续时长
   - 影响区域范围
   - 台风等级演变历程
   - 生命周期各阶段特征

## 二、路径特征分析
   - 移动路径详细描述（起点→转折点→终点）
   - 移动速度变化规律及原因分析
   - 路径转折点分析（时间、位置、原因）
   - 路径异常特征（如有）
   - 与历史台风路径对比

## 三、强度演变分析
   - 最大强度及出现时间、地点
   - 强度变化趋势（增强/减弱阶段详细分析）
   - 中心气压变化规律及影响因素
   - 最大风速变化规律及影响因素
   - 强度变化与环境因素关系

## 四、历史影响评估
   - 主要影响地区及影响程度
   - 灾害类型与程度（风灾、雨灾、潮灾）
   - 经济损失评估（如有数据）
   - 人员伤亡情况（如有数据）
   - 历史意义与参考价值

【输出要求】
- **使用Markdown格式输出**，包括标题（##）、列表（-）、加粗（**）等
- 报告总字数不少于**1500字**
- 每个章节至少包含**4-6个分析要点**
- 关键数据使用**加粗**突出显示
- 语言专业详尽，逻辑清晰
- 直接输出报告内容，不使用代码块包装"""

    def _build_prediction_prompt(self, typhoon_id: str, typhoon_name: str, prediction_data: Dict) -> str:
        """构建预测报告提示词"""
        return f"""基于预测数据生成台风预测报告：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【预测数据】
{json.dumps(prediction_data, ensure_ascii=False, indent=2)}

【报告格式要求】
## 一、当前状态
   - 当前位置（经纬度、地理位置描述）
   - 当前强度（风速、气压、等级）
   - 移动方向与速度
   - 当前影响范围

## 二、未来路径预测
   - 未来6小时路径趋势及关键点位
   - 未来12-24小时路径预测及可能影响区域
   - 未来48-72小时路径预测及登陆可能性
   - 预计登陆点与时间（如适用，包括置信度）
   - 路径不确定性分析
   - 可能的路径调整因素

## 三、强度变化预测
   - 未来24小时风速变化趋势及峰值预测
   - 未来48-72小时风速变化趋势
   - 气压变化趋势及最低值预测
   - 强度等级变化预测（热带低压→台风→强台风等）
   - 强度变化的影响因素分析
   - 强度预测的不确定性说明

## 四、预警建议
   - 重点关注区域及预警等级
   - 各区域预警时间窗口
   - 防范重点（风、雨、潮）
   - 应急准备建议（3-5条）
   - 监测关注要点

【输出要求】
- **使用Markdown格式输出**，包括标题（##）、列表（-）、加粗（**）等
- 报告总字数不少于**1500字**
- 每个章节至少包含**4-6个分析要点**
- 关键预测数据使用**加粗**突出显示
- 语言专业详尽，逻辑清晰
- 直接输出报告内容，不使用代码块包装"""

    def _build_impact_prompt(self, typhoon_id: str, typhoon_name: str, historical_data: Dict) -> str:
        """构建影响评估报告提示词"""
        return f"""基于历史数据生成台风影响评估报告：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史数据】
{json.dumps(historical_data, ensure_ascii=False, indent=2)}

【报告格式要求】
## 一、影响区域评估
   - 主要影响省份/城市详细列表
   - 影响范围（半径、面积估算）
   - 影响时段（开始时间、持续时间、结束时间）
   - 各区域受影响程度分级
   - 影响区域地理特征分析

## 二、灾害风险分析
   - **风灾风险**：最大风速、风力等级、阵风情况
   - **雨灾风险**：累计降雨量、降雨强度、持续时间
   - **潮灾风险**：风暴潮高度、海浪高度、潮位预测
   - **次生灾害风险**：山洪、泥石流、城市内涝等
   - 各类灾害的空间分布特征
   - 灾害叠加效应分析

## 三、影响程度评估
   - **人员安全风险等级**：高/中/低风险区域划分
   - **财产损失风险等级**：经济损失预估
   - **基础设施影响评估**：电力、通信、供水等
   - **交通运输影响评估**：公路、铁路、航空、水运
   - **农业影响评估**：农作物、渔业损失
   - **工商业影响评估**：停工停产情况

## 四、防灾减灾建议
   - **人员转移建议**（5-7条具体措施）
     - 转移时间窗口
     - 转移路线规划
     - 安置点选择
   - **物资准备建议**（5-7条具体措施）
     - 应急物资清单
     - 储备量建议
     - 储存位置
   - **应急响应建议**（5-7条具体措施）
     - 应急预案启动
     - 部门协调机制
     - 信息发布渠道

【输出要求】
- **使用Markdown格式输出**，包括标题（##）、列表（-）、加粗（**）等
- 报告总字数不少于**1500字**
- 每个章节至少包含**5-7个分析要点**
- 风险等级使用**加粗**明确标注
- 语言专业详尽，逻辑清晰
- 直接输出报告内容，不使用代码块包装"""
    
    def _parse_json_from_text(self, text) -> Dict:
        """
        从文本中提取JSON数据

        Args:
            text: 包含JSON的文本（可能是字符串、列表或其他类型）

        Returns:
            Dict: 解析后的JSON数据
        """
        try:
            import re

            # 类型检查和转换
            if text is None:
                logger.warning("_parse_json_from_text: 输入为None")
                return {"raw_text": ""}

            # 如果是列表，尝试提取文本内容
            if isinstance(text, list):
                logger.info(f"_parse_json_from_text: 输入是列表类型，长度={len(text)}")
                # 尝试从列表中提取文本
                text_parts = []
                for item in text:
                    if isinstance(item, dict):
                        # 如果是字典，尝试获取text字段
                        if "text" in item:
                            text_parts.append(str(item["text"]))
                        else:
                            text_parts.append(json.dumps(item, ensure_ascii=False))
                    elif isinstance(item, str):
                        text_parts.append(item)
                    else:
                        text_parts.append(str(item))
                text = " ".join(text_parts)
                logger.info(f"_parse_json_from_text: 列表转换后的文本长度={len(text)}")

            # 如果不是字符串，转换为字符串
            if not isinstance(text, str):
                logger.warning(f"_parse_json_from_text: 输入类型为{type(text)}，转换为字符串")
                text = str(text)

            # 如果文本为空
            if not text.strip():
                logger.warning("_parse_json_from_text: 文本为空")
                return {"raw_text": ""}

            # 尝试提取JSON代码块
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                logger.info(f"_parse_json_from_text: 找到JSON字符串，长度={len(json_str)}")
                return json.loads(json_str)
            else:
                logger.warning("_parse_json_from_text: 未找到JSON格式数据")
                return {"raw_text": text}

        except json.JSONDecodeError as e:
            logger.error(f"_parse_json_from_text: JSON解析失败: {e}")
            return {"raw_text": text if isinstance(text, str) else str(text)}
        except Exception as e:
            logger.error(f"_parse_json_from_text: 处理失败: {e}, 输入类型={type(text)}")
            return {"raw_text": str(text) if text is not None else ""}


# 创建全局服务实例
qwen_service = QwenService()

