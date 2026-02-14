"""
AI客服API接口
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Tuple
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import uuid
import logging
import json
import asyncio

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.typhoon import Question, AskHistory
from app.models.user import User

router = APIRouter(tags=["AI客服"])
logger = logging.getLogger(__name__)

# 定义北京时区（UTC+8）
BEIJING_TZ = timezone(timedelta(hours=8))


def get_beijing_time():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)


async def find_preset_question(question_text: str, db: AsyncSession) -> Question:
    """
    根据用户问题查找匹配的预设问题
    
    匹配规则：
    1. 首先尝试精确匹配（不区分大小写）
    2. 如果没有精确匹配，尝试模糊匹配（包含关系）
    
    Args:
        question_text: 用户输入的问题
        db: 数据库会话
        
    Returns:
        匹配的 Question 对象，如果没有匹配则返回 None
    """
    try:
        # 1. 首先尝试精确匹配（不区分大小写）
        stmt = select(Question).where(
            func.lower(Question.question) == func.lower(question_text.strip())
        )
        result = await db.execute(stmt)
        matched = result.scalar_one_or_none()
        
        if matched:
            logger.info(f"找到精确匹配的预设问题: {matched.question}")
            return matched
        
        # 2. 如果没有精确匹配，尝试模糊匹配（用户问题包含预设问题关键词）
        # 获取所有预设问题
        all_stmt = select(Question).order_by(Question.weight.desc())
        all_result = await db.execute(all_stmt)
        all_questions = all_result.scalars().all()
        
        user_question_lower = question_text.lower().strip()
        
        for q in all_questions:
            # 检查用户问题是否包含预设问题的关键词（长度大于3才进行模糊匹配）
            preset_question_lower = q.question.lower()
            if len(preset_question_lower) > 3:
                if preset_question_lower in user_question_lower or user_question_lower in preset_question_lower:
                    logger.info(f"找到模糊匹配的预设问题: {q.question}")
                    return q
        
        return None
    except Exception as e:
        logger.error(f"查找预设问题失败: {str(e)}")
        return None


def get_model_display_name(model_key: str, deep_thinking: bool = False) -> str:
    """
    获取模型的显示名称
    
    Args:
        model_key: 模型键名（deepseek, glm, qwen）
        deep_thinking: 是否启用深度思考模式
    
    Returns:
        模型显示名称
    """
    if deep_thinking:
        return "DeepSeek-R1(深度思考)"
    
    model_names = {
        "deepseek": "DeepSeek-V3.2(DeepSeek)",
        "glm": "GLM-4.7(智谱清言)",
        "qwen": "Qwen3-235B-A22B(通义千问)"
    }
    
    return model_names.get(model_key, model_key)


class QuestionResponse(BaseModel):
    """问题响应模型"""
    id: int
    question: str
    answer: str
    weight: int

    class Config:
        from_attributes = True


class AskRequest(BaseModel):
    """提问请求模型"""
    session_id: str
    question: str
    model: str = "deepseek"  # 模型选择：deepseek, glm, qwen
    deep_thinking: bool = False  # 是否启用深度思考模式


class AskResponse(BaseModel):
    """提问响应模型"""
    answer: str
    matched: bool  # 是否匹配到预设问题
    reasoning_content: str = ""  # AI推理内容（深度思考模式）


class SessionResponse(BaseModel):
    """会话响应模型"""
    session_id: str
    first_question: str
    created_at: datetime
    message_count: int

    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    """历史记录响应模型"""
    id: int
    question: str
    answer: str
    reasoning_content: str = ""  # AI推理内容（深度思考模式）
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/ai-agent/questions", response_model=List[QuestionResponse])
async def get_top_questions(db: AsyncSession = Depends(get_db)):
    """
    获取热门问题列表
    按照权重降序返回前10条问题
    """
    try:
        # 查询前10条问题，按weight降序排序
        stmt = select(Question).order_by(Question.weight.desc()).limit(10)
        result = await db.execute(stmt)
        questions = result.scalars().all()

        return [
            QuestionResponse(
                id=q.id,
                question=q.question,
                answer=q.answer,
                weight=q.weight
            )
            for q in questions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询问题失败: {str(e)}")


@router.get("/ai-agent/questions/{question_id}", response_model=QuestionResponse)
async def get_question_by_id(question_id: int, db: AsyncSession = Depends(get_db)):
    """
    根据ID获取问题详情
    """
    try:
        stmt = select(Question).where(Question.id == question_id)
        result = await db.execute(stmt)
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="问题不存在")

        return QuestionResponse(
            id=question.id,
            question=question.question,
            answer=question.answer,
            weight=question.weight
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询问题失败: {str(e)}")


async def call_ai_service_with_retry(
    model_key: str,
    model_name: str,
    question: str,
    max_retries: int = 2,
    use_thinking_config: bool = False,
    stream: bool = False
) -> Tuple[str, str, bool]:
    """
    调用AI服务并支持重试机制

    Args:
        model_key: 模型键名（deepseek, glm, qwen）
        model_name: 实际的模型名称
        question: 用户问题
        max_retries: 最大重试次数
        use_thinking_config: 是否使用深度思考模式的专用配置
        stream: 是否启用流式传输

    Returns:
        (answer, reasoning_content, success): 回答内容、推理内容和是否成功的标志
    """
    import httpx
    from app.core.config import settings
    import asyncio

    # 优化的系统提示词
    system_prompt = """你是一个通用型智能助手，具备多领域的知识解答能力，需严格遵循以下规则：

