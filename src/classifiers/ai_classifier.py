"""基于AI的分类器（Kimi API）"""
import os
import requests
import yaml
from typing import Dict, Optional
from dotenv import load_dotenv


class AIClassifier:
    """AI分类器（使用Kimi API）"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        config_path: str = "config/classification_rules.yaml"
    ):
        """
        初始化AI分类器

        Args:
            api_key: Kimi API密钥
            api_url: Kimi API地址
            model: 使用的模型
            config_path: 配置文件路径
        """
        # 加载环境变量
        load_dotenv()

        self.api_key = api_key or os.getenv('KIMI_API_KEY')
        self.api_url = api_url or os.getenv('KIMI_API_URL', 'https://api.moonshot.cn/v1/chat/completions')
        self.model = model or os.getenv('KIMI_MODEL', 'kimi-k2-turbo-preview')

        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.prompt_template = self.config.get('ai_prompt_template', '')

        if not self.api_key:
            raise ValueError("未配置KIMI_API_KEY，请在.env文件中设置")

    def classify(self, transaction: Dict, timeout: int = 30) -> str:
        """
        使用AI对交易进行分类

        Args:
            transaction: 交易字典
            timeout: 超时时间（秒）

        Returns:
            分类名称
        """
        # 构建提示词
        prompt = self.prompt_template.format(
            date=transaction.get('date', '未知'),
            amount=transaction.get('amount', 0),
            counterparty=transaction.get('counterparty', '未知'),
            description=transaction.get('description', '未知')
        )

        try:
            # 调用Kimi API
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3  # 降低随机性，保持分类一致性
                },
                timeout=timeout
            )

            response.raise_for_status()
            result = response.json()

            # 提取分类结果
            category = result['choices'][0]['message']['content'].strip()

            # 清理可能的额外文本
            category = self._clean_category_name(category)

            return category

        except requests.exceptions.RequestException as e:
            print(f"AI分类请求失败: {str(e)}")
            return "其他"
        except (KeyError, IndexError) as e:
            print(f"AI分类响应解析失败: {str(e)}")
            return "其他"

    def classify_batch(self, transactions: list, batch_size: int = 10) -> list:
        """
        批量分类

        Args:
            transactions: 交易列表
            batch_size: 每批数量

        Returns:
            分类结果列表
        """
        results = []

        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i + batch_size]

            for transaction in batch:
                category = self.classify(transaction)
                results.append(category)

        return results

    def _clean_category_name(self, category: str) -> str:
        """
        清理分类名称

        AI可能返回带解释的文本，需要提取分类名称
        """
        # 移除可能的前缀
        prefixes = ['分类：', '分类:', '类别：', '类别:']
        for prefix in prefixes:
            if category.startswith(prefix):
                category = category[len(prefix):].strip()

        # 只保留第一行（如果有多行）
        category = category.split('\n')[0].strip()

        # 移除引号
        category = category.strip('"\'')

        return category

    def validate_api_key(self) -> bool:
        """
        验证API密钥是否有效

        Returns:
            是否有效
        """
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": "测试"}
                    ],
                    "max_tokens": 10
                },
                timeout=10
            )

            return response.status_code == 200

        except:
            return False
