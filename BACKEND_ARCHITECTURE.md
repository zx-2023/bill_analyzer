# 后台架构完整说明文档

## 📋 已实现的核心后台能力

### 1. 增强的数据库设计

#### 主表：Transaction（交易记录）
**新增字段**：
- `subcategory`: 二级分类（如"餐饮美食-外卖"）
- `is_anomaly`, `anomaly_type`, `anomaly_score`, `anomaly_reason`: 异常检测相关
- `is_subscription`, `subscription_group`, `subscription_name`, `subscription_cycle`, `subscription_confidence`: 订阅识别相关

#### 扩展表（models_extended.py）：
1. **SubscriptionPattern**: 订阅模式表 - 记录识别到的定期扣款模式
2. **AnomalyRecord**: 异常记录表 - 详细记录每个异常交易
3. **MonthlyStatistics**: 月度统计表 - 预计算的月度数据，支持趋势分析
4. **BudgetPlan**: 预算计划表 - 用户预算设置和预警

### 2. 完整的平台支持

#### 已实现的解析器：
1. **AlipayParser** (`src/parsers/alipay_parser.py`)
   - GBK编码处理
   - 智能表头检测
   - 支持CSV格式

2. **WeChatParser** (`src/parsers/wechat_parser.py`)
   - UTF-8编码
   - 跳过前16行说明
   - 特殊收支标识处理

3. **BankParser** (`src/parsers/bank_parser.py`)
   - 根据金额正负判断收支
   - 支持多种银行格式
   - 日期时间合并

4. **MeituanParser** (`src/parsers/meituan_parser.py`)
   - 外卖订单处理
   - 默认分类为"餐饮美食-外卖"
   - 商家信息提取

### 3. 智能分类系统

#### 一级分类（10个主分类）：
- 餐饮美食、交通出行、购物消费、居家生活、文化娱乐
- 医疗健康、教育培训、人情往来、金融保险、通讯充值

#### 二级分类（SubcategoryClassifier）：
配置文件：`config/subcategory_rules.yaml`

**示例二级分类**：
- 餐饮美食 → 外卖、堂食、咖啡奶茶、快餐
- 交通出行 → 打车、公共交通、加油、停车、长途出行
- 购物消费 → 线上购物、超市购物、服饰鞋包、数码电器
- 文化娱乐 → 视频会员、音乐会员、电影演出、游戏、健身运动

**分类策略**：
1. 规则优先（关键词、商户、正则表达式）
2. AI辅助（Kimi API，规则置信度<0.8时调用）
3. 两级分类：先一级后二级

### 4. 高级分析功能

#### 异常检测（AnomalyDetector）：
检测类型：
- **大额支出**: 超过95%分位数的交易
- **异常商户**: 陌生商户的大额支出
- **高频异常**: 同一天对同一商户多次大额交易

输出：
- `is_anomaly`: 是否异常
- `anomaly_type`: 异常类型
- `anomaly_score`: 异常分数（0-1）
- `anomaly_reason`: 异常原因说明

#### 订阅识别（SubscriptionDetector）：
识别周期：
- `monthly`: 每月（28-31天）
- `yearly`: 每年（360-370天）
- `weekly`: 每周（6-8天）
- `biweekly`: 每两周（13-15天）
- `quarterly`: 每季度（85-95天）

算法：
1. 按商户分组
2. 按金额聚类（容差10%）
3. 检测时间规律性
4. 计算置信度

输出：
- `is_subscription`: 是否订阅
- `subscription_group`: 订阅组ID
- `subscription_name`: 订阅名称
- `subscription_cycle`: 订阅周期
- `subscription_confidence`: 识别置信度

### 5. 数据处理流水线

#### DataProcessingPipeline（完整流程）：
```python
from src.processors.pipeline import DataProcessingPipeline

pipeline = DataProcessingPipeline(use_ai=False)
result = pipeline.process(df)

# 结果包含：
# - result['df']: 处理后的DataFrame
# - result['stats']: 统计信息
# - result['warnings']: 警告列表
# - result['errors']: 错误列表
```

**处理步骤**：
1. 数据清洗（移除无效记录、标准化）
2. 智能去重（同平台强去重 + 跨平台模糊匹配）
3. 一级分类（规则 + AI）
4. 二级分类（细分）
5. 异常检测
6. 订阅识别

### 6. 可视化组件（Plotly）

