"""
分析API路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.typhoon import ImageAnalysis
from app.schemas.typhoon import ImageAnalysisCreate, ImageAnalysisResponse
from app.services.ai.ai_factory import ai_factory

router = APIRouter(prefix="/analysis", tags=["分析"])


@router.post("/satellite-image", response_model=ImageAnalysisResponse)
async def analyze_satellite_image(
    image_url: str = Body(None, description="图片URL"),
    image_path: str = Body(None, description="图片本地路径"),
    typhoon_id: str = Body(None, description="台风编号"),
    db: AsyncSession = Depends(get_db)
):
    """
    分析台风卫星图像

    使用通义千问Qwen3-VL模型智能解析台风预报图，提取结构化信息

    Args:
        image_url: 图片URL（支持http/https URL或base64编码）
        image_path: 图片本地路径
        typhoon_id: 台风编号（可选）

    Returns:
        ImageAnalysisResponse: 分析结果
    """
    if not image_url and not image_path:
        raise HTTPException(
            status_code=400,
            detail="必须提供image_url或image_path"
        )
    
    # 调用AI服务分析图片
    result = await ai_factory.analyze_typhoon_image(
        image_path=image_path,
        image_url=image_url
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"图像分析失败: {result.get('error', '未知错误')}"
        )
    
    # 从提取的数据中获取台风信息
    extracted_data = result.get("extracted_data", {})
    if not typhoon_id and extracted_data:
        typhoon_id = extracted_data.get("typhoon_id")

    # 处理 analysis_text，确保是字符串类型
    analysis_text = result.get("analysis_text", "")
    if isinstance(analysis_text, list):
        # 如果是列表，提取文本内容并合并
        text_parts = []
        for item in analysis_text:
            if isinstance(item, dict) and "text" in item:
                text_parts.append(str(item["text"]))
            elif isinstance(item, str):
                text_parts.append(item)
            else:
                text_parts.append(str(item))
        analysis_text = "\n".join(text_parts)
    elif not isinstance(analysis_text, str):
        analysis_text = str(analysis_text) if analysis_text else ""

    # 处理 extracted_data，确保是字典类型（用于JSON序列化）
    if not isinstance(extracted_data, dict):
        extracted_data = {"raw_data": str(extracted_data)} if extracted_data else {}

    # 保存分析结果
    db_analysis = ImageAnalysis(
        typhoon_id=typhoon_id,
        typhoon_name=extracted_data.get("typhoon_name"),
        image_url=image_url or "",
        image_path=image_path or "",
        analysis_result=analysis_text,
        extracted_data=extracted_data,
        model_used=result.get("model_used", "unknown")
    )

    db.add(db_analysis)
    await db.commit()
    await db.refresh(db_analysis)
    
    return db_analysis


@router.get("/{typhoon_id}", response_model=List[ImageAnalysisResponse])
async def get_analyses(
    typhoon_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """获取台风的图像分析记录"""
    query = select(ImageAnalysis).where(
        ImageAnalysis.typhoon_id == typhoon_id
    ).order_by(desc(ImageAnalysis.created_at)).limit(limit)

    result = await db.execute(query)
    analyses = result.scalars().all()

    return analyses

