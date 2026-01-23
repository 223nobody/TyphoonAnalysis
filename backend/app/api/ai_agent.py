"""
AI客服API接口
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Tuple
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import uuid
import logging

from app.core.database import get_db
from app.models.typhoon import Question, AskHistory

router = APIRouter(tags=["AI客服"])
logger = logging.getLogger(__name__)

# 定义北京时区（UTC+8）
BEIJING_TZ = timezone(timedelta(hours=8))


def get_beijing_time():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)


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
    max_retries: int = 2
) -> Tuple[str, bool]:
    """
    调用AI服务并支持重试机制

    Args:
        model_key: 模型键名（deepseek, glm, qwen）
        model_name: 实际的模型名称
        question: 用户问题
        max_retries: 最大重试次数

    Returns:
        (answer, success): 回答内容和是否成功的标志
    """
    import httpx
    from app.core.config import settings
    import asyncio

    # 优化的系统提示词
    system_prompt = """你是一个通用型智能助手，具备多领域的知识解答能力，需严格遵循以下规则：

1. 核心能力：
   - 通用知识解答：回答生活、科技、文化、教育、气象、职场等多领域的常见问题；
   - 逻辑分析：针对用户的问题提供清晰、有条理的分析和解决方案；
   - 信息解读：用通俗易懂的语言解释专业概念、数据和规则；
   - 建议给出：基于客观事实为用户提供合理、可落地的建议；
   - 多轮对话：结合历史上下文保持回答的连贯性和一致性。

