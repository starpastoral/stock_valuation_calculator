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

# 导入自定义模块
from data_fetcher import StockDataFetcher
from wacc_updater import WACCUpdater
from turbo_industry_mapper import TurboIndustryMapper
from dcf_calculator import DCFCalculator
from report_generator import ReportGenerator
from config import DEFAULT_WACC, PORTFOLIOS_FILE

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ValuationSystem:
    """股票估值系统"""
    
    def __init__(self):
        self.data_fetcher = StockDataFetcher()
        self.wacc_updater = WACCUpdater()
        self.industry_mapper = TurboIndustryMapper()
        self.dcf_calculator = DCFCalculator()
        self.report_generator = ReportGenerator()
    
    def ensure_data_ready(self):
        """确保数据准备就绪"""
        logger.info("检查数据准备状态...")
        
        # 确保WACC数据可用
        if not self.wacc_updater.ensure_wacc_data():
            logger.warning("WACC数据不可用，将使用默认折现率")
        
        return True
    
    def get_wacc_for_stock(self, symbol, sector, industry):
        """获取股票的WACC（使用Turbo缓存直接获取）"""
        # 首先尝试直接从Turbo缓存获取WACC
        wacc = self.industry_mapper.get_wacc_direct(symbol)
        stock_info = self.industry_mapper.get_stock_info(symbol)
        
        if stock_info:
            # 从Turbo缓存成功获取
            damodaran_industry = stock_info.get('industry', '')
            mapping_source = "Turbo缓存"
            logger.info(f"{symbol}: Turbo缓存直接获取 WACC={wacc:.2%}, 行业={damodaran_industry}")
            return wacc, mapping_source, damodaran_industry
        
        # 如果Turbo缓存没有，尝试使用yfinance数据作为兜底
        if industry:
            logger.info(f"{symbol}: Turbo缓存未找到，尝试yfinance行业: {industry}")
            fallback_wacc = self.wacc_updater.get_wacc_for_industry(industry)
            if fallback_wacc is not None:
                return fallback_wacc, "yfinance兜底", industry
            damodaran_industry = industry
        elif sector:
            logger.info(f"{symbol}: Turbo缓存未找到，尝试yfinance板块: {sector}")
            fallback_wacc = self.wacc_updater.get_wacc_for_industry(sector)
            if fallback_wacc is not None:
                return fallback_wacc, "yfinance兜底", sector
            damodaran_industry = sector
        else:
            damodaran_industry = "未知行业"
        
        # 使用默认WACC
        logger.warning(f"{symbol}: 使用默认WACC {DEFAULT_WACC:.2%}")
        return DEFAULT_WACC, "默认值", damodaran_industry
    
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
        
        # 执行DCF计算
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

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='股票估值计算器')
    parser.add_argument('symbols', nargs='*', help='股票代码 (例如: AAPL GOOGL)')
    parser.add_argument('--portfolio', '-p', help='使用股票组合')
    parser.add_argument('--excel', '-e', action='store_true', help='导出到Excel')
    parser.add_argument('--output', '-o', help='输出文件名')
    parser.add_argument('--list-portfolios', action='store_true', help='列出所有股票组合')
    parser.add_argument('--list-industries', action='store_true', help='列出所有可用行业')
    parser.add_argument('--set-industry', nargs=2, metavar=('SYMBOL', 'INDUSTRY'), 
                       help='设置股票的自定义行业 (例如: --set-industry AAPL "计算机与外设")')
    parser.add_argument('--update-wacc', action='store_true', help='更新WACC数据')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建估值系统
    valuation_system = ValuationSystem()
    
    # 处理各种命令
    if args.list_portfolios:
        valuation_system.list_portfolios()
        return
    
    if args.list_industries:
        valuation_system.list_industries()
        return
    
    if args.set_industry:
        symbol, industry = args.set_industry
        if valuation_system.set_custom_industry(symbol, industry):
            print(f"✅ 已设置 {symbol} 的行业为: {industry}")
        else:
            print(f"❌ 设置 {symbol} 的行业失败")
        return
    
    if args.update_wacc:
        if valuation_system.update_wacc_data():
            print("✅ WACC数据更新成功")
        else:
            print("❌ WACC数据更新失败")
        return
    
    # 确保数据准备就绪
    if not valuation_system.ensure_data_ready():
        logger.error("数据准备失败，退出程序")
        sys.exit(1)
    
    # 获取要估值的股票列表
    symbols = []
    
    if args.portfolio:
        # 使用组合
        portfolio_stocks = valuation_system.load_portfolio(args.portfolio)
        if portfolio_stocks:
            symbols = portfolio_stocks
            logger.info(f"使用组合 '{args.portfolio}': {symbols}")
        else:
            sys.exit(1)
    elif args.symbols:
        # 使用命令行参数
        symbols = [s.upper() for s in args.symbols]
    else:
        # 没有指定股票
        parser.print_help()
        sys.exit(1)
    
    if not symbols:
        logger.error("没有指定要估值的股票")
        sys.exit(1)
    
    # 执行估值
    logger.info(f"开始估值 {len(symbols)} 只股票: {symbols}")
    
    if len(symbols) == 1:
        # 单个股票
        result = valuation_system.valuate_single_stock(symbols[0])
        results = [result]
    else:
        # 多个股票
        results = valuation_system.valuate_multiple_stocks(symbols)
    
    # 生成报告
    valuation_system.report_generator.generate_console_report(results)
    valuation_system.report_generator.print_statistics(results)
    
    # 生成Excel报告
    if args.excel:
        filename = args.output if args.output else None
        excel_file = valuation_system.report_generator.generate_excel_report(results, filename)
        if excel_file:
            print(f"\n📊 Excel报告已生成: {excel_file}")
    
    logger.info("估值完成")

if __name__ == "__main__":
    main() 