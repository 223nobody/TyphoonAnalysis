"""
CSV数据加载器

用于从CSV文件加载台风路径数据
"""
import logging
from typing import List, Optional, Dict
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TyphoonPathData:
    """台风路径数据类（不依赖SQLAlchemy模型）"""
    typhoon_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    center_pressure: Optional[float] = None
    max_wind_speed: Optional[float] = None
    moving_speed: Optional[float] = None
    moving_direction: Optional[str] = None
    intensity: Optional[str] = None
    typhoon_name: Optional[str] = None
    typhoon_name_en: Optional[str] = None
    typhoon_name_ch: Optional[str] = None


class CSVDataLoader:
    """
    CSV数据加载器

    从CSV文件加载台风路径数据并转换为TyphoonPath对象
    """

    def __init__(
        self,
        csv_path: str = None,
        encoding: str = 'utf-8'
    ):
        """
        初始化CSV数据加载器

        Args:
            csv_path: CSV文件路径，默认为项目数据目录下的typhoon_paths_1966_2026.csv
            encoding: 文件编码
        """
        if csv_path is None:
            # 从当前文件位置向上找到backend目录，然后找到data/csv目录
            current_file = Path(__file__)
            backend_dir = current_file.parent.parent.parent.parent.parent
            csv_path = backend_dir / "data" / "csv" / "typhoon_paths_1966_2026.csv"

        self.csv_path = Path(csv_path)
        self.encoding = encoding
        self._data_cache: Optional[pd.DataFrame] = None

        logger.info(f"CSV数据加载器初始化完成，数据源: {self.csv_path}")

    def load_all(self) -> List[TyphoonPathData]:
        """
        加载所有台风路径数据

        Returns:
            TyphoonPathData对象列表
        """
        try:
            df = self._load_csv()
            return self._dataframe_to_paths(df)
        except Exception as e:
            logger.error(f"加载CSV数据失败: {e}")
            raise

    def load_by_typhoon_id(self, typhoon_id: str) -> List[TyphoonPathData]:
        """
        按台风编号加载数据

        Args:
            typhoon_id: 台风编号

        Returns:
            指定台风的路径数据列表
        """
        try:
            df = self._load_csv()
            filtered_df = df[df['ty_code'] == typhoon_id]
            return self._dataframe_to_paths(filtered_df)
        except Exception as e:
            logger.error(f"加载台风 {typhoon_id} 数据失败: {e}")
            raise

    def load_by_year(self, year: int) -> List[TyphoonPathData]:
        """
        按年份加载数据

        Args:
            year: 年份

        Returns:
            指定年份的台风路径数据列表
        """
        try:
            df = self._load_csv()
            df['year'] = pd.to_datetime(df['timestamp']).dt.year
            filtered_df = df[df['year'] == year]
            return self._dataframe_to_paths(filtered_df)
        except Exception as e:
            logger.error(f"加载 {year} 年数据失败: {e}")
            raise

    def load_by_year_range(self, start_year: int, end_year: int) -> List[TyphoonPathData]:
        """
        按年份范围加载数据

        Args:
            start_year: 起始年份
            end_year: 结束年份

        Returns:
            指定年份范围的台风路径数据列表
        """
        try:
            df = self._load_csv()
            df['year'] = pd.to_datetime(df['timestamp']).dt.year
            filtered_df = df[(df['year'] >= start_year) & (df['year'] <= end_year)]
            return self._dataframe_to_paths(filtered_df)
        except Exception as e:
            logger.error(f"加载 {start_year}-{end_year} 年数据失败: {e}")
            raise

    def get_typhoon_list(self) -> List[Dict]:
        """
        获取所有台风的基本信息列表

        Returns:
            台风信息列表，每个元素包含 ty_code, ty_name_en, ty_name_ch
        """
        try:
            df = self._load_csv()
            typhoon_info = df[['ty_code', 'ty_name_en', 'ty_name_ch']].drop_duplicates()
            return typhoon_info.to_dict('records')
        except Exception as e:
            logger.error(f"获取台风列表失败: {e}")
            raise

    def get_statistics(self) -> Dict:
        """
        获取数据集统计信息

        Returns:
            统计信息字典
        """
        try:
            df = self._load_csv()
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            stats = {
                'total_records': len(df),
                'total_typhoons': df['ty_code'].nunique(),
                'date_range': {
                    'start': df['timestamp'].min().strftime('%Y-%m-%d'),
                    'end': df['timestamp'].max().strftime('%Y-%m-%d')
                },
                'years': sorted(df['timestamp'].dt.year.unique().tolist()),
                'intensity_distribution': df['intensity'].value_counts().to_dict()
            }

            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    def _load_csv(self) -> pd.DataFrame:
        """
        加载CSV文件到DataFrame

        Returns:
            数据DataFrame
        """
        if self._data_cache is None:
            if not self.csv_path.exists():
                raise FileNotFoundError(f"CSV文件不存在: {self.csv_path}")

            df = pd.read_csv(self.csv_path, encoding=self.encoding)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['ty_code'] = df['ty_code'].astype(str)  # 确保台风编号为字符串类型

            self._data_cache = df
            logger.info(f"CSV数据加载完成，共 {len(df)} 条记录")

        return self._data_cache.copy()

    def _dataframe_to_paths(self, df: pd.DataFrame) -> List[TyphoonPathData]:
        """
        将DataFrame转换为TyphoonPathData对象列表

        Args:
            df: 数据DataFrame

        Returns:
            TyphoonPathData对象列表
        """
        paths = []

        for _, row in df.iterrows():
            try:
                path = TyphoonPathData(
                    typhoon_id=str(row['ty_code']),
                    timestamp=row['timestamp'],
                    latitude=float(row['latitude']),
                    longitude=float(row['longitude']),
                    center_pressure=self._parse_float(row['center_pressure']),
                    max_wind_speed=self._parse_float(row['max_wind_speed']),
                    moving_speed=self._parse_float(row['moving_speed']),
                    moving_direction=str(row['moving_direction']).strip() if pd.notna(row['moving_direction']) else None,
                    intensity=str(row['intensity']).strip() if pd.notna(row['intensity']) else None,
                    typhoon_name_en=str(row['ty_name_en']).strip() if pd.notna(row['ty_name_en']) else None,
                    typhoon_name_ch=str(row['ty_name_ch']).strip() if pd.notna(row['ty_name_ch']) else None
                )
                paths.append(path)
            except Exception as e:
                logger.warning(f"解析数据行失败: {e}, 行数据: {row}")
                continue

        logger.info(f"转换完成，生成 {len(paths)} 个TyphoonPathData对象")
        return paths

    def _parse_float(self, value) -> Optional[float]:
        """
        解析浮点数值

        Args:
            value: 输入值

        Returns:
            浮点数或None
        """
        if pd.isna(value) or value == '' or value == '        ':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def clear_cache(self):
        """清除数据缓存"""
        self._data_cache = None
        logger.info("数据缓存已清除")
