"""微信支付账单解析器"""
import pandas as pd
from .base_parser import BaseParser


class WeChatParser(BaseParser):
    """微信支付账单解析器"""

    PLATFORM_NAME = "wechat"

    def parse(self, file_path: str) -> pd.DataFrame:
        """
        解析微信支付账单

        微信账单特点：
        - CSV文件前16行是说明信息
        - 编码：UTF-8
        - 列名包含：交易时间、交易类型、交易对方、商品、收/支、金额(元)
        """
        # 读取原始文件
        df = self.read_file(file_path)

        # 标准化字段
        df_standard = self.standardize(df)

        # 处理微信特殊的收支标识
        df_standard = self._normalize_type(df_standard)

        # 验证数据
        self.validate_data(df_standard)

        return df_standard

    def detect_format(self, file_path: str) -> bool:
        """
        检测是否为微信支付账单格式
        """
        try:
            # 尝试读取（跳过前16行）
            df = pd.read_csv(file_path, encoding='utf-8', skiprows=16, nrows=5)

            detection_features = self.platform_config.get('detection_features', {})
            required_columns = detection_features.get('column_names', [])

            # 检查是否包含微信特征列
            has_required_columns = all(col in df.columns for col in required_columns)

            # 检查是否包含微信关键字
            header_keywords = detection_features.get('header_keywords', [])

            # 读取文件头部检查关键字
            with open(file_path, 'r', encoding='utf-8') as f:
                first_lines = ''.join([next(f) for _ in range(16)])
                has_keywords = any(keyword in first_lines for keyword in header_keywords)

            return has_required_columns or has_keywords

        except Exception:
            return False

    def _normalize_type(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        规范化收支类型

        微信的收/支字段可能有多种格式：
        - "收入"、"支出"
        - "/"（表示收入）
        - 有时为空
        """
        if 'type' not in df.columns:
            return df

        def clean_type(val):
            val_str = str(val).strip()

            if val_str in ['收入', '/']:
                return 'income'
            elif val_str in ['支出', '支']:
                return 'expense'
            else:
                # 根据金额正负判断（如果金额有符号）
                return 'expense'  # 默认为支出

        df['type'] = df['type'].apply(clean_type)

        return df
