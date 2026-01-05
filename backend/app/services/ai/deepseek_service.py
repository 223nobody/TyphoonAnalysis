"""
DeepSeek AI服务
提供基于DeepSeek API的台风报告生成功能

注意：DeepSeek主要用于文本生成，不支持图像分析。
图像分析功能请使用通义千问的视觉模型（qwen-vl-max）。

特性：
- 支持自动重试机制（最多3次）
- 详细的错误日志记录
- 当API调用失败时直接返回错误，不进行服务降级
"""
import asyncio
import json
import logging
from typing import Dict, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class DeepSeekService:
    """DeepSeek AI服务类 - 专注于文本报告生成"""

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_API_BASE_URL
        self.model = settings.DEEPSEEK_MODEL
        self.timeout = 90  # 超时时间90秒
        self.max_retries = 3  # 最大重试次数
        self.retry_delay = 2  # 重试间隔（秒）

    async def _make_api_request(
        self,
        payload: Dict,
        headers: Dict
    ) -> Dict:
        """
        发送API请求，支持重试机制

        Args:
            payload: 请求体
            headers: 请求头

        Returns:
            Dict: API响应结果

        Raises:
            Exception: 所有重试失败后抛出异常
        """
        endpoint = f"{self.base_url}/v1/chat/completions"
        last_error = None

        # 记录配置信息（用于诊断）
        logger.info(f"DeepSeek API配置 - Base URL: {self.base_url}, Model: {self.model}")
        logger.info(f"DeepSeek API配置 - API Key前缀: {self.api_key[:20]}...")

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"DeepSeek API请求 - 第{attempt}次尝试")
                logger.info(f"  - 请求URL: {endpoint}")
                logger.info(f"  - 请求模型: {payload.get('model')}")
                logger.info(f"  - 超时设置: {self.timeout}秒")

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers=headers
                    )

                    # 记录响应状态
                    logger.info(f"DeepSeek API响应 - 状态码: {response.status_code}")

                    # 检查是否需要重试的状态码
                    if response.status_code in [500, 502, 503, 504]:
                        error_msg = f"服务器错误 {response.status_code}"
                        logger.warning(f"DeepSeek API返回{response.status_code}，准备重试...")

                        # 尝试获取错误详情
                        try:
                            error_detail = response.text
                            logger.warning(f"错误详情（前500字符）: {error_detail[:500]}")

                            # 尝试解析JSON错误信息
                            try:
                                error_json = response.json()
                                logger.warning(f"错误JSON: {json.dumps(error_json, ensure_ascii=False, indent=2)}")
                            except:
                                pass
                        except Exception as parse_error:
                            logger.warning(f"无法解析错误详情: {parse_error}")

                        # 特殊处理503错误
                        if response.status_code == 503:
                            logger.error("=" * 60)
                            logger.error("DeepSeek API 503错误诊断:")
                            logger.error(f"  1. API端点: {endpoint}")
                            logger.error(f"  2. 可能原因: 代理服务不可用或模型通道配置错误")
                            logger.error(f"  3. 建议操作:")
                            logger.error(f"     - 检查代理服务 {self.base_url} 是否正常")
                            logger.error(f"     - 尝试切换到官方API: https://api.deepseek.com")
                            logger.error(f"     - 检查模型名称 '{self.model}' 是否正确")
                            logger.error(f"     - 查看配置文档: backend/DEEPSEEK_API_CONFIG.md")
                            logger.error("=" * 60)

                        last_error = Exception(f"{error_msg}: {error_detail[:200] if 'error_detail' in locals() else ''}")

                        # 如果不是最后一次尝试，等待后重试
                        if attempt < self.max_retries:
                            wait_time = self.retry_delay * attempt
                            logger.info(f"等待{wait_time}秒后重试...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise last_error

                    # 其他错误直接抛出
                    response.raise_for_status()

                    # 成功返回结果
                    result = response.json()
                    logger.info(f"DeepSeek API请求成功 - 第{attempt}次尝试")
                    logger.info(f"  - 响应数据: {json.dumps(result, ensure_ascii=False)[:200]}...")
                    return result

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"DeepSeek API超时 - 第{attempt}次尝试")
                logger.warning(f"  - 超时时间: {self.timeout}秒")
                logger.warning(f"  - 错误详情: {e}")
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.info(f"等待{wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(f"DeepSeek API HTTP错误 - 第{attempt}次尝试")
                logger.error(f"  - 状态码: {e.response.status_code}")
                logger.error(f"  - 错误信息: {e}")

                # 尝试获取响应内容
                try:
                    error_content = e.response.text
                    logger.error(f"  - 响应内容: {error_content[:500]}")
                except:
                    pass

                # 对于客户端错误（4xx），不重试
                if 400 <= e.response.status_code < 500:
                    logger.error("客户端错误（4xx），不进行重试")
                    raise
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    await asyncio.sleep(wait_time)

            except Exception as e:
                last_error = e
                logger.error(f"DeepSeek API请求异常 - 第{attempt}次尝试")
                logger.error(f"  - 异常类型: {type(e).__name__}")
                logger.error(f"  - 异常信息: {e}")
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    await asyncio.sleep(wait_time)

        # 所有重试都失败
        logger.error("DeepSeek API所有重试均失败")
        logger.error(f"  - 最后错误: {last_error}")
        raise last_error or Exception("DeepSeek API请求失败，已达到最大重试次数")

    async def generate_typhoon_report(
        self,
        typhoon_id: str,
        typhoon_name: str,
        prediction_data: Dict,
        analysis_data: Optional[Dict] = None
    ) -> Dict:
        """
        使用DeepSeek生成台风分析报告

        支持自动重试机制，当API调用失败时直接返回错误

        Args:
            typhoon_id: 台风编号
            typhoon_name: 台风名称
            prediction_data: 预测数据
            analysis_data: 分析数据（可选，未使用）

        Returns:
            Dict: 报告生成结果，包含以下字段：
                - success: bool - 是否成功
                - report_content: str - 报告内容
                - model_used: str - 使用的模型
                - error: str - 错误信息（仅在失败时）
        """
        logger.info(f"开始生成台风报告 - 台风ID: {typhoon_id}, 名称: {typhoon_name}")

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
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一位专业的气象分析专家，擅长分析台风路径和强度变化，能够生成清晰、专业、易于理解的台风分析报告。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 使用重试机制发送请求
            result = await self._make_api_request(payload, headers)

            # 提取生成的报告内容
            report_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            logger.info(f"DeepSeek报告生成成功 - 内容长度: {len(report_content)}")

            return {
                "success": True,
                "report_content": report_content.strip(),
                "model_used": self.model
            }

        except Exception as e:
            logger.error(f"DeepSeek报告生成失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误详情: {str(e)}")

            # 直接返回错误，不进行服务降级
            return {
                "success": False,
                "error": f"DeepSeek服务调用失败: {str(e)}",
                "report_content": ""
            }


# 创建全局服务实例
deepseek_service = DeepSeekService()
