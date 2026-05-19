"""基于规则的分类器"""
import re
import yaml
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional


class RuleClassifier:
    """规则分类器"""

    def __init__(self, config_path: str = "config/classification_rules.yaml"):
        """
        初始化规则分类器

        Args:
            config_path: 分类规则配置文件路径
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.categories = self.config.get('categories', {})
        self.confidence_levels = self.config.get('confidence', {})

    def classify(self, transaction: Dict) -> Tuple[Optional[str], float]:
        """
        对交易进行分类

        Args:
            transaction: 交易字典，包含description, counterparty等字段

        Returns:
            (分类名称, 置信度)
        """
        description = str(transaction.get('description', '')).lower()
        counterparty = str(transaction.get('counterparty', '')).lower()
        original_category = str(transaction.get('original_category', '')).lower()

        # 合并所有文本用于匹配
        combined_text = f"{description} {counterparty} {original_category}"

        best_category = None
        best_confidence = 0.0

        # 遍历所有分类规则
        for category, rules in self.categories.items():
            confidence = self._match_category(combined_text, description, counterparty, rules)

            if confidence > best_confidence:
                best_confidence = confidence
                best_category = category

        # 如果置信度太低，返回"其他"
        if best_confidence < 0.5:
            return "其他", best_confidence

        return best_category, best_confidence

    def classify_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        批量分类 - 使用向量化pandas操作替代逐行迭代

        Args:
            df: 包含 description, counterparty 等字段的DataFrame

        Returns:
            添加了 category, classification_confidence, classification_method 列的DataFrame
        """
        result_df = df.copy()
        n = len(df)

        if n == 0:
            result_df['category'] = pd.Series(dtype=str)
            result_df['classification_confidence'] = pd.Series(dtype=float)
            result_df['classification_method'] = pd.Series(dtype=str)
            return result_df

        # 准备小写文本列
        desc = df['description'].fillna('').astype(str).str.lower()
        counterparty = df['counterparty'].fillna('').astype(str).str.lower()
        if 'original_category' in df.columns:
            orig_cat = df['original_category'].fillna('').astype(str).str.lower()
        else:
            orig_cat = pd.Series('', index=df.index)
        combined = desc + ' ' + counterparty + ' ' + orig_cat

        high_conf = self.confidence_levels.get('high', 0.9)
        medium_conf = self.confidence_levels.get('medium', 0.7)

        best_category = np.full(n, '其他', dtype=object)
        best_confidence = np.zeros(n)

        # 遍历所有分类规则，向量化匹配
        for category, rules in self.categories.items():
            cat_confidence = np.zeros(n)

            # 1. 关键词匹配（高置信度） - 匹配 combined_text
            keywords = rules.get('keywords', [])
            if keywords:
                escaped = [re.escape(kw.lower()) for kw in keywords]
                pat = '|'.join(escaped)
                kw_match = combined.str.contains(pat, na=False).values
                np.maximum(cat_confidence, kw_match.astype(float) * high_conf, out=cat_confidence)

            # 2. 商户精确匹配（高置信度） - 匹配 counterparty
            merchants = rules.get('merchants', [])
            if merchants:
                escaped = [re.escape(m.lower()) for m in merchants]
                pat = '|'.join(escaped)
                m_match = counterparty.str.contains(pat, na=False).values
                np.maximum(cat_confidence, m_match.astype(float) * high_conf, out=cat_confidence)

            # 3. 正则表达式匹配（中置信度） - 匹配 combined_text
            patterns = rules.get('patterns', [])
            if patterns:
                # 尝试合并所有正则为一个模式
                try:
                    pat = '|'.join(patterns)
                    p_match = combined.str.contains(pat, case=False, na=False).values
                except re.error:
                    # 回退到逐个正则匹配
                    p_match = np.zeros(n, dtype=bool)
                    for p in patterns:
                        try:
                            p_match |= combined.str.contains(p, case=False, na=False).values
                        except re.error:
                            continue
                np.maximum(cat_confidence, p_match.astype(float) * medium_conf, out=cat_confidence)

            # 4. 检查排除关键词 - 降低置信度
            exclude_keywords = rules.get('exclude_keywords', [])
            if exclude_keywords:
                escaped = [re.escape(ek.lower()) for ek in exclude_keywords]
                pat = '|'.join(escaped)
                ex_match = combined.str.contains(pat, na=False).values
                cat_confidence = np.where(ex_match, cat_confidence * 0.5, cat_confidence)

            # 更新最佳分类
            better = cat_confidence > best_confidence
            best_confidence = np.where(better, cat_confidence, best_confidence)
            best_category = np.where(better, category, best_category)

        # 置信度太低时返回"其他"
        low_conf = best_confidence < 0.5
        best_category = np.where(low_conf, '其他', best_category)

        result_df['category'] = best_category
        result_df['classification_confidence'] = best_confidence
        result_df['classification_method'] = 'rule'

        return result_df

    def _match_category(
        self,
        combined_text: str,
        description: str,
        counterparty: str,
        rules: Dict
    ) -> float:
        """
        匹配分类规则

        Args:
            combined_text: 合并文本
            description: 描述
            counterparty: 交易对方
            rules: 规则字典

        Returns:
            置信度分数
        """
        max_confidence = 0.0

        # 1. 关键词匹配（高置信度）
        keywords = rules.get('keywords', [])
        for keyword in keywords:
            if keyword.lower() in combined_text:
                max_confidence = max(max_confidence, self.confidence_levels.get('high', 0.9))
                break

        # 2. 商户精确匹配（高置信度）
        merchants = rules.get('merchants', [])
        for merchant in merchants:
            if merchant.lower() in counterparty:
                max_confidence = max(max_confidence, self.confidence_levels.get('high', 0.9))
                break

        # 3. 正则表达式匹配（中置信度）
        patterns = rules.get('patterns', [])
        for pattern in patterns:
            try:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    max_confidence = max(max_confidence, self.confidence_levels.get('medium', 0.7))
                    break
            except re.error:
                continue

        # 4. 检查排除关键词
        exclude_keywords = rules.get('exclude_keywords', [])
        for exclude_kw in exclude_keywords:
            if exclude_kw.lower() in combined_text:
                # 如果包含排除关键词，降低置信度
                max_confidence *= 0.5
                break

        return max_confidence

    def get_categories(self) -> list:
        """获取所有分类名称"""
        return list(self.categories.keys())

    def add_learning_rule(
        self,
        category: str,
        rule_type: str,
        rule_value: str
    ):
        """
        添加学习到的新规则

        Args:
            category: 分类名称
            rule_type: 规则类型（keywords/merchants/patterns）
            rule_value: 规则值
        """
        if category not in self.categories:
            self.categories[category] = {
                'keywords': [],
                'merchants': [],
                'patterns': [],
                'exclude_keywords': []
            }

        if rule_type in self.categories[category]:
            if rule_value not in self.categories[category][rule_type]:
                self.categories[category][rule_type].append(rule_value)

    def save_rules(self, output_path: str = "config/classification_rules.yaml"):
        """
        保存规则到文件

        Args:
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, sort_keys=False)
