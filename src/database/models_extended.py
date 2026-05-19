"""扩展数据库模型 - 订阅模式和异常记录"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .models import Base


class SubscriptionPattern(Base):
    """订阅模式表 - 识别定期扣款模式"""
    __tablename__ = 'subscription_patterns'

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_name = Column(String(100), nullable=False)  # 订阅名称
    merchant = Column(String(200), nullable=False, index=True)  # 商户名称
    category = Column(String(50))  # 分类

    # 模式特征
    cycle = Column(String(20), nullable=False)  # monthly/yearly/weekly/daily
    typical_amount = Column(Float)  # 典型金额
    amount_variance = Column(Float)  # 金额波动范围（±）
    day_of_month = Column(Integer)  # 每月扣款日（如每月1号）

    # 统计信息
    detection_count = Column(Integer, default=0)  # 检测到的次数
    first_detected = Column(DateTime)  # 首次检测时间
    last_detected = Column(DateTime)  # 最近检测时间
    confidence = Column(Float, default=0.0)  # 模式置信度

    # 状态
    is_active = Column(Boolean, default=True)  # 是否活跃
    is_user_confirmed = Column(Boolean, default=False)  # 用户确认

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<SubscriptionPattern(name={self.subscription_name}, merchant={self.merchant}, cycle={self.cycle})>"


class AnomalyRecord(Base):
    """异常记录表 - 记录检测到的异常交易"""
    __tablename__ = 'anomaly_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(100), ForeignKey('transactions.transaction_id'), index=True)

    # 异常信息
    anomaly_type = Column(String(50), nullable=False)  # large_amount/unusual_merchant/high_frequency/duplicate_pattern
    severity = Column(String(20))  # low/medium/high/critical
    score = Column(Float, nullable=False)  # 异常分数（0-1）
    description = Column(Text)  # 异常描述

    # 检测详情
    detection_method = Column(String(50))  # statistical/rule_based/ml_based
    baseline_value = Column(Float)  # 基准值
    actual_value = Column(Float)  # 实际值
    deviation = Column(Float)  # 偏差度

    # 处理状态
    is_reviewed = Column(Boolean, default=False)  # 是否已审核
    is_confirmed = Column(Boolean, default=False)  # 是否确认为异常
    review_note = Column(Text)  # 审核备注

    detected_at = Column(DateTime, default=datetime.now)
    reviewed_at = Column(DateTime)

    def __repr__(self):
        return f"<AnomalyRecord(type={self.anomaly_type}, severity={self.severity}, score={self.score})>"


class MonthlyStatistics(Base):
    """月度统计表 - 预计算的月度统计数据"""
    __tablename__ = 'monthly_statistics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)

    # 财务统计
    total_income = Column(Float, default=0.0)
    total_expense = Column(Float, default=0.0)
    net_balance = Column(Float, default=0.0)
    transaction_count = Column(Integer, default=0)

    # 分类统计（JSON格式存储）
    category_breakdown = Column(Text)  # JSON: {category: {amount, count, percentage}}

    # 同比/环比
    yoy_income_change = Column(Float)  # 同比收入变化率
    yoy_expense_change = Column(Float)  # 同比支出变化率
    mom_income_change = Column(Float)  # 环比收入变化率
    mom_expense_change = Column(Float)  # 环比支出变化率

    # 异常指标
    anomaly_count = Column(Integer, default=0)
    large_expense_count = Column(Integer, default=0)
    max_single_expense = Column(Float)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<MonthlyStatistics(year={self.year}, month={self.month}, expense={self.total_expense})>"


class BudgetPlan(Base):
    """预算计划表"""
    __tablename__ = 'budget_plans'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False, index=True)
    monthly_limit = Column(Float, nullable=False)
    alert_threshold = Column(Float, default=0.8)  # 80% alert
    year_month = Column(String(7), nullable=False, index=True)  # '2024-01'
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'monthly_limit': self.monthly_limit,
            'alert_threshold': self.alert_threshold,
            'year_month': self.year_month,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }
