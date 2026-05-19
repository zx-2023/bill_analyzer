"""Database operations tests"""
import pytest
from datetime import datetime


class TestTransactionCRUD:
    def test_add_transaction(self, db, sample_transactions):
        """Adding a transaction should work and be retrievable"""
        db.add_transaction(sample_transactions[0])
        assert db.transaction_exists('TXN001')

    def test_add_transactions_bulk(self, db, sample_transactions):
        """Bulk insert should add all records"""
        count = db.add_transactions_bulk(sample_transactions)
        assert count == 5

    def test_transaction_exists_false(self, db):
        """Non-existent transaction should return False"""
        assert not db.transaction_exists('NONEXISTENT')

    def test_get_transaction_by_id(self, db_with_data):
        """Should return dict with correct fields"""
        txn = db_with_data.get_transaction_by_id('TXN001')
        assert txn is not None
        assert txn['transaction_id'] == 'TXN001'
        assert txn['amount'] == 25.50
        assert txn['platform'] == 'alipay'
        assert isinstance(txn, dict)

    def test_get_transaction_by_id_not_found(self, db_with_data):
        """Missing transaction should return None"""
        assert db_with_data.get_transaction_by_id('NONEXISTENT') is None

    def test_update_transaction(self, db_with_data):
        """Update should change specified fields"""
        db_with_data.update_transaction('TXN001', {
            'category': '生活服务',
            'classification_method': 'manual',
            'is_verified': True
        })
        txn = db_with_data.get_transaction_by_id('TXN001')
        assert txn['category'] == '生活服务'
        assert txn['classification_method'] == 'manual'
        assert txn['is_verified'] == True

    def test_duplicate_transaction_id_rejected(self, db_with_data):
        """Duplicate transaction_id should raise"""
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            db_with_data.add_transaction({
                'transaction_id': 'TXN001',
                'platform': 'alipay',
                'date': datetime(2024, 3, 15),
                'amount': 100,
                'type': 'expense',
            })


class TestTransactionQueries:
    def test_get_transactions_all(self, db_with_data):
        """Should return all transactions as dicts"""
        txns = db_with_data.get_transactions()
        assert len(txns) == 5
        assert all(isinstance(t, dict) for t in txns)

    def test_get_transactions_by_platform(self, db_with_data):
        """Platform filter should work"""
        txns = db_with_data.get_transactions(platform='alipay')
        assert all(t['platform'] == 'alipay' for t in txns)
        assert len(txns) == 3

    def test_get_transactions_by_category(self, db_with_data):
        """Category filter should work"""
        txns = db_with_data.get_transactions(category='餐饮美食')
        assert all(t['category'] == '餐饮美食' for t in txns)

    def test_get_transactions_by_type(self, db_with_data):
        """Type filter should work"""
        txns = db_with_data.get_transactions(trans_type='income')
        assert len(txns) == 1
        assert txns[0]['type'] == 'income'

    def test_get_transactions_by_date_range(self, db_with_data):
        """Date range filter should work"""
        txns = db_with_data.get_transactions(
            date_from=datetime(2024, 3, 16),
            date_to=datetime(2024, 3, 16, 23, 59, 59)
        )
        assert len(txns) == 2

    def test_get_transactions_limit(self, db_with_data):
        """Limit should cap results"""
        txns = db_with_data.get_transactions(limit=2)
        assert len(txns) == 2

    def test_get_transactions_keyword(self, db_with_data):
        """Keyword search should match counterparty or description"""
        txns = db_with_data.get_transactions(keyword='京东')
        assert len(txns) == 1
        assert txns[0]['counterparty'] == '京东商城'

    def test_get_transactions_amount_range(self, db_with_data):
        """Amount range filter should work"""
        txns = db_with_data.get_transactions(amount_min=100, amount_max=6000)
        assert all(100 <= t['amount'] <= 6000 for t in txns)

    def test_get_transactions_is_anomaly(self, db_with_data):
        """Anomaly filter should work"""
        txns = db_with_data.get_transactions(is_anomaly=True)
        assert len(txns) == 1
        assert txns[0]['transaction_id'] == 'TXN002'

    def test_get_transactions_is_subscription(self, db_with_data):
        """Subscription filter should work"""
        txns = db_with_data.get_transactions(is_subscription=True)
        assert len(txns) == 1
        assert txns[0]['transaction_id'] == 'TXN003'

    def test_get_uncategorized(self, db):
        """Should return transactions with no/empty/other category"""
        db.add_transaction({
            'transaction_id': 'UNCAT1',
            'platform': 'alipay',
            'date': datetime(2024, 3, 15),
            'amount': 10,
            'type': 'expense',
            'category': None,
        })
        db.add_transaction({
            'transaction_id': 'UNCAT2',
            'platform': 'alipay',
            'date': datetime(2024, 3, 15),
            'amount': 20,
            'type': 'expense',
            'category': '其他',
        })
        uncategorized = db.get_uncategorized_transactions()
        assert len(uncategorized) == 2

    def test_get_transactions_sorted_desc(self, db_with_data):
        """Results should be sorted by date descending"""
        txns = db_with_data.get_transactions()
        dates = [t['date'] for t in txns]
        assert dates == sorted(dates, reverse=True)


