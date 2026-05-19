"""银行账单解析器"""
import pandas as pd
from .base_parser import BaseParser


class BankParser(BaseParser):
    """银行账单解析器

    支持多种银行格式，通过金额正负判断收支
    """

    PLATFORM_NAME = "bank"

    def parse(self, file_path: str) -> pd.DataFrame:
        """
        解析银行账单

        银行账单特点：
        - 通常用金额正负表示收支（正为收入，负为支出）
        - 列名：交易日期、摘要、交易金额、账户余额
        - 可能包含借贷标识
        """
        # 读取原始文件
        df = self.read_file(file_path)

        # 合并日期和时间列（如果分开）
        df = self._merge_date_time(df)

        # 标准化字段
        df_standard = self.standardize(df)

        # 根据金额符号判断收支类型
        df_standard = self._determine_type_by_amount(df_standard)

        # 验证数据
        self.validate_data(df_standard)

        return df_standard

    def detect_format(self, file_path: str) -> bool:
        """
        检测是否为银行账单格式
        """
        try:
            # 尝试读取前几行
            df = pd.read_csv(file_path, encoding='utf-8', nrows=5)

            detection_features = self.platform_config.get('detection_features', {})
            required_columns = detection_features.get('column_names', [])

            # 检查是否包含银行特征列
            has_required_columns = all(col in df.columns for col in required_columns)

            # 检查关键字
            header_keywords = detection_features.get('header_keywords', [])
            file_content = df.to_string()
            has_keywords = any(keyword in file_content for keyword in header_keywords)

            return has_required_columns or has_keywords

        except Exception:
            return False

    def _merge_date_time(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        合并日期和时间列

        有些银行账单会将日期和时间分为两列
        """
        if 'date' in df.columns and 'time' in df.columns:
            # 合并日期时间
            df['date'] = pd.to_datetime(
                df['date'].astype(str) + ' ' + df['time'].astype(str),
                errors='coerce'
            )
            df = df.drop(columns=['time'])

        return df

    def _determine_type_by_amount(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        根据金额正负判断收支类型

        银行账单中：
        - 正数：收入（存入）
        - 负数：支出（支取）
        """
        if 'amount' not in df.columns:
            return df

        # 如果已有type字段且不为空，保留
        if 'type' in df.columns:
            df['type'] = df.apply(
                lambda row: row['type'] if pd.notna(row['type']) and row['type'] != ''
                else ('income' if row['amount'] > 0 else 'expense'),
                axis=1
            )
        else:
            # 根据金额符号判断
            df['type'] = df['amount'].apply(
                lambda x: 'income' if x > 0 else 'expense'
            )

        # 将金额转为绝对值（符号由type字段表示）
        df['amount'] = df['amount'].abs()

        return df
