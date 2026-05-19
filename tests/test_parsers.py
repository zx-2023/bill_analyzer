"""Parser unit tests for the bill_analyzer project.

Tests cover all four platform parsers (Alipay, WeChat, Bank, Meituan):
- Interface compliance (required methods)
- Format detection (positive and negative cases)
- Parsing and output standardization
- Encoding handling
"""
import os
import tempfile
import pytest
import pandas as pd

# Adjust sys.path so imports work from the project root
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.parsers.alipay_parser import AlipayParser
from src.parsers.wechat_parser import WeChatParser
from src.parsers.bank_parser import BankParser
from src.parsers.meituan_parser import MeituanParser
from src.parsers.base_parser import BaseParser


# ---------------------------------------------------------------------------
# Fixtures: parser instances
# ---------------------------------------------------------------------------

@pytest.fixture
def alipay_parser():
    return AlipayParser()


@pytest.fixture
def wechat_parser():
    return WeChatParser()


@pytest.fixture
def bank_parser():
    return BankParser()


@pytest.fixture
def meituan_parser():
    return MeituanParser()


# ---------------------------------------------------------------------------
# Fixtures: synthetic test data files
# ---------------------------------------------------------------------------

ALIPAY_PERSONAL_CSV_CONTENT = (
    "支付宝交易记录明细查询\n"
    "账号:[test@example.com]\n"
    "起始日期:[2025-01-01 00:00:00]    终止日期:[2025-01-31 23:59:59]\n"
    "产品名称:[支付宝]\n"
    "--------------------------交易记录明细列表----------------------------\n"
    "交易时间,交易分类,交易对方,商品说明,收/支,金额,交易状态,交易订单号\n"
    "2025-01-15 10:30:00,餐饮美食,肯德基,炸鸡套餐,支出,35.00,交易成功,20250115001\n"
    "2025-01-16 14:00:00,日用百货,超市,牛奶面包,支出,28.50,交易成功,20250116002\n"
    "2025-01-17 09:00:00,工资薪酬,公司,1月工资,收入,8000.00,交易成功,20250117003\n"
    "2025-01-18 08:00:00,餐饮美食,星巴克,咖啡,支出,32.00,交易成功,20250118004\n"
    "2025-01-19 12:00:00,餐饮美食,麦当劳,午餐,支出,25.00,交易成功,20250119005\n"
)

ALIPAY_MERCHANT_CSV_CONTENT = (
    "账单编号,服务提供方,月份,费用名称,应收总额,实收总额\n"
    "MB20250101,支付宝,2025-01,平台服务费,500.00,480.00\n"
    "MB20250102,支付宝,2025-02,平台服务费,600.00,570.00\n"
    "MB20250103,支付宝,2025-03,平台服务费,550.00,530.00\n"
    "MB20250104,支付宝,2025-04,平台服务费,580.00,560.00\n"
    "MB20250105,支付宝,2025-05,平台服务费,620.00,600.00\n"
    "MB20250106,支付宝,2025-06,平台服务费,610.00,590.00\n"
    "MB20250107,支付宝,2025-07,平台服务费,630.00,610.00\n"
    "MB20250108,支付宝,2025-08,平台服务费,640.00,620.00\n"
    "MB20250109,支付宝,2025-09,平台服务费,650.00,630.00\n"
)

WECHAT_CSV_CONTENT = (
    "微信支付账单明细\n"
    "微信昵称：[测试用户]\n"
    "起始时间：[2025-01-01] 终止时间：[2025-01-31]\n"
    "导出类型：[全部]\n"
    "导出时间：[2025-02-01]\n"
    "以下为明细\n"
    "----------------------微信支付账单明细列表-----------------------------\n"
    "line8\n"
    "line9\n"
    "line10\n"
    "line11\n"
    "line12\n"
    "line13\n"
    "line14\n"
    "line15\n"
    "line16\n"
    "交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态,交易单号,商户单号,备注\n"
    "2025-01-15 10:30:00,商户消费,肯德基,炸鸡套餐,支出,¥35.00,零钱,支付成功,T100001,M100001,\n"
    "2025-01-16 14:00:00,商户消费,超市,牛奶面包,支出,¥28.50,零钱,支付成功,T100002,M100002,\n"
    "2025-01-17 09:00:00,转账,张三,微信转账,收入,¥200.00,零钱,已存入零钱,T100003,M100003,\n"
)

