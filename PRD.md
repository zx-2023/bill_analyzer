# 家庭财务数据分析系统 — 产品需求文档 (PRD)

> **版本**: v1.1  
> **更新日期**: 2026-05-18  
> **状态**: 基于代码审查后更新

---

## 1. 产品概述

### 1.1 产品定位
一个面向家庭用户的本地化财务数据分析工具，支持导入多平台（支付宝、微信支付、银行、美团）账单数据，通过智能分类、去重、异常检测和订阅识别等功能，帮助用户全面了解家庭收支状况。

### 1.2 核心价值
- **隐私优先**: 所有数据本地存储（SQLite），不上传云端
- **多平台聚合**: 统一处理来自不同支付平台的异构账单
- **智能分析**: 自动分类 + AI辅助 + 异常检测 + 订阅识别
- **可视化洞察**: 交互式图表呈现消费趋势和结构

### 1.3 目标用户
家庭财务管理者，需要汇总多平台账单、了解消费结构、发现异常支出和隐性订阅的个人用户。

---

## 2. 功能模块现状

### 2.1 数据导入（✅ 已实现）

| 功能 | 状态 | 说明 |
|------|------|------|
| 支付宝 CSV 导入 | ✅ 完成 | GBK编码，智能表头检测，跳过广告行 |
| 微信支付 CSV 导入 | ✅ 完成 | UTF-8编码，跳过前16行说明 |
| 银行账单 CSV/Excel 导入 | ✅ 完成 | 根据金额正负判断收支 |
| 美团 CSV/Excel 导入 | ✅ 完成 | 外卖订单处理，默认分类餐饮 |
| 支付宝 API 导入 | ✅ 完成 | 商家/企业账号，OAuth + 自用模式 |
| 自动格式检测 | ✅ 完成 | `detect_format()` 校验文件格式 |
| **PDF 账单导入** | ❌ 未实现 | 银行流水PDF、支付宝/微信导出PDF 暂不支持 |

**支持的文件格式**: CSV, XLS, XLSX  
**不支持**: PDF, OFX, QIF

### 2.2 数据处理流水线（✅ 已实现）

完整6步 Pipeline（`src/processors/pipeline.py`）:

1. **数据清洗** — 移除无效记录、标准化字段
2. **智能去重** — 同平台强去重（transaction_id） + 跨平台模糊匹配（时间窗口±5min + 金额 + 描述相似度>80%）
3. **一级分类** — 规则优先（YAML关键词/商户/正则） + AI回退（Kimi API，置信度<0.8时）
4. **二级分类** — 细分子类别（外卖/堂食/咖啡等），置信度>0.6时应用
5. **异常检测** — 大额支出（>95%分位）、异常商户、高频异常
6. **订阅识别** — 月付/年付/周付/双周/季付，基于商户+金额聚类+时间规律

### 2.3 分类系统（✅ 已实现）

**一级分类（10个）**: 餐饮美食、交通出行、购物消费、居家生活、文化娱乐、医疗健康、教育培训、人情往来、金融保险、通讯充值

**分类策略**: 
- 规则分类器: `config/classification_rules.yaml`（关键词0.9、商户0.9、正则0.7）
- AI分类器: Kimi API（`kimi-k2-turbo-preview`，temperature 0.3）
- 混合分类器: 规则优先，置信度<0.8时调用AI

**二级分类**: `config/subcategory_rules.yaml`（如 餐饮美食→外卖/堂食/咖啡奶茶）

### 2.4 数据库设计（✅ 已实现）

**核心表**:
| 表 | 用途 |
|----|------|
| `transactions` | 交易记录（含异常/订阅/分类字段） |
| `categories` | 分类管理（支持层级） |
| `classification_rules` | 分类规则（支持学习） |
| `import_history` | 导入历史（文件哈希防重复） |

**扩展表**（`models_extended.py`，已定义但未集成到主流程）:
| 表 | 用途 | 集成状态 |
|----|------|----------|
| `SubscriptionPattern` | 订阅模式记录 | ⚠️ 定义但未使用 |
| `AnomalyRecord` | 异常记录详情 | ⚠️ 定义但未使用 |
| `MonthlyStatistics` | 月度预计算统计 | ⚠️ 定义但未使用 |
| `BudgetPlan` | 预算计划 | ⚠️ 定义但未使用 |

