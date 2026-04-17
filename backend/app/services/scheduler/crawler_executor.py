"""
统一爬虫执行器。
负责当前年份台风同步、活跃台风路径更新，以及活跃台风多机构预报入库。
"""
import logging
from datetime import datetime

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.typhoon import (
    ActiveTyphoonForecast,
    CrawlerLog,
    Typhoon,
    TyphoonPath,
)
from app.services.crawler.active_typhoon_crawler import active_typhoon_crawler
from app.services.crawler.bulletin_crawler import bulletin_crawler
from app.services.crawler.cma_crawler import cma_crawler

logger = logging.getLogger(__name__)


def _get_current_year() -> int:
    return datetime.now().year


def _convert_typhoon_id_to_short(full_id: str) -> str:
    """例如: 202604 -> 2604"""
    full_id = str(full_id)
    if len(full_id) == 6 and full_id.startswith("20"):
        return full_id[2:]
    return full_id


def _convert_typhoon_id_to_full(typhoon_id: str, year: int | None = None) -> str:
    """例如: 2604 -> 202604"""
    typhoon_id = str(typhoon_id)
    if len(typhoon_id) >= 6:
        return typhoon_id

    if len(typhoon_id) == 4:
        if year is None:
            year = 2000 + int(typhoon_id[:2])
        return f"{year}{typhoon_id[-2:]}"

    if year is None:
        year = _get_current_year()
    return f"{year}{typhoon_id.zfill(2)}"


def _match_typhoon_id(source_id: str, target_id: str) -> bool:
    source_id = str(source_id)
    target_id = str(target_id)
    return (
        source_id == target_id
        or _convert_typhoon_id_to_short(source_id) == target_id
        or _convert_typhoon_id_to_short(target_id) == source_id
    )


async def _upsert_typhoon_paths(db, typhoon_id: str, path_points: list[dict]) -> tuple[int, int, int]:
    inserted_count = 0
    updated_count = 0
    failed_count = 0

    for idx, point in enumerate(path_points):
        try:
            timestamp = point.get("timestamp")
            latitude = point.get("latitude")
            longitude = point.get("longitude")

            if not timestamp or latitude is None or longitude is None:
                failed_count += 1
                continue

            existing_query = select(TyphoonPath).where(
                TyphoonPath.typhoon_id == typhoon_id,
                TyphoonPath.timestamp == timestamp,
            )
            existing_result = await db.execute(existing_query)
            existing_path = existing_result.scalar_one_or_none()

            if existing_path:
                existing_path.latitude = float(latitude)
                existing_path.longitude = float(longitude)
                existing_path.center_pressure = point.get("center_pressure")
                existing_path.max_wind_speed = point.get("max_wind_speed")
                existing_path.moving_speed = point.get("moving_speed")
                existing_path.moving_direction = point.get("moving_direction")
                existing_path.intensity = point.get("intensity")
                updated_count += 1
            else:
                db.add(TyphoonPath(
                    typhoon_id=typhoon_id,
                    timestamp=timestamp,
                    latitude=float(latitude),
                    longitude=float(longitude),
                    center_pressure=point.get("center_pressure"),
                    max_wind_speed=point.get("max_wind_speed"),
                    moving_speed=point.get("moving_speed"),
                    moving_direction=point.get("moving_direction"),
                    intensity=point.get("intensity"),
                ))
                inserted_count += 1
        except Exception as e:
            logger.error(f"处理台风 {typhoon_id} 路径点 {idx} 失败: {e}")
            failed_count += 1

    return inserted_count, updated_count, failed_count


