"""数据库操作"""
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, func, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from .models import Base, Transaction, Category, ClassificationRule, ImportHistory
from .models_extended import BudgetPlan


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: str = "database/bills.db"):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径
        """
        # 确保数据库目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def init_db(self):
        """初始化数据库表"""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Session:
        """获取数据库会话（上下文管理器）"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ==================== Transaction操作 ====================

    def add_transaction(self, transaction_data: Dict[str, Any]) -> Transaction:
        """添加单条交易记录"""
        with self.get_session() as session:
            transaction = Transaction(**transaction_data)
            session.add(transaction)
            session.flush()
            return transaction

    def add_transactions_bulk(self, transactions_data: List[Dict[str, Any]]) -> int:
        """批量添加交易记录"""
        with self.get_session() as session:
            transactions = [Transaction(**data) for data in transactions_data]
            session.bulk_save_objects(transactions)
            return len(transactions)

    def get_transaction_by_id(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """根据交易ID获取记录"""
        with self.get_session() as session:
            result = session.query(Transaction).filter(
                Transaction.transaction_id == transaction_id
            ).first()
            return result.to_dict() if result else None

    def transaction_exists(self, transaction_id: str) -> bool:
        """检查交易是否存在"""
        with self.get_session() as session:
            return session.query(Transaction).filter(
                Transaction.transaction_id == transaction_id
            ).count() > 0

    def update_transaction(self, transaction_id: str, update_data: Dict[str, Any]):
        """更新交易记录"""
        with self.get_session() as session:
            session.query(Transaction).filter(
                Transaction.transaction_id == transaction_id
            ).update(update_data)

    def get_transactions(
        self,
        platform: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        trans_type: Optional[str] = None,
        is_duplicate: Optional[bool] = None,
        limit: Optional[int] = None,
        keyword: Optional[str] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        subcategory: Optional[str] = None,
        is_anomaly: Optional[bool] = None,
        is_subscription: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        查询交易记录

        Args:
            platform: 平台筛选
            category: 分类筛选
            date_from: 开始日期
            date_to: 结束日期
            trans_type: 交易类型（income/expense）
            is_duplicate: 是否重复
            limit: 返回数量限制
            keyword: 关键词搜索（匹配交易对方和描述）
            amount_min: 最小金额
            amount_max: 最大金额
            subcategory: 二级分类筛选
            is_anomaly: 是否异常交易
            is_subscription: 是否订阅交易
        """
        with self.get_session() as session:
            query = session.query(Transaction)

            if platform:
                query = query.filter(Transaction.platform == platform)
            if category:
                query = query.filter(Transaction.category == category)
            if date_from:
                query = query.filter(Transaction.date >= date_from)
            if date_to:
                query = query.filter(Transaction.date <= date_to)
            if trans_type:
                query = query.filter(Transaction.type == trans_type)
            if is_duplicate is not None:
                query = query.filter(Transaction.is_duplicate == is_duplicate)
            if keyword:
                query = query.filter(
                    or_(
                        Transaction.counterparty.contains(keyword),
                        Transaction.description.contains(keyword)
                    )
                )
            if amount_min is not None:
                query = query.filter(Transaction.amount >= amount_min)
            if amount_max is not None:
                query = query.filter(Transaction.amount <= amount_max)
            if subcategory:
                query = query.filter(Transaction.subcategory == subcategory)
            if is_anomaly is not None:
                query = query.filter(Transaction.is_anomaly == is_anomaly)
            if is_subscription is not None:
                query = query.filter(Transaction.is_subscription == is_subscription)

            query = query.order_by(Transaction.date.desc())

            if limit:
                query = query.limit(limit)

            return [t.to_dict() for t in query.all()]

    def get_uncategorized_transactions(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取未分类的交易"""
        with self.get_session() as session:
            query = session.query(Transaction).filter(
                or_(
                    Transaction.category == None,
                    Transaction.category == '',
                    Transaction.category == '其他'
                )
            ).order_by(Transaction.date.desc())

            if limit:
                query = query.limit(limit)

            return [t.to_dict() for t in query.all()]

    # ==================== 统计查询 ====================

    def get_summary_stats(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, float]:
        """获取汇总统计"""
        with self.get_session() as session:
            query = session.query(
                func.sum(Transaction.amount).filter(Transaction.type == 'income').label('total_income'),
                func.sum(Transaction.amount).filter(Transaction.type == 'expense').label('total_expense'),
                func.count(Transaction.id).label('total_count')
            ).filter(Transaction.is_duplicate == False)

            if date_from:
                query = query.filter(Transaction.date >= date_from)
            if date_to:
                query = query.filter(Transaction.date <= date_to)

            result = query.first()

            total_income = float(result[0] or 0)
            total_expense = float(result[1] or 0)
            total_count = int(result[2] or 0)

            return {
                'total_income': total_income,
                'total_expense': abs(total_expense),
                'balance': total_income - abs(total_expense),
                'total_count': total_count
            }

    def get_category_stats(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """获取分类统计"""
        with self.get_session() as session:
            query = session.query(
                Transaction.category,
                func.sum(Transaction.amount).label('total_amount'),
                func.count(Transaction.id).label('count')
            ).filter(
                and_(
                    Transaction.is_duplicate == False,
                    Transaction.type == 'expense',
                    Transaction.category != None
                )
            )

            if date_from:
                query = query.filter(Transaction.date >= date_from)
            if date_to:
                query = query.filter(Transaction.date <= date_to)

            results = query.group_by(Transaction.category).order_by(
                func.sum(Transaction.amount).desc()
            ).all()

            return [
                {
                    'category': r[0],
                    'total_amount': abs(float(r[1])),
                    'count': int(r[2])
                }
                for r in results
            ]

    def get_top_merchants(
        self,
        limit: int = 10,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """获取消费最高的商户"""
        with self.get_session() as session:
            query = session.query(
                Transaction.counterparty,
                func.sum(Transaction.amount).label('total_amount'),
                func.count(Transaction.id).label('count')
            ).filter(
                and_(
                    Transaction.is_duplicate == False,
                    Transaction.type == 'expense',
                    Transaction.counterparty != None
                )
            )

            if date_from:
                query = query.filter(Transaction.date >= date_from)
            if date_to:
                query = query.filter(Transaction.date <= date_to)

            results = query.group_by(Transaction.counterparty).order_by(
                func.sum(Transaction.amount).desc()
            ).limit(limit).all()

            return [
                {
                    'merchant': r[0],
                    'total_amount': abs(float(r[1])),
                    'count': int(r[2])
                }
                for r in results
            ]

    # ==================== Category操作 ====================

    def add_category(self, name: str, parent_id: Optional[int] = None, **kwargs) -> Category:
        """添加分类"""
        with self.get_session() as session:
            category = Category(name=name, parent_id=parent_id, **kwargs)
            session.add(category)
            session.flush()
            return category

    def get_all_categories(self) -> List[Dict[str, Any]]:
        """获取所有分类"""
        with self.get_session() as session:
            categories = session.query(Category).filter(Category.is_active == True).order_by(
                Category.sort_order, Category.name
            ).all()
            return [
                {
                    'id': c.id,
                    'name': c.name,
                    'parent_id': c.parent_id,
                    'icon': c.icon,
                    'color': c.color,
                    'description': c.description,
                    'is_active': c.is_active,
                    'sort_order': c.sort_order,
                }
                for c in categories
            ]

    # ==================== ImportHistory操作 ====================

    def add_import_history(self, history_data: Dict[str, Any]) -> ImportHistory:
        """添加导入历史"""
        with self.get_session() as session:
            history = ImportHistory(**history_data)
            session.add(history)
            session.flush()
            return history

    def file_imported(self, file_hash: str) -> bool:
        """检查文件是否已导入"""
        with self.get_session() as session:
            return session.query(ImportHistory).filter(
                ImportHistory.file_hash == file_hash
            ).count() > 0

    # ==================== BudgetPlan操作 ====================

    def set_budget(self, category: str, monthly_limit: float, year_month: str, alert_threshold: float = 0.8) -> Dict[str, Any]:
        """设置或更新预算"""
        with self.get_session() as session:
            existing = session.query(BudgetPlan).filter(
                BudgetPlan.category == category,
                BudgetPlan.year_month == year_month
            ).first()
            if existing:
                existing.monthly_limit = monthly_limit
                existing.alert_threshold = alert_threshold
                session.flush()
                return existing.to_dict()
            else:
                budget = BudgetPlan(
                    category=category,
                    monthly_limit=monthly_limit,
                    alert_threshold=alert_threshold,
                    year_month=year_month
                )
                session.add(budget)
                session.flush()
                return budget.to_dict()

    def get_budgets(self, year_month: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取预算计划"""
        with self.get_session() as session:
            query = session.query(BudgetPlan).filter(BudgetPlan.is_active == True)
            if year_month:
                query = query.filter(BudgetPlan.year_month == year_month)
            query = query.order_by(BudgetPlan.category)
            return [b.to_dict() for b in query.all()]

    def delete_budget(self, budget_id: int):
        """删除预算"""
        with self.get_session() as session:
            session.query(BudgetPlan).filter(BudgetPlan.id == budget_id).delete()
