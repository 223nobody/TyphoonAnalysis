"""
GLM AI服务
提供基于GLM API的台风报告生成功能

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


class GlmService:
    """GLM AI服务类 - 专注于文本报告生成"""

    def __init__(self):
        self.api_key = settings.AI_API_KEY  # 使用统一的API Key
        self.base_url = settings.AI_API_BASE_URL  # 使用统一的Base URL
        self.model = settings.GLM_MODEL
        self.timeout = settings.AI_REPORT_TIMEOUT
        self.max_tokens = settings.AI_REPORT_MAX_TOKENS
        self.max_retries = settings.AI_REPORT_MAX_RETRIES
        self.retry_delay = settings.AI_REPORT_RETRY_DELAY
        self.temperature = settings.AI_REPORT_TEMPERATURE
        self.top_p = settings.AI_REPORT_TOP_P

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
        logger.info(f"GLM API配置 - Base URL: {self.base_url}, Model: {self.model}")

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"GLM API请求 - 第{attempt}次尝试")
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
                    logger.info(f"GLM API响应 - 状态码: {response.status_code}")

                    # 其他错误直接抛出
                    response.raise_for_status()

                    # 成功返回结果
                    result = response.json()
                    logger.info(f"GLM API请求成功 - 第{attempt}次尝试")
                    logger.info(f"  - 响应数据: {json.dumps(result, ensure_ascii=False)[:200]}...")
                    return result

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"GLM API超时 - 第{attempt}次尝试")
                logger.warning(f"  - 超时时间: {self.timeout}秒")
                logger.warning(f"  - 错误详情: {e}")
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.info(f"等待{wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(f"GLM API HTTP错误 - 第{attempt}次尝试")
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
                logger.error(f"GLM API请求异常 - 第{attempt}次尝试")
                logger.error(f"  - 异常类型: {type(e).__name__}")
                logger.error(f"  - 异常信息: {e}")
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    await asyncio.sleep(wait_time)

        # 所有重试都失败
        logger.error("GLM API所有重试均失败")
        logger.error(f"  - 最后错误: {last_error}")
        raise last_error or Exception("GLM API请求失败，已达到最大重试次数")

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
                "model": self.model,
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
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "top_p": self.top_p,
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

---

### 1.1 🕐 生命周期时间线

> **关键时间节点**

- **生成时间**：YYYY年MM月DD日 HH:mm（经纬度位置）
- **消散时间**：YYYY年MM月DD日 HH:mm（经纬度位置）
- **持续时长**：X天X小时（总计XX小时）

### 1.2 📍 影响区域范围

> **地理覆盖范围**

- **主要影响区域**：列出省份/地区
- **影响半径**：约XX~XX km
- **覆盖面积**：约XX万平方公里
- **最大影响时段**：YYYY年MM月DD日至DD日

### 1.3 📊 台风等级演变

> **强度变化历程**

| 时间段 | 台风等级 | 中心气压 | 最大风速 |
|--------|----------|----------|----------|
| 初期 | *热带低压* | XXX hPa | XX m/s |
| 发展期 | *台风* | XXX hPa | XX m/s |
| 巅峰期 | *强台风* | XXX hPa | XX m/s |
| 衰减期 | *热带风暴* | XXX hPa | XX m/s |

**📌 关键结论**：台风在XX时段达到最强，等级为*XX*，持续时间约XX小时。

### 1.4 🔄 生命周期特征

**各阶段特征分析**：

1. **生成阶段**（X天）
    - 初始位置及环境条件
    - 发展速度及影响因素
    
2. **发展阶段**（X天）
    - 强度增强规律
    - 路径调整特征
    
3. **成熟阶段**（X天）
    - 最强时段表现
    - 影响范围扩大情况
    
4. **衰减阶段**（X天）
    - 减弱速度及原因
    - 残余影响评估

---

【Markdown格式规范】
1. **视觉层次**：
   - 章节开头使用分隔线 `---`
   - 重要数据使用引用块 `>`
   - 对比数据使用表格展示

2. **列表格式**：
   - 有序步骤使用数字列表 `1. 2. 3.`
   - 并列要点使用无序列表 `-`
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 时间：`YYYY年MM月DD日 HH:mm`
   - 经纬度：`XX.XX°N/S, XX.XX°E/W`
   - 风速：`XX m/s（XX级）`或范围`XX~XX m/s`
   - 气压：`XXX hPa`或范围`XXX~XXX hPa`
   - 距离：`XX km`或范围`XX~XX km`
   - 百分比：`XX%`
   - 温度：`XX°C`

4. **视觉强调元素**：
   - 时间节点使用 `🕐` 图标
   - 位置信息使用 `📍` 图标
   - 数据统计使用 `📊` 图标
   - 重要提示使用 `📌` 图标
   - 警告信息使用 `⚠️` 图标

5. **强调格式**：
   - 关键数据使用 `**加粗**`
   - 台风等级使用 `*斜体*`
   - 关键结论单独成段并加粗

【输出要求】
- 本章节字数不少于**250字**
- 严格按照上述格式输出
- 直接输出章节内容，不使用代码块包装
- 确保表格、列表、图标正确显示"""

            elif chapter_name == "路径特征分析":
                return f"""基于历史路径数据生成台风综合分析报告的第二章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史路径数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 二、路径特征分析

---

### 2.1 🗺️ 移动路径描述

> **路径关键节点**

**完整路径轨迹**：

1. **起点**：XX.XX°N, XX.XX°E（地理位置描述）
2. **关键转折点**：XX.XX°N, XX.XX°E（转折时间及原因）
3. **登陆点**（如有）：XX.XX°N, XX.XX°E（登陆时间及地点）
4. **终点**：XX.XX°N, XX.XX°E（消散位置）

**📌 路径总结**：台风整体呈XX方向移动，路径长度约XX km，主要影响XX区域。

### 2.2 ⚡ 移动速度分析

> **速度变化规律**

| 阶段 | 时间段 | 平均速度 | 速度特征 |
|------|--------|----------|----------|
| 初期 | XX日-XX日 | XX km/h | 缓慢移动 |
| 加速期 | XX日-XX日 | XX~XX km/h | 快速移动 |
| 减速期 | XX日-XX日 | XX km/h | 逐渐减慢 |

**速度变化原因**：
- 副热带高压影响
- 西风槽引导作用
- 地形摩擦效应

### 2.3 🔄 路径转折点分析

**主要转折点详情**：

1. **第一转折点**（YYYY年MM月DD日 HH:mm）
    - 位置：XX.XX°N, XX.XX°E
    - 转折角度：约XX°
    - 转折原因：副热带高压减弱/西风槽影响

2. **第二转折点**（如有）
    - 位置：XX.XX°N, XX.XX°E
    - 转折角度：约XX°
    - 转折原因：地形影响/环流调整

### 2.4 📊 路径特征评估

**异常特征识别**：

- ⚠️ **路径异常**：是否存在突然转向、停滞、回旋等异常行为
- **历史对比**：与历史同期台风路径的相似度约XX%
- **预测难度**：路径复杂度评级（高/中/低）

**📌 关键结论**：本次台风路径XX（规律/异常），主要受XX系统影响。

---

【Markdown格式规范】
1. **视觉层次**：
   - 章节开头使用分隔线 `---`
   - 重要数据使用引用块 `>`
   - 对比数据使用表格展示

2. **列表格式**：
   - 有序步骤使用数字列表 `1. 2. 3.`
   - 并列要点使用无序列表 `-`
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 时间：`YYYY年MM月DD日 HH:mm`
   - 经纬度：`XX.XX°N/S, XX.XX°E/W`
   - 速度：`XX km/h`或范围`XX~XX km/h`
   - 距离：`XX km`
   - 角度：`XX°`
   - 百分比：`XX%`

4. **视觉强调元素**：
   - 路径信息使用 `🗺️` 图标
   - 速度信息使用 `⚡` 图标
   - 转折点使用 `🔄` 图标
   - 数据统计使用 `📊` 图标
   - 警告信息使用 `⚠️` 图标
   - 重要提示使用 `📌` 图标

5. **强调格式**：
   - 关键数据使用 `**加粗**`
   - 关键结论单独成段并加粗

【输出要求】
- 本章节字数不少于**250字**
- 严格按照上述格式输出
- 直接输出章节内容，不使用代码块包装
- 确保表格、列表、图标正确显示"""

            elif chapter_name == "强度演变分析":
                return f"""基于历史路径数据生成台风综合分析报告的第三章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史路径数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 三、强度演变分析

---

### 3.1 💪 最大强度评估

> **巅峰时刻数据**

- **最大风速**：**XX m/s（XX级）**
- **最低气压**：**XXX hPa**
- **出现时间**：YYYY年MM月DD日 HH:mm
- **出现位置**：XX.XX°N, XX.XX°E（地理位置）
- **台风等级**：*超强台风/强台风/台风*

**📌 强度评级**：本次台风最大强度在历史同期台风中排名前XX%。

### 3.2 📈 强度变化趋势

> **完整演变过程**

| 阶段 | 时间段 | 风速范围 | 气压范围 | 等级变化 |
|------|--------|----------|----------|----------|
| 生成期 | XX日-XX日 | XX~XX m/s | XXX~XXX hPa | *热带低压* |
| 增强期 | XX日-XX日 | XX~XX m/s | XXX~XXX hPa | *热带风暴→台风* |
| 巅峰期 | XX日-XX日 | XX~XX m/s | XXX~XXX hPa | *强台风* |
| 减弱期 | XX日-XX日 | XX~XX m/s | XXX~XXX hPa | *台风→热带风暴* |

**强度变化特征**：

1. **增强阶段**（持续XX小时）
    - 增强速度：XX m/s/天
    - 主要影响因素：海温XX°C、水汽充足

2. **维持阶段**（持续XX小时）
    - 强度波动范围：±X m/s
    - 维持原因：环境条件稳定

3. **减弱阶段**（持续XX小时）
    - 减弱速度：XX m/s/天
    - 主要原因：登陆/冷空气/海温下降

### 3.3 🌡️ 气压演变规律

> **中心气压变化**

**气压变化曲线特征**：
- **最低气压**：XXX hPa（YYYY年MM月DD日）
- **气压降幅**：从XXX hPa降至XXX hPa，降幅XX hPa
- **降压速度**：最快XX hPa/12h（快速增强期）

**影响因素分析**：
- 海表温度：XX~XX°C（适宜/偏高/偏低）
- 垂直风切变：XX m/s（弱/中等/强）
- 高空辐散条件：良好/一般/较差

### 3.4 💨 风速演变规律

> **最大风速变化**

**风速变化特征**：
- **最大风速**：XX m/s（XX级）
- **风速增幅**：从XX m/s增至XX m/s，增幅XX m/s
- **增速最快时段**：YYYY年MM月DD日至DD日（XX m/s/天）

**风速分布特征**：
- 7级风圈半径：XX~XX km
- 10级风圈半径：XX~XX km
- 12级风圈半径：XX~XX km

### 3.5 🌍 环境因素影响

**关键环境要素**：

1. **海洋条件**
    - 海表温度：XX~XX°C
    - 海洋热含量：高/中/低

2. **大气环流**
    - 副热带高压：强度XX、位置XX
    - 西风槽：影响程度XX

3. **其他因素**
    - 垂直风切变：XX m/s
    - 水汽输送：充足/一般/不足

**📌 关键结论**：台风强度变化主要受XX因素控制，XX阶段增强最快。

---

【Markdown格式规范】
1. **视觉层次**：
   - 章节开头使用分隔线 `---`
   - 重要数据使用引用块 `>`
   - 对比数据使用表格展示

2. **列表格式**：
   - 有序步骤使用数字列表 `1. 2. 3.`
   - 并列要点使用无序列表 `-`
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 时间：`YYYY年MM月DD日 HH:mm`
   - 风速：`XX m/s（XX级）`或范围`XX~XX m/s`
   - 气压：`XXX hPa`或范围`XXX~XXX hPa`
   - 温度：`XX°C`或范围`XX~XX°C`
   - 距离：`XX km`或范围`XX~XX km`
   - 速度变化：`XX m/s/天`或`XX hPa/12h`

4. **视觉强调元素**：
   - 强度信息使用 `💪` 图标
   - 趋势分析使用 `📈` 图标
   - 温度信息使用 `🌡️` 图标
   - 风速信息使用 `💨` 图标
   - 环境因素使用 `🌍` 图标
   - 重要提示使用 `📌` 图标

5. **强调格式**：
   - 关键数据使用 `**加粗**`
   - 台风等级使用 `*斜体*`
   - 关键结论单独成段并加粗

【输出要求】
- 本章节字数不少于**250字**
- 严格按照上述格式输出
- 直接输出章节内容，不使用代码块包装
- 确保表格、列表、图标正确显示"""

            elif chapter_name == "历史影响评估":
                return f"""基于历史路径数据生成台风综合分析报告的第四章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史路径数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 四、历史影响评估

---

### 4.1 🌏 影响地区分析

> **主要受灾区域**

| 地区 | 影响程度 | 影响时段 | 主要灾害 |
|------|----------|----------|----------|
| XX省XX市 | **严重** | XX日-XX日 | 风灾、雨灾 |
| XX省XX市 | **较重** | XX日-XX日 | 雨灾、潮灾 |
| XX省XX市 | **一般** | XX日-XX日 | 风灾 |

**影响范围统计**：
- 受影响省份：XX个
- 受影响城市：XX个
- 受灾人口：约XX万人
- 转移安置人口：约XX万人

### 4.2 ⚠️ 灾害类型评估

> **三大主要灾害**

**1. 风灾影响**
- **最大风力**：XX级（XX m/s）
- **持续时间**：XX小时
- **影响范围**：XX km半径
- **主要损失**：房屋受损XX间、树木倒伏XX棵

**2. 雨灾影响**
- **最大降雨量**：XXX mm（XX市XX区）
- **累计降雨**：XX~XXX mm
- **降雨时长**：XX小时
- **主要损失**：农田受淹XX万亩、道路中断XX条

**3. 潮灾影响**
- **最大风暴潮**：X.X米
- **海浪高度**：X~X米
- **影响海岸线**：约XX km
- **主要损失**：海堤损毁XX处、渔船受损XX艘

### 4.3 💰 损失评估

> **经济社会影响**

**直接经济损失**：
- **总损失**：约**XX亿元**
- **农业损失**：XX亿元（农作物XX万亩）
- **工业损失**：XX亿元（停工企业XX家）
- **基础设施损失**：XX亿元（道路、电力、通信等）
- **居民财产损失**：XX亿元（房屋、车辆等）

**人员伤亡情况**：
- 死亡人数：XX人
- 失踪人数：XX人
- 受伤人数：XX人

⚠️ **注**：如无具体数据，说明"暂无详细统计数据"。

### 4.4 📚 历史意义

**历史地位评估**：

1. **强度排名**
    - 在近XX年同期台风中排名第XX位
    - 登陆强度为历史第XX强

2. **影响范围**
    - 影响范围为近XX年最广/较广/一般
    - 持续时间为历史第XX长

3. **参考价值**
    - 路径特征：典型/罕见，可作为XX类型台风参考
    - 强度演变：具有XX特征，值得深入研究
    - 防灾经验：为未来类似台风防御提供XX借鉴

**📌 关键结论**：本次台风在XX方面具有显著特征，对XX地区造成XX影响，为历史上XX台风之一。

---

【Markdown格式规范】
1. **视觉层次**：
   - 章节开头使用分隔线 `---`
   - 重要数据使用引用块 `>`
   - 对比数据使用表格展示

2. **列表格式**：
   - 有序步骤使用数字列表 `1. 2. 3.`
   - 并列要点使用无序列表 `-`
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 影响程度：`**严重**`、`**较重**`、`**一般**`
   - 经济损失：`XX亿元`
   - 人员数量：`XX人`或`XX万人`
   - 面积：`XX万亩`或`XX万平方公里`
   - 降雨量：`XXX mm`
   - 风暴潮：`X.X米`
   - 距离：`XX km`

4. **视觉强调元素**：
   - 地区信息使用 `🌏` 图标
   - 灾害警告使用 `⚠️` 图标
   - 经济损失使用 `💰` 图标
   - 历史意义使用 `📚` 图标
   - 重要提示使用 `📌` 图标

5. **强调格式**：
   - 影响程度使用 `**加粗**`
   - 关键数据使用 `**加粗**`
   - 关键结论单独成段并加粗

【输出要求】
- 本章节字数不少于**250字**
- 严格按照上述格式输出
- 直接输出章节内容，不使用代码块包装
- 确保表格、列表、图标正确显示"""

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

