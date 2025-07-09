#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票估值计算器 - 主程序
基于DCF模型进行股票估值，支持单个股票和批量估值
"""

import argparse
import sys
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
import concurrent.futures
import time

# 导入自定义模块
from data_fetcher import StockDataFetcher
from wacc_processor import WACCProcessor
from wacc_updater import WACCUpdater
from turbo_industry_mapper import TurboIndustryMapper
from dcf_calculator import DCFCalculator
from dcf_calculator import EnhancedDCFCalculator
from report_generator import ReportGenerator
from currency_formatter import format_price, format_large_number, format_percentage, get_currency_from_result
from config import DEFAULT_WACC, PORTFOLIOS_FILE, VALUATION_THRESHOLDS, VALUE_RATIO_THRESHOLDS

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ValuationSystem:
    """股票估值系统"""
    
    def __init__(self):
        self.data_fetcher = StockDataFetcher()
        self.dcf_calculator = DCFCalculator()  # 统一使用增强版DCF
        self.report_generator = ReportGenerator()
        self.wacc_processor = WACCProcessor()
        self.wacc_updater = WACCUpdater()
        
        # 新增：会话缓存
        self.session_cache = {}
    
    def ensure_data_ready(self):
        """确保数据已准备好"""
        try:
            # 检查行业WACC数据是否存在
            if not self.wacc_processor.is_data_available():
                logger.info("行业WACC数据不可用，正在更新...")
                self.wacc_updater.update_wacc_data()
            
            logger.info("数据检查完成")
        except Exception as e:
            logger.warning(f"数据准备检查失败: {e}")
    
    def get_wacc_for_stock(self, symbol, sector, industry):
        """获取股票的WACC"""
        try:
            # 优先尝试个股WACC
            from individual_wacc_calculator import IndividualWACCCalculator
            individual_wacc_calc = IndividualWACCCalculator()
            individual_result = individual_wacc_calc.calculate_individual_wacc(symbol)
            
            if 'error' not in individual_result:
                wacc = individual_result['wacc']
                logger.info(f"✅ {symbol}: 使用个股WACC {wacc:.2%}")
                return wacc, '个股WACC', None
            
            # 个股WACC失败，使用行业WACC
            logger.info(f"个股WACC计算失败，使用行业WACC作为备选")
            
            # 使用智能缓存系统
            wacc_info = self.wacc_processor.get_industry_wacc(symbol, sector, industry)
            
            if wacc_info:
                wacc = wacc_info['wacc']
                mapping_source = wacc_info.get('mapping_source', '未知')
                damodaran_industry = wacc_info.get('damodaran_industry', '未知')
                
                logger.info(f"✅ {symbol}: 使用行业WACC {wacc:.2%} (来源: {mapping_source})")
                return wacc, mapping_source, damodaran_industry
            else:
                logger.warning(f"⚠️ {symbol}: 无法获取行业WACC，使用默认值 {DEFAULT_WACC:.2%}")
                return DEFAULT_WACC, '默认WACC', None
                
        except Exception as e:
            logger.error(f"❌ {symbol}: 获取WACC失败 - {e}")
            return DEFAULT_WACC, '默认WACC', None
    
    def valuate_single_stock(self, symbol):
        """估值单个股票"""
        logger.info(f"开始估值股票: {symbol}")
        
        # 获取股票数据
        stock_data = self.data_fetcher.get_complete_data(symbol)
        
        if 'error' in stock_data:
            return {
                'symbol': symbol,
                'error': stock_data['error'],
                'timestamp': datetime.now().isoformat()
            }
        
        # 获取WACC
        wacc, mapping_source, damodaran_industry = self.get_wacc_for_stock(
            symbol, stock_data['sector'], stock_data['industry']
        )
        
        # 执行DCF计算（现在内部使用增强版逻辑）
        dcf_result = self.dcf_calculator.calculate_dcf_valuation(stock_data, wacc)
        
        if 'error' in dcf_result:
            return {
                'symbol': symbol,
                'error': dcf_result['error'],
                'timestamp': datetime.now().isoformat()
            }
        
        # 评估估值
        evaluation = self.dcf_calculator.evaluate_valuation(dcf_result)
        
        # 组装结果
        result = dcf_result.copy()
        result.update({
            'name': stock_data['name'],
            'sector': stock_data['sector'],
            'industry': stock_data['industry'],
            'damodaran_industry': damodaran_industry,
            'mapping_source': mapping_source,
            'evaluation': evaluation,
            'target_currency': stock_data.get('target_currency', 'USD'),
            'currency': stock_data.get('currency', 'USD'),
            'timestamp': datetime.now().isoformat()
        })
        
        # 如果使用了增强版计算，添加额外信息
        if self.dcf_calculator.is_enhanced_calculation(dcf_result):
            result['enhanced_features'] = True
            enhanced_analysis = self.dcf_calculator.get_enhanced_analysis(dcf_result)
            if enhanced_analysis:
                result['stage_analysis'] = enhanced_analysis.get('stage_analysis')
                result['growth_scenarios'] = enhanced_analysis.get('growth_scenarios')
                result['market_implied'] = enhanced_analysis.get('market_implied')
        
        return result
    
    def valuate_multiple_stocks_concurrent(self, symbols: List[str], 
                                         max_workers: int = 4, 
                                         progress_callback=None) -> List[Dict]:
        """
        并发估值多个股票 - 保持完整的估值质量
        
        Args:
            symbols: 股票代码列表
            max_workers: 最大并发数（建议2-6，避免API限制）
            progress_callback: 进度回调函数
        """
        results = []
        completed = 0
        
        def process_with_progress(symbol):
            """带进度更新的处理函数"""
            nonlocal completed
            try:
                result = self.valuate_single_stock(symbol)
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(symbols), symbol)
                return result
            except Exception as e:
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(symbols), symbol, error=str(e))
                return {
                    'symbol': symbol,
                    'error': f'估值失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                }
        
        # 使用线程池并发处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_symbol = {
                executor.submit(process_with_progress, symbol): symbol 
                for symbol in symbols
            }
            
            # 收集结果（保持原有顺序）
            symbol_to_future = {symbol: future for future, symbol in future_to_symbol.items()}
            
            for symbol in symbols:
                future = symbol_to_future[symbol]
                try:
                    result = future.result(timeout=300)  # 5分钟超时
                    results.append(result)
                except concurrent.futures.TimeoutError:
                    results.append({
                        'symbol': symbol,
                        'error': '估值超时（5分钟）',
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    results.append({
                        'symbol': symbol,
                        'error': f'并发处理失败: {str(e)}',
                        'timestamp': datetime.now().isoformat()
                    })
        
        return results
    
    def _default_progress_callback(self, completed, total, current_symbol, error=None):
        """默认进度回调"""
        if error:
            logger.error(f"[{completed}/{total}] ❌ {current_symbol}: {error}")
        else:
            logger.info(f"[{completed}/{total}] ✅ {current_symbol} 估值完成")
    
    def _valuate_multiple_stocks_sequential(self, symbols):
        """保持原有的串行处理逻辑"""
        results = []
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"处理第 {i}/{len(symbols)} 个股票: {symbol}")
            
            try:
                result = self.valuate_single_stock(symbol)
                results.append(result)
            except Exception as e:
                logger.error(f"估值 {symbol} 时发生错误: {e}")
                results.append({
                    'symbol': symbol,
                    'error': f'估值失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
        
        return results

    def valuate_multiple_stocks(self, symbols: List[str], use_concurrent: bool = True) -> List[Dict]:
        """
        估值多个股票 - 兼容原有接口，但提供选择
        
        Args:
            symbols: 股票代码列表
            use_concurrent: 是否使用并发处理（默认True）
        """
        if use_concurrent and len(symbols) >= 3:  # 3个以上股票使用并发
            logger.info(f"检测到{len(symbols)}个股票，启用并发处理模式")
            return self.valuate_multiple_stocks_concurrent(
                symbols, 
                max_workers=min(4, len(symbols)),
                progress_callback=self._default_progress_callback
            )
        else:
            logger.info(f"使用串行处理")
            return self._valuate_multiple_stocks_sequential(symbols)
    
    def performance_test(self, symbols: List[str], test_concurrent: bool = True) -> Dict:
        """
        性能测试 - 对比串行和并发处理的性能
        
        Args:
            symbols: 测试股票代码列表
            test_concurrent: 是否测试并发处理
        
        Returns:
            Dict: 性能测试结果
        """
        results = {
            'test_symbols': symbols,
            'symbol_count': len(symbols),
            'test_date': datetime.now().isoformat(),
            'sequential': {},
            'concurrent': {}
        }
        
        # 测试串行处理
        logger.info(f"🔄 开始串行处理性能测试 - {len(symbols)}个股票")
        start_time = time.time()
        
        try:
            sequential_results = self._valuate_multiple_stocks_sequential(symbols)
            sequential_time = time.time() - start_time
            
            successful_count = len([r for r in sequential_results if 'error' not in r])
            
            results['sequential'] = {
                'total_time': sequential_time,
                'avg_time_per_stock': sequential_time / len(symbols),
                'successful_count': successful_count,
                'error_count': len(symbols) - successful_count,
                'results': sequential_results
            }
            
            logger.info(f"✅ 串行处理完成: {sequential_time:.2f}秒 (平均每股 {sequential_time/len(symbols):.2f}秒)")
            
        except Exception as e:
            logger.error(f"❌ 串行处理测试失败: {e}")
            results['sequential']['error'] = str(e)
        
        # 测试并发处理
        if test_concurrent:
            logger.info(f"🔄 开始并发处理性能测试 - {len(symbols)}个股票")
            start_time = time.time()
            
            try:
                concurrent_results = self.valuate_multiple_stocks_concurrent(
                    symbols, 
                    max_workers=min(4, len(symbols)),
                    progress_callback=self._default_progress_callback
                )
                concurrent_time = time.time() - start_time
                
                successful_count = len([r for r in concurrent_results if 'error' not in r])
                
                results['concurrent'] = {
                    'total_time': concurrent_time,
                    'avg_time_per_stock': concurrent_time / len(symbols),
                    'successful_count': successful_count,
                    'error_count': len(symbols) - successful_count,
                    'results': concurrent_results
                }
                
                logger.info(f"✅ 并发处理完成: {concurrent_time:.2f}秒 (平均每股 {concurrent_time/len(symbols):.2f}秒)")
                
                # 计算性能提升
                if 'total_time' in results['sequential']:
                    speedup = results['sequential']['total_time'] / concurrent_time
                    time_saved = results['sequential']['total_time'] - concurrent_time
                    results['performance_gain'] = {
                        'speedup_ratio': speedup,
                        'time_saved_seconds': time_saved,
                        'time_saved_percent': (time_saved / results['sequential']['total_time']) * 100
                    }
                    
                    logger.info(f"📊 性能提升: {speedup:.2f}x 加速，节省 {time_saved:.2f}秒 ({time_saved/results['sequential']['total_time']*100:.1f}%)")
                
            except Exception as e:
                logger.error(f"❌ 并发处理测试失败: {e}")
                results['concurrent']['error'] = str(e)
        
        return results
    
    def generate_performance_report(self, test_results: Dict) -> str:
        """生成性能测试报告"""
        report = []
        report.append("=" * 60)
        report.append("📊 性能测试报告")
        report.append("=" * 60)
        report.append(f"测试时间: {test_results['test_date']}")
        report.append(f"测试股票数量: {test_results['symbol_count']}")
        report.append(f"测试股票: {', '.join(test_results['test_symbols'])}")
        report.append("-" * 60)
        
        # 串行处理结果
        if 'sequential' in test_results and 'total_time' in test_results['sequential']:
            seq = test_results['sequential']
            report.append("🔄 串行处理:")
            report.append(f"  总耗时: {seq['total_time']:.2f}秒")
            report.append(f"  平均每股: {seq['avg_time_per_stock']:.2f}秒")
            report.append(f"  成功数量: {seq['successful_count']}/{test_results['symbol_count']}")
            report.append(f"  失败数量: {seq['error_count']}")
        
        # 并发处理结果
        if 'concurrent' in test_results and 'total_time' in test_results['concurrent']:
            conc = test_results['concurrent']
            report.append("\n⚡ 并发处理:")
            report.append(f"  总耗时: {conc['total_time']:.2f}秒")
            report.append(f"  平均每股: {conc['avg_time_per_stock']:.2f}秒")
            report.append(f"  成功数量: {conc['successful_count']}/{test_results['symbol_count']}")
            report.append(f"  失败数量: {conc['error_count']}")
        
        # 性能提升
        if 'performance_gain' in test_results:
            gain = test_results['performance_gain']
            report.append("\n🚀 性能提升:")
            report.append(f"  加速比: {gain['speedup_ratio']:.2f}x")
            report.append(f"  节省时间: {gain['time_saved_seconds']:.2f}秒")
            report.append(f"  提升百分比: {gain['time_saved_percent']:.1f}%")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def load_portfolio(self, portfolio_name):
        """加载股票组合"""
        try:
            if not os.path.exists(PORTFOLIOS_FILE):
                logger.error(f"组合文件不存在: {PORTFOLIOS_FILE}")
                return None
            
            with open(PORTFOLIOS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            portfolios = data.get('portfolios', {})
            
            if portfolio_name not in portfolios:
                logger.error(f"未找到组合: {portfolio_name}")
                available = list(portfolios.keys())
                logger.info(f"可用组合: {available}")
                return None
            
            return portfolios[portfolio_name]['stocks']
            
        except Exception as e:
            logger.error(f"加载组合失败: {e}")
            return None
    
    def list_portfolios(self):
        """列出所有可用组合"""
        try:
            if not os.path.exists(PORTFOLIOS_FILE):
                print("没有找到组合文件")
                return
            
            with open(PORTFOLIOS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            portfolios = data.get('portfolios', {})
            
            if not portfolios:
                print("没有配置任何组合")
                return
            
            print("\n可用的股票组合:")
            print("-" * 40)
            
            for name, info in portfolios.items():
                description = info.get('description', '无描述')
                stocks = info.get('stocks', [])
                print(f"组合名称: {name}")
                print(f"描述: {description}")
                print(f"股票数量: {len(stocks)}")
                print(f"股票列表: {', '.join(stocks)}")
                print("-" * 40)
                
        except Exception as e:
            logger.error(f"列出组合失败: {e}")
    
    def set_custom_industry(self, symbol, industry):
        """设置自定义行业（智能缓存不支持此功能）"""
        logger.warning("智能缓存系统不支持自定义行业设置功能")
        return False
    
    def list_industries(self):
        """列出可用行业（从WACC数据获取）"""
        wacc_industries = self.wacc_updater.list_available_industries()
        
        print("\n可用的达摩达兰行业分类:")
        print("-" * 50)
        
        if wacc_industries:
            for i, industry in enumerate(sorted(wacc_industries), 1):
                print(f"{i:2d}. {industry}")
            print("-" * 50)
            print(f"总计: {len(wacc_industries)} 个行业")
        else:
            print("无可用行业数据")
            print("-" * 50)
    
    def update_wacc_data(self):
        """手动更新WACC数据"""
        logger.info("手动更新WACC数据...")
        return self.wacc_updater.update_wacc_data()
    
    def analyze_stock_reverse_dcf(self, symbol):
        """反向DCF分析"""
        logger.info(f"开始反向DCF分析: {symbol}")
        
        # 获取股票数据
        stock_data = self.data_fetcher.get_complete_data(symbol)
        
        if 'error' in stock_data:
            return {
                'symbol': symbol,
                'error': stock_data['error'],
                'timestamp': datetime.now().isoformat()
            }
        
        # 获取WACC
        wacc, mapping_source, damodaran_industry = self.get_wacc_for_stock(
            symbol, stock_data['sector'], stock_data['industry']
        )
        
        # 执行反向DCF计算
        from dcf_calculator import ReverseDCFCalculator
        reverse_dcf = ReverseDCFCalculator()
        
        reverse_result = reverse_dcf.calculate_implied_growth(
            symbol, float(stock_data['current_price']), stock_data, wacc
        )
        
        if 'error' in reverse_result:
            return {
                'symbol': symbol,
                'error': reverse_result['error'],
                'timestamp': datetime.now().isoformat()
            }
        
        # 组装结果
        result = {
            'symbol': symbol,
            'name': stock_data['name'],
            'sector': stock_data['sector'],
            'industry': stock_data['industry'],
            'current_price': stock_data['current_price'],
            'wacc': wacc,
            'implied_growth': reverse_result,
            'timestamp': datetime.now().isoformat()
        }
        
        return result
    
    def batch_analyze_reverse_dcf(self, symbols):
        """批量反向DCF分析"""
        results = []
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"反向DCF分析第 {i}/{len(symbols)} 个股票: {symbol}")
            
            try:
                result = self.analyze_stock_reverse_dcf(symbol)
                results.append(result)
            except Exception as e:
                logger.error(f"反向DCF分析 {symbol} 时发生错误: {e}")
                results.append({
                    'symbol': symbol,
                    'error': f'分析失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
        
        return results
    
    def compare_traditional_vs_enhanced(self, symbol):
        """对比传统DCF与增强版DCF（现在统一使用增强版）"""
        logger.info(f"开始对比分析: {symbol}")
        
        # 获取股票数据
        stock_data = self.data_fetcher.get_complete_data(symbol)
        
        if 'error' in stock_data:
            return {
                'symbol': symbol,
                'error': stock_data['error'],
                'timestamp': datetime.now().isoformat()
            }
        
        # 获取WACC
        wacc, mapping_source, damodaran_industry = self.get_wacc_for_stock(
            symbol, stock_data['sector'], stock_data['industry']
        )
        
        # 执行DCF计算（现在内部已经是增强版）
        dcf_result = self.dcf_calculator.calculate_dcf_valuation(stock_data, wacc)
        
        if 'error' in dcf_result:
            return {
                'symbol': symbol,
                'error': dcf_result['error'],
                'timestamp': datetime.now().isoformat()
            }
        
        # 获取增强版分析详情
        enhanced_analysis = self.dcf_calculator.get_enhanced_analysis(dcf_result)
        
        # 组装结果
        result = {
            'symbol': symbol,
            'name': stock_data['name'],
            'sector': stock_data['sector'],
            'industry': stock_data['industry'],
            'current_price': stock_data['current_price'],
            'wacc': wacc,
            'unified_dcf_result': dcf_result,
            'enhanced_analysis': enhanced_analysis,
            'calculation_method': dcf_result.get('calculation_method', 'enhanced_dcf'),
            'timestamp': datetime.now().isoformat()
        }
        
        return result

class IndividualWACCCalculator:
    """
    个股WACC计算器
    使用Alpha Vantage API获取个股数据，并计算WACC
    """
    def __init__(self):
        self.alpha_vantage_api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
        if not self.alpha_vantage_api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY 环境变量未设置")
        self.base_url = "https://www.alphavantage.co/query"
        self.wacc_data = {}
        self.data_processor = None # 新增：数据处理器

    def calculate_individual_wacc(self, symbol):
        """计算个股WACC"""
        try:
            from individual_wacc_calculator import IndividualWACCCalculator
            from data_processor import DataProcessor
            
            calculator = IndividualWACCCalculator()
            wacc_result = calculator.calculate_individual_wacc(symbol)
            
            if wacc_result and 'wacc' in wacc_result:
                # 🔧 重要修复：对WACC极端值进行修正
                processor = DataProcessor()
                original_wacc = wacc_result['wacc']
                corrected_wacc = processor.fix_wacc_extremes(original_wacc, symbol)
                
                if abs(corrected_wacc - original_wacc) > 0.001:  # 如果有修正
                    logger.warning(f"{symbol}: WACC修正 {original_wacc:.4f} -> {corrected_wacc:.4f}")
                    wacc_result['wacc'] = corrected_wacc
                    wacc_result['wacc_original'] = original_wacc
                    wacc_result['wacc_corrected'] = True
                
                return wacc_result['wacc']
            else:
                logger.warning(f"{symbol}: 无法计算个股WACC，使用行业WACC")
                return None
                
        except Exception as e:
            logger.error(f"计算个股WACC失败: {e}")
            return None

def main():
    """主程序"""
    parser = argparse.ArgumentParser(description='股票估值计算器')
    parser.add_argument('symbols', nargs='*', help='股票代码（多个用空格分隔）')
    parser.add_argument('--portfolio', '-p', help='使用股票组合')
    parser.add_argument('--excel', '-e', action='store_true', help='生成Excel报告')
    parser.add_argument('--output', '-o', help='输出文件名')
    parser.add_argument('--industries', action='store_true', help='列出可用行业')
    parser.add_argument('--portfolios', action='store_true', help='列出可用组合')
    parser.add_argument('--update', action='store_true', help='更新WACC数据')
    parser.add_argument('--reverse-dcf', action='store_true', help='反向DCF分析')
    parser.add_argument('--compare', action='store_true', help='对比分析')
    parser.add_argument('--performance-test', action='store_true', help='运行性能测试')
    
    args = parser.parse_args()
    
    # 创建估值系统
    valuation_system = ValuationSystem()
    
    # 处理不同的命令
    if args.industries:
        valuation_system.list_industries()
        return
    
    if args.portfolios:
        valuation_system.list_portfolios()
        return
    
    if args.update:
        valuation_system.update_wacc_data()
        return
    
    # 获取股票列表
    symbols = []
    if args.portfolio:
        portfolio_symbols = valuation_system.load_portfolio(args.portfolio)
        if portfolio_symbols:
            symbols = portfolio_symbols
        else:
            print(f"无法加载组合: {args.portfolio}")
            return
    elif args.symbols:
        symbols = [s.upper() for s in args.symbols]
    else:
        print("请指定股票代码或使用 --help 查看帮助")
        return
    
    # 确保数据准备好
    valuation_system.ensure_data_ready()
    
    print(f"\n准备分析 {len(symbols)} 个股票: {', '.join(symbols)}")
    
    # 执行分析
    if args.reverse_dcf:
        results = valuation_system.batch_analyze_reverse_dcf(symbols)
        print("\n🔮 反向DCF分析结果:")
        for result in results:
            if 'error' in result:
                print(f"❌ {result['symbol']}: {result['error']}")
            else:
                implied = result['implied_growth']
                print(f"📊 {result['symbol']}: 市场隐含增长率 {implied['implied_growth_percent']}")
    
    elif args.compare:
        results = []
        for symbol in symbols:
            result = valuation_system.compare_traditional_vs_enhanced(symbol)
            results.append(result)
        
        print("\n📊 对比分析结果:")
        for result in results:
            if 'error' in result:
                print(f"❌ {result['symbol']}: {result['error']}")
            else:
                method = result.get('calculation_method', 'enhanced_dcf')
                dcf_result = result['unified_dcf_result']
                intrinsic_value = dcf_result.get('intrinsic_value', 0)
                current_price = result['current_price']
                gap = (intrinsic_value - current_price) / current_price * 100
                currency = get_currency_from_result(result)
                print(f"📈 {result['symbol']}: 估值 {format_price(intrinsic_value, result)} vs 现价 {format_price(current_price, result)} ({gap:+.1f}%) [方法: {method}]")
    
    elif args.performance_test:
        # 运行性能测试
        test_symbols = symbols[:5] # 使用前5个股票进行性能测试
        test_results = valuation_system.performance_test(test_symbols)
        print(valuation_system.generate_performance_report(test_results))
    
    else:
        # 标准估值分析
        results = valuation_system.valuate_multiple_stocks(symbols)
        
        # 显示结果
        print("\n📊 估值结果:")
        print("-" * 80)
        
        for result in results:
            if 'error' in result:
                print(f"❌ {result['symbol']}: {result['error']}")
            else:
                symbol = result['symbol']
                name = result.get('name', 'N/A')
                intrinsic_value = result.get('intrinsic_value', 0)
                current_price = result.get('current_price', 0)
                irr = result.get('irr', 0)
                evaluation = result.get('evaluation', '无法评估')
                implied_growth_percent = result.get('implied_growth_percent', 'N/A')
                calculation_method = result.get('calculation_method', 'traditional_dcf')
                
                # 计算估值差距
                if current_price > 0:
                    gap = (intrinsic_value - current_price) / current_price * 100
                    gap_str = f"{gap:+.1f}%"
                else:
                    gap_str = "N/A"
                
                currency = get_currency_from_result(result)
                print(f"📈 {symbol} ({name}): 估值 {format_price(intrinsic_value, result)} | 现价 {format_price(current_price, result)} | 差距 {gap_str}")
                print(f"   IRR: {irr:.2%} | 隐含增长率: {implied_growth_percent} | 评估: {evaluation}")
                print(f"   计算方法: {calculation_method}")
                
                # 显示发展阶段信息
                stage_analysis = result.get('stage_analysis')
                if stage_analysis:
                    print(f"   发展阶段: {stage_analysis.stage} (置信度: {stage_analysis.confidence:.1%})")
                    print(f"   关键驱动: {', '.join(stage_analysis.key_drivers)}")
                    
                    # 显示各场景估值
                    model_valuations = result.get('model_valuations', {})
                    if model_valuations:
                                            conservative_val = model_valuations.get('conservative', {}).get('dcf_value', 0)
                    base_val = model_valuations.get('base', {}).get('dcf_value', 0)
                    optimistic_val = model_valuations.get('optimistic', {}).get('dcf_value', 0)
                    print(f"   场景估值: 保守 {format_price(conservative_val, result)} | "
                          f"基准 {format_price(base_val, result)} | "
                          f"乐观 {format_price(optimistic_val, result)}")
                        
                    # 显示投资建议
                    recommendation = result.get('recommendation', {})
                    if recommendation:
                        print(f"   投资建议: {recommendation.get('action', 'N/A')} ({recommendation.get('rationale', 'N/A')})")
                
                print("-" * 80)
    
    # 生成Excel报告
    if args.excel:
        output_file = args.output or f"估值报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        try:
            valuation_system.report_generator.generate_excel_report(results, output_file)
            print(f"✅ Excel报告已生成: {output_file}")
        except Exception as e:
            print(f"❌ Excel报告生成失败: {e}")

if __name__ == "__main__":
    main() 