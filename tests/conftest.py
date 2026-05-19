"""Shared test fixtures"""
import sys
import os

# Ensure project root is on sys.path so `from src...` imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd
from datetime import datetime
from src.database.operations import DatabaseManager


@pytest.fixture
def db():
    """In-memory SQLite database"""
    manager = DatabaseManager(db_path=":memory:")
    manager.init_db()
    return manager


@pytest.fixture
def sample_transactions():
    """Sample transaction dicts for testing"""
    return [
        {
            'transaction_id': 'TXN001',
            'platform': 'alipay',
            'date': datetime(2024, 3, 15, 10, 30, 0),
            'amount': 25.50,
            'type': 'expense',
            'category': '餐饮美食',
            'subcategory': '外卖',
            'counterparty': '美团外卖',
            'description': '美团外卖-午餐',
            'is_duplicate': False,
            'classification_method': 'rule',
            'classification_confidence': 0.9,
            'is_anomaly': False,
            'is_subscription': False,
            'is_verified': False,
        },
        {
            'transaction_id': 'TXN002',
            'platform': 'wechat',
            'date': datetime(2024, 3, 15, 14, 0, 0),
            'amount': 5000.00,
            'type': 'expense',
            'category': '购物消费',
            'subcategory': '数码电子',
            'counterparty': '京东商城',
            'description': '京东-笔记本电脑',
            'is_duplicate': False,
            'classification_method': 'rule',
            'classification_confidence': 0.85,
            'is_anomaly': True,
            'anomaly_type': 'large_amount',
            'anomaly_score': 0.92,
            'anomaly_reason': '金额超过95%分位数',
            'is_subscription': False,
            'is_verified': False,
        },
        {
            'transaction_id': 'TXN003',
            'platform': 'alipay',
            'date': datetime(2024, 3, 16, 9, 0, 0),
            'amount': 15.00,
            'type': 'expense',
            'category': '餐饮美食',
            'subcategory': '饮品',
            'counterparty': '瑞幸咖啡',
            'description': '瑞幸咖啡',
            'is_duplicate': False,
            'classification_method': 'rule',
            'classification_confidence': 0.95,
            'is_anomaly': False,
            'is_subscription': True,
            'subscription_group': 'SUB001',
            'subscription_name': '瑞幸咖啡',
            'subscription_cycle': 'weekly',
            'subscription_confidence': 0.8,
            'is_verified': False,
        },
        {
            'transaction_id': 'TXN004',
            'platform': 'bank',
            'date': datetime(2024, 3, 16, 12, 0, 0),
            'amount': 8000.00,
            'type': 'income',
            'category': '工资薪资',
            'counterparty': 'XX公司',
            'description': '工资',
            'is_duplicate': False,
            'classification_method': 'rule',
            'classification_confidence': 0.95,
            'is_anomaly': False,
            'is_subscription': False,
            'is_verified': False,
        },
        {
            'transaction_id': 'TXN005',
            'platform': 'alipay',
            'date': datetime(2024, 3, 15, 10, 32, 0),
            'amount': 25.50,
            'type': 'expense',
            'category': '餐饮美食',
            'counterparty': '美团外卖',
            'description': '美团外卖-午餐',
            'is_duplicate': True,
            'duplicate_group': 'DUP001',
            'duplicate_confidence': 0.95,
            'classification_method': 'rule',
            'classification_confidence': 0.9,
            'is_anomaly': False,
            'is_subscription': False,
            'is_verified': False,
        },
    ]


@pytest.fixture
def sample_df(sample_transactions):
    """Sample DataFrame for pipeline testing"""
    df = pd.DataFrame(sample_transactions)
    return df


@pytest.fixture
def db_with_data(db, sample_transactions):
    """Database pre-populated with sample data"""
    for txn in sample_transactions:
        db.add_transaction(txn)
    return db