---

### 1.1 🌏 主要影响区域

> **受影响省份/城市清单**

| 省份 | 主要城市 | 影响程度 | 受灾人口 |
|------|----------|----------|----------|
| XX省 | XX市、XX市 | **严重影响** | XX万人 |
| XX省 | XX市、XX市 | **较重影响** | XX万人 |
| XX省 | XX市 | **一般影响** | XX万人 |

**统计汇总**：
- 受影响省份：**XX个**
- 受影响地级市：**XX个**
- 受影响县区：**XX个**
- 总受灾人口：约**XX万人**

### 1.2 📏 影响范围评估

> **空间覆盖范围**

**范围参数**：
- **影响半径**：约XX~XX km
- **覆盖面积**：约**XX万平方公里**
- **海岸线长度**：约XX km
- **内陆深入**：最远达XX km

**影响区域分布**：
- 沿海地区：XX个城市（占XX%）
- 内陆地区：XX个城市（占XX%）
- 山区地带：XX个县区（占XX%）

### 1.3 🕐 影响时段分析

> **时间轴详解**

**关键时间节点**：

1. **影响开始**：YYYY年MM月DD日 HH:mm
    - 首个预警发布时间
    - 外围云系开始影响

2. **影响高峰**：YYYY年MM月DD日 HH:mm至DD日 HH:mm
    - 风雨最强时段
    - 持续时间：XX小时

