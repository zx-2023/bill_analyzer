"""混合分类器（规则优先+AI辅助）"""
from typing import Dict, Tuple
from .rule_classifier import RuleClassifier
from .ai_classifier import AIClassifier


class HybridClassifier:
    """混合分类器"""

    def __init__(
        self,
        confidence_threshold: float = 0.8,
        use_ai: bool = False
    ):
        """
        初始化混合分类器

        Args:
            confidence_threshold: 规则分类置信度阈值，低于此值时使用AI
            use_ai: 是否启用AI分类
        """
        self.rule_classifier = RuleClassifier()
        self.ai_classifier = None
        self.confidence_threshold = confidence_threshold
        self.use_ai = use_ai

        # 尝试初始化AI分类器
        if use_ai:
            try:
                self.ai_classifier = AIClassifier()
                # 验证API密钥
                if not self.ai_classifier.validate_api_key():
                    print("警告：Kimi API密钥无效，将只使用规则分类")
                    self.ai_classifier = None
                    self.use_ai = False
            except Exception as e:
                print(f"警告：AI分类器初始化失败 - {str(e)}，将只使用规则分类")
                self.ai_classifier = None
                self.use_ai = False

    def classify(self, transaction: Dict) -> Tuple[str, float, str]:
        """
        对交易进行分类

        Args:
            transaction: 交易字典

        Returns:
            (分类名称, 置信度, 分类方法)
        """
        # Step 1: 尝试规则分类
        category, confidence = self.rule_classifier.classify(transaction)

        if confidence >= self.confidence_threshold:
            # 高置信度，直接返回规则分类结果
            return category, confidence, "rule"

        # Step 2: 低置信度，尝试使用AI
        if self.use_ai and self.ai_classifier:
            try:
                ai_category = self.ai_classifier.classify(transaction)

                # 验证AI分类结果是否有效
                if ai_category in self.rule_classifier.get_categories():
                    return ai_category, 0.9, "ai"  # AI分类默认给0.9置信度
                else:
                    # AI返回了未知分类，使用规则结果
                    return category if category else "其他", confidence, "rule"

            except Exception as e:
                print(f"AI分类失败: {str(e)}")
                return category if category else "其他", confidence, "rule"

        # 没有AI或AI不可用，返回规则结果
        return category if category else "其他", confidence, "rule"

    def classify_batch(self, transactions: list) -> list:
        """
        批量分类

        Args:
            transactions: 交易列表

        Returns:
            分类结果列表 [(category, confidence, method), ...]
        """
        results = []

        # 先用规则分类所有交易
        for transaction in transactions:
            category, confidence, method = self.classify(transaction)
            results.append({
                'transaction': transaction,
                'category': category,
                'confidence': confidence,
                'method': method
            })

        return results

    def enable_ai(self):
        """启用AI分类"""
        if not self.ai_classifier:
            try:
                self.ai_classifier = AIClassifier()
                self.use_ai = True
            except Exception as e:
                print(f"启用AI失败: {str(e)}")

    def disable_ai(self):
        """禁用AI分类"""
        self.use_ai = False

    def get_stats(self, results: list) -> dict:
        """
        获取分类统计

        Args:
            results: 分类结果列表

        Returns:
            统计信息
        """
        total = len(results)
        rule_count = sum(1 for r in results if r['method'] == 'rule')
        ai_count = sum(1 for r in results if r['method'] == 'ai')
        manual_count = sum(1 for r in results if r['method'] == 'manual')

        avg_confidence = sum(r['confidence'] for r in results) / total if total > 0 else 0

        return {
            'total': total,
            'rule_classified': rule_count,
            'ai_classified': ai_count,
            'manual_classified': manual_count,
            'average_confidence': avg_confidence
        }
