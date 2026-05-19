"""家庭财务数据分析系统 - Streamlit主应用"""
import streamlit as st
import pandas as pd
import yaml
from datetime import datetime, timedelta
import os

# 设置页面配置
st.set_page_config(
    page_title="家庭财务数据分析系统",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 忽略 openpyxl 警告
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# 导入自定义模块
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.operations import DatabaseManager
from src.parsers.alipay_parser import AlipayParser
from src.parsers.wechat_parser import WeChatParser
from src.parsers.bank_parser import BankParser
from src.parsers.meituan_parser import MeituanParser
from src.processors.pipeline import DataProcessingPipeline
from src.visualization.charts import (
    create_expense_trend_chart,
    create_category_pie_chart,
    create_monthly_comparison_chart,
    create_top_merchants_chart,
    create_subscription_chart,
    create_anomaly_scatter
)
from src.utils.exporters import export_to_excel


# 初始化session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseManager()
    st.session_state.db.init_db()

if 'pipeline' not in st.session_state:
    st.session_state.pipeline = DataProcessingPipeline(use_ai=False)


# 平台解析器映射
PLATFORM_PARSERS = {
    '支付宝': AlipayParser(),
    '微信支付': WeChatParser(),
    '银行账单': BankParser(),
    '美团': MeituanParser()
}


def _prepare_excel_export(df: pd.DataFrame) -> bytes:
    """Prepare data and call export_to_excel.

    Builds category_stats, monthly_stats, anomaly and subscription DataFrames
    from a transactions DataFrame, then returns the Excel file bytes.
    """
    # Ensure date is datetime
    if 'date' in df.columns:
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # --- Category stats ---
    category_stats_raw = st.session_state.db.get_category_stats()
    cat_df = pd.DataFrame(category_stats_raw) if category_stats_raw else pd.DataFrame()
    if not cat_df.empty and 'total_amount' in cat_df.columns:
        total = cat_df['total_amount'].sum()
        cat_df['percentage'] = (cat_df['total_amount'] / total * 100).round(2) if total else 0
    else:
        cat_df = pd.DataFrame(columns=['category', 'total_amount', 'count', 'percentage'])

    # --- Monthly stats ---
    expense_df = df[df['type'] == 'expense'] if 'type' in df.columns else pd.DataFrame()
    income_df = df[df['type'] == 'income'] if 'type' in df.columns else pd.DataFrame()

    if not expense_df.empty:
        monthly_expense = expense_df.set_index('date').resample('M')['amount'].sum()
    else:
        monthly_expense = pd.Series(dtype=float)

    if not income_df.empty:
        monthly_income = income_df.set_index('date').resample('M')['amount'].sum()
    else:
        monthly_income = pd.Series(dtype=float)

    all_months = monthly_expense.index.union(monthly_income.index)
    monthly_stats = pd.DataFrame({
        'month': all_months.strftime('%Y-%m'),
        'total_expense': monthly_expense.reindex(all_months, fill_value=0).values,
        'total_income': monthly_income.reindex(all_months, fill_value=0).values,
    })
    monthly_stats['balance'] = monthly_stats['total_income'] - monthly_stats['total_expense']

    # --- Anomaly / subscription subsets ---
    anomaly_df = df[df.get('is_anomaly', False) == True] if 'is_anomaly' in df.columns else pd.DataFrame()
    subscription_df = df[df.get('is_subscription', False) == True] if 'is_subscription' in df.columns else pd.DataFrame()

    return export_to_excel(df, cat_df, monthly_stats, anomaly_df, subscription_df)


def show_sidebar():
    """侧边栏导航"""
    st.sidebar.title("💰 财务分析系统")

    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "功能导航",
        [
            "📊 财务总览",
            "📥 数据导入",
            "📋 交易记录",
            "⚠️ 异常检测",
            "🔄 订阅管理",
            "💰 预算管理",
            "🏷️ 分类管理",
            "⚙️ 系统设置"
        ]
    )

    st.sidebar.markdown("---")

    # 显示统计信息
    try:
        stats = st.session_state.db.get_summary_stats()
        st.sidebar.metric("总支出", f"¥{stats['total_expense']:,.2f}")
        st.sidebar.metric("总收入", f"¥{stats['total_income']:,.2f}")
        st.sidebar.metric("结余", f"¥{stats['balance']:,.2f}")
    except Exception:
        st.sidebar.metric("总支出", "—")
        st.sidebar.metric("总收入", "—")
        st.sidebar.metric("结余", "—")

    # 预算预警
    try:
        current_month = datetime.now().strftime('%Y-%m')
        budgets = st.session_state.db.get_budgets(year_month=current_month)
        if budgets:
            year = datetime.now().year
            month = datetime.now().month
            date_from = datetime(year, month, 1)
            if month == 12:
                date_to = datetime(year + 1, 1, 1)
            else:
                date_to = datetime(year, month + 1, 1)
            category_stats = st.session_state.db.get_category_stats(date_from, date_to)
            spending_by_cat = {s['category']: s['total_amount'] for s in category_stats}

            over_budget = []
            for b in budgets:
                spent = spending_by_cat.get(b['category'], 0)
                if b['monthly_limit'] > 0 and spent / b['monthly_limit'] > b['alert_threshold']:
                    over_budget.append(b['category'])

            if over_budget:
                st.sidebar.warning(f"⚠️ 预算预警: {', '.join(over_budget)}")
    except Exception:
        pass

    return page


