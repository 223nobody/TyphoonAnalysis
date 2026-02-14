"""
台风历史数据爬虫 - 从浙江台风网获取历史台风数据并保存到CSV
优化版本：增加多机构预报数据和登陆信息提取
"""
import requests
import csv
import os
import json
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import time
import numpy as np


class TyphoonDataCrawler:
    """台风历史数据爬虫（优化版）"""

    def __init__(self):
        self.base_url = "https://typhoon.slt.zj.gov.cn"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://typhoon.slt.zj.gov.cn/',
            'X-Requested-With': 'XMLHttpRequest'
        }

    def fetch_year_typhoons(self, year: int) -> List[Dict]:
        """获取指定年份的台风列表"""
        url = f"{self.base_url}/Api/TyphoonList/{year}"

        try:
            print(f"正在获取{year}年台风列表: {url}")
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"请求{year}年台风列表失败: {e}")
            return []
        except Exception as e:
            print(f"处理{year}年台风列表失败: {e}")
            return []

        typhoon_list = []
        if isinstance(data, list):
            for ty_item in data:
                try:
                    tfid = ty_item.get('tfid', '')
                    name = ty_item.get('name', '')
                    enname = ty_item.get('enname', '')

                    # 跳过无名台风
                    if not enname or enname.lower() == 'nameless':
                        continue

                    # 过滤typhoon_name等于'-'的台风
                    if str(enname) == '-':
                        print(f"  跳过名称为'-'的台风")
                        continue

                    # 从tfid中提取编号
                    try:
                        ty_number = int(tfid[4:]) if len(tfid) >= 5 else 0
                    except ValueError:
                        ty_number = 0

                    typhoon_list.append({
                        'ty_code': tfid,
                        'ty_number': ty_number,
                        'year': year,
                        'ty_name_en': enname,
                        'ty_name_ch': name
                    })
                except Exception as e:
                    print(f"跳过异常台风数据: {ty_item}, 错误: {e}")
                    continue

        print(f"成功获取{year}年{len(typhoon_list)}个台风")
        return typhoon_list

    def fetch_typhoon_path(self, ty_code: str, ty_name_en: str, ty_name_ch: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        获取指定台风的路径数据、登陆信息和多机构预报
        
        Returns:
            (path_points, land_info, forecast_data)
        """
        url = f"{self.base_url}/Api/TyphoonInfo/{ty_code}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"正在获取台风路径: {url}")
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                break
            except requests.RequestException as e:
                print(f"请求路径失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return [], [], []
            except Exception as e:
                print(f"处理路径数据失败: {e}")
                return [], [], []

        # 提取路径点数据
        path_points = []
        points = data.get('points', [])
        
        for point in points:
            try:
                # 解析经纬度
                lat = self._parse_float(point.get('lat'))
                lng = self._parse_float(point.get('lng'))

                # 跳过无效坐标
                if lat is None or lng is None:
                    continue

                # 解析气压
                pressure = self._parse_float(point.get('pressure'))

                # 解析时间
                time_str = point.get('time', '')
                timestamp = self._parse_datetime(time_str)
                if timestamp is None:
                    continue

                # 获取其他字段
                ty_type = point.get('strong', '')
                direction = point.get('movedirection', '')
                move_speed = self._parse_float(point.get('movespeed'))
                max_wind_speed = self._parse_float(point.get('speed'))
                power = self._parse_int(point.get('power'))
                
                # 提取风圈半径（如果存在）
                radius7 = self._parse_float(point.get('radius7'))
                radius10 = self._parse_float(point.get('radius10'))
                radius12 = self._parse_float(point.get('radius12'))

                path_points.append({
                    'ty_code': ty_code,
                    'ty_name_en': ty_name_en,
                    'ty_name_ch': ty_name_ch,
                    'timestamp': timestamp,
                    'latitude': lat,
                    'longitude': lng,
                    'center_pressure': pressure,
                    'max_wind_speed': max_wind_speed,
                    'moving_speed': move_speed,
                    'moving_direction': direction if direction else None,
                    'intensity': ty_type,
                    'power': power,
                    'radius7': radius7,
                    'radius10': radius10,
                    'radius12': radius12
                })
            except Exception as e:
                print(f"解析路径点失败: {e}, 数据: {point}")
                continue

        # 提取登陆信息
        land_info = []
        land_data = data.get('land', [])
        for land in land_data:
            try:
                land_record = {
                    'ty_code': ty_code,
                    'ty_name_en': ty_name_en,
                    'ty_name_ch': ty_name_ch,
                    'land_address': land.get('landaddress', ''),
                    'land_time': land.get('landtime', ''),
                    'land_lng': self._parse_float(land.get('lng')),
                    'land_lat': self._parse_float(land.get('lat')),
                    'land_info': land.get('info', ''),
                    'land_strong': land.get('strong', '')
                }
                land_info.append(land_record)
            except Exception as e:
                print(f"解析登陆信息失败: {e}")
                continue

        # 提取多机构预报数据
        forecast_data = []
        for point in points:
            try:
                timestamp = point.get('time', '')
                forecasts = point.get('forecast', [])
                
                for forecast in forecasts:
                    agency = forecast.get('tm', '')
                    forecast_points = forecast.get('forecastpoints', [])
                    
                    for fp in forecast_points:
                        forecast_record = {
                            'ty_code': ty_code,
                            'ty_name_en': ty_name_en,
                            'ty_name_ch': ty_name_ch,
                            'observation_time': timestamp,
                            'agency': agency,
                            'forecast_time': fp.get('time', ''),
                            'forecast_lat': self._parse_float(fp.get('lat')),
                            'forecast_lng': self._parse_float(fp.get('lng')),
                            'forecast_strong': fp.get('strong', ''),
                            'forecast_power': self._parse_int(fp.get('power')),
                            'forecast_speed': self._parse_float(fp.get('speed')),
                            'forecast_pressure': self._parse_float(fp.get('pressure')),
                            'forecast_publish_time': fp.get('ybsj', '')
                        }
                        forecast_data.append(forecast_record)
            except Exception as e:
                print(f"解析预报数据失败: {e}")
                continue

        print(f"成功解析台风{ty_code}: {len(path_points)}个路径点, {len(land_info)}个登陆点, {len(forecast_data)}个预报点")
        return path_points, land_info, forecast_data

    def _parse_float(self, value) -> Optional[float]:
        """安全地解析浮点数"""
        if value is None or value == '' or value == ' ' or value == '999999':
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
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def _parse_datetime(self, time_str: str) -> Optional[str]:
        """解析时间字符串为标准格式"""
        if not time_str:
            return None

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y%m%d%H%M%S",
            "%Y-%m-%dT%H:%M:%S",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(time_str, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

        print(f"无法解析时间字符串: {time_str}")
        return None


def save_to_csv(all_path_data: List[Dict], output_file: str):
    """将台风路径数据保存到CSV文件"""
    if not all_path_data:
        print("没有数据需要保存")
        return

    # 定义CSV字段顺序（扩展版本）
    fieldnames = [
        'ty_code',
        'ty_name_en',
        'ty_name_ch',
        'timestamp',
        'latitude',
        'longitude',
        'center_pressure',
        'max_wind_speed',
        'moving_speed',
        'moving_direction',
        'intensity',
        'power',
        'radius7',
        'radius10',
        'radius12'
    ]

    # 写入CSV文件
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_path_data)

    print(f"\n✓ 路径数据已保存到: {output_file}")
    print(f"  总计: {len(all_path_data)} 条路径记录")


def save_land_to_csv(land_data: List[Dict], output_file: str):
    """将登陆信息保存到CSV文件"""
    if not land_data:
        print("没有登陆数据需要保存")
        return

    fieldnames = [
        'ty_code',
        'ty_name_en',
        'ty_name_ch',
        'land_address',
        'land_time',
        'land_lng',
        'land_lat',
        'land_info',
        'land_strong'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(land_data)

    print(f"✓ 登陆数据已保存到: {output_file}")
    print(f"  总计: {len(land_data)} 条登陆记录")


def save_forecast_to_csv(forecast_data: List[Dict], output_file: str):
    """将多机构预报数据保存到CSV文件"""
    if not forecast_data:
        print("没有预报数据需要保存")
        return

    fieldnames = [
        'ty_code',
        'ty_name_en',
        'ty_name_ch',
        'observation_time',
        'agency',
        'forecast_time',
        'forecast_lat',
        'forecast_lng',
        'forecast_strong',
        'forecast_power',
        'forecast_speed',
        'forecast_pressure',
        'forecast_publish_time'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(forecast_data)

    print(f"✓ 预报数据已保存到: {output_file}")
    print(f"  总计: {len(forecast_data)} 条预报记录")


def main():
    """主函数 - 爬取并保存台风数据到CSV"""
    # 设置爬取时间范围为1966-2026年
    START_YEAR = 1966
    END_YEAR = 2026
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    PATH_OUTPUT_FILE = os.path.join(current_dir, "typhoon_paths_1966_2026.csv")
    LAND_OUTPUT_FILE = os.path.join(current_dir, "typhoon_land_1966_2026.csv")
    FORECAST_OUTPUT_FILE = os.path.join(current_dir, "typhoon_forecast_1966_2026.csv")

    print(f"开始获取{START_YEAR}-{END_YEAR}年的台风数据...")
    print(f"路径数据将保存到: {PATH_OUTPUT_FILE}")
    print(f"登陆数据将保存到: {LAND_OUTPUT_FILE}")
    print(f"预报数据将保存到: {FORECAST_OUTPUT_FILE}\n")

    crawler = TyphoonDataCrawler()
    all_path_data = []
    all_land_data = []
    all_forecast_data = []
    total_typhoons = 0

    # 按年份爬取
    for year in range(START_YEAR, END_YEAR + 1):
        print(f"\n{'='*60}")
        print(f"处理 {year} 年")
        print(f"{'='*60}")

        # 获取该年份的台风列表
        typhoons = crawler.fetch_year_typhoons(year)
        if not typhoons:
            print(f"{year}年无台风数据")
            continue

        # 获取每个台风的数据
        year_path_count = 0
        year_land_count = 0
        year_forecast_count = 0
        
        for idx, ty in enumerate(typhoons, 1):
            print(f"\n[{idx}/{len(typhoons)}] {ty['ty_name_ch']} ({ty['ty_name_en']}) - {ty['ty_code']}")

            path_data, land_data, forecast_data = crawler.fetch_typhoon_path(
                ty['ty_code'],
                ty['ty_name_en'],
                ty['ty_name_ch']
            )

            if path_data:
                all_path_data.extend(path_data)
                year_path_count += len(path_data)
                
            if land_data:
                all_land_data.extend(land_data)
                year_land_count += len(land_data)
                
            if forecast_data:
                all_forecast_data.extend(forecast_data)
                year_forecast_count += len(forecast_data)
                
            if path_data or land_data or forecast_data:
                total_typhoons += 1
                print(f"  ✓ 获取 {len(path_data)} 个路径点, {len(land_data)} 个登陆点, {len(forecast_data)} 个预报点")
            else:
                print(f"  ✗ 无数据")

            # 添加延迟避免请求过快
            time.sleep(0.3)

        print(f"\n{year}年处理完成: {len(typhoons)}个台风, {year_path_count}个路径点, {year_land_count}个登陆点, {year_forecast_count}个预报点")

    # 保存最终数据
    print(f"\n{'='*60}")
    print("爬取完成，保存最终数据...")
    print(f"{'='*60}")
    
    save_to_csv(all_path_data, PATH_OUTPUT_FILE)
    save_land_to_csv(all_land_data, LAND_OUTPUT_FILE)
    save_forecast_to_csv(all_forecast_data, FORECAST_OUTPUT_FILE)

    print(f"\n{'='*60}")
    print(f"数据导入完成！")
    print(f"总计台风: {total_typhoons} 个")
    print(f"总计路径点: {len(all_path_data)} 个")
    print(f"总计登陆点: {len(all_land_data)} 个")
    print(f"总计预报点: {len(all_forecast_data)} 个")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
