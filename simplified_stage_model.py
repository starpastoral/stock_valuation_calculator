#!/usr/bin/env python3
"""
简化的发展阶段识别模型
核心理念：一个标准的平衡方案，复杂性通过DCF三场景处理
"""

import pandas as pd
import numpy as np
import yfinance as yf
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

class DevelopmentStage(Enum):
    DECLINE = "衰退期"
    MATURE = "成熟期" 
    MODERATE_GROWTH = "温和成长"
    HIGH_GROWTH = "高成长"

@dataclass
class StageResult:
    """发展阶段识别结果"""
    stage: str
    score: float
    confidence: float
    base_metrics: Dict[str, float]
    reasoning: str

class StandardStageIdentifier:
    """
    标准发展阶段识别器
    采用固定的平衡方案：客观基础(60%) + 有限前瞻(40%) + 逻辑检验
    """
    
    def __init__(self):
        # 固定配置参数，不再允许外部调整
        self.base_weight = 0.6      # 基础财务权重
        self.forward_weight = 0.4   # 前瞻权重
        self.max_adjustment = 0.3   # 最大调整幅度
    
    def identify_stage(self, symbol: str, market: str = "US") -> StageResult:
        """主入口：识别发展阶段"""
        try:
            # 1. 基础财务分析
            base_analysis = self._analyze_fundamentals(symbol, market)
            
            # 2. 前瞻性调整
            forward_adjustment = self._calculate_forward_adjustment(symbol, market)
            
            # 3. 综合评分和阶段判断
            final_score, stage = self._determine_final_stage(
                base_analysis, forward_adjustment, symbol
            )
            
            # 4. 生成推理说明
            reasoning = self._generate_reasoning(base_analysis, forward_adjustment, stage)
            
            return StageResult(
                stage=stage.value,
                score=final_score,
                confidence=0.75,  # 固定置信度，基于测试结果
                base_metrics=base_analysis['metrics'],
                reasoning=reasoning
            )
            
        except Exception as e:
            return StageResult(
                stage=DevelopmentStage.MATURE.value,
                score=0.5,
                confidence=0.3,
                base_metrics={},
                reasoning=f"数据获取失败: {str(e)}"
            )
    
    def _analyze_fundamentals(self, symbol: str, market: str) -> Dict:
        """基础财务分析 - 客观层"""
        try:
            # 获取财务数据
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                return self._default_analysis()
            
            # 核心指标分析
            metrics = {
                'revenue_growth': self._score_revenue_growth(info),
                'profitability': self._score_profitability(info),
                'cash_flow_quality': self._score_cash_flow(info),
                'business_scale': self._score_business_scale(info)
            }
            
            # 加权计算基础评分
            weights = {'revenue_growth': 0.4, 'profitability': 0.3, 'cash_flow_quality': 0.2, 'business_scale': 0.1}
            base_score = sum(metrics[k] * weights[k] for k in metrics)
            
            return {
                'base_score': base_score,
                'metrics': metrics,
                'confidence': 0.8
            }
            
        except Exception as e:
            print(f"基础分析失败: {e}")
            return self._default_analysis()
    
    def _calculate_forward_adjustment(self, symbol: str, market: str) -> float:
        """计算前瞻性调整 - 有限主观层"""
        
        # 行业前景评估（基于当前技术趋势和商业环境）
        industry_outlook = {
            # 高前景行业
            'NVDA': 0.3, 'PLTR': 0.25, '1810.HK': 0.25, 'SNOW': 0.2,
            
            # 中等前景行业  
            'MSFT': 0.2, 'AMZN': 0.15, 'AAPL': 0.1, 'V': 0.1, 'MA': 0.1,
            'TSLA': 0.15,  # 竞争加剧但仍有前景
            
            # 稳定行业
            'JNJ': 0.1, 'KO': 0.05, 'PG': 0.05, 'WMT': 0.1, 'JPM': 0.1,
            
            # 衰退风险行业
            'T': 0.0, 'XOM': 0.0, 'GE': 0.0, 'IBM': -0.05, 'F': 0.05
        }
        
        adjustment = industry_outlook.get(symbol, 0.05)  # 默认小幅正调整
        
        # 限制调整幅度
        return np.clip(adjustment, -self.max_adjustment, self.max_adjustment)
    
    def _determine_final_stage(self, base_analysis: Dict, forward_adjustment: float, symbol: str) -> Tuple[float, DevelopmentStage]:
        """确定最终阶段"""
        
        base_score = base_analysis['base_score']
        
        # 加权合成最终评分
        final_score = (
            base_score * self.base_weight + 
            (base_score + forward_adjustment) * self.forward_weight
        )
        
        final_score = np.clip(final_score, 0.0, 1.0)
        
        # 阶段判断
        if final_score >= 0.75:
            stage = DevelopmentStage.HIGH_GROWTH
        elif final_score >= 0.55:
            stage = DevelopmentStage.MODERATE_GROWTH
        elif final_score >= 0.35:
            stage = DevelopmentStage.MATURE
        else:
            stage = DevelopmentStage.DECLINE
        
        # 逻辑检验：防止明显不合理结果
        stage = self._sanity_check(stage, base_analysis, symbol)
        
        return final_score, stage
    
    def _sanity_check(self, stage: DevelopmentStage, base_analysis: Dict, symbol: str) -> DevelopmentStage:
        """常识性检查"""
        
        metrics = base_analysis.get('metrics', {})
        revenue_growth = metrics.get('revenue_growth', 0)
        
        # 高收入增长企业不应被判为衰退
        if revenue_growth > 0.7 and stage == DevelopmentStage.DECLINE:
            return DevelopmentStage.MODERATE_GROWTH
        
        # 有增长迹象的不应判为衰退
        if revenue_growth > 0.3 and stage == DevelopmentStage.DECLINE:
            return DevelopmentStage.MATURE
            
        return stage
    
    def _generate_reasoning(self, base_analysis: Dict, forward_adjustment: float, stage: DevelopmentStage) -> str:
        """生成推理说明"""
        
        base_score = base_analysis['base_score']
        metrics = base_analysis.get('metrics', {})
        
        reasoning = f"基础评分: {base_score:.3f}"
        
        # 关键指标分析
        if metrics.get('revenue_growth', 0) > 0.7:
            reasoning += " | 收入高增长"
        elif metrics.get('revenue_growth', 0) < 0.3:
            reasoning += " | 收入增长放缓"
            
        if metrics.get('profitability', 0) > 0.7:
            reasoning += " | 盈利能力强"
        elif metrics.get('profitability', 0) < 0.4:
            reasoning += " | 盈利能力待提升"
        
        # 前瞻调整说明
        if forward_adjustment > 0.1:
            reasoning += " | 行业前景向好"
        elif forward_adjustment < -0.1:
            reasoning += " | 行业面临挑战"
        
        reasoning += f" → {stage.value}"
        
        return reasoning
    
    # 辅助方法
    def _score_revenue_growth(self, info: Dict) -> float:
        """收入增长评分"""
        revenue_growth = info.get('revenueGrowth', 0) or 0
        
        if revenue_growth > 0.3: return 1.0
        elif revenue_growth > 0.15: return 0.8
        elif revenue_growth > 0.05: return 0.6
        elif revenue_growth > 0: return 0.4
        elif revenue_growth > -0.05: return 0.2
        elif revenue_growth > -0.15: return 0.1
        else: return 0.05
    
    def _score_profitability(self, info: Dict) -> float:
        """盈利能力评分"""
        profit_margins = info.get('profitMargins', 0) or 0
        roe = info.get('returnOnEquity', 0) or 0
        
        score = 0
        
        # 利润率部分
        if profit_margins > 0.2: score += 0.5
        elif profit_margins > 0.1: score += 0.4
        elif profit_margins > 0.05: score += 0.3
        elif profit_margins > 0: score += 0.2
        elif profit_margins > -0.1: score += 0.1
        
        # ROE部分
        if roe and roe > 0.15: score += 0.5
        elif roe and roe > 0.1: score += 0.4
        elif roe and roe > 0.05: score += 0.3
        elif roe and roe > 0: score += 0.2
        elif roe and roe > -0.1: score += 0.1
        
        return min(score, 1.0)
    
    def _score_cash_flow(self, info: Dict) -> float:
        """现金流质量评分"""
        free_cash_flow = info.get('freeCashflow', 0) or 0
        market_cap = info.get('marketCap', 1) or 1
        
        if free_cash_flow > 0 and market_cap > 0:
            fcf_yield = free_cash_flow / market_cap
            if fcf_yield > 0.05: return 0.8
            elif fcf_yield > 0.03: return 0.6
            elif fcf_yield > 0.01: return 0.4
            else: return 0.3
        else:
            return 0.2
    
    def _score_business_scale(self, info: Dict) -> float:
        """业务规模评分"""
        market_cap = info.get('marketCap', 0) or 0
        
        if market_cap > 500_000_000_000: return 0.7
        elif market_cap > 100_000_000_000: return 0.6
        elif market_cap > 50_000_000_000: return 0.7
        elif market_cap > 10_000_000_000: return 0.8
        else: return 0.5
    
    def _default_analysis(self) -> Dict:
        """默认分析结果"""
        return {
            'base_score': 0.5,
            'metrics': {'revenue_growth': 0.3, 'profitability': 0.3, 'cash_flow_quality': 0.3, 'business_scale': 0.5},
            'confidence': 0.3
        }

def test_simplified_model():
    """测试简化模型"""
    print("=" * 60)
    print("简化标准发展阶段识别模型")
    print("=" * 60)
    
    identifier = StandardStageIdentifier()
    
    test_stocks = [
        ("1810.HK", "小米"),
        ("PLTR", "Palantir"), 
        ("AAPL", "苹果"),
        ("MSFT", "微软"),
        ("KO", "可口可乐"),
        ("T", "AT&T"),
        ("IBM", "IBM")
    ]
    
    for symbol, name in test_stocks:
        market = "HK" if ".HK" in symbol else "US"
        result = identifier.identify_stage(symbol, market)
        
        print(f"\n{name} ({symbol}):")
        print(f"  发展阶段: {result.stage}")
        print(f"  综合评分: {result.score:.3f}")
        print(f"  置信度: {result.confidence:.2f}")
        print(f"  推理: {result.reasoning}")

if __name__ == "__main__":
    test_simplified_model() 