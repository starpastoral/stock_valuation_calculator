# DCF计算模块
import numpy as np
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
            shares_outstanding = stock_data['shares_outstanding']
            current_price = stock_data['current_price']
            
            # 检查数据有效性
            if latest_fcf <= 0:
                return {'error': '负自由现金流，无法估值'}
            
            if wacc <= self.perpetual_growth_rate:
                return {'error': f'折现率({wacc:.2%})必须大于永续增长率({self.perpetual_growth_rate:.2%})'}
            
            # 计算未来现金流
            future_fcf = self._project_future_fcf(latest_fcf)
            
            # 计算终值
            terminal_value = self._calculate_terminal_value(future_fcf[-1], wacc)
            
            # 计算现值 - 按照标准DCF公式
            pv_fcf = self._calculate_present_value(future_fcf, wacc)
            # 终值现值 = 终值 / (1+折现率)^10
            pv_terminal = terminal_value / ((1 + wacc) ** self.forecast_years)
            
            # 内在价值 = 未来现金流现值 + 终值现值
            enterprise_value = sum(pv_fcf) + pv_terminal
            intrinsic_value_per_share = enterprise_value / shares_outstanding
            
            # 计算IRR
            irr = self._calculate_irr(current_price, intrinsic_value_per_share)
            
            return {
                'symbol': stock_data['symbol'],
                'current_price': current_price,
                'intrinsic_value': intrinsic_value_per_share,
                'irr': irr,
                'wacc': wacc,

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
    
    def _project_future_fcf(self, latest_fcf):
        """
        预测未来现金流 - 按照标准DCF公式
        只使用永续增长率2.5%（名义GDP）预测所有未来现金流
        """
        future_fcf = []
        
        # 标准DCF：只使用永续增长率预测未来10年现金流
        for year in range(1, self.forecast_years + 1):
            if year == 1:
                fcf = latest_fcf * (1 + self.perpetual_growth_rate)
            else:
                fcf = future_fcf[-1] * (1 + self.perpetual_growth_rate)
            
            future_fcf.append(fcf)
        
        return future_fcf
    
    def _calculate_terminal_value(self, final_year_fcf, wacc):
        """
        计算终值 - 按照标准DCF公式
        终值 = FCF(第10年) × (1+永续增长率) / (折现率-永续增长率)
        永续增长率固定为2.5%（名义GDP）
        """
        terminal_fcf = final_year_fcf * (1 + self.perpetual_growth_rate)
        terminal_value = terminal_fcf / (wacc - self.perpetual_growth_rate)
        return terminal_value
    
    def _calculate_present_value(self, future_fcf, wacc):
        """
        计算现值 - 按照标准DCF公式
        未来10年现值 = Σ[FCF(年份) / (1+折现率)^年份]
        """
        pv_fcf = []
        for i, fcf in enumerate(future_fcf):
            year = i + 1
            pv = fcf / ((1 + wacc) ** year)
            pv_fcf.append(pv)
        return pv_fcf
    
    def _calculate_irr(self, current_price, intrinsic_value_per_share):
        """
        计算IRR - 使用Total Return方法
        
        改进说明：
        - 不再假设投资者每年收到全部自由现金流
        - 基于DCF计算的内在价值，计算买入持有到期的年化收益率
        - 更符合实际投资场景：买入股票后在未来某个时点卖出
        
        Args:
            current_price: 当前股价
            intrinsic_value_per_share: 每股内在价值
        """
        try:
            # Total Return IRR计算
            # IRR = (内在价值 / 当前价格)^(1/年数) - 1
            if current_price <= 0 or intrinsic_value_per_share <= 0:
                logger.warning("股价或内在价值为负，无法计算IRR")
                return None
            
            irr = (intrinsic_value_per_share / current_price) ** (1/self.forecast_years) - 1
            
            # 合理性检查 - 年化收益率在-50%到50%之间
            if irr < -0.5 or irr > 0.5:
                logger.warning(f"IRR异常: {irr:.2%}，当前价格: {current_price:.2f}，内在价值: {intrinsic_value_per_share:.2f}")
                return None
            
            logger.info(f"IRR计算: 内在价值 {intrinsic_value_per_share:.2f} / 当前价格 {current_price:.2f} = {irr:.2%}")
            return irr
                
        except Exception as e:
            logger.error(f"IRR计算失败: {e}")
            return None
    
    def evaluate_valuation(self, dcf_result):
        """
        根据IRR和内在价值倍数综合评估估值
        
        Args:
            dcf_result: DCF计算结果
            
        Returns:
            str: 评估结果（严重高估/高估/合理/低估/严重低估）
        """
        if 'error' in dcf_result:
            return '无法评估'
        
        irr = dcf_result.get('irr')
        if irr is None:
            return '无法计算IRR'
        
        # 计算内在价值倍数
        current_price = dcf_result.get('current_price')
        intrinsic_value = dcf_result.get('intrinsic_value')
        
        if current_price <= 0 or intrinsic_value <= 0:
            return '数据异常'
        
        value_ratio = intrinsic_value / current_price
        
        # 基于配置的阈值评估
        from config import VALUATION_THRESHOLDS, VALUE_RATIO_THRESHOLDS
        
        # 优先基于内在价值倍数评估（更直观）
        if value_ratio >= VALUE_RATIO_THRESHOLDS['严重低估']:
            return '严重低估'
        elif value_ratio >= VALUE_RATIO_THRESHOLDS['低估']:
            return '低估'
        elif value_ratio <= VALUE_RATIO_THRESHOLDS['严重高估']:
            return '严重高估'
        elif value_ratio <= VALUE_RATIO_THRESHOLDS['高估']:
            return '高估'
        else:
            # 在合理区间内，进一步基于IRR评估
            if irr < VALUATION_THRESHOLDS['高估']:
                return '高估'
            elif irr < VALUATION_THRESHOLDS['低估']:
                return '合理'
            else:
                return '低估'
    
    def create_sensitivity_analysis(self, stock_data, base_wacc, wacc_range=0.02, perpetual_growth_range=0.005):
        """
        创建敏感性分析 - 仅对WACC和永续增长率进行敏感性分析
        
        Args:
            stock_data: 股票数据
            base_wacc: 基准折现率
            wacc_range: WACC变化范围 (±2%)
            perpetual_growth_range: 永续增长率变化范围 (±0.5%)
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
        
        # 永续增长率敏感性分析
        perpetual_growth_scenarios = [
            self.perpetual_growth_rate - perpetual_growth_range,
            self.perpetual_growth_rate,
            self.perpetual_growth_rate + perpetual_growth_range
        ]
        
        for wacc in wacc_scenarios:
            for perp_growth in perpetual_growth_scenarios:
                # 临时修改永续增长率
                original_growth = self.perpetual_growth_rate
                self.perpetual_growth_rate = perp_growth
                
                # 计算DCF
                result = self.calculate_dcf_valuation(stock_data, wacc)
                
                # 恢复原始永续增长率
                self.perpetual_growth_rate = original_growth
                
                if 'error' not in result:
                    key = f"WACC_{wacc:.1%}_PerpGrowth_{perp_growth:.1%}"
                    sensitivity_data[key] = {
                        'intrinsic_value': result['intrinsic_value'],
                        'wacc': wacc,
                        'perpetual_growth_rate': perp_growth
                    }
        
        return sensitivity_data 