async def _sync_typhoon_records(db, typhoons: list[dict], task_name: str) -> dict:
    existing_ids_result = await db.execute(select(Typhoon.typhoon_id))
    existing_ids = set(existing_ids_result.scalars().all())

    new_count = 0
    updated_count = 0
    path_count = 0
    new_typhoon_ids: list[str] = []

    for typhoon_data in typhoons:
        typhoon_id = typhoon_data["typhoon_id"]

        if typhoon_id in existing_ids:
            existing_result = await db.execute(
                select(Typhoon).where(Typhoon.typhoon_id == typhoon_id)
            )
            existing = existing_result.scalar_one_or_none()
            if not existing:
                continue

            changed = False
            for field in ("typhoon_name", "typhoon_name_cn", "year", "status"):
                new_value = typhoon_data.get(field)
                if getattr(existing, field) != new_value:
                    setattr(existing, field, new_value)
                    changed = True
            if changed:
                updated_count += 1
        else:
            db.add(Typhoon(**typhoon_data))
            new_count += 1
            new_typhoon_ids.append(typhoon_id)

    await db.commit()

    for typhoon_id in new_typhoon_ids:
        try:
            paths = await cma_crawler.get_typhoon_path(typhoon_id)
            inserted_count, _, _ = await _upsert_typhoon_paths(db, typhoon_id, paths)
            path_count += inserted_count
        except Exception as e:
            logger.error(f"{task_name}: 抓取台风 {typhoon_id} 历史路径失败: {e}")

    await db.commit()

    return {
        "total": len(typhoons),
        "new_count": new_count,
        "updated_count": updated_count,
        "path_count": path_count,
        "new_typhoon_ids": new_typhoon_ids,
    }


async def _sync_active_typhoon_forecasts(db, active_typhoons: list[Typhoon]) -> dict:
    total_inserted = 0
    total_updated = 0
    total_failed = 0
    total_forecast = 0

    for active_typhoon in active_typhoons:
        typhoon_id = active_typhoon.typhoon_id
        full_typhoon_id = _convert_typhoon_id_to_full(typhoon_id, active_typhoon.year)
        logger.info(f"同步活跃台风 {typhoon_id} 的实时路径与预报，上游编号 {full_typhoon_id}")

        raw_data = active_typhoon_crawler.fetch_active_typhoon_data(full_typhoon_id)
        if not raw_data:
            logger.warning(f"台风 {typhoon_id} 未获取到浙江台风网详情数据")
            continue

        path_points = active_typhoon_crawler.parse_typhoon_path(raw_data)
        typhoon_points = [
            point for point in path_points
            if _match_typhoon_id(point.get("typhoon_id", ""), typhoon_id)
        ]

        if not typhoon_points:
            logger.warning(f"台风 {typhoon_id} 未解析到可入库的活跃路径点")
            continue

        await db.execute(
            delete(ActiveTyphoonForecast).where(ActiveTyphoonForecast.typhoon_id == typhoon_id)
        )

        inserted_count, updated_count, failed_count = await _upsert_typhoon_paths(
            db, typhoon_id, typhoon_points
        )
        forecast_count = 0

        for point in typhoon_points:
            forecast_groups = point.get("forecast", [])
            if not isinstance(forecast_groups, list):
                continue

            for forecast_group in forecast_groups:
                agency = forecast_group.get("tm", "未知")
                forecast_points = forecast_group.get("forecastpoints", [])
                if not isinstance(forecast_points, list):
                    continue

                for fp in forecast_points:
                    forecast_time_str = fp.get("time")
                    if not forecast_time_str:
                        continue

                    fp_lat = active_typhoon_crawler._parse_float(fp.get("lat") or fp.get("latitude"))
                    fp_lon = active_typhoon_crawler._parse_float(fp.get("lng") or fp.get("longitude"))
                    if fp_lat is None or fp_lon is None:
                        continue

                    base_time_str = fp.get("ybsj")
                    base_time = (
                        active_typhoon_crawler._parse_time(str(base_time_str))
                        if base_time_str else point["timestamp"]
                    )

                    db.add(ActiveTyphoonForecast(
                        typhoon_id=typhoon_id,
                        base_time=base_time,
                        forecast_time=active_typhoon_crawler._parse_time(str(forecast_time_str)),
                        forecast_agency=agency,
                        latitude=fp_lat,
                        longitude=fp_lon,
                        center_pressure=active_typhoon_crawler._parse_float(fp.get("pressure")),
                        max_wind_speed=active_typhoon_crawler._parse_float(fp.get("speed")),
                        power_level=active_typhoon_crawler._parse_int(fp.get("power")),
                        intensity=str(fp.get("strong")) if fp.get("strong") else None,
                    ))
                    forecast_count += 1

        total_inserted += inserted_count
        total_updated += updated_count
        total_failed += failed_count
        total_forecast += forecast_count

        logger.info(
            f"台风 {typhoon_id} 处理完成 | 插入:{inserted_count} | 更新:{updated_count} | "
            f"失败:{failed_count} | 预报:{forecast_count}"
        )

    await db.commit()

    return {
        "inserted": total_inserted,
        "updated": total_updated,
        "failed": total_failed,
        "forecast": total_forecast,
    }


