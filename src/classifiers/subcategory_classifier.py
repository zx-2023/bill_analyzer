"""二级分类器"""
import re
import yaml
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional


class SubcategoryClassifier:
    """二级分类器 - 在一级分类基础上进行细分"""

    def __init__(self, config_path: str = "config/subcategory_rules.yaml"):
        """
        初始化二级分类器

        Args:
            config_path: 二级分类规则配置文件路径
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.subcategory_rules = yaml.safe_load(f)

    def classify(
        self,
        primary_category: str,
        transaction: Dict
    ) -> Tuple[Optional[str], float]:
        """
        对交易进行二级分类

        Args:
            primary_category: 一级分类名称
            transaction: 交易字典

        Returns:
            (二级分类名称, 置信度)
        """
        # 如果一级分类不存在或没有二级分类规则
        if primary_category not in self.subcategory_rules:
            return None, 0.0

        try:
            # 确保值为字符串类型
            description = transaction.get('description', '')
            if description is not None and not isinstance(description, str):
                description = str(description)
            description = description.lower() if description else ''
            
            counterparty = transaction.get('counterparty', '')
            if counterparty is not None and not isinstance(counterparty, str):
                counterparty = str(counterparty)
            counterparty = counterparty.lower() if counterparty else ''
            
            combined_text = f"{description} {counterparty}"
        except AttributeError as e:
            # 如果仍然出错，打印详细信息
            print(f"DEBUG: Error in subcategory classifier")
            print(f"  description type: {type(transaction.get('description'))}, value: {transaction.get('description')}")
            print(f"  counterparty type: {type(transaction.get('counterparty'))}, value: {transaction.get('counterparty')}")
            raise

        subcategories = self.subcategory_rules[primary_category]

        best_subcategory = None
        best_confidence = 0.0

        # 遍历该一级分类下的所有二级分类
        for subcategory, rules in subcategories.items():
            confidence = self._match_subcategory(combined_text, description, counterparty, rules)

            if confidence > best_confidence:
                best_confidence = confidence
                best_subcategory = subcategory

        return best_subcategory, best_confidence

    def _match_subcategory(
        self,
        combined_text: str,
        description: str,
        counterparty: str,
        rules: Dict
    ) -> float:
        """
        匹配二级分类规则

        Args:
            combined_text: 合并文本
            description: 描述
            counterparty: 交易对方
            rules: 规则字典

        Returns:
            置信度分数
        """
        max_confidence = 0.0

        # 关键词匹配
        keywords = rules.get('keywords', [])
        for keyword in keywords:
            # 确保keyword是字符串
            keyword_str = str(keyword) if keyword is not None else ''
            if keyword_str.lower() in combined_text:
                max_confidence = max(max_confidence, 0.9)
                break

        # 商户匹配
        merchants = rules.get('merchants', [])
        for merchant in merchants:
            # 确保merchant是字符串
            merchant_str = str(merchant) if merchant is not None else ''
            if merchant_str.lower() in counterparty:
                max_confidence = max(max_confidence, 0.95)
                break

        # 排除关键词
        exclude_keywords = rules.get('exclude_keywords', [])
        for exclude_kw in exclude_keywords:
            # 确保exclude_kw是字符串
            exclude_str = str(exclude_kw) if exclude_kw is not None else ''
            if exclude_str.lower() in combined_text:
                max_confidence *= 0.3  # 大幅降低置信度
                break

        return max_confidence

    def classify_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        批量二级分类 - 使用向量化pandas操作替代逐行迭代

        Args:
            df: 包含 category, description, counterparty, is_duplicate 等字段的DataFrame

        Returns:
            添加了 subcategory 列的DataFrame
        """
        result_df = df.copy()

        if 'subcategory' not in result_df.columns:
            result_df['subcategory'] = None

        # 只处理有分类且非重复的行
        mask = df['category'].notna() & ~df['is_duplicate']
        classifiable = df[mask]

        if classifiable.empty:
            return result_df

        # 准备小写文本列
        desc = classifiable['description'].fillna('').astype(str).str.lower()
        counterparty_col = classifiable['counterparty'].fillna('').astype(str).str.lower()
        combined = desc + ' ' + counterparty_col

        # 按一级分类分组，组内向量化匹配
        for primary_category, group in classifiable.groupby('category'):
            if primary_category not in self.subcategory_rules:
                continue

            subcategories = self.subcategory_rules[primary_category]
            group_idx = group.index
            group_combined = combined.loc[group_idx]
            group_counterparty = counterparty_col.loc[group_idx]
            group_n = len(group_idx)

            best_subcat = np.full(group_n, None, dtype=object)
            best_conf = np.zeros(group_n)

            for subcategory, rules in subcategories.items():
                subcat_conf = np.zeros(group_n)

                # 关键词匹配 -> 0.9
                keywords = rules.get('keywords', [])
                if keywords:
                    escaped = [re.escape(str(kw).lower()) for kw in keywords if kw is not None]
                    if escaped:
                        pat = '|'.join(escaped)
                        kw_match = group_combined.str.contains(pat, na=False).values
                        np.maximum(subcat_conf, kw_match.astype(float) * 0.9, out=subcat_conf)

                # 商户匹配 -> 0.95
                merchants = rules.get('merchants', [])
                if merchants:
                    escaped = [re.escape(str(m).lower()) for m in merchants if m is not None]
                    if escaped:
                        pat = '|'.join(escaped)
                        m_match = group_counterparty.str.contains(pat, na=False).values
                        np.maximum(subcat_conf, m_match.astype(float) * 0.95, out=subcat_conf)

                # 排除关键词 -> 置信度乘以 0.3
                exclude_keywords = rules.get('exclude_keywords', [])
                if exclude_keywords:
                    escaped = [re.escape(str(ek).lower()) for ek in exclude_keywords if ek is not None]
                    if escaped:
                        pat = '|'.join(escaped)
                        ex_match = group_combined.str.contains(pat, na=False).values
                        subcat_conf = np.where(ex_match, subcat_conf * 0.3, subcat_conf)

                # 更新最佳二级分类
                better = subcat_conf > best_conf
                best_conf = np.where(better, subcat_conf, best_conf)
                best_subcat = np.where(better, subcategory, best_subcat)

            # 只在置信度 > 0.6 时赋值
            for i, idx in enumerate(group_idx):
                if best_subcat[i] is not None and best_conf[i] > 0.6:
                    result_df.at[idx, 'subcategory'] = best_subcat[i]

        return result_df

    def get_subcategories(self, primary_category: str) -> list:
        """
        获取指定一级分类下的所有二级分类

        Args:
            primary_category: 一级分类名称

        Returns:
            二级分类列表
        """
        if primary_category not in self.subcategory_rules:
            return []

        return list(self.subcategory_rules[primary_category].keys())
