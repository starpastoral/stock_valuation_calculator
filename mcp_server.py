#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票估值MCP服务器
将股票估值功能暴露为MCP工具，供其他AI助手调用
"""

import asyncio
import json
import logging
from typing import Any, Sequence
import traceback

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    LoggingLevel
)
import mcp.types as types

# 导入估值系统
from valuation import ValuationSystem
from report_generator import ReportGenerator

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stock_valuation_mcp")

class StockValuationMCP:
    """股票估值MCP服务器"""
    
    def __init__(self):
        self.server = Server("stock-valuation-calculator")
        self.valuation_system = ValuationSystem()
        self.report_generator = ReportGenerator()
        
        # 注册工具
        self._register_tools()
        
        # 注册处理器
        self._register_handlers()
    
    def _register_tools(self):
        """注册MCP工具"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """列出所有可用工具"""
            return [
                Tool(
                    name="valuate_stock",
                    description="估值单个股票，使用DCF模型计算内在价值和IRR",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "股票代码，如AAPL, GOOGL等"
                            }
                        },
                        "required": ["symbol"]
                    }
                ),
                Tool(
                    name="valuate_multiple_stocks",
                    description="批量估值多个股票",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbols": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "股票代码列表，如['AAPL', 'GOOGL', 'MSFT']"
                            }
                        },
                        "required": ["symbols"]
                    }
                ),
                Tool(
                    name="valuate_portfolio",
                    description="估值预设的股票组合",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "portfolio_name": {
                                "type": "string",
                                "description": "组合名称，如tech_stocks, bank_stocks等"
                            }
                        },
                        "required": ["portfolio_name"]
                    }
                ),
                Tool(
                    name="list_portfolios",
                    description="列出所有可用的股票组合",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="update_wacc_data",
                    description="更新WACC数据（从达摩达兰网站）",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="list_industries",
                    description="列出所有可用的行业分类",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="generate_excel_report",
                    description="生成Excel格式的估值报告",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbols": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "要包含在报告中的股票代码列表"
                            },
                            "filename": {
                                "type": "string",
                                "description": "输出文件名（可选）"
                            }
                        },
                        "required": ["symbols"]
                    }
                )
            ]
    
    def _register_handlers(self):
        """注册工具处理器"""
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """处理工具调用"""
            try:
                if name == "valuate_stock":
                    return await self._handle_valuate_stock(arguments)
                elif name == "valuate_multiple_stocks":
                    return await self._handle_valuate_multiple_stocks(arguments)
                elif name == "valuate_portfolio":
                    return await self._handle_valuate_portfolio(arguments)
                elif name == "list_portfolios":
                    return await self._handle_list_portfolios(arguments)
                elif name == "update_wacc_data":
                    return await self._handle_update_wacc_data(arguments)
                elif name == "list_industries":
                    return await self._handle_list_industries(arguments)
                elif name == "generate_excel_report":
                    return await self._handle_generate_excel_report(arguments)
                else:
                    raise ValueError(f"未知工具: {name}")
                    
            except Exception as e:
                logger.error(f"工具调用失败 {name}: {e}\n{traceback.format_exc()}")
                return [types.TextContent(
                    type="text",
                    text=f"错误: {str(e)}"
                )]
    
    async def _handle_valuate_stock(self, arguments: dict) -> list[types.TextContent]:
        """处理单股票估值"""
        symbol = arguments["symbol"].upper()
        
        try:
            result = self.valuation_system.valuate_single_stock(symbol)
            
            if 'error' in result:
                response = f"❌ {symbol} 估值失败: {result['error']}"
            else:
                response = self._format_single_valuation(result)
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            return [types.TextContent(
                type="text", 
                text=f"估值 {symbol} 时发生错误: {str(e)}"
            )]
    
    async def _handle_valuate_multiple_stocks(self, arguments: dict) -> list[types.TextContent]:
        """处理多股票估值"""
        symbols = [s.upper() for s in arguments["symbols"]]
        
        try:
            results = self.valuation_system.valuate_multiple_stocks(symbols)
            response = self._format_multiple_valuations(results)
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"批量估值失败: {str(e)}"
            )]
    
    async def _handle_valuate_portfolio(self, arguments: dict) -> list[types.TextContent]:
        """处理组合估值"""
        portfolio_name = arguments["portfolio_name"]
        
        try:
            stocks = self.valuation_system.load_portfolio(portfolio_name)
            if stocks is None:
                return [types.TextContent(
                    type="text",
                    text=f"❌ 组合 '{portfolio_name}' 不存在"
                )]
            
            results = self.valuation_system.valuate_multiple_stocks(stocks)
            response = f"📁 组合: {portfolio_name}\n股票: {', '.join(stocks)}\n\n"
            response += self._format_multiple_valuations(results)
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"组合估值失败: {str(e)}"
            )]
    
    async def _handle_list_portfolios(self, arguments: dict) -> list[types.TextContent]:
        """处理列出组合"""
        try:
            import os
            from config import PORTFOLIOS_FILE
            
            if not os.path.exists(PORTFOLIOS_FILE):
                return [types.TextContent(
                    type="text",
                    text="❌ 没有找到组合文件"
                )]
            
            with open(PORTFOLIOS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            portfolios = data.get('portfolios', {})
            if not portfolios:
                return [types.TextContent(
                    type="text",
                    text="📁 没有配置任何组合"
                )]
            
            response = "📁 可用的股票组合：\n" + "=" * 40 + "\n"
            
            for name, info in portfolios.items():
                description = info.get('description', '无描述')
                stocks = info.get('stocks', [])
                response += f"组合名称: {name}\n"
                response += f"描述: {description}\n"
                response += f"股票数量: {len(stocks)}\n"
                response += f"股票列表: {', '.join(stocks)}\n"
                response += "-" * 30 + "\n"
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"获取组合信息失败: {str(e)}"
            )]
    
    async def _handle_update_wacc_data(self, arguments: dict) -> list[types.TextContent]:
        """处理更新WACC数据"""
        try:
            self.valuation_system.update_wacc_data()
            return [types.TextContent(
                type="text",
                text="✅ WACC数据更新完成"
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"❌ WACC数据更新失败: {str(e)}"
            )]
    
    async def _handle_list_industries(self, arguments: dict) -> list[types.TextContent]:
        """处理列出行业"""
        try:
            # 直接调用现有方法（它会打印到控制台）
            self.valuation_system.list_industries()
            return [types.TextContent(
                type="text",
                text="✅ 行业信息已输出到控制台"
            )]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"❌ 获取行业信息失败: {str(e)}"
            )]
    
    async def _handle_generate_excel_report(self, arguments: dict) -> list[types.TextContent]:
        """处理生成Excel报告"""
        symbols = [s.upper() for s in arguments["symbols"]]
        filename = arguments.get("filename")
        
        try:
            # 先进行估值
            results = self.valuation_system.valuate_multiple_stocks(symbols)
            
            # 生成Excel报告
            filepath = self.report_generator.generate_excel_report(results, filename)
            
            if filepath:
                return [types.TextContent(
                    type="text",
                    text=f"✅ Excel报告已生成: {filepath}"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text="❌ Excel报告生成失败"
                )]
                
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"生成Excel报告失败: {str(e)}"
            )]
    
    def _format_single_valuation(self, result: dict) -> str:
        """格式化单个股票估值结果"""
        if 'error' in result:
            return f"❌ {result['symbol']}: {result['error']}"
        
        response = f"✅ {result['symbol']} ({result.get('name', 'N/A')}) 估值结果：\n"
        response += f"- 当前价格：${result['current_price']:.2f}\n"
        response += f"- 内在价值：${result['intrinsic_value']:.2f}\n"
        response += f"- 年化收益率（IRR）：{result['irr']:.1%}" if result['irr'] else "- 年化收益率（IRR）：N/A"
        response += f"\n- 评估结论：{result['evaluation']}\n"
        
        response += f"\n主要估值参数：\n"
        response += f"- 折现率（WACC）：{result['wacc']:.2%}\n"
        response += f"- 永续增长率：{result['perpetual_growth_rate']:.2%}\n"
        response += f"- 最新自由现金流（FCF）：${result['latest_fcf']:,.2f}\n"
        response += f"- 行业属性：{result.get('damodaran_industry', 'N/A')}"
        
        return response
    
    def _format_multiple_valuations(self, results: list) -> str:
        """格式化多个股票估值结果"""
        response = "📊 批量估值结果：\n" + "=" * 60 + "\n"
        
        for result in results:
            if 'error' in result:
                response += f"❌ {result['symbol']}: {result['error']}\n"
            else:
                response += f"✅ {result['symbol']} ({result.get('name', 'N/A')})\n"
                response += f"   当前价格: ${result['current_price']:.2f}\n"
                response += f"   内在价值: ${result['intrinsic_value']:.2f}\n"
                response += f"   IRR: {result['irr']:.1%}" if result['irr'] else "   IRR: N/A"
                response += f"\n   评估: {result['evaluation']}\n"
                response += f"   WACC: {result['wacc']:.2%}, 永续增长率: {result['perpetual_growth_rate']:.2%}\n"
            response += "-" * 40 + "\n"
        
        return response
    
    async def run(self):
        """运行MCP服务器"""
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, 
                write_stream, 
                InitializationOptions(
                    server_name="stock-valuation-calculator",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )

async def main():
    """主函数"""
    server = StockValuationMCP()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main()) 