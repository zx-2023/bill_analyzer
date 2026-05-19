"""账单解析器基类"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd
import yaml
import os


class BaseParser(ABC):
    """账单解析器抽象基类"""

    PLATFORM_NAME: str = ""  # 平台名称（子类必须定义）

    def __init__(self, config_path: str = "config/platform_config.yaml"):
        """
        初始化解析器

        Args:
            config_path: 平台配置文件路径
        """
        self.config = self._load_config(config_path)
        self.platform_config = self.config['platforms'].get(self.PLATFORM_NAME, {})
        self.common_config = self.config.get('common', {})

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @abstractmethod
    def parse(self, file_path: str) -> pd.DataFrame:
        """
        解析账单文件

        Args:
            file_path: 账单文件路径

        Returns:
            标准化的DataFrame
        """
        pass

    @abstractmethod
    def detect_format(self, file_path: str) -> bool:
        """
        检测文件是否为该平台格式

        Args:
            file_path: 文件路径

        Returns:
            是否匹配该平台格式
        """
        pass

    def read_file(self, file_path: str) -> pd.DataFrame:
        """
        读取文件

        Args:
            file_path: 文件路径

        Returns:
            原始DataFrame
        """
        encoding = self.platform_config.get('encoding', 'utf-8')
        skip_rows = self.platform_config.get('skip_rows', 0)
        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            if file_ext == '.csv':
                return pd.read_csv(file_path, encoding=encoding, skiprows=skip_rows)
            elif file_ext in ['.xlsx', '.xls']:
                return pd.read_excel(file_path, skiprows=skip_rows)
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")
        except UnicodeDecodeError:
            # 尝试其他编码
            alt_encodings = ['gbk', 'utf-8', 'gb2312', 'gb18030']
            for enc in alt_encodings:
                try:
                    if file_ext == '.csv':
                        return pd.read_csv(file_path, encoding=enc, skiprows=skip_rows)
                except:
                    continue
            raise ValueError(f"无法读取文件，编码错误")

    def standardize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化DataFrame字段

        Args:
            df: 原始DataFrame

        Returns:
            标准化后的DataFrame
        """
        # 字段映射
        column_mapping = self.platform_config.get('column_mapping', {})
        df_standard = df.rename(columns=column_mapping)

        # 类型映射
        type_mapping = self.platform_config.get('type_mapping', {})
        if 'type' in df_standard.columns and type_mapping:
            df_standard['type'] = df_standard['type'].map(
                lambda x: type_mapping.get(x, x)
            )

        # 添加平台标识
        df_standard['platform'] = self.PLATFORM_NAME

        # 清洗金额
        if 'amount' in df_standard.columns:
            df_standard['amount'] = self._clean_amount(df_standard['amount'])

        # 解析日期
        if 'date' in df_standard.columns:
            df_standard['date'] = self._parse_date(df_standard['date'])

        # 生成唯一交易ID
        df_standard['transaction_id'] = self._generate_transaction_id(df_standard)

        # 过滤无效状态
        valid_statuses = self.platform_config.get('valid_statuses', [])
        if valid_statuses and 'status' in df_standard.columns:
            df_standard = df_standard[df_standard['status'].isin(valid_statuses)]

        return df_standard

    def _clean_amount(self, amount_series: pd.Series) -> pd.Series:
        """清洗金额数据"""
        remove_chars = self.common_config.get('amount_cleaning', {}).get('remove_chars', [])

        def clean_value(val):
            if pd.isna(val):
                return 0.0

            # 转换为字符串
            val_str = str(val)

            # 移除特殊字符
            for char in remove_chars:
                val_str = val_str.replace(char, '')

            try:
                return float(val_str)
            except:
                return 0.0

        return amount_series.apply(clean_value)

    def _parse_date(self, date_series: pd.Series) -> pd.Series:
        """解析日期"""
        date_formats = self.common_config.get('date_formats', [])
        primary_format = self.platform_config.get('date_format', '%Y-%m-%d %H:%M:%S')

        # 先尝试主格式
        try:
            return pd.to_datetime(date_series, format=primary_format)
        except:
            pass

        # 尝试备选格式
        for fmt in date_formats:
            try:
                return pd.to_datetime(date_series, format=fmt)
            except:
                continue

        # 最后让pandas自动推断
        try:
            return pd.to_datetime(date_series)
        except:
            return date_series

    def _generate_transaction_id(self, df: pd.DataFrame) -> pd.Series:
        """
        生成唯一交易ID

        Args:
            df: DataFrame

        Returns:
            交易ID Series
        """
        # 如果原始数据有交易ID，直接使用
        if 'transaction_id' in df.columns:
            return df['transaction_id'].astype(str)

        # 否则生成：平台_日期时间戳_索引
        return df.apply(
            lambda row: f"{self.PLATFORM_NAME}_{row.name}_{hash(str(row.to_dict())) % 1000000}",
            axis=1
        )

    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        验证数据完整性

        Args:
            df: DataFrame

        Returns:
            是否有效
        """
        required_columns = ['transaction_id', 'date', 'amount', 'platform']

        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必要字段: {col}")

        # 检查空值
        if df['transaction_id'].isna().any():
            raise ValueError("存在空的交易ID")

        if df['date'].isna().any():
            raise ValueError("存在空的日期")

        return True

    def to_dict_list(self, df: pd.DataFrame) -> List[Dict]:
        """
        将DataFrame转换为字典列表

        Args:
            df: DataFrame

        Returns:
            字典列表
        """
        return df.to_dict('records')
