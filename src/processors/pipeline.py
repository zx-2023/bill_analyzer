"""完整的数据处理流水线"""
import pandas as pd
from typing import Dict, List
from .data_cleaner import DataCleaner
from .deduplicator import Deduplicator
from .anomaly_detector import AnomalyDetector
from .subscription_detector import SubscriptionDetector
from src.classifiers.hybrid_classifier import HybridClassifier
from src.classifiers.subcategory_classifier import SubcategoryClassifier


class DataProcessingPipeline:
    """数据处理流水线 - 整合所有处理步骤"""

    def __init__(self, use_ai: bool = False):
        """
        初始化处理流水线

        Args:
            use_ai: 是否启用AI分类
        """
        self.cleaner = DataCleaner()
        self.deduplicator = Deduplicator()
        self.primary_classifier = HybridClassifier(use_ai=use_ai)
        self.subcategory_classifier = SubcategoryClassifier()
        self.anomaly_detector = AnomalyDetector()
        self.subscription_detector = SubscriptionDetector()

    def process(
        self,
        df: pd.DataFrame,
        enable_anomaly_detection: bool = True,
        enable_subscription_detection: bool = True
    ) -> Dict:
        """
        执行完整的数据处理流程

        Args:
            df: 原始DataFrame
            enable_anomaly_detection: 是否启用异常检测
            enable_subscription_detection: 是否启用订阅检测

        Returns:
            处理结果字典，包含处理后的DataFrame和统计信息
        """
        result = {
            'df': df.copy(),
            'stats': {},
            'warnings': [],
            'errors': []
        }

        # Step 1: 数据清洗
        try:
            result['df'] = self.cleaner.clean(result['df'])
            result['stats']['cleaned_count'] = len(result['df'])
        except Exception as e:
            result['errors'].append(f"数据清洗失败: {str(e)}")
            return result

        # Step 2: 去重
        try:
            result['df'] = self.deduplicator.deduplicate(result['df'])
            dup_summary = self.deduplicator.get_duplicate_summary(result['df'])
            result['stats']['duplicate_summary'] = dup_summary

            if dup_summary['needs_review'] > 0:
                result['warnings'].append(
                    f"发现 {dup_summary['needs_review']} 条疑似重复交易需要人工审核"
                )
        except Exception as e:
            result['errors'].append(f"去重失败: {str(e)}")

        # Step 3: 一级分类
        try:
            df_to_classify = result['df'][~result['df']['is_duplicate']].copy()

            for idx, row in df_to_classify.iterrows():
                category, confidence, method = self.primary_classifier.classify(row.to_dict())
                result['df'].at[idx, 'category'] = category
                result['df'].at[idx, 'classification_confidence'] = confidence
                result['df'].at[idx, 'classification_method'] = method

            result['stats']['classified_count'] = len(df_to_classify)
        except Exception as e:
            result['errors'].append(f"一级分类失败: {str(e)}")

        # Step 4: 二级分类
        try:
            for idx, row in result['df'].iterrows():
                if pd.isna(row.get('category')) or row.get('is_duplicate'):
                    continue

                # 转换为字典并确保字符串字段是字符串类型
                row_dict = row.to_dict()
                # 确保关键字段是字符串
                for key in ['description', 'counterparty', 'category']:
                    if key in row_dict and row_dict[key] is not None:
                        row_dict[key] = str(row_dict[key])
                
                subcategory, subcat_confidence = self.subcategory_classifier.classify(
                    row_dict['category'],
                    row_dict
                )

                if subcategory and subcat_confidence > 0.6:
                    result['df'].at[idx, 'subcategory'] = subcategory
        except Exception as e:
            result['errors'].append(f"二级分类失败: {str(e)}")

        # Step 5: 异常检测
        if enable_anomaly_detection:
            try:
                result['df'] = self.anomaly_detector.detect(result['df'])
                anomaly_summary = self.anomaly_detector.get_anomaly_summary(result['df'])
                result['stats']['anomaly_summary'] = anomaly_summary

                if anomaly_summary['total_anomalies'] > 0:
                    result['warnings'].append(
                        f"检测到 {anomaly_summary['total_anomalies']} 条异常交易"
                    )
            except Exception as e:
                result['errors'].append(f"异常检测失败: {str(e)}")

        # Step 6: 订阅识别
        if enable_subscription_detection:
            try:
                result['df'] = self.subscription_detector.detect(result['df'])
                subscription_summary = self.subscription_detector.get_subscription_summary(result['df'])
                result['stats']['subscription_summary'] = subscription_summary

                if subscription_summary['total_subscriptions'] > 0:
                    result['warnings'].append(
                        f"识别到 {subscription_summary['total_subscriptions']} 个订阅服务，"
                        f"预计月度成本 ¥{subscription_summary['monthly_cost']:.2f}"
                    )
            except Exception as e:
                result['errors'].append(f"订阅识别失败: {str(e)}")

        # 汇总统计
        result['stats']['total_transactions'] = len(result['df'])
        result['stats']['unique_transactions'] = len(result['df'][~result['df']['is_duplicate']])

        return result

    def get_summary_report(self, result: Dict) -> str:
        """
        生成处理摘要报告

        Args:
            result: 处理结果字典

        Returns:
            格式化的摘要文本
        """
        stats = result['stats']
        warnings = result['warnings']
        errors = result['errors']

        report = ["=" * 50]
        report.append("数据处理摘要报告")
        report.append("=" * 50)

        # 基本统计
        report.append(f"\n总交易数: {stats.get('total_transactions', 0)}")
        report.append(f"有效交易数: {stats.get('unique_transactions', 0)}")
        report.append(f"已分类数: {stats.get('classified_count', 0)}")

        # 去重统计
        if 'duplicate_summary' in stats:
            dup = stats['duplicate_summary']
            report.append(f"\n去重统计:")
            report.append(f"  - 重复交易: {dup.get('duplicate_count', 0)}")
            report.append(f"  - 高置信度: {dup.get('high_confidence_duplicates', 0)}")
            report.append(f"  - 需审核: {dup.get('needs_review', 0)}")

        # 异常统计
        if 'anomaly_summary' in stats:
            anom = stats['anomaly_summary']
            if anom.get('total_anomalies', 0) > 0:
                report.append(f"\n异常检测:")
                report.append(f"  - 异常交易数: {anom['total_anomalies']}")
                for anom_type, count in anom.get('by_type', {}).items():
                    report.append(f"  - {anom_type}: {count}")

        # 订阅统计
        if 'subscription_summary' in stats:
            sub = stats['subscription_summary']
            if sub.get('total_subscriptions', 0) > 0:
                report.append(f"\n订阅识别:")
                report.append(f"  - 订阅服务数: {sub['total_subscriptions']}")
                report.append(f"  - 预计月度成本: ¥{sub.get('monthly_cost', 0):.2f}")

        # 警告
        if warnings:
            report.append(f"\n⚠️ 警告:")
            for warning in warnings:
                report.append(f"  - {warning}")

        # 错误
        if errors:
            report.append(f"\n❌ 错误:")
            for error in errors:
                report.append(f"  - {error}")

        report.append("\n" + "=" * 50)

        return "\n".join(report)