def show_dashboard():
    """财务总览页面"""
    st.title("📊 财务总览")

    # 日期范围选择
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("开始日期", datetime.now() - timedelta(days=30))
    with col2:
        date_to = st.date_input("结束日期", datetime.now())

    # 获取统计数据
    stats = st.session_state.db.get_summary_stats(
        datetime.combine(date_from, datetime.min.time()),
        datetime.combine(date_to, datetime.max.time())
    )

    # 关键指标卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("总支出", f"¥{stats['total_expense']:,.2f}")

    with col2:
        st.metric("总收入", f"¥{stats['total_income']:,.2f}")

    with col3:
        st.metric("结余", f"¥{stats['balance']:,.2f}")

    with col4:
        st.metric("交易笔数", stats['total_count'])

    st.markdown("---")

    # 获取交易数据用于图表
    transactions = st.session_state.db.get_transactions(
        date_from=datetime.combine(date_from, datetime.min.time()),
        date_to=datetime.combine(date_to, datetime.max.time()),
        limit=10000
    )

    if transactions:
        df = pd.DataFrame(transactions)

        # 第一行：支出趋势 + 分类饼图
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📈 支出趋势")
            period = st.selectbox("聚合周期", ['day', 'week', 'month'], key='trend_period')
            fig_trend = create_expense_trend_chart(df, period=period)
            st.plotly_chart(fig_trend, use_container_width=True)

        with col2:
            st.subheader("🥧 支出分类占比")
            category_stats = st.session_state.db.get_category_stats(
                datetime.combine(date_from, datetime.min.time()),
                datetime.combine(date_to, datetime.max.time())
            )
            if category_stats:
                fig_pie = create_category_pie_chart(category_stats)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("暂无分类数据")

        st.markdown("---")

        # 第二行：月度对比
        st.subheader("📊 月度支出对比")
        fig_monthly = create_monthly_comparison_chart(df)
        st.plotly_chart(fig_monthly, use_container_width=True)

        st.markdown("---")

        # 第三行：Top商户 + 异常检测
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏆 Top 10 消费商户")
            top_merchants = st.session_state.db.get_top_merchants(
                limit=10,
                date_from=datetime.combine(date_from, datetime.min.time()),
                date_to=datetime.combine(date_to, datetime.max.time())
            )
            if top_merchants:
                fig_merchants = create_top_merchants_chart(top_merchants, limit=10)
                st.plotly_chart(fig_merchants, use_container_width=True)
            else:
                st.info("暂无商户数据")

        with col2:
            st.subheader("⚠️ 异常交易分布")
            anomaly_df = df[df.get('is_anomaly', False) == True]
            if len(anomaly_df) > 0:
                st.metric("异常交易数", len(anomaly_df))
                fig_anomaly = create_anomaly_scatter(df)
                st.plotly_chart(fig_anomaly, use_container_width=True)
            else:
                st.info("未检测到异常交易")

        # 数据导出
        st.markdown("---")
        st.subheader("📥 数据导出")
        excel_data = _prepare_excel_export(df)
        st.download_button(
            label="📊 导出为Excel",
            data=excel_data,
            file_name=f"financial_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dashboard_excel_export"
        )

    else:
        st.info("暂无交易数据，请先导入账单")