【核心能力】
- 通用知识解答：回答生活、科技、文化、教育、气象、职场等多领域的常见问题
- 逻辑分析：针对用户的问题提供清晰、有条理的分析和解决方案
- 信息解读：用通俗易懂的语言解释专业概念、数据和规则
- 建议给出：基于客观事实为用户提供合理、可落地的建议
- 多轮对话：结合历史上下文保持回答的连贯性和一致性

【回答格式要求（必须严格遵守）】
1. 禁止使用任何Markdown标记
   - 不使用：**粗体**、###标题、---分隔线、`代码`、表情符号等
   - 只使用纯文本格式

2. 必须使用数字序号分点回答
   - 主要观点使用：1. 2. 3. 等数字序号
   - 次级内容使用：1.1 1.2 或 - 符号作为子项
   - 每个分点回答完毕后必须换行
3. 格式示例
   正确格式：
   1. 第一个要点的标题
   这里是第一个要点的详细说明内容，可以多行描述。

   1.1 第一个要点的子项
   子项的详细说明。

   2. 第二个要点的标题
   这里是第二个要点的详细说明内容。

4. 内容要求
   - 回答内容不少于200字
   - 层级清晰，使用适当缩进
   - 关键信息直接陈述，保持文本整洁
   - 避免杂乱排版，确保易读性

【风格要求】
- 专业、简洁、易懂
- 根据问题领域适配语气（气象与科学问题偏严谨，生活问题偏亲和）
- 保持客观中立，基于事实回答

