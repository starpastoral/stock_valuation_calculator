# 数据获取模块
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from currency_converter import CurrencyConverter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockDataFetcher:
    """股票数据获取器"""
    
    def __init__(self):
        self.cache = {}
        self.currency_converter = CurrencyConverter()
    
    def get_stock_info(self, symbol):
        """获取股票基本信息"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # 检查必要字段
            required_fields = ['sector', 'industry', 'marketCap', 'currentPrice']
            missing_fields = [field for field in required_fields if field not in info or info[field] is None]
            
            if missing_fields:
                logger.warning(f"{symbol}: 缺少字段 {missing_fields}")
                return None
                
            return {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'sector': info.get('sector', '未知'),
                'industry': info.get('industry', '未知'),
                'market_cap': info.get('marketCap', 0),
                'current_price': info.get('currentPrice', 0),
                'currency': info.get('currency', 'USD')
            }
            
        except Exception as e:
            logger.error(f"获取 {symbol} 基本信息失败: {e}")
            return None
    
    def get_financial_data(self, symbol):
        """获取财务数据"""
        try:
            ticker = yf.Ticker(symbol)
            
            # 获取现金流量表
            cash_flow = ticker.cashflow
            if cash_flow.empty:
                logger.warning(f"{symbol}: 现金流数据为空")
                return None
            
            # 获取资产负债表
            balance_sheet = ticker.balance_sheet
            if balance_sheet.empty:
                logger.warning(f"{symbol}: 资产负债表数据为空")
                return None
            
            # 获取利润表
            income_stmt = ticker.financials
            if income_stmt.empty:
                logger.warning(f"{symbol}: 利润表数据为空")
                return None
            
            return {
                'cash_flow': cash_flow,
                'balance_sheet': balance_sheet,
                'income_statement': income_stmt
            }
            
        except Exception as e:
            logger.error(f"获取 {symbol} 财务数据失败: {e}")
            return None
    
    def calculate_free_cash_flow(self, symbol):
        """计算自由现金流"""
        try:
            financial_data = self.get_financial_data(symbol)
            if not financial_data:
                return None
            
            cash_flow = financial_data['cash_flow']
            
            # 获取经营现金流和资本支出
            operating_cash_flow = cash_flow.loc['Total Cash From Operating Activities'] if 'Total Cash From Operating Activities' in cash_flow.index else None
            capex = cash_flow.loc['Capital Expenditures'] if 'Capital Expenditures' in cash_flow.index else None
            
            if operating_cash_flow is None or capex is None:
                # 尝试其他字段名
                for field in cash_flow.index:
                    if 'Operating' in field and 'Cash' in field:
                        operating_cash_flow = cash_flow.loc[field]
                        break
                
                for field in cash_flow.index:
                    if 'Capital' in field and ('Expenditure' in field or 'Investment' in field):
                        capex = cash_flow.loc[field]
                        break
            
            if operating_cash_flow is None or capex is None:
                logger.warning(f"{symbol}: 无法找到经营现金流或资本支出数据")
                return None
            
            # 计算自由现金流（资本支出通常为负数）
            free_cash_flow = operating_cash_flow + capex
            
            # 转换为正序排列（最新年份在前）
            free_cash_flow = free_cash_flow.sort_index(ascending=False)
            
            # 检查是否有足够的历史数据
            if len(free_cash_flow) < 3:
                logger.warning(f"{symbol}: 历史现金流数据不足")
                return None
            
            # 检查最近2年现金流情况
            recent_fcf = free_cash_flow.head(2)  # 最近2年
            if (recent_fcf <= 0).all():
                logger.warning(f"{symbol}: 最近2年都是负自由现金流，无法估值")
                return None
            
            # 如果有历史负现金流但最新年份为正，给出警告但继续
            if (free_cash_flow <= 0).any():
                negative_years = free_cash_flow[free_cash_flow <= 0]
                logger.warning(f"{symbol}: 历史存在负自由现金流年份: {negative_years.index.year.tolist()}")
            
            # 确保最新年份现金流为正
            if free_cash_flow.iloc[0] <= 0:
                logger.warning(f"{symbol}: 最新年份现金流为负，无法估值")
                return None
            
            return free_cash_flow
            
        except Exception as e:
            logger.error(f"计算 {symbol} 自由现金流失败: {e}")
            return None
    

    
    def get_shares_outstanding(self, symbol):
        """获取流通股数"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            shares = info.get('sharesOutstanding')
            if shares is None:
                shares = info.get('impliedSharesOutstanding') 
            if shares is None:
                shares = info.get('floatShares')
            
            return shares
            
        except Exception as e:
            logger.error(f"获取 {symbol} 流通股数失败: {e}")
            return None
    


    def get_complete_data(self, symbol):
        """获取完整的股票数据用于估值"""
        logger.info(f"获取 {symbol} 的完整数据...")
        
        # 获取基本信息
        stock_info = self.get_stock_info(symbol)
        if not stock_info:
            return {"error": "无法获取基本信息"}
        
        # 获取自由现金流
        fcf = self.calculate_free_cash_flow(symbol)
        if fcf is None:
            return {"error": "无法计算自由现金流"}
        
        # 货币转换
        latest_fcf_original = fcf.iloc[0]
        latest_fcf_converted, target_currency, source_currency, exchange_rate = self.currency_converter.convert_financial_data(symbol, latest_fcf_original)
        
        # 转换所有历史自由现金流
        fcf_converted = {}
        for date, value in fcf.items():
            if pd.notna(value):
                converted_value, _, _, _ = self.currency_converter.convert_financial_data(symbol, value)
                fcf_converted[date] = converted_value
            else:
                fcf_converted[date] = value
        
        # 获取货币信息
        currency_info = self.currency_converter.get_currency_info(symbol)
        
        # 获取流通股数
        shares_outstanding = self.get_shares_outstanding(symbol)
        if shares_outstanding is None:
            return {"error": "无法获取流通股数"}
        
        return {
            'symbol': symbol,
            'name': stock_info['name'],
            'sector': stock_info['sector'],
            'industry': stock_info['industry'],
            'current_price': stock_info['current_price'],
            'market_cap': stock_info['market_cap'],
            'currency': target_currency,  # 使用转换后的目标货币
            'free_cash_flow': fcf_converted,
            'latest_fcf': latest_fcf_converted,
            'latest_fcf_original': latest_fcf_original,
            'exchange_rate': exchange_rate,
            'source_currency': source_currency,
            'target_currency': target_currency,
            'currency_info': currency_info,
            'shares_outstanding': shares_outstanding,
            'data_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        } 