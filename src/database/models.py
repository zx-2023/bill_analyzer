"""数据库模型定义"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Transaction(Base):
    """交易记录表"""
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(100), unique=True, nullable=False, index=True)
    platform = Column(String(20), nullable=False, index=True)  # alipay/wechat/bank/meituan
    date = Column(DateTime, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    type = Column(String(10), nullable=False)  # income/expense/internal
    category = Column(String(50), index=True)  # 一级分类
    subcategory = Column(String(50))  # 二级分类
    counterparty = Column(String(200))  # 交易对方
    counterparty_account = Column(String(100))  # 对方账号
    description = Column(Text)  # 交易描述
    payment_method = Column(String(50))  # 支付方式
    status = Column(String(50))  # 交易状态
    original_category = Column(String(50))  # 原始分类
    note = Column(Text)  # 备注
    raw_data = Column(Text)  # 原始JSON数据

    # 去重相关
    is_duplicate = Column(Boolean, default=False, index=True)
    duplicate_group = Column(String(50))  # 重复交易组ID
    duplicate_confidence = Column(Float)  # 重复置信度

    # 分类相关
    classification_method = Column(String(20))  # rule/ai/manual
    classification_confidence = Column(Float)  # 分类置信度
    is_verified = Column(Boolean, default=False)  # 是否人工确认

    # 异常检测相关
    is_anomaly = Column(Boolean, default=False, index=True)  # 是否异常
    anomaly_type = Column(String(50))  # 异常类型：large_amount/unusual_merchant/high_frequency
    anomaly_score = Column(Float)  # 异常分数（0-1）
    anomaly_reason = Column(Text)  # 异常原因说明

    # 订阅识别相关
    is_subscription = Column(Boolean, default=False, index=True)  # 是否订阅扣款
    subscription_group = Column(String(50))  # 订阅组ID（同一订阅的不同扣款）
    subscription_name = Column(String(100))  # 订阅名称
    subscription_cycle = Column(String(20))  # 订阅周期：monthly/yearly/weekly
    subscription_confidence = Column(Float)  # 订阅识别置信度

    # 时间戳
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Transaction(id={self.id}, date={self.date}, amount={self.amount}, category={self.category})>"

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'platform': self.platform,
            'date': self.date.strftime('%Y-%m-%d %H:%M:%S') if self.date else None,
            'amount': self.amount,
            'type': self.type,
            'category': self.category,
            'subcategory': self.subcategory,
            'counterparty': self.counterparty,
            'description': self.description,
            'is_duplicate': self.is_duplicate,
            'is_verified': self.is_verified
        }


class Category(Base):
    """分类管理表"""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey('categories.id'))
    icon = Column(String(50))
    color = Column(String(20))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    # 自关联
    children = relationship("Category", backref="parent", remote_side=[id])

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Category(name={self.name})>"


class ClassificationRule(Base):
    """分类规则表（动态学习）"""
    __tablename__ = 'classification_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False, index=True)
    rule_type = Column(String(20), nullable=False)  # keyword/pattern/merchant/mcc
    rule_value = Column(String(200), nullable=False)
    confidence = Column(Float, default=0.8)

    # 统计信息
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

    # 学习来源
    source = Column(String(20))  # manual/ai/auto_learned
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<ClassificationRule(category={self.category}, type={self.rule_type}, value={self.rule_value})>"


class ImportHistory(Base):
    """导入历史记录"""
    __tablename__ = 'import_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(200), nullable=False)
    platform = Column(String(20), nullable=False)
    file_hash = Column(String(64), unique=True, index=True)  # MD5文件哈希，防止重复导入

    # 导入统计
    total_rows = Column(Integer)
    imported_rows = Column(Integer)
    duplicate_rows = Column(Integer)
    error_rows = Column(Integer)

    # 时间范围
    date_from = Column(DateTime)
    date_to = Column(DateTime)

    status = Column(String(20))  # success/partial/failed
    error_message = Column(Text)

    import_time = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<ImportHistory(filename={self.filename}, platform={self.platform}, status={self.status})>"
