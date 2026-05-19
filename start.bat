@echo off
REM 财务分析系统快速启动脚本 (Windows版本)

REM 检查虚拟环境
if not exist venv (
    echo ❌ 虚拟环境不存在！
    echo 请先运行: setup_env.bat
    pause
    exit /b 1
)

REM 激活虚拟环境
echo 🔄 激活虚拟环境...
call venv\Scripts\activate.bat

REM 启动应用
echo 🚀 启动财务分析系统...
echo.
echo 📍 访问地址: http://localhost:8501
echo ⏹️  停止应用: 按 Ctrl+C
echo.

streamlit run app.py
