# DCF计算模块 - 增强版核心
import yfinance as yf
import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from scipy.optimize import brentq
from dataclasses import dataclass
from config import PERPETUAL_GROWTH_RATE, FORECAST_YEARS, DEFAULT_WACC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GrowthScenario:
    """增长率场景数据类"""
    name: str
    years_1_3: float
    years_4_7: float
    years_8_12: float
    terminal: float
    description: str

@dataclass
class StageInfo:
    """公司发展阶段信息"""
    stage: str
    confidence: float
    metrics: Dict
    key_drivers: List[str]

class CompanyStageIdentifier:
    """公司发展阶段识别器"""
    
    def __init__(self):
        self.stage_thresholds = {
            'high_growth': {'revenue_growth': 0.15, 'size_factor': 0.3},
            'moderate_growth': {'revenue_growth': 0.08, 'size_factor': 0.5},
            'mature': {'revenue_growth': 0.05, 'size_factor': 0.7},
            'decline': {'revenue_growth': 0.0, 'size_factor': 1.0}
        }
    
    def identify_stage(self, symbol: str, financial_data: Dict) -> StageInfo:
        """识别公司发展阶段"""
        try:
            # 分析营收增长率
            revenue_growth = self._analyze_revenue_growth(symbol)
            
            # 分析规模因子
            size_factor = self._calculate_size_factor(financial_data.get('market_cap', 0))
            
            # 分析盈利稳定性
            profitability_stability = self._analyze_profitability_stability(symbol)
            
            # 分析现金流质量
            cash_flow_quality = self._analyze_cash_flow_quality(financial_data)
            
            # 综合评分
            stage_score = self._calculate_stage_score(
                revenue_growth, size_factor, profitability_stability, cash_flow_quality
            )
            
            # 确定阶段
            stage = self._determine_stage(stage_score)
            
            # 将实际计算的历史增长率传递给financial_data
            financial_data['historical_growth'] = revenue_growth
            
            return StageInfo(
                stage=stage,
                confidence=stage_score.get('confidence', 0.5),
                metrics={
                    'revenue_growth': revenue_growth,
                    'size_factor': size_factor,
                    'profitability_stability': profitability_stability,
                    'cash_flow_quality': cash_flow_quality
                },
                key_drivers=self._identify_key_drivers(stage, stage_score)
            )
            
        except Exception as e:
            logger.error(f"识别公司发展阶段失败 {symbol}: {e}")
            return StageInfo(
                stage='mature',
                confidence=0.3,
                metrics={},
                key_drivers=['数据不足']
            )
    
    def _analyze_revenue_growth(self, symbol: str) -> float:
        """分析营收增长率"""
        try:
            ticker = yf.Ticker(symbol)
            financials = ticker.financials
            
            if financials.empty:
                return 0.05  # 默认5%
            
            # 获取总营收
            revenue_row = None
            for idx in financials.index:
                if 'total revenue' in str(idx).lower() or 'revenue' in str(idx).lower():
                    revenue_row = financials.loc[idx]
                    break
            
            if revenue_row is None:
                return 0.05
            
            # 计算过去3年平均增长率
            revenue_values = revenue_row.dropna().sort_index()
            
            if len(revenue_values) < 2:
                return 0.05
            
            growth_rates = []
            for i in range(1, len(revenue_values)):
                if revenue_values.iloc[i-1] > 0:
                    growth_rate = (revenue_values.iloc[i] - revenue_values.iloc[i-1]) / revenue_values.iloc[i-1]
                    growth_rates.append(growth_rate)
            
            if not growth_rates:
                return 0.05
            
            avg_growth = float(np.mean(growth_rates))  # 转换为float
            # 对于极端增长率，给予更宽松的限制
            return max(min(avg_growth, 2.0), -0.5)  # 限制在-50%到200%之间
            
        except Exception as e:
            logger.error(f"分析营收增长率失败 {symbol}: {e}")
            return 0.05
    
    def _calculate_size_factor(self, market_cap: float) -> float:
        """计算规模因子 (0-1, 数值越大公司规模越大)"""
        if market_cap <= 0:
            return 0.3
        
        # 使用对数函数，避免极大值
        log_cap = np.log10(market_cap)
        
        # 市值分级
        if log_cap < 9:  # < 10亿
            return 0.1
        elif log_cap < 10:  # 10-100亿
            return 0.3
        elif log_cap < 11:  # 100-1000亿
            return 0.6
        elif log_cap < 12:  # 1000-10000亿
            return 0.8
        else:  # > 1万亿
            return 1.0
    
    def _analyze_profitability_stability(self, symbol: str) -> float:
        """分析盈利稳定性"""
        try:
            ticker = yf.Ticker(symbol)
            financials = ticker.financials
            
            if financials.empty:
                return 0.5
            
            # 获取净利润
            net_income_row = None
            for idx in financials.index:
                if 'net income' in str(idx).lower():
                    net_income_row = financials.loc[idx]
                    break
            
            if net_income_row is None:
                return 0.5
            
            net_income_values = net_income_row.dropna().sort_index()
            
            if len(net_income_values) < 3:
                return 0.5
            
            # 计算盈利稳定性（变异系数的倒数）
            if np.mean(net_income_values) != 0:
                cv = np.std(net_income_values) / abs(np.mean(net_income_values))
                stability = 1 / (1 + cv)  # 变异系数越小，稳定性越高
            else:
                stability = 0.3
            
            return max(min(stability, 1.0), 0.0)
            
        except Exception as e:
            logger.error(f"分析盈利稳定性失败 {symbol}: {e}")
            return 0.5
    
    def _analyze_cash_flow_quality(self, financial_data: Dict) -> float:
        """分析现金流质量"""
        try:
            latest_fcf = financial_data.get('latest_fcf', 0)
            
            if latest_fcf <= 0:
                return 0.2
            elif latest_fcf < 1e9:  # < 10亿
                return 0.4
            elif latest_fcf < 5e9:  # 10-50亿
                return 0.6
            elif latest_fcf < 20e9:  # 50-200亿
                return 0.8
            else:  # > 200亿
                return 1.0
                
        except Exception as e:
            logger.error(f"分析现金流质量失败: {e}")
            return 0.5
    
    def _calculate_stage_score(self, revenue_growth: float, size_factor: float, 
                             profitability_stability: float, cash_flow_quality: float) -> Dict:
        """计算阶段评分"""
        
        # 权重分配 - 提高营收增长率权重，降低规模因子权重
        weights = {
            'revenue_growth': 0.6,  # 增加营收增长率权重
            'size_factor': 0.1,     # 降低规模因子权重  
            'profitability_stability': 0.2,
            'cash_flow_quality': 0.1
        }
        
        # 标准化评分 - 调整增长率评分标准
        normalized_scores = {
            # 更激进的增长率评分：15%为基准，60%+为满分
            'revenue_growth': min(max(revenue_growth / 0.15, 0), 4) / 4,  
            # 对于超大市值公司，如果增长率足够高，仍可认为是高成长
            'size_factor': max(0.3, 1 - size_factor) if revenue_growth > 0.3 else 1 - size_factor,
            'profitability_stability': profitability_stability,
            'cash_flow_quality': cash_flow_quality
        }
        
        # 计算加权评分
        total_score = sum(normalized_scores[key] * weights[key] for key in weights)
        
        # 计算置信度
        confidence = min(sum(1 if score > 0.3 else 0 for score in normalized_scores.values()) / 4, 1.0)
        
        return {
            'total_score': total_score,
            'confidence': confidence,
            'individual_scores': normalized_scores,
            'weights': weights
        }
    
    def _determine_stage(self, stage_score: Dict) -> str:
        """确定发展阶段"""
        score = stage_score['total_score']
        individual_scores = stage_score.get('individual_scores', {})
        
        # 特殊规则：如果营收增长率评分很高，即使总分不够也可能是高成长
        revenue_score = individual_scores.get('revenue_growth', 0)
        
        if score >= 0.7 or (revenue_score >= 0.8 and score >= 0.5):
            return 'high_growth'
        elif score >= 0.5:
            return 'moderate_growth'
        elif score >= 0.3:
            return 'mature'
        else:
            return 'decline'
    
    def _identify_key_drivers(self, stage: str, stage_score: Dict) -> List[str]:
        """识别关键驱动因素"""
        drivers = []
        scores = stage_score.get('individual_scores', {})
        
        if scores.get('revenue_growth', 0) > 0.6:
            drivers.append('强劲营收增长')
        if scores.get('size_factor', 0) > 0.6:
            drivers.append('较小规模优势')
        if scores.get('profitability_stability', 0) > 0.6:
            drivers.append('盈利稳定性')
        if scores.get('cash_flow_quality', 0) > 0.6:
            drivers.append('现金流质量')
        
        if not drivers:
            drivers.append('基础面表现一般')
        
        return drivers

