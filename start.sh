#!/bin/bash
# 财务分析系统快速启动脚本

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在！"
    echo "请先运行: bash setup_env.sh"
    exit 1
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 启动应用
echo "🚀 启动财务分析系统..."
echo ""
echo "📍 访问地址: http://localhost:8501"
echo "⏹️  停止应用: 按 Ctrl+C"
echo ""

streamlit run app.py
