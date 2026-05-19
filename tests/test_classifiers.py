"""Tests for classifier modules"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from src.classifiers.rule_classifier import RuleClassifier
from src.classifiers.subcategory_classifier import SubcategoryClassifier
from src.classifiers.hybrid_classifier import HybridClassifier


# ---------------------------------------------------------------------------
# RuleClassifier
# ---------------------------------------------------------------------------

class TestRuleClassifier:
    @pytest.fixture
    def classifier(self):
        return RuleClassifier()

    # --- classify (single transaction) ---

    def test_classify_known_merchant(self, classifier):
        """Known merchant should get high confidence"""
        category, confidence = classifier.classify(
            {'counterparty': '美团外卖', 'description': '外卖订单'}
        )
        assert category == '餐饮美食'
        assert confidence >= 0.8

    def test_classify_transport_keyword(self, classifier):
        """Transport keyword should match 交通出行"""
        category, confidence = classifier.classify(
            {'counterparty': '滴滴出行', 'description': '快车'}
        )
        assert category == '交通出行'
        assert confidence >= 0.8

    def test_classify_shopping_keyword(self, classifier):
        """Shopping keyword should match 购物消费"""
        category, confidence = classifier.classify(
            {'counterparty': '京东商城', 'description': '京东-数码产品'}
        )
        assert category == '购物消费'
        assert confidence >= 0.7

    def test_classify_unknown_returns_other(self, classifier):
        """Unknown merchant/description should return '其他' with low confidence"""
        category, confidence = classifier.classify(
            {'counterparty': 'UNKNOWN_RANDOM_XYZ_12345', 'description': 'zzz random stuff qqq'}
        )
        assert category == '其他'
        assert confidence < 0.5

    def test_classify_returns_tuple(self, classifier):
        """classify() should always return (str, float)"""
        result = classifier.classify({'counterparty': '星巴克', 'description': '咖啡'})
        assert isinstance(result, tuple)
        assert len(result) == 2
        category, confidence = result
        assert isinstance(category, str)
        assert isinstance(confidence, float)

    def test_classify_missing_fields(self, classifier):
        """Should handle missing fields gracefully (empty dict)"""
        category, confidence = classifier.classify({})
        assert isinstance(category, str)
        assert isinstance(confidence, float)

    def test_classify_none_values(self, classifier):
        """Should handle None values in fields"""
        category, confidence = classifier.classify(
            {'counterparty': None, 'description': None}
        )
        assert isinstance(category, str)
        assert isinstance(confidence, float)

    # --- classify_batch ---

    def test_classify_batch_basic(self, classifier):
        """Batch classification should work on DataFrame"""
        df = pd.DataFrame([
            {'counterparty': '美团外卖', 'description': '外卖', 'amount': 25, 'type': 'expense'},
            {'counterparty': '滴滴出行', 'description': '快车', 'amount': 30, 'type': 'expense'},
        ])
        result = classifier.classify_batch(df)
        assert 'category' in result.columns
        assert 'classification_confidence' in result.columns
        assert 'classification_method' in result.columns
        assert len(result) == 2

    def test_classify_batch_categories_correct(self, classifier):
        """Batch classification should assign correct categories"""
        df = pd.DataFrame([
            {'counterparty': '美团外卖', 'description': '外卖午餐', 'amount': 25, 'type': 'expense'},
            {'counterparty': '滴滴出行', 'description': '快车', 'amount': 30, 'type': 'expense'},
        ])
        result = classifier.classify_batch(df)
        assert result.iloc[0]['category'] == '餐饮美食'
        assert result.iloc[1]['category'] == '交通出行'

    def test_classify_batch_method_is_rule(self, classifier):
        """Batch classification method should always be 'rule'"""
        df = pd.DataFrame([
            {'counterparty': '星巴克', 'description': '咖啡', 'amount': 35, 'type': 'expense'},
        ])
        result = classifier.classify_batch(df)
        assert result.iloc[0]['classification_method'] == 'rule'

    def test_classify_batch_empty_dataframe(self, classifier):
        """Batch classification on empty DataFrame should return empty with correct columns"""
        df = pd.DataFrame(columns=['counterparty', 'description', 'amount', 'type'])
        result = classifier.classify_batch(df)
        assert 'category' in result.columns
        assert 'classification_confidence' in result.columns
        assert 'classification_method' in result.columns
        assert len(result) == 0

    def test_classify_batch_preserves_original_columns(self, classifier):
        """Batch classification should preserve all original columns"""
        df = pd.DataFrame([
            {'counterparty': '星巴克', 'description': '咖啡', 'amount': 35, 'type': 'expense', 'extra_col': 'keep_me'},
        ])
        result = classifier.classify_batch(df)
        assert 'extra_col' in result.columns
        assert result.iloc[0]['extra_col'] == 'keep_me'

    # --- get_categories ---

    def test_get_categories_returns_list(self, classifier):
        """Should return list of available categories"""
        categories = classifier.get_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0

    def test_get_categories_contains_expected(self, classifier):
        """Should contain known categories from config"""
        categories = classifier.get_categories()
        assert '餐饮美食' in categories
        assert '交通出行' in categories
        assert '购物消费' in categories
        assert '居家生活' in categories

    # --- add_learning_rule ---

    def test_add_learning_rule_new_keyword(self, classifier):
        """Adding a learning rule should extend the category"""
        classifier.add_learning_rule('餐饮美食', 'keywords', '新关键词测试')
        assert '新关键词测试' in classifier.categories['餐饮美食']['keywords']

    def test_add_learning_rule_new_category(self, classifier):
        """Adding a rule for non-existent category should create it"""
        classifier.add_learning_rule('新测试分类', 'keywords', '测试词')
        assert '新测试分类' in classifier.categories
        assert '测试词' in classifier.categories['新测试分类']['keywords']

    def test_add_learning_rule_no_duplicate(self, classifier):
        """Adding the same rule twice should not create duplicates"""
        classifier.add_learning_rule('餐饮美食', 'keywords', '去重测试词')
        classifier.add_learning_rule('餐饮美食', 'keywords', '去重测试词')
        count = classifier.categories['餐饮美食']['keywords'].count('去重测试词')
        assert count == 1


# ---------------------------------------------------------------------------
# SubcategoryClassifier
# ---------------------------------------------------------------------------

class TestSubcategoryClassifier:
    @pytest.fixture
    def classifier(self):
        return SubcategoryClassifier()

    def test_classify_known_subcategory(self, classifier):
        """Should classify known subcategory correctly"""
        subcategory, confidence = classifier.classify(
            '餐饮美食',
            {'counterparty': '美团外卖', 'description': '外卖午餐'}
        )
        assert subcategory == '外卖'
        assert confidence > 0.6

    def test_classify_coffee_subcategory(self, classifier):
        """Should classify coffee shops correctly"""
        subcategory, confidence = classifier.classify(
            '餐饮美食',
            {'counterparty': '瑞幸咖啡', 'description': '咖啡'}
        )
        assert subcategory == '咖啡奶茶'
        assert confidence > 0.6

    def test_classify_unknown_primary(self, classifier):
        """Unknown primary category should return (None, 0.0)"""
        subcategory, confidence = classifier.classify(
            '不存在的分类',
            {'counterparty': '测试', 'description': '测试'}
        )
        assert subcategory is None
        assert confidence == 0.0

    def test_classify_batch_adds_subcategory_column(self, classifier):
        """Batch classify should add subcategory column"""
        df = pd.DataFrame([
            {
                'counterparty': '美团外卖',
                'description': '外卖午餐',
                'category': '餐饮美食',
                'amount': 25,
                'type': 'expense',
                'is_duplicate': False,
            },
        ])
        result = classifier.classify_batch(df)
        assert 'subcategory' in result.columns

    def test_classify_batch_correct_subcategory(self, classifier):
        """Batch classify should assign correct subcategory"""
        df = pd.DataFrame([
            {
                'counterparty': '美团外卖',
                'description': '外卖午餐',
                'category': '餐饮美食',
                'amount': 25,
                'type': 'expense',
                'is_duplicate': False,
            },
        ])
        result = classifier.classify_batch(df)
        assert result.iloc[0]['subcategory'] == '外卖'

    def test_classify_batch_skips_duplicates(self, classifier):
        """Batch classify should skip records marked as duplicates"""
        df = pd.DataFrame([
            {
                'counterparty': '美团外卖',
                'description': '外卖午餐',
                'category': '餐饮美食',
                'amount': 25,
                'type': 'expense',
                'is_duplicate': True,
            },
        ])
        result = classifier.classify_batch(df)
        assert result.iloc[0]['subcategory'] is None

    def test_classify_batch_preserves_rows(self, classifier):
        """Batch classify should not add or remove rows"""
        df = pd.DataFrame([
            {
                'counterparty': '美团外卖',
                'description': '外卖午餐',
                'category': '餐饮美食',
                'amount': 25,
                'type': 'expense',
                'is_duplicate': False,
            },
            {
                'counterparty': '滴滴出行',
                'description': '快车',
                'category': '交通出行',
                'amount': 30,
                'type': 'expense',
                'is_duplicate': False,
            },
        ])
        result = classifier.classify_batch(df)
        assert len(result) == 2

    def test_get_subcategories(self, classifier):
        """Should return subcategories for a known primary category"""
        subs = classifier.get_subcategories('餐饮美食')
        assert isinstance(subs, list)
        assert len(subs) > 0
        assert '外卖' in subs

    def test_get_subcategories_unknown(self, classifier):
        """Should return empty list for unknown primary category"""
        subs = classifier.get_subcategories('不存在的分类')
        assert subs == []


# ---------------------------------------------------------------------------
# HybridClassifier
# ---------------------------------------------------------------------------

class TestHybridClassifier:
    def test_init_without_ai(self):
        """Should initialize with rules only when use_ai=False"""
        classifier = HybridClassifier(use_ai=False)
        assert classifier.rule_classifier is not None
        assert classifier.use_ai is False
        assert classifier.ai_classifier is None

    def test_rule_classifier_accessible(self):
        """Rule classifier should be accessible and functional"""
        classifier = HybridClassifier(use_ai=False)
        assert hasattr(classifier, 'rule_classifier')
        assert hasattr(classifier.rule_classifier, 'classify')
        assert hasattr(classifier.rule_classifier, 'classify_batch')

    def test_classify_returns_tuple_of_three(self):
        """classify() should return (category, confidence, method)"""
        classifier = HybridClassifier(use_ai=False)
        result = classifier.classify({'counterparty': '美团外卖', 'description': '外卖'})
        assert isinstance(result, tuple)
        assert len(result) == 3
        category, confidence, method = result
        assert isinstance(category, str)
        assert isinstance(confidence, float)
        assert isinstance(method, str)

    def test_classify_uses_rule_method(self):
        """Without AI, method should always be 'rule'"""
        classifier = HybridClassifier(use_ai=False)
        category, confidence, method = classifier.classify(
            {'counterparty': '美团外卖', 'description': '外卖'}
        )
        assert method == 'rule'

    def test_classify_correct_category(self):
        """Should classify correctly via rule classifier"""
        classifier = HybridClassifier(use_ai=False)
        category, confidence, method = classifier.classify(
            {'counterparty': '美团外卖', 'description': '外卖'}
        )
        assert category == '餐饮美食'
        assert confidence >= 0.8

    def test_confidence_threshold_default(self):
        """Default confidence threshold should be 0.8"""
        classifier = HybridClassifier(use_ai=False)
        assert classifier.confidence_threshold == 0.8

    def test_confidence_threshold_custom(self):
        """Should accept custom confidence threshold"""
        classifier = HybridClassifier(use_ai=False, confidence_threshold=0.5)
        assert classifier.confidence_threshold == 0.5

    def test_disable_ai(self):
        """disable_ai() should set use_ai to False"""
        classifier = HybridClassifier(use_ai=False)
        classifier.disable_ai()
        assert classifier.use_ai is False

    def test_classify_batch_returns_list(self):
        """classify_batch should return a list of dicts"""
        classifier = HybridClassifier(use_ai=False)
        transactions = [
            {'counterparty': '美团外卖', 'description': '外卖'},
            {'counterparty': '滴滴出行', 'description': '快车'},
        ]
        results = classifier.classify_batch(transactions)
        assert isinstance(results, list)
        assert len(results) == 2
        for r in results:
            assert 'category' in r
            assert 'confidence' in r
            assert 'method' in r

    def test_get_stats(self):
        """get_stats should return correct statistics"""
        classifier = HybridClassifier(use_ai=False)
        results = [
            {'category': '餐饮美食', 'confidence': 0.9, 'method': 'rule', 'transaction': {}},
            {'category': '交通出行', 'confidence': 0.85, 'method': 'rule', 'transaction': {}},
        ]
        stats = classifier.get_stats(results)
        assert stats['total'] == 2
        assert stats['rule_classified'] == 2
        assert stats['ai_classified'] == 0
        assert stats['average_confidence'] == pytest.approx(0.875)


# ---------------------------------------------------------------------------
# AIClassifier (mocked)
# ---------------------------------------------------------------------------

class TestAIClassifier:
    @patch('src.classifiers.ai_classifier.load_dotenv')
    def test_init_without_key_raises(self, mock_dotenv):
        """Should raise ValueError when no API key is available"""
        with patch.dict('os.environ', {}, clear=True):
            from src.classifiers.ai_classifier import AIClassifier
            with pytest.raises(ValueError, match="未配置KIMI_API_KEY"):
                AIClassifier(api_key=None)

    @patch('src.classifiers.ai_classifier.requests')
    def test_classify_mocked(self, mock_requests):
        """AI classification with mocked API response"""
        from src.classifiers.ai_classifier import AIClassifier

        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': '餐饮美食'}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        classifier = AIClassifier(api_key='test-fake-key')
        result = classifier.classify({
            'date': '2024-03-15',
            'amount': 25.0,
            'counterparty': '美团外卖',
            'description': '外卖午餐',
        })
        assert result == '餐饮美食'

    @patch('src.classifiers.ai_classifier.requests')
    def test_classify_api_error_returns_other(self, mock_requests):
        """API error should return '其他'"""
        from src.classifiers.ai_classifier import AIClassifier
        import requests as real_requests

        mock_requests.post.side_effect = real_requests.exceptions.ConnectionError("connection failed")
        mock_requests.exceptions = real_requests.exceptions

        classifier = AIClassifier(api_key='test-fake-key')
        result = classifier.classify({
            'date': '2024-03-15',
            'amount': 25.0,
            'counterparty': '测试',
            'description': '测试',
        })
        assert result == '其他'

    @patch('src.classifiers.ai_classifier.requests')
    def test_validate_api_key_success(self, mock_requests):
        """validate_api_key should return True on 200"""
        from src.classifiers.ai_classifier import AIClassifier

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response

        classifier = AIClassifier(api_key='test-fake-key')
        assert classifier.validate_api_key() is True

    @patch('src.classifiers.ai_classifier.requests')
    def test_validate_api_key_failure(self, mock_requests):
        """validate_api_key should return False on error"""
        from src.classifiers.ai_classifier import AIClassifier
        import requests as real_requests

        mock_requests.post.side_effect = real_requests.exceptions.ConnectionError("fail")
        mock_requests.exceptions = real_requests.exceptions

        classifier = AIClassifier(api_key='test-fake-key')
        assert classifier.validate_api_key() is False

    @patch('src.classifiers.ai_classifier.requests')
    def test_clean_category_name(self, mock_requests):
        """Should clean prefix from AI response"""
        from src.classifiers.ai_classifier import AIClassifier

        classifier = AIClassifier(api_key='test-fake-key')
        assert classifier._clean_category_name('分类：餐饮美食') == '餐饮美食'
        assert classifier._clean_category_name('类别:交通出行') == '交通出行'
        assert classifier._clean_category_name('"购物消费"') == '购物消费'
        assert classifier._clean_category_name('居家生活\n这是因为...') == '居家生活'