class DynamicGrowthCalculator:
    """动态增长率计算器"""
    
    def __init__(self):
        self.perpetual_growth_rate = 0.025  # 永续增长率2.5%
    
    def calculate_growth_scenarios(self, symbol: str, stage_info: StageInfo, 
                                 financial_data: Dict) -> Dict[str, GrowthScenario]:
        """计算多场景增长率"""
        
        stage = stage_info.stage
        
        if stage == 'high_growth':
            return self._calculate_high_growth_scenarios(symbol, financial_data)
        elif stage == 'moderate_growth':
            return self._calculate_moderate_growth_scenarios(symbol, financial_data)
        elif stage == 'mature':
            return self._calculate_mature_scenarios(symbol, financial_data)
        else:
            return self._calculate_decline_scenarios(symbol, financial_data)
    
    def _calculate_high_growth_scenarios(self, symbol: str, financial_data: Dict) -> Dict[str, GrowthScenario]:
        """计算高成长公司的增长率场景"""
        
        # 获取分析师预期（仅作为参考，不直接使用）
        analyst_forecast = self._get_analyst_forecast(symbol)
        
        # 获取历史增长率，但设置合理上限
        raw_historical_growth = financial_data.get('historical_growth', 0.15)
        
        # 🔧 关键改进：基于历史增长率的合理性判断，而不是直接限制
        # 分析师预期可以帮助我们理解增长的可持续性，但不直接作为模型参数
        
        # 如果历史增长率过高，采用更保守的衰减系数
        if raw_historical_growth > 0.8:  # 80%以上
            # 超高增长，快速衰减
            base_growth = min(raw_historical_growth * 0.2, 0.25)  # 更激进的衰减
            print(f"⚠️ 超高历史增长率 {raw_historical_growth:.1%}，采用激进衰减至 {base_growth:.1%}")
        elif raw_historical_growth > 0.5:  # 50%-80%
            # 高增长，中等衰减
            base_growth = min(raw_historical_growth * 0.5, 0.25)  # 稍微保守一些
            print(f"📊 高历史增长率 {raw_historical_growth:.1%}，采用中等衰减至 {base_growth:.1%}")
        else:
            # 正常增长率
            base_growth = raw_historical_growth
            print(f"✅ 正常历史增长率 {raw_historical_growth:.1%}")
        
        # 行业增长率
        industry_growth = 0.08  # 默认8%
        
        # 📈 计算各场景，基于调整后的历史增长率
        scenarios = {
            'conservative': GrowthScenario(
                name='保守场景',
                years_1_3=min(base_growth * 0.8, 0.15),  # 最高15%
                years_4_7=min(base_growth * 0.5, 0.12),  # 最高12%
                years_8_12=min(max(base_growth * 0.3, industry_growth), 0.08),  # 最高8%
                terminal=self.perpetual_growth_rate,
                description='保守预期，考虑竞争加剧和增长放缓'
            ),
            'base': GrowthScenario(
                name='基准场景',
                years_1_3=min(base_growth, 0.20),  # 最高20%
                years_4_7=min(base_growth * 0.7, 0.15),  # 最高15%
                years_8_12=min(max(base_growth * 0.4, industry_growth), 0.10),  # 最高10%
                terminal=self.perpetual_growth_rate,
                description='基于当前趋势的合理预期'
            ),
            'optimistic': GrowthScenario(
                name='乐观场景',
                years_1_3=min(base_growth * 1.2, 0.25),  # 最高25%
                years_4_7=min(base_growth * 0.8, 0.18),  # 最高18%
                years_8_12=min(max(base_growth * 0.5, industry_growth), 0.12),  # 最高12%
                terminal=min(self.perpetual_growth_rate * 1.2, 0.03),
                description='乐观预期，假设公司持续领先'
            )
        }
        
        # 🔍 输出分析师预期对比（仅供参考）
        print(f"📊 分析师预期: {analyst_forecast:.1%} (仅作参考，不直接使用)")
        
        return scenarios
    
    def _calculate_moderate_growth_scenarios(self, symbol: str, financial_data: Dict) -> Dict[str, GrowthScenario]:
        """温和成长公司的增长率场景"""
        
        analyst_forecast = self._get_analyst_forecast(symbol)
        historical_growth = financial_data.get('historical_growth', 0.10)
        
        scenarios = {
            'conservative': GrowthScenario(
                name='保守场景',
                years_1_3=min(analyst_forecast * 0.8, 0.10),
                years_4_7=max(historical_growth * 0.7, 0.05),
                years_8_12=0.04,
                terminal=self.perpetual_growth_rate,
                description='保守预期，增长逐步放缓'
            ),
            'base': GrowthScenario(
                name='基准场景',
                years_1_3=min(analyst_forecast, 0.15),
                years_4_7=max(historical_growth * 0.9, 0.08),
                years_8_12=0.05,
                terminal=self.perpetual_growth_rate,
                description='稳健增长预期'
            ),
            'optimistic': GrowthScenario(
                name='乐观场景',
                years_1_3=min(analyst_forecast * 1.1, 0.20),
                years_4_7=historical_growth,
                years_8_12=0.06,
                terminal=self.perpetual_growth_rate,
                description='乐观预期，保持稳定增长'
            )
        }
        
        return scenarios
    
    def _calculate_mature_scenarios(self, symbol: str, financial_data: Dict) -> Dict[str, GrowthScenario]:
        """成熟公司的增长率场景"""
        
        analyst_forecast = self._get_analyst_forecast(symbol)
        historical_growth = financial_data.get('historical_growth', 0.05)
        
        scenarios = {
            'conservative': GrowthScenario(
                name='保守场景',
                years_1_3=min(analyst_forecast * 0.8, 0.05),
                years_4_7=0.03,
                years_8_12=self.perpetual_growth_rate,
                terminal=self.perpetual_growth_rate,
                description='保守预期，增长与经济同步'
            ),
            'base': GrowthScenario(
                name='基准场景',
                years_1_3=min(analyst_forecast, 0.08),
                years_4_7=0.04,
                years_8_12=self.perpetual_growth_rate,
                terminal=self.perpetual_growth_rate,
                description='成熟期标准增长'
            ),
            'optimistic': GrowthScenario(
                name='乐观场景',
                years_1_3=min(analyst_forecast * 1.1, 0.10),
                years_4_7=0.05,
                years_8_12=0.03,
                terminal=self.perpetual_growth_rate,
                description='乐观预期，轻微超越市场'
            )
        }
        
        return scenarios
    
    def _calculate_decline_scenarios(self, symbol: str, financial_data: Dict) -> Dict[str, GrowthScenario]:
        """衰退期公司的增长率场景"""
        
        scenarios = {
            'conservative': GrowthScenario(
                name='保守场景',
                years_1_3=0.01,
                years_4_7=0.02,
                years_8_12=self.perpetual_growth_rate,
                terminal=self.perpetual_growth_rate,
                description='保守预期，缓慢恢复'
            ),
            'base': GrowthScenario(
                name='基准场景',
                years_1_3=0.02,
                years_4_7=0.025,
                years_8_12=self.perpetual_growth_rate,
                terminal=self.perpetual_growth_rate,
                description='基准预期，逐步稳定'
            ),
            'optimistic': GrowthScenario(
                name='乐观场景',
                years_1_3=0.04,
                years_4_7=0.03,
                years_8_12=self.perpetual_growth_rate,
                terminal=self.perpetual_growth_rate,
                description='乐观预期，成功转型'
            )
        }
        
        return scenarios
    
    def _get_analyst_forecast(self, symbol: str) -> float:
        """获取分析师预期增长率"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # 尝试获取分析师预期
            earnings_growth = info.get('earningsGrowth')
            revenue_growth = info.get('revenueGrowth')
            
            if earnings_growth is not None and earnings_growth > 0:
                return min(earnings_growth, 1.0)  # 最高100%
            elif revenue_growth is not None and revenue_growth > 0:
                return min(revenue_growth, 1.0)
            else:
                return 0.1  # 默认10%
                
        except Exception as e:
            logger.error(f"获取分析师预期失败 {symbol}: {e}")
            return 0.1

class ReverseDCFCalculator:
    """反向DCF计算器"""
    
    def __init__(self):
        self.forecast_years = 10
        self.perpetual_growth_rate = 0.025
    
    def calculate_implied_growth(self, symbol: str, current_price: float, 
                               financial_data: Dict, wacc: float) -> Dict:
        """计算市场隐含增长率"""
        
        try:
            # 获取基础数据
            latest_fcf = financial_data['latest_fcf']
            shares_outstanding = financial_data['shares_outstanding']
            
            if latest_fcf <= 0 or shares_outstanding <= 0:
                return {'error': '基础数据无效'}
            
            # 计算目标企业价值
            target_enterprise_value = current_price * shares_outstanding
            
            # 使用二分法求解隐含增长率
            implied_growth = self._solve_implied_growth(
                target_enterprise_value, latest_fcf, wacc
            )
            
            if implied_growth is None:
                return {'error': '无法求解隐含增长率'}
            
            # 分析合理性
            reasonableness = self._analyze_growth_reasonableness(
                symbol, implied_growth, financial_data
            )
            
            return {
                'implied_growth_rate': implied_growth,
                'implied_growth_percent': f"{implied_growth:.1%}",
                'reasonableness_score': reasonableness['score'],
                'feasibility_analysis': reasonableness['analysis'],
                'benchmark_comparison': reasonableness['comparison']
            }
            
        except Exception as e:
            logger.error(f"计算隐含增长率失败 {symbol}: {e}")
            return {'error': f'计算失败: {str(e)}'}
    
    def _solve_implied_growth(self, target_enterprise_value: float, 
                            latest_fcf: float, wacc: float) -> Optional[float]:
        """使用数值方法求解隐含增长率"""
        
        def dcf_equation(growth_rate):
            """DCF方程"""
            if growth_rate >= wacc:
                return float('inf')  # 增长率不能大于等于折现率
            
            try:
                # 计算未来现金流现值
                pv_fcf = 0
                current_fcf = latest_fcf
                
                for year in range(1, self.forecast_years + 1):
                    current_fcf = current_fcf * (1 + growth_rate)
                    pv_fcf += current_fcf / ((1 + wacc) ** year)
                
                # 计算终值
                terminal_fcf = current_fcf * (1 + self.perpetual_growth_rate)
                terminal_value = terminal_fcf / (wacc - self.perpetual_growth_rate)
                pv_terminal = terminal_value / ((1 + wacc) ** self.forecast_years)
                
                # 总企业价值
                enterprise_value = pv_fcf + pv_terminal
                
                return enterprise_value - target_enterprise_value
                
            except:
                return float('inf')
        
        try:
            # 扩大搜索范围以处理高估值股票
            upper_bound = min(wacc - 0.001, 0.8)  # 最高80%增长率
            
            # 检查是否有解
            lower_val = dcf_equation(-0.1)
            upper_val = dcf_equation(upper_bound)
            
            # 如果边界值同号，说明在搜索范围内无解
            if lower_val * upper_val > 0:
                # 检查是否是超高估值（企业价值太高）
                if lower_val < 0:  # 都小于目标值，说明需要更高增长率
                    return upper_bound  # 返回最大可能的增长率作为近似
                else:
                    return None  # 无解
            
            implied_growth = brentq(dcf_equation, -0.1, upper_bound)
            return implied_growth
            
        except Exception as e:
            logger.error(f"求解隐含增长率失败: {e}")
            # 作为备选方案，尝试估算
            try:
                # 简单估算：如果所有测试点都低于目标，返回最高增长率
                if dcf_equation(0.5) < 0:
                    return 0.5  # 估算市场隐含50%+增长率
                return None
            except:
                return None
    
    def _analyze_growth_reasonableness(self, symbol: str, implied_growth: float, 
                                     financial_data: Dict) -> Dict:
        """分析隐含增长率的合理性"""
        
        # 历史增长率对比
        historical_growth = financial_data.get('historical_growth', 0.05)
        
        # 计算合理性评分
        score = self._calculate_reasonableness_score(implied_growth, historical_growth)
        
        # 分析评语
        analysis = self._generate_feasibility_analysis(implied_growth, historical_growth)
        
        # 基准对比
        comparison = self._generate_benchmark_comparison(implied_growth)
        
        return {
            'score': score,
            'analysis': analysis,
            'comparison': comparison
        }
    
    def _calculate_reasonableness_score(self, implied_growth: float, historical_growth: float) -> float:
        """计算合理性评分 (0-1)"""
        
        # 基于历史增长率的合理性
        if historical_growth > 0:
            growth_ratio = implied_growth / historical_growth
            if 0.5 <= growth_ratio <= 2.0:
                historical_score = 1.0
            elif 0.3 <= growth_ratio <= 3.0:
                historical_score = 0.7
            else:
                historical_score = 0.3
        else:
            historical_score = 0.5
        
        # 基于绝对增长率的合理性
        if implied_growth < 0:
            absolute_score = 0.2
        elif implied_growth <= 0.1:
            absolute_score = 0.8
        elif implied_growth <= 0.2:
            absolute_score = 0.6
        elif implied_growth <= 0.3:
            absolute_score = 0.4
        else:
            absolute_score = 0.2
        
        # 综合评分
        return (historical_score + absolute_score) / 2
    
    def _generate_feasibility_analysis(self, implied_growth: float, historical_growth: float) -> str:
        """生成可行性分析"""
        
        if implied_growth < 0:
            return "市场预期负增长，可能反映行业或公司基本面恶化"
        elif implied_growth <= 0.05:
            return "市场预期低增长，符合成熟期公司特征"
        elif implied_growth <= 0.15:
            return "市场预期温和增长，较为合理"
        elif implied_growth <= 0.25:
            return "市场预期较高增长，需要强劲基本面支撑"
        else:
            return "市场预期超高增长，实现难度极大，存在泡沫风险"
    
    def _generate_benchmark_comparison(self, implied_growth: float) -> str:
        """生成基准对比"""
        
        gdp_growth = 0.025  # 名义GDP增长率
        
        if implied_growth < gdp_growth:
            return f"低于名义GDP增长率({gdp_growth:.1%})，相对保守"
        elif implied_growth < gdp_growth * 2:
            return f"略高于名义GDP增长率({gdp_growth:.1%})，相对合理"
        elif implied_growth < gdp_growth * 4:
            return f"显著高于名义GDP增长率({gdp_growth:.1%})，需要创新驱动"
        else:
            return f"远超名义GDP增长率({gdp_growth:.1%})，挑战极大"

class EnhancedDCFCalculator:
    """增强版DCF计算器"""
    
    def __init__(self):
        self.stage_identifier = CompanyStageIdentifier()
        self.growth_calculator = DynamicGrowthCalculator()
        self.reverse_dcf = ReverseDCFCalculator()
        self.forecast_years = 10
        self.perpetual_growth_rate = 0.025
    
    def analyze_stock_comprehensive(self, symbol: str, financial_data: Dict, wacc: float) -> Dict:
        """综合分析股票"""
        
        try:
            # 1. 识别发展阶段
            stage_info = self.stage_identifier.identify_stage(symbol, financial_data)
            
            # 2. 计算动态增长率场景
            growth_scenarios = self.growth_calculator.calculate_growth_scenarios(
                symbol, stage_info, financial_data
            )
            
            # 3. 计算各场景下的DCF估值
            model_valuations = {}
            for scenario_name, scenario in growth_scenarios.items():
                valuation = self._calculate_dcf_with_scenario(
                    financial_data, wacc, scenario
                )
                model_valuations[scenario_name] = valuation
            
            # 4. 反向DCF计算
            current_price = financial_data['current_price']
            # 确保current_price是float类型
            try:
                current_price = float(current_price)
            except (ValueError, TypeError):
                current_price = 0.0
                
            market_implied = self.reverse_dcf.calculate_implied_growth(
                symbol, current_price, financial_data, wacc
            )
            
            # 5. 生成对比分析
            insights = self._generate_valuation_insights(
                symbol, model_valuations, market_implied, stage_info, current_price
            )
            
            return {
                'symbol': symbol,
                'stage_analysis': stage_info,
                'growth_scenarios': growth_scenarios,
                'model_valuations': model_valuations,
                'market_implied': market_implied,
                'valuation_insights': insights,
                'recommendation': self._generate_recommendation(insights)
            }
            
        except Exception as e:
            logger.error(f"综合分析失败 {symbol}: {e}")
            return {'error': f'分析失败: {str(e)}'}
    
    def _calculate_dcf_with_scenario(self, financial_data: Dict, wacc: float, 
                                   scenario: GrowthScenario) -> Dict:
        """使用特定场景计算DCF"""
        
        try:
            latest_fcf = financial_data['latest_fcf']
            shares_outstanding = financial_data['shares_outstanding']
            
            # 计算未来现金流
            future_fcf = []
            current_fcf = latest_fcf
            
            # 第1-3年
            for year in range(1, 4):
                current_fcf = current_fcf * (1 + scenario.years_1_3)
                future_fcf.append(current_fcf)
            
            # 第4-7年
            for year in range(4, 8):
                current_fcf = current_fcf * (1 + scenario.years_4_7)
                future_fcf.append(current_fcf)
            
            # 第8-10年
            for year in range(8, 11):
                current_fcf = current_fcf * (1 + scenario.years_8_12)
                future_fcf.append(current_fcf)
            
            # 计算现值
            pv_fcf = []
            for i, fcf in enumerate(future_fcf):
                year = i + 1
                pv = fcf / ((1 + wacc) ** year)
                pv_fcf.append(pv)
            
            # 计算终值
            terminal_fcf = future_fcf[-1] * (1 + scenario.terminal)
            terminal_value = terminal_fcf / (wacc - scenario.terminal)
            pv_terminal = terminal_value / ((1 + wacc) ** self.forecast_years)
            
            # 计算每股价值
            enterprise_value = sum(pv_fcf) + pv_terminal
            intrinsic_value = enterprise_value / shares_outstanding
            
            return {
                'scenario_name': scenario.name,
                'dcf_value': intrinsic_value,
                'enterprise_value': enterprise_value,
                'terminal_value': terminal_value,
                'pv_terminal': pv_terminal,
                'future_fcf': future_fcf,
                'pv_fcf': pv_fcf,
                'growth_rates': {
                    'years_1_3': scenario.years_1_3,
                    'years_4_7': scenario.years_4_7,
                    'years_8_12': scenario.years_8_12,
                    'terminal': scenario.terminal
                }
            }
            
        except Exception as e:
            logger.error(f"DCF计算失败: {e}")
            return {'error': str(e)}
    
    def _generate_valuation_insights(self, symbol: str, model_valuations: Dict, 
                                   market_implied: Dict, stage_info: StageInfo, current_price: float = 0) -> Dict:
        """生成估值洞察"""
        
        try:
            base_valuation = model_valuations.get('base', {})
            base_dcf_value = base_valuation.get('dcf_value', 0)
            
            # 计算估值差距
            valuation_gap = self._calculate_valuation_gap(model_valuations, current_price)
            
            # 增长预期分析
            growth_analysis = self._analyze_growth_expectations(model_valuations, market_implied)
            
            # 风险评估
            risk_assessment = self._assess_risk_factors(symbol, stage_info, market_implied)
            
            return {
                'valuation_gap': valuation_gap,
                'growth_analysis': growth_analysis,
                'risk_assessment': risk_assessment,
                'key_insights': self._generate_key_insights(valuation_gap, growth_analysis, risk_assessment)
            }
            
        except Exception as e:
            logger.error(f"生成估值洞察失败: {e}")
            return {'error': str(e)}
    
    def _calculate_valuation_gap(self, model_valuations: Dict, current_price: float) -> Dict:
        """计算估值差距"""
        
        if current_price <= 0:
            return {'error': '当前价格无效'}
        
        gaps = {}
        for scenario_name, valuation in model_valuations.items():
            if 'error' not in valuation:
                dcf_value = valuation['dcf_value']
                absolute_gap = dcf_value - current_price
                relative_gap = absolute_gap / current_price
                
                gaps[scenario_name] = {
                    'absolute_gap': absolute_gap,
                    'relative_gap': relative_gap,
                    'relative_gap_percent': f"{relative_gap:.1%}"
                }
        
        return gaps
    
    def _analyze_growth_expectations(self, model_valuations: Dict, market_implied: Dict) -> Dict:
        """分析增长预期"""
        
        if 'error' in market_implied:
            return {'error': '市场隐含数据无效'}
        
        implied_growth = market_implied.get('implied_growth_rate', 0)
        
        # 与模型场景对比
        scenario_comparison = {}
        for scenario_name, valuation in model_valuations.items():
            if 'error' not in valuation:
                growth_rates = valuation.get('growth_rates', {})
                avg_growth = np.mean(list(growth_rates.values())[:-1])  # 排除terminal
                
                scenario_comparison[scenario_name] = {
                    'model_growth': avg_growth,
                    'vs_implied': implied_growth - avg_growth,
                    'vs_implied_percent': f"{(implied_growth - avg_growth):.1%}"
                }
        
        return {
            'implied_growth': implied_growth,
            'implied_growth_percent': f"{implied_growth:.1%}",
            'scenario_comparison': scenario_comparison,
            'reasonableness': market_implied.get('reasonableness_score', 0)
        }
    
    def _assess_risk_factors(self, symbol: str, stage_info: StageInfo, market_implied: Dict) -> Dict:
        """评估风险因素"""
        
        risks = []
        opportunities = []
        
        # 基于发展阶段的风险
        stage = stage_info.stage
        if stage == 'high_growth':
            risks.append('增长放缓风险')
            risks.append('竞争加剧风险')
            opportunities.append('持续创新优势')
        elif stage == 'mature':
            risks.append('市场饱和风险')
            opportunities.append('稳定现金流')
        elif stage == 'decline':
            risks.append('行业衰退风险')
            opportunities.append('转型机会')
        
        # 基于市场预期的风险
        if 'error' not in market_implied:
            implied_growth = market_implied.get('implied_growth_rate', 0)
            reasonableness = market_implied.get('reasonableness_score', 0)
            
            if implied_growth > 0.2:
                risks.append('市场预期过高风险')
            if reasonableness < 0.5:
                risks.append('增长预期不切实际')
        
        return {
            'risks': risks,
            'opportunities': opportunities,
            'overall_risk_level': self._calculate_overall_risk_level(risks, opportunities)
        }
    
    def _calculate_overall_risk_level(self, risks: List[str], opportunities: List[str]) -> str:
        """计算整体风险水平"""
        
        risk_score = len(risks)
        opportunity_score = len(opportunities)
        
        if risk_score > opportunity_score + 2:
            return '高风险'
        elif risk_score > opportunity_score:
            return '中风险'
        else:
            return '低风险'
    
    def _generate_key_insights(self, valuation_gap: Dict, growth_analysis: Dict, 
                             risk_assessment: Dict) -> List[str]:
        """生成关键洞察"""
        
        insights = []
        
        # 估值洞察
        if 'base' in valuation_gap:
            base_gap = valuation_gap['base']
            relative_gap = base_gap.get('relative_gap', 0)
            
            if relative_gap > 0.2:
                insights.append(f"模型显示被低估约{abs(relative_gap):.1%}")
            elif relative_gap < -0.2:
                insights.append(f"模型显示被高估约{abs(relative_gap):.1%}")
            else:
                insights.append("估值相对合理")
        
        # 增长预期洞察
        if 'error' not in growth_analysis:
            reasonableness = growth_analysis.get('reasonableness', 0)
            if reasonableness < 0.5:
                insights.append("市场增长预期可能过于乐观")
            elif reasonableness > 0.8:
                insights.append("市场增长预期相对保守")
        
        # 风险洞察
        risk_level = risk_assessment.get('overall_risk_level', '中风险')
        insights.append(f"整体风险水平: {risk_level}")
        
        return insights
    
    def _generate_recommendation(self, insights: Dict) -> Dict:
        """生成投资建议"""
        
        # 基于洞察生成建议
        key_insights = insights.get('key_insights', [])
        risk_level = insights.get('risk_assessment', {}).get('overall_risk_level', '中风险')
        
        # 简单的决策逻辑
        if any('低估' in insight for insight in key_insights) and risk_level != '高风险':
            action = '买入'
            rationale = '模型显示被低估，风险可控'
        elif any('高估' in insight for insight in key_insights) or risk_level == '高风险':
            action = '卖出'
            rationale = '估值过高或风险过大'
        else:
            action = '持有'
            rationale = '估值合理，维持观望'
        
        return {
            'action': action,
            'rationale': rationale,
            'confidence': 'medium'  # 可以基于各种因素计算置信度
        } 

class DCFCalculator:
    """DCF估值计算器 - 基于增强版DCF核心重构"""
    
    def __init__(self):
        self.perpetual_growth_rate = PERPETUAL_GROWTH_RATE
        self.forecast_years = FORECAST_YEARS
        self.default_wacc = DEFAULT_WACC
        
        # 内部使用增强版DCF组件
        self.enhanced_calculator = EnhancedDCFCalculator()
        self.stage_identifier = CompanyStageIdentifier()
        self.growth_calculator = DynamicGrowthCalculator()
    
    def calculate_dcf_valuation(self, stock_data, wacc):
        """
        计算DCF估值 - 统一接口，内部使用增强版DCF
        
        Args:
            stock_data: 股票数据字典
            wacc: 加权平均资本成本
            
        Returns:
            dict: 估值结果（保持原接口兼容）
        """
        try:
            # 优先使用增强版DCF
            enhanced_result = self.enhanced_calculator.analyze_stock_comprehensive(
                stock_data['symbol'], stock_data, wacc
            )
            
            if 'error' not in enhanced_result:
                # 转换为兼容格式
                return self._convert_to_compatible_format(enhanced_result, stock_data, wacc)
            else:
                logger.warning(f"增强版DCF计算失败: {enhanced_result['error']}")
                # 回退到传统DCF
                return self._calculate_traditional_dcf(stock_data, wacc)
                
        except Exception as e:
            logger.error(f"DCF计算失败: {e}")
            # 回退到传统DCF
            return self._calculate_traditional_dcf(stock_data, wacc)
    
    def _convert_to_compatible_format(self, enhanced_result, stock_data, wacc):
        """将增强版DCF结果转换为兼容格式"""
        try:
            # 从增强版结果中提取数据
            symbol = enhanced_result['symbol']
            current_price = stock_data['current_price']  # 从stock_data获取
            
            # 使用基准场景的估值作为主估值
            model_valuations = enhanced_result.get('model_valuations', {})
            base_valuation = model_valuations.get('base', {})  # 使用英文键
            
            if 'error' in base_valuation or not base_valuation:
                # 如果基准场景失败，尝试其他场景
                for scenario_name, scenario_data in model_valuations.items():
                    if 'error' not in scenario_data and scenario_data:
                        base_valuation = scenario_data
                        break
                
                if not base_valuation or 'error' in base_valuation:
                    logger.warning("所有增强版场景都失败，回退到传统DCF")
                    return self._calculate_traditional_dcf(stock_data, wacc)
            
            intrinsic_value = base_valuation['dcf_value']
            
            # 计算IRR
            irr = self._calculate_irr(current_price, intrinsic_value)
            
            # 获取隐含增长率
            market_implied = enhanced_result.get('market_implied', {})
            implied_growth_rate = None
            implied_growth_percent = None
            
            if 'error' not in market_implied:
                implied_growth_rate = market_implied.get('implied_growth_rate', 0)
                implied_growth_percent = market_implied.get('implied_growth_percent', 'N/A')
            
            # 构造兼容格式的结果
            result = {
                'symbol': symbol,
                'name': stock_data.get('name', 'N/A'),
                'current_price': current_price,
                'intrinsic_value': intrinsic_value,
                'irr': irr,
                'evaluation': self._get_evaluation(irr),
                'wacc': wacc,
                'perpetual_growth_rate': self.perpetual_growth_rate,
                'forecast_years': self.forecast_years,
                'latest_fcf': stock_data.get('latest_fcf', 0),
                'enterprise_value': base_valuation.get('enterprise_value', 0),
                'terminal_value': base_valuation.get('terminal_value', 0),
                'pv_terminal': base_valuation.get('pv_terminal', 0),
                'shares_outstanding': stock_data.get('shares_outstanding', 0),
                'future_fcf': base_valuation.get('future_fcf', []),
                'pv_fcf': base_valuation.get('pv_fcf', []),
                'damodaran_industry': stock_data.get('damodaran_industry', 'N/A'),
                'sector': stock_data.get('sector', 'N/A'),
                'industry': stock_data.get('industry', 'N/A'),
                
                # 新增字段：隐含增长率
                'implied_growth_rate': implied_growth_rate,
                'implied_growth_percent': implied_growth_percent,
                
                # 增强版DCF特有信息
                'enhanced_features': True,
                'stage_analysis': enhanced_result.get('stage_analysis', {}),
                'model_valuations': model_valuations,
                'market_implied': market_implied,
                'recommendation': enhanced_result.get('recommendation', {}),
                'calculation_method': 'enhanced_dcf'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"转换增强版DCF结果失败: {e}")
            return self._calculate_traditional_dcf(stock_data, wacc)
    
    def _calculate_traditional_dcf(self, stock_data, wacc):
        """传统DCF计算（备选方案）"""
        try:
            symbol = stock_data['symbol']
            current_price = stock_data['current_price']
            latest_fcf = stock_data['latest_fcf']
            shares_outstanding = stock_data['shares_outstanding']
            
            if latest_fcf <= 0 or shares_outstanding <= 0:
                return {
                    'symbol': symbol,
                    'error': f'关键财务数据缺失: FCF={latest_fcf}, Shares={shares_outstanding}'
                }
            
            # 使用固定增长率计算
            growth_rate = 0.05  # 5%的保守增长率
            
            # 计算预测现金流
            future_fcf = []
            pv_fcf = []
            
            for year in range(1, self.forecast_years + 1):
                fcf = latest_fcf * ((1 + growth_rate) ** year)
                pv = fcf / ((1 + wacc) ** year)
                future_fcf.append(fcf)
                pv_fcf.append(pv)
            
            # 计算终值
            terminal_fcf = future_fcf[-1] * (1 + self.perpetual_growth_rate)
            terminal_value = terminal_fcf / (wacc - self.perpetual_growth_rate)
            pv_terminal = terminal_value / ((1 + wacc) ** self.forecast_years)
            
            # 计算企业价值和每股价值
            enterprise_value = sum(pv_fcf) + pv_terminal
            intrinsic_value = enterprise_value / shares_outstanding
            
            # 计算IRR
            irr = self._calculate_irr(current_price, intrinsic_value)
            
            # 计算隐含增长率
            implied_growth_rate = self._calculate_implied_growth_rate(
                current_price, latest_fcf, shares_outstanding, wacc
            )
            implied_growth_percent = f"{implied_growth_rate:.1%}" if implied_growth_rate else "N/A"
            
            return {
                'symbol': symbol,
                'name': stock_data.get('name', 'N/A'),
                'current_price': current_price,
                'intrinsic_value': intrinsic_value,
                'irr': irr,
                'evaluation': self._get_evaluation(irr),
                'wacc': wacc,
                'perpetual_growth_rate': self.perpetual_growth_rate,
                'forecast_years': self.forecast_years,
                'latest_fcf': latest_fcf,
                'enterprise_value': enterprise_value,
                'terminal_value': terminal_value,
                'pv_terminal': pv_terminal,
                'shares_outstanding': shares_outstanding,
                'future_fcf': future_fcf,
                'pv_fcf': pv_fcf,
                'damodaran_industry': stock_data.get('damodaran_industry', 'N/A'),
                'sector': stock_data.get('sector', 'N/A'),
                'industry': stock_data.get('industry', 'N/A'),
                
                # 新增字段：隐含增长率
                'implied_growth_rate': implied_growth_rate,
                'implied_growth_percent': implied_growth_percent,
                
                # 标记为传统DCF
                'enhanced_features': False,
                'calculation_method': 'traditional_dcf'
            }
            
        except Exception as e:
            logger.error(f"传统DCF计算失败: {e}")
            return {
                'symbol': stock_data.get('symbol', 'N/A'),
                'error': f'DCF计算失败: {str(e)}'
            }
    
    def _calculate_implied_growth_rate(self, current_price, latest_fcf, shares_outstanding, wacc):
        """计算隐含增长率"""
        try:
            # 使用简化的反向DCF计算
            # 假设永续增长率为配置的永续增长率
            # 目标企业价值 = 股价 * 股数
            target_enterprise_value = current_price * shares_outstanding
            
            # 使用二分法求解隐含增长率
            low, high = -0.1, 0.5  # -10%到50%的范围
            tolerance = 0.0001
            
            for _ in range(100):  # 最多迭代100次
                mid = (low + high) / 2
                
                # 计算在此增长率下的企业价值
                calculated_ev = self._calculate_enterprise_value_with_growth(
                    latest_fcf, mid, wacc, self.perpetual_growth_rate
                )
                
                if abs(calculated_ev - target_enterprise_value) < tolerance:
                    return mid
                
                if calculated_ev < target_enterprise_value:
                    low = mid
                else:
                    high = mid
            
            # 如果无法收敛，返回中值
            return (low + high) / 2
            
        except Exception as e:
            logger.error(f"隐含增长率计算失败: {e}")
            return None
    
    def _calculate_enterprise_value_with_growth(self, latest_fcf, growth_rate, wacc, perpetual_growth_rate):
        """根据增长率计算企业价值"""
        try:
            # 计算预测现金流的现值
            pv_fcf = 0
            for year in range(1, self.forecast_years + 1):
                fcf = latest_fcf * ((1 + growth_rate) ** year)
                pv = fcf / ((1 + wacc) ** year)
                pv_fcf += pv
            
            # 计算终值现值
            terminal_fcf = latest_fcf * ((1 + growth_rate) ** self.forecast_years) * (1 + perpetual_growth_rate)
            terminal_value = terminal_fcf / (wacc - perpetual_growth_rate)
            pv_terminal = terminal_value / ((1 + wacc) ** self.forecast_years)
            
            return pv_fcf + pv_terminal
            
        except Exception as e:
            logger.error(f"企业价值计算失败: {e}")
            return 0
    
    def _calculate_irr(self, current_price, intrinsic_value):
        """计算IRR（内部收益率）"""
        try:
            if current_price <= 0:
                return None
            
            # 简化IRR计算：假设10年持有期
            return (intrinsic_value / current_price) ** (1/10) - 1
            
        except Exception as e:
            logger.error(f"IRR计算失败: {e}")
            return None
    
    def _get_evaluation(self, irr):
        """根据IRR获取评估结果"""
        if irr is None:
            return "无法评估"
        
        from config import VALUATION_THRESHOLDS
        
        if irr >= VALUATION_THRESHOLDS['低估']:
            return "低估"
        elif irr >= VALUATION_THRESHOLDS['合理_上限']:
            return "合理"
        elif irr >= VALUATION_THRESHOLDS['高估']:
            return "合理"
        else:
            return "高估"
    
    def is_enhanced_calculation(self, result):
        """检查是否使用了增强版计算"""
        return result.get('enhanced_features', False)
    
    def get_enhanced_analysis(self, result):
        """获取增强版分析信息"""
        if not self.is_enhanced_calculation(result):
            return None
        
        return {
            'stage_analysis': result.get('stage_analysis', {}),
            'model_valuations': result.get('model_valuations', {}),
            'market_implied': result.get('market_implied', {}),
            'recommendation': result.get('recommendation', {})
        }
    
    def evaluate_valuation(self, dcf_result):
        """评估估值"""
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
        
        # 优先基于内在价值倍数评估
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
            elif irr < VALUATION_THRESHOLDS['合理_上限']:
                return '合理'
            else:
                return '低估'
    
    def create_sensitivity_analysis(self, stock_data, base_wacc, wacc_range=0.02, perpetual_growth_range=0.005):
        """创建敏感性分析"""
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