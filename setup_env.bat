@echo off
REM 财务分析系统环境配置脚本 (Windows版本)

echo 🚀 开始配置财务分析系统环境...
echo.

REM 检查Python版本
echo 1️⃣ 检查Python版本...
python --version
if %errorlevel% neq 0 (
    echo    ❌ Python未安装或未添加到PATH
    echo    请访问 https://www.python.org/downloads/ 下载安装
    pause
    exit /b 1
)
echo    ✅ Python检查通过
echo.

REM 创建虚拟环境
echo 2️⃣ 创建虚拟环境...
if exist venv (
    echo    ⚠️  虚拟环境已存在，跳过创建
) else (
    python -m venv venv
    echo    ✅ 虚拟环境创建成功
)
echo.

REM 激活虚拟环境
echo 3️⃣ 激活虚拟环境...
call venv\Scripts\activate.bat
echo    ✅ 虚拟环境已激活
echo.

REM 升级pip
echo 4️⃣ 升级pip...
python -m pip install --upgrade pip --quiet
echo    ✅ pip升级完成
echo.

REM 安装依赖
echo 5️⃣ 安装项目依赖...
echo    这可能需要几分钟，请耐心等待...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo    ❌ 依赖安装失败
    pause
    exit /b 1
)
echo    ✅ 依赖安装成功
echo.

REM 验证安装
echo 6️⃣ 验证安装...
python -c "import streamlit; print('   ✅ Streamlit:', streamlit.__version__)"
python -c "import pandas; print('   ✅ Pandas:', pandas.__version__)"
echo.

REM 初始化数据库
echo 7️⃣ 初始化数据库...
python scripts\init_db.py
if %errorlevel% neq 0 (
    echo    ❌ 数据库初始化失败
    pause
    exit /b 1
)
echo    ✅ 数据库初始化成功
echo.

REM 完成
echo 🎉 环境配置完成！
echo.
echo 📝 下一步操作：
echo    1. 激活虚拟环境: venv\Scripts\activate
echo    2. 启动应用: streamlit run app.py
echo    3. 或直接运行: start.bat
echo.

pause
