"""
台风编号格式转换工具

处理台风编号的格式转换：
- 4位格式: 2601 (年份后2位 + 编号2位)
- 6位格式: 202601 (完整年份4位 + 编号2位)
"""
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def normalize_typhoon_id(typhoon_id: str) -> str:
    """
    将台风编号统一转换为6位格式
    
    支持的输入格式：
    - 4位格式: "2601" -> "202601"
    - 6位格式: "202601" -> "202601"
    - 数字: 2601 -> "202601"
    
    Args:
        typhoon_id: 原始台风编号
        
    Returns:
        标准化的6位台风编号
        
    Raises:
        ValueError: 格式无效时抛出
    """
    if typhoon_id is None:
        raise ValueError("台风编号不能为空")
    
    # 转换为字符串并去除空白
    typhoon_id = str(typhoon_id).strip()
    
    if not typhoon_id:
        raise ValueError("台风编号不能为空")
    
    # 检查是否为纯数字
    if not typhoon_id.isdigit():
        raise ValueError(f"台风编号必须是数字，当前值: {typhoon_id}")
    
    # 根据长度处理
    if len(typhoon_id) == 6:
        # 已经是6位格式
        return typhoon_id
    elif len(typhoon_id) == 4:
        # 4位格式，需要转换为6位
        # 根据当前年份判断世纪
        year_suffix = typhoon_id[:2]
        number = typhoon_id[2:]
        
        current_year = datetime.now().year
        current_century = current_year // 100 * 100  # 如 2000, 2100
        
        # 尝试当前世纪
        full_year = current_century + int(year_suffix)
        
        # 如果结果年份大于当前年份+1，则可能是上个世纪
        if full_year > current_year + 1:
            full_year -= 100
        
        normalized = f"{full_year}{number}"
        logger.debug(f"台风编号转换: {typhoon_id} -> {normalized}")
        return normalized
    elif len(typhoon_id) == 5:
        # 可能是5位格式（年份1位+编号2位 或 年份2位+编号1位）
        # 优先尝试年份2位+编号1位
        year_suffix = typhoon_id[:2]
        number = typhoon_id[2:].zfill(2)  # 补齐到2位
        
        current_year = datetime.now().year
        current_century = current_year // 100 * 100
        
        full_year = current_century + int(year_suffix)
        if full_year > current_year + 1:
            full_year -= 100
        
        normalized = f"{full_year}{number}"
        logger.debug(f"台风编号转换: {typhoon_id} -> {normalized}")
        return normalized
    else:
        raise ValueError(f"台风编号格式无效，期望4位或6位数字，当前值: {typhoon_id}")


def convert_to_4digit(typhoon_id: str) -> str:
    """
    将台风编号转换为4位格式（简短格式）
    
    Args:
        typhoon_id: 原始台风编号
        
    Returns:
        4位格式台风编号
    """
    normalized = normalize_typhoon_id(typhoon_id)
    # 取年份后2位 + 编号2位
    return normalized[2:]


def extract_year(typhoon_id: str) -> int:
    """
    从台风编号中提取年份
    
    Args:
        typhoon_id: 台风编号
        
    Returns:
        年份（4位数字）
    """
    normalized = normalize_typhoon_id(typhoon_id)
    return int(normalized[:4])


def extract_number(typhoon_id: str) -> int:
    """
    从台风编号中提取当年编号
    
    Args:
        typhoon_id: 台风编号
        
    Returns:
        当年编号（1-99）
    """
    normalized = normalize_typhoon_id(typhoon_id)
    return int(normalized[4:])


def is_valid_typhoon_id(typhoon_id: str) -> bool:
    """
    检查台风编号是否有效
    
    Args:
        typhoon_id: 台风编号
        
    Returns:
        是否有效
    """
    try:
        normalize_typhoon_id(typhoon_id)
        return True
    except ValueError:
        return False


def format_typhoon_id(typhoon_id: str, format: str = "6digit") -> str:
    """
    格式化台风编号
    
    Args:
        typhoon_id: 原始台风编号
        format: 输出格式 ("6digit" | "4digit" | "full")
            - "6digit": 202601
            - "4digit": 2601
            - "full": 2026-01
            
    Returns:
        格式化后的台风编号
    """
    normalized = normalize_typhoon_id(typhoon_id)
    
    if format == "6digit":
        return normalized
    elif format == "4digit":
        return normalized[2:]
    elif format == "full":
        return f"{normalized[:4]}-{normalized[4:]}"
    else:
        raise ValueError(f"未知格式: {format}")


def try_normalize_typhoon_id(typhoon_id: Optional[str], default: Optional[str] = None) -> Optional[str]:
    """
    尝试标准化台风编号，失败时返回默认值
    
    Args:
        typhoon_id: 原始台风编号
        default: 失败时的默认值
        
    Returns:
        标准化后的编号或默认值
    """
    if typhoon_id is None:
        return default
    
    try:
        return normalize_typhoon_id(typhoon_id)
    except ValueError:
        return default