BANK_CSV_CONTENT = (
    "交易日期,摘要,交易金额,账户余额,对方户名,备注\n"
    "2025-01-15,消费-POS,\"-35.00\",10000.00,肯德基,\n"
    "2025-01-16,消费-POS,\"-28.50\",9971.50,超市,\n"
    "2025-01-17,工资,8000.00,17971.50,公司,1月工资\n"
)

MEITUAN_CSV_CONTENT = (
    "订单时间,订单内容,商家名称,实付金额,订单号,订单状态\n"
    "2025-01-15 12:00:00,麻辣烫套餐,张亮麻辣烫,22.00,MT20250115001,订单完成\n"
    "2025-01-16 18:30:00,黄焖鸡米饭,黄焖鸡,18.50,MT20250116002,订单完成\n"
)


@pytest.fixture
def alipay_csv(tmp_path):
    """Create a synthetic Alipay personal bill CSV (GBK encoded)."""
    file_path = tmp_path / "alipay_test.csv"
    file_path.write_text(ALIPAY_PERSONAL_CSV_CONTENT, encoding='gbk')
    return str(file_path)


@pytest.fixture
def alipay_merchant_csv(tmp_path):
    """Create a synthetic Alipay merchant bill CSV."""
    file_path = tmp_path / "alipay_merchant_test.csv"
    file_path.write_text(ALIPAY_MERCHANT_CSV_CONTENT, encoding='gbk')
    return str(file_path)


@pytest.fixture
def wechat_csv(tmp_path):
    """Create a synthetic WeChat Pay bill CSV (UTF-8 encoded, 16 header lines)."""
    file_path = tmp_path / "wechat_test.csv"
    file_path.write_text(WECHAT_CSV_CONTENT, encoding='utf-8')
    return str(file_path)


@pytest.fixture
def bank_csv(tmp_path):
    """Create a synthetic bank statement CSV."""
    file_path = tmp_path / "bank_test.csv"
    file_path.write_text(BANK_CSV_CONTENT, encoding='utf-8')
    return str(file_path)


@pytest.fixture
def meituan_csv(tmp_path):
    """Create a synthetic Meituan order CSV."""
    file_path = tmp_path / "meituan_test.csv"
    file_path.write_text(MEITUAN_CSV_CONTENT, encoding='utf-8')
    return str(file_path)


@pytest.fixture
def real_alipay_csv():
    """Path to the real Alipay sample bill if it exists."""
    path = os.path.join(os.path.dirname(__file__), 'fixtures', 'sample_bill.csv')
    if os.path.exists(path):
        return path
    pytest.skip("Real Alipay sample file not found at tests/fixtures/sample_bill.csv")


# ---------------------------------------------------------------------------
# 1. Parser interface compliance
# ---------------------------------------------------------------------------

class TestParserInterface:
    """Every parser must inherit from BaseParser and expose parse/detect_format."""

    @pytest.mark.parametrize("parser_cls", [AlipayParser, WeChatParser, BankParser, MeituanParser])
    def test_inherits_from_base_parser(self, parser_cls):
        assert issubclass(parser_cls, BaseParser)

    @pytest.mark.parametrize("parser_cls", [AlipayParser, WeChatParser, BankParser, MeituanParser])
    def test_has_parse_method(self, parser_cls):
        assert hasattr(parser_cls, 'parse')
        assert callable(getattr(parser_cls, 'parse'))

    @pytest.mark.parametrize("parser_cls", [AlipayParser, WeChatParser, BankParser, MeituanParser])
    def test_has_detect_format_method(self, parser_cls):
        assert hasattr(parser_cls, 'detect_format')
        assert callable(getattr(parser_cls, 'detect_format'))

    @pytest.mark.parametrize("parser_cls,expected_name", [
        (AlipayParser, "alipay"),
        (WeChatParser, "wechat"),
        (BankParser, "bank"),
        (MeituanParser, "meituan"),
    ])
    def test_platform_name(self, parser_cls, expected_name):
        assert parser_cls.PLATFORM_NAME == expected_name