#### 已实现的图表（src/visualization/charts.py）：
1. **create_expense_trend_chart**: 支出趋势折线图（按日/周/月）
2. **create_category_pie_chart**: 分类占比饼图
3. **create_monthly_comparison_chart**: 月度同比/环比对比图
4. **create_top_merchants_chart**: Top商户横向条形图
5. **create_subscription_chart**: 订阅扣款分布图
6. **create_anomaly_scatter**: 异常交易散点图

## 🔧 使用方式

### 初始化数据库
```bash
python scripts/init_db.py
```

### 完整数据导入流程示例
```python
from src.parsers.alipay_parser import AlipayParser
from src.processors.pipeline import DataProcessingPipeline
from src.database.operations import DatabaseManager

# 1. 解析账单
parser = AlipayParser()
df = parser.parse('data/raw/alipay_bill.csv')

# 2. 处理数据
pipeline = DataProcessingPipeline(use_ai=False)
result = pipeline.process(df)

# 3. 查看摘要
print(pipeline.get_summary_report(result))

# 4. 导入数据库
db = DatabaseManager()
records = result['df'].to_dict('records')
for record in records:
    if not db.transaction_exists(record['transaction_id']):
        db.add_transaction(record)
```

### 可视化示例
```python
from src.visualization.charts import (
    create_expense_trend_chart,
    create_category_pie_chart,
    create_anomaly_scatter
)

# 趋势图
fig_trend = create_expense_trend_chart(df, period='month')
fig_trend.show()

# 分类饼图
category_stats = db.get_category_stats()
fig_pie = create_category_pie_chart(category_stats)
fig_pie.show()

# 异常散点图
fig_anomaly = create_anomaly_scatter(df)
fig_anomaly.show()
```

## 📊 核心功能对照表

| 需求功能 | 实现状态 | 模块位置 |
|---------|---------|---------|
| 支付宝解析 | ✅ | `src/parsers/alipay_parser.py` |
| 微信解析 | ✅ | `src/parsers/wechat_parser.py` |
| 银行解析 | ✅ | `src/parsers/bank_parser.py` |
| 美团解析 | ✅ | `src/parsers/meituan_parser.py` |
| 智能去重 | ✅ | `src/processors/deduplicator.py` |
| 一级分类 | ✅ | `src/classifiers/hybrid_classifier.py` |
| 二级分类 | ✅ | `src/classifiers/subcategory_classifier.py` |
| 异常检测 | ✅ | `src/processors/anomaly_detector.py` |
| 订阅识别 | ✅ | `src/processors/subscription_detector.py` |
| 趋势分析 | ✅ | `src/visualization/charts.py` |
| 图表可视化 | ✅ | `src/visualization/charts.py` |

## 🎯 关键设计原则

### 1. 数据标准化
所有平台账单统一转换为标准Schema：
```python
{
    'transaction_id': 唯一ID,
    'platform': 平台标识,
    'date': 日期时间,
    'amount': 金额（绝对值）,
    'type': 收支类型（income/expense）,
    'category': 一级分类,
    'subcategory': 二级分类,
    'counterparty': 交易对方,
    'description': 交易描述,
    # ... 其他字段
}
```

### 2. 分层处理
- **解析层**: 各平台解析器 → 标准化DataFrame
- **处理层**: 清洗 → 去重 → 分类 → 检测
- **存储层**: SQLite数据库 → 统计查询
- **展示层**: Streamlit界面 → Plotly可视化

### 3. 可扩展性
- 新增平台：继承BaseParser，添加platform_config
- 新增分类：编辑YAML配置文件
- 新增检测规则：扩展Detector类

### 4. 性能优化
- 向量化操作（pandas）
- 批量数据库操作
- 预计算月度统计
- 分类规则缓存

## 📝 下一步建议

1. **Web界面集成**: 更新Streamlit app.py集成所有新功能
2. **测试数据**: 准备脱敏的测试账单文件
3. **配置优化**: 根据实际使用调整分类规则和检测阈值
4. **性能测试**: 大数据量（>10万条）性能测试

## ⚠️ 重要提示

1. **隐私保护**: 所有数据本地存储，不上传云端
2. **API密钥**: Kimi API密钥需在.env中配置（可选）
3. **数据备份**: 定期备份database/bills.db文件
4. **规则调优**: classification_rules.yaml和subcategory_rules.yaml可根据个人习惯调整
