"""家庭财务数据分析系统 - Streamlit主应用"""
import streamlit as st
import pandas as pd
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
    except:
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
        df = pd.DataFrame([t.to_dict() for t in transactions])

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

    # 筛选条件
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        platform_filter = st.selectbox("平台", ["全部", "alipay", "wechat", "bank", "meituan"])

    with col2:
        categories = ["全部"] + list(set([
            t.category for t in st.session_state.db.get_transactions(limit=1000)
            if t.category
        ]))
        category_filter = st.selectbox("一级分类", categories)

    with col3:
        type_filter = st.selectbox("类型", ["全部", "income", "expense"])

    with col4:
        limit = st.number_input("显示数量", min_value=10, max_value=1000, value=100)

    # 查询
    transactions = st.session_state.db.get_transactions(
        platform=None if platform_filter == "全部" else platform_filter,
        category=None if category_filter == "全部" else category_filter,
        trans_type=None if type_filter == "全部" else type_filter,
        limit=limit
    )

    if transactions:
        df = pd.DataFrame([t.to_dict() for t in transactions])

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

        # 导出功能
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 导出为CSV",
            data=csv,
            file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("暂无交易记录")


def show_anomaly_page():
    """异常检测页面"""
    st.title("⚠️ 异常交易检测")

    # 获取所有异常交易
    transactions = st.session_state.db.get_transactions(limit=10000)

    if transactions:
        df = pd.DataFrame([t.to_dict() for t in transactions])
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
        df = pd.DataFrame([t.to_dict() for t in transactions])
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


def show_category_management():
    """分类管理页面"""
    st.title("🏷️ 分类管理")

    # 未分类交易
    st.subheader("未分类交易")

    uncategorized = st.session_state.db.get_uncategorized_transactions(limit=100)

    if uncategorized:
        st.warning(f"⚠️ 发现 {len(uncategorized)} 条未分类交易")

        df = pd.DataFrame([t.to_dict() for t in uncategorized])
        st.dataframe(df, use_container_width=True)

        if st.button("使用AI批量分类"):
            st.info("💡 AI分类功能需要配置Kimi API密钥（在系统设置中配置）")
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
    elif page == "🏷️ 分类管理":
        show_category_management()
    elif page == "⚙️ 系统设置":
        show_settings()


if __name__ == "__main__":
    main()
