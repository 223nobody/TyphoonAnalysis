"""
数据验证模块

提供输入数据验证功能
"""
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.models.typhoon import TyphoonPath


def normalize_datetime(dt: datetime) -> datetime:
    """
    标准化时间戳，确保所有时间都是带时区的（aware）
    
    Args:
        dt: 输入时间（可能是naive或aware）
        
    Returns:
        带时区的datetime对象
    """
    if dt is None:
        return None
    
    # 如果已经是aware，直接返回
    if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
        return dt
    
    # 如果是naive，假设为UTC时区
    return dt.replace(tzinfo=timezone.utc)


@dataclass
class ValidationResult:
    """验证结果数据类"""
    is_valid: bool
    error_message: Optional[str] = None
    warning_messages: List[str] = None

    def __post_init__(self):
        if self.warning_messages is None:
            self.warning_messages = []


def validate_paths_data(
    paths: List[TyphoonPath],
    min_points: int = 3,
    min_time_span_hours: int = 12
) -> ValidationResult:
    """
    验证路径数据有效性

    Args:
        paths: 路径数据列表
        min_points: 最小数据点数量
        min_time_span_hours: 最小时间跨度(小时)

    Returns:
        ValidationResult: 验证结果
    """
    warnings = []

    # 1. 检查数据点数量
    if len(paths) < min_points:
        return ValidationResult(
            is_valid=False,
            error_message=f"历史数据不足，至少需要{min_points}个观测点，当前只有{len(paths)}个"
        )

    # 2. 按时间排序（使用标准化后的时间）
    sorted_paths = sorted(paths, key=lambda x: normalize_datetime(x.timestamp))

    # 3. 检查时间跨度（使用标准化后的时间）
    first_time = normalize_datetime(sorted_paths[0].timestamp)
    last_time = normalize_datetime(sorted_paths[-1].timestamp)
    time_span = last_time - first_time
    if time_span.total_seconds() < min_time_span_hours * 3600:
        return ValidationResult(
            is_valid=False,
            error_message=f"历史时间跨度不足，至少需要{min_time_span_hours}小时，当前只有{time_span.total_seconds() / 3600:.1f}小时"
        )

    # 4. 检查经纬度有效性
    for i, path in enumerate(sorted_paths):
        if path.latitude is None or path.longitude is None:
            return ValidationResult(
                is_valid=False,
                error_message=f"第{i+1}个数据点缺少经纬度信息"
            )

        if not (-90 <= path.latitude <= 90):
            return ValidationResult(
                is_valid=False,
                error_message=f"第{i+1}个数据点纬度异常: {path.latitude}"
            )

        if not (-180 <= path.longitude <= 180):
            warnings.append(f"第{i+1}个数据点经度超出[-180, 180]范围: {path.longitude}")

    # 5. 检查时间连续性（使用标准化后的时间）
    for i in range(1, len(sorted_paths)):
        curr_time = normalize_datetime(sorted_paths[i].timestamp)
        prev_time = normalize_datetime(sorted_paths[i-1].timestamp)
        time_diff = curr_time - prev_time
        if time_diff.total_seconds() > 24 * 3600:  # 超过24小时的间隔
            warnings.append(f"第{i}与第{i+1}个数据点之间时间间隔过大: {time_diff}")

    # 6. 检查气压和风速
    valid_pressures = [p.center_pressure for p in sorted_paths if p.center_pressure is not None]
    valid_winds = [p.max_wind_speed for p in sorted_paths if p.max_wind_speed is not None]

    if len(valid_pressures) < min_points // 2:
        warnings.append("气压数据缺失较多，可能影响强度预测准确性")

    if len(valid_winds) < min_points // 2:
        warnings.append("风速数据缺失较多，可能影响强度预测准确性")

    return ValidationResult(
        is_valid=True,
        warning_messages=warnings
    )


def validate_prediction_request(
    typhoon_id: str,
    forecast_hours: int
) -> ValidationResult:
    """
    验证预测请求参数

    Args:
        typhoon_id: 台风编号
        forecast_hours: 预报时效

    Returns:
        ValidationResult: 验证结果
    """
    # 验证台风编号
    if not typhoon_id or not typhoon_id.strip():
        return ValidationResult(
            is_valid=False,
            error_message="台风编号不能为空"
        )

    # 验证预报时效
    valid_hours = [12, 24, 48, 72, 120]
    if forecast_hours not in valid_hours:
        return ValidationResult(
            is_valid=False,
            error_message=f"预报时效必须是以下值之一: {valid_hours}"
        )

    return ValidationResult(is_valid=True)