"""

    # 根据问题复杂度动态调整 max_tokens
    question_length = len(question)
    is_simple_question = (
        question_length < 50 or
        any(keyword in question.lower() for keyword in ['吗', '吧', '是否', '对不对', '可以吗', '能不能', '会不会'])
    )

    max_tokens = 2000 if is_simple_question else 3000
    logger.info(f"问题复杂度判断 - 问题长度: {question_length}, 简单问题: {is_simple_question}, max_tokens: {max_tokens}")

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "stream": stream,
        "temperature": 0.8,  # 降低随机性
        "top_p": 0.95,        # 提升聚焦性
        "presence_penalty": 0.1,  # 新增：减少重复内容，提升多样性
        "frequency_penalty": 0.1, # 新增：避免模型过度谨慎
        "max_tokens": max_tokens,
        "stop": None
    }

    # 根据是否使用深度思考模式选择不同的API配置
    if use_thinking_config:
        # 深度思考模式：使用专用的API配置
        api_key = settings.AI_API_KEY_THINKING if settings.AI_API_KEY_THINKING else settings.AI_API_KEY
        api_base_url = settings.AI_API_BASE_URL_THINKING if settings.AI_API_BASE_URL_THINKING else settings.AI_API_BASE_URL
        logger.info(f"使用深度思考模式配置 - API Base URL: {api_base_url}")
    else:
        # 普通模式：使用默认的API配置
        api_key = settings.AI_API_KEY
        api_base_url = settings.AI_API_BASE_URL

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 重试逻辑
    for attempt in range(max_retries):
        try:
            logger.info(f"尝试调用AI服务 - 模型: {model_key} ({model_name}), 尝试次数: {attempt + 1}/{max_retries}, 流式: {stream}")

            # 根据是否使用深度思考模式设置不同的超时时间
            timeout_seconds = 120.0 if use_thinking_config else 60.0
            
            if stream:
                # 流式传输模式 - 返回异步生成器
                async def stream_generator():
                    full_answer = ""
                    full_reasoning = ""
                    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                        async with client.stream(
                            "POST",
                            f"{api_base_url}/chat/completions",
                            json=payload,
                            headers=headers
                        ) as response:
                            response.raise_for_status()

                            async for line in response.aiter_lines():
                                if not line.strip():
                                    continue

                                if not line.startswith("data: "):
                                    continue

                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break

                                try:
                                    data = json.loads(data_str)

                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        chunk = {"content": "", "reasoning_content": ""}

                                        if "content" in delta and delta["content"]:
                                            chunk["content"] = delta["content"]
                                            full_answer += delta["content"]

                                        if "reasoning_content" in delta and delta["reasoning_content"]:
                                            chunk["reasoning_content"] = delta["reasoning_content"]
                                            full_reasoning += delta["reasoning_content"]

                                        # 实时 yield 数据块
                                        if chunk["content"] or chunk["reasoning_content"]:
                                            yield chunk

                                except json.JSONDecodeError:
                                    continue
                                except Exception as e:
                                    logger.warning(f"解析流式响应行失败: {str(e)}")
                                    continue

                    # 返回最终的完整内容
                    yield {"done": True, "full_answer": full_answer, "full_reasoning": full_reasoning}

                return stream_generator(), True
            else:
                # 非流式传输模式（原有逻辑）
                async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                    response = await client.post(
                        f"{api_base_url}/chat/completions",
                        json=payload,
                        headers=headers
                    )
                    response.raise_for_status()
                    result_data = response.json()

                    # 提取AI回答和推理内容
                    message = result_data.get("choices", [{}])[0].get("message", {})
                    answer = message.get("content", "")
                    reasoning_content = message.get("reasoning_content", "")

                    if answer:
                        logger.info(f"AI服务回答成功 - 模型: {model_key}, 回答长度: {len(answer)}, 推理内容长度: {len(reasoning_content)}")
                        return answer, reasoning_content, True
                    else:
                        logger.warning(f"AI服务返回空回答 - 模型: {model_key}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2)  # 等待2秒后重试
                            continue
                        return "", "", False

        except httpx.TimeoutException:
            logger.warning(f"AI服务请求超时 - 模型: {model_key}, 尝试次数: {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(3)  # 等待3秒后重试
                continue
            return "", "", False

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.warning(f"AI服务HTTP错误 - 模型: {model_key}, 状态码: {status_code}, 尝试次数: {attempt + 1}/{max_retries}")

            # 对于503等临时错误，进行重试
            if status_code in [503, 502, 504] and attempt < max_retries - 1:
                await asyncio.sleep(3)  # 等待3秒后重试
                continue
            return "", "", False

        except Exception as e:
            logger.warning(f"调用AI服务异常 - 模型: {model_key}, 错误: {str(e)}, 尝试次数: {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # 等待2秒后重试
                continue
            return "", "", False

    return "", "", False


@router.post("/ai-agent/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    用户提问接口
    1. 优先从questions表中查找匹配的问题，如果找到则直接返回答案
    2. 如果没有找到匹配的问题，则调用AI服务生成回答（支持多模型切换、重试和自动降级）
    3. 保存对话历史（严格关联当前用户的 user_id）
    4. 返回答案
    """
    try:
        logger.info(f"用户提问 - 用户ID: {current_user.id}, 会话ID: {request.session_id}, 问题: {request.question}")

        # 1. 首先尝试从questions表中查找匹配的预设问题
        preset_question = await find_preset_question(request.question, db)

        if preset_question:
            # 找到匹配的预设问题，直接使用预设答案
            logger.info(f"使用预设问题答案 - 问题ID: {preset_question.id}, 问题: {preset_question.question}")

            # 获取当前北京时间
            current_time = get_beijing_time()

            # 保存对话历史，标记为非AI生成
            history = AskHistory(
                session_id=request.session_id,
                question=request.question,
                answer=preset_question.answer,
                reasoning_content=None,
                is_ai_generated=False,
                ai_mode=None,
                created_at=current_time,
                user_id=current_user.id
            )
            db.add(history)
            await db.commit()

            logger.info(f"[预设问题回答] 用户ID: {current_user.id}, 会话ID: {request.session_id}, 时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

            return AskResponse(answer=preset_question.answer, matched=True, reasoning_content="")

        # 2. 没有找到预设问题，调用AI服务生成回答
        from app.core.config import settings

        reasoning_content = ""  # 初始化推理内容

        logger.info(f"未找到预设问题，开始调用AI服务 - 用户选择模型: {request.model}, 深度思考: {request.deep_thinking}, 问题: {request.question}")

        # 根据深度思考模式和用户选择的模型，确定实际使用的模型
        if request.deep_thinking:
            # 启用深度思考模式：不管选择什么模型，都使用 DEEPSEEK_MODEL_THINKING
            actual_model_name = settings.DEEPSEEK_MODEL_THINKING
            actual_model_key = "deepseek"
            logger.info(f"深度思考模式已启用，强制使用 DeepSeek 深度思考模型: {actual_model_name}")
        else:
            # 未启用深度思考模式：根据用户选择的模型决定
            if request.model == "deepseek":
                # 选择 deepseek 且未启用深度思考，使用 DEEPSEEK_NOTHINK_MODEL
                actual_model_name = settings.DEEPSEEK_MODEL
                actual_model_key = "deepseek"
                logger.info(f"使用 DeepSeek 非深度思考模型: {actual_model_name}")
            elif request.model == "glm":
                actual_model_name = settings.GLM_MODEL
                actual_model_key = "glm"
            elif request.model == "qwen":
                actual_model_name = settings.QWEN_TEXT_MODEL
                actual_model_key = "qwen"
            else:
                actual_model_name = settings.DEEPSEEK_MODEL
                actual_model_key = "deepseek"

        # 模型映射（用于降级）
        model_map = {
            "deepseek": settings.DEEPSEEK_MODEL if not request.deep_thinking else settings.DEEPSEEK_MODEL_THINKING,
            "glm": settings.GLM_MODEL,
            "qwen": settings.QWEN_TEXT_MODEL
        }

        # 定义模型降级顺序（当前模型失败时尝试的备选模型）
        # 如果启用了深度思考模式，不进行降级
        if request.deep_thinking:
            fallback_order = {
                "deepseek": [],  # 深度思考模式不降级
                "glm": [],
                "qwen": []
            }
        else:
            fallback_order = {
                "deepseek": ["glm", "qwen"],
                "glm": ["deepseek", "qwen"],
                "qwen": ["deepseek", "glm"]
            }

        # 首先尝试实际选择的模型
        answer, reasoning_content, success = await call_ai_service_with_retry(
            actual_model_key,
            actual_model_name,
            request.question,
            max_retries=2,
            use_thinking_config=request.deep_thinking  # 深度思考模式使用专用配置
        )

        used_model = actual_model_key
        selected_model_key = request.model  # 保留用户原始选择的模型键名，用于后续提示

        # 如果失败，尝试降级到其他模型（仅在非深度思考模式下）
        if not success and not request.deep_thinking:
            logger.warning(f"模型 {actual_model_key} 调用失败，开始尝试降级到备选模型")

            fallback_models = fallback_order.get(actual_model_key, ["deepseek", "glm"])

            for fallback_key in fallback_models:
                fallback_name = model_map.get(fallback_key)
                if not fallback_name:
                    continue

                logger.info(f"尝试降级模型: {fallback_key} ({fallback_name})")

                answer, reasoning_content, success = await call_ai_service_with_retry(
                    fallback_key,
                    fallback_name,
                    request.question,
                    max_retries=1,  # 降级模型只重试1次
                    use_thinking_config=False  # 降级模型不使用深度思考配置
                )

                if success:
                    used_model = fallback_key
                    logger.info(f"模型降级成功 - 从 {selected_model_key} 降级到 {fallback_key}")
                    break

        # 处理最终结果
        if success and answer:
            matched = False
            is_ai_generated = True

            # 如果使用了降级模型，在回答前添加提示
            if used_model != selected_model_key:
                model_names = {
                    "deepseek": "DeepSeek",
                    "glm": "GLM（智谱清言）",
                    "qwen": "Qwen（通义千问）"
                }
                original_name = model_names.get(selected_model_key, selected_model_key)
                used_name = model_names.get(used_model, used_model)
                answer = f"[提示：{original_name}模型暂时不可用，已自动切换到{used_name}模型]\n\n{answer}"

            logger.info(f"AI服务最终成功 - 使用模型: {used_model}, 回答长度: {len(answer)}")
        else:
            # 所有模型都失败
            logger.error(f"所有AI模型均调用失败 - 原始模型: {selected_model_key}")

            model_names = {
                "deepseek": "DeepSeek",
                "glm": "GLM（智谱清言）",
                "qwen": "Qwen（通义千问）"
            }
            original_name = model_names.get(selected_model_key, selected_model_key)

            answer = f"抱歉，{original_name}模型暂时不可用，且备选模型也无法响应。\n\n建议您：\n1. 稍后重试\n2. 尝试切换到其他AI模型"
            matched = False
            is_ai_generated = False

        # 获取当前北京时间
        current_time = get_beijing_time()

        # 获取模型显示名称
        ai_mode = get_model_display_name(used_model, request.deep_thinking) if is_ai_generated else None

        # 保存对话历史，标记是否由AI生成，使用北京时间，并关联用户ID
        history = AskHistory(
            session_id=request.session_id,
            question=request.question,
            answer=answer,
            reasoning_content=reasoning_content if request.deep_thinking else None,
            is_ai_generated=is_ai_generated,
            ai_mode=ai_mode,
            created_at=current_time,
            user_id=current_user.id
        )
        db.add(history)
        await db.commit()

        # 打印AI回答时间
        answer_time = get_beijing_time()
        answer_time_str = answer_time.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[AI回答] 用户ID: {current_user.id}, 会话ID: {request.session_id}, 时间: {answer_time_str}, 回答长度: {len(answer)}, 推理内容长度: {len(reasoning_content)}, AI生成: {is_ai_generated}, AI模型: {ai_mode}")

        return AskResponse(answer=answer, matched=matched, reasoning_content=reasoning_content)
    except Exception as e:
        await db.rollback()
        logger.error(f"处理提问失败 - 用户ID: {current_user.id}, 会话ID: {request.session_id}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理提问失败: {str(e)}")


@router.get("/ai-agent/sessions", response_model=List[SessionResponse])
async def get_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户的所有对话会话列表
    优先使用AI生成的第一条问题作为标题，如果没有则使用第一条提问
    """
    try:
        # 获取当前用户的所有会话ID
        sessions_stmt = select(AskHistory.session_id).where(
            AskHistory.user_id == current_user.id
        ).distinct()
        sessions_result = await db.execute(sessions_stmt)
        session_ids = [row[0] for row in sessions_result.all()]

        sessions = []
        for session_id in session_ids:
            # 优先查找AI生成的第一条记录
            ai_stmt = select(AskHistory).where(
                and_(
                    AskHistory.session_id == session_id,
                    AskHistory.user_id == current_user.id,
                    AskHistory.is_ai_generated == True
                )
            ).order_by(AskHistory.created_at.asc()).limit(1)

            ai_result = await db.execute(ai_stmt)
            ai_record = ai_result.scalar_one_or_none()

            if ai_record:
                # 找到AI生成的记录，使用它作为标题
                first_question = ai_record.question
                created_at = ai_record.created_at
            else:
                # 没有AI生成的记录，使用第一条提问
                first_stmt = select(AskHistory).where(
                    and_(
                        AskHistory.session_id == session_id,
                        AskHistory.user_id == current_user.id
                    )
                ).order_by(AskHistory.created_at.asc()).limit(1)

                first_result = await db.execute(first_stmt)
                first_record = first_result.scalar_one_or_none()

                if first_record:
                    first_question = first_record.question
                    created_at = first_record.created_at
                else:
                    continue  # 跳过空会话

            # 统计消息数量
            count_stmt = select(func.count(AskHistory.id)).where(
                and_(
                    AskHistory.session_id == session_id,
                    AskHistory.user_id == current_user.id
                )
            )
            count_result = await db.execute(count_stmt)
            message_count = count_result.scalar()

            sessions.append({
                'session_id': session_id,
                'first_question': first_question,
                'created_at': created_at,
                'message_count': message_count
            })

        # 按创建时间降序排序
        sessions.sort(key=lambda x: x['created_at'], reverse=True)

        return [
            SessionResponse(
                session_id=s['session_id'],
                first_question=s['first_question'],
                created_at=s['created_at'],
                message_count=s['message_count']
            )
            for s in sessions
        ]
    except Exception as e:
        logger.error(f"查询会话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询会话列表失败: {str(e)}")


@router.get("/ai-agent/sessions/{session_id}", response_model=List[HistoryResponse])
async def get_session_history(
    session_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户指定会话的完整对话历史
    严格基于 user_id 进行权限验证，防止越权访问
    """
    try:
        stmt = select(AskHistory).where(
            and_(
                AskHistory.session_id == session_id,
                AskHistory.user_id == current_user.id
            )
        ).order_by(AskHistory.created_at.asc())

        result = await db.execute(stmt)
        history = result.scalars().all()

        return [
            HistoryResponse(
                id=h.id,
                question=h.question,
                answer=h.answer,
                reasoning_content=h.reasoning_content or "",  # 添加推理内容
                created_at=h.created_at
            )
            for h in history
        ]
    except Exception as e:
        logger.error(f"查询会话历史失败 - 用户ID: {current_user.id}, 会话ID: {session_id}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询会话历史失败: {str(e)}")


@router.post("/ai-agent/sessions")
async def create_session(
    current_user: User = Depends(get_current_active_user)
):
    """
    创建新的对话会话
    返回新的session_id
    需要用户登录，确保会话与用户关联
    """
    try:
        new_session_id = str(uuid.uuid4())
        logger.info(f"创建新会话 - 用户ID: {current_user.id}, 会话ID: {new_session_id}")
        return {"session_id": new_session_id}
    except Exception as e:
        logger.error(f"创建会话失败 - 用户ID: {current_user.id}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.post("/ai-agent/ask-stream")
async def ask_question_stream(
    request: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    用户提问接口（流式传输）
    1. 优先从questions表中查找匹配的问题，如果找到则直接返回答案
    2. 如果没有找到匹配的问题，则调用AI服务生成回答（支持多模型切换、重试和自动降级）
    3. 使用Server-Sent Events (SSE)流式返回结果
    4. 保存对话历史（严格关联当前用户的 user_id）
    """
    # 在生成器外部先查询预设问题和必要的数据
    preset_question = await find_preset_question(request.question, db)
    
    async def generate():
        # 在生成器内部创建独立的数据库会话
        from app.core.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            try:
                logger.info(f"用户提问（流式） - 用户ID: {current_user.id}, 会话ID: {request.session_id}, 问题: {request.question}")

                # 1. 使用外部查询结果处理预设问题
                if preset_question:
                    # 找到匹配的预设问题，直接流式返回答案
                    logger.info(f"使用预设问题答案（流式） - 问题ID: {preset_question.id}, 问题: {preset_question.question}")

                    # 模拟流式输出，将答案分段发送
                    answer = preset_question.answer
                    chunk_size = 50  # 每50个字符分一段

                    for i in range(0, len(answer), chunk_size):
                        chunk = answer[i:i + chunk_size]
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                        await asyncio.sleep(0.05)  # 小延迟模拟打字效果

                    # 获取当前北京时间
                    current_time = get_beijing_time()

                    # 保存对话历史，标记为非AI生成
                    history = AskHistory(
                        session_id=request.session_id,
                        question=request.question,
                        answer=answer,
                        reasoning_content=None,
                        is_ai_generated=False,
                        ai_mode=None,
                        created_at=current_time,
                        user_id=current_user.id
                    )
                    session.add(history)
                    await session.commit()

                    logger.info(f"[预设问题回答（流式）] 用户ID: {current_user.id}, 会话ID: {request.session_id}, 时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

                    yield "data: [DONE]\n\n"
                    return

                # 2. 没有找到预设问题，调用AI服务生成回答
                from app.core.config import settings

                reasoning_content = ""
                full_answer = ""

                logger.info(f"未找到预设问题，开始调用AI服务（流式） - 用户选择模型: {request.model}, 深度思考: {request.deep_thinking}, 问题: {request.question}")

                if request.deep_thinking:
                    actual_model_name = settings.DEEPSEEK_MODEL_THINKING
                    actual_model_key = "deepseek"
                    logger.info(f"深度思考模式已启用，强制使用 DeepSeek 深度思考模型: {actual_model_name}")
                else:
                    if request.model == "deepseek":
                        actual_model_name = settings.DEEPSEEK_MODEL
                        actual_model_key = "deepseek"
                        logger.info(f"使用 DeepSeek 非深度思考模型: {actual_model_name}")
                    elif request.model == "glm":
                        actual_model_name = settings.GLM_MODEL
                        actual_model_key = "glm"
                    elif request.model == "qwen":
                        actual_model_name = settings.QWEN_TEXT_MODEL
                        actual_model_key = "qwen"
                    else:
                        actual_model_name = settings.DEEPSEEK_MODEL
                        actual_model_key = "deepseek"

                model_map = {
                    "deepseek": settings.DEEPSEEK_MODEL if not request.deep_thinking else settings.DEEPSEEK_MODEL_THINKING,
                    "glm": settings.GLM_MODEL,
                    "qwen": settings.QWEN_TEXT_MODEL
                }

                if request.deep_thinking:
                    fallback_order = {
                        "deepseek": [],
                        "glm": [],
                        "qwen": []
                    }
                else:
                    fallback_order = {
                        "deepseek": ["glm", "qwen"],
                        "glm": ["deepseek", "qwen"],
                        "qwen": ["deepseek", "glm"]
                    }

                # 调用流式 AI 服务
                stream_generator, success = await call_ai_service_with_retry(
                    actual_model_key,
                    actual_model_name,
                    request.question,
                    max_retries=2,
                    use_thinking_config=request.deep_thinking,
                    stream=True
                )

                used_model = actual_model_key
                selected_model_key = request.model

                # 如果失败，尝试降级
                if not success and not request.deep_thinking:
                    logger.warning(f"模型 {actual_model_key} 调用失败，开始尝试降级到备选模型")
                    fallback_models = fallback_order.get(actual_model_key, ["deepseek", "glm"])

                    for fallback_key in fallback_models:
                        fallback_name = model_map.get(fallback_key)
                        if not fallback_name:
                            continue

                        logger.info(f"尝试降级模型: {fallback_key} ({fallback_name})")

                        stream_generator, success = await call_ai_service_with_retry(
                            fallback_key,
                            fallback_name,
                            request.question,
                            max_retries=1,
                            use_thinking_config=False,
                            stream=True
                        )

                        if success:
                            used_model = fallback_key
                            logger.info(f"模型降级成功 - 从 {selected_model_key} 降级到 {fallback_key}")
                            break

                if success:
                    matched = False
                    is_ai_generated = True

                    # 如果使用了降级模型，先发送提示
                    if used_model != selected_model_key:
                        model_names = {
                            "deepseek": "DeepSeek",
                            "glm": "GLM（智谱清言）",
                            "qwen": "Qwen（通义千问）"
                        }
                        original_name = model_names.get(selected_model_key, selected_model_key)
                        used_name = model_names.get(used_model, used_model)
                        prefix_message = f"[提示：{original_name}模型暂时不可用，已自动切换到{used_name}模型]\n\n"
                        yield f"data: {json.dumps({'type': 'content', 'content': prefix_message})}\n\n"
                        full_answer += prefix_message

                    # 实时推送 AI 响应流
                    async for chunk in stream_generator:
                        if chunk.get("done"):
                            # 流式传输完成，使用收集的完整内容
                            if not full_answer:
                                full_answer = chunk.get("full_answer", "")
                            if not reasoning_content:
                                reasoning_content = chunk.get("full_reasoning", "")
                            break

                        # 推送推理内容
                        if chunk.get("reasoning_content"):
                            reasoning_content += chunk["reasoning_content"]
                            yield f"data: {json.dumps({'type': 'reasoning_content', 'content': chunk['reasoning_content']})}\n\n"

                        # 推送回答内容
                        if chunk.get("content"):
                            full_answer += chunk["content"]
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk['content']})}\n\n"

                    logger.info(f"AI服务最终成功（流式） - 使用模型: {used_model}, 回答长度: {len(full_answer)}")
                else:
                    logger.error(f"所有AI模型均调用失败 - 原始模型: {selected_model_key}")

                    model_names = {
                        "deepseek": "DeepSeek",
                        "glm": "GLM（智谱清言）",
                        "qwen": "Qwen（通义千问）"
                    }
                    original_name = model_names.get(selected_model_key, selected_model_key)

                    full_answer = f"抱歉，{original_name}模型暂时不可用，且备选模型也无法响应。\n\n建议您：\n1. 稍后重试\n2. 尝试切换到其他AI模型"
                    matched = False
                    is_ai_generated = False
                    yield f"data: {json.dumps({'type': 'content', 'content': full_answer})}\n\n"

                current_time = get_beijing_time()

                # 获取模型显示名称
                ai_mode = get_model_display_name(used_model, request.deep_thinking) if is_ai_generated else None

                history = AskHistory(
                    session_id=request.session_id,
                    question=request.question,
                    answer=full_answer,
                    reasoning_content=reasoning_content if request.deep_thinking else None,
                    is_ai_generated=is_ai_generated,
                    ai_mode=ai_mode,
                    created_at=current_time,
                    user_id=current_user.id
                )
                session.add(history)
                await session.commit()

                answer_time = get_beijing_time()
                answer_time_str = answer_time.strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"[AI回答（流式）] 用户ID: {current_user.id}, 会话ID: {request.session_id}, 时间: {answer_time_str}, 回答长度: {len(full_answer)}, 推理内容长度: {len(reasoning_content)}, AI生成: {is_ai_generated}, AI模型: {ai_mode}")

                yield "data: [DONE]\n\n"

            except Exception as e:
                await session.rollback()
                logger.error(f"处理提问失败（流式） - 用户ID: {current_user.id}, 会话ID: {request.session_id}, 错误: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'message': f'处理提问失败: {str(e)}'})}\n\n"
                yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


