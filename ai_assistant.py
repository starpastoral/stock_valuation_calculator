#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票估值AI助手 - 基于Ollama的对话式界面
提供自然语言交互来调用股票估值功能
"""

import sys
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
import re

try:
    import ollama
except ImportError:
    print("错误: 未安装ollama库，请运行: pip install ollama")
    sys.exit(1)

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

# 导入估值系统模块
from valuation import ValuationSystem
from config import PORTFOLIOS_FILE

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StockValuationAI:
    """股票估值AI助手"""
    
    def __init__(self, model_name: Optional[str] = None):
        self.console = Console()
        self.valuation_system = ValuationSystem()
        self.conversation_history = []
        
        # 验证Ollama服务
        if not self._check_ollama_service():
            self.console.print("[red]错误: Ollama服务未运行，请先启动Ollama[/red]")
            sys.exit(1)
        
        # 自动选择可用模型
        selected_model = self._select_available_model(model_name)
        if not selected_model:
            self.console.print("[red]错误: 没有可用的模型，请先安装一个模型[/red]")
            sys.exit(1)
        
        # 确保model_name为字符串类型
        self.model_name: str = selected_model
        self.console.print(f"[green]✅ 使用模型: {self.model_name}[/green]")
    
    def _check_ollama_service(self) -> bool:
        """检查Ollama服务是否运行"""
        try:
            ollama.list()
            return True
        except Exception as e:
            logger.error(f"Ollama服务检查失败: {e}")
            return False
    
    def _select_available_model(self, preferred_model=None) -> Optional[str]:
        """自动选择可用模型"""
        try:
            models = ollama.list()
            available_models = [model.model for model in models.models if model.model]
            
            if not available_models:
                self.console.print("[yellow]没有安装任何模型，推荐安装: ollama pull llama3.1[/yellow]")
                return None
            
            # 如果指定了首选模型且可用，使用它
            if preferred_model and preferred_model in available_models:
                return preferred_model
            
            # 模型优先级列表（按推荐程度排序）
            preferred_models = [
                'llama3.1', 'llama3.1:8b', 'llama3.1:70b',
                'llama3', 'llama3:8b', 'llama3:70b', 
                'llama2', 'llama2:7b', 'llama2:13b',
                'qwen', 'qwen:7b', 'qwen:14b',
                'gemma', 'gemma:7b', 'gemma:2b'
            ]
            
            # 寻找推荐的模型
            for model in preferred_models:
                if model in available_models:
                    self.console.print(f"[cyan]找到推荐模型: {model}[/cyan]")
                    return model
            
            # 如果没有找到推荐模型，使用第一个可用的
            selected_model = available_models[0]
            self.console.print(f"[yellow]使用第一个可用模型: {selected_model}[/yellow]")
            self.console.print(f"[dim]可用模型列表: {', '.join(available_models)}[/dim]")
            return selected_model
            
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return None
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个专业的股票估值AI助手，可以帮助用户进行股票估值分析。

你的核心能力包括：
1. 估值单个股票 - 使用DCF模型计算内在价值和IRR
2. 批量估值多个股票 - 同时分析多支股票
3. 管理股票组合 - 查看和估值预设的股票组合
4. 查看可用组合列表
5. 更新WACC数据（每月更新）
6. 查看行业分类信息

DCF模型关键参数说明（标准做法）：
- 增长率：基于历史数据计算，用于预测未来10年现金流
- 永续增长率：固定为2.5%（名义GDP增长率），仅用于终值计算
- 折现率(WACC)：基于达摩达兰行业数据的加权平均资本成本

重要限制：
- 你只能通过调用指定的函数来实现功能，不能自己计算或编造数据
- 所有估值数据来自yfinance和达摩达兰WACC表
- 你不能提供投资建议，只能提供估值分析结果
- 采用标准DCF做法：永续增长率固定为2.5%，增长率用于预测10年现金流
- 如果用户询问超出你能力范围的问题，请明确说明

可用函数：
- valuate_stock(symbol): 估值单个股票
- valuate_stocks(symbols): 估值多个股票（用逗号分隔）
- valuate_portfolio(name): 估值指定组合
- list_portfolios(): 查看所有可用组合
- update_wacc(): 更新WACC数据
- list_industries(): 查看行业分类

用户输入示例和对应函数调用：
- "估值苹果" -> valuate_stock("AAPL")
- "分析TSLA和NVDA" -> valuate_stocks("TSLA,NVDA") 
- "估值科技股组合" -> valuate_portfolio("tech_stocks")
- "有哪些组合" -> list_portfolios()
- "更新数据" -> update_wacc()

请用专业但友好的语气回答，并且总是通过函数调用来获取真实数据。"""

    def _extract_function_calls(self, response: str) -> List[Dict[str, Any]]:
        """从AI响应中提取函数调用"""
        function_calls = []
        
        # 匹配函数调用模式
        patterns = [
            r'valuate_stock\(["\']([^"\']+)["\']\)',
            r'valuate_stocks\(["\']([^"\']+)["\']\)',
            r'valuate_portfolio\(["\']([^"\']+)["\']\)',
            r'list_portfolios\(\)',
            r'update_wacc\(\)',
            r'list_industries\(\)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response)
            if 'valuate_stock(' in response and pattern.startswith('valuate_stock'):
                for match in matches:
                    function_calls.append({'function': 'valuate_stock', 'args': [match]})
            elif 'valuate_stocks(' in response and pattern.startswith('valuate_stocks'):
                for match in matches:
                    function_calls.append({'function': 'valuate_stocks', 'args': [match]})
            elif 'valuate_portfolio(' in response and pattern.startswith('valuate_portfolio'):
                for match in matches:
                    function_calls.append({'function': 'valuate_portfolio', 'args': [match]})
            elif 'list_portfolios()' in response:
                function_calls.append({'function': 'list_portfolios', 'args': []})
            elif 'update_wacc()' in response:
                function_calls.append({'function': 'update_wacc', 'args': []})
            elif 'list_industries()' in response:
                function_calls.append({'function': 'list_industries', 'args': []})
        
        return function_calls
    
    def _execute_function(self, function_name: str, args: List[str]) -> Dict[str, Any]:
        """执行函数调用"""
        try:
            if function_name == 'valuate_stock':
                if len(args) != 1:
                    return {'error': '参数错误：需要1个股票代码'}
                result = self.valuation_system.valuate_single_stock(args[0].upper())
                return {'success': True, 'data': result}
            
            elif function_name == 'valuate_stocks':
                if len(args) != 1:
                    return {'error': '参数错误：需要股票代码列表（逗号分隔）'}
                symbols = [s.strip().upper() for s in args[0].split(',')]
                results = self.valuation_system.valuate_multiple_stocks(symbols)
                return {'success': True, 'data': results}
            
            elif function_name == 'valuate_portfolio':
                if len(args) != 1:
                    return {'error': '参数错误：需要组合名称'}
                portfolio_name = args[0]
                stocks = self.valuation_system.load_portfolio(portfolio_name)
                if stocks is None:
                    return {'error': f'组合 {portfolio_name} 不存在'}
                results = self.valuation_system.valuate_multiple_stocks(stocks)
                return {'success': True, 'data': results, 'portfolio_name': portfolio_name}
            
            elif function_name == 'list_portfolios':
                return {'success': True, 'action': 'list_portfolios'}
            
            elif function_name == 'update_wacc':
                return {'success': True, 'action': 'update_wacc'}
            
            elif function_name == 'list_industries':
                return {'success': True, 'action': 'list_industries'}
            
            else:
                return {'error': f'未知函数: {function_name}'}
                
        except Exception as e:
            logger.error(f"执行函数 {function_name} 失败: {e}")
            return {'error': f'执行失败: {str(e)}'}
    
    def _format_valuation_result(self, data) -> str:
        """格式化估值结果"""
        if isinstance(data, list):
            # 多个股票的结果
            formatted = "\n📊 批量估值结果：\n"
            formatted += "=" * 60 + "\n"
            
            for result in data:
                if 'error' in result:
                    formatted += f"❌ {result['symbol']}: {result['error']}\n"
                else:
                    formatted += f"✅ {result['symbol']} ({result.get('name', 'N/A')})\n"
                    formatted += f"   当前价格: ${result['current_price']:.2f}\n"
                    formatted += f"   内在价值: ${result['intrinsic_value']:.2f}\n"
                    formatted += f"   IRR: {result['irr']:.1%}" if result['irr'] else "   IRR: N/A"
                    formatted += f"\n   评估: {result['evaluation']}\n"
                    formatted += f"   WACC: {result['wacc']:.2%}, 永续增长率: {result['perpetual_growth_rate']:.2%}\n"
                formatted += "-" * 40 + "\n"
        else:
            # 单个股票的结果
            if 'error' in data:
                formatted = f"❌ {data['symbol']}: {data['error']}"
            else:
                formatted = f"✅ {data['symbol']} ({data.get('name', 'N/A')}) 估值结果：\n"
                formatted += f"当前价格: ${data['current_price']:.2f}\n"
                formatted += f"内在价值: ${data['intrinsic_value']:.2f}\n"
                formatted += f"IRR: {data['irr']:.1%}" if data['irr'] else "IRR: N/A"
                formatted += f"\n评估结果: {data['evaluation']}\n"
                formatted += f"\n主要估值参数：\n"
                formatted += f"  折现率（WACC）: {data['wacc']:.2%}\n"
                formatted += f"  永续增长率: {data['perpetual_growth_rate']:.2%}\n"
                formatted += f"  最新自由现金流（FCF）: ${data['latest_fcf']:,}\n"
        
        return formatted
    
    def _handle_function_results(self, results: List[Dict[str, Any]]) -> str:
        """处理函数执行结果"""
        output = ""
        
        for result in results:
            if not result.get('success', False):
                output += f"❌ 错误: {result.get('error', '未知错误')}\n"
                continue
            
            if 'data' in result:
                output += self._format_valuation_result(result['data'])
                
                # 如果是组合估值，显示组合信息
                if 'portfolio_name' in result:
                    output += f"\n📁 组合: {result['portfolio_name']}\n"
                
            elif result.get('action') == 'list_portfolios':
                output += self._get_portfolios_info()
            elif result.get('action') == 'update_wacc':
                try:
                    self.valuation_system.update_wacc_data()
                    output += "✅ WACC数据更新完成\n"
                except Exception as e:
                    output += f"❌ WACC数据更新失败: {str(e)}\n"
            elif result.get('action') == 'list_industries':
                output += self._get_industries_info()
        
        return output
    
    def _get_portfolios_info(self) -> str:
        """获取组合信息"""
        try:
            import os
            if not os.path.exists(PORTFOLIOS_FILE):
                return "❌ 没有找到组合文件\n"
            
            with open(PORTFOLIOS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            portfolios = data.get('portfolios', {})
            if not portfolios:
                return "📁 没有配置任何组合\n"
            
            output = "📁 可用的股票组合：\n"
            output += "=" * 40 + "\n"
            
            for name, info in portfolios.items():
                description = info.get('description', '无描述')
                stocks = info.get('stocks', [])
                output += f"组合名称: {name}\n"
                output += f"描述: {description}\n"
                output += f"股票数量: {len(stocks)}\n"
                output += f"股票列表: {', '.join(stocks)}\n"
                output += "-" * 30 + "\n"
            
            return output
            
        except Exception as e:
            return f"❌ 获取组合信息失败: {str(e)}\n"
    
    def _get_industries_info(self) -> str:
        """获取行业信息"""
        try:
            self.valuation_system.list_industries()
            return "✅ 行业信息已在上方显示\n"
        except Exception as e:
            return f"❌ 获取行业信息失败: {str(e)}\n"
    
    def chat(self, user_input: str) -> str:
        """处理用户输入并返回响应"""
        try:
            # 将用户输入添加到对话历史
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # 调用Ollama生成响应
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.get_system_prompt()},
                    *self.conversation_history
                ]
            )
            
            ai_response = response['message']['content']
            
            # 提取函数调用
            function_calls = self._extract_function_calls(ai_response)
            
            # 执行函数调用
            function_results = []
            if function_calls:
                for call in function_calls:
                    result = self._execute_function(call['function'], call['args'])
                    function_results.append(result)
            
            # 处理函数结果
            function_output = ""
            if function_results:
                function_output = self._handle_function_results(function_results)
            
            # 构建最终响应
            final_response = ai_response
            if function_output:
                final_response += f"\n\n{function_output}"
            
            # 将AI响应添加到对话历史
            self.conversation_history.append({
                "role": "assistant", 
                "content": final_response
            })
            
            return final_response
            
        except Exception as e:
            error_msg = f"处理请求时发生错误: {str(e)}"
            logger.error(f"Chat error: {e}\n{traceback.format_exc()}")
            return error_msg
    
    def run_interactive(self):
        """运行交互式对话"""
        self.console.print(Panel(
            "[bold blue]🤖 股票估值AI助手[/bold blue]\n\n"
            "我可以帮您进行股票估值分析，支持以下功能：\n"
            "• 估值单个股票（如：估值苹果、分析TSLA）\n"
            "• 批量估值（如：分析AAPL,GOOGL,MSFT）\n"
            "• 组合估值（如：估值科技股组合）\n"
            "• 查看组合列表（如：有哪些组合）\n"
            "• 更新数据（如：更新WACC数据）\n\n"
            "[yellow]输入 'quit' 或 'exit' 退出[/yellow]",
            title="欢迎使用股票估值AI助手",
            border_style="blue"
        ))
        
        while True:
            try:
                user_input = Prompt.ask("\n[bold green]您[/bold green]", default="")
                
                if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                    self.console.print("[yellow]再见！感谢使用股票估值AI助手！[/yellow]")
                    break
                
                if not user_input.strip():
                    continue
                
                # 显示思考中...
                with self.console.status("[bold yellow]AI正在分析中...[/bold yellow]"):
                    response = self.chat(user_input)
                
                # 显示AI响应
                self.console.print(Panel(
                    Markdown(response),
                    title="[bold blue]🤖 AI助手[/bold blue]",
                    border_style="blue"
                ))
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]程序被中断，再见！[/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]发生错误: {str(e)}[/red]")
                logger.error(f"Interactive error: {e}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='股票估值AI助手')
    parser.add_argument('--model', help='指定Ollama模型名称（可选，默认自动选择）')
    parser.add_argument('--chat', action='store_true', help='启动交互式对话')
    parser.add_argument('--query', type=str, help='直接查询（非交互模式）')
    
    args = parser.parse_args()
    
    # 创建AI助手实例（如果未指定模型，会自动选择）
    ai_assistant = StockValuationAI(model_name=args.model)
    
    if args.query:
        # 单次查询模式
        response = ai_assistant.chat(args.query)
        print(response)
    else:
        # 交互式模式
        ai_assistant.run_interactive()

if __name__ == "__main__":
    main()