3. **影响结束**：YYYY年MM月DD日 HH:mm
    - 警报解除时间
    - 天气转好时间

**总持续时间**：**X天X小时**（从预警发布到解除）

### 1.4 📊 影响程度分级

> **分级评估标准**

| 影响等级 | 区域数量 | 主要特征 | 代表城市 |
|----------|----------|----------|----------|
| **严重影响** | XX个 | 风速>XX m/s，降雨>XXX mm | XX市、XX市 |
| **较重影响** | XX个 | 风速XX~XX m/s，降雨XX~XXX mm | XX市、XX市 |
| **一般影响** | XX个 | 风速<XX m/s，降雨<XX mm | XX市、XX市 |

**分级依据**：
- 风速强度：XX%权重
- 降雨量：XX%权重
- 持续时间：XX%权重
- 经济损失：XX%权重

### 1.5 🗺️ 地理特征分析

**地形地貌影响**：

1. **沿海平原区**
    - 特征：地势低平，易受风暴潮影响
    - 主要风险：海水倒灌、内涝

2. **丘陵山地区**
    - 特征：地形复杂，降雨集中
    - 主要风险：山洪、泥石流、滑坡

3. **河网密集区**
    - 特征：水系发达，排水压力大
    - 主要风险：洪涝、堤防溃决

