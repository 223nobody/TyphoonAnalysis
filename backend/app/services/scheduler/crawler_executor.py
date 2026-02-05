"""
统一爬虫执行器 - 协调所有爬虫组件的执行
"""
import logging
from datetime import datetime
from sqlalchemy import select, delete

from app.core.database import AsyncSessionLocal
from app.models.typhoon import CrawlerLog, Typhoon, TyphoonPath, ActiveTyphoonForecast
from app.services.crawler.cma_crawler import cma_crawler
from app.services.crawler.active_typhoon_crawler import active_typhoon_crawler
from app.services.crawler.bulletin_crawler import bulletin_crawler

logger = logging.getLogger(__name__)


async def run_all_crawlers():
    """
    执行所有爬虫任务 - 完整的数据爬取流程
    
    执行顺序：
    1. 台风公报爬取
    2. 活跃台风列表爬取
    3. 活跃台风路径爬取
    """
    start_time = datetime.now()
    logger.info("开始执行完整爬取任务")

    results = {
        'bulletin': None,
        'typhoons': None,
        'active_typhoon': None
    }

    async with AsyncSessionLocal() as db:
        try:
            # 1. 爬取台风公报
            try:
                logger.info("爬取台风公报...")
                bulletin = bulletin_crawler.get_typhoon_bulletin()
                if bulletin:
                    results['bulletin'] = 'success'
                else:
                    results['bulletin'] = 'no_data'
                    logger.info("当前没有活跃的台风公报")
            except Exception as e:
                results['bulletin'] = 'failed'
                logger.error(f"台风公报爬取失败: {e}")

            # 2. 爬取活跃台风列表
            try:
                logger.info("爬取活跃台风列表...")
                typhoons = await cma_crawler.get_active_typhoons()
                if typhoons:
                    results['typhoons'] = f"{len(typhoons)}个"
                else:
                    results['typhoons'] = 'no_data'
                    logger.info("没有活跃台风")
            except Exception as e:
                results['typhoons'] = 'failed'
                logger.error(f"活跃台风列表爬取失败: {e}")

            # 3. 爬取活跃台风路径数据
            try:
                logger.info("爬取活跃台风路径数据...")
                await fetch_active_typhoon_task()
                results['active_typhoon'] = 'success'
                logger.info("活跃台风路径数据爬取完成")
            except Exception as e:
                results['active_typhoon'] = 'failed'
                logger.error(f"活跃台风路径爬取失败: {e}")

            # 记录执行结果
            duration = (datetime.now() - start_time).total_seconds()
            status = 'success' if all(r in ['success', 'no_data'] for r in results.values()) else 'partial'

            log = CrawlerLog(
                task_type="full_crawl",
                status=status,
                message=f"完整爬取完成 | 公报:{results['bulletin']} | 台风:{results['typhoons']} | 路径:{results['active_typhoon']} | 耗时:{duration:.1f}秒",
                data_count=0
            )
            db.add(log)
            await db.commit()

            logger.info(f"完整爬取任务完成，耗时: {duration:.1f}秒")

        except Exception as e:
            logger.error(f"完整爬取任务失败: {e}", exc_info=True)
            
            try:
                log = CrawlerLog(
                    task_type="full_crawl",
                    status="failed",
                    message=f"完整爬取失败: {str(e)}",
                    error_message=str(e)
                )
                db.add(log)
                await db.commit()
            except Exception as log_error:
                logger.error(f"记录错误日志失败: {log_error}")


