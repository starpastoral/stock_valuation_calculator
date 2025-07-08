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

# 导入自定义模块
from data_fetcher import StockDataFetcher
from wacc_processor import WACCProcessor
from wacc_updater import WACCUpdater
from turbo_industry_mapper import TurboIndustryMapper
from dcf_calculator import DCFCalculator
from dcf_calculator import EnhancedDCFCalculator
from report_generator import ReportGenerator
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
    
    def valuate_multiple_stocks(self, symbols):
        """估值多个股票"""
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
                print(f"📈 {result['symbol']}: 估值 ${intrinsic_value:.2f} vs 现价 ${current_price:.2f} ({gap:+.1f}%) [方法: {method}]")
    
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
                
                print(f"📈 {symbol} ({name}): 估值 ${intrinsic_value:.2f} | 现价 ${current_price:.2f} | 差距 {gap_str}")
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
                        print(f"   场景估值: 保守 ${model_valuations.get('conservative', {}).get('dcf_value', 0):.2f} | "
                              f"基准 ${model_valuations.get('base', {}).get('dcf_value', 0):.2f} | "
                              f"乐观 ${model_valuations.get('optimistic', {}).get('dcf_value', 0):.2f}")
                        
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