**📌 关键结论**：本次台风主要影响XX地区，覆盖XX万平方公里，持续XX天，XX地区受灾最严重。

---

【Markdown格式规范】
1. **视觉层次**：
   - 章节开头使用分隔线 `---`
   - 重要数据使用引用块 `>`
   - 对比数据使用表格展示

2. **列表格式**：
   - 有序步骤使用数字列表 `1. 2. 3.`
   - 并列要点使用无序列表 `-`
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 时间：`YYYY年MM月DD日 HH:mm`
   - 距离：`XX km`或范围`XX~XX km`
   - 面积：`XX万平方公里`
   - 人口：`XX万人`
   - 持续时间：`X天X小时`
   - 百分比：`XX%`

4. **视觉强调元素**：
   - 地区信息使用 `🌏` 图标
   - 范围信息使用 `📏` 图标
   - 时间信息使用 `🕐` 图标
   - 数据统计使用 `📊` 图标
   - 地图信息使用 `🗺️` 图标
   - 重要提示使用 `📌` 图标

5. **强调格式**：
   - 影响程度使用 `**加粗**`
   - 关键数据使用 `**加粗**`
   - 关键结论单独成段并加粗

【输出要求】
- 本章节字数不少于**250字**
- 严格按照上述格式输出
- 直接输出章节内容，不使用代码块包装
- 确保表格、列表、图标正确显示"""

            elif chapter_name == "灾害风险分析":
                return f"""基于历史数据生成台风影响评估报告的第二章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 二、灾害风险分析