def show_import_page():
    """数据导入页面"""
    st.title("📥 数据导入")
    
    tab1, tab2 = st.tabs(["📁 文件上传", "🔌 支付宝API导入"])
    
    with tab1:
        # 平台选择
        platform_choice = st.selectbox(
            "选择账单平台",
            list(PLATFORM_PARSERS.keys()),
            help="选择您要导入的账单来源平台"
        )

        parser = PLATFORM_PARSERS[platform_choice]

        st.info(f"💡 当前支持导入：{', '.join(PLATFORM_PARSERS.keys())}")

        # 文件上传
        uploaded_file = st.file_uploader(
            "上传账单文件",
            type=['csv', 'xlsx', 'xls'],
            help="支持CSV和Excel格式"
        )

        if uploaded_file is not None:
            # 保存临时文件
            temp_path = f"data/raw/temp_{uploaded_file.name}"
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)

            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.success(f"文件已上传: {uploaded_file.name}")

            # 检测格式
            if parser.detect_format(temp_path):
                st.success(f"✅ 检测为{platform_choice}账单")

                # 解析按钮
                if st.button("开始解析并导入", type="primary"):
                    _process_import(temp_path, parser)
            else:
                st.warning(f"⚠️ 未能识别为{platform_choice}账单格式，请确认文件类型")
                # 允许强制导入
                if st.button("强制尝试解析"):
                     _process_import(temp_path, parser)

    with tab2:
        st.subheader("支付宝商家账单API导入")
        st.info("💡 此功能仅支持支付宝商家/企业账号，需要配置API密钥")
        
        from src.integrations.alipay_client import AlipayClient
        client = AlipayClient()
        
        if not client.client:
            st.error("❌ 未检测到支付宝API配置，请在.env文件中配置ALIPAY_APP_ID等信息")
        else:
            st.success("✅ 支付宝API客户端已初始化")
            
            # 1. 授权 / 模式选择
            st.markdown("#### 1. 授权模式")
            
            # 添加自用型应用选项
            is_self_app = st.checkbox("我是自用型应用 (直接使用密钥，无需OAuth授权)", value=True, help="如果您是使用自己的支付宝账号创建的应用来下载自己的账单，请勾选此项")
            
            if not is_self_app:
                st.markdown("##### OAuth 授权 (ISV模式)")
                auth_url = client.get_oauth_url("http://localhost:8501")
                st.markdown(f"[点击此处进行授权]({auth_url})")
                
                auth_code = st.text_input("请输入授权码 (Auth Code)", help="授权回调URL中的auth_code参数")
                
                if auth_code:
                    if st.button("获取Token"):
                        token_info = client.get_access_token(auth_code)
                        if token_info:
                            st.session_state['alipay_token'] = token_info.get('access_token')
                            st.success("✅ 获取Token成功")
                        else:
                            st.error("获取Token失败")
            else:
                st.info("✅ 自用型模式：将直接使用应用私钥签名请求")
                st.session_state['alipay_token'] = None # 清除token，确保不使用过期token
            
            # 2. 下载账单
            st.markdown("#### 2. 下载账单")
            bill_date = st.date_input("选择账单日期", datetime.now() - timedelta(days=1))
            bill_type = st.selectbox("账单类型", ["trade", "signcustomer"])
            
            if st.button("查询并下载账单"):
                date_str = bill_date.strftime('%Y-%m-%d')
                token = st.session_state.get('alipay_token')
                
                with st.spinner("正在查询账单下载地址..."):
                    download_url = client.query_bill_download_url(bill_type, date_str, token)
                    
                    if download_url:
                        st.success("✅ 获取下载地址成功")
                        st.markdown(f"[点击下载账单文件]({download_url})")
                        
                        # 自动下载并处理
                        try:
                            import requests
                            resp = requests.get(download_url)
                            if resp.status_code == 200:
                                # 保存为临时文件
                                temp_file = f"data/raw/alipay_api_{date_str}.zip" # 通常是zip
                                with open(temp_file, "wb") as f:
                                    f.write(resp.content)
                                st.info(f"文件已下载至: {temp_file} (需解压后导入)")
                                # 这里可以进一步添加解压和自动导入逻辑
                            else:
                                st.error("下载文件失败")
                        except Exception as e:
                            st.error(f"下载异常: {e}")
                    else:
                        st.error("未查询到账单或接口调用失败")