### 2.5 Web界面（✅ 已实现）

**7个页面**:

| 页面 | 功能 | 核心组件 |
|------|------|----------|
| 📊 财务总览 | 仪表盘 | 6个Plotly图表：趋势线、饼图、月度对比、Top商户、异常散点 |
| 📥 数据导入 | 文件上传 + API导入 | 平台选择、格式检测、流水线处理、统计报告 |
| 📋 交易记录 | 浏览/筛选/导出 | 平台/分类/类型筛选，CSV导出 |
| ⚠️ 异常检测 | 异常交易审查 | 概览卡片、散点图、类型分布、明细表 |
| 🔄 订阅管理 | 订阅服务管理 | 月度/年度成本、周期分布、明细展开 |
| 🏷️ 分类管理 | 未分类处理 | 未分类列表、AI批量分类、规则查看 |
| ⚙️ 系统设置 | 配置管理 | AI设置、数据库信息、备份 |

### 2.6 可视化（✅ 已实现）

`src/visualization/charts.py` 提供6个Plotly图表函数:
- `create_expense_trend_chart` — 支出趋势（日/周/月）
- `create_category_pie_chart` — 分类饼图
- `create_monthly_comparison_chart` — 月度同比/环比
- `create_top_merchants_chart` — Top N 商户
- `create_subscription_chart` — 订阅分布
- `create_anomaly_scatter` — 异常散点图

---

## 3. 已知问题与技术债务

### 3.1 代码质量
| 问题 | 位置 | 严重度 |
|------|------|--------|
| `bare except` 捕获异常 | `app.py:88` (`except:`) | 中 |
| `to_dict()` 缺少异常/订阅字段 | `models.py:61-76` | 高 — 导致前端拿不到 `is_anomaly` 等字段 |
| 分类逐行循环 | `pipeline.py:78-82` | 中 — 大数据量时性能差 |
| Session内返回ORM对象 | `operations.py:128` | 高 — session关闭后访问延迟加载属性会报错 |
| `models_extended.py` 未集成 | `src/database/` | 低 — 表定义存在但无处使用 |
| 根目录散落调试脚本 | `test_parser.py`, `debug_*.py`, `inspect_*.py` 等 | 低 |

### 3.2 功能缺口
| 缺失功能 | 影响 | 优先级 |
|-----------|------|--------|
| PDF账单解析 | 银行流水和部分平台导出为PDF | **高** |
| 手动分类/修正交易 | 用户无法在UI中手动修改分类 | 高 |
| 预算管理 | `BudgetPlan`表已设计但无UI和逻辑 | 中 |
| 数据导出Excel（多Sheet） | 仅支持CSV导出 | 中 |
| 搜索/高级筛选 | 交易记录页筛选能力有限 | 中 |
| 多用户/家庭成员 | 无用户区分 | 低 |
| 自然语言查询 | "上个月餐饮花了多少" | 低 |

### 3.3 测试
- `tests/` 目录为空，无任何自动化测试
- 根目录有若干手工调试脚本（`test_parser.py`, `test_csv_analysis.py`）但非正式测试

---

## 4. 技术栈

| 层 | 技术 |
|----|------|
| 语言 | Python 3.8+ |
| Web框架 | Streamlit |
| 数据处理 | Pandas, NumPy |
| 数据库 | SQLite + SQLAlchemy ORM |
| 可视化 | Plotly |
| AI分类 | Kimi API (kimi-k2-turbo-preview) |
| 支付宝SDK | alipay-sdk-python |
| 配置管理 | PyYAML, python-dotenv |
| 日志 | Loguru |

---

## 5. 数据流架构

