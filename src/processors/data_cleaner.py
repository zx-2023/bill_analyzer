"""数据清洗模块"""
import pandas as pd
import yaml
from typing import List, Dict


class DataCleaner:
    """数据清洗器"""

    def __init__(self, config_path: str = "config/classification_rules.yaml"):
        """初始化数据清洗器"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗数据

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        df = df.copy()

        # 1. 移除无效记录
        df = self._remove_invalid_records(df)

        # 2. 标准化商户名称
        df = self._standardize_counterparty(df)

        # 3. 过滤排除的交易
        df = self._filter_excluded_transactions(df)

        # 4. 处理金额符号（确保支出为负，收入为正）
        df = self._normalize_amount_sign(df)

        return df

    def _remove_invalid_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """移除无效记录"""
        # 移除金额为0的记录
        df = df[df['amount'] != 0]

        # 移除日期为空的记录
        df = df[pd.notna(df['date'])]

        # 移除交易ID为空的记录
        df = df[pd.notna(df['transaction_id'])]

        return df.reset_index(drop=True)

    def _standardize_counterparty(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化商户名称

        去除公司后缀、括号内容等
        """
        if 'counterparty' not in df.columns:
            return df

        def clean_name(name):
            if pd.isna(name):
                return name

            name = str(name)

            # 去除常见公司后缀
            suffixes = [
                '有限公司', '股份有限公司', '(中国)', '（中国）',
                'Co.,Ltd', 'Inc.', 'Corp.', 'LLC',
                '专卖店', '旗舰店', '官方旗舰店'
            ]

            for suffix in suffixes:
                name = name.replace(suffix, '')

            # 去除括号及其内容
            import re
            name = re.sub(r'\([^)]*\)', '', name)
            name = re.sub(r'\（[^）]*\）', '', name)

            # 去除前后空格
            name = name.strip()

            return name

        df['counterparty'] = df['counterparty'].apply(clean_name)

        return df

    def _filter_excluded_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤排除的交易类型

        根据配置文件排除规则
        """
        exclude_config = self.config.get('exclude_transactions', {})
        exclude_keywords = exclude_config.get('keywords', [])

        if not exclude_keywords:
            return df

        # 检查description字段
        if 'description' in df.columns:
            mask = df['description'].apply(
                lambda x: not any(keyword in str(x) for keyword in exclude_keywords)
            )
            df = df[mask]

        return df.reset_index(drop=True)

    def _normalize_amount_sign(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化金额符号

        确保：
        - 支出（expense）为正数（后续处理时会转负）
        - 收入（income）为正数
        """
        if 'amount' not in df.columns or 'type' not in df.columns:
            return df

        # 确保金额都是绝对值（符号由type字段决定）
        df['amount'] = df['amount'].abs()

        return df