---

### 2.1 💨 风灾风险

> **风力破坏评估**

| 风力等级 | 风速范围 | 影响区域 | 主要危害 |
|----------|----------|----------|----------|
| 12级以上 | >XX m/s | XX市XX区 | 房屋严重损毁、树木连根拔起 |
| 10-11级 | XX~XX m/s | XX市XX区 | 房屋受损、广告牌倒塌 |
| 8-9级 | XX~XX m/s | XX市XX区 | 树枝折断、门窗损坏 |

**风灾特征**：
- **最大风速**：**XX m/s（XX级）**
- **最大阵风**：**XX m/s（XX级）**
- **持续时间**：XX小时（≥8级风）
- **影响半径**：约XX km

**⚠️ 高风险区域**：沿海地区、高层建筑、临时建筑物

### 2.2 🌧️ 雨灾风险

> **降雨灾害评估**

**降雨统计**：
- **最大降雨量**：**XXX mm**（XX市XX区）
- **累计降雨**：XX~XXX mm
- **降雨强度**：最大XX mm/h
- **持续时间**：XX小时

**降雨分布**：

| 降雨等级 | 降雨量 | 影响区域 | 主要风险 |
|----------|--------|----------|----------|
| 特大暴雨 | >250 mm | XX市 | 严重内涝、山洪 |
| 大暴雨 | 100~250 mm | XX市 | 城市内涝、农田受淹 |
| 暴雨 | 50~100 mm | XX市 | 局部积水 |

**⚠️ 高风险区域**：低洼地带、山区、河网密集区

### 2.3 🌊 潮灾风险

> **风暴潮灾害评估**

**潮位数据**：
- **最大风暴潮**：**X.X米**（超警戒X.X米）
- **最大海浪**：**X~X米**
- **影响海岸线**：约XX km
- **持续时间**：XX小时

**受影响区域**：

| 区域 | 潮位高度 | 超警戒值 | 主要风险 |
|------|----------|----------|----------|
| XX港 | X.X米 | +X.X米 | 海水倒灌、码头受损 |
| XX湾 | X.X米 | +X.X米 | 海堤漫顶、养殖受损 |
| XX滩 | X.X米 | +X.X米 | 海岸侵蚀 |

**⚠️ 高风险区域**：沿海低地、港口码头、海水养殖区

### 2.4 ⚠️ 次生灾害风险

> **衍生灾害评估**

**1. 山洪泥石流**
- **高风险区**：XX个山区县
- **风险等级**：**高风险**
- **主要诱因**：强降雨+陡坡地形
- **潜在威胁**：XX个村庄、XX条道路

**2. 城市内涝**
- **高风险区**：XX个城市低洼区
- **风险等级**：**高风险**
- **主要诱因**：短时强降雨+排水不畅
- **潜在威胁**：XX条道路、XX个地下空间

**3. 地质灾害**
- **高风险区**：XX处地质灾害隐患点
- **风险等级**：**中高风险**
- **主要类型**：滑坡、崩塌、地面塌陷
- **潜在威胁**：XX户居民、XX条道路

### 2.5 🗺️ 灾害分布特征

**空间分布规律**：

1. **沿海地区**：以风灾、潮灾为主
2. **山区地带**：以雨灾、次生灾害为主
3. **平原地区**：以内涝为主
4. **城市区域**：以内涝、风灾为主

### 2.6 🔗 灾害叠加效应

> **多灾种耦合分析**

**叠加效应评估**：

- **风雨叠加**：XX地区同时遭受XX级大风和XXX mm降雨，灾害程度放大XX%
- **雨潮叠加**：XX地区降雨与风暴潮叠加，导致排水困难，内涝加重
- **多灾叠加**：XX地区风、雨、潮三灾叠加，形成**极高风险**区域