```
文件上传/API导入
       │
       ▼
  平台解析器 (AlipayParser / WeChatParser / BankParser / MeituanParser)
       │
       ▼ 标准化 DataFrame
       │
  DataProcessingPipeline
  ├── 1. DataCleaner        — 清洗
  ├── 2. Deduplicator       — 去重
  ├── 3. HybridClassifier   — 一级分类（规则+AI）
  ├── 4. SubcategoryClassifier — 二级分类
  ├── 5. AnomalyDetector    — 异常检测
  └── 6. SubscriptionDetector — 订阅识别
       │
       ▼ 处理后 DataFrame + 统计
       │
  DatabaseManager → SQLite (bills.db)
       │
       ▼
  Streamlit UI → Plotly 图表
```

---

## 6. 未来路线图

### P0 — 高优先级
- [ ] **PDF账单解析**: 支持银行流水PDF、支付宝/微信导出的PDF账单
- [ ] **修复 `to_dict()` 缺失字段**: 确保异常/订阅字段正确传递到前端
- [ ] **修复 Session 生命周期问题**: ORM对象在session外使用的bug
- [ ] **基础测试覆盖**: Parser单元测试、Pipeline集成测试

### P1 — 中优先级
- [ ] 手动分类/修正交易功能
- [ ] 预算管理（利用已有 BudgetPlan 表）
- [ ] Excel多Sheet导出
- [ ] 交易搜索和高级筛选
- [ ] 分类性能优化（向量化替代逐行循环）

### P2 — 低优先级
- [ ] 趋势预测（基于历史数据）
- [ ] 自然语言查询
- [ ] 智能消费建议
- [ ] 定期报告生成
- [ ] 移动端适配
- [ ] 清理根目录调试脚本

---

## 7. 目录结构

```
bill_analyzer/
├── app.py                          # Streamlit 主应用（7个页面）
├── config/
│   ├── classification_rules.yaml   # 一级分类规则
│   ├── subcategory_rules.yaml      # 二级分类规则
│   └── platform_config.yaml        # 平台解析配置
├── src/
│   ├── parsers/                    # 解析器
│   │   ├── base_parser.py
│   │   ├── alipay_parser.py
│   │   ├── wechat_parser.py
│   │   ├── bank_parser.py
│   │   └── meituan_parser.py
│   ├── processors/                 # 处理器
│   │   ├── pipeline.py             # 6步处理流水线
│   │   ├── data_cleaner.py
│   │   ├── deduplicator.py
│   │   ├── anomaly_detector.py
│   │   └── subscription_detector.py
│   ├── classifiers/                # 分类器
│   │   ├── rule_classifier.py
│   │   ├── ai_classifier.py
│   │   ├── hybrid_classifier.py
│   │   └── subcategory_classifier.py
│   ├── database/                   # 数据库
│   │   ├── models.py               # 核心ORM模型
│   │   ├── models_extended.py      # 扩展表（未集成）
│   │   └── operations.py           # CRUD操作
│   ├── integrations/
│   │   └── alipay_client.py        # 支付宝API客户端
│   ├── visualization/
│   │   └── charts.py               # 6个Plotly图表
│   └── utils/
│       └── logger.py
├── data/
│   ├── raw/                        # 原始上传文件（临时）
│   ├── processed/                  # 处理后数据
│   └── exports/                    # 导出文件
├── database/
│   └── bills.db                    # SQLite数据库
├── tests/                          # 测试（当前为空）
│   └── samples/                    # 测试样本文件（待创建）
├── scripts/
│   └── init_db.py                  # 数据库初始化
└── requirements.txt
```

---

## 8. 配置说明

### 环境变量 (.env)
```env
# AI分类（可选）
KIMI_API_KEY=sk-xxx

# 支付宝API（可选，商家账号）
ALIPAY_APP_ID=xxx
ALIPAY_PRIVATE_KEY=xxx
ALIPAY_PUBLIC_KEY=xxx
APP_ENV=production
```

### 分类规则 (classification_rules.yaml)
```yaml
categories:
  分类名:
    keywords: []       # 关键词匹配（置信度0.9）
    merchants: []      # 商户匹配（置信度0.9）
    patterns: []       # 正则匹配（置信度0.7）
    exclude_keywords: [] # 排除关键词（降低置信度50%）
```

---

*本文档基于 2026-05-18 对代码库的完整审查生成，反映项目实际实现状态。*
