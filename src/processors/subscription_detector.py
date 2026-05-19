"""订阅识别模块 - 识别定期扣款模式"""
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import timedelta
from collections import defaultdict
import hashlib


class SubscriptionDetector:
    """订阅扣款检测器"""

    def __init__(
        self,
        min_occurrences: int = 3,
        amount_tolerance: float = 0.1,
        day_tolerance: int = 3
    ):
        """
        初始化订阅检测器

        Args:
            min_occurrences: 最少出现次数（至少3次才识别为订阅）
            amount_tolerance: 金额容差（10%以内波动视为同一订阅）
            day_tolerance: 日期容差（±3天内视为同一周期）
        """
        self.min_occurrences = min_occurrences
        self.amount_tolerance = amount_tolerance
        self.day_tolerance = day_tolerance

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        检测订阅模式

        Args:
            df: 交易DataFrame

        Returns:
            标记了订阅的DataFrame
        """
        df = df.copy()

        # 初始化订阅字段
        df['is_subscription'] = False
        df['subscription_group'] = None
        df['subscription_name'] = None
        df['subscription_cycle'] = None
        df['subscription_confidence'] = 0.0
        
        if df.empty or 'type' not in df.columns:
            return df

        # 只检测支出
        expense_df = df[df['type'] == 'expense'].copy()

        if len(expense_df) < self.min_occurrences:
            return df

        # 按商户分组检测
        for merchant, group in expense_df.groupby('counterparty'):
            if len(group) < self.min_occurrences:
                continue

            # 检测该商户是否有订阅模式
            subscriptions = self._detect_merchant_subscriptions(group)

            # 标记订阅
            for sub in subscriptions:
                indices = sub['indices']
                group_id = sub['group_id']
                cycle = sub['cycle']
                confidence = sub['confidence']

                df.loc[indices, 'is_subscription'] = True
                df.loc[indices, 'subscription_group'] = group_id
                df.loc[indices, 'subscription_name'] = merchant
                df.loc[indices, 'subscription_cycle'] = cycle
                df.loc[indices, 'subscription_confidence'] = confidence

        return df

    def _detect_merchant_subscriptions(self, group: pd.DataFrame) -> List[Dict]:
        """
        检测单个商户的订阅模式

        Args:
            group: 同一商户的交易记录

        Returns:
            订阅模式列表
        """
        subscriptions = []

        # 按金额聚类
        amount_clusters = self._cluster_by_amount(group)

        for cluster in amount_clusters:
            if len(cluster) < self.min_occurrences:
                continue

            # 检测时间规律性
            cycle, confidence = self._detect_time_pattern(cluster)

            if cycle and confidence > 0.6:
                subscription = {
                    'indices': cluster.index.tolist(),
                    'group_id': self._generate_group_id(cluster),
                    'cycle': cycle,
                    'confidence': confidence,
                    'typical_amount': cluster['amount'].median()
                }
                subscriptions.append(subscription)

        return subscriptions

    def _cluster_by_amount(self, group: pd.DataFrame) -> List[pd.DataFrame]:
        """
        按金额聚类

        相似金额的交易聚为一类
        """
        clusters = []
        sorted_group = group.sort_values('amount')

        current_cluster = []
        last_amount = None

        for idx, row in sorted_group.iterrows():
            amount = row['amount']

            if last_amount is None:
                current_cluster.append(idx)
                last_amount = amount
            else:
                # 判断金额是否在容差范围内
                diff_ratio = abs(amount - last_amount) / last_amount
                if diff_ratio <= self.amount_tolerance:
                    current_cluster.append(idx)
                else:
                    # 保存当前聚类
                    if len(current_cluster) >= self.min_occurrences:
                        clusters.append(group.loc[current_cluster])
                    # 开始新聚类
                    current_cluster = [idx]
                    last_amount = amount

        # 保存最后一个聚类
        if len(current_cluster) >= self.min_occurrences:
            clusters.append(group.loc[current_cluster])

        return clusters

    def _detect_time_pattern(self, cluster: pd.DataFrame) -> tuple:
        """
        检测时间规律性

        Returns:
            (周期类型, 置信度)
        """
        dates = pd.to_datetime(cluster['date']).sort_values()

        if len(dates) < 2:
            return None, 0.0

        # 计算相邻日期间隔
        intervals = [(dates.iloc[i+1] - dates.iloc[i]).days for i in range(len(dates)-1)]

        if not intervals:
            return None, 0.0

        avg_interval = np.mean(intervals)
        std_interval = np.std(intervals)

        # 判断周期类型
        cycle = None
        confidence = 0.0

        # 每月（28-31天）
        if 25 <= avg_interval <= 35:
            cycle = 'monthly'
            confidence = self._calculate_confidence(avg_interval, std_interval, 30)

        # 每年（360-370天）
        elif 360 <= avg_interval <= 370:
            cycle = 'yearly'
            confidence = self._calculate_confidence(avg_interval, std_interval, 365)

        # 每周（6-8天）
        elif 6 <= avg_interval <= 8:
            cycle = 'weekly'
            confidence = self._calculate_confidence(avg_interval, std_interval, 7)

        # 每两周（13-15天）
        elif 13 <= avg_interval <= 15:
            cycle = 'biweekly'
            confidence = self._calculate_confidence(avg_interval, std_interval, 14)

        # 每季度（85-95天）
        elif 85 <= avg_interval <= 95:
            cycle = 'quarterly'
            confidence = self._calculate_confidence(avg_interval, std_interval, 90)

        return cycle, confidence

    def _calculate_confidence(self, avg_interval: float, std_interval: float, expected_interval: int) -> float:
        """
        计算订阅识别置信度

        Args:
            avg_interval: 平均间隔
            std_interval: 间隔标准差
            expected_interval: 期望间隔

        Returns:
            置信度 (0-1)
        """
        # 基于标准差的置信度
        if std_interval == 0:
            variability_score = 1.0
        else:
            variability_score = max(0, 1 - (std_interval / expected_interval))

        # 基于平均值偏差的置信度
        deviation = abs(avg_interval - expected_interval) / expected_interval
        deviation_score = max(0, 1 - deviation)

        # 综合置信度
        confidence = (variability_score * 0.7 + deviation_score * 0.3)

        return min(confidence, 1.0)

    def _generate_group_id(self, cluster: pd.DataFrame) -> str:
        """生成订阅组ID"""
        merchant = cluster['counterparty'].iloc[0]
        amount = cluster['amount'].median()
        seed = f"{merchant}_{amount}"
        return hashlib.md5(seed.encode()).hexdigest()[:16]

    def get_subscription_summary(self, df: pd.DataFrame) -> Dict:
        """
        获取订阅摘要

        Args:
            df: DataFrame

        Returns:
            订阅统计信息
        """
        subscriptions = df[df['is_subscription'] == True]

        if subscriptions.empty:
            return {
                'total_subscriptions': 0,
                'by_cycle': {},
                'monthly_cost': 0.0
            }

        # 按订阅组统计
        subscription_groups = subscriptions.groupby('subscription_group').agg({
            'subscription_name': 'first',
            'amount': 'median',
            'subscription_cycle': 'first',
            'date': 'count'
        }).reset_index()

        subscription_groups.columns = ['group_id', 'name', 'amount', 'cycle', 'count']

        # 估算月度成本
        monthly_cost = 0.0
        for _, row in subscription_groups.iterrows():
            amount = row['amount']
            cycle = row['cycle']

            if cycle == 'monthly':
                monthly_cost += amount
            elif cycle == 'yearly':
                monthly_cost += amount / 12
            elif cycle == 'quarterly':
                monthly_cost += amount / 3
            elif cycle == 'weekly':
                monthly_cost += amount * 4.33
            elif cycle == 'biweekly':
                monthly_cost += amount * 2.17

        summary = {
            'total_subscriptions': len(subscription_groups),
            'by_cycle': subscriptions['subscription_cycle'].value_counts().to_dict(),
            'monthly_cost': monthly_cost,
            'subscriptions': subscription_groups.to_dict('records')
        }

        return summary