async def run_all_crawlers():
    """执行完整抓取流程。"""
    start_time = datetime.now()
    results = {
        "bulletin": "no_data",
        "typhoons": "no_data",
        "active_typhoon": "no_data",
    }

    async with AsyncSessionLocal() as db:
        try:
            try:
                bulletin = bulletin_crawler.get_typhoon_bulletin()
                results["bulletin"] = "success" if bulletin else "no_data"
            except Exception as e:
                results["bulletin"] = "failed"
                logger.error(f"台风公报抓取失败: {e}")

            try:
                typhoons = await cma_crawler.get_typhoons_by_year(_get_current_year())
                if typhoons:
                    sync_result = await _sync_typhoon_records(db, typhoons, "full_crawl")
                    results["typhoons"] = (
                        f"{sync_result['total']}个|新增:{sync_result['new_count']}|"
                        f"更新:{sync_result['updated_count']}"
                    )
            except Exception as e:
                results["typhoons"] = "failed"
                logger.error(f"当前年份台风基础信息同步失败: {e}")

            try:
                active_typhoons_result = await db.execute(
                    select(Typhoon).where(Typhoon.status == 1)
                )
                active_typhoons = active_typhoons_result.scalars().all()
                if active_typhoons:
                    forecast_result = await _sync_active_typhoon_forecasts(db, active_typhoons)
                    results["active_typhoon"] = (
                        f"路径插入:{forecast_result['inserted']}|更新:{forecast_result['updated']}|"
                        f"预报:{forecast_result['forecast']}"
                    )
            except Exception as e:
                results["active_typhoon"] = "failed"
                logger.error(f"活跃台风路径和预报同步失败: {e}")

            duration = (datetime.now() - start_time).total_seconds()
            status = "success" if all(v != "failed" for v in results.values()) else "partial"

            db.add(CrawlerLog(
                task_type="full_crawl",
                status=status,
                message=(
                    f"完整爬取完成 | 公报:{results['bulletin']} | "
                    f"台风:{results['typhoons']} | 活跃:{results['active_typhoon']} | "
                    f"耗时:{duration:.1f}秒"
                ),
                data_count=0,
            ))
            await db.commit()
        except Exception as e:
            logger.error(f"完整爬取任务失败: {e}", exc_info=True)
            db.add(CrawlerLog(
                task_type="full_crawl",
                status="failed",
                message=f"完整爬取失败: {str(e)}",
                error_message=str(e),
            ))
            await db.commit()


async def _run_yearly_sync(year: int, task_type: str) -> dict:
    start_time = datetime.now()
    async with AsyncSessionLocal() as db:
        typhoons = await cma_crawler.get_typhoons_by_year(year)

        if not typhoons:
            db.add(CrawlerLog(
                task_type=task_type,
                status="success",
                message=f"{year}年台风同步完成 | 无新增数据",
                data_count=0,
            ))
            await db.commit()
            return {"total": 0, "new_count": 0, "updated_count": 0, "path_count": 0}

        sync_result = await _sync_typhoon_records(db, typhoons, task_type)
        duration = (datetime.now() - start_time).total_seconds()

        db.add(CrawlerLog(
            task_type=task_type,
            status="success",
            message=(
                f"{year}年台风同步 | 总数:{sync_result['total']} | 新增:{sync_result['new_count']} | "
                f"更新:{sync_result['updated_count']} | 路径:{sync_result['path_count']} | "
                f"耗时:{duration:.1f}秒"
            ),
            data_count=sync_result["total"],
        ))
        await db.commit()
        return sync_result


