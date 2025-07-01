#!/usr/bin/env python3
"""
货币转换模块
根据股票的交易所和报价货币，将财务数据转换为正确的计价单位
"""

import requests
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import yfinance as yf

logger = logging.getLogger(__name__)

class CurrencyConverter:
    """智能货币转换器"""
    
    def __init__(self, cache_file="data/cache/exchange_rates.json"):
        """
        初始化货币转换器
        
        Args:
            cache_file: 汇率缓存文件路径
        """
        self.cache_file = cache_file
        self.cache_duration = 3600  # 缓存1小时
        self.exchange_rates = {}
        self.last_updated = None
        
        # 确保缓存目录存在
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        
        # 加载缓存的汇率数据
        self._load_cached_rates()
        
        # 交易所与货币的映射关系
        self.exchange_currency_map = {
            # 美国交易所
            'NASDAQ': 'USD',
            'NYSE': 'USD', 
            'AMEX': 'USD',
            'BATS': 'USD',
            
            # 日本交易所
            'JPX': 'JPY',
            'TSE': 'JPY',
            'OSE': 'JPY',
            
            # 香港交易所
            'HKEX': 'HKD',
            'HKG': 'HKD',
            
            # 欧洲交易所
            'LSE': 'GBP',        # 伦敦证券交易所
            'FRA': 'EUR',        # 法兰克福
            'AMS': 'EUR',        # 阿姆斯特丹
            'EPA': 'EUR',        # 巴黎
            'BIT': 'EUR',        # 米兰
            
            # 加拿大
            'TSX': 'CAD',
            'CVE': 'CAD',
            
            # 澳大利亚
            'ASX': 'AUD',
            
            # 韩国
            'KRX': 'KRW',
            'KOE': 'KRW',
            
            # 中国大陆
            'SHE': 'CNY',        # 深圳
            'SHG': 'CNY',        # 上海
        }
        
        # 免费汇率API配置
        self.rate_apis = [
            {
                'name': 'exchangerate-api',
                'url': 'https://api.exchangerate-api.com/v4/latest/{base}',
                'free': True
            }
        ]
    
    def _load_cached_rates(self):
        """加载缓存的汇率数据"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.exchange_rates = cache_data.get('rates', {})
                    self.last_updated = datetime.fromisoformat(cache_data.get('last_updated', '2000-01-01'))
                    logger.info(f"加载缓存汇率数据: {len(self.exchange_rates)} 个汇率对")
        except Exception as e:
            logger.warning(f"加载汇率缓存失败: {e}")
            self.exchange_rates = {}
            self.last_updated = None
    
    def _save_cached_rates(self):
        """保存汇率数据到缓存"""
        try:
            cache_data = {
                'rates': self.exchange_rates,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info(f"保存汇率缓存: {len(self.exchange_rates)} 个汇率对")
        except Exception as e:
            logger.error(f"保存汇率缓存失败: {e}")
    
    def _fetch_exchange_rates(self, base_currency: str) -> bool:
        """
        从API获取实时汇率
        
        Args:
            base_currency: 基准货币
            
        Returns:
            bool: 是否成功获取汇率
        """
        for api_config in self.rate_apis:
            try:
                url = api_config['url'].format(base=base_currency)
                logger.info(f"获取 {base_currency} 汇率: {api_config['name']}")
                
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # 处理不同API的响应格式
                if 'rates' in data:
                    rates = data['rates']
                elif 'conversion_rates' in data:
                    rates = data['conversion_rates']
                else:
                    logger.warning(f"未识别的API响应格式: {api_config['name']}")
                    continue
                
                # 更新汇率缓存
                for target_currency, rate in rates.items():
                    key = f"{base_currency}_{target_currency}"
                    self.exchange_rates[key] = rate
                
                # 添加反向汇率
                for target_currency, rate in rates.items():
                    if rate != 0:
                        reverse_key = f"{target_currency}_{base_currency}"
                        self.exchange_rates[reverse_key] = 1.0 / rate
                
                self.last_updated = datetime.now()
                self._save_cached_rates()
                
                logger.info(f"成功获取 {base_currency} 汇率: {len(rates)} 个货币对")
                return True
                
            except Exception as e:
                logger.warning(f"API {api_config['name']} 获取汇率失败: {e}")
                continue
        
        return False
    
    def _needs_rate_update(self) -> bool:
        """检查是否需要更新汇率"""
        if self.last_updated is None:
            return True
        
        time_since_update = datetime.now() - self.last_updated
        return time_since_update.total_seconds() > self.cache_duration
    
    def get_stock_currencies(self, symbol: str) -> Tuple[str, str]:
        """
        获取股票的报价货币和财务数据货币
        
        Args:
            symbol: 股票代码
            
        Returns:
            Tuple[报价货币, 财务数据货币]
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # 获取报价货币
            quote_currency = info.get('currency', 'USD')
            
            # 获取财务数据货币
            financial_currency = info.get('financialCurrency', quote_currency)
            
            # 根据交易所推断货币（作为备用）
            exchange = info.get('exchange', '')
            if exchange in self.exchange_currency_map:
                expected_currency = self.exchange_currency_map[exchange]
                if quote_currency == 'USD' and expected_currency != 'USD':
                    # 可能是ADR或其他跨境上市
                    logger.info(f"{symbol}: 检测到跨境上市，交易所={exchange}, 报价货币={quote_currency}")
            
            logger.info(f"{symbol}: 报价货币={quote_currency}, 财务货币={financial_currency}, 交易所={exchange}")
            
            return quote_currency, financial_currency
            
        except Exception as e:
            logger.error(f"获取 {symbol} 货币信息失败: {e}")
            return 'USD', 'USD'
    
    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """
        获取汇率
        
        Args:
            from_currency: 源货币
            to_currency: 目标货币
            
        Returns:
            float: 汇率，如果获取失败返回None
        """
        # 同种货币
        if from_currency == to_currency:
            return 1.0
        
        # 检查缓存
        key = f"{from_currency}_{to_currency}"
        if key in self.exchange_rates and not self._needs_rate_update():
            return self.exchange_rates[key]
        
        # 需要更新汇率
        if self._needs_rate_update():
            # 尝试获取主要货币的汇率
            major_currencies = ['USD', 'EUR', 'CNY', 'JPY', 'GBP', 'HKD', 'CAD', 'AUD', 'KRW', 'TWD']
            for base in major_currencies:
                if from_currency == base or to_currency == base:
                    if self._fetch_exchange_rates(base):
                        break
            else:
                # 如果不是主要货币，尝试以USD为基准
                self._fetch_exchange_rates('USD')
        
        # 再次检查缓存
        if key in self.exchange_rates:
            return self.exchange_rates[key]
        
        logger.error(f"无法获取汇率: {from_currency} -> {to_currency}")
        return None
    
    def convert_financial_data(self, symbol: str, value: float) -> Tuple[float, str, str, float]:
        """
        转换财务数据到正确的计价货币
        
        Args:
            symbol: 股票代码
            value: 原始财务数据值
            
        Returns:
            Tuple[转换后的值, 目标货币, 源货币, 汇率]
        """
        try:
            quote_currency, financial_currency = self.get_stock_currencies(symbol)
            
            # 如果财务数据已经是报价货币，无需转换
            if financial_currency == quote_currency:
                return value, quote_currency, financial_currency, 1.0
            
            # 获取汇率
            exchange_rate = self.get_exchange_rate(financial_currency, quote_currency)
            
            if exchange_rate is None:
                logger.warning(f"{symbol}: 无法获取汇率 {financial_currency}->{quote_currency}，使用原始值")
                return value, financial_currency, financial_currency, 1.0
            
            converted_value = value * exchange_rate
            
            logger.info(f"{symbol}: 货币转换 {financial_currency}->{quote_currency}, "
                       f"汇率={exchange_rate:.4f}, 原值={value:,.0f}, 转换后={converted_value:,.0f}")
            
            return converted_value, quote_currency, financial_currency, exchange_rate
            
        except Exception as e:
            logger.error(f"财务数据货币转换失败 {symbol}: {e}")
            return value, 'USD', 'USD', 1.0
    
    def get_currency_info(self, symbol: str) -> Dict:
        """
        获取股票的完整货币信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 货币信息字典
        """
        quote_currency, financial_currency = self.get_stock_currencies(symbol)
        exchange_rate = 1.0
        
        if financial_currency != quote_currency:
            exchange_rate = self.get_exchange_rate(financial_currency, quote_currency) or 1.0
        
        return {
            'quote_currency': quote_currency,
            'financial_currency': financial_currency,
            'exchange_rate': exchange_rate,
            'conversion_needed': financial_currency != quote_currency,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        } 