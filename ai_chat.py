#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票估值AI助手启动脚本
简化的启动接口
"""

import sys
import os

# 确保能导入ai_assistant模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """主函数"""
    # 检查Ollama是否安装和运行
    try:
        import ollama
        # 测试连接
        ollama.list()
    except ImportError:
        print("❌ 错误: 未安装ollama库")
        print("请运行: pip install ollama")
        return 1
    except Exception as e:
        print("❌ 错误: Ollama服务未运行")
        print("请先启动Ollama服务:")
        print("  macOS: ollama serve")
        print("  或者: brew services start ollama")
        return 1
    
    # 导入并启动AI助手
    try:
        from ai_assistant import StockValuationAI
        
        print("🚀 正在启动股票估值AI助手...")
        
        # 检查命令行参数
        if len(sys.argv) > 1:
            # 直接查询模式
            query = " ".join(sys.argv[1:])
            ai = StockValuationAI()
            response = ai.chat(query)
            print("\n" + "="*60)
            print("AI助手回复:")
            print("="*60)
            print(response)
        else:
            # 交互式模式
            ai = StockValuationAI()
            ai.run_interactive()
            
    except Exception as e:
        print(f"❌ 启动失败: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 