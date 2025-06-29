#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI助手测试脚本
验证Ollama服务和AI助手功能是否正常
"""

import sys
import os

def test_ollama_connection():
    """测试Ollama连接"""
    print("🔍 测试Ollama连接...")
    
    try:
        import ollama
        models = ollama.list()
        print("✅ Ollama服务运行正常")
        
        # 显示可用模型
        available_models = [m['name'] for m in models['models']]
        print(f"📋 可用模型: {', '.join(available_models)}")
        
        # 检查推荐模型
        if 'llama3.1' in available_models:
            print("✅ 推荐模型 llama3.1 已安装")
        else:
            print("⚠️  推荐模型 llama3.1 未安装，请运行: ollama pull llama3.1")
            
        return True
        
    except ImportError:
        print("❌ 未安装ollama库，请运行: pip install ollama")
        return False
    except Exception as e:
        print(f"❌ Ollama连接失败: {e}")
        print("请确保Ollama服务正在运行: ollama serve")
        return False

def test_valuation_system():
    """测试估值系统"""
    print("\n🔍 测试估值系统...")
    
    try:
        from valuation import ValuationSystem
        vs = ValuationSystem()
        print("✅ 估值系统模块加载成功")
        
        # 测试数据准备
        if vs.ensure_data_ready():
            print("✅ 数据准备就绪")
        else:
            print("⚠️  数据准备有问题，但系统仍可运行")
            
        return True
        
    except Exception as e:
        print(f"❌ 估值系统测试失败: {e}")
        return False

def test_ai_assistant():
    """测试AI助手"""
    print("\n🔍 测试AI助手...")
    
    try:
        from ai_assistant import StockValuationAI
        
        # 测试创建实例（不实际初始化模型）
        print("✅ AI助手模块加载成功")
        
        # 测试系统提示词
        ai = StockValuationAI.__new__(StockValuationAI)  # 不调用__init__
        prompt = ai.get_system_prompt()
        if len(prompt) > 100:
            print("✅ 系统提示词生成正常")
        else:
            print("⚠️  系统提示词异常")
            
        return True
        
    except Exception as e:
        print(f"❌ AI助手测试失败: {e}")
        return False

def test_dependencies():
    """测试依赖包"""
    print("\n🔍 测试依赖包...")
    
    required_packages = [
        'yfinance', 'pandas', 'numpy', 'scipy', 
        'requests', 'beautifulsoup4', 'rich', 'ollama'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n请安装缺失的包: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def main():
    """主测试函数"""
    print("🧪 股票估值AI助手 - 系统测试")
    print("=" * 50)
    
    tests = [
        ("依赖包测试", test_dependencies),
        ("Ollama连接测试", test_ollama_connection),
        ("估值系统测试", test_valuation_system),
        ("AI助手测试", test_ai_assistant)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 测试结果: {passed}/{total} 项通过")
    
    if passed == total:
        print("🎉 所有测试通过！AI助手已准备就绪")
        print("\n启动AI助手:")
        print("python ai_chat.py")
    else:
        print("⚠️  部分测试未通过，请检查上述错误信息")
        
    print("\n详细使用说明: AI_GUIDE.md")

if __name__ == "__main__":
    main() 