async def run_typhoons_crawler():
    """定时同步当前年份全部台风，避免只抓活跃台风造成漏数。"""
    try:
        await _run_yearly_sync(_get_current_year(), "typhoons_crawl")
    except Exception as e:
        logger.error(f"当前年份台风同步失败: {e}", exc_info=True)
        async with AsyncSessionLocal() as db:
            db.add(CrawlerLog(
                task_type="typhoons_crawl",
                status="failed",
                message="当前年份台风同步失败",
                error_message=str(e),
            ))
            await db.commit()


async def run_current_year_typhoons_crawler():
    """显式的当前年份补偿任务，供调度器单独调用。"""
    await run_typhoons_crawler()


async def run_typhoons_crawler_by_year(year: int):
    """手动补抓指定年份的全部台风。"""
    try:
        await _run_yearly_sync(year, "typhoons_crawl_by_year")
    except Exception as e:
        logger.error(f"{year}年台风同步失败: {e}", exc_info=True)
        async with AsyncSessionLocal() as db:
            db.add(CrawlerLog(
                task_type="typhoons_crawl_by_year",
                status="failed",
                message=f"{year}年台风同步失败",
                error_message=str(e),
            ))
            await db.commit()


async def fetch_active_typhoon_task():
    """
    同步当前数据库中活跃台风的实时路径与预测路径。
    如果数据库里还没有 active 记录，会先从 CMA 拉一次活跃台风基础信息补齐。
    """
    async with AsyncSessionLocal() as db:
        try:
            active_typhoons_result = await db.execute(
                select(Typhoon).where(Typhoon.status == 1)
            )
            active_typhoons = active_typhoons_result.scalars().all()

            if not active_typhoons:
                logger.info("数据库中没有活跃台风，先尝试从 CMA 同步活跃台风状态")
                active_typhoon_payloads = await cma_crawler.get_active_typhoons()
                if active_typhoon_payloads:
                    await _sync_typhoon_records(db, active_typhoon_payloads, "active_typhoon_prefetch")
                    active_typhoons_result = await db.execute(
                        select(Typhoon).where(Typhoon.status == 1)
                    )
                    active_typhoons = active_typhoons_result.scalars().all()

            if not active_typhoons:
                logger.info("当前没有活跃台风")
                return {"inserted": 0, "updated": 0, "failed": 0, "forecast": 0}

            result = await _sync_active_typhoon_forecasts(db, active_typhoons)
            return result
        except Exception as e:
            logger.error(f"活跃台风抓取任务失败: {e}", exc_info=True)
            await db.rollback()
            raise


async def run_active_typhoon_crawler():
    """定时同步活跃台风实时路径和多机构预测路径。"""
    start_time = datetime.now()
    try:
        result = await fetch_active_typhoon_task()
        duration = (datetime.now() - start_time).total_seconds()

        async with AsyncSessionLocal() as db:
            db.add(CrawlerLog(
                task_type="active_typhoon_crawl",
                status="success",
                message=(
                    f"活跃台风同步完成 | 路径插入:{result['inserted']} | "
                    f"路径更新:{result['updated']} | 预报:{result['forecast']} | "
                    f"耗时:{duration:.1f}秒"
                ),
                data_count=result["forecast"],
            ))
            await db.commit()
    except Exception as e:
        logger.error(f"活跃台风同步失败: {e}", exc_info=True)
        async with AsyncSessionLocal() as db:
            db.add(CrawlerLog(
                task_type="active_typhoon_crawl",
                status="failed",
                message="活跃台风同步失败",
                error_message=str(e),
            ))
            await db.commit()
