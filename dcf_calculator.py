# DCF计算模块
import numpy as np
from scipy.optimize import fsolve
import logging
from config import PERPETUAL_GROWTH_RATE, FORECAST_YEARS, DEFAULT_WACC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DCFCalculator:
    """DCF估值计算器"""
    
    def __init__(self):
        self.perpetual_growth_rate = PERPETUAL_GROWTH_RATE
        self.forecast_years = FORECAST_YEARS
        self.default_wacc = DEFAULT_WACC
    
    def calculate_dcf_valuation(self, stock_data, wacc):
        """
        计算DCF估值
        
        Args:
            stock_data: 股票数据字典
            wacc: 折现率
            
        Returns:
            dict: DCF计算结果
        """
        try:
            if 'error' in stock_data:
                return {'error': stock_data['error']}
            
            # 获取基础数据
            latest_fcf = stock_data['latest_fcf']
            growth_rate = stock_data['growth_rate']
            shares_outstanding = stock_data['shares_outstanding']
            current_price = stock_data['current_price']
            
            # 检查数据有效性
            if latest_fcf <= 0:
                return {'error': '负自由现金流，无法估值'}
            
            if wacc <= self.perpetual_growth_rate:
                return {'error': f'折现率({wacc:.2%})必须大于永续增长率({self.perpetual_growth_rate:.2%})'}
            
            # 计算未来现金流
            future_fcf = self._project_future_fcf(latest_fcf, growth_rate)
            
            # 计算终值
            terminal_value = self._calculate_terminal_value(future_fcf[-1], wacc)
            
            # 计算现值
            pv_fcf = self._calculate_present_value(future_fcf, wacc)
            pv_terminal = terminal_value / ((1 + wacc) ** self.forecast_years)
            
            # 计算企业价值和每股价值
            enterprise_value = sum(pv_fcf) + pv_terminal
            intrinsic_value_per_share = enterprise_value / shares_outstanding
            
            # 计算IRR
            irr = self._calculate_irr(current_price, future_fcf, terminal_value, shares_outstanding)
            
            return {
                'symbol': stock_data['symbol'],
                'current_price': current_price,
                'intrinsic_value': intrinsic_value_per_share,
                'upside_downside': (intrinsic_value_per_share - current_price) / current_price,
                'irr': irr,
                'wacc': wacc,
                'growth_rate': growth_rate,
                'latest_fcf': latest_fcf,
                'enterprise_value': enterprise_value,
                'terminal_value': terminal_value,
                'pv_terminal': pv_terminal,
                'future_fcf': future_fcf,
                'pv_fcf': pv_fcf,
                'shares_outstanding': shares_outstanding,
                'forecast_years': self.forecast_years,
                'perpetual_growth_rate': self.perpetual_growth_rate
            }
            
        except Exception as e:
            logger.error(f"DCF计算失败: {e}")
            return {'error': f'DCF计算失败: {str(e)}'}
    
    def _project_future_fcf(self, latest_fcf, growth_rate):
        """预测未来现金流"""
        future_fcf = []
        
        for year in range(1, self.forecast_years + 1):
            # 简单的线性递减增长率模型
            # 从初始增长率递减到永续增长率
            if year <= 5:
                # 前5年使用历史增长率
                year_growth_rate = growth_rate
            else:
                # 后5年线性递减到永续增长率
                decline_factor = (year - 5) / 5  # 0 to 1
                year_growth_rate = growth_rate * (1 - decline_factor) + self.perpetual_growth_rate * decline_factor
            
            if year == 1:
                fcf = latest_fcf * (1 + year_growth_rate)
            else:
                fcf = future_fcf[-1] * (1 + year_growth_rate)
            
            future_fcf.append(fcf)
        
        return future_fcf
    
    def _calculate_terminal_value(self, final_year_fcf, wacc):
        """计算终值"""
        terminal_fcf = final_year_fcf * (1 + self.perpetual_growth_rate)
        terminal_value = terminal_fcf / (wacc - self.perpetual_growth_rate)
        return terminal_value
    
    def _calculate_present_value(self, future_fcf, wacc):
        """计算现值"""
        pv_fcf = []
        for i, fcf in enumerate(future_fcf):
            pv = fcf / ((1 + wacc) ** (i + 1))
            pv_fcf.append(pv)
        return pv_fcf
    
    def _calculate_irr(self, current_price, future_fcf, terminal_value, shares_outstanding):
        """计算IRR"""
        try:
            # 计算每股现金流
            fcf_per_share = [fcf / shares_outstanding for fcf in future_fcf]
            terminal_value_per_share = terminal_value / shares_outstanding
            
            # 创建现金流序列 (初始投资为负，未来现金流为正)
            cash_flows = [-current_price]  # 初始投资
            cash_flows.extend(fcf_per_share[:-1])  # 前9年现金流
            cash_flows.append(fcf_per_share[-1] + terminal_value_per_share)  # 第10年现金流+终值
            
            # 定义NPV函数
            def npv(rate):
                return sum([cf / (1 + rate) ** i for i, cf in enumerate(cash_flows)])
            
            # 使用数值方法求解IRR
            # 初始猜测值为10%
            try:
                irr = fsolve(npv, 0.1)[0]
                # 验证结果是否合理
                if irr < -0.9 or irr > 5.0:  # IRR在-90%到500%之间
                    return None
                return irr
            except:
                return None
                
        except Exception as e:
            logger.error(f"IRR计算失败: {e}")
            return None
    
    def evaluate_valuation(self, dcf_result):
        """
        根据IRR评估估值
        
        Args:
            dcf_result: DCF计算结果
            
        Returns:
            str: 评估结果（高估/合理/低估）
        """
        if 'error' in dcf_result:
            return '无法评估'
        
        irr = dcf_result.get('irr')
        if irr is None:
            return '无法计算IRR'
        
        # 基于配置的阈值评估
        from config import VALUATION_THRESHOLDS
        
        if irr < VALUATION_THRESHOLDS['高估']:
            return '高估'
        elif irr < VALUATION_THRESHOLDS['合理']:
            return '合理'
        else:
            return '低估'
    
    def create_sensitivity_analysis(self, stock_data, base_wacc, wacc_range=0.02, growth_range=0.05):
        """
        创建敏感性分析
        
        Args:
            stock_data: 股票数据
            base_wacc: 基准折现率
            wacc_range: WACC变化范围 (±2%)
            growth_range: 增长率变化范围 (±5%)
        """
        if 'error' in stock_data:
            return None
        
        sensitivity_data = {}
        
        # WACC敏感性分析
        wacc_scenarios = [
            base_wacc - wacc_range,
            base_wacc,
            base_wacc + wacc_range
        ]
        
        # 增长率敏感性分析
        base_growth = stock_data['growth_rate']
        growth_scenarios = [
            base_growth - growth_range,
            base_growth,
            base_growth + growth_range
        ]
        
        for wacc in wacc_scenarios:
            for growth in growth_scenarios:
                # 创建修改后的股票数据
                modified_data = stock_data.copy()
                modified_data['growth_rate'] = growth
                
                # 计算DCF
                result = self.calculate_dcf_valuation(modified_data, wacc)
                
                if 'error' not in result:
                    key = f"WACC_{wacc:.1%}_Growth_{growth:.1%}"
                    sensitivity_data[key] = {
                        'intrinsic_value': result['intrinsic_value'],
                        'upside_downside': result['upside_downside'],
                        'wacc': wacc,
                        'growth_rate': growth
                    }
        
        return sensitivity_data 