**📌 关键结论**：本次台风以XX灾害为主，XX地区风险最高，需重点防范XX叠加效应。

---

【Markdown格式规范】
1. **视觉层次**：
   - 章节开头使用分隔线 `---`
   - 重要数据使用引用块 `>`
   - 对比数据使用表格展示

2. **列表格式**：
   - 有序步骤使用数字列表 `1. 2. 3.`
   - 并列要点使用无序列表 `-`
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 风速：`XX m/s（XX级）`或范围`XX~XX m/s`
   - 降雨量：`XXX mm`或范围`XX~XXX mm`
   - 降雨强度：`XX mm/h`
   - 风暴潮：`X.X米`
   - 海浪高度：`X~X米`
   - 距离：`XX km`
   - 百分比：`XX%`

4. **视觉强调元素**：
   - 风灾使用 `💨` 图标
   - 雨灾使用 `🌧️` 图标
   - 潮灾使用 `🌊` 图标
   - 次生灾害使用 `⚠️` 图标
   - 分布特征使用 `🗺️` 图标
   - 叠加效应使用 `🔗` 图标
   - 重要提示使用 `📌` 图标

5. **强调格式**：
   - 风险等级使用 `**加粗**`
   - 关键数据使用 `**加粗**`
   - 关键结论单独成段并加粗

【输出要求】
- 本章节字数不少于**250字**
- 严格按照上述格式输出
- 直接输出章节内容，不使用代码块包装
- 确保表格、列表、图标正确显示"""

            elif chapter_name == "影响程度评估":
                return f"""基于历史数据生成台风影响评估报告的第三章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 三、影响程度评估

---

### 3.1 👥 人员安全风险

> **风险区域划分**

| 风险等级 | 区域数量 | 主要特征 | 受威胁人口 |
|----------|----------|----------|------------|
| **高风险** | XX个 | 沿海低地、山洪易发区 | XX万人 |
| **中风险** | XX个 | 城市低洼区、河网密集区 | XX万人 |
| **低风险** | XX个 | 内陆平原、地势较高区 | XX万人 |

**安全威胁分析**：
- **直接威胁**：强风、暴雨、风暴潮
- **次生威胁**：山洪、泥石流、房屋倒塌
- **需转移人口**：约**XX万人**
- **特殊人群**：老人XX万、儿童XX万、病患XX万

### 3.2 💰 财产损失风险

> **经济损失预估**

**总体损失评估**：
- **预估总损失**：约**XX~XX亿元**
- **直接经济损失**：XX亿元（占XX%）
- **间接经济损失**：XX亿元（占XX%）

**分类损失统计**：

| 损失类别 | 预估金额 | 占比 | 主要项目 |
|----------|----------|------|----------|
| 房屋建筑 | XX亿元 | XX% | 居民住宅、公共建筑 |
| 基础设施 | XX亿元 | XX% | 道路、桥梁、管网 |
| 农业损失 | XX亿元 | XX% | 农作物、养殖业 |
| 工商业 | XX亿元 | XX% | 停工停产、设备损坏 |

### 3.3 ⚡ 基础设施影响

> **关键设施风险评估**

**1. 电力系统**
- **受影响用户**：约XX万户
- **风险等级**：**高风险**
- **主要威胁**：输电线路倒塌、变电站进水
- **预计停电时长**：XX~XX小时

**2. 通信系统**
- **受影响基站**：约XX个
- **风险等级**：**中高风险**
- **主要威胁**：基站断电、光缆损坏
- **预计中断时长**：XX~XX小时

**3. 供水系统**
- **受影响人口**：约XX万人
- **风险等级**：**中风险**
- **主要威胁**：水源污染、管网破损
- **预计影响时长**：XX~XX天

### 3.4 🚗 交通运输影响

> **交通系统风险评估**

| 交通方式 | 影响程度 | 受影响线路 | 预计中断时长 |
|----------|----------|------------|--------------|
| **公路** | **严重** | XX条高速、XX条国道 | XX~XX小时 |
| **铁路** | **较重** | XX条线路 | XX~XX小时 |
| **航空** | **严重** | XX个机场 | XX~XX小时 |
| **水运** | **严重** | XX个港口 | XX~XX天 |

**交通管制措施**：
- 高速公路封闭：XX条
- 铁路停运：XX趟
- 航班取消：约XX架次
- 港口停航：XX个

### 3.5 🌾 农业影响

> **农业损失评估**

**农作物影响**：
- **受灾面积**：约**XX万亩**
- **绝收面积**：约**XX万亩**
- **主要作物**：水稻XX万亩、蔬菜XX万亩、果树XX万亩
- **预估损失**：约**XX亿元**

**渔业影响**：
- **受损养殖面积**：约XX万亩
- **受损渔船**：约XX艘
- **预估损失**：约XX亿元

