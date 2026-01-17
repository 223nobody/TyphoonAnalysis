"""
图像爬虫服务
参考oceanMonitor的爬虫设计，实现多源图像数据爬取
"""
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
import aiohttp
from pathlib import Path

from app.config.image_sources import (
    SATELLITE_SOURCES,
    NWP_SOURCES,
    ENVIRONMENT_SOURCES,
    TRACK_FORECAST_SOURCES
)

logger = logging.getLogger(__name__)


class ImageCrawler:
    """图像爬虫基类"""
    
    def __init__(self, save_dir: str = "data/images"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()
    
    async def download_image(
        self,
        url: str,
        save_path: Path,
        retry: int = 3
    ) -> bool:
        """
        下载单张图像
        
        Args:
            url: 图像URL
            save_path: 保存路径
            retry: 重试次数
        
        Returns:
            是否下载成功
        """
        for attempt in range(retry):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        save_path.parent.mkdir(parents=True, exist_ok=True)
                        save_path.write_bytes(content)
                        logger.info(f"✅ 下载成功: {url} -> {save_path}")
                        return True
                    else:
                        logger.warning(f"⚠️ HTTP {response.status}: {url}")
            except Exception as e:
                logger.error(f"❌ 下载失败 (尝试 {attempt + 1}/{retry}): {url} - {e}")
                if attempt < retry - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
        
        return False
    
    async def batch_download(
        self,
        urls: List[str],
        save_dir: Path,
        max_concurrent: int = 5
    ) -> Dict[str, bool]:
        """
        批量下载图像（并发控制）
        
        Args:
            urls: 图像URL列表
            save_dir: 保存目录
            max_concurrent: 最大并发数
        
        Returns:
            下载结果字典 {url: success}
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}
        
        async def download_with_semaphore(url: str, idx: int):
            async with semaphore:
                filename = f"image_{idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                save_path = save_dir / filename
                success = await self.download_image(url, save_path)
                results[url] = success
        
        tasks = [download_with_semaphore(url, i) for i, url in enumerate(urls)]
        await asyncio.gather(*tasks)
        
        return results


class SatelliteCrawler(ImageCrawler):
    """卫星云图爬虫"""
    
    async def crawl_himawari(self, typhoon_id: str) -> List[str]:
        """
        爬取向日葵卫星云图
        
        Args:
            typhoon_id: 台风ID
        
        Returns:
            下载的图像路径列表
        """
        logger.info(f"开始爬取向日葵卫星云图: {typhoon_id}")
        source = SATELLITE_SOURCES["himawari"]
        save_dir = self.save_dir / "satellite" / "himawari" / typhoon_id
        
        # 构建图像URL列表（示例）
        urls = []
        for channel in source["channels"].keys():
            # 实际URL需要根据JMA的API格式构建
            url = f"{source['base_url']}{channel}/latest.jpg"
            urls.append(url)
        
        # 批量下载
        results = await self.batch_download(urls, save_dir)
        
        # 返回成功下载的图像路径
        downloaded = [
            str(save_dir / f"image_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            for i, (url, success) in enumerate(results.items())
            if success
        ]
        
        logger.info(f"✅ 向日葵卫星云图爬取完成: {len(downloaded)}/{len(urls)}")
        return downloaded
    
    async def crawl_fengyun(self, typhoon_id: str) -> List[str]:
        """
        爬取风云卫星云图
        
        Args:
            typhoon_id: 台风ID
        
        Returns:
            下载的图像路径列表
        """
        logger.info(f"开始爬取风云卫星云图: {typhoon_id}")
        source = SATELLITE_SOURCES["fengyun"]
        save_dir = self.save_dir / "satellite" / "fengyun" / typhoon_id
        
        # 构建CMA台风云图URL
        urls = []
        base_url = "http://typhoon.nmc.cn/weatherservice/satellite"
        
        # 获取最新的卫星云图
        for channel in ["visible", "infrared", "water_vapor"]:
            url = f"{base_url}/{typhoon_id}/{channel}.jpg"
            urls.append(url)
        
        results = await self.batch_download(urls, save_dir)
        
        downloaded = [
            str(save_dir / f"image_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            for i, (url, success) in enumerate(results.items())
            if success
        ]
        
        logger.info(f"✅ 风云卫星云图爬取完成: {len(downloaded)}/{len(urls)}")
        return downloaded


class NWPCrawler(ImageCrawler):
    """数值预报图像爬虫"""
    
    async def crawl_gfs(self, typhoon_id: str, forecast_hours: List[int]) -> List[str]:
        """
        爬取GFS数值预报图
        
        Args:
            typhoon_id: 台风ID
            forecast_hours: 预报时效列表
        
        Returns:
            下载的图像路径列表
        """
        logger.info(f"开始爬取GFS数值预报图: {typhoon_id}")
        source = NWP_SOURCES["gfs"]
        save_dir = self.save_dir / "nwp" / "gfs" / typhoon_id
        
        urls = []
        # 构建GFS预报图URL（示例）
        for hour in forecast_hours:
            for product in source["products"]:
                url = f"{source['base_url']}?product={product}&hour={hour}"
                urls.append(url)
        
        results = await self.batch_download(urls, save_dir)
        
        downloaded = [
            str(save_dir / f"image_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            for i, (url, success) in enumerate(results.items())
            if success
        ]
        
        logger.info(f"✅ GFS数值预报图爬取完成: {len(downloaded)}/{len(urls)}")
        return downloaded


class EnvironmentCrawler(ImageCrawler):
    """环境要素图像爬虫"""
    
    async def crawl_sst(self, region: str = "western_pacific") -> List[str]:
        """
        爬取海表温度图
        
        Args:
            region: 区域名称
        
        Returns:
            下载的图像路径列表
        """
        logger.info(f"开始爬取海表温度图: {region}")
        source = ENVIRONMENT_SOURCES["sst"]
        save_dir = self.save_dir / "environment" / "sst" / region
        
        urls = [
            source["urls"]["noaa"] + "latest.jpg",
            source["urls"]["cma"] + "latest.jpg"
        ]
        
        results = await self.batch_download(urls, save_dir)
        
        downloaded = [
            str(save_dir / f"image_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            for i, (url, success) in enumerate(results.items())
            if success
        ]
        
        logger.info(f"✅ 海表温度图爬取完成: {len(downloaded)}/{len(urls)}")
        return downloaded

