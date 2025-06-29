#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票估值计算器安装脚本 - 使用uv包管理器
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def check_uv_installed():
    """检查uv是否已安装"""
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_uv():
    """安装uv包管理器"""
    print("📦 正在安装uv包管理器...")
    
    system = platform.system().lower()
    
    try:
        if system == "darwin":  # macOS
            # 使用brew安装uv
            subprocess.run(['brew', 'install', 'uv'], check=True)
        elif system == "linux":
            # 使用pip安装uv
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'uv'], check=True)
        else:
            # Windows或其他系统
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'uv'], check=True)
        
        print("✅ uv安装成功")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ uv安装失败: {e}")
        print("请手动安装uv:")
        print("  macOS: brew install uv")
        print("  其他: pip install uv")
        return False

def install_dependencies():
    """使用uv安装项目依赖"""
    print("📚 正在安装项目依赖...")
    
    try:
        # 同步依赖
        subprocess.run(['uv', 'sync'], check=True)
        print("✅ 依赖安装成功")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        print("尝试使用传统方式安装:")
        
        try:
            subprocess.run(['uv', 'pip', 'install', '-r', 'requirements.txt'], check=True)
            print("✅ 依赖安装成功（使用requirements.txt）")
            return True
        except subprocess.CalledProcessError as e2:
            print(f"❌ 依赖安装失败: {e2}")
            return False

def setup_data():
    """设置数据"""
    print("\n🔧 设置数据文件...")
    
    try:
        # 运行数据设置脚本
        result = subprocess.run(['python', 'setup.py'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 数据设置完成")
            print(result.stdout)
        else:
            print("⚠️  数据设置需要手动完成")
            print("请运行: python setup.py --stock-file /path/to/your/stock_file.xlsx")
            
        return True
        
    except Exception as e:
        print(f"❌ 数据设置失败: {e}")
        return False

def run_tests():
    """运行基本测试"""
    print("\n🧪 运行基本测试...")
    
    try:
        # 测试导入主要模块
        test_imports = [
            'import yfinance',
            'import pandas', 
            'import numpy',
            'import scipy',
            'import polars',
            'from data_processor import DataProcessor',
            'from wacc_updater import WACCUpdater',
            'from turbo_industry_mapper import TurboIndustryMapper'
        ]
        
        for import_statement in test_imports:
            try:
                exec(import_statement)
                print(f"  ✅ {import_statement}")
            except ImportError as e:
                print(f"  ❌ {import_statement} - {e}")
                return False
        
        print("✅ 所有模块导入成功")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主安装函数"""
    print("🚀 股票估值计算器安装程序")
    print("使用uv进行现代化Python包管理")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 9):
        print("❌ 需要Python 3.9或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    
    print(f"✅ Python版本: {sys.version}")
    
    # 检查并安装uv
    if not check_uv_installed():
        print("📦 uv未安装，正在安装...")
        if not install_uv():
            return False
    else:
        print("✅ uv已安装")
    
    # 创建虚拟环境（如果不存在）
    print("\n🌐 设置虚拟环境...")
    venv_path = Path('.venv')
    
    if not venv_path.exists():
        try:
            subprocess.run(['uv', 'venv'], check=True)
            print("✅ 虚拟环境创建成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ 虚拟环境创建失败: {e}")
            return False
    else:
        print("✅ 虚拟环境已存在")
    
    # 安装依赖
    if not install_dependencies():
        return False
    
    # 设置数据
    setup_data()
    
    # 运行测试
    if not run_tests():
        print("⚠️  测试未通过，但安装可能仍然成功")
    
    print("\n🎉 安装完成！")
    print("\n💡 使用方法:")
    print("  1. 激活虚拟环境:")
    print("     source .venv/bin/activate  # macOS/Linux")
    print("     .venv\\Scripts\\activate     # Windows")
    print("\n  2. 运行股票估值:")
    print("     python valuation.py AAPL")
    print("\n  3. 如有大型股票文件，请运行:")
    print("     python setup.py --stock-file /path/to/stock_file.xlsx")
    print("\n  4. 查看所有选项:")
    print("     python valuation.py --help")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ 安装失败，请检查错误信息")
        sys.exit(1)
    else:
        print("\n✅ 安装成功！") 