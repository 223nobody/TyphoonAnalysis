"""
通义千问图像分析服务
基于 few-shot 标注样例与结构化结果增强单张卫星图分析
"""
import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class QwenImageService:
    """通义千问图像 few-shot 分析服务"""

    def __init__(self):
        self.api_key = settings.AI_API_KEY_VL or settings.AI_API_KEY
        self.base_url = settings.AI_API_BASE_URL_VL or "https://dashscope.aliyuncs.com/api/v1"
        self.model = settings.QWEN_VL_MODEL or "qwen-vl-max-latest"
        self.timeout = 180.0
        self.max_retries = 3
        self.retry_delay = 2
        self.backend_dir = Path(__file__).resolve().parents[3]
        self.examples_dir = self.backend_dir / "data" / "images" / "test"
        self.examples_manifest = self.examples_dir / "examples.json"

    def _create_client(self):
        return httpx.AsyncClient(timeout=self.timeout)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _load_examples(self, image_type: str, limit: int = 3) -> List[Dict[str, Any]]:
        if not self.examples_manifest.exists():
            logger.warning("few-shot 样例配置不存在: %s", self.examples_manifest)
            return []

        try:
            items = json.loads(self.examples_manifest.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("读取 few-shot 样例配置失败: %s", exc, exc_info=True)
            return []

        if not isinstance(items, list):
            return []

        matched = [item for item in items if item.get("image_type") == image_type]
        selected = matched or items

        result: List[Dict[str, Any]] = []
        for item in selected[:limit]:
            file_path = self.examples_dir / item.get("filename", "")
            if not file_path.exists():
                logger.warning("few-shot 样例图不存在: %s", file_path)
                continue
            entry = dict(item)
            entry["file_path"] = file_path
            result.append(entry)

        return result

    def _encode_image_to_data_url(self, image_path: Path) -> str:
        suffix = image_path.suffix.lower()
        mime_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(suffix, "image/png")
        encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _build_analysis_prompt(
        self,
        structured_result: Dict[str, Any],
        image_type: str,
        examples: List[Dict[str, Any]],
    ) -> str:
        structured_snapshot = {
            "method": structured_result.get("method"),
            "confidence": structured_result.get("confidence"),
            "center": structured_result.get("center"),
            "intensity": structured_result.get("intensity"),
            "eye": structured_result.get("eye"),
            "structure": structured_result.get("structure"),
        }
        example_descriptions = "\n".join(
            [
                (
                    f"- 样例 {index}: {example.get('filename')} | "
                    f"标注类型: {example.get('annotation_type')} | "
                    f"学习重点: {example.get('description')}"
                )
                for index, example in enumerate(examples, start=1)
            ]
        )
        if not example_descriptions:
            example_descriptions = (
                "- 当前没有可用的 few-shot 标注样例，请优先基于目标图和结构化结果进行分析。"
            )

        return (
            "你是一名台风卫星云图分析助手。\n\n"
            "【任务目标】\n"
            "1. 先学习已标注样例图中的台风眼位置与眼墙、螺旋云带、云系核心之间的相对关系。\n"
            "2. 样例图中的红色圆圈只出现在教学样例里，红圈中心就是台风眼中心。\n"
            "3. 待分析的目标图没有红圈或任何人工标注，你需要根据样例学到的视觉特征去推断目标图中的台风眼位置。\n"
            "4. 结构化分析结果只是辅助参考，你需要对比它与视觉判读的一致性，并明确指出不确定性。\n\n"
            f"【图像类型】{image_type}\n\n"
            "【已标注样例说明】\n"
            f"{example_descriptions}\n\n"
            "【结构化分析参考】\n"
            f"{json.dumps(structured_snapshot, ensure_ascii=False, indent=2)}\n\n"
            "【输出要求】\n"
            "1. 只输出 JSON，不要输出代码块或额外说明。\n"
            "2. 不要编造精确像素坐标；如果无法判断，请使用 null 或明确写出“不确定”。\n"
            "3. markdown_report 使用 Markdown，至少包含“图像概览”“台风眼判断”“云系结构”“强度和发展阶段”“与结构化结果的一致性”“风险与局限”“结论”七个部分。\n"
            "4. JSON 字段必须包含：\n"
            "{\n"
            '  "summary": "一句话摘要",\n'
            '  "overall_assessment": "综合判断",\n'
            '  "eye_detected": true,\n'
            '  "eye_position_description": "台风眼大致位置描述",\n'
            '  "eye_confidence": 0.0,\n'
            '  "eye_evidence": ["判读依据1", "判读依据2"],\n'
            '  "center_location_hint": "相对画面位置描述",\n'
            '  "intensity_assessment": "强度语义解读",\n'
            '  "organization_assessment": "组织程度评估",\n'
            '  "development_stage": "发展阶段",\n'
            '  "cloud_system_description": "云系结构描述",\n'
            '  "analysis_highlights": ["关键发现1", "关键发现2"],\n'
            '  "analysis_limitations": ["局限1", "局限2"],\n'
            '  "consistency_score": 0.0,\n'
            '  "risk_flags": ["风险提示"],\n'
            '  "markdown_report": "Markdown 报告"\n'
            "}"
        )

    def _normalize_content_to_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
                elif isinstance(item, str):
                    parts.append(item)
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            return "\n".join(parts)

        if isinstance(content, dict):
            if "text" in content:
                return str(content["text"])
            return json.dumps(content, ensure_ascii=False)

        return str(content)

    def _parse_ai_response(self, content: str) -> Dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            logger.warning("Qwen 图像分析返回非 JSON，降级为 Markdown 文本")

        return {
            "summary": "AI 返回了非结构化文本结果",
            "overall_assessment": "AI 返回格式不稳定，已按文本报告展示",
            "eye_detected": None,
            "eye_position_description": "未提供结构化位置描述",
            "eye_confidence": None,
            "eye_evidence": [],
            "center_location_hint": "未提供相对位置提示",
            "intensity_assessment": "未提供强度语义解读",
            "organization_assessment": "未提供组织程度评估",
            "development_stage": "未提供发展阶段信息",
            "cloud_system_description": "未提供云系结构描述",
            "analysis_highlights": [],
            "analysis_limitations": [],
            "consistency_score": None,
            "risk_flags": ["AI 返回格式不稳定，已按纯文本报告展示"],
            "markdown_report": content,
        }

    async def _make_api_request_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        api_url = f"{self.base_url}/services/aigc/multimodal-generation/generation"
        headers = self._get_headers()
        last_error: Optional[Exception] = None

        async with self._create_client() as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.post(api_url, headers=headers, json=payload)
                    response.raise_for_status()
                    return response.json()
                except Exception as exc:
                    last_error = exc
                    logger.warning("图像分析 API 请求失败，第 %s 次尝试: %s", attempt, exc)
                    if attempt < self.max_retries:
                        import asyncio

                        await asyncio.sleep(self.retry_delay * attempt)

        raise last_error or RuntimeError("图像分析 API 请求失败")

    async def analyze_image(
        self,
        image_path: str,
        image_type: str,
        structured_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "success": False,
                "error": "未配置视觉模型 API Key",
                "processing_time": 0.0,
            }

        start_time = datetime.now()
        target_path = Path(image_path)
        examples = self._load_examples(image_type=image_type, limit=3)

        try:
            content: List[Dict[str, Any]] = [
                {
                    "type": "text",
                    "text": self._build_analysis_prompt(
                        structured_result=structured_result,
                        image_type=image_type,
                        examples=examples,
                    ),
                }
            ]

            for index, example in enumerate(examples, start=1):
                content.append(
                    {
                        "type": "text",
                        "text": (
                            f"样例 {index}（已标注教学样例）：{example.get('description', '')} "
                            "请注意，样例图中的红色圆圈中心点就是台风眼中心，"
                            "你需要学习红圈中心与周围云系结构的对应关系。"
                        ),
                    }
                )
                content.append(
                    {
                        "type": "image",
                        "image": self._encode_image_to_data_url(example["file_path"]),
                    }
                )

            content.append(
                {
                    "type": "text",
                    "text": (
                        "下面是待分析的目标图。目标图没有红圈或任何人工标注，"
                        "请基于上面的标注样例学习到的台风眼位置特征，结合结构化结果，"
                        "直接输出纯 JSON 分析结果。"
                    ),
                }
            )
            content.append(
                {
                    "type": "image",
                    "image": self._encode_image_to_data_url(target_path),
                }
            )

            payload = {
                "model": self.model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": content,
                        }
                    ]
                },
                "parameters": {
                    "max_tokens": 2200,
                    "temperature": 0.2,
                },
            }

            raw_result = await self._make_api_request_with_retry(payload)
            raw_content = ""
            if "output" in raw_result and "choices" in raw_result["output"]:
                raw_content = self._normalize_content_to_text(
                    raw_result["output"]["choices"][0]["message"]["content"]
                )
            elif "choices" in raw_result:
                raw_content = self._normalize_content_to_text(
                    raw_result["choices"][0]["message"]["content"]
                )
            else:
                raw_content = self._normalize_content_to_text(raw_result)

            parsed = self._parse_ai_response(raw_content)
            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "summary": parsed.get("summary"),
                "overall_assessment": parsed.get("overall_assessment"),
                "eye_detected": parsed.get("eye_detected"),
                "eye_position_description": parsed.get("eye_position_description"),
                "eye_confidence": parsed.get("eye_confidence"),
                "eye_evidence": parsed.get("eye_evidence") or [],
                "center_location_hint": parsed.get("center_location_hint"),
                "intensity_assessment": parsed.get("intensity_assessment"),
                "organization_assessment": parsed.get("organization_assessment"),
                "development_stage": parsed.get("development_stage"),
                "cloud_system_description": parsed.get("cloud_system_description"),
                "analysis_highlights": parsed.get("analysis_highlights") or [],
                "analysis_limitations": parsed.get("analysis_limitations") or [],
                "consistency_score": parsed.get("consistency_score"),
                "risk_flags": parsed.get("risk_flags") or [],
                "markdown_report": parsed.get("markdown_report") or raw_content,
                "fewshot_examples_used": [example.get("filename") for example in examples],
                "model_used": self.model,
                "processing_time": processing_time,
                "raw_response": raw_result,
            }
        except Exception as exc:
            logger.error("Qwen 图像分析失败: %s", exc, exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "fewshot_examples_used": [example.get("filename") for example in examples],
                "processing_time": (datetime.now() - start_time).total_seconds(),
            }


qwen_image_service = QwenImageService()
