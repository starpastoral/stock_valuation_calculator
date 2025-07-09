#!/usr/bin/env python3
"""
货币格式化工具
提供统一的货币显示格式，使用明确的货币单位而非符号
"""

def format_currency(value, currency_code='USD', precision=2):
    """
    格式化货币显示
    
    Args:
        value: 数值
        currency_code: 货币代码（如USD、CNY、EUR等）
        precision: 小数位数
    
    Returns:
        str: 格式化后的货币字符串
    """
    if precision == 0:
        return f"{value:,.0f} {currency_code}"
    else:
        return f"{value:,.{precision}f} {currency_code}"

def get_currency_from_result(result):
    """
    从估值结果中获取货币信息
    
    Args:
        result: 估值结果字典
    
    Returns:
        str: 货币代码
    """
    # 优先使用target_currency
    currency = result.get('target_currency', 'USD')
    
    # 如果没有target_currency，尝试其他字段
    if not currency or currency == 'USD':
        currency = result.get('currency', 'USD')
    
    return currency

def format_price(value, result=None, currency_code=None):
    """
    格式化价格显示
    
    Args:
        value: 价格值
        result: 估值结果字典（可选）
        currency_code: 明确的货币代码（可选）
    
    Returns:
        str: 格式化后的价格字符串
    """
    if currency_code:
        currency = currency_code
    elif result:
        currency = get_currency_from_result(result)
    else:
        currency = 'USD'
    
    return format_currency(value, currency, 2)

def format_large_number(value, result=None, currency_code=None):
    """
    格式化大数字（如现金流、企业价值等）
    
    Args:
        value: 数值
        result: 估值结果字典（可选）
        currency_code: 明确的货币代码（可选）
    
    Returns:
        str: 格式化后的数字字符串
    """
    if currency_code:
        currency = currency_code
    elif result:
        currency = get_currency_from_result(result)
    else:
        currency = 'USD'
    
    return format_currency(value, currency, 0)

def format_percentage(value, precision=1):
    """
    格式化百分比显示
    
    Args:
        value: 百分比值（如0.05表示5%）
        precision: 小数位数
    
    Returns:
        str: 格式化后的百分比字符串
    """
    return f"{value*100:+.{precision}f}%" 