#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个股WACC计算器
实现基于公司财务数据的个股WACC自动计算
"""

import yfinance as yf
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

class IndividualWACCCalculator:
    """个股WACC计算器"""
    
    def __init__(self):
        self.risk_free_rate = None
        self.market_risk_premium = 0.055  # 默认市场风险溢价 5.5%
        self._update_risk_free_rate()
    
    def _update_risk_free_rate(self):
        """更新无风险利率（美国10年期国债收益率）"""
        try:
            # 获取美国10年期国债收益率作为无风险利率
            treasury = yf.Ticker("^TNX")
            hist = treasury.history(period="5d")
            if not hist.empty:
                self.risk_free_rate = hist['Close'].iloc[-1] / 100  # 转换为小数
                logger.info(f"无风险利率 (10年期美债): {self.risk_free_rate:.4f}")
            else:
                self.risk_free_rate = 0.045  # 默认4.5%
                logger.warning("无法获取实时无风险利率，使用默认值 4.5%")
        except Exception as e:
            logger.error(f"获取无风险利率失败: {e}")
            self.risk_free_rate = 0.045  # 默认4.5%
    
    def get_beta(self, symbol: str) -> Optional[float]:
        """获取股票的Beta值"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            beta = info.get('beta')
            if beta is None or not isinstance(beta, (int, float)):
                logger.warning(f"{symbol}: Beta值无效或不存在")
                return 1.0  # 默认Beta = 1
            return float(beta)
        except Exception as e:
            logger.error(f"获取 {symbol} Beta值失败: {e}")
            return 1.0
    
    def calculate_cost_of_equity(self, symbol: str, beta: Optional[float] = None) -> float:
        """计算股权成本 (Cost of Equity)"""
        if beta is None:
            beta = self.get_beta(symbol)
        
        # 确保beta不为None
        if beta is None:
            beta = 1.0
        
        if self.risk_free_rate is None:
            self._update_risk_free_rate()
        
        # 确保risk_free_rate不为None
        if self.risk_free_rate is None:
            self.risk_free_rate = 0.045  # 设置默认值
        
        # CAPM模型: Re = Rf + β * (ERP)
        cost_of_equity = self.risk_free_rate + beta * self.market_risk_premium
        
        logger.info(f"{symbol}: 股权成本 = {self.risk_free_rate:.4f} + {beta:.4f} × {self.market_risk_premium:.4f} = {cost_of_equity:.4f}")
        return cost_of_equity
    
    def get_debt_info(self, symbol: str) -> Dict:
        """获取债务信息"""
        try:
            ticker = yf.Ticker(symbol)
            
            # 获取资产负债表
            balance_sheet = ticker.balance_sheet
            if balance_sheet.empty:
                logger.warning(f"{symbol}: 无法获取资产负债表")
                return {}
            
            # 获取损益表
            income_stmt = ticker.income_stmt
            if income_stmt.empty:
                logger.warning(f"{symbol}: 无法获取损益表")
                return {}
            
            # 获取现金流量表
            cash_flow = ticker.cashflow
            
            # 获取最新年度数据
            latest_bs = balance_sheet.iloc[:, 0]
            latest_income = income_stmt.iloc[:, 0]
            latest_cf = cash_flow.iloc[:, 0] if not cash_flow.empty else pd.Series()
            
            # 获取债务信息
            total_debt = 0
            short_term_debt = 0
            long_term_debt = 0
            cash_and_equivalents = 0
            
            # 债务字段
            if 'Total Debt' in latest_bs.index:
                total_debt = latest_bs['Total Debt'] if pd.notna(latest_bs['Total Debt']) else 0
            else:
                # 分别获取短期和长期债务
                if 'Current Debt' in latest_bs.index:
                    short_term_debt = latest_bs['Current Debt'] if pd.notna(latest_bs['Current Debt']) else 0
                elif 'Current Debt And Capital Lease Obligation' in latest_bs.index:
                    short_term_debt = latest_bs['Current Debt And Capital Lease Obligation'] if pd.notna(latest_bs['Current Debt And Capital Lease Obligation']) else 0
                
                if 'Long Term Debt' in latest_bs.index:
                    long_term_debt = latest_bs['Long Term Debt'] if pd.notna(latest_bs['Long Term Debt']) else 0
                elif 'Long Term Debt And Capital Lease Obligation' in latest_bs.index:
                    long_term_debt = latest_bs['Long Term Debt And Capital Lease Obligation'] if pd.notna(latest_bs['Long Term Debt And Capital Lease Obligation']) else 0
                
                total_debt = short_term_debt + long_term_debt
            
            # 现金和现金等价物
            cash_fields = ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments', 'Cash']
            for field in cash_fields:
                if field in latest_bs.index and pd.notna(latest_bs[field]):
                    cash_and_equivalents = latest_bs[field]
                    break
            
            # 净债务
            net_debt = total_debt - cash_and_equivalents
            
            # 利息费用 - 多种来源
            interest_expense = 0
            
            # 1. 从损益表获取利息费用
            interest_fields = [
                'Interest Expense',
                'Interest Expense Non Operating', 
                'Net Interest Income'
            ]
            
            for field in interest_fields:
                if field in latest_income.index and pd.notna(latest_income[field]):
                    value = latest_income[field]
                    if field == 'Net Interest Income':
                        # 净利息收入为负表示利息支出
                        if value < 0:
                            interest_expense = abs(value)
                        else:
                            # 如果是正的净利息收入，说明现金收益大于债务成本
                            interest_expense = 0
                    else:
                        interest_expense = abs(value)
                    break
            
            # 2. 从现金流量表获取利息支付（作为补充）
            interest_paid = 0
            if not cash_flow.empty:
                for field in latest_cf.index:
                    field_str = str(field)  # 确保field是字符串
                    if 'interest' in field_str.lower() and 'paid' in field_str.lower():
                        value = latest_cf[field]
                        if pd.notna(value):
                            interest_paid = abs(value)
                            break
            
            # 选择较合理的利息费用
            if interest_expense == 0 and interest_paid > 0:
                interest_expense = interest_paid
            
            return {
                'total_debt': total_debt,
                'short_term_debt': short_term_debt,
                'long_term_debt': long_term_debt,
                'cash_and_equivalents': cash_and_equivalents,
                'net_debt': net_debt,
                'interest_expense': interest_expense,
                'interest_paid': interest_paid
            }
            
        except Exception as e:
            logger.error(f"获取 {symbol} 债务信息失败: {e}")
            return {}
    
    def calculate_cost_of_debt(self, symbol: str, debt_info: Optional[Dict] = None) -> float:
        """计算债务成本 (Cost of Debt)"""
        if debt_info is None:
            debt_info = self.get_debt_info(symbol)
        
        total_debt = debt_info.get('total_debt', 0)
        net_debt = debt_info.get('net_debt', 0)
        interest_expense = debt_info.get('interest_expense', 0)
        cash_and_equivalents = debt_info.get('cash_and_equivalents', 0)
        
        # 如果现金大于债务，公司实际上是净现金状态
        if net_debt <= 0:
            logger.info(f"{symbol}: 净现金公司 (现金: {cash_and_equivalents:,.0f}, 债务: {total_debt:,.0f})")
            return 0.01  # 使用很低的成本（1%）
        
        # 如果没有债务，使用默认成本
        if total_debt <= 0:
            logger.warning(f"{symbol}: 无债务，使用默认债务成本 1%")
            return 0.01
        
        # 如果没有利息费用，使用默认成本
        if interest_expense <= 0:
            logger.warning(f"{symbol}: 无利息费用，使用默认债务成本 3%")
            return 0.03
        
        # 计算债务成本
        cost_of_debt = interest_expense / total_debt
        
        # 合理性检查
        if cost_of_debt > 0.20:  # 超过20%可能异常
            logger.warning(f"{symbol}: 债务成本异常高 ({cost_of_debt:.2%})，使用默认值 5%")
            return 0.05
        
        logger.info(f"{symbol}: 债务成本 = {interest_expense:,.0f} / {total_debt:,.0f} = {cost_of_debt:.4f}")
        return cost_of_debt
    
    def get_market_cap(self, symbol: str) -> float:
        """获取市值"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            market_cap = info.get('marketCap')
            if market_cap is None:
                logger.warning(f"{symbol}: 无法获取市值")
                return 0
            return float(market_cap)
        except Exception as e:
            logger.error(f"获取 {symbol} 市值失败: {e}")
            return 0
    
    def get_tax_rate(self, symbol: str) -> float:
        """获取税率"""
        try:
            ticker = yf.Ticker(symbol)
            income_stmt = ticker.income_stmt
            
            if income_stmt.empty:
                logger.warning(f"{symbol}: 无法获取损益表，使用默认税率")
                return 0.25  # 默认25%
            
            # 获取多年数据分析
            tax_rates = []
            profitable_years = 0
            
            for i, col in enumerate(income_stmt.columns):
                year_data = income_stmt.iloc[:, i]
                pretax = year_data.get('Pretax Income')
                tax_provision = year_data.get('Tax Provision')
                
                if pd.notna(pretax) and pd.notna(tax_provision):
                    if pretax > 0:  # 盈利年份
                        effective_rate = tax_provision / pretax
                        if 0 <= effective_rate <= 0.6:  # 合理范围
                            tax_rates.append(effective_rate)
                            profitable_years += 1
                            logger.info(f"{symbol}: {col.year}年税率 = {effective_rate:.2%}")
            
            latest_income = income_stmt.iloc[:, 0]
            latest_pretax = latest_income.get('Pretax Income')
            
            # 1. 如果当前年份亏损，使用历史平均税率或预期税率
            if pd.notna(latest_pretax) and latest_pretax <= 0:
                logger.warning(f"{symbol}: 当前年份亏损，税前利润={latest_pretax:,.0f}")
                
                if tax_rates:
                    avg_rate = sum(tax_rates) / len(tax_rates)
                    logger.info(f"{symbol}: 使用历史平均税率 = {avg_rate:.2%}")
                    return avg_rate
                else:
                    # 使用基于国家的默认税率
                    return self._get_default_tax_rate(symbol)
            
            # 2. 当前年份盈利，检查最新税率
            latest_tax_provision = latest_income.get('Tax Provision')
            if pd.notna(latest_pretax) and pd.notna(latest_tax_provision) and latest_pretax > 0:
                latest_rate = latest_tax_provision / latest_pretax
                
                # 检查是否为异常低税率（可能是NOL抵扣）
                if latest_rate < 0.10:  # 税率低于10%
                    logger.warning(f"{symbol}: 检测到异常低税率 {latest_rate:.2%}，可能原因：")
                    logger.warning(f"  - 前期亏损结转(NOL)抵扣")
                    logger.warning(f"  - 税收优惠或抵扣")
                    
                    # 如果有历史数据，评估是否应该使用NOL调整后的税率
                    if len(tax_rates) > 1:
                        # 计算历史正常税率
                        normal_rates = [rate for rate in tax_rates if rate >= 0.10]
                        if normal_rates:
                            normal_avg = sum(normal_rates) / len(normal_rates)
                            logger.info(f"{symbol}: 历史正常税率平均 = {normal_avg:.2%}")
                            
                            # 如果NOL抵扣是暂时的，考虑使用正常税率进行WACC计算
                            # 但对于WACC计算，我们可以选择保守估计
                            logger.info(f"{symbol}: 选择使用当前实际税率 {latest_rate:.2%} (考虑NOL效应)")
                            return latest_rate
                
                # 检查是否为异常高税率
                elif latest_rate > 0.40:  # 税率高于40%
                    logger.warning(f"{symbol}: 检测到异常高税率 {latest_rate:.2%}，可能原因：")
                    logger.warning(f"  - 一次性税务调整")
                    logger.warning(f"  - 特殊税务事项")
                    
                    # 使用历史平均税率
                    if tax_rates:
                        avg_rate = sum(tax_rates) / len(tax_rates)
                        logger.info(f"{symbol}: 使用历史平均税率 = {avg_rate:.2%}")
                        return avg_rate
                
                # 正常税率范围
                if 0.05 <= latest_rate <= 0.40:
                    logger.info(f"{symbol}: 使用最新税率 = {latest_rate:.2%}")
                    return latest_rate
            
            # 3. 优先使用yfinance提供的计算税率
            if 'Tax Rate For Calcs' in latest_income.index:
                tax_rate = latest_income['Tax Rate For Calcs']
                if pd.notna(tax_rate) and 0 <= tax_rate <= 0.6:
                    logger.info(f"{symbol}: 使用yfinance计算税率 = {tax_rate:.4f}")
                    return tax_rate
            
            # 4. 使用基于国家的默认税率
            return self._get_default_tax_rate(symbol)
            
        except Exception as e:
            logger.error(f"获取 {symbol} 税率失败: {e}")
            return 0.25
    
    def _get_default_tax_rate(self, symbol: str) -> float:
        """根据公司所在国家获取默认税率"""
        try:
            ticker = yf.Ticker(symbol)
            ticker_info = ticker.info
            country = ticker_info.get('country', 'United States')
            
            default_tax_rates = {
                'United States': 0.21,
                'China': 0.25,
                'Japan': 0.23,
                'United Kingdom': 0.19,
                'Germany': 0.30,
                'France': 0.28,
                'Canada': 0.27,
                'Australia': 0.30,
                'Denmark': 0.22,  # 为NVO添加
                'Netherlands': 0.25
            }
            
            default_rate = default_tax_rates.get(country, 0.25)
            logger.info(f"{symbol}: 使用国家默认税率 ({country}): {default_rate:.2%}")
            return default_rate
            
        except Exception as e:
            logger.error(f"获取 {symbol} 国家信息失败: {e}")
            return 0.25
    
    def calculate_individual_wacc(self, symbol: str) -> Dict:
        """计算个股WACC"""
        logger.info(f"计算 {symbol} 个股WACC...")
        
        try:
            # 获取各项数据
            beta = self.get_beta(symbol)
            cost_of_equity = self.calculate_cost_of_equity(symbol, beta)
            debt_info = self.get_debt_info(symbol)
            cost_of_debt = self.calculate_cost_of_debt(symbol, debt_info)
            market_cap = self.get_market_cap(symbol)
            tax_rate = self.get_tax_rate(symbol)
            
            total_debt = debt_info.get('total_debt', 0)
            net_debt = debt_info.get('net_debt', 0)
            cash_and_equivalents = debt_info.get('cash_and_equivalents', 0)
            
            # 对于净现金公司，使用净现金而非总债务
            if net_debt <= 0:
                # 净现金公司：使用权益价值 + 净现金
                total_value = market_cap + abs(net_debt)
                equity_weight = market_cap / total_value
                debt_weight = abs(net_debt) / total_value
                # 净现金的"成本"实际上是收益，使用负值
                effective_cost_of_debt = -0.02  # 假设现金收益率2%
            else:
                # 有净债务公司：传统计算
                total_value = market_cap + total_debt
                equity_weight = market_cap / total_value
                debt_weight = total_debt / total_value
                effective_cost_of_debt = cost_of_debt
            
            if total_value <= 0:
                logger.error(f"{symbol}: 总价值为0，无法计算WACC")
                return {'error': '总价值为0'}
            
            # 计算WACC
            wacc = (equity_weight * cost_of_equity) + (debt_weight * effective_cost_of_debt * (1 - tax_rate))
            
            result = {
                'symbol': symbol,
                'wacc': wacc,
                'cost_of_equity': cost_of_equity,
                'cost_of_debt': cost_of_debt,
                'effective_cost_of_debt': effective_cost_of_debt,
                'tax_rate': tax_rate,
                'beta': beta,
                'risk_free_rate': self.risk_free_rate,
                'market_risk_premium': self.market_risk_premium,
                'market_cap': market_cap,
                'total_debt': total_debt,
                'net_debt': net_debt,
                'cash_and_equivalents': cash_and_equivalents,
                'total_value': total_value,
                'equity_weight': equity_weight,
                'debt_weight': debt_weight,
                'is_net_cash_company': net_debt <= 0,
                'calculation_date': datetime.now().isoformat()
            }
            
            logger.info(f"{symbol}: 个股WACC = {wacc:.4f} ({wacc:.2%})")
            return result
            
        except Exception as e:
            logger.error(f"计算 {symbol} 个股WACC失败: {e}")
            return {'error': str(e)}
    
    def batch_calculate_wacc(self, symbols: list) -> Dict:
        """批量计算个股WACC"""
        results = {}
        
        for symbol in symbols:
            result = self.calculate_individual_wacc(symbol)
            results[symbol] = result
        
        return results
    
    def format_wacc_comparison(self, individual_wacc: Dict, industry_wacc: float) -> str:
        """格式化WACC对比信息"""
        if 'error' in individual_wacc:
            return f"计算失败: {individual_wacc['error']}"
        
        symbol = individual_wacc['symbol']
        ind_wacc = individual_wacc['wacc']
        diff = ind_wacc - industry_wacc
        diff_pct = (diff / industry_wacc) * 100
        
        return f"""
{symbol} WACC对比:
├─ 个股WACC: {ind_wacc:.4f} ({ind_wacc:.2%})
├─ 行业WACC: {industry_wacc:.4f} ({industry_wacc:.2%})
├─ 差异: {diff:+.4f} ({diff_pct:+.1f}%)
├─ 股权成本: {individual_wacc['cost_of_equity']:.4f}
├─ 债务成本: {individual_wacc['cost_of_debt']:.4f}
├─ 权重: 股权{individual_wacc['equity_weight']:.1%} | 债务{individual_wacc['debt_weight']:.1%}
└─ Beta: {individual_wacc['beta']:.2f}
""" 