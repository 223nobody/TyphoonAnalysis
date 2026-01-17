"""
CMA台风网爬虫服务 - 使用中国气象局真实API
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
import http.client
import json
import time

logger = logging.getLogger(__name__)


def clean_moving_direction(value):
    """
    清洗移动方向字段，将无效值转换为 None

    Args:
        value: 原始移动方向值

    Returns:
        清洗后的移动方向值，无效值返回 None
    """
    if not value:
        return None

    value = str(value).strip()

    # 将无效值转换为 None
    if value.lower() in ['0', 'no', '']:
        return None

    return value


class CMACrawler:
    """中国气象局台风网爬虫"""

    def __init__(self):
        self.base_url = "typhoon.nmc.cn"
        self.headers = {
            "Accept": "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01",
            "Referer": "https://typhoon.nmc.cn/web.html",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # 强度代码映射
        self.type_map = {
            'TD': '热带低压', 'TS': '热带风暴', 'STS': '强热带风暴',
            'TY': '台风', 'STY': '强台风', 'SuperTY': '超强台风',
            'LPA': '低气压', 'INVEST': '热带扰动'
        }
        
        # 方向代码映射
        self.dir_map = {
            'N': '北', 'S': '南', 'E': '东', 'W': '西',
            'NE': '东北', 'NW': '西北', 'SE': '东南', 'SW': '西南',
            'NNE': '东北偏北', 'ENE': '东北偏东', 'NNW': '西北偏北', 'WNW': '西北偏西',
            'SSE': '东南偏南', 'ESE': '东南偏东', 'SSW': '西南偏南', 'WSW': '西南偏西'
        }

    async def get_active_typhoons(self) -> List[Dict]:
        """
        获取当前活跃的台风列表（使用list_default接口）

        Returns:
            List[Dict]: 台风列表
        """
        try:
            logger.info("开始获取活跃台风列表（使用default接口）")

            # 使用default接口获取当前活跃台风
            typhoons = await self._get_default_typhoons()

            if not typhoons:
                logger.warning("没有活跃台风")
                return []

            logger.info(f"成功获取 {len(typhoons)} 个活跃台风")
            return typhoons

        except Exception as e:
            logger.error(f"获取活跃台风列表失败: {e}")
            return []

    async def get_typhoon_bulletin(self) -> Optional[Dict]:
        """
        获取台风公报数据

        Returns:
            Optional[Dict]: 台风公报数据，包含发布时间、描述、详细列表等
        """
        conn = None
        try:
            logger.info("开始获取台风公报")

            # 使用 www.nmc.cn 域名
            conn = http.client.HTTPSConnection("www.nmc.cn", port=443, timeout=30)

            t = int(time.time() * 1000)
            url = f"/dataservice/typhoon/news.json?v={t}"

            headers = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": "https://typhoon.nmc.cn/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
                "X-Requested-With": "XMLHttpRequest"
            }

            conn.request('GET', url, headers=headers)
            res = conn.getresponse()
            content = res.read().decode('utf-8')

            # 解析JSON
            data = json.loads(content)

            if data.get('code') == 0 and data.get('data'):
                bulletin_data = data['data']
                logger.info(f"成功获取台风公报，发布时间: {bulletin_data.get('releaseTime')}")
                return bulletin_data
            else:
                logger.warning(f"台风公报数据格式异常: {data}")
                return None

        except Exception as e:
            logger.error(f"获取台风公报失败: {e}")
            return None
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass


    async def _get_default_typhoons(self) -> List[Dict]:
        """
        获取默认接口的台风列表（list_default）

        Returns:
            List[Dict]: 台风列表
        """
        conn = http.client.HTTPSConnection(self.base_url, port=443)

        try:
            t = int(time.time() * 1000)  # 毫秒级时间戳
            url = f"/weatherservice/typhoon/jsons/list_default?t={t}&callback=typhoon_jsons_list_default"

            logger.info(f"请求URL: https://{self.base_url}{url}")

            conn.request('GET', url, headers=self.headers)
            res = conn.getresponse()
            content = res.read().decode('utf-8')

            # 处理default接口的callback格式
            callback_prefix = 'typhoon_jsons_list_default('
            if content.startswith(callback_prefix) and content.endswith('))'):
                # 处理双重括号的特殊情况
                json_str = content[len(callback_prefix)+1:-2]
            else:
                # 常规情况：切割掉callback包裹
                json_str = content.split('(', 1)[1].rsplit(')', 1)[0]

            obj = json.loads(json_str, strict=False)

            typhoons = []
            if 'typhoonList' in obj:
                for ty_temp in obj['typhoonList']:
                    try:
                        temp_id = ty_temp[0]
                        temp_name_en = ty_temp[1] or 'nameless'
                        temp_name_ch = ty_temp[2]
                        temp_code = ty_temp[4]  # 台风编号，直接使用API返回的值
                        temp_status = ty_temp[7] if len(ty_temp) > 7 else 'stop'  # 获取状态字段

                        # 跳过无名台风
                        if temp_name_en == 'nameless':
                            continue

                        # 从台风编号推断年份
                        # 如果编号是4位数字（如2601），年份从前2位推断（26 -> 2026）
                        # 如果编号是6位数字（如202601），年份从前4位提取
                        temp_code_str = str(temp_code)
                        if len(temp_code_str) == 4:
                            # 4位编号：前2位是年份后2位
                            year_suffix = int(temp_code_str[:2])
                            year = 2000 + year_suffix  # 2601 -> 2026
                        elif len(temp_code_str) >= 6:
                            # 6位编号：前4位是完整年份
                            year = int(temp_code_str[:4])
                        else:
                            # 其他情况使用当前年份
                            year = datetime.now().year

                        # 获取该台风的详细信息（包括最新路径点）
                        detail = await self._get_typhoon_detail(temp_id, temp_code, temp_name_en, temp_name_ch, year, temp_status)

                        if detail:
                            typhoons.append(detail)

                        # 避免请求过快
                        time.sleep(0.3)

                    except (IndexError, TypeError, ValueError) as e:
                        logger.warning(f"跳过异常台风数据：{ty_temp}，错误：{e}")
                        continue

            return typhoons

        except Exception as e:
            logger.error(f"获取default台风列表失败：{e}")
            return []
        finally:
            conn.close()

    async def _get_typhoon_detail(self, ty_id: int, ty_code: str, ty_name_en: str, ty_name_ch: str, year: int, status_str: str) -> Optional[Dict]:
        """
        获取台风详细信息

        Args:
            ty_id: 台风ID
            ty_code: 台风编号
            ty_name_en: 台风英文名
            ty_name_ch: 台风中文名
            year: 年份
            status_str: 状态字符串（"stop" 或其他值）

        Returns:
            Optional[Dict]: 台风详细信息
        """
        conn = http.client.HTTPSConnection(self.base_url, port=443)

        try:
            t = int(time.time() * 1000)
            url = f"/weatherservice/typhoon/jsons/view_{ty_id}?t={t}&callback=typhoon_jsons_view_{ty_id}"

            conn.request('GET', url, headers=self.headers)
            res = conn.getresponse()
            content = res.read().decode('utf-8')

            # 处理callback格式
            callback_prefix = f'typhoon_jsons_view_{ty_id}('
            if content.startswith(callback_prefix) and content.endswith('))'):
                json_str = content[len(callback_prefix)+1:-2]
            else:
                json_str = content.split('(', 1)[1].rsplit(')', 1)[0]

            ty_path_obj = json.loads(json_str, strict=False)

            if 'typhoon' not in ty_path_obj:
                return None

            ty_group_detail = ty_path_obj['typhoon']
            ty_group_list = ty_group_detail[8]  # 路径点列表

            if not ty_group_list:
                return None

            # 根据状态字符串设置状态值：stop=0, 其他=1
            status = 0 if status_str == "stop" else 1

            # 返回台风基本信息（只保留必要字段）
            return {
                "typhoon_id": ty_code,
                "typhoon_name": ty_name_en,
                "typhoon_name_cn": ty_name_ch,
                "year": year,
                "status": status
            }

        except Exception as e:
            logger.error(f"获取台风{ty_code}详细信息失败：{e}")
            return None
        finally:
            conn.close()

    async def get_typhoon_path(self, typhoon_id: str) -> List[Dict]:
        """
        获取指定台风的路径数据

        Args:
            typhoon_id: 台风编号

        Returns:
            List[Dict]: 路径数据列表
        """
        try:
            logger.info(f"开始获取台风 {typhoon_id} 的路径数据")

            # typhoon_id格式：202501（年份+序号）
            # 我们需要调用API获取路径数据
            paths = await self._get_typhoon_path_by_code(typhoon_id)

            if not paths:
                logger.warning(f"台风 {typhoon_id} 没有路径数据")
                return []

            logger.info(f"成功获取台风 {typhoon_id} 的 {len(paths)} 个路径点")

            # 添加调试日志：显示第一个路径点的数据结构
            if paths:
                logger.debug(f"第一个路径点数据示例: {paths[0]}")

            return paths

        except Exception as e:
            logger.error(f"获取台风路径失败 {typhoon_id}: {e}", exc_info=True)
            return []

    async def _get_typhoon_path_by_code(self, typhoon_code: str) -> List[Dict]:
        """
        通过台风编号获取路径数据

        Args:
            typhoon_code: 台风编号（如202501）

        Returns:
            List[Dict]: 路径数据列表
        """
        # 从台风编号提取年份
        try:
            typhoon_code_str = str(typhoon_code)
            if len(typhoon_code_str) == 4:
                year_suffix = int(typhoon_code_str[:2])
                year = 2000 + year_suffix
            elif len(typhoon_code_str) >= 6:
                year = int(typhoon_code_str[:4])
            else:
                year = datetime.now().year
        except Exception as e:
            year = datetime.now().year
            logger.warning(f"无法从编号提取年份，使用当前年份: {year}, 错误: {e}")

        conn = None
        try:
            # 获取该年份的台风列表，找到对应的ID
            conn = http.client.HTTPSConnection(self.base_url, port=443, timeout=30)

            t = int(time.time() * 1000)
            url = f"/weatherservice/typhoon/jsons/list_{year}?t={t}&callback=typhoon_jsons_list_{year}"

            conn.request('GET', url, headers=self.headers)
            res = conn.getresponse()
            content = res.read().decode('utf-8')

            # 解析JSON
            json_str = content.split('(', 1)[1].rsplit(')', 1)[0]
            obj = json.loads(json_str, strict=False)

            # 查找对应的台风ID
            ty_id = None
            if 'typhoonList' in obj:
                for ty_temp in obj['typhoonList']:
                    if str(ty_temp[4]) == str(typhoon_code):
                        ty_id = ty_temp[0]
                        break
            else:
                logger.error(f"API响应中没有 'typhoonList' 字段")

            if not ty_id:
                logger.warning(f"未找到台风编号 {typhoon_code} 对应的ID")
                return []

            # 关闭第一个连接
            conn.close()
            conn = None

            # 获取路径数据
            conn = http.client.HTTPSConnection(self.base_url, port=443, timeout=30)

            t = int(time.time() * 1000)
            url = f"/weatherservice/typhoon/jsons/view_{ty_id}?t={t}&callback=typhoon_jsons_view_{ty_id}"

            conn.request('GET', url, headers=self.headers)
            res = conn.getresponse()
            content = res.read().decode('utf-8')

            # 解析callback格式
            callback_prefix = f'typhoon_jsons_view_{ty_id}('
            if content.startswith(callback_prefix) and content.endswith('))'):
                json_str = content[len(callback_prefix)+1:-2]
            else:
                json_str = content.split('(', 1)[1].rsplit(')', 1)[0]

            ty_path_obj = json.loads(json_str, strict=False)

            if 'typhoon' not in ty_path_obj:
                logger.error(f"API响应中没有 'typhoon' 字段")
                return []

            ty_group_detail = ty_path_obj['typhoon']
            ty_group_list = ty_group_detail[8]  # 路径点列表

            # 解析路径点数据
            paths = []
            for idx, temp_ty_group in enumerate(ty_group_list):
                try:
                    lat = temp_ty_group[5]  # 纬度
                    lon = temp_ty_group[4]  # 经度
                    bp = temp_ty_group[6]   # 中心气压
                    ts = temp_ty_group[2]   # 时间戳
                    ty_type = temp_ty_group[3]  # 强度类型
                    max_wind = temp_ty_group[7] if len(temp_ty_group) > 7 else None  # 最大风速
                    direction = temp_ty_group[8] if len(temp_ty_group) > 8 else None  # 移动方向
                    speed = temp_ty_group[9] if len(temp_ty_group) > 9 else None  # 移动速度

                    # 清洗移动方向字段
                    moving_direction = self.dir_map.get(direction, direction) if direction else None
                    moving_direction = clean_moving_direction(moving_direction)

                    # 转换时间戳
                    timestamp = datetime.fromtimestamp(ts / 1000)

                    path_data = {
                        "typhoon_id": typhoon_code,
                        "timestamp": timestamp,
                        "latitude": lat,
                        "longitude": lon,
                        "center_pressure": bp,
                        "max_wind_speed": max_wind,
                        "intensity": self.type_map.get(ty_type, ty_type),
                        "moving_direction": moving_direction,
                        "moving_speed": speed
                    }
                    paths.append(path_data)

                except (IndexError, TypeError, ValueError) as e:
                    logger.warning(f"解析路径点失败 (索引 {idx}): {e}")
                    continue

            logger.info(f"成功获取台风 {typhoon_code} 的 {len(paths)} 个路径点")

            return paths

        except Exception as e:
            logger.error(f"[路径爬取] ❌ 获取台风 {typhoon_code} 路径数据失败: {e}", exc_info=True)
            return []
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass


# 创建全局爬虫实例
cma_crawler = CMACrawler()