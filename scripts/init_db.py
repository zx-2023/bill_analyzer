"""初始化数据库脚本"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.models import Base
from src.database.models_extended import SubscriptionPattern, AnomalyRecord, MonthlyStatistics, BudgetPlan
from src.database.operations import DatabaseManager


def init_database():
    """初始化数据库和基础数据"""
    print("正在初始化数据库...")

    db = DatabaseManager()
    db.init_db()

    print("数据库表创建成功！")

    # 初始化默认分类
    default_categories = [
        {"name": "餐饮美食", "icon": "🍔", "color": "#FF6B6B"},
        {"name": "交通出行", "icon": "🚗", "color": "#4ECDC4"},
        {"name": "购物消费", "icon": "🛍️", "color": "#45B7D1"},
        {"name": "居家生活", "icon": "🏠", "color": "#96CEB4"},
        {"name": "文化娱乐", "icon": "🎬", "color": "#FFEAA7"},
        {"name": "医疗健康", "icon": "💊", "color": "#DFE6E9"},
        {"name": "教育培训", "icon": "📚", "color": "#74B9FF"},
        {"name": "人情往来", "icon": "🎁", "color": "#FD79A8"},
        {"name": "金融保险", "icon": "💰", "color": "#FDCB6E"},
        {"name": "通讯充值", "icon": "📱", "color": "#6C5CE7"},
        {"name": "其他", "icon": "📦", "color": "#B2BEC3"}
    ]

    print("正在创建默认分类...")
    for cat in default_categories:
        try:
            db.add_category(**cat)
            print(f"  ✓ {cat['name']}")
        except Exception as e:
            print(f"  ✗ {cat['name']} 创建失败: {str(e)}")

    print("\n数据库初始化完成！")


if __name__ == "__main__":
    init_database()
