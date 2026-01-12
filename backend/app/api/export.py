"""
数据导出API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import csv
import json
import io
from datetime import datetime

from app.core.database import get_db
from app.models.typhoon import Typhoon, TyphoonPath
from pydantic import BaseModel

router = APIRouter(prefix="/export", tags=["数据导出"])


# ========== 请求/响应模型 ==========
class BatchExportRequest(BaseModel):
    """批量导出请求"""
    typhoon_ids: List[str]
    format: str = "csv"  # csv 或 json
    include_path: bool = True


# ========== 辅助函数 ==========
def generate_csv_content(typhoon_data: dict, include_path: bool = True) -> str:
    """生成CSV内容"""
    output = io.StringIO()

    if include_path and typhoon_data.get('paths'):
        # 包含路径数据的CSV
        writer = csv.writer(output)
        writer.writerow([
            '台风编号(typhoon_id)', '英文名(typhoon_name)', '中文名(typhoon_name_cn)', '年份(year)',
            '时间(timestamp)', '纬度(latitude)', '经度(longitude)', '中心气压(center_pressure)',
            '最大风速(max_wind_speed)', '移动速度(moving_speed)', '移动方向(moving_direction)', '强度等级(intensity)'
        ])
        
        for path in typhoon_data['paths']:
            writer.writerow([
                typhoon_data['typhoon_id'],
                typhoon_data['typhoon_name'],
                typhoon_data.get('typhoon_name_cn', ''),
                typhoon_data['year'],
                path['timestamp'],
                path['latitude'],
                path['longitude'],
                path.get('center_pressure', ''),
                path.get('max_wind_speed', ''),
                path.get('moving_speed', ''),
                path.get('moving_direction', ''),
                path.get('intensity', '')
            ])
    else:
        # 仅基本信息的CSV
        writer = csv.writer(output)
        writer.writerow(['台风编号(typhoon_id)', '英文名(typhoon_name)', '中文名(typhoon_name_cn)', '年份(year)', '状态(status)'])
        writer.writerow([
            typhoon_data['typhoon_id'],
            typhoon_data['typhoon_name'],
            typhoon_data.get('typhoon_name_cn', ''),
            typhoon_data['year'],
            typhoon_data.get('status', '')
        ])

    return output.getvalue()


def generate_json_content(typhoon_data: dict, include_path: bool = True) -> str:
    """生成JSON内容"""
    if not include_path:
        # 移除路径数据
        export_data = {k: v for k, v in typhoon_data.items() if k != 'paths'}
    else:
        export_data = typhoon_data
    
    return json.dumps(export_data, ensure_ascii=False, indent=2)


# ========== API端点 ==========

@router.get("/typhoon/{typhoon_id}")
async def export_typhoon_data(
    typhoon_id: str,
    format: str = Query("csv", regex="^(csv|json)$", description="导出格式"),
    include_path: bool = Query(True, description="是否包含路径数据"),
    db: AsyncSession = Depends(get_db)
):
    """
    导出单个台风数据
    
    支持CSV和JSON两种格式
    可选择是否包含路径数据
    """
    # 查询台风基本信息
    typhoon_query = select(Typhoon).where(Typhoon.typhoon_id == typhoon_id)
    typhoon_result = await db.execute(typhoon_query)
    typhoon = typhoon_result.scalar_one_or_none()
    
    if not typhoon:
        raise HTTPException(status_code=404, detail=f"台风 {typhoon_id} 不存在")
    
    # 构建基本数据
    typhoon_data = {
        "typhoon_id": typhoon.typhoon_id,
        "typhoon_name": typhoon.typhoon_name,
        "typhoon_name_cn": typhoon.typhoon_name_cn,
        "year": typhoon.year,
        "status": typhoon.status
    }
    
    # 查询路径数据
    if include_path:
        path_query = select(TyphoonPath).where(
            TyphoonPath.typhoon_id == typhoon_id
        ).order_by(TyphoonPath.timestamp)
        path_result = await db.execute(path_query)
        paths = path_result.scalars().all()
        
        typhoon_data['paths'] = [
            {
                "timestamp": str(p.timestamp),
                "latitude": p.latitude,
                "longitude": p.longitude,
                "center_pressure": p.center_pressure,
                "max_wind_speed": p.max_wind_speed,
                "moving_speed": p.moving_speed,
                "moving_direction": p.moving_direction,
                "intensity": p.intensity
            }
            for p in paths
        ]
    
    # 生成文件内容
    if format == "csv":
        content = generate_csv_content(typhoon_data, include_path)
        media_type = "text/csv"
        filename = f"typhoon_{typhoon_id}_{datetime.now().strftime('%Y%m%d')}.csv"
    else:  # json
        content = generate_json_content(typhoon_data, include_path)
        media_type = "application/json"
        filename = f"typhoon_{typhoon_id}_{datetime.now().strftime('%Y%m%d')}.json"
    
    # 返回文件流
    return StreamingResponse(
        io.BytesIO(content.encode('utf-8-sig')),  # 使用utf-8-sig支持Excel打开CSV
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/batch")
async def export_batch_typhoons(
    request: BatchExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    批量导出多个台风数据
    
    将多个台风数据合并到一个文件中导出
    """
    if not request.typhoon_ids:
        raise HTTPException(status_code=400, detail="台风编号列表不能为空")
    
    if len(request.typhoon_ids) > 50:
        raise HTTPException(status_code=400, detail="最多只能批量导出50个台风")
    
    all_typhoon_data = []
    
    for typhoon_id in request.typhoon_ids:
        # 查询台风基本信息
        typhoon_query = select(Typhoon).where(Typhoon.typhoon_id == typhoon_id)
        typhoon_result = await db.execute(typhoon_query)
        typhoon = typhoon_result.scalar_one_or_none()
        
        if not typhoon:
            continue
        
        typhoon_data = {
            "typhoon_id": typhoon.typhoon_id,
            "typhoon_name": typhoon.typhoon_name,
            "typhoon_name_cn": typhoon.typhoon_name_cn,
            "year": typhoon.year,
            "status": typhoon.status
        }
        
        # 查询路径数据
        if request.include_path:
            path_query = select(TyphoonPath).where(
                TyphoonPath.typhoon_id == typhoon_id
            ).order_by(TyphoonPath.timestamp)
            path_result = await db.execute(path_query)
            paths = path_result.scalars().all()
            
            typhoon_data['paths'] = [
                {
                    "timestamp": str(p.timestamp),
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                    "center_pressure": p.center_pressure,
                    "max_wind_speed": p.max_wind_speed,
                    "moving_speed": p.moving_speed,
                    "moving_direction": p.moving_direction,
                    "intensity": p.intensity
                }
                for p in paths
            ]
        
        all_typhoon_data.append(typhoon_data)
    
    if not all_typhoon_data:
        raise HTTPException(status_code=404, detail="未找到任何有效的台风数据")
    
    # 生成文件内容
    if request.format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        if request.include_path:
            # 包含路径数据的CSV
            writer.writerow([
                '台风编号(typhoon_id)', '英文名(typhoon_name)', '中文名(typhoon_name_cn)', '年份(year)',
                '时间(timestamp)', '纬度(latitude)', '经度(longitude)', '中心气压(center_pressure)',
                '最大风速(max_wind_speed)', '移动速度(moving_speed)', '移动方向(moving_direction)', '强度等级(intensity)'
            ])
            
            for typhoon_data in all_typhoon_data:
                for path in typhoon_data.get('paths', []):
                    writer.writerow([
                        typhoon_data['typhoon_id'],
                        typhoon_data['typhoon_name'],
                        typhoon_data.get('typhoon_name_cn', ''),
                        typhoon_data['year'],
                        path['timestamp'],
                        path['latitude'],
                        path['longitude'],
                        path.get('center_pressure', ''),
                        path.get('max_wind_speed', ''),
                        path.get('moving_speed', ''),
                        path.get('moving_direction', ''),
                        path.get('intensity', '')
                    ])
        else:
            # 仅基本信息的CSV
            writer.writerow(['台风编号(typhoon_id)', '英文名(typhoon_name)', '中文名(typhoon_name_cn)', '年份(year)', '状态(status)'])
            for typhoon_data in all_typhoon_data:
                writer.writerow([
                    typhoon_data['typhoon_id'],
                    typhoon_data['typhoon_name'],
                    typhoon_data.get('typhoon_name_cn', ''),
                    typhoon_data['year'],
                    typhoon_data.get('status', '')
                ])
        
        content = output.getvalue()
        media_type = "text/csv"
        filename = f"typhoons_batch_{datetime.now().strftime('%Y%m%d')}.csv"
    else:  # json
        content = json.dumps(all_typhoon_data, ensure_ascii=False, indent=2)
        media_type = "application/json"
        filename = f"typhoons_batch_{datetime.now().strftime('%Y%m%d')}.json"
    
    # 返回文件流
    return StreamingResponse(
        io.BytesIO(content.encode('utf-8-sig')),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

