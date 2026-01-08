import requests
import json
from urllib import request
import http.client
import datetime
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.typhoon import Base, Typhoon, TyphoonPath


class TyDetailMidModel:
    def __init__(self, ty_code: str, id: int, year: int, ty_name_en: str = None, ty_name_ch: str = None):
        self.ty_code = ty_code
        self.id = id
        self.year = year  # 新增年份属性
        self.ty_name_en = ty_name_en
        self.ty_name_ch = ty_name_ch

    def __str__(self) -> str:
        return f'TyDetailMidModel:id:{self.id}|ty_code:{self.ty_code}|name_en:{self.ty_name_en}|name_ch：{self.ty_name_ch}|year:{self.year}'


class TyPathMidModel:
    def __init__(self, ty_id: int, ty_code: str, ty_name_en: str, ty_name_ch: str, ty_path_list: [] = None):
        self.ty_id = ty_id
        self.ty_code = ty_code
        self.ty_name_en = ty_name_en
        self.ty_name_ch = ty_name_ch
        self.ty_path_list = ty_path_list if ty_path_list is not None else []

    def __str__(self) -> str:
        return f'TyPathMidModel: id={self.ty_id}, code={self.ty_code}, name={self.ty_name_ch}({self.ty_name_en}), path_count={len(self.ty_path_list)}'


class TyForecastRealDataMidModel:
    def __init__(self, lat: float, lon: float, bp: float, ts: int, ty_type: str, 
                 direction: str = None, speed: float = None, max_wind_speed: float = None,  # 新增最大风速字段
                 forecast_ty_path_list: [] = None):
        self.lat = lat
        self.lon = lon
        self.bp = bp
        self.ts = ts
        self.ty_type = ty_type
        self.direction = direction  # 移动方向
        self.speed = speed  # 移动速度（公里/小时）
        self.max_wind_speed = max_wind_speed  # 最大风速（新增）

    @property
    def forecast_dt(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.ts / 1000)
    
    _dir_map = {
        'N': '北', 'S': '南', 'E': '东', 'W': '西',
        'NE': '东北', 'NW': '西北', 'SE': '东南', 'SW': '西南',
        'NNE': '东北偏北', 'ENE': '东北偏东', 'NNW': '西北偏北', 'WNW': '西北偏西',
        'SSE': '东南偏南', 'ESE': '东南偏东', 'SSW': '西南偏南', 'WSW': '西南偏西'
    }
    
    _type_map = {
        'TD': '热带低压', 'TS': '热带风暴', 'STS': '强热带风暴',
        'TY': '台风', 'STY': '强台风', 'SuperTY': '超强台风',
        'LPA': '低气压', 'INVEST': '热带扰动'
    }

    def __str__(self) -> str:
        dir_cn = self._dir_map.get(self.direction, self.direction) if self.direction else '未知'
        type_cn = self._type_map.get(self.ty_type, self.ty_type)
        speed_str = f' | 移动方向：{dir_cn} | 移动速度：{self.speed}公里/小时' if self.speed else ''
        wind_str = f' | 最大风速：{self.max_wind_speed}节' if self.max_wind_speed else ''  # 新增风速显示
        
        return (f'位置：{self.lat}°N, {self.lon}°E | 气压：{self.bp}hPa | 时间：{self.forecast_dt.strftime("%Y-%m-%d %H:%M")} | '
                f'类型：{type_cn}{speed_str}{wind_str}')  # 添加风速信息


