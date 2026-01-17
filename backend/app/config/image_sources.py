"""
图像数据源配置
参考oceanMonitor项目的数据源设计
"""

# 卫星云图数据源
SATELLITE_SOURCES = {
    "himawari": {
        "name": "向日葵卫星 (Himawari)",
        "provider": "日本气象厅 (JMA)",
        "base_url": "https://www.jma.go.jp/bosai/himawari/data/satimg/",
        "channels": {
            "visible": "可见光",
            "infrared": "红外",
            "water_vapor": "水汽",
            "enhanced_ir": "增强红外"
        },
        "update_interval": 10,  # 分钟
        "resolution": "2km",
        "coverage": "西太平洋"
    },
    "fengyun": {
        "name": "风云卫星 (FY-4A)",
        "provider": "中国气象局 (CMA)",
        "base_url": "http://typhoon.nmc.cn/weatherservice/satellite/",
        "channels": {
            "visible": "可见光",
            "infrared": "红外",
            "water_vapor": "水汽"
        },
        "update_interval": 15,
        "resolution": "4km",
        "coverage": "东亚及西太平洋"
    },
    "goes": {
        "name": "GOES卫星",
        "provider": "美国NOAA",
        "base_url": "https://cdn.star.nesdis.noaa.gov/GOES16/",
        "channels": {
            "visible": "可见光",
            "infrared": "红外",
            "water_vapor": "水汽"
        },
        "update_interval": 10,
        "resolution": "2km",
        "coverage": "东太平洋及大西洋"
    }
}

# 数值预报图像源
NWP_SOURCES = {
    "gfs": {
        "name": "GFS全球预报系统",
        "provider": "美国NOAA",
        "base_url": "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl",
        "products": ["wind", "pressure", "temperature", "precipitation"],
        "forecast_hours": [0, 6, 12, 24, 48, 72, 96, 120],
        "update_interval": 360  # 6小时
    },
    "ecmwf": {
        "name": "ECMWF欧洲中期预报",
        "provider": "ECMWF",
        "base_url": "https://charts.ecmwf.int/",
        "products": ["wind", "pressure", "geopotential"],
        "forecast_hours": [0, 12, 24, 48, 72, 96, 120, 144, 168],
        "update_interval": 720  # 12小时
    },
    "cma": {
        "name": "CMA数值预报",
        "provider": "中国气象局",
        "base_url": "http://typhoon.nmc.cn/weatherservice/nwp/",
        "products": ["wind", "pressure", "track"],
        "forecast_hours": [0, 12, 24, 48, 72, 96, 120],
        "update_interval": 360
    }
}

# 环境要素分析图源
ENVIRONMENT_SOURCES = {
    "sst": {
        "name": "海表温度",
        "provider": "NOAA/CMA",
        "urls": {
            "noaa": "https://www.ospo.noaa.gov/data/sst/contour/",
            "cma": "http://typhoon.nmc.cn/weatherservice/ocean/sst/"
        },
        "update_interval": 1440  # 24小时
    },
    "wave": {
        "name": "海浪高度",
        "provider": "NOAA",
        "url": "https://polar.ncep.noaa.gov/waves/",
        "update_interval": 360
    },
    "wind_shear": {
        "name": "风切变",
        "provider": "CIMSS",
        "url": "http://tropic.ssec.wisc.edu/real-time/windshear/",
        "update_interval": 360
    },
    "vorticity": {
        "name": "涡度分析",
        "provider": "JMA/CMA",
        "update_interval": 360
    }
}

# 台风路径预报图源
TRACK_FORECAST_SOURCES = {
    "jtwc": {
        "name": "联合台风警报中心",
        "provider": "美国海军",
        "base_url": "https://www.metoc.navy.mil/jtwc/products/",
        "products": ["track_forecast", "intensity_forecast", "wind_radii"],
        "update_interval": 360
    },
    "jma": {
        "name": "日本气象厅",
        "provider": "JMA",
        "base_url": "https://www.jma.go.jp/bosai/map.html",
        "products": ["track_forecast", "probability_circle"],
        "update_interval": 360
    },
    "cma": {
        "name": "中国气象局",
        "provider": "CMA",
        "base_url": "http://typhoon.nmc.cn/weatherservice/typhoon/",
        "products": ["track_forecast", "intensity_forecast"],
        "update_interval": 180  # 3小时
    }
}

# 图像类型分类
IMAGE_CATEGORIES = {
    "satellite": {
        "name": "卫星云图",
        "sources": SATELLITE_SOURCES,
        "priority": 1
    },
    "nwp": {
        "name": "数值预报",
        "sources": NWP_SOURCES,
        "priority": 2
    },
    "environment": {
        "name": "环境要素",
        "sources": ENVIRONMENT_SOURCES,
        "priority": 3
    },
    "track": {
        "name": "路径预报",
        "sources": TRACK_FORECAST_SOURCES,
        "priority": 4
    }
}

