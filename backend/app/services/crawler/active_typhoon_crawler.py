"""
活跃台风数据爬虫 - 从浙江台风网获取活跃台风路径数据
"""
import requests
import logging
from typing import Optional, List, Dict
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ActiveTyphoonCrawler:
    """活跃台风数据爬虫"""

    def __init__(self):
        # 浙江台风网API地址（可能需要根据实际情况调整）
        self.base_url = "https://typhoon.slt.zj.gov.cn/Api/TyphoonInfo"
        self.alternative_urls = [
            "https://typhoon.slt.zj.gov.cn/Api/TyphoonInfo",
            "https://typhoon.slt.zj.gov.cn/api/typhooninfo",
            "https://typhoon.slt.zj.gov.cn/Api/Typhoon",
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://typhoon.slt.zj.gov.cn/',
        }

    def fetch_active_typhoon_data(self, year_month: str = "202601") -> Optional[Dict]:
        """
        获取活跃台风数据

        Args:
            year_month: 年月，格式如 "202601"

        Returns:
            台风数据字典，如果失败返回None
        """
        # 尝试多个可能的URL
        urls_to_try = [
            f"{self.base_url}/{year_month}",
            f"{self.base_url}?year={year_month[:4]}&month={year_month[4:]}",
            f"{self.base_url}?yearMonth={year_month}",
        ]

        for url in urls_to_try:
            try:
                logger.info(f"正在尝试爬取活跃台风数据: {url}")

                response = requests.get(url, headers=self.headers, timeout=10)
                logger.info(f"响应状态码: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        logger.info(f"成功获取活跃台风数据，数据类型: {type(data)}")

                        # 打印数据结构用于调试
                        if isinstance(data, dict):
                            logger.info(f"数据字典键: {list(data.keys())}")
                        elif isinstance(data, list):
                            logger.info(f"数据列表长度: {len(data)}")

                        # 如果数据不为空，返回
                        if data:
                            return data
                        else:
                            logger.warning(f"URL {url} 返回空数据")

                    except json.JSONDecodeError as e:
                        logger.warning(f"URL {url} JSON解析失败: {e}")
                        logger.debug(f"响应内容: {response.text[:500]}")
                        continue
                else:
                    logger.warning(f"URL {url} 返回状态码: {response.status_code}")

            except requests.RequestException as e:
                logger.warning(f"URL {url} 请求失败: {e}")
                continue
            except Exception as e:
                logger.warning(f"URL {url} 处理失败: {e}")
                continue

        logger.error(f"所有URL尝试失败，无法获取活跃台风数据")
        return None
    
    def parse_typhoon_path(self, raw_data: Dict) -> List[Dict]:
        """
        解析台风路径数据

        Args:
            raw_data: 原始数据

        Returns:
            解析后的路径点列表
        """
        path_points = []

        try:
            # 根据实际API返回的数据结构进行解析
            if not raw_data:
                logger.warning("原始数据为空")
                return path_points

            # 打印原始数据结构用于调试
            logger.info(f"原始数据类型: {type(raw_data)}")
            if isinstance(raw_data, dict):
                logger.info(f"原始数据键: {list(raw_data.keys())}")

            # 尝试多种可能的数据结构
            typhoons = []

            # 可能的台风列表字段名
            possible_list_keys = ['typhoonList', 'list', 'data', 'typhoons', 'items', 'records']
            for key in possible_list_keys:
                if key in raw_data and raw_data[key]:
                    typhoons = raw_data[key]
                    logger.info(f"找到台风列表，字段名: {key}, 数量: {len(typhoons)}")
                    break

            # 如果raw_data本身就是列表
            if not typhoons and isinstance(raw_data, list):
                typhoons = raw_data
                logger.info(f"原始数据本身是列表，数量: {len(typhoons)}")

            # 如果raw_data是单个台风对象
            if not typhoons and isinstance(raw_data, dict):
                # 检查是否包含路径点数据
                possible_point_keys = ['points', 'path', 'pathPoints', 'track', 'positions']
                for key in possible_point_keys:
                    if key in raw_data:
                        typhoons = [raw_data]  # 包装成列表
                        logger.info(f"原始数据是单个台风对象")
                        break

            if not typhoons:
                logger.warning("未找到台风数据")
                return path_points

            # 解析每个台风
            for typhoon in typhoons:
                if not isinstance(typhoon, dict):
                    logger.warning(f"台风数据格式错误: {type(typhoon)}")
                    continue

                # 获取台风ID
                typhoon_id = (
                    typhoon.get('tfid') or
                    typhoon.get('id') or
                    typhoon.get('typhoonId') or
                    typhoon.get('number') or
                    ''
                )

                if not typhoon_id:
                    logger.warning(f"台风ID为空，跳过该台风")
                    continue

                logger.info(f"解析台风: {typhoon_id}")

                # 获取路径点数据
                points = []
                possible_point_keys = ['points', 'path', 'pathPoints', 'track', 'positions', 'data']
                for key in possible_point_keys:
                    if key in typhoon and typhoon[key]:
                        points = typhoon[key]
                        logger.info(f"找到路径点，字段名: {key}, 数量: {len(points)}")
                        break

                if not points:
                    logger.warning(f"台风 {typhoon_id} 没有路径点数据")
                    continue

                # 解析每个路径点
                for idx, point in enumerate(points):
                    try:
                        if not isinstance(point, dict):
                            logger.warning(f"路径点 {idx} 格式错误: {type(point)}")
                            continue

                        # 解析时间
                        time_str = (
                            point.get('time') or
                            point.get('timestamp') or
                            point.get('datetime') or
                            point.get('forecastTime') or
                            ''
                        )

                        if time_str:
                            timestamp = self._parse_time(str(time_str))
                        else:
                            timestamp = datetime.now()

                        # 解析经纬度
                        lat = self._parse_float(
                            point.get('lat') or
                            point.get('latitude') or
                            point.get('LAT') or
                            0
                        )

                        lon = self._parse_float(
                            point.get('lon') or
                            point.get('lng') or
                            point.get('longitude') or
                            point.get('LON') or
                            0
                        )

                        # 跳过无效坐标
                        if lat == 0 and lon == 0:
                            logger.warning(f"路径点 {idx} 坐标无效，跳过")
                            continue

                        # 解析其他字段
                        # 气压（单位：hPa）
                        pressure = self._parse_float(
                            point.get('pressure') or
                            point.get('centerPressure') or
                            point.get('PRESSURE') or
                            None
                        )

                        # 最大风速（单位：m/s）- 浙江台风网的 speed 字段
                        wind_speed = self._parse_float(
                            point.get('speed') or  # 浙江台风网使用 speed 表示风速
                            point.get('windSpeed') or
                            point.get('maxWind') or
                            point.get('WIND') or
                            None
                        )

                        # 风力等级 - 浙江台风网的 power 字段
                        power_level = self._parse_int(point.get('power'))

                        # 移动速度（单位：km/h）
                        moving_speed = self._parse_float(
                            point.get('movespeed') or
                            point.get('moveSpeed') or
                            None
                        )

                        # 移动方向
                        moving_direction = (
                            point.get('movedirection') or
                            point.get('moveDir') or
                            point.get('direction') or
                            None
                        )

                        # 强度等级（如：热带低压、热带风暴等）
                        intensity = (
                            point.get('strong') or
                            point.get('intensity') or
                            point.get('STRONG') or
                            None
                        )

                        # 解析风圈半径（格式："东北|东南|西南|西北"）
                        radius7 = self._parse_radius(point.get('radius7'))
                        radius10 = self._parse_radius(point.get('radius10'))
                        radius12 = self._parse_radius(point.get('radius12'))

                        # 位置描述
                        position_desc = point.get('ckposition')
                        distance_info = point.get('jl')

                        path_point = {
                            'typhoon_id': str(typhoon_id),
                            'timestamp': timestamp,
                            'latitude': lat,
                            'longitude': lon,
                            'center_pressure': pressure,
                            'max_wind_speed': wind_speed,
                            'power_level': power_level,
                            'moving_speed': moving_speed,
                            'moving_direction': str(moving_direction) if moving_direction else None,
                            'intensity': str(intensity) if intensity else None,
                            # 风圈半径
                            'radius7_ne': radius7[0] if radius7 else None,
                            'radius7_se': radius7[1] if radius7 else None,
                            'radius7_sw': radius7[2] if radius7 else None,
                            'radius7_nw': radius7[3] if radius7 else None,
                            'radius10_ne': radius10[0] if radius10 else None,
                            'radius10_se': radius10[1] if radius10 else None,
                            'radius10_sw': radius10[2] if radius10 else None,
                            'radius10_nw': radius10[3] if radius10 else None,
                            'radius12_ne': radius12[0] if radius12 else None,
                            'radius12_se': radius12[1] if radius12 else None,
                            'radius12_sw': radius12[2] if radius12 else None,
                            'radius12_nw': radius12[3] if radius12 else None,
                            # 位置描述
                            'position_desc': str(position_desc) if position_desc else None,
                            'distance_info': str(distance_info) if distance_info else None,
                            'data_source': '浙江台风网',
                            # 预报数据（单独处理）
                            'forecast': point.get('forecast', [])
                        }

                        path_points.append(path_point)

                    except Exception as e:
                        logger.warning(f"解析路径点 {idx} 失败: {e}", exc_info=True)
                        continue

            logger.info(f"成功解析 {len(path_points)} 个路径点")

        except Exception as e:
            logger.error(f"解析台风路径数据失败: {e}", exc_info=True)

        return path_points

    def _parse_float(self, value) -> Optional[float]:
        """安全地解析浮点数"""
        if value is None or value == '' or value == ' ':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_int(self, value) -> Optional[int]:
        """安全地解析整数"""
        if value is None or value == '' or value == ' ':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _parse_radius(self, radius_str: str) -> Optional[list]:
        """
        解析风圈半径字符串
        格式："东北|东南|西南|西北" 或 "230|150|300|250"
        返回：[东北, 东南, 西南, 西北] 的浮点数列表
        """
        if not radius_str or radius_str == '':
            return None

        try:
            parts = radius_str.split('|')
            if len(parts) != 4:
                return None

            # 尝试转换为浮点数
            result = []
            for part in parts:
                if part == '' or part == ' ':
                    result.append(None)
                else:
                    try:
                        result.append(float(part))
                    except (ValueError, TypeError):
                        result.append(None)

            # 如果所有值都是None，返回None
            if all(v is None for v in result):
                return None

            return result
        except Exception:
            return None

    def _parse_time(self, time_str: str) -> datetime:
        """解析时间字符串"""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y%m%d%H%M%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y%m%d%H",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        
        # 如果都失败，返回当前时间
        logger.warning(f"无法解析时间字符串: {time_str}")
        return datetime.now()


# 创建全局实例
active_typhoon_crawler = ActiveTyphoonCrawler()

