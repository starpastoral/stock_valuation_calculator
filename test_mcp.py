#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP服务器测试脚本
验证MCP服务器是否正常工作
"""

import asyncio
import json
import sys
import traceback
from pathlib import Path

def test_mcp_dependencies():
    """测试MCP依赖"""
    print("🔍 测试MCP依赖...")
    
    try:
        import mcp
        print("✅ MCP库已安装")
        
        from mcp.server import Server
        from mcp.types import Tool, TextContent
        print("✅ MCP核心模块导入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ MCP依赖缺失: {e}")
        print("请运行: uv sync")
        return False
    except Exception as e:
        print(f"❌ MCP依赖测试失败: {e}")
        return False

def test_valuation_dependencies():
    """测试估值系统依赖"""
    print("\n🔍 测试估值系统依赖...")
    
    try:
        from valuation import ValuationSystem
        from report_generator import ReportGenerator
        print("✅ 估值系统模块导入成功")
        
        # 测试创建实例
        vs = ValuationSystem()
        rg = ReportGenerator()
        print("✅ 估值系统实例创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 估值系统依赖测试失败: {e}")
        return False

async def test_mcp_server():
    """测试MCP服务器"""
    print("\n🔍 测试MCP服务器...")
    
    try:
        from mcp_server import StockValuationMCP
        
        # 创建服务器实例
        server = StockValuationMCP()
        print("✅ MCP服务器实例创建成功")
        
        # 验证服务器属性
        if hasattr(server, 'server'):
            print("✅ MCP服务器对象已初始化")
        
        if hasattr(server, 'valuation_system'):
            print("✅ 估值系统已集成")
        
        print("✅ MCP服务器测试通过")
        return True
        
    except Exception as e:
        print(f"❌ MCP服务器测试失败: {e}")
        traceback.print_exc()
        return False

def test_config_file():
    """测试配置文件"""
    print("\n🔍 测试配置文件...")
    
    config_file = Path("mcp_config.json")
    
    if not config_file.exists():
        print("❌ 配置文件不存在")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("✅ 配置文件格式正确")
        
        # 检查配置内容
        if 'mcpServers' in config:
            servers = config['mcpServers']
            if 'stock-valuation-calculator' in servers:
                server_config = servers['stock-valuation-calculator']
                print(f"✅ 服务器配置: {server_config.get('command', 'N/A')}")
                print(f"   工作目录: {server_config.get('cwd', 'N/A')}")
                return True
            else:
                print("❌ 缺少股票估值服务器配置")
                return False
        else:
            print("❌ 配置文件格式错误")
            return False
            
    except json.JSONDecodeError as e:
        print(f"❌ 配置文件JSON格式错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 配置文件测试失败: {e}")
        return False

def generate_claude_config():
    """生成Claude Desktop配置"""
    print("\n📝 生成Claude Desktop配置...")
    
    current_dir = Path.cwd()
    
    config = {
        "mcpServers": {
            "stock-valuation-calculator": {
                "command": "uv",
                "args": [
                    "--directory",
                    str(current_dir),
                    "run",
                    "python",
                    "mcp_server.py"
                ]
            }
        }
    }
    
    print("Claude Desktop配置内容:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
    
    # 保存配置文件
    output_file = current_dir / "claude_desktop_config.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 配置已保存到: {output_file}")
    
    # 给出使用说明
    import platform
    if platform.system() == "Darwin":  # macOS
        config_path = "~/Library/Application Support/Claude/claude_desktop_config.json"
    else:  # Windows
        config_path = "%APPDATA%\\Claude\\claude_desktop_config.json"
    
    print(f"\n📋 使用说明:")
    print(f"1. 复制上述配置内容到: {config_path}")
    print(f"2. 重启Claude Desktop")
    print(f"3. 测试: 在Claude中输入 '估值苹果公司'")

async def main():
    """主测试函数"""
    print("🧪 股票估值MCP服务器 - 测试套件")
    print("=" * 50)
    
    tests = [
        ("MCP依赖测试", test_mcp_dependencies),
        ("估值系统依赖测试", test_valuation_dependencies),
        ("MCP服务器测试", test_mcp_server),
        ("配置文件测试", test_config_file)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 测试结果: {passed}/{total} 项通过")
    
    if passed == total:
        print("🎉 所有测试通过！MCP服务器已准备就绪")
        generate_claude_config()
    else:
        print("⚠️  部分测试未通过，请检查上述错误信息")
    
    print("\n详细配置指南: MCP_GUIDE.md")

if __name__ == "__main__":
    asyncio.run(main()) 