**畜牧业影响**：
- **受威胁养殖场**：XX个
- **需转移牲畜**：约XX万头/只
- **预估损失**：约XX亿元

### 3.6 🏭 工商业影响

> **工商业损失评估**

**工业影响**：
- **停工企业**：约**XX家**
- **影响产值**：约**XX亿元**
- **主要行业**：制造业、化工、电子等
- **预计停工时长**：XX~XX天

**商业影响**：
- **停业商户**：约XX家
- **影响营业额**：约XX亿元
- **主要业态**：零售、餐饮、旅游等
- **预计停业时长**：XX~XX天

**📌 关键结论**：本次台风预计造成总损失XX~XX亿元，XX领域受影响最严重，需重点关注XX风险。

---

【Markdown格式规范】
1. **视觉层次**：
   - 章节开头使用分隔线 `---`
   - 重要数据使用引用块 `>`
   - 对比数据使用表格展示

2. **列表格式**：
   - 有序步骤使用数字列表 `1. 2. 3.`
   - 并列要点使用无序列表 `-`
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 风险等级：`**高风险**`、`**中风险**`、`**低风险**`
   - 经济损失：`XX亿元`或范围`XX~XX亿元`
   - 人口：`XX万人`
   - 面积：`XX万亩`
   - 数量：`XX家`、`XX个`、`XX艘`
   - 时长：`XX~XX小时`或`XX~XX天`
   - 百分比：`XX%`

4. **视觉强调元素**：
   - 人员安全使用 `👥` 图标
   - 经济损失使用 `💰` 图标
   - 基础设施使用 `⚡` 图标
   - 交通运输使用 `🚗` 图标
   - 农业影响使用 `🌾` 图标
   - 工商业使用 `🏭` 图标
   - 重要提示使用 `📌` 图标

5. **强调格式**：
   - 风险等级使用 `**加粗**`
   - 关键数据使用 `**加粗**`
   - 关键结论单独成段并加粗

【输出要求】
- 本章节字数不少于**250字**
- 严格按照上述格式输出
- 直接输出章节内容，不使用代码块包装
- 确保表格、列表、图标正确显示"""

            elif chapter_name == "防灾减灾建议":
                return f"""基于历史数据生成台风影响评估报告的第四章节：

【台风信息】
编号：{typhoon_id} | 名称：{typhoon_name}

【历史数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

【章节要求】
## 四、防灾减灾建议

---

### 4.1 🚨 人员转移建议

> **转移安置方案**

**1. 转移时间窗口**
- **预警发布**：台风登陆前XX~XX小时
- **转移启动**：台风登陆前XX~XX小时
- **转移完成**：台风登陆前XX小时
- **⚠️ 关键时段**：YYYY年MM月DD日 HH:mm前必须完成

**2. 转移路线规划**
- **沿海地区**：向内陆XX km以上转移
- **山区地带**：向地势较高、地质稳定区转移
- **低洼地区**：向地势高处转移
- **避开区域**：河道、水库下游、地质灾害隐患点

**3. 安置点选择**
- **临时安置点**：学校、体育馆、社区中心等（XX处）
- **容纳能力**：可安置XX万人
- **基本设施**：食品、饮水、医疗、通信
- **管理要求**：专人值守、定时巡查

**4. 特殊人群安置**
- **老年人**：优先转移，专人照顾
- **儿童**：集中安置，确保安全
- **病患**：医疗保障，药品充足
- **孕妇**：特别关注，医护随行

**5. 转移物资准备**
- 个人证件、现金
- 3天以上食品、饮用水
- 常用药品、急救用品
- 手电筒、收音机、充电宝
- 换洗衣物、雨具

### 4.2 📦 物资准备建议

> **应急物资储备清单**

**1. 应急物资清单**

| 物资类别 | 主要物品 | 储备量建议 | 优先级 |
|----------|----------|------------|--------|
| **食品饮水** | 方便食品、瓶装水 | 3~5天用量 | ⭐⭐⭐ |
| **医疗用品** | 急救包、常用药 | 家庭装 | ⭐⭐⭐ |
| **照明通信** | 手电筒、收音机 | 每户1套 | ⭐⭐⭐ |
| **防护用品** | 雨衣、雨靴、口罩 | 每人1套 | ⭐⭐ |
| **工具设备** | 绳索、铁锹、锤子 | 每户1套 | ⭐⭐ |

**2. 储备量建议**
- **家庭储备**：满足3~5天基本需求
- **社区储备**：满足XX%居民3天需求
- **政府储备**：满足XX万人7天需求

**3. 储存位置**
- **家庭**：易取位置，防水防潮
- **社区**：安全地带，便于分发
- **政府**：战略储备库，分散布局

**4. 物资调配方案**
- **调配原则**：就近调配、快速响应
- **运输路线**：多条备用路线
- **配送方式**：政府统一配送+社区自取
- **优先顺序**：重灾区>一般灾区>轻灾区

