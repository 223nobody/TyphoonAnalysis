"""
全量数据导入脚本 V2
从CSV文件导入台风数据到Neo4j知识图谱
包含所有新字段的计算逻辑

数据源:
1. typhoon_paths_1966_2026.csv - 台风路径数据（主数据源）
2. typhoon_land_1966_2026.csv - 台风登陆数据

导入实体:
- (:Typhoon) - 台风节点
- (:PathPoint) - 路径点节点
- (:Location) - 地理位置节点
- (:Time) - 时间节点
- (:Intensity) - 强度等级节点

关系:
- (:Typhoon)-[:HAS_PATH_POINT]->(:PathPoint)
- (:PathPoint)-[:NEXT]->(:PathPoint)
- (:Typhoon)-[:OCCURRED_IN]->(:Time)
- (:Typhoon)-[:LANDED_AT]->(:Location)
- (:Typhoon)-[:REACHED_INTENSITY]->(:Intensity)
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import math

# 添加backend到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from loguru import logger
from app.core.neo4j_client import neo4j_client
from app.core.config import settings


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """使用Haversine公式计算两点间距离（公里）"""
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_intensity_level(max_wind_speed: float) -> Tuple[str, str]:
    """根据最大风速获取强度等级代码和名称"""
    if max_wind_speed >= 51.0:
        return ("SuperTY", "超强台风")
    elif max_wind_speed >= 41.5:
        return ("STY", "强台风")
    elif max_wind_speed >= 32.7:
        return ("TY", "台风")
    elif max_wind_speed >= 24.5:
        return ("STS", "强热带风暴")
    elif max_wind_speed >= 17.2:
        return ("TS", "热带风暴")
    else:
        return ("TD", "热带低压")


def calculate_hour_of_year(timestamp_str: str) -> int:
    """计算年内小时数"""
    try:
        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        start_of_year = datetime(dt.year, 1, 1, 0, 0, 0)
        return int((dt - start_of_year).total_seconds() / 3600)
    except:
        return 0


def parse_timestamp_to_epoch(timestamp_str: str) -> int:
    """解析时间戳字符串为epoch毫秒"""
    try:
        dt = datetime.strptime(str(timestamp_str), '%Y-%m-%d %H:%M:%S')
        return int(dt.timestamp() * 1000)
    except:
        return 0


class FullDataImporterV2:
    """全量数据导入器 V2 - 包含所有新字段计算"""

    def __init__(self):
        self.batch_size = settings.KG_BATCH_SIZE
        self.csv_dir = Path(backend_dir) / "data" / "csv"

        # 强度等级定义
        self.intensity_definitions = [
            {"level": "TD", "name_cn": "热带低压", "wind_speed_min": 10.8, "wind_speed_max": 17.1},
            {"level": "TS", "name_cn": "热带风暴", "wind_speed_min": 17.2, "wind_speed_max": 24.4},
            {"level": "STS", "name_cn": "强热带风暴", "wind_speed_min": 24.5, "wind_speed_max": 32.6},
            {"level": "TY", "name_cn": "台风", "wind_speed_min": 32.7, "wind_speed_max": 41.4},
            {"level": "STY", "name_cn": "强台风", "wind_speed_min": 41.5, "wind_speed_max": 50.9},
            {"level": "SuperTY", "name_cn": "超强台风", "wind_speed_min": 51.0, "wind_speed_max": 999.0}
        ]

        self.stats = {
            "typhoons_imported": 0,
            "path_points_imported": 0,
            "locations_imported": 0,
            "landfalls_imported": 0,
            "intensities_imported": 0,
            "errors": []
        }

        # 存储登陆数据用于后续统计
        self.landfall_data = {}

    async def import_all(self):
        """执行全量导入主流程"""
        logger.info("\n" + "=" * 70)
        logger.info("Neo4j 全量数据导入 V2 开始")
        logger.info("=" * 70)

        start_time = datetime.now()

        try:
            # 1. 连接Neo4j
            logger.info("\n[1/10] 连接 Neo4j 数据库...")
            connected = await neo4j_client.connect()
            if not connected:
                raise ConnectionError("无法连接到Neo4j数据库")

            # 2. 导入强度等级定义
            logger.info("\n[2/10] 导入强度等级定义...")
            await self._import_intensity_definitions()

            # 3. 导入路径数据
            logger.info("\n[3/10] 导入台风路径数据...")
            await self._import_path_data()

            # 4. 导入登陆数据
            logger.info("\n[4/10] 导入登陆数据...")
            await self._import_landfall_data()

            # 5. 建立强度关系
            logger.info("\n[5/10] 建立强度关系...")
            await self._create_intensity_relationships()

            # 6. 更新时间节点统计
            logger.info("\n[6/10] 更新时间节点统计...")
            await self._update_time_node_stats()

            # 7. 建立生成和消散位置关系
            logger.info("\n[7/10] 建立生成和消散位置关系...")
            await self._create_lifecycle_relationships()

            # 8. 建立强度变化关系
            logger.info("\n[8/10] 建立强度变化关系...")
            await self._create_intensity_change_relationships()

            # 9. 建立相似性关系
            logger.info("\n[9/10] 建立相似性关系...")
            await self._create_similarity_relationships()

            # 10. 建立地理影响关系
            logger.info("\n[10/10] 建立地理影响关系...")
            await self._create_geographic_relationships()

            elapsed = (datetime.now() - start_time).total_seconds()

            logger.info("\n" + "=" * 70)
            logger.info("✅ 全量数据导入完成!")
            logger.info("=" * 70)
            logger.info(f"\n📊 导入统计:")
            logger.info(f"   台风节点: {self.stats['typhoons_imported']:,}")
            logger.info(f"   路径点节点: {self.stats['path_points_imported']:,}")
            logger.info(f"   地理位置节点: {self.stats['locations_imported']:,}")
            logger.info(f"   登陆关系: {self.stats['landfalls_imported']:,}")
            logger.info(f"   强度定义: {self.stats['intensities_imported']}")
            logger.info(f"\n⏱️  总耗时: {elapsed:.2f} 秒")

            if self.stats['errors']:
                logger.warning(f"\n⚠️  导入过程中有 {len(self.stats['errors'])} 个错误")

            return True

        except Exception as e:
            logger.error(f"\n❌ 全量导入失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

        finally:
            await neo4j_client.close()

    async def _import_intensity_definitions(self):
        """导入强度等级定义"""
        logger.info("创建强度等级定义节点...")

        query = """
        UNWIND $intensities as intensity
        MERGE (i:Intensity {level: intensity.level})
        SET i.name_cn = intensity.name_cn,
            i.wind_speed_min = intensity.wind_speed_min,
            i.wind_speed_max = intensity.wind_speed_max,
            i.created_at = datetime()
        RETURN count(i) as imported
        """

        try:
            result = await neo4j_client.run(query, {"intensities": self.intensity_definitions})
            self.stats['intensities_imported'] = result[0]['imported'] if result else 0
            logger.info(f"✅ 已导入 {self.stats['intensities_imported']} 个强度等级定义")
        except Exception as e:
            logger.error(f"❌ 强度等级导入失败: {e}")
            raise

    async def _import_path_data(self):
        """导入路径数据"""
        csv_path = self.csv_dir / "typhoon_paths_1966_2026.csv"

        if not csv_path.exists():
            raise FileNotFoundError(f"路径数据文件不存在: {csv_path}")

        logger.info(f"读取路径数据文件: {csv_path}")

        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            logger.info(f"📄 CSV文件读取成功，共 {len(df):,} 行数据")
        except Exception as e:
            logger.error(f"❌ CSV文件读取失败: {e}")
            raise

        required_columns = ['ty_code', 'ty_name_en', 'ty_name_ch', 'timestamp', 'latitude', 'longitude']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"CSV文件缺少必要列: {missing_columns}")

        grouped = df.groupby('ty_code')
        total_typhoons = len(grouped)
        logger.info(f"🔍 发现 {total_typhoons} 个独立台风")

        for idx, (ty_code, group) in enumerate(grouped, 1):
            try:
                if idx % 100 == 0 or idx == 1:
                    logger.info(f"   处理进度: {idx}/{total_typhoons} ({idx/total_typhoons*100:.1f}%)")

                await self._import_single_typhoon(ty_code, group)
                self.stats['typhoons_imported'] += 1

            except Exception as e:
                import traceback
                error_msg = f"台风 {ty_code} 导入失败: {e}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                self.stats['errors'].append(error_msg)

        logger.info(f"✅ 路径数据导入完成，成功导入 {self.stats['typhoons_imported']} 个台风")

    async def _import_single_typhoon(self, ty_code: str, group: pd.DataFrame):
        """导入单个台风的数据"""
        group = group.sort_values('timestamp')
        first_row = group.iloc[0]
        last_row = group.iloc[-1]

        # 计算台风统计数据
        typhoon_stats = self._calculate_typhoon_stats(group)

        typhoon_data = {
            'typhoon_id': str(ty_code),
            'name_en': str(first_row['ty_name_en']) if pd.notna(first_row['ty_name_en']) else '',
            'name_cn': str(first_row['ty_name_ch']) if pd.notna(first_row['ty_name_ch']) else '',
            'year': int(str(ty_code)[:4]),
            'max_wind_speed': typhoon_stats['max_wind_speed'],
            'min_pressure': typhoon_stats['min_pressure'],
            'max_power': typhoon_stats['max_power'],
            'peak_intensity': typhoon_stats['peak_intensity'],
            'total_path_points': len(group),
            'duration_hours': self._calculate_duration(group),
            'start_lat': float(first_row['latitude']),
            'start_lon': float(first_row['longitude']),
            'end_lat': float(last_row['latitude']),
            'end_lon': float(last_row['longitude']),
            'avg_moving_speed': typhoon_stats['avg_moving_speed'],
            'max_moving_speed': typhoon_stats['max_moving_speed'],
            'total_distance_km': typhoon_stats['total_distance_km'],
            'start_time_epoch': parse_timestamp_to_epoch(str(first_row['timestamp'])),
            'end_time_epoch': parse_timestamp_to_epoch(str(last_row['timestamp']))
        }

        # 准备路径点数据
        path_points = self._prepare_path_points(group, str(ty_code))

        await self._create_typhoon_with_paths(typhoon_data, path_points)
        self.stats['path_points_imported'] += len(path_points)

    def _calculate_typhoon_stats(self, group: pd.DataFrame) -> Dict:
        """计算台风统计数据"""
        stats = {
            'max_wind_speed': 0.0,
            'min_pressure': 9999.0,
            'max_power': None,
            'peak_intensity': None,
            'avg_moving_speed': None,
            'max_moving_speed': None,
            'total_distance_km': 0.0
        }

        # 强度统计
        if pd.notna(group['max_wind_speed']).any():
            stats['max_wind_speed'] = float(group['max_wind_speed'].max())
            stats['peak_intensity'] = get_intensity_level(stats['max_wind_speed'])[0]

        if pd.notna(group['center_pressure']).any():
            stats['min_pressure'] = float(group['center_pressure'].min())

        if pd.notna(group['power']).any():
            stats['max_power'] = int(group['power'].max())

        # 移动统计
        moving_speeds = []
        total_distance = 0.0
        prev_lat, prev_lon = None, None

        for _, row in group.iterrows():
            if pd.notna(row.get('moving_speed')):
                moving_speeds.append(float(row['moving_speed']))

            current_lat = float(row['latitude'])
            current_lon = float(row['longitude'])

            if prev_lat is not None and prev_lon is not None:
                total_distance += calculate_distance(prev_lat, prev_lon, current_lat, current_lon)

            prev_lat, prev_lon = current_lat, current_lon

        if moving_speeds:
            stats['avg_moving_speed'] = sum(moving_speeds) / len(moving_speeds)
            stats['max_moving_speed'] = max(moving_speeds)

        stats['total_distance_km'] = round(total_distance, 2)

        return stats

    def _prepare_path_points(self, group: pd.DataFrame, typhoon_id: str) -> List[Dict]:
        """准备路径点数据"""
        path_points = []
        first_row = group.iloc[0]
        genesis_lat = float(first_row['latitude'])
        genesis_lon = float(first_row['longitude'])

        for seq, (_, row) in enumerate(group.iterrows(), 1):
            timestamp_str = str(row['timestamp'])
            current_lat = float(row['latitude'])
            current_lon = float(row['longitude'])

            # 计算距生成点距离
            distance_from_genesis = calculate_distance(genesis_lat, genesis_lon, current_lat, current_lon)

            # 计算到下一个路径点的距离
            distance_to_next = None
            if seq < len(group):
                next_row = group.iloc[seq]
                next_lat = float(next_row['latitude'])
                next_lon = float(next_row['longitude'])
                distance_to_next = calculate_distance(current_lat, current_lon, next_lat, next_lon)

            # 计算气压变化趋势
            pressure_trend = None
            if seq > 1:
                prev_row = group.iloc[seq - 2]
                prev_pressure = float(prev_row['center_pressure']) if pd.notna(prev_row.get('center_pressure')) else None
                current_pressure = float(row['center_pressure']) if pd.notna(row.get('center_pressure')) else None
                if prev_pressure is not None and current_pressure is not None:
                    pressure_trend = current_pressure - prev_pressure

            # 获取强度等级
            wind_speed = float(row['max_wind_speed']) if pd.notna(row.get('max_wind_speed')) else 0.0
            intensity_level, intensity_name = get_intensity_level(wind_speed)

            csv_intensity = str(row['intensity']).strip() if pd.notna(row.get('intensity')) else None
            if csv_intensity:
                intensity_name = csv_intensity

            path_point = {
                'sequence': seq,
                'lat': current_lat,
                'lon': current_lon,
                'timestamp_epoch': parse_timestamp_to_epoch(timestamp_str),
                'hour_of_year': calculate_hour_of_year(timestamp_str),
                'pressure': float(row['center_pressure']) if pd.notna(row.get('center_pressure')) else None,
                'wind_speed': float(row['max_wind_speed']) if pd.notna(row.get('max_wind_speed')) else None,
                'intensity': intensity_name,
                'intensity_level': intensity_level,
                'power': int(row['power']) if pd.notna(row.get('power')) else None,
                'moving_direction': str(row['moving_direction']).strip() if pd.notna(row.get('moving_direction')) else None,
                'moving_speed': float(row['moving_speed']) if pd.notna(row.get('moving_speed')) else None,
                'distance_from_genesis': round(distance_from_genesis, 2),
                'distance_to_next': round(distance_to_next, 2) if distance_to_next is not None else None,
                'pressure_trend': round(pressure_trend, 2) if pressure_trend is not None else None
            }
            path_points.append(path_point)

        return path_points

    async def _create_typhoon_with_paths(self, typhoon_data: Dict, path_points: List[Dict]):
        """在Neo4j中创建台风节点和路径点节点"""
        query = """
        // 1. 创建台风节点
        MERGE (t:Typhoon {typhoon_id: $typhoon_id})
        SET t.name_en = $name_en,
            t.name_cn = $name_cn,
            t.year = $year,
            t.max_wind_speed = $max_wind_speed,
            t.min_pressure = $min_pressure,
            t.max_power = $max_power,
            t.peak_intensity = $peak_intensity,
            t.total_path_points = $total_path_points,
            t.duration_hours = $duration_hours,
            t.start_lat = $start_lat,
            t.start_lon = $start_lon,
            t.end_lat = $end_lat,
            t.end_lon = $end_lon,
            t.avg_moving_speed = $avg_moving_speed,
            t.max_moving_speed = $max_moving_speed,
            t.total_distance_km = $total_distance_km,
            t.start_time = datetime({epochMillis: $start_time_epoch}),
            t.end_time = datetime({epochMillis: $end_time_epoch}),
            t.created_at = datetime()

        // 2. 创建时间节点
        WITH t
        MERGE (tm:Time {year: $year})
        SET tm.is_peak_season = ($year_month >= 7 AND $year_month <= 9)
        MERGE (t)-[:OCCURRED_IN]->(tm)

        // 3. 创建路径点节点
        WITH t
        UNWIND $path_points as path
        CREATE (p:PathPoint {
            typhoon_id: $typhoon_id,
            sequence: path.sequence,
            lat: path.lat,
            lon: path.lon,
            location: point({latitude: path.lat, longitude: path.lon}),
            timestamp: datetime({epochMillis: path.timestamp_epoch}),
            hour_of_year: path.hour_of_year,
            pressure: path.pressure,
            wind_speed: path.wind_speed,
            intensity: path.intensity,
            intensity_level: path.intensity_level,
            power: path.power,
            moving_direction: path.moving_direction,
            moving_speed: path.moving_speed,
            distance_from_genesis: path.distance_from_genesis,
            distance_to_next: path.distance_to_next,
            pressure_trend: path.pressure_trend
        })
        CREATE (t)-[:HAS_PATH_POINT]->(p)

        // 4. 连接路径点
        WITH t, p, path
        OPTIONAL MATCH (prev:PathPoint {typhoon_id: $typhoon_id, sequence: path.sequence - 1})
        WHERE path.sequence > 1
        FOREACH (ignore IN CASE WHEN prev IS NOT NULL THEN [1] ELSE [] END |
            CREATE (prev)-[:NEXT]->(p)
        )

        RETURN count(p) as path_points_created
        """

        year_month = 0
        if path_points:
            try:
                first_timestamp_epoch = path_points[0].get('timestamp_epoch', 0)
                if first_timestamp_epoch > 0:
                    dt = datetime.fromtimestamp(first_timestamp_epoch / 1000)
                    year_month = dt.month
            except:
                pass

        params = {**typhoon_data, 'path_points': path_points, 'year_month': year_month}

        try:
            result = await neo4j_client.run(query, params)
            return result[0]['path_points_created'] if result else 0
        except Exception as e:
            logger.error(f"创建台风 {typhoon_data['typhoon_id']} 失败: {e}")
            raise

    async def _import_landfall_data(self):
        """导入登陆数据"""
        csv_path = self.csv_dir / "typhoon_land_1966_2026.csv"

        if not csv_path.exists():
            logger.warning(f"⚠️ 登陆数据文件不存在: {csv_path}")
            return

        logger.info(f"读取登陆数据文件: {csv_path}")

        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            logger.info(f"📄 登陆数据读取成功，共 {len(df):,} 条登陆记录")
        except Exception as e:
            logger.error(f"❌ 登陆数据读取失败: {e}")
            return

        required_columns = ['ty_code', 'land_address', 'land_time']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"⚠️ 登陆数据缺少列: {missing_columns}")
            return

        # 按台风统计登陆次数
        landfall_counts = df.groupby('ty_code').size().to_dict()

        landfalls = []
        for _, row in df.iterrows():
            raw_lat = float(row['land_lat']) if pd.notna(row.get('land_lat')) else None
            raw_lon = float(row['land_lng']) if pd.notna(row.get('land_lng')) else None
            lat, lon = self._correct_coordinates(raw_lat, raw_lon)

            land_time_epoch = parse_timestamp_to_epoch(str(row['land_time']))

            typhoon_id = str(row['ty_code'])
            landfall = {
                'typhoon_id': typhoon_id,
                'location_name': str(row['land_address']).strip() if pd.notna(row['land_address']) else '',
                'land_time_epoch': land_time_epoch,
                'intensity': str(row['land_strong']).strip() if pd.notna(row.get('land_strong')) else None,
                'land_info': str(row['land_info']).strip() if pd.notna(row.get('land_info')) else None,
                'lat': lat,
                'lon': lon,
                'landfall_count': landfall_counts.get(typhoon_id, 0)
            }
            landfalls.append(landfall)

            # 存储登陆数据用于后续统计
            if typhoon_id not in self.landfall_data:
                self.landfall_data[typhoon_id] = []
            self.landfall_data[typhoon_id].append(landfall)

        # 分批导入
        total = len(landfalls)
        imported = 0

        for i in range(0, total, self.batch_size):
            batch = landfalls[i:i + self.batch_size]

            query = """
            UNWIND $landfalls as landfall
            MATCH (t:Typhoon {typhoon_id: landfall.typhoon_id})
            SET t.landfall_count = landfall.landfall_count
            MERGE (l:Location {name: landfall.location_name})
            SET l.lat = landfall.lat,
                l.lon = landfall.lon,
                l.location = CASE WHEN landfall.lat IS NOT NULL AND landfall.lon IS NOT NULL
                    THEN point({latitude: landfall.lat, longitude: landfall.lon})
                    ELSE NULL END,
                l.intensity = landfall.intensity,
                l.description = landfall.land_info,
                l.type = 'city'
            MERGE (t)-[r:LANDED_AT]->(l)
            SET r.land_time = datetime({epochMillis: landfall.land_time_epoch}),
                r.lat = landfall.lat,
                r.lon = landfall.lon,
                r.intensity = landfall.intensity
            RETURN count(r) as imported
            """

            try:
                result = await neo4j_client.run(query, {"landfalls": batch})
                batch_imported = result[0]['imported'] if result else 0
                imported += batch_imported

                if (i // self.batch_size) % 10 == 0:
                    logger.info(f"   登陆数据导入进度: {min(i + len(batch), total)}/{total}")

            except Exception as e:
                error_msg = f"批次 {i//self.batch_size} 导入失败: {e}"
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)

        self.stats['landfalls_imported'] = imported

        try:
            location_result = await neo4j_client.run("MATCH (l:Location) RETURN count(l) as count")
            self.stats['locations_imported'] = location_result[0]['count'] if location_result else 0
        except:
            pass

        logger.info(f"✅ 登陆数据导入完成，成功导入 {imported} 条登陆关系")

    async def _create_intensity_relationships(self):
        """建立台风与强度等级的关系，包含时间信息"""
        logger.info("建立台风与强度等级的关系...")

        # 首先为每个台风计算各个强度等级的时间范围
        query_calc_times = """
        MATCH (t:Typhoon)-[:HAS_PATH_POINT]->(p:PathPoint)
        WHERE p.wind_speed > 0
        WITH t, p,
            CASE
                WHEN p.wind_speed >= 51.0 THEN 'SuperTY'
                WHEN p.wind_speed >= 41.5 THEN 'STY'
                WHEN p.wind_speed >= 32.7 THEN 'TY'
                WHEN p.wind_speed >= 24.5 THEN 'STS'
                WHEN p.wind_speed >= 17.2 THEN 'TS'
                ELSE 'TD'
            END as intensity_level
        WITH t, intensity_level,
             min(p.timestamp) as start_time,
             max(p.timestamp) as end_time,
             count(p) as point_count,
             max(p.wind_speed) as max_wind_in_level
        RETURN t.typhoon_id as typhoon_id, intensity_level,
               start_time, end_time, point_count, max_wind_in_level
        ORDER BY t.typhoon_id, start_time
        """

        try:
            # 获取所有台风的强度时间数据
            intensity_times = await neo4j_client.run(query_calc_times)
            logger.info(f"📊 计算出 {len(intensity_times)} 条台风-强度时间记录")

            # 按台风分组处理
            typhoon_intensities = {}
            for record in intensity_times:
                typhoon_id = record['typhoon_id']
                if typhoon_id not in typhoon_intensities:
                    typhoon_intensities[typhoon_id] = []
                typhoon_intensities[typhoon_id].append({
                    'intensity_level': record['intensity_level'],
                    'start_time_epoch': int(record['start_time'].to_native().timestamp() * 1000) if hasattr(record['start_time'], 'to_native') else 0,
                    'end_time_epoch': int(record['end_time'].to_native().timestamp() * 1000) if hasattr(record['end_time'], 'to_native') else 0,
                    'point_count': record['point_count'],
                    'max_wind_in_level': record['max_wind_in_level']
                })

            # 批量创建关系
            total_relationships = 0
            for typhoon_id, intensities in typhoon_intensities.items():
                query_create = """
                MATCH (t:Typhoon {typhoon_id: $typhoon_id})
                UNWIND $intensities as intensity_data
                MATCH (i:Intensity {level: intensity_data.intensity_level})
                MERGE (t)-[r:REACHED_INTENSITY]->(i)
                SET r.start_time = datetime({epochMillis: intensity_data.start_time_epoch}),
                    r.end_time = datetime({epochMillis: intensity_data.end_time_epoch}),
                    r.duration_hours = duration.inSeconds(
                        datetime({epochMillis: intensity_data.start_time_epoch}),
                        datetime({epochMillis: intensity_data.end_time_epoch})
                    ) / 3600.0,
                    r.point_count = intensity_data.point_count,
                    r.max_wind_speed = intensity_data.max_wind_in_level
                RETURN count(r) as created
                """

                try:
                    result = await neo4j_client.run(query_create, {
                        'typhoon_id': typhoon_id,
                        'intensities': intensities
                    })
                    total_relationships += len(intensities)
                except Exception as e:
                    logger.error(f"创建台风 {typhoon_id} 的强度关系失败: {e}")

            logger.info(f"✅ 已建立 {total_relationships} 个强度关系（含时间信息）")
        except Exception as e:
            logger.error(f"❌ 强度关系建立失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def _update_time_node_stats(self):
        """更新时间节点统计信息"""
        logger.info("更新时间节点统计信息...")

        query = """
        // 为每个年份计算统计信息
        MATCH (t:Typhoon)-[:OCCURRED_IN]->(tm:Time)
        WITH tm.year as year, tm,
             count(t) as total_typhoons,
             max(t.max_wind_speed) as max_wind_speed
        // 找到最强台风
        MATCH (strongest:Typhoon)-[:OCCURRED_IN]->(tm2:Time {year: year})
        WHERE strongest.max_wind_speed = max_wind_speed
        WITH year, tm, total_typhoons, max_wind_speed, strongest.typhoon_id as strongest_id,
             strongest.peak_intensity as strongest_level
        // 计算登陆次数
        OPTIONAL MATCH (t2:Typhoon)-[:OCCURRED_IN]->(tm3:Time {year: year})
        OPTIONAL MATCH (t2)-[r:LANDED_AT]->()
        WITH year, tm, total_typhoons, max_wind_speed, strongest_id, strongest_level,
             count(r) as total_landfalls
        // 更新时间节点
        SET tm.total_typhoons = total_typhoons,
            tm.total_landfalls = total_landfalls,
            tm.strongest_typhoon_id = strongest_id,
            tm.strongest_wind_speed = max_wind_speed,
            tm.strongest_intensity_level = strongest_level
        RETURN count(tm) as updated
        """

        try:
            result = await neo4j_client.run(query)
            updated = result[0]['updated'] if result else 0
            logger.info(f"✅ 已更新 {updated} 个时间节点的统计信息")
        except Exception as e:
            logger.error(f"❌ 时间节点统计更新失败: {e}")

    def _calculate_duration(self, group: pd.DataFrame) -> int:
        """计算台风持续时长（小时）"""
        try:
            timestamps = pd.to_datetime(group['timestamp'])
            duration = (timestamps.max() - timestamps.min()).total_seconds() / 3600
            return int(duration)
        except:
            return 0

    def _correct_coordinates(self, raw_lat: float, raw_lon: float) -> tuple:
        """纠正经纬度"""
        if raw_lat is None or raw_lon is None:
            return (raw_lat, raw_lon)

        if -90 <= raw_lat <= 90 and not (-90 <= raw_lon <= 90):
            return (raw_lat, raw_lon)
        elif -90 <= raw_lon <= 90 and not (-90 <= raw_lat <= 90):
            return (raw_lon, raw_lat)
        else:
            if abs(raw_lat) <= abs(raw_lon):
                return (raw_lat, raw_lon)
            else:
                return (raw_lon, raw_lat)

    async def _create_lifecycle_relationships(self):
        """建立生成和消散位置关系"""
        logger.info("建立生成和消散位置关系...")

        # 创建生成位置关系
        query_gen = """
        MATCH (t:Typhoon)-[:HAS_PATH_POINT]->(p:PathPoint {sequence: 0})
        MERGE (loc:Location {name: '生成位置_' + t.typhoon_id})
        ON CREATE SET loc.lat = p.lat, loc.lon = p.lon
        MERGE (t)-[r:GENERATED_AT]->(loc)
        SET r.timestamp = p.timestamp,
            r.lat = p.lat,
            r.lon = p.lon,
            r.description = '台风生成位置'
        RETURN count(r) as created
        """

        # 创建消散位置关系
        query_dis = """
        MATCH (t:Typhoon)-[:HAS_PATH_POINT]->(p:PathPoint)
        WITH t, p ORDER BY p.sequence DESC
        WITH t, head(collect(p)) as last_p
        MERGE (loc:Location {name: '消散位置_' + t.typhoon_id})
        ON CREATE SET loc.lat = last_p.lat, loc.lon = last_p.lon
        MERGE (t)-[r:DISSIPATED_AT]->(loc)
        SET r.timestamp = last_p.timestamp,
            r.lat = last_p.lat,
            r.lon = last_p.lon,
            r.description = '台风消散位置'
        RETURN count(r) as created
        """

        try:
            result_gen = await neo4j_client.run(query_gen)
            gen_count = result_gen[0]['created'] if result_gen else 0

            result_dis = await neo4j_client.run(query_dis)
            dis_count = result_dis[0]['created'] if result_dis else 0

            logger.info(f"✅ 已建立 {gen_count} 个生成位置关系, {dis_count} 个消散位置关系")
        except Exception as e:
            logger.error(f"❌ 生命周期关系建立失败: {e}")

    async def _create_intensity_change_relationships(self):
        """建立强度变化关系"""
        logger.info("建立强度变化关系...")

        # 查询台风的强度变化序列
        query = """
        MATCH (t:Typhoon)-[:HAS_PATH_POINT]->(p:PathPoint)
        WHERE p.intensity_level IS NOT NULL
        WITH t, p ORDER BY p.sequence
        WITH t,
             collect({level: p.intensity_level, time: p.timestamp, wind: p.wind_speed, pressure: p.pressure}) as points
        WITH t, points,
             [i in range(0, size(points)-2) WHERE points[i].level <> points[i+1].level | {
                 from_level: points[i].level,
                 to_level: points[i+1].level,
                 change_time: points[i+1].time,
                 wind_change: points[i+1].wind - points[i].wind,
                 pressure_change: CASE WHEN points[i].pressure IS NOT NULL AND points[i+1].pressure IS NOT NULL
                                      THEN points[i+1].pressure - points[i].pressure
                                      ELSE NULL END
             }] as changes
        UNWIND changes as change
        WITH t, change
        MATCH (i:Intensity {level: change.to_level})
        MERGE (t)-[r:INTENSIFIED_TO]->(i)
        SET r.from_level = change.from_level,
            r.to_level = change.to_level,
            r.change_time = change.change_time,
            r.wind_speed_change = change.wind_change,
            r.pressure_change = change.pressure_change
        RETURN count(r) as created
        """

        try:
            result = await neo4j_client.run(query)
            created = result[0]['created'] if result else 0
            logger.info(f"✅ 已建立 {created} 个强度增强关系")

            # 同样创建减弱关系（反向）
            query_weaken = """
            MATCH (t:Typhoon)-[:HAS_PATH_POINT]->(p:PathPoint)
            WHERE p.intensity_level IS NOT NULL
            WITH t, p ORDER BY p.sequence
            WITH t,
                 collect({level: p.intensity_level, time: p.timestamp, wind: p.wind_speed, pressure: p.pressure}) as points
            WITH t, points,
                 [i in range(0, size(points)-2)
                  WHERE points[i].level <> points[i+1].level
                    AND CASE points[i].level
                        WHEN 'TD' THEN 1
                        WHEN 'TS' THEN 2
                        WHEN 'STS' THEN 3
                        WHEN 'TY' THEN 4
                        WHEN 'STY' THEN 5
                        WHEN 'SuperTY' THEN 6
                        ELSE 0
                        END >
                        CASE points[i+1].level
                        WHEN 'TD' THEN 1
                        WHEN 'TS' THEN 2
                        WHEN 'STS' THEN 3
                        WHEN 'TY' THEN 4
                        WHEN 'STY' THEN 5
                        WHEN 'SuperTY' THEN 6
                        ELSE 0
                        END | {
                     from_level: points[i].level,
                     to_level: points[i+1].level,
                     change_time: points[i+1].time,
                     wind_change: points[i+1].wind - points[i].wind,
                     pressure_change: CASE WHEN points[i].pressure IS NOT NULL AND points[i+1].pressure IS NOT NULL
                                          THEN points[i+1].pressure - points[i].pressure
                                          ELSE NULL END
                 }] as changes
            UNWIND changes as change
            WITH t, change
            MATCH (i:Intensity {level: change.to_level})
            MERGE (t)-[r:WEAKENED_TO]->(i)
            SET r.from_level = change.from_level,
                r.to_level = change.to_level,
                r.change_time = change.change_time,
                r.wind_speed_change = change.wind_change,
                r.pressure_change = change.pressure_change
            RETURN count(r) as created
            """

            result_weak = await neo4j_client.run(query_weaken)
            weak_count = result_weak[0]['created'] if result_weak else 0
            logger.info(f"✅ 已建立 {weak_count} 个强度减弱关系")

        except Exception as e:
            logger.error(f"❌ 强度变化关系建立失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def _create_similarity_relationships(self):
        """建立相似性关系（基于路径相似度）"""
        logger.info("建立相似性关系...")

        # 简化的相似性计算：基于生成位置和峰值强度
        query = """
        MATCH (t1:Typhoon), (t2:Typhoon)
        WHERE t1.typhoon_id < t2.typhoon_id
          AND t1.year >= 2000 AND t2.year >= 2000  // 只计算2000年后的台风，减少计算量
        WITH t1, t2,
             sqrt((t1.start_lat - t2.start_lat)^2 + (t1.start_lon - t2.start_lon)^2) as genesis_dist,
             abs(t1.max_wind_speed - t2.max_wind_speed) as wind_diff
        WHERE genesis_dist < 5  // 生成位置距离小于5度
        WITH t1, t2, genesis_dist, wind_diff,
             1.0 / (1.0 + genesis_dist) as genesis_sim,
             CASE WHEN t1.max_wind_speed > 0 AND t2.max_wind_speed > 0
                  THEN 1.0 - (wind_diff / CASE WHEN t1.max_wind_speed > t2.max_wind_speed THEN t1.max_wind_speed ELSE t2.max_wind_speed END)
                  ELSE 0.5
             END as intensity_sim
        WITH t1, t2, genesis_sim, intensity_sim,
             (genesis_sim * 0.5 + intensity_sim * 0.5) as total_sim
        WHERE total_sim > 0.6
        MERGE (t1)-[r:SIMILAR_TO]->(t2)
        SET r.similarity_score = total_sim,
            r.genesis_similarity = genesis_sim,
            r.intensity_similarity = intensity_sim,
            r.path_similarity = 0.5,
            r.temporal_similarity = 0.5,
            r.calculated_at = datetime()
        RETURN count(r) as created
        """

        try:
            result = await neo4j_client.run(query)
            created = result[0]['created'] if result else 0
            logger.info(f"✅ 已建立 {created} 个相似性关系")
        except Exception as e:
            logger.error(f"❌ 相似性关系建立失败: {e}")

    async def _create_geographic_relationships(self):
        """建立地理影响关系"""
        logger.info("建立地理影响关系...")

        # 获取主要城市/地区列表（从登陆数据中提取）
        query_major_locations = """
        MATCH (l:Location)
        WITH l, count{(l)<-[:LANDED_AT]-()} as landfall_count
        WHERE landfall_count > 0
        RETURN l.name as name, l.lat as lat, l.lon as lon
        """

        try:
            locations = await neo4j_client.run(query_major_locations)
            logger.info(f"📍 找到 {len(locations)} 个主要地点")

            total_affected = 0
            total_passed = 0

            for loc in locations:
                # 创建影响区域关系（台风路径经过该地点附近100km内）
                query_affected = """
                MATCH (t:Typhoon)-[:HAS_PATH_POINT]->(p:PathPoint)
                WITH t, p,
                     2 * 6371 * asin(sqrt(
                        sin(radians(p.lat - $lat)/2)^2 +
                        cos(radians($lat)) * cos(radians(p.lat)) *
                        sin(radians(p.lon - $lon)/2)^2
                     )) as distance_km
                WHERE distance_km < 100
                WITH t, min(distance_km) as min_dist, min(p.timestamp) as first_pass
                MERGE (loc:Location {name: $name})
                MERGE (t)-[r:AFFECTED_AREA]->(loc)
                SET r.min_distance_km = min_dist,
                    r.impact_level = CASE
                        WHEN min_dist < 50 THEN 'high'
                        WHEN min_dist < 100 THEN 'medium'
                        ELSE 'low'
                    END
                RETURN count(r) as created
                """

                result = await neo4j_client.run(query_affected, {
                    'name': loc['name'],
                    'lat': loc['lat'],
                    'lon': loc['lon']
                })
                total_affected += result[0]['created'] if result else 0

                # 创建经过附近关系（更近的距离，50km内）
                query_passed = """
                MATCH (t:Typhoon)-[:HAS_PATH_POINT]->(p:PathPoint)
                WITH t, p,
                     2 * 6371 * asin(sqrt(
                        sin(radians(p.lat - $lat)/2)^2 +
                        cos(radians($lat)) * cos(radians(p.lat)) *
                        sin(radians(p.lon - $lon)/2)^2
                     )) as distance_km
                WHERE distance_km < 50
                WITH t, min(distance_km) as min_dist, min(p.timestamp) as first_pass
                MERGE (loc:Location {name: $name})
                MERGE (t)-[r:PASSED_NEAR]->(loc)
                SET r.min_distance_km = min_dist,
                    r.passed_at = first_pass
                RETURN count(r) as created
                """

                result_passed = await neo4j_client.run(query_passed, {
                    'name': loc['name'],
                    'lat': loc['lat'],
                    'lon': loc['lon']
                })
                total_passed += result_passed[0]['created'] if result_passed else 0

            logger.info(f"✅ 已建立 {total_affected} 个影响区域关系, {total_passed} 个经过附近关系")

        except Exception as e:
            logger.error(f"❌ 地理影响关系建立失败: {e}")
            import traceback
            logger.error(traceback.format_exc())


async def main():
    """主函数"""
    importer = FullDataImporterV2()
    success = await importer.import_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