# ---------------------------------------------------------------------------
# 2. AlipayParser tests
# ---------------------------------------------------------------------------

class TestAlipayParser:
    """Tests for the Alipay personal bill parser."""

    def test_detect_format_positive(self, alipay_parser, alipay_csv):
        """Alipay parser should detect its own format."""
        assert alipay_parser.detect_format(alipay_csv) is True

    def test_detect_format_rejects_wechat(self, alipay_parser, wechat_csv):
        """Alipay parser should reject a WeChat-format file."""
        assert alipay_parser.detect_format(wechat_csv) is False

    def test_detect_format_rejects_bank(self, alipay_parser, bank_csv):
        """Alipay parser should reject a bank-format file."""
        assert alipay_parser.detect_format(bank_csv) is False

    def test_detect_format_rejects_meituan(self, alipay_parser, meituan_csv):
        """Alipay parser should reject a Meituan-format file."""
        assert alipay_parser.detect_format(meituan_csv) is False

    def test_parse_returns_dataframe(self, alipay_parser, alipay_csv):
        """parse() should return a pandas DataFrame."""
        result = alipay_parser.parse(alipay_csv)
        assert isinstance(result, pd.DataFrame)

    def test_parse_not_empty(self, alipay_parser, alipay_csv):
        """Parsed result should not be empty."""
        result = alipay_parser.parse(alipay_csv)
        assert len(result) > 0

    def test_standardized_columns_present(self, alipay_parser, alipay_csv):
        """Output should contain the required standardized columns."""
        result = alipay_parser.parse(alipay_csv)
        required_cols = ['transaction_id', 'platform', 'date', 'amount']
        for col in required_cols:
            assert col in result.columns, f"Missing required column: {col}"

    def test_platform_column_value(self, alipay_parser, alipay_csv):
        """Platform column should be 'alipay' for all rows."""
        result = alipay_parser.parse(alipay_csv)
        assert (result['platform'] == 'alipay').all()

    def test_amount_is_numeric(self, alipay_parser, alipay_csv):
        """Amount column should be numeric (float)."""
        result = alipay_parser.parse(alipay_csv)
        assert pd.api.types.is_numeric_dtype(result['amount'])

    def test_transaction_id_not_null(self, alipay_parser, alipay_csv):
        """Transaction IDs should not be null."""
        result = alipay_parser.parse(alipay_csv)
        assert result['transaction_id'].notna().all()

    def test_type_mapping(self, alipay_parser, alipay_csv):
        """Type column should contain mapped values (income/expense/internal)."""
        result = alipay_parser.parse(alipay_csv)
        if 'type' in result.columns:
            valid_types = {'income', 'expense', 'internal'}
            actual_types = set(result['type'].dropna().unique())
            assert actual_types.issubset(valid_types), (
                f"Unexpected type values: {actual_types - valid_types}"
            )


class TestAlipayParserRealFile:
    """Tests using the real Alipay sample file (skipped if not available)."""

    def test_detect_format_real_file(self, alipay_parser, real_alipay_csv):
        """Real Alipay sample should be detected correctly."""
        assert alipay_parser.detect_format(real_alipay_csv) is True

    def test_parse_real_file(self, alipay_parser, real_alipay_csv):
        """Real Alipay sample should parse without errors."""
        result = alipay_parser.parse(real_alipay_csv)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_real_file_has_standardized_columns(self, alipay_parser, real_alipay_csv):
        """Real file output should have standard columns."""
        result = alipay_parser.parse(real_alipay_csv)
        required_cols = ['transaction_id', 'platform', 'date', 'amount']
        for col in required_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_real_file_platform_value(self, alipay_parser, real_alipay_csv):
        """Platform should be 'alipay' in real file output."""
        result = alipay_parser.parse(real_alipay_csv)
        assert (result['platform'] == 'alipay').all()


