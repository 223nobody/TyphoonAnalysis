"""
评估指标模块

提供预测准确性评估指标计算
"""
import numpy as np
from typing import List, Optional, Tuple
from math import radians, sin, cos, sqrt, atan2

from app.models.typhoon import TyphoonPath


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    计算两点间的Haversine距离 (公里)

    Args:
        lat1: 点1纬度
        lon1: 点1经度
        lat2: 点2纬度
        lon2: 点2经度

    Returns:
        距离 (公里)
    """
    R = 6371  # 地球半径 (公里)

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def calculate_path_error(
    predicted_lats: List[float],
    predicted_lons: List[float],
    actual_lats: List[float],
    actual_lons: List[float]
) -> dict:
    """
    计算路径预测误差

    Args:
        predicted_lats: 预测纬度列表
        predicted_lons: 预测经度列表
        actual_lats: 实际纬度列表
        actual_lons: 实际经度列表

    Returns:
        误差指标字典
    """
    if len(predicted_lats) != len(actual_lats):
        raise ValueError("预测值和实际值长度不匹配")

    distances = []
    lat_errors = []
    lon_errors = []

    for i in range(len(predicted_lats)):
        # Haversine距离
        dist = haversine_distance(
            predicted_lats[i], predicted_lons[i],
            actual_lats[i], actual_lons[i]
        )
        distances.append(dist)

        # 经纬度绝对误差
        lat_errors.append(abs(predicted_lats[i] - actual_lats[i]))
        lon_errors.append(abs(predicted_lons[i] - actual_lons[i]))

    return {
        "mean_distance_error_km": np.mean(distances),
        "max_distance_error_km": np.max(distances),
        "mean_lat_error": np.mean(lat_errors),
        "mean_lon_error": np.mean(lon_errors),
        "distance_errors": distances
    }


def calculate_intensity_error(
    predicted_pressures: List[Optional[float]],
    predicted_winds: List[Optional[float]],
    actual_pressures: List[Optional[float]],
    actual_winds: List[Optional[float]]
) -> dict:
    """
    计算强度预测误差

    Args:
        predicted_pressures: 预测气压列表
        predicted_winds: 预测风速列表
        actual_pressures: 实际气压列表
        actual_winds: 实际风速列表

    Returns:
        误差指标字典
    """
    pressure_errors = []
    wind_errors = []

    for i in range(len(predicted_pressures)):
        if predicted_pressures[i] is not None and actual_pressures[i] is not None:
            pressure_errors.append(abs(predicted_pressures[i] - actual_pressures[i]))

        if predicted_winds[i] is not None and actual_winds[i] is not None:
            wind_errors.append(abs(predicted_winds[i] - actual_winds[i]))

    result = {
        "pressure_error_count": len(pressure_errors),
        "wind_error_count": len(wind_errors)
    }

    if pressure_errors:
        result["mean_pressure_error_hpa"] = np.mean(pressure_errors)
        result["max_pressure_error_hpa"] = np.max(pressure_errors)

    if wind_errors:
        result["mean_wind_error_ms"] = np.mean(wind_errors)
        result["max_wind_error_ms"] = np.max(wind_errors)

    return result


def calculate_rmse(predictions: List[float], actuals: List[float]) -> float:
    """
    计算均方根误差 (RMSE)

    Args:
        predictions: 预测值列表
        actuals: 实际值列表

    Returns:
        RMSE值
    """
    if len(predictions) != len(actuals):
        raise ValueError("预测值和实际值长度不匹配")

    errors = np.array(predictions) - np.array(actuals)
    return np.sqrt(np.mean(errors ** 2))


def calculate_mae(predictions: List[float], actuals: List[float]) -> float:
    """
    计算平均绝对误差 (MAE)

    Args:
        predictions: 预测值列表
        actuals: 实际值列表

    Returns:
        MAE值
    """
    if len(predictions) != len(actuals):
        raise ValueError("预测值和实际值长度不匹配")

    errors = np.abs(np.array(predictions) - np.array(actuals))
    return np.mean(errors)


def calculate_mape(predictions: List[float], actuals: List[float]) -> float:
    """
    计算平均绝对百分比误差 (MAPE)

    Args:
        predictions: 预测值列表
        actuals: 实际值列表

    Returns:
        MAPE值 (%)
    """
    if len(predictions) != len(actuals):
        raise ValueError("预测值和实际值长度不匹配")

    actuals_array = np.array(actuals)
    # 避免除以0
    mask = actuals_array != 0
    if not mask.any():
        return 0.0

    errors = np.abs((np.array(predictions) - actuals_array) / actuals_array)
    return np.mean(errors[mask]) * 100
