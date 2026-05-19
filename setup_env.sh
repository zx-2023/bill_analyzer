#!/bin/bash
# 财务分析系统环境配置脚本

echo "🚀 开始配置财务分析系统环境..."
echo ""

# 检查Python版本
echo "1️⃣ 检查Python版本..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   当前Python版本: $PYTHON_VERSION"

# 检查是否满足最低版本要求（3.8+）
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
    echo "   ❌ Python版本过低，需要3.8+，请升级Python"
    exit 1
fi

if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 12 ]; then
    echo "   ⚠️  Python 3.12可能有兼容性问题，建议使用3.9-3.11"
fi

echo "   ✅ Python版本检查通过"
echo ""

# 创建虚拟环境
echo "2️⃣ 创建虚拟环境..."
if [ -d "venv" ]; then
    echo "   ⚠️  虚拟环境已存在，跳过创建"
else
    python3 -m venv venv
    echo "   ✅ 虚拟环境创建成功"
fi
echo ""

# 激活虚拟环境
echo "3️⃣ 激活虚拟环境..."
source venv/bin/activate
echo "   ✅ 虚拟环境已激活"
echo ""

# 升级pip
echo "4️⃣ 升级pip到最新版本..."
pip install --upgrade pip --quiet
echo "   ✅ pip升级完成"
echo ""

# 安装依赖
echo "5️⃣ 安装项目依赖..."
echo "   这可能需要几分钟，请耐心等待..."
pip install -r requirements.txt --quiet

if [ $? -eq 0 ]; then
    echo "   ✅ 依赖安装成功"
else
    echo "   ❌ 依赖安装失败，请检查错误信息"
    exit 1
fi
echo ""

# 验证关键包
echo "6️⃣ 验证关键包安装..."
python -c "import streamlit; print('   ✅ Streamlit:', streamlit.__version__)"
python -c "import pandas; print('   ✅ Pandas:', pandas.__version__)"
python -c "import plotly; print('   ✅ Plotly:', plotly.__version__)"
python -c "import sqlalchemy; print('   ✅ SQLAlchemy:', sqlalchemy.__version__)"
echo ""

# 初始化数据库
echo "7️⃣ 初始化数据库..."
python scripts/init_db.py

if [ $? -eq 0 ]; then
    echo "   ✅ 数据库初始化成功"
else
    echo "   ❌ 数据库初始化失败"
    exit 1
fi
echo ""

# 完成
echo "🎉 环境配置完成！"
echo ""
echo "📝 下一步操作："
echo "   1. 激活虚拟环境: source venv/bin/activate"
echo "   2. 启动应用: streamlit run app.py"
echo "   3. 浏览器访问: http://localhost:8501"
echo ""
echo "💡 提示："
echo "   - 每次使用前需要激活虚拟环境"
echo "   - 退出环境: deactivate"
echo ""