2. 回答准则（强制遵守）：
   - 格式要求：
     1. 仅使用纯文本回答,禁止使用任何markdown标记(包括**、###、---、` `、🔍、📱等符号/表情);
     2. 复杂问题优先用数字序号分点说明,层级用“1.1/1.2”或“-”区分，避免杂乱排版;
     3. 使用数字序号分点说明时每个分点回答完需要换行;
     4. 关键信息直接陈述，无需额外装饰性符号，保持文本整洁;
     5. 回答内容不能少于400字;
   - 风格要求：专业、简洁、易懂，根据问题领域适配语气（气象与科学问题偏严谨）；
"""

    # 【优化2】调整模型参数，提升规范性
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "stream": False,
        "temperature": 0.8,  # 降低随机性
        "top_p": 0.95,        # 提升聚焦性
        "presence_penalty": 0.1,  # 新增：减少重复内容，提升多样性
        "frequency_penalty": 0.1, # 新增：避免模型过度谨慎
        "max_tokens": 3000,
        "stop": None
    }

    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json"
    }

    # 重试逻辑
    for attempt in range(max_retries):
        try:
            logger.info(f"尝试调用AI服务 - 模型: {model_key} ({model_name}), 尝试次数: {attempt + 1}/{max_retries}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.AI_API_BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result_data = response.json()

                # 提取AI回答
                answer = result_data.get("choices", [{}])[0].get("message", {}).get("content", "")

                if answer:
                    logger.info(f"AI服务回答成功 - 模型: {model_key}, 回答长度: {len(answer)}")
                    return answer, True
                else:
                    logger.warning(f"AI服务返回空回答 - 模型: {model_key}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)  # 等待1秒后重试
                        continue
                    return "", False

        except httpx.TimeoutException:
            logger.warning(f"AI服务请求超时 - 模型: {model_key}, 尝试次数: {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # 等待1秒后重试
                continue
            return "", False

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.warning(f"AI服务HTTP错误 - 模型: {model_key}, 状态码: {status_code}, 尝试次数: {attempt + 1}/{max_retries}")

            # 对于503等临时错误，进行重试
            if status_code in [503, 502, 504] and attempt < max_retries - 1:
                await asyncio.sleep(2)  # 等待2秒后重试
                continue
            return "", False

        except Exception as e:
            logger.warning(f"调用AI服务异常 - 模型: {model_key}, 错误: {str(e)}, 尝试次数: {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # 等待1秒后重试
                continue
            return "", False

    return "", False


@router.post("/ai-agent/ask", response_model=AskResponse)
async def ask_question(request: AskRequest, db: AsyncSession = Depends(get_db)):
    """
    用户提问接口
    1. 尝试匹配预设问题
    2. 如果未匹配，调用AI服务生成回答（支持多模型切换、重试和自动降级）
    3. 保存对话历史
    4. 返回答案
    """
    try:
        # 尝试模糊匹配预设问题
        stmt = select(Question).where(Question.question.like(f"%{request.question}%"))
        result = await db.execute(stmt)
        matched_question = result.scalar_one_or_none()

        is_ai_generated = False  # 标记是否由AI生成

        if matched_question:
            # 匹配到预设问题
            answer = matched_question.answer
            matched = True
            is_ai_generated = False
        else:
            # 未匹配到，调用AI服务生成回答
            from app.core.config import settings

            logger.info(f"开始调用AI服务 - 用户选择模型: {request.model}, 深度思考: {request.deep_thinking}, 问题: {request.question}")

            # 根据深度思考模式和用户选择的模型，确定实际使用的模型
            if request.deep_thinking:
                # 启用深度思考模式：不管选择什么模型，都使用 DEEPSEEK_MODEL
                actual_model_name = settings.DEEPSEEK_MODEL
                actual_model_key = "deepseek"
                logger.info(f"深度思考模式已启用，强制使用 DeepSeek 深度思考模型: {actual_model_name}")
            else:
                # 未启用深度思考模式：根据用户选择的模型决定
                if request.model == "deepseek":
                    # 选择 deepseek 且未启用深度思考，使用 DEEPSEEK_NOTHINK_MODEL
                    actual_model_name = settings.DEEPSEEK_NOTHINK_MODEL
                    actual_model_key = "deepseek"
                    logger.info(f"使用 DeepSeek 非深度思考模型: {actual_model_name}")
                elif request.model == "glm":
                    actual_model_name = settings.GLM_MODEL
                    actual_model_key = "glm"
                elif request.model == "qwen":
                    actual_model_name = settings.QWEN_TEXT_MODEL
                    actual_model_key = "qwen"
                else:
                    # 默认使用 DEEPSEEK_NOTHINK_MODEL
                    actual_model_name = settings.DEEPSEEK_NOTHINK_MODEL
                    actual_model_key = "deepseek"

            # 模型映射（用于降级）
            model_map = {
                "deepseek": settings.DEEPSEEK_NOTHINK_MODEL if not request.deep_thinking else settings.DEEPSEEK_MODEL,
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
            answer, success = await call_ai_service_with_retry(
                actual_model_key,
                actual_model_name,
                request.question,
                max_retries=2
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

                    answer, success = await call_ai_service_with_retry(
                        fallback_key,
                        fallback_name,
                        request.question,
                        max_retries=1  # 降级模型只重试1次
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

                answer = f"抱歉，{original_name}模型暂时不可用，且备选模型也无法响应。\n\n建议您：\n1. 稍后重试\n2. 尝试切换到其他AI模型\n3. 从左侧预设问题中选择"
                matched = False
                is_ai_generated = False

        # 获取当前北京时间
        current_time = get_beijing_time()

        # 保存对话历史，标记是否由AI生成，使用北京时间
        history = AskHistory(
            session_id=request.session_id,
            question=request.question,
            answer=answer,
            is_ai_generated=is_ai_generated,
            created_at=current_time
        )
        db.add(history)
        await db.commit()

        # 打印AI回答时间
        answer_time = get_beijing_time()
        answer_time_str = answer_time.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[AI回答] 时间: {answer_time_str}, 回答长度: {len(answer)}")

        return AskResponse(answer=answer, matched=matched)
    except Exception as e:
        await db.rollback()
        logger.error(f"处理提问失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理提问失败: {str(e)}")


@router.get("/ai-agent/sessions", response_model=List[SessionResponse])
async def get_sessions(db: AsyncSession = Depends(get_db)):
    """
    获取所有对话会话列表
    优先使用AI生成的第一条问题作为标题，如果没有则使用第一条提问
    """
    try:
        from sqlalchemy import and_

        # 获取所有会话ID
        sessions_stmt = select(AskHistory.session_id).distinct()
        sessions_result = await db.execute(sessions_stmt)
        session_ids = [row[0] for row in sessions_result.all()]

        sessions = []
        for session_id in session_ids:
            # 优先查找AI生成的第一条记录
            ai_stmt = select(AskHistory).where(
                and_(
                    AskHistory.session_id == session_id,
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
                    AskHistory.session_id == session_id
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
                AskHistory.session_id == session_id
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
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    获取指定会话的完整对话历史
    """
    try:
        stmt = select(AskHistory).where(
            AskHistory.session_id == session_id
        ).order_by(AskHistory.created_at.asc())

        result = await db.execute(stmt)
        history = result.scalars().all()

        return [
            HistoryResponse(
                id=h.id,
                question=h.question,
                answer=h.answer,
                created_at=h.created_at
            )
            for h in history
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询会话历史失败: {str(e)}")


@router.post("/ai-agent/sessions")
async def create_session():
    """
    创建新的对话会话
    返回新的session_id
    """
    try:
        new_session_id = str(uuid.uuid4())
        return {"session_id": new_session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")

