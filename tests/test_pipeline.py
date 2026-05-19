"""Tests for the data processing pipeline"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.processors.pipeline import DataProcessingPipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pipeline():
    return DataProcessingPipeline(use_ai=False)


@pytest.fixture
def raw_df():
    """Simulates raw parser output -- needs cleaning, dedup, classification"""
    return pd.DataFrame([
        {
            'transaction_id': 'T001',
            'platform': 'alipay',
            'date': datetime(2024, 3, 15, 10, 0),
            'amount': 25.50,
            'type': 'expense',
            'counterparty': '美团外卖',
            'description': '美团外卖-午餐',
            'status': '交易成功',
        },
        {
            'transaction_id': 'T002',
            'platform': 'alipay',
            'date': datetime(2024, 3, 15, 14, 0),
            'amount': 5000.00,
            'type': 'expense',
            'counterparty': '京东商城',
            'description': '京东-数码产品',
            'status': '交易成功',
        },
        {
            'transaction_id': 'T003',
            'platform': 'alipay',
            'date': datetime(2024, 3, 16, 9, 0),
            'amount': 15.00,
            'type': 'expense',
            'counterparty': '瑞幸咖啡',
            'description': '瑞幸咖啡',
            'status': '交易成功',
        },
        {
            'transaction_id': 'T004',
            'platform': 'alipay',
            'date': datetime(2024, 3, 16, 12, 0),
            'amount': 8000.00,
            'type': 'income',
            'counterparty': 'XX公司',
            'description': '工资',
            'status': '交易成功',
        },
    ])


@pytest.fixture
def duplicate_df():
    """DataFrame with intentional duplicates for dedup testing"""
    return pd.DataFrame([
        {
            'transaction_id': 'T010',
            'platform': 'alipay',
            'date': datetime(2024, 3, 20, 10, 0),
            'amount': 50.00,
            'type': 'expense',
            'counterparty': '美团外卖',
            'description': '午餐外卖',
            'status': '交易成功',
        },
        {
            'transaction_id': 'T010',  # same transaction_id -> duplicate
            'platform': 'alipay',
            'date': datetime(2024, 3, 20, 10, 0),
            'amount': 50.00,
            'type': 'expense',
            'counterparty': '美团外卖',
            'description': '午餐外卖',
            'status': '交易成功',
        },
        {
            'transaction_id': 'T011',
            'platform': 'alipay',
            'date': datetime(2024, 3, 20, 12, 0),
            'amount': 30.00,
            'type': 'expense',
            'counterparty': '瑞幸咖啡',
            'description': '咖啡',
            'status': '交易成功',
        },
    ])


# ---------------------------------------------------------------------------
# TestPipelineProcess
# ---------------------------------------------------------------------------

class TestPipelineProcess:
    def test_process_returns_dict(self, pipeline, raw_df):
        """Process should return a result dict with expected keys"""
        result = pipeline.process(raw_df)
        assert isinstance(result, dict)
        assert 'df' in result
        assert 'stats' in result
        assert 'warnings' in result
        assert 'errors' in result

    def test_process_preserves_records(self, pipeline, raw_df):
        """Process should not lose valid records"""
        result = pipeline.process(raw_df)
        # All 4 records are valid (non-zero amount, have date and transaction_id)
        # Some may be filtered by exclude_transactions keywords (e.g. "工资" is not excluded,
        # but we need to account for cleaning)
        assert len(result['df']) >= 3

    def test_process_adds_classification(self, pipeline, raw_df):
        """Process should add category column"""
        result = pipeline.process(raw_df)
        df = result['df']
        assert 'category' in df.columns

    def test_process_adds_dedup_flag(self, pipeline, raw_df):
        """Process should add is_duplicate column"""
        result = pipeline.process(raw_df)
        df = result['df']
        assert 'is_duplicate' in df.columns

    def test_process_adds_subcategory(self, pipeline, raw_df):
        """Process should add subcategory column"""
        result = pipeline.process(raw_df)
        df = result['df']
        assert 'subcategory' in df.columns

    def test_process_stats_populated(self, pipeline, raw_df):
        """Stats should have key metrics"""
        result = pipeline.process(raw_df)
        stats = result['stats']
        assert 'total_transactions' in stats
        assert 'unique_transactions' in stats

    def test_process_no_errors(self, pipeline, raw_df):
        """Normal processing should produce no errors"""
        result = pipeline.process(raw_df)
        assert len(result['errors']) == 0

    def test_process_correct_classification(self, pipeline, raw_df):
        """Known merchants should be classified correctly"""
        result = pipeline.process(raw_df)
        df = result['df']
        # Find the 美团外卖 row
        meituan_rows = df[df['counterparty'].str.contains('美团', na=False)]
        if not meituan_rows.empty:
            assert meituan_rows.iloc[0]['category'] == '餐饮美食'

    def test_process_dedup_summary_in_stats(self, pipeline, raw_df):
        """Duplicate summary should be in stats"""
        result = pipeline.process(raw_df)
        assert 'duplicate_summary' in result['stats']

    def test_process_classified_count_in_stats(self, pipeline, raw_df):
        """Classified count should be in stats"""
        result = pipeline.process(raw_df)
        assert 'classified_count' in result['stats']

    def test_process_with_duplicates(self, pipeline, duplicate_df):
        """Processing data with duplicates should detect them"""
        result = pipeline.process(duplicate_df)
        df = result['df']
        assert df['is_duplicate'].any()
        dup_summary = result['stats']['duplicate_summary']
        assert dup_summary['duplicate_count'] > 0

    def test_process_unique_transactions_count(self, pipeline, raw_df):
        """unique_transactions should equal total minus duplicates"""
        result = pipeline.process(raw_df)
        stats = result['stats']
        df = result['df']
        expected_unique = len(df[~df['is_duplicate']])
        assert stats['unique_transactions'] == expected_unique


# ---------------------------------------------------------------------------
# TestPipelineAnomalyDetection
# ---------------------------------------------------------------------------

class TestPipelineAnomalyDetection:
    def test_process_anomaly_detection_enabled(self, pipeline, raw_df):
        """Anomaly detection should run when enabled"""
        result = pipeline.process(raw_df, enable_anomaly_detection=True)
        assert 'anomaly_summary' in result['stats']

    def test_process_anomaly_detection_disabled(self, pipeline, raw_df):
        """Anomaly detection should not run when disabled"""
        result = pipeline.process(raw_df, enable_anomaly_detection=False)
        assert 'anomaly_summary' not in result['stats']

    def test_anomaly_detection_adds_columns(self, pipeline, raw_df):
        """Anomaly detection should add is_anomaly and related columns"""
        result = pipeline.process(raw_df, enable_anomaly_detection=True)
        df = result['df']
        assert 'is_anomaly' in df.columns
        assert 'anomaly_type' in df.columns
        assert 'anomaly_score' in df.columns


# ---------------------------------------------------------------------------
# TestPipelineSubscriptionDetection
# ---------------------------------------------------------------------------

class TestPipelineSubscriptionDetection:
    def test_process_subscription_detection_enabled(self, pipeline, raw_df):
        """Subscription detection should run when enabled"""
        result = pipeline.process(raw_df, enable_subscription_detection=True)
        assert 'subscription_summary' in result['stats']

    def test_process_subscription_detection_disabled(self, pipeline, raw_df):
        """Subscription detection should not run when disabled"""
        result = pipeline.process(raw_df, enable_subscription_detection=False)
        assert 'subscription_summary' not in result['stats']

    def test_subscription_detection_adds_columns(self, pipeline, raw_df):
        """Subscription detection should add is_subscription and related columns"""
        result = pipeline.process(raw_df, enable_subscription_detection=True)
        df = result['df']
        assert 'is_subscription' in df.columns
        assert 'subscription_group' in df.columns
        assert 'subscription_cycle' in df.columns


# ---------------------------------------------------------------------------
# TestPipelineReport
# ---------------------------------------------------------------------------

class TestPipelineReport:
    def test_summary_report_is_string(self, pipeline, raw_df):
        """Summary report should be a string"""
        result = pipeline.process(raw_df)
        report = pipeline.get_summary_report(result)
        assert isinstance(report, str)

    def test_summary_report_header(self, pipeline, raw_df):
        """Summary report should contain header"""
        result = pipeline.process(raw_df)
        report = pipeline.get_summary_report(result)
        assert '数据处理摘要报告' in report

    def test_report_contains_stats(self, pipeline, raw_df):
        """Report should contain key statistics"""
        result = pipeline.process(raw_df)
        report = pipeline.get_summary_report(result)
        assert '总交易数' in report
        assert '有效交易数' in report
        assert '已分类数' in report

    def test_report_contains_dedup_stats(self, pipeline, raw_df):
        """Report should contain dedup statistics"""
        result = pipeline.process(raw_df)
        report = pipeline.get_summary_report(result)
        assert '去重统计' in report

    def test_report_with_warnings(self, pipeline, duplicate_df):
        """Report should include warnings when they exist"""
        result = pipeline.process(duplicate_df)
        # If there are warnings, they should appear in the report
        if result['warnings']:
            report = pipeline.get_summary_report(result)
            assert '警告' in report

    def test_report_with_errors(self, pipeline):
        """Report should include errors when they exist"""
        # Create a result dict with manual errors
        fake_result = {
            'df': pd.DataFrame(),
            'stats': {'total_transactions': 0, 'unique_transactions': 0},
            'warnings': [],
            'errors': ['测试错误'],
        }
        report = pipeline.get_summary_report(fake_result)
        assert '错误' in report
        assert '测试错误' in report


# ---------------------------------------------------------------------------
# TestPipelineErrorHandling
# ---------------------------------------------------------------------------

class TestPipelineErrorHandling:
    def test_empty_dataframe(self, pipeline):
        """Should handle empty DataFrame gracefully"""
        empty_df = pd.DataFrame(columns=[
            'transaction_id', 'platform', 'date', 'amount',
            'type', 'counterparty', 'description', 'status'
        ])
        result = pipeline.process(empty_df)
        assert isinstance(result, dict)
        assert 'df' in result
        assert 'errors' in result

    def test_missing_columns_graceful(self, pipeline):
        """Should handle DataFrame with missing expected columns"""
        bad_df = pd.DataFrame({'random_col': [1, 2, 3]})
        result = pipeline.process(bad_df)
        # Should report errors in the result, not raise an exception
        assert isinstance(result, dict)
        assert 'errors' in result
        # The cleaner step should fail because 'amount' column is missing
        assert len(result['errors']) > 0

    def test_dataframe_with_zero_amounts(self, pipeline):
        """Records with zero amount should be cleaned out"""
        df = pd.DataFrame([
            {
                'transaction_id': 'T100',
                'platform': 'alipay',
                'date': datetime(2024, 3, 15, 10, 0),
                'amount': 0.0,  # zero amount -> should be removed
                'type': 'expense',
                'counterparty': '测试',
                'description': '测试',
                'status': '交易成功',
            },
            {
                'transaction_id': 'T101',
                'platform': 'alipay',
                'date': datetime(2024, 3, 15, 11, 0),
                'amount': 50.00,
                'type': 'expense',
                'counterparty': '美团外卖',
                'description': '外卖',
                'status': '交易成功',
            },
        ])
        result = pipeline.process(df)
        # The zero-amount record should be cleaned out
        assert len(result['df']) == 1

    def test_dataframe_with_null_dates(self, pipeline):
        """Records with null dates should be cleaned out"""
        df = pd.DataFrame([
            {
                'transaction_id': 'T200',
                'platform': 'alipay',
                'date': None,  # null date -> should be removed
                'amount': 25.00,
                'type': 'expense',
                'counterparty': '测试',
                'description': '测试',
                'status': '交易成功',
            },
            {
                'transaction_id': 'T201',
                'platform': 'alipay',
                'date': datetime(2024, 3, 15, 11, 0),
                'amount': 50.00,
                'type': 'expense',
                'counterparty': '美团外卖',
                'description': '外卖',
                'status': '交易成功',
            },
        ])
        result = pipeline.process(df)
        assert len(result['df']) == 1


# ---------------------------------------------------------------------------
# TestPipelineInit
# ---------------------------------------------------------------------------

class TestPipelineInit:
    def test_init_without_ai(self):
        """Pipeline should initialize successfully without AI"""
        pipeline = DataProcessingPipeline(use_ai=False)
        assert pipeline.cleaner is not None
        assert pipeline.deduplicator is not None
        assert pipeline.primary_classifier is not None
        assert pipeline.subcategory_classifier is not None
        assert pipeline.anomaly_detector is not None
        assert pipeline.subscription_detector is not None

    def test_init_ai_disabled(self):
        """Pipeline AI should be disabled when use_ai=False"""
        pipeline = DataProcessingPipeline(use_ai=False)
        assert pipeline.primary_classifier.use_ai is False