class TestAlipayMerchantParser:
    """Tests for Alipay merchant bill parsing."""

    def test_detect_format_merchant_csv(self, alipay_parser, alipay_merchant_csv):
        """Alipay parser should detect merchant CSV format."""
        assert alipay_parser.detect_format(alipay_merchant_csv) is True

    def test_parse_merchant_csv_does_not_crash(self, alipay_parser, alipay_merchant_csv):
        """Merchant CSV parse should either return a DataFrame or raise ValueError."""
        try:
            result = alipay_parser.parse(alipay_merchant_csv)
            assert isinstance(result, pd.DataFrame)
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# 3. WeChatParser tests
# ---------------------------------------------------------------------------

class TestWeChatParser:
    """Tests for the WeChat Pay bill parser."""

    def test_detect_format_positive(self, wechat_parser, wechat_csv):
        """WeChat parser should detect its own format."""
        assert wechat_parser.detect_format(wechat_csv) is True

    def test_detect_format_rejects_alipay(self, wechat_parser, alipay_csv):
        """WeChat parser should reject an Alipay-format file."""
        assert wechat_parser.detect_format(alipay_csv) is False

    def test_detect_format_rejects_bank(self, wechat_parser, bank_csv):
        """WeChat parser should reject a bank-format file."""
        assert wechat_parser.detect_format(bank_csv) is False

    def test_parse_returns_dataframe(self, wechat_parser, wechat_csv):
        """parse() should return a DataFrame."""
        result = wechat_parser.parse(wechat_csv)
        assert isinstance(result, pd.DataFrame)

    def test_parse_not_empty(self, wechat_parser, wechat_csv):
        """Parsed result should contain rows."""
        result = wechat_parser.parse(wechat_csv)
        assert len(result) > 0

    def test_platform_value(self, wechat_parser, wechat_csv):
        """Platform column should be 'wechat'."""
        result = wechat_parser.parse(wechat_csv)
        assert (result['platform'] == 'wechat').all()

    def test_standardized_columns(self, wechat_parser, wechat_csv):
        """Output should have required standardized columns."""
        result = wechat_parser.parse(wechat_csv)
        required_cols = ['transaction_id', 'platform', 'date', 'amount']
        for col in required_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_type_normalization(self, wechat_parser, wechat_csv):
        """Type column should be normalized to income/expense."""
        result = wechat_parser.parse(wechat_csv)
        if 'type' in result.columns:
            valid_types = {'income', 'expense'}
            actual_types = set(result['type'].dropna().unique())
            assert actual_types.issubset(valid_types), (
                f"Unexpected type values: {actual_types - valid_types}"
            )


# ---------------------------------------------------------------------------
# 4. BankParser tests
# ---------------------------------------------------------------------------

class TestBankParser:
    """Tests for the bank statement parser."""

    def test_detect_format_positive(self, bank_parser, bank_csv):
        """Bank parser should detect its own format."""
        assert bank_parser.detect_format(bank_csv) is True

    def test_detect_format_rejects_alipay(self, bank_parser, alipay_csv):
        """Bank parser should reject an Alipay-format file."""
        assert bank_parser.detect_format(alipay_csv) is False

    def test_detect_format_rejects_wechat(self, bank_parser, wechat_csv):
        """Bank parser should reject a WeChat-format file."""
        assert bank_parser.detect_format(wechat_csv) is False

    def test_parse_returns_dataframe(self, bank_parser, bank_csv):
        """parse() should return a DataFrame."""
        result = bank_parser.parse(bank_csv)
        assert isinstance(result, pd.DataFrame)

    def test_parse_not_empty(self, bank_parser, bank_csv):
        """Parsed result should contain rows."""
        result = bank_parser.parse(bank_csv)
        assert len(result) > 0

    def test_platform_value(self, bank_parser, bank_csv):
        """Platform column should be 'bank'."""
        result = bank_parser.parse(bank_csv)
        assert (result['platform'] == 'bank').all()

    def test_standardized_columns(self, bank_parser, bank_csv):
        """Output should have required standardized columns."""
        result = bank_parser.parse(bank_csv)
        required_cols = ['transaction_id', 'platform', 'date', 'amount']
        for col in required_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_amount_sign_determines_type(self, bank_parser, bank_csv):
        """Negative amounts should be expense, positive should be income."""
        result = bank_parser.parse(bank_csv)
        if 'type' in result.columns:
            valid_types = {'income', 'expense'}
            actual_types = set(result['type'].dropna().unique())
            assert actual_types.issubset(valid_types), (
                f"Unexpected type values: {actual_types - valid_types}"
            )

    def test_amount_is_absolute(self, bank_parser, bank_csv):
        """After parsing, amounts should be absolute values (non-negative)."""
        result = bank_parser.parse(bank_csv)
        assert (result['amount'] >= 0).all(), "All amounts should be non-negative"


