"""
台风公报爬虫服务
从中国气象局获取最新的台风公报信息
"""
import http.client
import json
import logging
import time
import ssl  # 新增：导入SSL模块
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class BulletinCrawler:
    """台风公报爬虫"""
    
    def __init__(self):
        self.base_url = "www.nmc.cn"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://typhoon.nmc.cn/'
        }
        self._cached_bulletin = None
        self._cache_time = None
        self._cache_duration = 300  # 缓存5分钟

    def _create_ssl_context(self) -> ssl.SSLContext:
        """创建跳过SSL证书验证的上下文（解决自签名证书问题）"""
        ctx = ssl.create_default_context()
        # 禁用证书验证（仅解决当前自签名证书问题，生产环境建议替换为可信CA证书）
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        logger.warning("已禁用SSL证书验证（仅适配自签名证书场景，生产环境请配置可信CA）")
        return ctx
    
    def get_typhoon_bulletin(self) -> Optional[Dict]:
        """
        获取最新的台风公报信息
        
        Returns:
            Optional[Dict]: 台风公报数据，如果没有活跃台风则返回None
        """
        # 检查缓存
        if self._cached_bulletin and self._cache_time:
            if time.time() - self._cache_time < self._cache_duration:
                logger.debug("使用缓存的台风公报数据")
                return self._cached_bulletin
        
        conn = None
        try:
            # 新增：创建跳过SSL验证的上下文
            ssl_context = self._create_ssl_context()
            # 修改：传入SSL上下文，解决证书验证失败问题
            conn = http.client.HTTPSConnection(
                self.base_url, 
                port=443, 
                timeout=10,
                context=ssl_context  # 核心：传入自定义SSL上下文
            )
            
            # 添加时间戳参数避免缓存
            t = int(time.time() * 1000)
            url = f"/dataservice/typhoon/news.json?v={t}"
            
            logger.info(f"正在获取台风公报: https://{self.base_url}{url}")
            
            conn.request('GET', url, headers=self.headers)
            res = conn.getresponse()
            content = res.read().decode('utf-8')
            
            # 解析JSON
            data = json.loads(content)
            
            if data.get('code') != 0 or data.get('msg') != 'success':
                logger.warning(f"台风公报API返回异常: {data.get('msg')}")
                return None
            
            bulletin_data = data.get('data')
            if not bulletin_data:
                logger.warning("台风公报数据为空")
                return None
            
            # 解析公报内容
            parsed_bulletin = self._parse_bulletin(bulletin_data)
            
            if parsed_bulletin:
                # 更新缓存
                self._cached_bulletin = parsed_bulletin
                self._cache_time = time.time()
                logger.info(f"成功获取台风公报")
            
            return parsed_bulletin
            
        except http.client.HTTPException as e:
            logger.error(f"HTTP请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return None
        except ssl.SSLError as e:
            logger.error(f"SSL证书验证失败: {e}")
            return None
        except Exception as e:
            logger.error(f"获取台风公报失败: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def _parse_bulletin(self, bulletin_data: Dict) -> Optional[Dict]:
        """
        解析台风公报数据
        
        Args:
            bulletin_data: 原始公报数据
            
        Returns:
            Optional[Dict]: 解析后的公报信息
        """
        try:
            list_data = bulletin_data.get('list', [])
            if not list_data:
                return None
            
            # 将列表转换为字典，方便查找
            info_dict = {}
            for item in list_data:
                label = item.get('label', '')
                text = item.get('text', '')
                if label:
                    info_dict[label] = text
            
            # 提取关键信息
            parsed = {
                'release_time': bulletin_data.get('releaseTime'),
                'description': bulletin_data.get('description'),
                'typhoon_name': info_dict.get('命名', ''),
                'typhoon_number': info_dict.get('编号', ''),
                'time': info_dict.get('时间', ''),
                'position': info_dict.get('中心位置', ''),
                'intensity': info_dict.get('强度等级', ''),
                'max_wind': info_dict.get('最大风力', ''),
                'center_pressure': info_dict.get('中心气压', ''),
                'reference_position': info_dict.get('参考位置', ''),
                'wind_circle': info_dict.get('风圈半径', ''),
                'forecast': info_dict.get('预报结论', ''),
                'summary': info_dict.get('摘要', bulletin_data.get('description', ''))
            }
            
            return parsed
            
        except Exception as e:
            logger.error(f"解析台风公报失败: {e}")
            return None


# 创建全局实例
bulletin_crawler = BulletinCrawler()