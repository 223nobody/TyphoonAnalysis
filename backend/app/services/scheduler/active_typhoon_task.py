"""
活跃台风爬虫定时任务
"""
import logging
from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.typhoon import Typhoon, TyphoonPath, ActiveTyphoonForecast
from app.services.crawler.active_typhoon_crawler import active_typhoon_crawler

logger = logging.getLogger(__name__)


async def fetch_active_typhoon_task():
    """
    定时任务：爬取活跃台风数据并存储到 active_typhoon 表

    业务逻辑：
    1. 查询数据库中是否存在活跃台风（status=1）
    2. 如果存在活跃台风，爬取浙江台风网数据
    3. 解析路径数据并存储到 active_typhoon 表
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. 查询数据库中的活跃台风（status=1）
            active_typhoon_query = select(Typhoon).where(Typhoon.status == 1)
            result = await db.execute(active_typhoon_query)
            active_typhoons = result.scalars().all()

            if not active_typhoons:
                return

            # 取第一个活跃台风
            active_typhoon = active_typhoons[0]
            typhoon_id = active_typhoon.typhoon_id

            # 2. 获取年月参数（从台风ID中提取，格式如 2601 -> 202601）
            year_month = f"2026{typhoon_id[2:4]}" if len(typhoon_id) >= 4 else "202601"

            # 3. 爬取浙江台风网数据
            raw_data = active_typhoon_crawler.fetch_active_typhoon_data(year_month)

            if not raw_data:
                logger.warning("爬取活跃台风数据失败")
                return

            # 4. 解析路径数据
            path_points = active_typhoon_crawler.parse_typhoon_path(raw_data)

            if not path_points:
                logger.warning("未能解析到路径数据")
                return

            # 5. 存储到 typhoon_paths 表（更新或插入）
            # 删除该台风的旧预报数据
            delete_forecast_stmt = delete(ActiveTyphoonForecast).where(ActiveTyphoonForecast.typhoon_id == typhoon_id)
            await db.execute(delete_forecast_stmt)

            # 插入或更新路径数据
            inserted_count = 0
            updated_count = 0
            failed_count = 0
            forecast_count = 0

            for idx, point in enumerate(path_points):
                try:
                    # 数据验证
                    if not point.get('timestamp'):
                        logger.warning(f"路径点 {idx} 缺少时间戳，跳过")
                        failed_count += 1
                        continue

                    if point.get('latitude') is None or point.get('longitude') is None:
                        logger.warning(f"路径点 {idx} 缺少经纬度，跳过")
                        failed_count += 1
                        continue

                    # 检查该路径点是否已存在
                    existing_query = select(TyphoonPath).where(
                        TyphoonPath.typhoon_id == typhoon_id,
                        TyphoonPath.timestamp == point['timestamp']
                    )
                    existing_result = await db.execute(existing_query)
                    existing_path = existing_result.scalar_one_or_none()

                    if existing_path:
                        # 更新现有记录
                        existing_path.latitude = float(point['latitude'])
                        existing_path.longitude = float(point['longitude'])
                        existing_path.center_pressure = float(point['center_pressure']) if point.get('center_pressure') is not None else None
                        existing_path.max_wind_speed = float(point['max_wind_speed']) if point.get('max_wind_speed') is not None else None
                        existing_path.moving_speed = float(point['moving_speed']) if point.get('moving_speed') is not None else None
                        existing_path.moving_direction = str(point['moving_direction']) if point.get('moving_direction') else None
                        existing_path.intensity = str(point['intensity']) if point.get('intensity') else None
                        updated_count += 1
                    else:
                        # 插入新记录
                        new_path = TyphoonPath(
                            typhoon_id=typhoon_id,
                            timestamp=point['timestamp'],
                            latitude=float(point['latitude']),
                            longitude=float(point['longitude']),
                            center_pressure=float(point['center_pressure']) if point.get('center_pressure') is not None else None,
                            max_wind_speed=float(point['max_wind_speed']) if point.get('max_wind_speed') is not None else None,
                            moving_speed=float(point['moving_speed']) if point.get('moving_speed') is not None else None,
                            moving_direction=str(point['moving_direction']) if point.get('moving_direction') else None,
                            intensity=str(point['intensity']) if point.get('intensity') else None
                        )
                        db.add(new_path)
                        inserted_count += 1

                    # 处理预报数据
                    forecast_data = point.get('forecast', [])
                    if forecast_data and isinstance(forecast_data, list):
                        for forecast_agency_data in forecast_data:
                            try:
                                agency = forecast_agency_data.get('tm', '未知')
                                forecast_points = forecast_agency_data.get('forecastpoints', [])

                                for fp in forecast_points:
                                    try:
                                        # 解析预报时间
                                        forecast_time_str = fp.get('time')
                                        if not forecast_time_str:
                                            continue

                                        forecast_time = active_typhoon_crawler._parse_time(str(forecast_time_str))

                                        # 解析预报位置
                                        fp_lat = active_typhoon_crawler._parse_float(fp.get('lat') or fp.get('latitude'))
                                        fp_lon = active_typhoon_crawler._parse_float(fp.get('lng') or fp.get('longitude'))

                                        if fp_lat is None or fp_lon is None:
                                            continue

                                        # 创建预报记录
                                        forecast_record = ActiveTyphoonForecast(
                                            typhoon_id=typhoon_id,
                                            base_time=point['timestamp'],  # 预报基准时间
                                            forecast_time=forecast_time,
                                            forecast_agency=agency,
                                            latitude=fp_lat,
                                            longitude=fp_lon,
                                            center_pressure=active_typhoon_crawler._parse_float(fp.get('pressure')),
                                            max_wind_speed=active_typhoon_crawler._parse_float(fp.get('speed')),
                                            power_level=active_typhoon_crawler._parse_int(fp.get('power')),
                                            intensity=str(fp.get('strong')) if fp.get('strong') else None
                                        )
                                        db.add(forecast_record)
                                        forecast_count += 1
                                    except Exception as e:
                                        logger.warning(f"插入预报点失败: {e}")
                                        continue
                            except Exception as e:
                                logger.warning(f"处理预报机构数据失败: {e}")
                                continue

                    # 每10条记录输出一次进度
                    if (idx + 1) % 10 == 0:
                        logger.info(f"已处理 {idx + 1}/{len(path_points)} 个路径点")

                except Exception as e:
                    logger.error(f"插入路径点 {idx} 失败: {e}")
                    failed_count += 1
                    continue

            # 提交事务
            await db.commit()

        except Exception as e:
            logger.error(f"❌ 活跃台风爬取任务失败: {e}", exc_info=True)
            await db.rollback()

if __name__ == "__main__":
    import asyncio

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("=" * 60)
    logger.info("手动运行活跃台风爬虫任务")
    logger.info("=" * 60)

    # 运行爬虫任务
    asyncio.run(fetch_active_typhoon_task())

    logger.info("=" * 60)
    logger.info("任务执行完成")
    logger.info("=" * 60)