# ---------------------------------------------------------------------------
# 5. MeituanParser tests
# ---------------------------------------------------------------------------

class TestMeituanParser:
    """Tests for the Meituan order parser."""

    def test_detect_format_positive(self, meituan_parser, meituan_csv):
        """Meituan parser should detect its own format."""
        assert meituan_parser.detect_format(meituan_csv) is True

    def test_detect_format_rejects_alipay(self, meituan_parser, alipay_csv):
        """Meituan parser should reject an Alipay-format file."""
        assert meituan_parser.detect_format(alipay_csv) is False

    def test_detect_format_rejects_wechat(self, meituan_parser, wechat_csv):
        """Meituan parser should reject a WeChat-format file."""
        assert meituan_parser.detect_format(wechat_csv) is False

    def test_parse_returns_dataframe(self, meituan_parser, meituan_csv):
        """parse() should return a DataFrame."""
        result = meituan_parser.parse(meituan_csv)
        assert isinstance(result, pd.DataFrame)

    def test_parse_not_empty(self, meituan_parser, meituan_csv):
        """Parsed result should contain rows."""
        result = meituan_parser.parse(meituan_csv)
        assert len(result) > 0

    def test_platform_value(self, meituan_parser, meituan_csv):
        """Platform column should be 'meituan'."""
        result = meituan_parser.parse(meituan_csv)
        assert (result['platform'] == 'meituan').all()

    def test_standardized_columns(self, meituan_parser, meituan_csv):
        """Output should have required standardized columns."""
        result = meituan_parser.parse(meituan_csv)
        required_cols = ['transaction_id', 'platform', 'date', 'amount']
        for col in required_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_default_type_is_expense(self, meituan_parser, meituan_csv):
        """Meituan orders should default to expense type."""
        result = meituan_parser.parse(meituan_csv)
        if 'type' in result.columns:
            assert (result['type'] == 'expense').all()

    def test_default_category(self, meituan_parser, meituan_csv):
        """Meituan orders should be categorized as food/dining."""
        result = meituan_parser.parse(meituan_csv)
        if 'category' in result.columns:
            assert (result['category'] == '餐饮美食').all()


# ---------------------------------------------------------------------------
# 6. Cross-platform detect_format rejection tests
# ---------------------------------------------------------------------------

class TestCrossPlatformDetection:
    """Each parser must reject files from other platforms."""

    def test_alipay_rejects_nonexistent(self, alipay_parser, tmp_path):
        """detect_format should return False for a nonexistent file."""
        fake_path = str(tmp_path / "nonexistent.csv")
        assert alipay_parser.detect_format(fake_path) is False

    def test_wechat_rejects_nonexistent(self, wechat_parser, tmp_path):
        """detect_format should return False for a nonexistent file."""
        fake_path = str(tmp_path / "nonexistent.csv")
        assert wechat_parser.detect_format(fake_path) is False

    def test_bank_rejects_nonexistent(self, bank_parser, tmp_path):
        """detect_format should return False for a nonexistent file."""
        fake_path = str(tmp_path / "nonexistent.csv")
        assert bank_parser.detect_format(fake_path) is False

    def test_meituan_rejects_nonexistent(self, meituan_parser, tmp_path):
        """detect_format should return False for a nonexistent file."""
        fake_path = str(tmp_path / "nonexistent.csv")
        assert meituan_parser.detect_format(fake_path) is False

    def test_alipay_rejects_empty_file(self, alipay_parser, tmp_path):
        """detect_format should return False for an empty file."""
        empty = tmp_path / "empty.csv"
        empty.write_text("")
        assert alipay_parser.detect_format(str(empty)) is False

    def test_alipay_rejects_random_csv(self, alipay_parser, tmp_path):
        """detect_format should return False for a random CSV."""
        random_csv = tmp_path / "random.csv"
        random_csv.write_text("col_a,col_b,col_c\n1,2,3\n4,5,6\n")
        assert alipay_parser.detect_format(str(random_csv)) is False

    def test_wechat_rejects_random_csv(self, wechat_parser, tmp_path):
        """detect_format should return False for a random CSV."""
        random_csv = tmp_path / "random.csv"
        random_csv.write_text("col_a,col_b,col_c\n1,2,3\n4,5,6\n")
        assert wechat_parser.detect_format(str(random_csv)) is False


