#!/usr/bin/env python3
"""环境检查脚本 - 诊断系统配置问题"""

import sys
import os
from pathlib import Path

def print_header(text):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_python_version():
    """检查Python版本"""
    print("🐍 Python版本检查")
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    print(f"   当前版本: {version_str}")

    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"   ❌ 版本过低，需要3.8+")
        return False
    elif version.major == 3 and version.minor >= 12:
        print(f"   ⚠️  Python 3.12可能有兼容性问题")
        return True
    else:
        print(f"   ✅ 版本符合要求")
        return True

def check_packages():
    """检查必需包"""
    print("\n📦 依赖包检查")

    required_packages = {
        'pandas': '2.1.4',
        'streamlit': '1.29.0',
        'plotly': '5.18.0',
        'sqlalchemy': '2.0.23',
        'numpy': '1.26.2',
        'yaml': 'pyyaml',
        'dotenv': 'python-dotenv',
        'requests': '2.31.0',
        'fuzzywuzzy': '0.18.0'
    }

    all_ok = True
    for package, expected in required_packages.items():
        try:
            if package == 'yaml':
                import yaml
                version = yaml.__version__ if hasattr(yaml, '__version__') else 'unknown'
                package_name = 'pyyaml'
            elif package == 'dotenv':
                import dotenv
                version = dotenv.__version__ if hasattr(dotenv, '__version__') else 'unknown'
                package_name = 'python-dotenv'
            else:
                module = __import__(package)
                version = module.__version__
                package_name = package

            print(f"   ✅ {package_name}: {version}")
        except ImportError:
            print(f"   ❌ {expected}: 未安装")
            all_ok = False
        except Exception as e:
            print(f"   ⚠️  {package}: 检查失败 ({str(e)})")
            all_ok = False

    return all_ok

def check_project_structure():
    """检查项目结构"""
    print("\n📁 项目结构检查")

    required_dirs = [
        'src',
        'src/parsers',
        'src/processors',
        'src/classifiers',
        'src/database',
        'src/visualization',
        'config',
        'scripts',
        'data',
        'data/raw'
    ]

    required_files = [
        'app.py',
        'requirements.txt',
        'README.md',
        'config/classification_rules.yaml',
        'config/subcategory_rules.yaml',
        'scripts/init_db.py'
    ]

    all_ok = True

    # 检查目录
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"   ✅ {dir_path}/")
        else:
            print(f"   ❌ {dir_path}/ (缺失)")
            all_ok = False

    # 检查文件
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} (缺失)")
            all_ok = False

    return all_ok

def check_database():
    """检查数据库"""
    print("\n💾 数据库检查")

    db_path = Path('database/bills.db')

    if not db_path.parent.exists():
        print(f"   ⚠️  database目录不存在，将在首次运行时创建")
        return True

    if db_path.exists():
        size = db_path.stat().st_size / 1024  # KB
        print(f"   ✅ 数据库存在: {db_path}")
        print(f"   📊 文件大小: {size:.2f} KB")

        # 尝试连接数据库
        try:
            from sqlalchemy import create_engine, inspect
            engine = create_engine(f'sqlite:///{db_path}')
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"   📋 数据表数量: {len(tables)}")
            if tables:
                print(f"   📋 表名: {', '.join(tables)}")
            return True
        except Exception as e:
            print(f"   ⚠️  数据库连接失败: {str(e)}")
            return False
    else:
        print(f"   ℹ️  数据库未初始化")
        print(f"   💡 运行: python scripts/init_db.py")
        return True

def check_config_files():
    """检查配置文件"""
    print("\n⚙️  配置文件检查")

    config_files = {
        'config/classification_rules.yaml': '一级分类规则',
        'config/subcategory_rules.yaml': '二级分类规则',
        'config/platform_config.yaml': '平台配置'
    }

    all_ok = True
    for file_path, desc in config_files.items():
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            print(f"   ✅ {desc}: {file_path} ({size} bytes)")
        else:
            print(f"   ❌ {desc}: {file_path} (缺失)")
            all_ok = False

    # 检查.env文件（可选）
    env_path = Path('.env')
    if env_path.exists():
        print(f"   ✅ 环境变量配置: .env")
    else:
        print(f"   ℹ️  环境变量配置: .env (可选，AI分类需要)")

    return all_ok

def check_virtual_env():
    """检查虚拟环境"""
    print("\n🔧 虚拟环境检查")

    in_venv = sys.prefix != sys.base_prefix

    if in_venv:
        print(f"   ✅ 运行在虚拟环境中")
        print(f"   📍 环境路径: {sys.prefix}")
        return True
    else:
        print(f"   ⚠️  未在虚拟环境中运行")
        print(f"   💡 建议: 创建并激活虚拟环境")
        print(f"      python3 -m venv venv")
        print(f"      source venv/bin/activate  (macOS/Linux)")
        print(f"      venv\\Scripts\\activate    (Windows)")
        return False

def main():
    """主函数"""
    print_header("财务分析系统环境检查")

    results = {
        'Python版本': check_python_version(),
        '虚拟环境': check_virtual_env(),
        '依赖包': check_packages(),
        '项目结构': check_project_structure(),
        '配置文件': check_config_files(),
        '数据库': check_database()
    }

    print_header("检查结果汇总")

    all_passed = True
    for check, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {check}: {status}")
        if not result:
            all_passed = False

    print()

    if all_passed:
        print("🎉 所有检查通过！系统已就绪")
        print()
        print("📝 下一步:")
        print("   1. 启动应用: streamlit run app.py")
        print("   2. 或运行: bash start.sh (macOS/Linux)")
        print("   3. 或运行: start.bat (Windows)")
    else:
        print("⚠️  部分检查未通过，请修复上述问题")
        print()
        print("💡 建议:")
        print("   1. 运行环境配置脚本: bash setup_env.sh")
        print("   2. 手动安装缺失的依赖: pip install -r requirements.txt")
        print("   3. 初始化数据库: python scripts/init_db.py")

    print()
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
