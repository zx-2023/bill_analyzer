"""Plotly可视化图表组件"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Dict


def create_expense_trend_chart(df: pd.DataFrame, period: str = 'month') -> go.Figure:
    """
    创建支出趋势折线图

    Args:
        df: 交易DataFrame
        period: 聚合周期 ('day', 'week', 'month')

    Returns:
        Plotly Figure对象
    """
    # 只取支出数据
    expense_df = df[df['type'] == 'expense'].copy()

    # 按周期聚合
    expense_df['period'] = pd.to_datetime(expense_df['date'])

    if period == 'day':
        expense_df['period'] = expense_df['period'].dt.date
        title = '每日支出趋势'
    elif period == 'week':
        expense_df['period'] = expense_df['period'].dt.to_period('W').dt.start_time
        title = '每周支出趋势'
    else:  # month
        expense_df['period'] = expense_df['period'].dt.to_period('M').dt.start_time
        title = '每月支出趋势'

    # 聚合统计
    trend_data = expense_df.groupby('period').agg({
        'amount': 'sum',
        'transaction_id': 'count'
    }).reset_index()

    trend_data.columns = ['period', 'total_amount', 'transaction_count']

    # 创建图表
    fig = go.Figure()

    # 支出金额折线
    fig.add_trace(go.Scatter(
        x=trend_data['period'],
        y=trend_data['total_amount'],
        mode='lines+markers',
        name='支出金额',
        line=dict(color='#FF6B6B', width=2),
        marker=dict(size=8),
        hovertemplate='日期: %{x}<br>金额: ¥%{y:.2f}<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        xaxis_title='时间',
        yaxis_title='金额 (¥)',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        font=dict(family="Microsoft YaHei, SimHei, Arial, sans-serif")
    )

    return fig


def create_category_pie_chart(category_stats: List[Dict]) -> go.Figure:
    """
    创建分类占比饼图

    Args:
        category_stats: 分类统计列表

    Returns:
        Plotly Figure对象
    """
    if not category_stats:
        return go.Figure()

    df = pd.DataFrame(category_stats)

    fig = go.Figure(data=[go.Pie(
        labels=df['category'],
        values=df['total_amount'],
        hole=0.3,
        marker=dict(
            colors=px.colors.qualitative.Set3
        ),
        textposition='inside',
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>金额: ¥%{value:.2f}<br>占比: %{percent}<extra></extra>'
    )])

    fig.update_layout(
        title='支出分类占比',
        height=400,
        font=dict(family="Microsoft YaHei, SimHei, Arial, sans-serif")
    )

    return fig


def create_monthly_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """
    创建月度同比/环比对比图

    Args:
        df: 交易DataFrame

    Returns:
        Plotly Figure对象
    """
    expense_df = df[df['type'] == 'expense'].copy()
    expense_df['month'] = pd.to_datetime(expense_df['date']).dt.to_period('M')

    monthly_stats = expense_df.groupby('month').agg({
        'amount': 'sum'
    }).reset_index()

    monthly_stats['month_str'] = monthly_stats['month'].astype(str)
    monthly_stats['mom_change'] = monthly_stats['amount'].pct_change() * 100

    fig = go.Figure()

    # 月度支出柱状图
    fig.add_trace(go.Bar(
        x=monthly_stats['month_str'],
        y=monthly_stats['amount'],
        name='月度支出',
        marker_color='#4ECDC4',
        hovertemplate='月份: %{x}<br>支出: ¥%{y:.2f}<extra></extra>'
    ))

    # 环比变化折线图
    fig.add_trace(go.Scatter(
        x=monthly_stats['month_str'],
        y=monthly_stats['mom_change'],
        name='环比变化率',
        yaxis='y2',
        mode='lines+markers',
        line=dict(color='#FF6B6B', width=2),
        marker=dict(size=8),
        hovertemplate='月份: %{x}<br>环比: %{y:.1f}%<extra></extra>'
    ))

    fig.update_layout(
        title='月度支出对比',
        xaxis_title='月份',
        yaxis=dict(title='支出金额 (¥)'),
        yaxis2=dict(
            title='环比变化率 (%)',
            overlaying='y',
            side='right'
        ),
        hovermode='x unified',
        template='plotly_white',
        height=450,
        font=dict(family="Microsoft YaHei, SimHei, Arial, sans-serif")
    )

    return fig


def create_top_merchants_chart(top_merchants: List[Dict], limit: int = 10) -> go.Figure:
    """
    创建Top商户横向条形图

    Args:
        top_merchants: 商户统计列表
        limit: 显示数量

    Returns:
        Plotly Figure对象
    """
    if not top_merchants:
        return go.Figure()

    df = pd.DataFrame(top_merchants[:limit])

    fig = go.Figure(data=[go.Bar(
        x=df['total_amount'],
        y=df['merchant'],
        orientation='h',
        marker=dict(
            color=df['total_amount'],
            colorscale='Reds',
            showscale=False
        ),
        text=df['total_amount'].apply(lambda x: f'¥{x:.2f}'),
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>总支出: ¥%{x:.2f}<br>交易次数: %{customdata}<extra></extra>',
        customdata=df['count']
    )])

    fig.update_layout(
        title=f'Top {limit} 消费商户',
        xaxis_title='支出金额 (¥)',
        yaxis=dict(autorange='reversed'),  # 从上到下排序
        height=400,
        template='plotly_white',
        font=dict(family="Microsoft YaHei, SimHei, Arial, sans-serif")
    )

    return fig


def create_subscription_chart(subscriptions: List[Dict]) -> go.Figure:
    """
    创建订阅扣款分布图

    Args:
        subscriptions: 订阅统计列表

    Returns:
        Plotly Figure对象
    """
    if not subscriptions:
        return go.Figure()

    df = pd.DataFrame(subscriptions)

    # 颜色映射
    cycle_colors = {
        'monthly': '#4ECDC4',
        'yearly': '#FF6B6B',
        'quarterly': '#95E1D3',
        'weekly': '#FFEAA7',
        'biweekly': '#DFE6E9'
    }

    df['color'] = df['cycle'].map(cycle_colors)

    fig = go.Figure(data=[go.Bar(
        x=df['name'],
        y=df['amount'],
        marker=dict(color=df['color']),
        text=df['cycle'],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>金额: ¥%{y:.2f}<br>周期: %{text}<br>次数: %{customdata}<extra></extra>',
        customdata=df['count']
    )])

    fig.update_layout(
        title='订阅扣款分析',
        xaxis_title='订阅服务',
        yaxis_title='金额 (¥)',
        height=400,
        template='plotly_white',
        font=dict(family="Microsoft YaHei, SimHei, Arial, sans-serif")
    )

    return fig


def create_anomaly_scatter(df: pd.DataFrame) -> go.Figure:
    """
    创建异常交易散点图

    Args:
        df: 交易DataFrame

    Returns:
        Plotly Figure对象
    """
    expense_df = df[df['type'] == 'expense'].copy()

    # 区分正常和异常
    normal = expense_df[expense_df['is_anomaly'] == False]
    anomaly = expense_df[expense_df['is_anomaly'] == True]

    fig = go.Figure()

    # 正常交易
    fig.add_trace(go.Scatter(
        x=normal['date'],
        y=normal['amount'],
        mode='markers',
        name='正常交易',
        marker=dict(color='#4ECDC4', size=6, opacity=0.6),
        hovertemplate='日期: %{x}<br>金额: ¥%{y:.2f}<br>商户: %{customdata}<extra></extra>',
        customdata=normal['counterparty']
    ))

    # 异常交易
    if not anomaly.empty:
        fig.add_trace(go.Scatter(
            x=anomaly['date'],
            y=anomaly['amount'],
            mode='markers',
            name='异常交易',
            marker=dict(
                color='#FF6B6B',
                size=12,
                symbol='diamond',
                line=dict(width=2, color='#C44569')
            ),
            hovertemplate='日期: %{x}<br>金额: ¥%{y:.2f}<br>商户: %{customdata[0]}<br>原因: %{customdata[1]}<extra></extra>',
            customdata=anomaly[['counterparty', 'anomaly_reason']]
        ))

    fig.update_layout(
        title='交易金额分布与异常检测',
        xaxis_title='日期',
        yaxis_title='金额 (¥)',
        hovermode='closest',
        template='plotly_white',
        height=450,
        font=dict(family="Microsoft YaHei, SimHei, Arial, sans-serif")
    )

    return fig
