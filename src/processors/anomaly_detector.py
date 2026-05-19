"""异常检测模块"""
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import numpy as np


class AnomalyDetector:
    """异常检测器 - 识别大额支出、异常模式等"""

    def __init__(
        self,
        large_amount_percentile: float = 0.95,
        unusual_merchant_threshold: int = 1,
        min_transactions_for_stats: int = 10
    ):
        """
        初始化异常检测器

        Args:
            large_amount_percentile: 大额支出百分位数（超过此百分位的为大额）
            unusual_merchant_threshold: 异常商户阈值（交易次数少于此值视为异常）
            min_transactions_for_stats: 最小交易数量要求
        """
        self.large_amount_percentile = large_amount_percentile
        self.unusual_merchant_threshold = unusual_merchant_threshold
        self.min_transactions_for_stats = min_transactions_for_stats

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        执行异常检测

        Args:
            df: 交易DataFrame

        Returns:
            标记了异常的DataFrame
        """
        df = df.copy()

        # 初始化异常检测字段
        df['is_anomaly'] = False
        df['anomaly_type'] = None
        df['anomaly_score'] = 0.0
        df['anomaly_reason'] = None
        
        if df.empty or 'type' not in df.columns:
            return df

        # 只对支出进行异常检测
        expense_df = df[df['type'] == 'expense'].copy()

        if len(expense_df) < self.min_transactions_for_stats:
            return df  # 数据量太少，不进行检测

        # 1. 检测大额支出
        df = self._detect_large_amounts(df, expense_df)

        # 2. 检测异常商户
        df = self._detect_unusual_merchants(df, expense_df)

        # 3. 检测高频异常
        df = self._detect_high_frequency(df, expense_df)

        return df

    def _detect_large_amounts(self, df: pd.DataFrame, expense_df: pd.DataFrame) -> pd.DataFrame:
        """
        检测大额支出异常

        使用百分位数方法：超过95%分位数的视为大额
        """
        threshold = expense_df['amount'].quantile(self.large_amount_percentile)

        # 标记大额支出
        large_amount_mask = (df['type'] == 'expense') & (df['amount'] > threshold)

        df.loc[large_amount_mask, 'is_anomaly'] = True
        df.loc[large_amount_mask, 'anomaly_type'] = 'large_amount'

        # 计算异常分数（超出程度）
        df.loc[large_amount_mask, 'anomaly_score'] = df.loc[large_amount_mask, 'amount'] / threshold

        df.loc[large_amount_mask, 'anomaly_reason'] = df.loc[large_amount_mask].apply(
            lambda row: f"金额 ¥{row['amount']:.2f} 超过95%分位数阈值 ¥{threshold:.2f}",
            axis=1
        )

        return df

    def _detect_unusual_merchants(self, df: pd.DataFrame, expense_df: pd.DataFrame) -> pd.DataFrame:
        """
        检测异常商户

        很少交易的商户出现大额支出可能是异常
        """
        # 统计每个商户的交易次数
        merchant_counts = expense_df['counterparty'].value_counts()

        # 找出只交易过1-2次的商户
        rare_merchants = merchant_counts[merchant_counts <= self.unusual_merchant_threshold].index

        # 对于这些商户，如果金额较大，标记为异常
        median_amount = expense_df['amount'].median()

        unusual_mask = (
            (df['counterparty'].isin(rare_merchants)) &
            (df['amount'] > median_amount * 2) &
            (df['type'] == 'expense')
        )

        df.loc[unusual_mask, 'is_anomaly'] = True
        df.loc[unusual_mask, 'anomaly_type'] = 'unusual_merchant'
        df.loc[unusual_mask, 'anomaly_score'] = 0.7

        df.loc[unusual_mask, 'anomaly_reason'] = df.loc[unusual_mask].apply(
            lambda row: f"陌生商户 '{row['counterparty']}' 出现较大金额 ¥{row['amount']:.2f}",
            axis=1
        )

        return df

    def _detect_high_frequency(self, df: pd.DataFrame, expense_df: pd.DataFrame) -> pd.DataFrame:
        """
        检测高频异常

        同一天内对同一商户多次大额支出可能异常
        """
        # 按日期和商户分组
        df['date_only'] = pd.to_datetime(df['date']).dt.date

        daily_merchant_stats = expense_df.groupby(
            [expense_df['date'].dt.date, 'counterparty']
        ).agg({
            'amount': ['count', 'sum', 'mean']
        }).reset_index()

        # 找出同一天对同一商户多次交易且总额较大的情况
        high_freq_threshold = 3  # 一天内超过3次
        high_amount_threshold = expense_df['amount'].quantile(0.9)

        suspicious_patterns = daily_merchant_stats[
            (daily_merchant_stats[('amount', 'count')] >= high_freq_threshold) &
            (daily_merchant_stats[('amount', 'sum')] > high_amount_threshold)
        ]

        if not suspicious_patterns.empty:
            for _, pattern in suspicious_patterns.iterrows():
                date = pattern[('date', '')]
                merchant = pattern[('counterparty', '')]

                high_freq_mask = (
                    (df['date_only'] == date) &
                    (df['counterparty'] == merchant) &
                    (df['type'] == 'expense')
                )

                df.loc[high_freq_mask, 'is_anomaly'] = True
                df.loc[high_freq_mask, 'anomaly_type'] = 'high_frequency'
                df.loc[high_freq_mask, 'anomaly_score'] = 0.6

                count = pattern[('amount', 'count')]
                total = pattern[('amount', 'sum')]
                df.loc[high_freq_mask, 'anomaly_reason'] = f"同一天对 '{merchant}' 有{count}笔交易，总计 ¥{total:.2f}"

        df = df.drop(columns=['date_only'])

        return df

    def get_anomaly_summary(self, df: pd.DataFrame) -> Dict:
        """
        获取异常检测摘要

        Args:
            df: DataFrame

        Returns:
            异常统计信息
        """
        anomalies = df[df['is_anomaly'] == True]

        if anomalies.empty:
            return {
                'total_anomalies': 0,
                'by_type': {},
                'total_amount': 0.0
            }

        summary = {
            'total_anomalies': len(anomalies),
            'by_type': anomalies['anomaly_type'].value_counts().to_dict(),
            'total_amount': anomalies['amount'].sum(),
            'avg_anomaly_score': anomalies['anomaly_score'].mean()
        }

        return summary
