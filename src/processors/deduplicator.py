"""去重模块"""
import pandas as pd
from typing import Tuple, List
from datetime import timedelta
from fuzzywuzzy import fuzz
import hashlib


class Deduplicator:
    """交易去重器"""

    def __init__(
        self,
        time_window_minutes: int = 5,
        similarity_threshold: float = 0.8,
        review_threshold: float = 0.7
    ):
        """
        初始化去重器

        Args:
            time_window_minutes: 时间窗口（分钟）
            similarity_threshold: 高置信度阈值
            review_threshold: 待审核阈值
        """
        self.time_window = timedelta(minutes=time_window_minutes)
        self.similarity_threshold = similarity_threshold
        self.review_threshold = review_threshold

    def deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        执行去重

        Args:
            df: 原始DataFrame

        Returns:
            标记了重复的DataFrame
        """
        df = df.copy()

        # 初始化去重相关字段
        df['is_duplicate'] = False
        df['duplicate_group'] = None
        df['duplicate_confidence'] = 0.0

        # 级别1：同平台相同交易ID去重
        df = self._deduplicate_by_transaction_id(df)

        # 级别2：跨平台模糊去重
        df = self._deduplicate_cross_platform(df)

        return df

    def _deduplicate_by_transaction_id(self, df: pd.DataFrame) -> pd.DataFrame:
        """同平台交易ID去重（强去重）"""
        # 找出重复的交易ID
        duplicates = df[df.duplicated(subset=['transaction_id'], keep='first')]

        if not duplicates.empty:
            df.loc[duplicates.index, 'is_duplicate'] = True
            df.loc[duplicates.index, 'duplicate_confidence'] = 1.0

            # 为每组重复交易分配相同的组ID
            for tid in duplicates['transaction_id'].unique():
                group_id = self._generate_group_id(tid)
                mask = df['transaction_id'] == tid
                df.loc[mask, 'duplicate_group'] = group_id

        return df

    def _deduplicate_cross_platform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        跨平台模糊去重

        策略：
        1. 时间窗口：±5分钟
        2. 金额精确匹配
        3. 描述相似度 >80%
        """
        # 只处理未标记为重复的记录
        candidates = df[~df['is_duplicate']].copy()

        if len(candidates) < 2:
            return df

        # 按时间排序
        candidates = candidates.sort_values('date')

        for i in range(len(candidates)):
            row1 = candidates.iloc[i]

            # 如果已标记为重复，跳过
            if df.loc[row1.name, 'is_duplicate']:
                continue

            # 在时间窗口内查找可能的重复
            for j in range(i + 1, len(candidates)):
                row2 = candidates.iloc[j]

                # 如果已标记为重复，跳过
                if df.loc[row2.name, 'is_duplicate']:
                    continue

                # 计算相似度
                similarity = self._calculate_similarity(row1, row2)

                if similarity >= self.similarity_threshold:
                    # 高置信度：自动标记为重复
                    group_id = self._generate_group_id(f"{row1.name}_{row2.name}")

                    df.loc[row2.name, 'is_duplicate'] = True
                    df.loc[row2.name, 'duplicate_confidence'] = similarity
                    df.loc[row2.name, 'duplicate_group'] = group_id

                    df.loc[row1.name, 'duplicate_group'] = group_id

                elif similarity >= self.review_threshold:
                    # 中等置信度：标记待审核
                    group_id = self._generate_group_id(f"{row1.name}_{row2.name}_review")

                    df.loc[row2.name, 'is_duplicate'] = True
                    df.loc[row2.name, 'duplicate_confidence'] = similarity
                    df.loc[row2.name, 'duplicate_group'] = group_id

                    df.loc[row1.name, 'duplicate_group'] = group_id

        return df

    def _calculate_similarity(self, row1: pd.Series, row2: pd.Series) -> float:
        """
        计算两条交易的相似度

        Args:
            row1: 交易1
            row2: 交易2

        Returns:
            相似度分数（0-1）
        """
        # 1. 时间分数
        time_diff = abs((row1['date'] - row2['date']).total_seconds() / 60)  # 分钟
        if time_diff > self.time_window.total_seconds() / 60:
            return 0.0  # 超出时间窗口，直接返回0

        time_score = max(0, 1 - time_diff / (self.time_window.total_seconds() / 60))

        # 2. 金额分数
        amount_score = 1.0 if abs(row1['amount'] - row2['amount']) < 0.01 else 0.0

        # 3. 描述相似度
        desc1 = str(row1.get('description', ''))
        desc2 = str(row2.get('description', ''))
        desc_similarity = fuzz.ratio(desc1, desc2) / 100.0

        # 4. 商户相似度
        counterparty1 = str(row1.get('counterparty', ''))
        counterparty2 = str(row2.get('counterparty', ''))
        counterparty_similarity = fuzz.ratio(counterparty1, counterparty2) / 100.0

        # 综合得分（加权）
        # 金额必须匹配，否则相似度为0
        if amount_score == 0:
            return 0.0

        # 加权计算
        final_score = (
            time_score * 0.3 +
            amount_score * 0.3 +
            desc_similarity * 0.2 +
            counterparty_similarity * 0.2
        )

        return final_score

    def _generate_group_id(self, seed: str) -> str:
        """生成重复组ID"""
        return hashlib.md5(seed.encode()).hexdigest()[:16]

    def get_duplicate_summary(self, df: pd.DataFrame) -> dict:
        """
        获取去重摘要统计

        Args:
            df: DataFrame

        Returns:
            统计信息字典
        """
        total = len(df)
        duplicates = df['is_duplicate'].sum()
        unique_groups = df['duplicate_group'].nunique()

        high_confidence = len(df[
            (df['is_duplicate']) &
            (df['duplicate_confidence'] >= self.similarity_threshold)
        ])

        needs_review = len(df[
            (df['is_duplicate']) &
            (df['duplicate_confidence'] < self.similarity_threshold) &
            (df['duplicate_confidence'] >= self.review_threshold)
        ])

        return {
            'total_transactions': total,
            'duplicate_count': duplicates,
            'unique_count': total - duplicates,
            'duplicate_groups': unique_groups,
            'high_confidence_duplicates': high_confidence,
            'needs_review': needs_review
        }
