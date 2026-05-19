# 家庭财务数据分析系统

一个基于Python和Streamlit的家庭账单数据分析工具，支持多平台账单导入、智能分类和可视化分析。

## 功能特性

- ✅ **多平台支持**：支付宝、微信支付、银行卡、美团（目前优先支持支付宝）
- ✅ **智能分类**：基于规则的分类器 + AI辅助（Kimi API）
- ✅ **智能去重**：多维度去重策略，避免重复计算
- ✅ **数据清洗**：自动处理格式不一致、无效数据
- ✅ **可视化分析**：财务总览、分类统计、商户排名
- ✅ **本地存储**：SQLite数据库，数据完全本地化

## 快速开始

### 1. 环境要求

- Python 3.8+
- pip

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 初始化数据库

```bash
python scripts/init_db.py
```

### 4. 配置环境变量（可选）

如果需要使用AI分类功能，复制`.env.example`为`.env`并配置：

```bash
cp .env.example .env
```

编辑`.env`文件，填入Kimi API密钥：

```env
KIMI_API_KEY=sk-your-kimi-api-key-here
```

### 5. 启动应用

```bash
streamlit run app.py
```

应用将在浏览器中自动打开（默认地址：http://localhost:8501）

## 使用指南

### 导入账单数据

1. 导出支付宝账单：
   - 登录支付宝网页版
   - 进入"账单" → "更多" → "下载账单明细"
   - 选择时间范围，格式选择CSV
   - 下载后保存为`alipay_bill.csv`

2. 在应用中导入：
   - 打开"数据导入"页面
   - 上传CSV文件
   - 点击"开始解析并导入"
   - 系统会自动完成：解析 → 清洗 → 去重 → 分类 → 入库

### 查看财务总览

- 进入"财务总览"页面
- 选择日期范围
- 查看总支出、总收入、结余等关键指标
- 查看分类占比和商户排名

### 管理分类

- 进入"分类管理"页面
- 查看未分类交易
- 使用AI批量分类（需配置API密钥）

## 项目结构

```
bill_analyzer/
├── config/                    # 配置文件
│   ├── classification_rules.yaml  # 分类规则
│   └── platform_config.yaml       # 平台解析配置
├── src/                       # 源代码
│   ├── parsers/              # 数据解析器
│   ├── processors/           # 数据处理
│   ├── classifiers/          # 分类引擎
│   ├── database/             # 数据库模型
│   └── visualization/        # 可视化组件
├── data/                      # 数据目录
│   ├── raw/                  # 原始账单
│   ├── processed/            # 处理后数据
│   └── exports/              # 导出文件
├── database/                  # SQLite数据库
├── scripts/                   # 辅助脚本
├── tests/                     # 测试代码
├── app.py                     # Streamlit主应用
└── requirements.txt           # 依赖列表
```

## 开发计划

### 已完成 ✅
- [x] 支付宝账单解析器
- [x] 数据清洗与去重
- [x] 规则分类器
- [x] AI分类器（Kimi API）
- [x] SQLite数据库设计
- [x] Streamlit基础界面
- [x] 财务总览仪表盘

### 进行中 🚧
- [ ] 微信支付解析器
- [ ] 银行卡解析器
- [ ] 美团解析器
- [ ] 可视化图表（Plotly）

### 计划中 📋
- [ ] 数据导出（Excel）
- [ ] 预算管理
- [ ] 异常检测
- [ ] 定期报告生成
- [ ] 移动端适配

## 常见问题

**Q: 支持哪些平台的账单？**

A: 目前优先支持支付宝，后续将陆续支持微信支付、银行卡、美团等平台。

**Q: 数据是否上传到云端？**

A: 不会。所有数据都存储在本地SQLite数据库中，确保隐私安全。

**Q: AI分类是否必须？**

A: 不是。系统默认使用规则分类（免费），AI分类是可选功能，需要Kimi API密钥。

**Q: 如何添加自定义分类规则？**

A: 编辑`config/classification_rules.yaml`文件，添加关键词或正则表达式规则。

## 技术栈

- **后端**：Python 3.8+
- **Web框架**：Streamlit
- **数据处理**：Pandas, NumPy
- **数据库**：SQLite (SQLAlchemy ORM)
- **可视化**：Plotly, Altair
- **AI接口**：Kimi API
- **配置管理**：PyYAML, python-dotenv

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提Issue。