def _process_import(file_path, parser):
    """处理导入逻辑"""
    with st.spinner("正在使用数据处理流水线..."):
        try:
            # 1. 解析
            st.write("步骤 1/4: 解析账单...")
            df = parser.parse(file_path)
            st.write(f"✓ 解析成功：{len(df)} 条记录")

            # 2. 使用完整流水线处理
            st.write("步骤 2/4: 数据处理流水线...")
            result = st.session_state.pipeline.process(
                df,
                enable_anomaly_detection=True,
                enable_subscription_detection=True
            )

            # 显示处理摘要
            st.write("步骤 3/4: 处理结果...")
            summary_report = st.session_state.pipeline.get_summary_report(result)

            with st.expander("📋 查看详细处理报告"):
                st.code(summary_report)

            # 显示警告
            if result['warnings']:
                for warning in result['warnings']:
                    st.warning(warning)

            # 显示错误
            if result['errors']:
                for error in result['errors']:
                    st.error(error)

            # 3. 导入数据库
            st.write("步骤 4/4: 导入数据库...")
            processed_df = result['df']
            records = processed_df.to_dict('records')
            imported_count = 0

            for record in records:
                if not st.session_state.db.transaction_exists(record['transaction_id']):
                    st.session_state.db.add_transaction(record)
                    imported_count += 1

            st.success(f"✅ 导入完成！成功导入 {imported_count} 条新记录")

            # 显示关键统计
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总记录", result['stats'].get('total_transactions', 0))
            with col2:
                st.metric("有效记录", result['stats'].get('unique_transactions', 0))
            with col3:
                anomaly_count = result['stats'].get('anomaly_summary', {}).get('total_anomalies', 0)
                st.metric("异常交易", anomaly_count)
            with col4:
                sub_count = result['stats'].get('subscription_summary', {}).get('total_subscriptions', 0)
                st.metric("订阅服务", sub_count)

            # 清理临时文件
            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception as e:
            st.error(f"导入失败：{str(e)}")
            import traceback
            st.code(traceback.format_exc())


