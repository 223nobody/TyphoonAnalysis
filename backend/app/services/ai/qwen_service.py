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
        self.timeout = 120  # 使用配置的超时时间
        self.max_tokens = 2000  # 使用配置的最大token数
        self.qwen_text_model = settings.QWEN_TEXT_MODEL  # 文本生成模型
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
        endpoint = f"{self.base_url}/chat/completions"
        last_error = None

        # 记录配置信息（用于诊断）
        logger.info(f"通义千问API配置 - Base URL: {self.base_url}, Model: {payload.get('model')}")

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"通义千问API请求 - 第{attempt}次尝试")
                logger.info(f"  - 请求URL: {endpoint}")
                logger.info(f"  - 请求模型: {payload.get('model')}")
                logger.info(f"  - 超时设置: {self.timeout}秒")

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers=headers
                    )

                    # 确保响应使用 UTF-8 编码
                    response.encoding = "utf-8"

                    # 记录响应状态
                    logger.info(f"通义千问API响应 - 状态码: {response.status_code}")

                    # 其他错误直接抛出
                    response.raise_for_status()

                    # 成功返回结果
                    result = response.json()
                    logger.info(f"通义千问API请求成功 - 第{attempt}次尝试")
                    logger.info(f"  - 响应数据: {json.dumps(result, ensure_ascii=False)[:200]}...")
                    return result

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"通义千问API超时 - 第{attempt}次尝试")
                logger.warning(f"  - 超时时间: {self.timeout}秒")
                logger.warning(f"  - 错误详情: {e}")
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.info(f"等待{wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(f"通义千问API HTTP错误 - 第{attempt}次尝试")
                logger.error(f"  - 状态码: {e.response.status_code}")
                logger.error(f"  - 错误信息: {e}")

                # 尝试获取响应内容
                try:
                    error_content = e.response.text
                    logger.error(f"  - 响应内容: {error_content[:500]}")
                except:
                    pass

            except Exception as e:
                last_error = e
                logger.error(f"通义千问API请求异常 - 第{attempt}次尝试")
                logger.error(f"  - 异常类型: {type(e).__name__}")
                logger.error(f"  - 异常信息: {e}")
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    await asyncio.sleep(wait_time)

        # 所有重试都失败
        logger.error("通义千问API所有重试均失败")
        logger.error(f"  - 最后错误: {last_error}")
        raise last_error or Exception("通义千问API请求失败，已达到最大重试次数")

    # 章节并发生成扩展 - 开始
    async def _generate_single_chapter(
        self,
        chapter_name: str,
        chapter_prompt: str
    ) -> Dict:
        """
        生成单个章节内容（支持重试机制）

        Args:
            chapter_name: 章节名称
            chapter_prompt: 章节提示词

        Returns:
            Dict: 章节生成结果，包含以下字段：
                - success: bool - 是否成功
                - content: str - 章节内容
                - error: str - 错误信息（仅在失败时）
        """
        logger.info(f"开始生成章节 - 章节名称: {chapter_name}")

        try:
            payload = {
                "model": self.qwen_text_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是气象分析专家，擅长生成详尽专业的台风报告。请使用Markdown格式输出，包括标题（##）、列表（-）、加粗（**）等格式。"
                    },
                    {
                        "role": "user",
                        "content": chapter_prompt
                    }
                ],
                "stream": False,
                "temperature": 0.6,
                "max_tokens": self.max_tokens,
                "top_p": 0.9,
                "frequency_penalty": 0.3,
                "response_format": {"type": "text"}
            }

            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json"
            }

            # 使用重试机制发送请求
            result = await self._make_api_request(payload, headers)

            # 提取生成的章节内容
            chapter_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            logger.info(f"章节生成成功 - 章节名称: {chapter_name}, 内容长度: {len(chapter_content)}")

            return {
                "success": True,
                "content": chapter_content.strip(),
                "error": None
            }

        except Exception as e:
            logger.error(f"章节生成失败 - 章节名称: {chapter_name}")
            logger.error(f"  - 错误类型: {type(e).__name__}")
            logger.error(f"  - 错误详情: {str(e)}")

            return {
                "success": False,
                "content": "",
                "error": str(e)
            }

    def _build_chapter_prompt(
        self,
        report_type: str,
        chapter_name: str,
        typhoon_id: str,
        typhoon_name: str,
        data: Dict
    ) -> str:
        """
        构建单个章节的提示词

        Args:
            report_type: 报告类型（comprehensive/impact）
            chapter_name: 章节名称
            typhoon_id: 台风编号
            typhoon_name: 台风名称
            data: 数据（历史数据或预测数据）

        Returns:
            str: 章节提示词
        """
        # 综合分析报告章节
        if report_type == "comprehensive":
            if chapter_name == "台风生命周期概况":
                return f"""基于历史路径数据生成台风综合分析报告的第一章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史路径数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 一、台风生命周期概况

### 1.1 生命周期时间线
- 生成时间、消散时间、持续时长

### 1.2 影响区域范围
- 影响区域的地理范围描述

### 1.3 台风等级演变
- 台风等级演变历程

### 1.4 生命周期特征
- 生命周期各阶段特征

【Markdown格式规范】
1. **标题层级**：
   - 章节标题使用 `##`（二级标题）
   - 子章节使用 `###`（三级标题）
   - 标题后空一行再开始内容

2. **列表格式**：
   - 使用 `-` 符号表示无序列表
   - 列表项之间不空行
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 时间格式：`YYYY年MM月DD日 HH:mm`（如：2024年09月15日 08:00）
   - 经纬度格式：`XX.XX°N/S, XX.XX°E/W`（如：25.50°N, 120.30°E）
   - 风速格式：`XX m/s（XX级）`（如：45 m/s（14级））
   - 气压格式：`XXX hPa`（如：950 hPa）
   - 持续时长：`X天X小时`（如：5天12小时）

4. **强调格式**：
   - 关键数据使用 `**加粗**`
   - 重要术语使用 `*斜体*`
   - 台风等级、风力等级使用加粗

5. **段落间距**：
   - 子章节之间空一行
   - 列表前后各空一行
   - 段落之间空一行

【输出要求】
- 本章节字数不少于**250字**
- 至少包含**4-6个分析要点**
- 语言专业详尽，逻辑清晰
- 直接输出章节内容，不使用代码块包装
- 严格遵循上述Markdown格式规范"""

            elif chapter_name == "路径特征分析":
                return f"""基于历史路径数据生成台风综合分析报告的第二章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史路径数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 二、路径特征分析

### 2.1 移动路径描述
- 移动路径详细描述（起点→转折点→终点）

### 2.2 移动速度分析
- 移动速度变化规律及原因分析

### 2.3 路径转折点分析
- 路径转折点分析（时间、位置、原因）

### 2.4 路径特征评估
- 路径异常特征（如有）
- 与历史台风路径对比

【Markdown格式规范】
1. **标题层级**：
   - 章节标题使用 `##`（二级标题）
   - 子章节使用 `###`（三级标题）
   - 标题后空一行再开始内容

2. **列表格式**：
   - 使用 `-` 符号表示无序列表
   - 列表项之间不空行
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 时间格式：`YYYY年MM月DD日 HH:mm`（如：2024年09月15日 08:00）
   - 经纬度格式：`XX.XX°N/S, XX.XX°E/W`（如：25.50°N, 120.30°E）
   - 移动速度：`XX km/h`（如：25 km/h）
   - 移动方向：`向XX方向移动`（如：向西北方向移动）

4. **强调格式**：
   - 关键位置数据使用 `**加粗**`
   - 转折点时间使用 `**加粗**`
   - 移动速度变化使用加粗

5. **段落间距**：
   - 子章节之间空一行
   - 列表前后各空一行
   - 段落之间空一行

【输出要求】
- 本章节字数不少于**250字**
- 至少包含**4-6个分析要点**
- 语言专业详尽，逻辑清晰
- 直接输出章节内容，不使用代码块包装
- 严格遵循上述Markdown格式规范"""

            elif chapter_name == "强度演变分析":
                return f"""基于历史路径数据生成台风综合分析报告的第三章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史路径数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 三、强度演变分析

### 3.1 最大强度评估
- 最大强度及出现时间、地点

### 3.2 强度变化趋势
- 强度变化趋势（增强/减弱阶段详细分析）

### 3.3 气压演变规律
- 中心气压变化规律及影响因素

### 3.4 风速演变规律
- 最大风速变化规律及影响因素

### 3.5 环境因素影响
- 强度变化与环境因素关系

【Markdown格式规范】
1. **标题层级**：
   - 章节标题使用 `##`（二级标题）
   - 子章节使用 `###`（三级标题）
   - 标题后空一行再开始内容

2. **列表格式**：
   - 使用 `-` 符号表示无序列表
   - 列表项之间不空行
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 时间格式：`YYYY年MM月DD日 HH:mm`（如：2024年09月15日 08:00）
   - 风速格式：`XX m/s（XX级）`（如：45 m/s（14级））
   - 气压格式：`XXX hPa`（如：950 hPa）
   - 台风等级：`*热带低压*`、`*热带风暴*`、`*强热带风暴*`、`*台风*`、`*强台风*`、`*超强台风*`

4. **强调格式**：
   - 最大风速、最低气压使用 `**加粗**`
   - 台风等级使用 `*斜体*`
   - 强度变化阶段使用加粗

5. **段落间距**：
   - 子章节之间空一行
   - 列表前后各空一行
   - 段落之间空一行

【输出要求】
- 本章节字数不少于**250字**
- 至少包含**4-6个分析要点**
- 语言专业详尽，逻辑清晰
- 直接输出章节内容，不使用代码块包装
- 严格遵循上述Markdown格式规范"""

            elif chapter_name == "历史影响评估":
                return f"""基于历史路径数据生成台风综合分析报告的第四章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史路径数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 四、历史影响评估

### 4.1 影响地区分析
- 主要影响地区及影响程度

### 4.2 灾害类型评估
- 灾害类型与程度（风灾、雨灾、潮灾）

### 4.3 损失评估
- 经济损失评估（如有数据）
- 人员伤亡情况（如有数据）

### 4.4 历史意义
- 历史意义与参考价值

【Markdown格式规范】
1. **标题层级**：
   - 章节标题使用 `##`（二级标题）
   - 子章节使用 `###`（三级标题）
   - 标题后空一行再开始内容

2. **列表格式**：
   - 使用 `-` 符号表示无序列表
   - 列表项之间不空行
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 影响程度：`**严重**`、`**较重**`、`**一般**`
   - 经济损失：`XX亿元`（如：150亿元）
   - 人员伤亡：`XX人`（如：50人）
   - 降雨量：`XXX mm`（如：500 mm）

4. **强调格式**：
   - 影响程度使用 `**加粗**`
   - 灾害类型使用 `*斜体*`
   - 损失数据使用加粗

5. **段落间距**：
   - 子章节之间空一行
   - 列表前后各空一行
   - 段落之间空一行

【输出要求】
- 本章节字数不少于**250字**
- 至少包含**4-6个分析要点**
- 语言专业详尽，逻辑清晰
- 直接输出章节内容，不使用代码块包装
- 严格遵循上述Markdown格式规范"""

        # 影响评估报告章节
        elif report_type == "impact":
            if chapter_name == "影响区域评估":
                return f"""基于历史数据生成台风影响评估报告的第一章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 一、影响区域评估

### 1.1 主要影响区域
- 主要影响省份/城市详细列表

### 1.2 影响范围评估
- 影响范围（半径、面积估算）

### 1.3 影响时段分析
- 影响时段（开始时间、持续时间、结束时间）

### 1.4 影响程度分级
- 各区域受影响程度分级

### 1.5 地理特征分析
- 影响区域地理特征分析

【Markdown格式规范】
1. **标题层级**：
   - 章节标题使用 `##`（二级标题）
   - 子章节使用 `###`（三级标题）
   - 标题后空一行再开始内容

2. **列表格式**：
   - 使用 `-` 符号表示无序列表
   - 列表项之间不空行
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 时间格式：`YYYY年MM月DD日 HH:mm`（如：2024年09月15日 08:00）
   - 影响范围：`半径XXX km，面积约XX万平方公里`
   - 持续时间：`X天X小时`（如：3天6小时）
   - 影响程度：`**严重影响**`、`**较重影响**`、`**一般影响**`

4. **强调格式**：
   - 省份/城市名称使用 `**加粗**`
   - 影响程度等级使用 `**加粗**`
   - 关键时间节点使用加粗

5. **段落间距**：
   - 子章节之间空一行
   - 列表前后各空一行
   - 段落之间空一行

【输出要求】
- 本章节字数不少于**250字**
- 至少包含**5-7个分析要点**
- 语言专业详尽，逻辑清晰
- 直接输出章节内容，不使用代码块包装
- 严格遵循上述Markdown格式规范"""

            elif chapter_name == "灾害风险分析":
                return f"""基于历史数据生成台风影响评估报告的第二章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 二、灾害风险分析

### 2.1 风灾风险
- 最大风速、风力等级、阵风情况

### 2.2 雨灾风险
- 累计降雨量、降雨强度、持续时间

### 2.3 潮灾风险
- 风暴潮高度、海浪高度、潮位预测

### 2.4 次生灾害风险
- 山洪、泥石流、城市内涝等

### 2.5 灾害分布特征
- 各类灾害的空间分布特征

### 2.6 灾害叠加效应
- 灾害叠加效应分析

【Markdown格式规范】
1. **标题层级**：
   - 章节标题使用 `##`（二级标题）
   - 子章节使用 `###`（三级标题）
   - 标题后空一行再开始内容

2. **列表格式**：
   - 使用 `-` 符号表示无序列表
   - 列表项之间不空行
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 风速格式：`XX m/s（XX级）`（如：45 m/s（14级））
   - 降雨量：`XXX mm`（如：500 mm）
   - 降雨强度：`XX mm/h`（如：50 mm/h）
   - 风暴潮：`X.X米`（如：3.5米）
   - 海浪高度：`X-X米`（如：5-8米）
   - 风险等级：`**高风险**`、`**中风险**`、`**低风险**`

4. **强调格式**：
   - 风险等级使用 `**加粗**`
   - 灾害类型使用 `*斜体*`
   - 关键数据使用加粗

5. **段落间距**：
   - 子章节之间空一行
   - 列表前后各空一行
   - 段落之间空一行

【输出要求】
- 本章节字数不少于**250字**
- 至少包含**5-7个分析要点**
- 语言专业详尽，逻辑清晰
- 直接输出章节内容，不使用代码块包装
- 严格遵循上述Markdown格式规范"""

            elif chapter_name == "影响程度评估":
                return f"""基于历史数据生成台风影响评估报告的第三章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 三、影响程度评估

### 3.1 人员安全风险
- 高/中/低风险区域划分

### 3.2 财产损失风险
- 经济损失预估

### 3.3 基础设施影响
- 电力、通信、供水等

### 3.4 交通运输影响
- 公路、铁路、航空、水运

### 3.5 农业影响
- 农作物、渔业损失

### 3.6 工商业影响
- 停工停产情况

【Markdown格式规范】
1. **标题层级**：
   - 章节标题使用 `##`（二级标题）
   - 子章节使用 `###`（三级标题）
   - 标题后空一行再开始内容

2. **列表格式**：
   - 使用 `-` 符号表示无序列表
   - 列表项之间不空行
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 风险等级：`**高风险**`、`**中风险**`、`**低风险**`
   - 经济损失：`XX亿元`（如：150亿元）
   - 受灾人口：`XX万人`（如：50万人）
   - 农作物损失：`XX万亩`（如：30万亩）
   - 停工企业：`XX家`（如：200家）

4. **强调格式**：
   - 风险等级使用 `**加粗**`
   - 影响类型使用 `*斜体*`
   - 损失数据使用加粗

5. **段落间距**：
   - 子章节之间空一行
   - 列表前后各空一行
   - 段落之间空一行

【输出要求】
- 本章节字数不少于**250字**
- 至少包含**5-7个分析要点**
- 语言专业详尽，逻辑清晰
- 直接输出章节内容，不使用代码块包装
- 严格遵循上述Markdown格式规范"""

            elif chapter_name == "防灾减灾建议":
                return f"""基于历史数据生成台风影响评估报告的第四章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 四、防灾减灾建议

### 4.1 人员转移建议
- 转移时间窗口
- 转移路线规划
- 安置点选择
- 特殊人群安置
- 转移物资准备

### 4.2 物资准备建议
- 应急物资清单
- 储备量建议
- 储存位置
- 物资调配方案
- 物资补充机制

### 4.3 应急响应建议
- 应急预案启动
- 部门协调机制
- 信息发布渠道
- 应急队伍部署
- 应急演练要求

【Markdown格式规范】
1. **标题层级**：
   - 章节标题使用 `##`（二级标题）
   - 子章节使用 `###`（三级标题）
   - 标题后空一行再开始内容

2. **列表格式**：
   - 使用 `-` 符号表示无序列表
   - 列表项之间不空行
   - 嵌套列表使用4空格缩进
   - 具体措施使用嵌套列表展示

3. **数据格式规范**：
   - 时间窗口：`YYYY年MM月DD日 HH:mm - HH:mm`
   - 物资数量：`XX件/套/箱`（如：1000件）
   - 人员数量：`XX人`（如：500人）
   - 响应级别：`**I级响应**`、`**II级响应**`、`**III级响应**`、`**IV级响应**`

4. **强调格式**：
   - 建议类别使用 `**加粗**`
   - 响应级别使用 `**加粗**`
   - 关键措施使用加粗

5. **段落间距**：
   - 子章节之间空一行
   - 列表前后各空一行
   - 段落之间空一行

【输出要求】
- 本章节字数不少于**250字**
- 至少包含**5-7个分析要点**
- 每类建议至少包含**3-5条具体措施**
- 语言专业详尽，逻辑清晰
- 直接输出章节内容，不使用代码块包装
- 严格遵循上述Markdown格式规范"""

        return ""
    # 章节并发生成扩展 - 结束

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
            Dict: 报告生成结果，包含以下字段：
                - success: bool - 是否成功
                - report_content: str - 报告内容
                - model_used: str - 使用的模型
                - error: str - 错误信息（仅在失败时）
        """
        logger.info(f"开始生成台风报告 - 台风ID: {typhoon_id}, 名称: {typhoon_name}, 类型: {report_type}")

        try:
            # 章节并发生成扩展 - 综合分析报告和影响评估报告使用章节并发生成
            if report_type in ["comprehensive", "impact"]:
                # 定义章节列表
                if report_type == "comprehensive":
                    chapters = ["台风生命周期概况", "路径特征分析", "强度演变分析", "历史影响评估"]
                    data = historical_data or {}
                else:  # impact
                    chapters = ["影响区域评估", "灾害风险分析", "影响程度评估", "防灾减灾建议"]
                    data = historical_data or {}

                logger.info(f"开始并发生成{len(chapters)}个章节")

                # 构建所有章节的提示词
                chapter_prompts = []
                for chapter_name in chapters:
                    prompt = self._build_chapter_prompt(
                        report_type=report_type,
                        chapter_name=chapter_name,
                        typhoon_id=typhoon_id,
                        typhoon_name=typhoon_name,
                        data=data
                    )
                    chapter_prompts.append((chapter_name, prompt))

                # 并发生成所有章节
                chapter_tasks = [
                    self._generate_single_chapter(chapter_name, prompt)
                    for chapter_name, prompt in chapter_prompts
                ]

                chapter_results = await asyncio.gather(*chapter_tasks, return_exceptions=True)

                # 合并章节结果
                report_parts = []
                failed_chapters = []

                for idx, (chapter_name, result) in enumerate(zip(chapters, chapter_results)):
                    if isinstance(result, Exception):
                        # 异常情况
                        error_msg = str(result)
                        logger.error(f"章节生成异常 - 章节名称: {chapter_name}, 异常: {error_msg}")
                        report_parts.append(f"\n\n【该章节生成失败：{error_msg}】\n\n")
                        failed_chapters.append(f"{chapter_name}({error_msg})")
                    elif result.get("success"):
                        # 成功生成
                        report_parts.append(result.get("content", ""))
                    else:
                        # 生成失败
                        error_msg = result.get("error", "未知错误")
                        logger.error(f"章节生成失败 - 章节名称: {chapter_name}, 错误: {error_msg}")
                        report_parts.append(f"\n\n【该章节生成失败：{error_msg}】\n\n")
                        failed_chapters.append(f"{chapter_name}({error_msg})")

                # 合并完整报告
                report_content = "\n\n".join(report_parts)

                logger.info(f"通义千问报告生成完成 - 总内容长度: {len(report_content)}, 失败章节数: {len(failed_chapters)}")

                # 构建返回结果
                result_dict = {
                    "success": True,
                    "report_content": report_content.strip(),
                    "model_used": self.qwen_text_model
                }

                # 如果有失败章节，添加错误信息
                if failed_chapters:
                    result_dict["error"] = f"部分章节生成失败: {', '.join(failed_chapters)}"

                return result_dict

            # 预测报告保持原有逻辑
            elif report_type == "prediction":
                prompt = self._build_prediction_prompt(typhoon_id, typhoon_name, prediction_data or {})

                payload = {
                    "model": self.qwen_text_model,
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
                    "max_tokens": self.max_tokens,
                    "top_p": 0.9,
                    "frequency_penalty": 0.3,
                    "response_format": {"type": "text"}
                }

                headers = {
                    "Authorization": self.api_key,
                    "Content-Type": "application/json"
                }

                # 使用重试机制发送请求
                result = await self._make_api_request(payload, headers)

                # 提取生成的报告内容
                report_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

                logger.info(f"通义千问报告生成成功 - 内容长度: {len(report_content)}")

                return {
                    "success": True,
                    "report_content": report_content.strip(),
                    "model_used": self.qwen_text_model
                }
            else:
                raise ValueError(f"不支持的报告类型: {report_type}")

        except Exception as e:
            logger.error(f"通义千问报告生成失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误详情: {str(e)}")

            return {
                "success": False,
                "error": f"通义千问服务调用失败: {str(e)}",
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