async def run_typhoons_crawler():
    """
    执行台风基本信息爬取任务
    """
    start_time = datetime.now()
    logger.info("开始爬取台风基本信息")

    async with AsyncSessionLocal() as db:
        try:
            from app.models.typhoon import Typhoon, TyphoonPath

            typhoons = await cma_crawler.get_active_typhoons()

            if not typhoons:
                logger.info("未获取到活跃台风数据")
                log = CrawlerLog(
                    task_type="typhoons_crawl",
                    status="success",
                    message="未获取到活跃台风",
                    data_count=0
                )
                db.add(log)
                await db.commit()
                return

            query = select(Typhoon.typhoon_id)
            result = await db.execute(query)
            existing_ids = set(result.scalars().all())

            new_count = 0
            updated_count = 0
            new_typhoon_ids = []

            for typhoon_data in typhoons:
                typhoon_id = typhoon_data["typhoon_id"]
                typhoon_status = typhoon_data["status"]

                if typhoon_id in existing_ids:
                    query = select(Typhoon).where(Typhoon.typhoon_id == typhoon_id)
                    result = await db.execute(query)
                    existing = result.scalar_one_or_none()

                    if existing and existing.status != typhoon_status:
                        existing.status = typhoon_status
                        updated_count += 1
                else:
                    new_typhoon = Typhoon(**typhoon_data)
                    db.add(new_typhoon)
                    new_count += 1
                    new_typhoon_ids.append(typhoon_id)

            await db.commit()

            path_count = 0
            if new_typhoon_ids:
                for typhoon_id in new_typhoon_ids:
                    try:
                        paths = await cma_crawler.get_typhoon_path(typhoon_id)

                        if not paths:
                            continue

                        for path_data in paths:
                            existing_path_query = select(TyphoonPath).where(
                                TyphoonPath.typhoon_id == path_data["typhoon_id"],
                                TyphoonPath.timestamp == path_data["timestamp"]
                            )
                            existing_path_result = await db.execute(existing_path_query)
                            existing_path = existing_path_result.scalar_one_or_none()

                            if existing_path:
                                continue

                            new_path = TyphoonPath(**path_data)
                            db.add(new_path)
                            path_count += 1

                    except Exception as e:
                        logger.error(f"爬取台风 {typhoon_id} 路径数据失败: {e}")
                        continue

                await db.commit()

            duration = (datetime.now() - start_time).total_seconds()
            log = CrawlerLog(
                task_type="typhoons_crawl",
                status="success",
                message=f"台风基本信息 | 总数:{len(typhoons)} | 新增:{new_count} | 更新:{updated_count} | 路径:{path_count} | 耗时:{duration:.1f}秒",
                data_count=len(typhoons)
            )
            db.add(log)
            await db.commit()

            logger.info(f"台风基本信息爬取完成 | 总数:{len(typhoons)} | 新增:{new_count} | 更新:{updated_count} | 路径:{path_count} | 耗时:{duration:.1f}秒")

        except Exception as e:
            logger.error(f"台风基本信息爬取失败: {e}", exc_info=True)
            
            try:
                log = CrawlerLog(
                    task_type="typhoons_crawl",
                    status="failed",
                    message="台风基本信息爬取失败",
                    error_message=str(e)
                )
                db.add(log)
                await db.commit()
            except Exception as log_error:
                logger.error(f"记录错误日志失败: {log_error}")


async def fetch_active_typhoon_task():
    """
    定时任务：爬取活跃台风数据并存储到数据库

    业务逻辑：
    1. 查询数据库中是否存在活跃台风（status=1）
    2. 如果存在活跃台风，爬取浙江台风网数据
    3. 解析路径数据并存储到 typhoon_paths 表
    4. 处理预报数据并存储到 active_typhoon_forecasts 表
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. 查询数据库中的活跃台风（status=1）
            active_typhoon_query = select(Typhoon).where(Typhoon.status == 1)
            result = await db.execute(active_typhoon_query)
            active_typhoons = result.scalars().all()

            if not active_typhoons:
                logger.info("没有活跃台风")
                return

            # 取第一个活跃台风
            active_typhoon = active_typhoons[0]
            typhoon_id = active_typhoon.typhoon_id

            # 2. 获取年月参数（从台风ID中提取，格式如 2601 -> 202601）
            if len(typhoon_id) >= 4:
                year_month = f"2026{typhoon_id[2:4]}"
            else:
                year_month = "202601"

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
                                            base_time=point['timestamp'],
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

            logger.info(f"活跃台风路径爬取完成 | 插入:{inserted_count} | 更新:{updated_count} | 失败:{failed_count} | 预报:{forecast_count}")

        except Exception as e:
            logger.error(f"活跃台风爬取任务失败: {e}", exc_info=True)
            await db.rollback()


async def run_active_typhoon_crawler():
    """
    执行活跃台风路径数据爬取任务（带日志记录）
    """
    start_time = datetime.now()
    logger.info("开始爬取活跃台风路径数据")

    try:
        await fetch_active_typhoon_task()

        duration = (datetime.now() - start_time).total_seconds()
        async with AsyncSessionLocal() as db:
            log = CrawlerLog(
                task_type="active_typhoon_crawl",
                status="success",
                message=f"活跃台风路径爬取完成 | 耗时:{duration:.1f}秒",
                data_count=0
            )
            db.add(log)
            await db.commit()

        logger.info(f"活跃台风路径爬取完成 | 耗时:{duration:.1f}秒")

    except Exception as e:
        logger.error(f"活跃台风路径爬取失败: {e}", exc_info=True)
        
        try:
            async with AsyncSessionLocal() as db:
                log = CrawlerLog(
                    task_type="active_typhoon_crawl",
                    status="failed",
                    message="活跃台风路径爬取失败",
                    error_message=str(e)
                )
                db.add(log)
                await db.commit()
        except Exception as log_error:
            logger.error(f"记录错误日志失败: {log_error}")
