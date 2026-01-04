"""
分析API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.typhoon import ImageAnalysis
from app.schemas.typhoon import ImageAnalysisCreate, ImageAnalysisResponse
from app.services.ai.qwen_service import qwen_service

router = APIRouter(prefix="/analysis", tags=["分析"])


@router.post("/image", response_model=ImageAnalysisResponse)
async def analyze_image(
    image_url: str = Body(None, description="图片URL"),
    image_path: str = Body(None, description="图片本地路径"),
    typhoon_id: str = Body(None, description="台风编号"),
    db: AsyncSession = Depends(get_db)
):
    """
    分析台风预报图
    
    使用通义千问Qwen3-VL模型智能解析台风预报图，提取结构化信息
    
    Args:
        image_url: 图片URL
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
    result = await qwen_service.analyze_typhoon_image(
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
    
    # 保存分析结果
    db_analysis = ImageAnalysis(
        typhoon_id=typhoon_id,
        typhoon_name=extracted_data.get("typhoon_name"),
        image_url=image_url or "",
        image_path=image_path or "",
        analysis_result=result["analysis_text"],
        extracted_data=extracted_data,
        model_used=result["model_used"]
    )
    
    db.add(db_analysis)
    await db.commit()
    await db.refresh(db_analysis)
    
    return db_analysis


@router.get("/{typhoon_id}", response_model=list[ImageAnalysisResponse])
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