def spider_get_year_typhoons(year: int) -> list[TyDetailMidModel]:
    """获取指定年份的台风列表"""
    baseUrl = 'typhoon.nmc.cn'
    conn = http.client.HTTPConnection(baseUrl)
    
    import time
    t = int(time.time() * 1000)  # 毫秒级时间戳
    
    url = f"/weatherservice/typhoon/jsons/list_{year}?t={t}&callback=typhoon_jsons_list_{year}"
    
    headers = {
        "Accept": "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01",
        "Referer": "https://typhoon.nmc.cn/web.html",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        conn.request('GET', url, headers=headers)
        res = conn.getresponse()
        content = res.read().decode('utf-8')
    except Exception as e:
        print(f"请求{year}年台风列表失败：{e}")
        return []
    
    try:
        json_str = content.split('(', 1)[1].rsplit(')', 1)[0]
        obj = json.loads(json_str, strict=False)
    except (json.JSONDecodeError, IndexError) as e:
        print(f"解析{year}年台风列表失败：{e}")
        return []
    
    typhoon_list = []
    if 'typhoonList' in obj:
        for ty_temp in obj['typhoonList']:
            try:
                temp_id = ty_temp[0]
                temp_code = ty_temp[4]
                temp_name_ch = ty_temp[2]
                temp_name_en = ty_temp[1] or 'nameless'
                if temp_name_en == 'nameless' :
                    continue
                
                typhoon_list.append(
                    TyDetailMidModel(
                        ty_code=temp_code,
                        id=temp_id,
                        year=year,
                        ty_name_en=temp_name_en,
                        ty_name_ch=temp_name_ch
                    )
                )
            except (IndexError, TypeError) as e:
                print(f"跳过异常台风数据：{ty_temp}，错误：{e}")
                continue
    return typhoon_list


def spider_get_all_typhoons(start_year: int, end_year: int) -> list[TyDetailMidModel]:
    """获取指定年份范围的所有台风列表"""
    all_typhoons = []
    for year in range(start_year, end_year + 1):
        year_typhoons = spider_get_year_typhoons(year)
        all_typhoons.extend(year_typhoons)
        import time
        time.sleep(1)
    return all_typhoons


def spider_get_ty_path(ty_id: int, ty_code: str, ty_name_en: str ) -> TyPathMidModel:
    """获取指定台风的路径数据"""
    baseUrl: str = 'typhoon.nmc.cn'
    conn = http.client.HTTPConnection(baseUrl)
    try:
        conn.request('GET', f"/weatherservice/typhoon/jsons/view_{str(ty_id)}")
        res = conn.getresponse()
        content = res.read().decode('utf-8')
    except Exception as e:
        print(f"请求路径失败：{e}")
        return TyPathMidModel(ty_id, ty_code, ty_name_en, "未知")

    try:
        index: int = len(f'typhoon_jsons_view_{str(ty_id)}') + 1
        new_json = content[index:-1]
        ty_path_obj = json.loads(new_json, strict=False)
    except (json.JSONDecodeError, IndexError) as e:
        print(f"解析路径数据失败：{e}")
        return TyPathMidModel(ty_id, ty_code, ty_name_en, "未知")

    ty_realdata_list = []
    ty_name_ch = "未知"
    if 'typhoon' in ty_path_obj:
        try:
            ty_group_detail = ty_path_obj['typhoon']
            ty_name_ch = ty_group_detail[2]  # 中文名
            ty_group_list = ty_group_detail[8]  # 路径点列表

            for temp_ty_group in ty_group_list:
                try:
                    lat = temp_ty_group[5]
                    lon = temp_ty_group[4]
                    bp = temp_ty_group[6]
                    ts = temp_ty_group[2]
                    ty_type = temp_ty_group[3]
                    direction = temp_ty_group[8] if len(temp_ty_group) > 8 else None
                    speed = temp_ty_group[9] if len(temp_ty_group) > 9 else None
                    max_wind_speed = temp_ty_group[7] if len(temp_ty_group) > 7 else None  # 获取最大风速（索引7）
                    
                    ty_realdata_list.append(
                        TyForecastRealDataMidModel(
                            lat=lat, 
                            lon=lon, 
                            bp=bp, 
                            ts=ts, 
                            ty_type=ty_type,
                            direction=direction,
                            speed=speed,
                            max_wind_speed=max_wind_speed  # 传递最大风速
                        )
                    )
                except (IndexError, TypeError) as e:
                    print(f"解析实时路径点失败：{e}，数据：{temp_ty_group}")
                    continue
        except (IndexError, TypeError) as e:
            print(f"解析台风详情失败：{e}")

    return TyPathMidModel(ty_id, ty_code, ty_name_en, ty_name_ch, ty_realdata_list)


def main():
    # 创建数据库连接
    DATABASE_URL = "sqlite:///./typhoon_analysis.db"
    engine = create_engine(DATABASE_URL, echo=False)

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 创建会话
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    print("开始获取2000-2025年的台风数据...")

    # 获取2005到2025年的所有台风数据
    all_typhoons = spider_get_all_typhoons(2000, 2025)
    if not all_typhoons:
        print("未获取到任何台风数据")
        session.close()
        return

    # 按年份分组
    typhoons_by_year = {}
    for ty in all_typhoons:
        if ty.year not in typhoons_by_year:
            typhoons_by_year[ty.year] = []
        typhoons_by_year[ty.year].append(ty)

    total_typhoons = 0
    total_paths = 0

    # 按年份顺序处理
    for year in sorted(typhoons_by_year.keys()):
        year_typhoons = typhoons_by_year[year]
        print(f"\n===== 处理 {year} 年（共{len(year_typhoons)}个台风） =====")

        for idx, ty_obj in enumerate(year_typhoons, 1):
            print(f"  [{idx}/{len(year_typhoons)}] {ty_obj.ty_name_ch}（{ty_obj.ty_name_en}） 编号：{ty_obj.ty_code}")

            try:
                # 检查台风是否已存在
                existing_typhoon = session.query(Typhoon).filter(
                    Typhoon.typhoon_id == ty_obj.ty_code
                ).first()

                if existing_typhoon:
                    print(f"    台风已存在，跳过")
                    continue

                # 获取路径数据
                ty_group = spider_get_ty_path(ty_obj.id, ty_obj.ty_code, ty_obj.ty_name_en)

                if not ty_group.ty_path_list:
                    print("    无路径数据，跳过")
                    continue

                # 创建台风记录
                typhoon = Typhoon(
                    typhoon_id=ty_obj.ty_code,
                    typhoon_name=ty_obj.ty_name_en,
                    typhoon_name_cn=ty_group.ty_name_ch,
                    year=ty_obj.year,
                    status=0  # 历史台风都是stop状态
                )

                session.add(typhoon)
                session.flush()  # 获取台风ID

                # 添加路径点
                path_count = 0
                for path_point in ty_group.ty_path_list:
                    # 清洗移动方向字段
                    moving_direction = _get_direction_cn(path_point.direction) if path_point.direction else None
                    moving_direction = clean_moving_direction(moving_direction)

                    typhoon_path = TyphoonPath(
                        typhoon_id=ty_obj.ty_code,
                        timestamp=path_point.forecast_dt,
                        latitude=path_point.lat,
                        longitude=path_point.lon,
                        center_pressure=path_point.bp,
                        max_wind_speed=path_point.max_wind_speed,  # 保存最大风速
                        intensity=_get_intensity_cn(path_point.ty_type),
                        moving_direction=moving_direction,
                        moving_speed=path_point.speed if path_point.speed else None
                    )
                    session.add(typhoon_path)
                    path_count += 1

                session.commit()
                total_typhoons += 1
                total_paths += path_count

                print(f"    ✅ 成功保存，路径点数：{path_count}")

            except Exception as e:
                session.rollback()
                print(f"    ❌ 处理失败：{e}")
                continue

    session.close()
    print(f"\n{'='*50}")
    print(f"数据导入完成！")
    print(f"总计导入台风：{total_typhoons} 个")
    print(f"总计导入路径点：{total_paths} 个")
    print(f"{'='*50}")


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


def _get_intensity_cn(ty_type: str) -> str:
    """将强度代码转换为中文"""
    type_map = {
        'TD': '热带低压', 'TS': '热带风暴', 'STS': '强热带风暴',
        'TY': '台风', 'STY': '强台风', 'SuperTY': '超强台风',
        'LPA': '低气压', 'INVEST': '热带扰动'
    }
    return type_map.get(ty_type, ty_type)


def _get_direction_cn(direction: str) -> str:
    """将方向代码转换为中文"""
    dir_map = {
        'N': '北', 'S': '南', 'E': '东', 'W': '西',
        'NE': '东北', 'NW': '西北', 'SE': '东南', 'SW': '西南',
        'NNE': '东北偏北', 'ENE': '东北偏东', 'NNW': '西北偏北', 'WNW': '西北偏西',
        'SSE': '东南偏南', 'ESE': '东南偏东', 'SSW': '西南偏南', 'WSW': '西南偏西'
    }
    return dir_map.get(direction, direction) if direction else None


if __name__ == '__main__':
    main()