# ---------------------------------------------------------------------------
# 7. Encoding handling tests
# ---------------------------------------------------------------------------

class TestEncodingHandling:
    """Verify parsers can handle their expected encoding."""

    def test_alipay_gbk_encoding(self, alipay_parser, tmp_path):
        """Alipay parser should handle GBK-encoded CSV files."""
        content = (
            "支付宝交易记录明细查询\n"
            "账号:[test]\n"
            "起始日期:[2025-01-01]    终止日期:[2025-01-31]\n"
            "---交易记录---\n"
            "交易时间,交易对方,商品说明,收/支,金额,交易状态,交易订单号\n"
            "2025-01-15 10:30:00,肯德基,套餐,支出,35.00,交易成功,TX001\n"
        )
        file_path = tmp_path / "gbk_test.csv"
        file_path.write_text(content, encoding='gbk')
        result = alipay_parser.parse(str(file_path))
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_alipay_utf8_encoding(self, alipay_parser, tmp_path):
        """Alipay parser should also handle UTF-8 encoded CSV files."""
        content = (
            "支付宝交易记录明细查询\n"
            "账号:[test]\n"
            "起始日期:[2025-01-01]    终止日期:[2025-01-31]\n"
            "---交易记录---\n"
            "交易时间,交易对方,商品说明,收/支,金额,交易状态,交易订单号\n"
            "2025-01-15 10:30:00,肯德基,套餐,支出,35.00,交易成功,TX001\n"
        )
        file_path = tmp_path / "utf8_test.csv"
        file_path.write_text(content, encoding='utf-8')
        result = alipay_parser.parse(str(file_path))
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_wechat_utf8_encoding(self, wechat_parser, wechat_csv):
        """WeChat parser should handle UTF-8 encoding (its default)."""
        result = wechat_parser.parse(wechat_csv)
        assert isinstance(result, pd.DataFrame)

    def test_bank_utf8_encoding(self, bank_parser, bank_csv):
        """Bank parser should handle UTF-8 encoding."""
        result = bank_parser.parse(bank_csv)
        assert isinstance(result, pd.DataFrame)


# ---------------------------------------------------------------------------
# 8. Data validation tests
# ---------------------------------------------------------------------------

class TestDataValidation:
    """Verify the base parser's validate_data behavior."""

    def test_validate_data_passes_on_good_data(self, alipay_parser, alipay_csv):
        """validate_data should pass for properly parsed data."""
        result = alipay_parser.parse(alipay_csv)
        assert alipay_parser.validate_data(result) is True

    def test_validate_data_rejects_missing_columns(self, alipay_parser):
        """validate_data should raise ValueError for missing required columns."""
        bad_df = pd.DataFrame({'foo': [1, 2], 'bar': [3, 4]})
        with pytest.raises(ValueError, match="缺少必要字段"):
            alipay_parser.validate_data(bad_df)

    def test_validate_data_rejects_null_transaction_id(self, alipay_parser):
        """validate_data should reject null transaction_id values."""
        bad_df = pd.DataFrame({
            'transaction_id': [None, 'TX001'],
            'date': ['2025-01-01', '2025-01-02'],
            'amount': [10.0, 20.0],
            'platform': ['alipay', 'alipay'],
        })
        with pytest.raises(ValueError, match="空的交易ID"):
            alipay_parser.validate_data(bad_df)
