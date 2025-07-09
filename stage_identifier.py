#!/usr/bin/env python3
"""
统一的企业发展阶段识别模块
提供标准化的阶段识别功能，替代原dcf_calculator中的CompanyStageIdentifier
"""

from simplified_stage_model import StandardStageIdentifier, StageResult, DevelopmentStage
from typing import Dict, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class StageInfo:
    """兼容原版的公司发展阶段信息"""
    stage: str
    confidence: float
    metrics: Dict
    key_drivers: List[str]

class CompanyStageIdentifier:
    """
    兼容性适配器
    保持与原版API兼容，内部使用新的StandardStageIdentifier
    """
    
    def __init__(self):
        self.standard_identifier = StandardStageIdentifier()
        logger.info("初始化企业发展阶段识别器 (使用新的StandardStageIdentifier)")
    
    def identify_stage(self, symbol: str, financial_data: Dict) -> StageInfo:
        """
        识别公司发展阶段 - 兼容原版API
        
        Args:
            symbol: 股票代码
            financial_data: 财务数据字典（为了兼容性保留，内部会重新获取）
            
        Returns:
            StageInfo: 发展阶段信息
        """
        try:
            # 确定市场
            market = "HK" if ".HK" in symbol.upper() else "US"
            
            # 使用新的标准识别器
            result = self.standard_identifier.identify_stage(symbol, market)
            
            # 转换为兼容格式
            stage_info = StageInfo(
                stage=self._convert_stage_name(result.stage),
                confidence=result.confidence,
                metrics=self._convert_metrics(result.base_metrics),
                key_drivers=self._extract_key_drivers(result.reasoning, result.base_metrics)
            )
            
            # 保持向后兼容：将计算结果传递给financial_data
            if isinstance(financial_data, dict):
                financial_data['historical_growth'] = result.base_metrics.get('revenue_growth', 0.05)
            
            logger.info(f"识别{symbol}发展阶段: {stage_info.stage} (置信度: {stage_info.confidence:.2f})")
            return stage_info
            
        except Exception as e:
            logger.error(f"识别公司发展阶段失败 {symbol}: {e}")
            return StageInfo(
                stage='mature',
                confidence=0.3,
                metrics={},
                key_drivers=['数据不足']
            )
    
    def _convert_stage_name(self, new_stage: str) -> str:
        """转换阶段名称以保持兼容性"""
        stage_mapping = {
            "高成长": "high_growth",
            "温和成长": "moderate_growth", 
            "成熟期": "mature",
            "衰退期": "decline"
        }
        return stage_mapping.get(new_stage, "mature")
    
    def _convert_metrics(self, base_metrics: Dict) -> Dict:
        """转换指标格式以保持兼容性"""
        return {
            'revenue_growth': base_metrics.get('revenue_growth', 0.05),
            'size_factor': 1 - base_metrics.get('business_scale', 0.5),  # 转换逻辑
            'profitability_stability': base_metrics.get('profitability', 0.5),
            'cash_flow_quality': base_metrics.get('cash_flow_quality', 0.5)
        }
    
    def _extract_key_drivers(self, reasoning: str, metrics: Dict) -> List[str]:
        """从推理文本中提取关键驱动因素"""
        drivers = []
        
        # 基于推理文本提取
        if "收入高增长" in reasoning:
            drivers.append("强劲营收增长")
        if "盈利能力强" in reasoning:
            drivers.append("盈利稳定性")
        if "行业前景向好" in reasoning:
            drivers.append("行业前景")
        
        # 基于指标提取
        if metrics.get('cash_flow_quality', 0) > 0.6:
            drivers.append("现金流质量")
        if metrics.get('business_scale', 0) < 0.4:  # 小公司
            drivers.append("较小规模优势")
            
        if not drivers:
            drivers.append("基础面表现一般")
        
        return drivers

# 新版本的主要接口
class StageIdentifier:
    """
    新版本的阶段识别器
    推荐新项目使用此接口
    """
    
    def __init__(self):
        self.identifier = StandardStageIdentifier()
    
    def identify_stage(self, symbol: str, market: str = "US") -> StageResult:
        """
        识别发展阶段 - 新版本API
        
        Args:
            symbol: 股票代码
            market: 市场标识 ("US", "HK", 等)
            
        Returns:
            StageResult: 详细的阶段识别结果
        """
        return self.identifier.identify_stage(symbol, market)
    
    def get_stage_simple(self, symbol: str, market: str = "US") -> str:
        """获取简单的阶段名称"""
        result = self.identify_stage(symbol, market)
        return result.stage
    
    def get_stage_score(self, symbol: str, market: str = "US") -> float:
        """获取阶段评分"""
        result = self.identify_stage(symbol, market)
        return result.score

# 便捷函数
def identify_company_stage(symbol: str, market: str = "US") -> StageResult:
    """便捷函数：识别公司发展阶段"""
    identifier = StageIdentifier()
    return identifier.identify_stage(symbol, market)

def get_stage_name(symbol: str, market: str = "US") -> str:
    """便捷函数：只获取阶段名称"""
    result = identify_company_stage(symbol, market)
    return result.stage

# 向后兼容性测试
def test_compatibility():
    """测试向后兼容性"""
    print("测试向后兼容性...")
    
    # 测试旧版API
    old_identifier = CompanyStageIdentifier()
    financial_data = {}
    
    for symbol in ["AAPL", "1810.HK", "KO"]:
        try:
            result = old_identifier.identify_stage(symbol, financial_data)
            print(f"{symbol}: {result.stage} (置信度: {result.confidence:.2f})")
        except Exception as e:
            print(f"{symbol}: 错误 - {e}")
    
    print("\n测试新版API...")
    
    # 测试新版API  
    new_identifier = StageIdentifier()
    
    for symbol in ["AAPL", "1810.HK", "KO"]:
        try:
            result = new_identifier.identify_stage(symbol)
            print(f"{symbol}: {result.stage} (评分: {result.score:.3f})")
        except Exception as e:
            print(f"{symbol}: 错误 - {e}")

if __name__ == "__main__":
    test_compatibility() 