**5. 物资补充机制**
- **日常补充**：定期检查，及时更新
- **应急补充**：启动应急采购程序
- **社会捐赠**：开通捐赠渠道，统一管理

### 4.3 🎯 应急响应建议

> **应急响应机制**

**1. 应急预案启动**

| 响应级别 | 启动条件 | 响应措施 | 责任单位 |
|----------|----------|----------|----------|
| **Ⅰ级响应** | 超强台风 | 全面动员、最高指挥 | 省级政府 |
| **Ⅱ级响应** | 强台风 | 重点防御、加强值守 | 市级政府 |
| **Ⅲ级响应** | 台风 | 密切监视、做好准备 | 县级政府 |
| **Ⅳ级响应** | 热带风暴 | 关注动态、预警发布 | 乡镇政府 |

**2. 部门协调机制**
- **指挥部**：统一指挥、综合协调
- **气象部门**：监测预警、信息发布
- **应急部门**：救援救灾、物资调配
- **公安部门**：交通管制、治安维护
- **卫生部门**：医疗救治、卫生防疫
- **电力通信**：抢修保障、应急通信

**3. 信息发布渠道**
- **官方媒体**：电视、广播、报纸
- **新媒体**：微信、微博、APP
- **应急广播**：村村响、社区广播
- **短信推送**：手机短信、预警信息
- **⚠️ 发布频率**：每XX小时更新一次

**4. 应急队伍部署**
- **专业救援队**：消防、武警、民兵（XX支队伍）
- **医疗队**：医疗救护、心理疏导（XX支队伍）
- **抢险队**：电力、通信、交通（XX支队伍）
- **志愿者队**：后勤保障、秩序维护（XX人）

**5. 应急演练要求**
- **演练频次**：每年XX次
- **演练内容**：人员转移、物资调配、应急救援
- **演练范围**：重点区域全覆盖
- **演练评估**：及时总结、持续改进

**📌 关键建议**：建议XX地区启动**XX级响应**，重点做好XX工作，确保人民生命财产安全。

---

【Markdown格式规范】
1. **视觉层次**：
   - 章节开头使用分隔线 `---`
   - 重要数据使用引用块 `>`
   - 对比数据使用表格展示

2. **列表格式**：
   - 有序步骤使用数字列表 `1. 2. 3.`
   - 并列要点使用无序列表 `-`
   - 嵌套列表使用4空格缩进

3. **数据格式规范**：
   - 时间：`YYYY年MM月DD日 HH:mm`或`XX~XX小时`
   - 距离：`XX km`
   - 数量：`XX处`、`XX万人`、`XX支队伍`
   - 响应级别：`**Ⅰ级响应**`、`**Ⅱ级响应**`等
   - 优先级：`⭐⭐⭐`（高）、`⭐⭐`（中）、`⭐`（低）

4. **视觉强调元素**：
   - 人员转移使用 `🚨` 图标
   - 物资准备使用 `📦` 图标
   - 应急响应使用 `🎯` 图标
   - 警告信息使用 `⚠️` 图标
   - 重要提示使用 `📌` 图标

5. **强调格式**：
   - 响应级别使用 `**加粗**`
   - 关键建议使用 `**加粗**`
   - 关键结论单独成段并加粗

【输出要求】
- 本章节字数不少于**250字**
- 严格按照上述格式输出
- 直接输出章节内容，不使用代码块包装
- 确保表格、列表、图标正确显示"""

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
        使用GLM生成台风分析报告（支持三种报告类型）

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

                logger.info(f"GLM报告生成完成 - 总内容长度: {len(report_content)}, 失败章节数: {len(failed_chapters)}")

                # 构建返回结果
                result_dict = {
                    "success": True,
                    "report_content": report_content.strip(),
                    "model_used": self.model
                }

                # 如果有失败章节，添加错误信息
                if failed_chapters:
                    result_dict["error"] = f"部分章节生成失败: {', '.join(failed_chapters)}"

                return result_dict

            # 预测报告保持原有逻辑
            elif report_type == "prediction":
                prompt = self._build_prediction_prompt(typhoon_id, typhoon_name, prediction_data or {})

                payload = {
                    "model": self.model,
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
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "top_p": self.top_p,
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

                logger.info(f"GLM报告生成成功 - 内容长度: {len(report_content)}")

                return {
                    "success": True,
                    "report_content": report_content.strip(),
                    "model_used": self.model
                }
            else:
                raise ValueError(f"不支持的报告类型: {report_type}")

        except Exception as e:
            logger.error(f"GLM报告生成失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误详情: {str(e)}")

            return {
                "success": False,
                "error": f"GLM服务调用失败: {str(e)}",
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
- 报告总字数不少于**1000字**
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
- 报告总字数不少于**1000字**
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
- 报告总字数不少于**1000字**
- 每个章节至少包含**5-7个分析要点**
- 风险等级使用**加粗**明确标注
- 语言专业详尽，逻辑清晰
- 直接输出报告内容，不使用代码块包装"""


# 创建全局服务实例
glm_service = GlmService()