def show_transactions():
    """交易记录页面"""
    st.title("📋 交易记录")

    # 加载二级分类配置
    subcategory_map = {}
    subcat_file = "config/subcategory_rules.yaml"
    if os.path.exists(subcat_file):
        with open(subcat_file, 'r', encoding='utf-8') as f:
            subcategory_map = yaml.safe_load(f) or {}

    # 第一行筛选：平台、一级分类、类型、显示数量
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        platform_filter = st.selectbox("平台", ["全部", "alipay", "wechat", "bank", "meituan"])

    with col2:
        categories = ["全部"] + list(set([
            t['category'] for t in st.session_state.db.get_transactions(limit=1000)
            if t.get('category')
        ]))
        category_filter = st.selectbox("一级分类", categories)

    with col3:
        type_filter = st.selectbox("类型", ["全部", "income", "expense"])

    with col4:
        limit = st.number_input("显示数量", min_value=10, max_value=1000, value=100)

    # 第二行筛选：关键词搜索、日期范围
    col1, col2, col3 = st.columns(3)

    with col1:
        keyword = st.text_input("🔍 关键词搜索", placeholder="搜索交易对方或描述")

    with col2:
        date_from = st.date_input("开始日期", datetime.now() - timedelta(days=30), key="txn_date_from")

    with col3:
        date_to = st.date_input("结束日期", datetime.now(), key="txn_date_to")

    # 第三行筛选：金额范围、二级分类、异常/订阅开关
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        amount_min = st.number_input("最小金额", min_value=0.0, value=0.0, step=10.0, format="%.2f")

    with col2:
        amount_max = st.number_input("最大金额", min_value=0.0, value=0.0, step=10.0, format="%.2f",
                                      help="设为0表示不限制")

    with col3:
        # 根据选中的一级分类加载对应的二级分类选项
        if category_filter != "全部" and category_filter in subcategory_map:
            subcategory_options = ["全部"] + list(subcategory_map[category_filter].keys())
        else:
            subcategory_options = ["全部"]
        subcategory_filter = st.selectbox("二级分类", subcategory_options)

    with col4:
        only_anomaly = st.checkbox("仅异常交易")
        only_subscription = st.checkbox("仅订阅交易")

    # 查询
    transactions = st.session_state.db.get_transactions(
        platform=None if platform_filter == "全部" else platform_filter,
        category=None if category_filter == "全部" else category_filter,
        trans_type=None if type_filter == "全部" else type_filter,
        date_from=datetime.combine(date_from, datetime.min.time()),
        date_to=datetime.combine(date_to, datetime.max.time()),
        limit=limit,
        keyword=keyword if keyword else None,
        amount_min=amount_min if amount_min > 0 else None,
        amount_max=amount_max if amount_max > 0 else None,
        subcategory=None if subcategory_filter == "全部" else subcategory_filter,
        is_anomaly=True if only_anomaly else None,
        is_subscription=True if only_subscription else None
    )

    if transactions:
        df = pd.DataFrame(transactions)

        # 选择显示列（包含二级分类）
        display_cols = [
            'date', 'platform', 'counterparty', 'description',
            'amount', 'type', 'category', 'subcategory',
            'is_anomaly', 'is_subscription'
        ]
        available_cols = [col for col in display_cols if col in df.columns]

        st.dataframe(
            df[available_cols].sort_values('date', ascending=False),
            use_container_width=True,
            height=600
        )

        # ==================== 手动分类编辑 ====================
        st.markdown("---")
        st.subheader("✏️ 手动分类编辑")

        # 加载分类名称
        rule_file = "config/classification_rules.yaml"
        category_names = []
        if os.path.exists(rule_file):
            with open(rule_file, 'r', encoding='utf-8') as f:
                rules = yaml.safe_load(f)
            category_names = list(rules.get('categories', {}).keys())

        if category_names:
            # 准备可编辑的DataFrame
            edit_cols = ['transaction_id', 'date', 'counterparty', 'description', 'amount', 'category', 'subcategory']
            edit_available = [col for col in edit_cols if col in df.columns]
            edit_df = df[edit_available].sort_values('date', ascending=False).copy()

            edited_df = st.data_editor(
                edit_df,
                column_config={
                    "transaction_id": st.column_config.TextColumn("交易ID", disabled=True),
                    "date": st.column_config.TextColumn("日期", disabled=True),
                    "counterparty": st.column_config.TextColumn("交易对方", disabled=True),
                    "description": st.column_config.TextColumn("描述", disabled=True),
                    "amount": st.column_config.NumberColumn("金额", disabled=True),
                    "category": st.column_config.SelectboxColumn(
                        "分类",
                        options=category_names,
                    ),
                    "subcategory": st.column_config.TextColumn("二级分类"),
                },
                disabled=["transaction_id", "date", "counterparty", "description", "amount"],
                hide_index=True,
                use_container_width=True,
                height=400,
                key="transaction_editor"
            )

            if st.button("💾 保存修改", type="primary", key="save_inline_edits"):
                change_count = 0
                for idx in edit_df.index:
                    orig_cat = edit_df.loc[idx, 'category'] if 'category' in edit_df.columns else None
                    orig_subcat = edit_df.loc[idx, 'subcategory'] if 'subcategory' in edit_df.columns else None
                    new_cat = edited_df.loc[idx, 'category'] if 'category' in edited_df.columns else None
                    new_subcat = edited_df.loc[idx, 'subcategory'] if 'subcategory' in edited_df.columns else None

                    # 统一空值比较
                    orig_cat = orig_cat if pd.notna(orig_cat) else None
                    orig_subcat = orig_subcat if pd.notna(orig_subcat) else None
                    new_cat = new_cat if pd.notna(new_cat) else None
                    new_subcat = new_subcat if pd.notna(new_subcat) else None

                    if orig_cat != new_cat or orig_subcat != new_subcat:
                        tid = edit_df.loc[idx, 'transaction_id']
                        update_data = {
                            'classification_method': 'manual',
                            'is_verified': True,
                            'classification_confidence': 1.0,
                        }
                        if new_cat is not None:
                            update_data['category'] = new_cat
                        if new_subcat is not None:
                            update_data['subcategory'] = new_subcat
                        st.session_state.db.update_transaction(tid, update_data)
                        change_count += 1

                if change_count > 0:
                    st.success(f"✅ 已保存 {change_count} 条修改")
                    st.rerun()
                else:
                    st.info("未检测到修改")
        else:
            st.warning("⚠️ 未找到分类规则配置文件，无法进行手动分类")

        st.markdown("---")

        # 导出功能
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 导出为CSV",
                data=csv,
                file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        with export_col2:
            excel_data = _prepare_excel_export(df)
            st.download_button(
                label="📊 导出为Excel",
                data=excel_data,
                file_name=f"financial_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("暂无交易记录")


def show_anomaly_page():
    """异常检测页面"""
    st.title("⚠️ 异常交易检测")

    # 获取所有异常交易
    transactions = st.session_state.db.get_transactions(limit=10000)

    if transactions:
        df = pd.DataFrame(transactions)
        anomaly_df = df[df.get('is_anomaly', False) == True]

        if len(anomaly_df) > 0:
            # 异常概览
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("异常交易总数", len(anomaly_df))

            with col2:
                st.metric("异常金额", f"¥{anomaly_df['amount'].sum():,.2f}")

            with col3:
                anomaly_types = anomaly_df['anomaly_type'].value_counts()
                st.metric("异常类型数", len(anomaly_types))

            with col4:
                avg_score = anomaly_df['anomaly_score'].mean()
                st.metric("平均异常分数", f"{avg_score:.2f}")

            st.markdown("---")

            # 异常散点图
            st.subheader("📊 异常交易可视化")
            fig_scatter = create_anomaly_scatter(df)
            st.plotly_chart(fig_scatter, use_container_width=True)

            st.markdown("---")

            # 异常类型分布
            st.subheader("🔍 异常类型分布")
            col1, col2 = st.columns(2)

            with col1:
                type_counts = anomaly_df['anomaly_type'].value_counts()
                st.bar_chart(type_counts)

            with col2:
                st.write("**异常类型说明**:")
                st.write("- **large_amount**: 大额支出（超过95%分位数）")
                st.write("- **unusual_merchant**: 异常商户（陌生商户大额消费）")
                st.write("- **high_frequency**: 高频异常（同日同商户多次大额）")

            st.markdown("---")

            # 异常交易明细
            st.subheader("📋 异常交易明细")

            # 按异常分数排序
            anomaly_df_sorted = anomaly_df.sort_values('anomaly_score', ascending=False)

            display_cols = [
                'date', 'counterparty', 'amount', 'category',
                'anomaly_type', 'anomaly_score', 'anomaly_reason'
            ]
            available_cols = [col for col in display_cols if col in anomaly_df_sorted.columns]

            st.dataframe(
                anomaly_df_sorted[available_cols],
                use_container_width=True,
                height=400
            )

        else:
            st.success("✅ 未检测到异常交易")
            st.info("💡 提示：异常检测基于统计分析，包括大额支出、异常商户和高频交易检测")

    else:
        st.info("暂无交易数据，请先导入账单")


def show_subscription_page():
    """订阅管理页面"""
    st.title("🔄 订阅服务管理")

    # 获取所有交易
    transactions = st.session_state.db.get_transactions(limit=10000)

    if transactions:
        df = pd.DataFrame(transactions)
        subscription_df = df[df.get('is_subscription', False) == True]

        if len(subscription_df) > 0:
            # 订阅统计
            from src.processors.subscription_detector import SubscriptionDetector
            detector = SubscriptionDetector()
            summary = detector.get_subscription_summary(df)

            # 概览卡片
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("订阅服务数", summary['total_subscriptions'])

            with col2:
                st.metric("预计月度成本", f"¥{summary['monthly_cost']:,.2f}")

            with col3:
                st.metric("订阅交易数", len(subscription_df))

            with col4:
                st.metric("年度预估", f"¥{summary['monthly_cost'] * 12:,.2f}")

            st.markdown("---")

            # 订阅图表
            if summary.get('subscriptions'):
                st.subheader("📊 订阅扣款分析")
                fig_sub = create_subscription_chart(summary['subscriptions'])
                st.plotly_chart(fig_sub, use_container_width=True)

            st.markdown("---")

            # 订阅周期分布
            st.subheader("🔍 订阅周期分布")
            col1, col2 = st.columns(2)

            with col1:
                cycle_counts = summary.get('by_cycle', {})
                if cycle_counts:
                    st.bar_chart(pd.Series(cycle_counts))

            with col2:
                st.write("**周期类型说明**:")
                st.write("- **monthly**: 每月（28-31天）")
                st.write("- **yearly**: 每年（360-370天）")
                st.write("- **quarterly**: 每季度（85-95天）")
                st.write("- **weekly**: 每周（6-8天）")
                st.write("- **biweekly**: 每两周（13-15天）")

            st.markdown("---")

            # 订阅明细
            st.subheader("📋 订阅服务明细")

            if summary.get('subscriptions'):
                subscriptions_df = pd.DataFrame(summary['subscriptions'])

                # 显示订阅信息
                for _, row in subscriptions_df.iterrows():
                    with st.expander(f"📌 {row['name']} - ¥{row['amount']:.2f}/{row['cycle']}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("扣款金额", f"¥{row['amount']:.2f}")
                        with col2:
                            st.metric("扣款周期", row['cycle'])
                        with col3:
                            st.metric("扣款次数", row['count'])

                        # 显示该订阅的所有交易
                        group_transactions = subscription_df[
                            subscription_df['subscription_group'] == row['group_id']
                        ].sort_values('date', ascending=False)

                        st.dataframe(
                            group_transactions[['date', 'amount', 'description']],
                            use_container_width=True
                        )

        else:
            st.info("未检测到订阅服务")
            st.write("💡 提示：订阅检测基于以下条件：")
            st.write("- 相同商户")
            st.write("- 相似金额（±10%容差）")
            st.write("- 规律的时间间隔")
            st.write("- 至少3次交易记录")

    else:
        st.info("暂无交易数据，请先导入账单")


def show_budget_page():
    """预算管理页面"""
    st.title("💰 预算管理")

    # Current month selector
    current_month = datetime.now().strftime('%Y-%m')
    year_month = st.text_input("预算月份", value=current_month, help="格式：YYYY-MM")

    # Get existing budgets and actual spending
    budgets = st.session_state.db.get_budgets(year_month=year_month)

    # Parse year_month for date range
    from datetime import date
    year, month = int(year_month[:4]), int(year_month[5:7])
    date_from = datetime(year, month, 1)
    if month == 12:
        date_to = datetime(year + 1, 1, 1)
    else:
        date_to = datetime(year, month + 1, 1)

    category_stats = st.session_state.db.get_category_stats(date_from, date_to)
    spending_by_cat = {s['category']: s['total_amount'] for s in category_stats}

    # Budget overview with progress bars
    if budgets:
        st.subheader("📊 预算执行情况")

        for budget in budgets:
            cat = budget['category']
            limit = budget['monthly_limit']
            spent = spending_by_cat.get(cat, 0)
            pct = spent / limit if limit > 0 else 0
            alert = budget['alert_threshold']

            col1, col2, col3 = st.columns([2, 3, 1])
            with col1:
                st.write(f"**{cat}**")
                st.caption(f"预算: ¥{limit:,.0f}")
            with col2:
                if pct > 1.0:
                    st.progress(1.0)
                    st.error(f"超支 ¥{spent - limit:,.0f}")
                elif pct > alert:
                    st.progress(pct)
                    st.warning(f"¥{spent:,.0f} / ¥{limit:,.0f} ({pct:.0%})")
                else:
                    st.progress(pct)
                    st.caption(f"¥{spent:,.0f} / ¥{limit:,.0f} ({pct:.0%})")
            with col3:
                st.metric("剩余", f"¥{max(limit - spent, 0):,.0f}")

    st.markdown("---")

    # Budget setting form
    st.subheader("⚙️ 设置预算")

    # Load categories from config
    with open('config/classification_rules.yaml', 'r', encoding='utf-8') as f:
        rules = yaml.safe_load(f)
    category_names = list(rules.get('categories', {}).keys())

    with st.form("budget_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            budget_cat = st.selectbox("分类", category_names)
        with col2:
            budget_amount = st.number_input("月度预算 (¥)", min_value=0.0, step=100.0, value=1000.0)
        with col3:
            budget_alert = st.slider("预警阈值", 0.5, 1.0, 0.8, 0.05)

        if st.form_submit_button("保存预算", type="primary"):
            st.session_state.db.set_budget(budget_cat, budget_amount, year_month, budget_alert)
            st.success(f"✅ 已设置 {budget_cat} 预算: ¥{budget_amount:,.0f}/月")
            st.rerun()

    # Show existing budgets with delete option
    if budgets:
        st.subheader("📋 已设置的预算")
        for budget in budgets:
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                st.write(budget['category'])
            with col2:
                st.write(f"¥{budget['monthly_limit']:,.0f}")
            with col3:
                st.write(f"预警: {budget['alert_threshold']:.0%}")
            with col4:
                if st.button("删除", key=f"del_budget_{budget['id']}"):
                    st.session_state.db.delete_budget(budget['id'])
                    st.rerun()


def show_category_management():
    """分类管理页面"""
    st.title("🏷️ 分类管理")

    # 未分类交易
    st.subheader("未分类交易")

    uncategorized = st.session_state.db.get_uncategorized_transactions(limit=100)

    if uncategorized:
        st.warning(f"⚠️ 发现 {len(uncategorized)} 条未分类交易")

        df_uncat = pd.DataFrame(uncategorized)

        # 显示未分类交易列表
        display_cols_uncat = ['date', 'counterparty', 'description', 'amount', 'platform']
        available_cols_uncat = [col for col in display_cols_uncat if col in df_uncat.columns]
        st.dataframe(df_uncat[available_cols_uncat], use_container_width=True)

        if st.button("使用AI批量分类"):
            st.info("💡 AI分类功能需要配置Kimi API密钥（在系统设置中配置）")

        # ==================== 手动批量分类 ====================
        st.markdown("---")
        st.subheader("📦 手动批量分类")

        # 加载分类名称
        rule_file_batch = "config/classification_rules.yaml"
        category_names_batch = []
        if os.path.exists(rule_file_batch):
            with open(rule_file_batch, 'r', encoding='utf-8') as f:
                rules_batch = yaml.safe_load(f)
            category_names_batch = list(rules_batch.get('categories', {}).keys())

        if category_names_batch and len(df_uncat) > 0:
            # 构建选项列表
            options_list = []
            for _, row in df_uncat.iterrows():
                label = f"{row.get('date', '')} | {row.get('counterparty', '')} | {row.get('description', '')} | ¥{row.get('amount', 0):.2f}"
                options_list.append(label)

            # 多选交易
            selected_labels = st.multiselect(
                "选择要分类的交易",
                options=options_list,
                help="选择一条或多条交易进行批量分类"
            )

            # 选择目标分类
            target_category = st.selectbox(
                "目标分类",
                options=category_names_batch,
                key="batch_target_category"
            )

            target_subcategory = st.text_input(
                "二级分类（可选）",
                key="batch_target_subcategory"
            )

            if st.button("🏷️ 批量分类", type="primary", key="batch_classify_btn"):
                if not selected_labels:
                    st.warning("请先选择要分类的交易")
                else:
                    # 找到选中的交易ID
                    selected_indices = [options_list.index(label) for label in selected_labels]
                    batch_count = 0
                    for sel_idx in selected_indices:
                        tid = df_uncat.iloc[sel_idx]['transaction_id']
                        update_data = {
                            'category': target_category,
                            'classification_method': 'manual',
                            'is_verified': True,
                            'classification_confidence': 1.0,
                        }
                        if target_subcategory:
                            update_data['subcategory'] = target_subcategory
                        st.session_state.db.update_transaction(tid, update_data)
                        batch_count += 1

                    st.success(f"✅ 已将 {batch_count} 条交易分类为「{target_category}」")
                    st.rerun()
        elif not category_names_batch:
            st.warning("⚠️ 未找到分类规则配置文件")
    else:
        st.success("✅ 所有交易已分类")

    st.markdown("---")

    # 分类规则查看
    st.subheader("📖 分类规则查看")

    rule_file = "config/classification_rules.yaml"
    if os.path.exists(rule_file):
        with open(rule_file, 'r', encoding='utf-8') as f:
            rules_content = f.read()

        with st.expander("查看一级分类规则"):
            st.code(rules_content, language='yaml')

    subcat_file = "config/subcategory_rules.yaml"
    if os.path.exists(subcat_file):
        with open(subcat_file, 'r', encoding='utf-8') as f:
            subcat_content = f.read()

        with st.expander("查看二级分类规则"):
            st.code(subcat_content, language='yaml')


def show_settings():
    """系统设置页面"""
    st.title("⚙️ 系统设置")

    # AI分类设置
    st.subheader("🤖 AI分类设置")

    use_ai = st.checkbox("启用AI分类（需要Kimi API密钥）", value=False)

    if use_ai:
        api_key = st.text_input("Kimi API Key", type="password")

        if api_key:
            st.info("💡 请在项目根目录的.env文件中配置：KIMI_API_KEY=your_key")
            st.code("KIMI_API_KEY=sk-your-key-here", language="bash")

        st.warning("⚠️ 启用AI分类后，对于规则置信度<0.8的交易将调用Kimi API进行分类")

    st.markdown("---")

    # 数据库信息
    st.subheader("💾 数据库信息")

    db_path = "database/bills.db"
    if os.path.exists(db_path):
        file_size = os.path.getsize(db_path) / 1024 / 1024  # MB
        st.info(f"数据库文件：{db_path}")
        st.info(f"文件大小：{file_size:.2f} MB")

    st.markdown("---")

    # 数据备份
    st.subheader("💾 数据备份")

    if st.button("备份数据库"):
        import shutil
        backup_path = f"database/backup/bills_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(db_path, backup_path)
        st.success(f"✅ 备份成功：{backup_path}")


def main():
    """主函数"""
    page = show_sidebar()

    if page == "📊 财务总览":
        show_dashboard()
    elif page == "📥 数据导入":
        show_import_page()
    elif page == "📋 交易记录":
        show_transactions()
    elif page == "⚠️ 异常检测":
        show_anomaly_page()
    elif page == "🔄 订阅管理":
        show_subscription_page()
    elif page == "💰 预算管理":
        show_budget_page()
    elif page == "🏷️ 分类管理":
        show_category_management()
    elif page == "⚙️ 系统设置":
        show_settings()


if __name__ == "__main__":
    main()
