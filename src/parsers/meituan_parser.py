"""美团账单解析器"""
import pandas as pd
from .base_parser import BaseParser


class MeituanParser(BaseParser):
    """美团账单解析器"""

    PLATFORM_NAME = "meituan"

    def parse(self, file_path: str) -> pd.DataFrame:
        """
        解析美团账单

        美团账单特点：
        - 主要是外卖和团购订单
        - 列名：订单时间、订单内容、商家名称、实付金额
        - 默认都是支出
        """
        # 读取原始文件
        df = self.read_file(file_path)

        # 标准化字段
        df_standard = self.standardize(df)

        # 设置默认交易类型为支出
        if 'type' not in df_standard.columns or df_standard['type'].isna().all():
            df_standard['type'] = self.platform_config.get('default_type', 'expense')

        # 美团订单默认分类为"餐饮美食-外卖"
        df_standard['category'] = '餐饮美食'
        df_standard['subcategory'] = '外卖'

        # 验证数据
        self.validate_data(df_standard)

        return df_standard

    def detect_format(self, file_path: str) -> bool:
        """
        检测是否为美团账单格式
        """
        try:
            # 尝试读取前几行
            df = pd.read_csv(file_path, encoding='utf-8', nrows=5)

            detection_features = self.platform_config.get('detection_features', {})
            required_columns = detection_features.get('column_names', [])

            # 检查是否包含美团特征列
            has_required_columns = all(col in df.columns for col in required_columns)

            # 检查关键字
            header_keywords = detection_features.get('header_keywords', [])
            file_content = df.to_string()
            has_keywords = any(keyword in file_content for keyword in header_keywords)

            return has_required_columns or has_keywords

        except Exception:
            return False