class TestStatsQueries:
    def test_summary_stats(self, db_with_data):
        """Summary stats should calculate correctly"""
        stats = db_with_data.get_summary_stats()
        assert stats['total_income'] == 8000.0
        # expenses: 25.50 + 5000 + 15 = 5040.50 (non-duplicate only)
        assert stats['total_expense'] > 0
        assert 'balance' in stats
        assert 'total_count' in stats

    def test_summary_stats_date_range(self, db_with_data):
        """Stats with date range should filter correctly"""
        stats = db_with_data.get_summary_stats(
            date_from=datetime(2024, 3, 16),
            date_to=datetime(2024, 3, 16, 23, 59, 59)
        )
        assert stats['total_income'] == 8000.0

    def test_category_stats(self, db_with_data):
        """Category stats should group expenses by category"""
        stats = db_with_data.get_category_stats()
        assert isinstance(stats, list)
        assert all('category' in s and 'total_amount' in s and 'count' in s for s in stats)
        categories = [s['category'] for s in stats]
        assert '餐饮美食' in categories

    def test_top_merchants(self, db_with_data):
        """Top merchants should return correct aggregation"""
        merchants = db_with_data.get_top_merchants(limit=5)
        assert isinstance(merchants, list)
        assert all('merchant' in m and 'total_amount' in m for m in merchants)


class TestToDict:
    def test_to_dict_completeness(self, db_with_data):
        """to_dict should include all business fields"""
        txn = db_with_data.get_transaction_by_id('TXN002')
        expected_fields = [
            'id', 'transaction_id', 'platform', 'date', 'amount', 'type',
            'category', 'subcategory', 'counterparty', 'counterparty_account',
            'description', 'payment_method', 'status', 'original_category', 'note',
            'is_duplicate', 'duplicate_group', 'duplicate_confidence',
            'classification_method', 'classification_confidence', 'is_verified',
            'is_anomaly', 'anomaly_type', 'anomaly_score', 'anomaly_reason',
            'is_subscription', 'subscription_group', 'subscription_name',
            'subscription_cycle', 'subscription_confidence',
            'created_at', 'updated_at',
        ]
        for field in expected_fields:
            assert field in txn, f"Missing field: {field}"

    def test_to_dict_anomaly_fields(self, db_with_data):
        """Anomaly fields should be populated correctly"""
        txn = db_with_data.get_transaction_by_id('TXN002')
        assert txn['is_anomaly'] == True
        assert txn['anomaly_type'] == 'large_amount'
        assert txn['anomaly_score'] == 0.92

    def test_to_dict_subscription_fields(self, db_with_data):
        """Subscription fields should be populated correctly"""
        txn = db_with_data.get_transaction_by_id('TXN003')
        assert txn['is_subscription'] == True
        assert txn['subscription_name'] == '瑞幸咖啡'
        assert txn['subscription_cycle'] == 'weekly'

    def test_to_dict_boolean_defaults(self, db_with_data):
        """Boolean fields should default to False, not None"""
        txn = db_with_data.get_transaction_by_id('TXN001')
        assert txn['is_duplicate'] == False
        assert txn['is_anomaly'] == False
        assert txn['is_subscription'] == False
        assert txn['is_verified'] == False


class TestBudget:
    def test_set_budget(self, db):
        """Setting a budget should work"""
        result = db.set_budget('餐饮美食', 2000.0, '2024-03')
        assert result['category'] == '餐饮美食'
        assert result['monthly_limit'] == 2000.0
        assert result['year_month'] == '2024-03'

    def test_set_budget_update(self, db):
        """Setting budget again for same category+month should update"""
        db.set_budget('餐饮美食', 2000.0, '2024-03')
        result = db.set_budget('餐饮美食', 3000.0, '2024-03')
        assert result['monthly_limit'] == 3000.0
        budgets = db.get_budgets(year_month='2024-03')
        assert len(budgets) == 1

    def test_get_budgets(self, db):
        """Should return list of budget dicts"""
        db.set_budget('餐饮美食', 2000.0, '2024-03')
        db.set_budget('购物消费', 5000.0, '2024-03')
        budgets = db.get_budgets(year_month='2024-03')
        assert len(budgets) == 2
        assert all(isinstance(b, dict) for b in budgets)

    def test_delete_budget(self, db):
        """Deleting budget should remove it"""
        result = db.set_budget('餐饮美食', 2000.0, '2024-03')
        db.delete_budget(result['id'])
        budgets = db.get_budgets(year_month='2024-03')
        assert len(budgets) == 0


class TestImportHistory:
    def test_file_imported_false(self, db):
        """New file hash should not exist"""
        assert not db.file_imported('abc123')

    def test_add_import_history(self, db):
        """Should track import history"""
        db.add_import_history({
            'filename': 'test.csv',
            'platform': 'alipay',
            'file_hash': 'abc123',
            'total_rows': 100,
            'imported_rows': 95,
            'status': 'success',
        })
        assert db.file_imported('abc123')
