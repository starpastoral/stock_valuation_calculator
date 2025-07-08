# 报告生成模块
import pandas as pd
import numpy as np
from datetime import datetime
import os
import logging
from config import OUTPUT_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportGenerator:
    """估值报告生成器"""
    
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_console_report(self, valuations):
        """生成控制台报告"""
        if not valuations:
            print("没有可显示的估值数据")
            return
        
        print("\n" + "="*80)
        print("股票估值报告")
        print("="*80)
        print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"报告股票数量: {len(valuations)}")
        print("="*80)
        
        # 创建汇总表格
        summary_data = []
        
        for valuation in valuations:
            if 'error' in valuation:
                summary_data.append({
                    '股票代码': valuation.get('symbol', 'N/A'),
                    '当前价格': 'N/A',
                    '内在价值': 'N/A',
                    'IRR': 'N/A',
                    '评估': valuation['error']
                })
            else:
                summary_data.append({
                    '股票代码': valuation['symbol'],
                    '当前价格': f"${valuation['current_price']:.2f}",
                    '内在价值': f"${valuation['intrinsic_value']:.2f}",
                    'IRR': f"{valuation['irr']:.1%}" if valuation['irr'] else 'N/A',
                    '评估': valuation['evaluation']
                })
        
        # 显示汇总表格
        df = pd.DataFrame(summary_data)
        print("\n汇总表格:")
        print(df.to_string(index=False))
        
        # 显示详细信息
        print("\n详细信息:")
        print("-"*80)
        
        for valuation in valuations:
            self._print_detailed_valuation(valuation)
    
    def _print_detailed_valuation(self, valuation):
        """打印单个股票的详细估值信息"""
        symbol = valuation.get('symbol', 'N/A')
        print(f"\n📊 {symbol} 详细估值")
        print("-"*40)
        
        if 'error' in valuation:
            print(f"❌ 错误: {valuation['error']}")
            return
        
        # 基本信息
        print(f"当前价格: ${valuation['current_price']:.2f}")
        print(f"内在价值: ${valuation['intrinsic_value']:.2f}")
        print(f"IRR (年化收益率): {valuation['irr']:.1%}" if valuation['irr'] else "IRR: 无法计算")
        print(f"评估结果: {valuation['evaluation']}")
        
        # 新增：隐含增长率
        implied_growth_percent = valuation.get('implied_growth_percent', 'N/A')
        print(f"市场隐含增长率: {implied_growth_percent}")
        
        # 估值参数
        print(f"\n估值参数:")
        print(f"  折现率 (WACC): {valuation['wacc']:.2%}")
        print(f"  永续增长率: {valuation['perpetual_growth_rate']:.2%}")
        print(f"  预测年数: {valuation['forecast_years']}年")
        print(f"  计算方法: {valuation.get('calculation_method', 'traditional_dcf')}")
        
        # 财务数据
        print(f"\n财务数据:")
        print(f"  最新自由现金流: ${valuation['latest_fcf']:,.0f}")
        print(f"  企业价值: ${valuation['enterprise_value']:,.0f}")
        print(f"  终值: ${valuation['terminal_value']:,.0f}")
        print(f"  流通股数: {valuation['shares_outstanding']:,.0f}")
        
        # 增强版DCF特有信息
        if valuation.get('enhanced_features', False):
            print(f"\n🚀 增强版DCF分析:")
            
            # 发展阶段
            stage_analysis = valuation.get('stage_analysis')
            if stage_analysis:
                print(f"  发展阶段: {stage_analysis.stage} (置信度: {stage_analysis.confidence:.1%})")
                if stage_analysis.key_drivers:
                    print(f"  关键驱动因素: {', '.join(stage_analysis.key_drivers)}")
            
            # 多场景估值
            model_valuations = valuation.get('model_valuations', {})
            if model_valuations:
                print(f"  多场景估值:")
                for scenario_name, scenario_data in model_valuations.items():
                    if 'error' not in scenario_data:
                        dcf_value = scenario_data.get('dcf_value', 0)
                        upside = (dcf_value - valuation['current_price']) / valuation['current_price'] * 100
                        print(f"    {scenario_name}: ${dcf_value:.2f} ({upside:+.1f}%)")
            
            # 市场隐含分析
            market_implied = valuation.get('market_implied', {})
            if market_implied and 'error' not in market_implied:
                print(f"  市场隐含分析:")
                print(f"    合理性评分: {market_implied.get('reasonableness_score', 0):.2f}/1.0")
                print(f"    可行性分析: {market_implied.get('feasibility_analysis', 'N/A')}")
            
            # 投资建议
            recommendation = valuation.get('recommendation', {})
            if recommendation:
                print(f"  投资建议: {recommendation.get('action', '未知')} - {recommendation.get('rationale', '无')}")
        
        print(f"  行业分类: {valuation.get('damodaran_industry', 'N/A')}")
        print(f"  板块: {valuation.get('sector', 'N/A')}")
    
    def generate_excel_report(self, valuations, filename=None):
        """生成Excel报告"""
        if not valuations:
            logger.warning("没有数据可以导出到Excel")
            return None
        
        if filename is None:
            filename = f"股票估值报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # 汇总表
                summary_df = self._create_summary_dataframe(valuations)
                summary_df.to_excel(writer, sheet_name='汇总', index=False)
                
                # 详细数据表
                detail_df = self._create_detail_dataframe(valuations)
                detail_df.to_excel(writer, sheet_name='详细数据', index=False)
                
                # 现金流预测表
                fcf_df = self._create_fcf_dataframe(valuations)
                if not fcf_df.empty:
                    fcf_df.to_excel(writer, sheet_name='现金流预测', index=False)
                
                # 参数表
                params_df = self._create_params_dataframe()
                params_df.to_excel(writer, sheet_name='参数设置', index=False)
            
            logger.info(f"Excel报告已生成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"生成Excel报告失败: {e}")
            return None
    
    def _create_summary_dataframe(self, valuations):
        """创建汇总数据表"""
        summary_data = []
        
        for valuation in valuations:
            if 'error' in valuation:
                row = {
                    '股票代码': valuation.get('symbol', 'N/A'),
                    '公司名称': valuation.get('name', 'N/A'),
                    '当前价格': None,
                    '内在价值': None,
                    'IRR': None,
                    '隐含增长率': None,
                    '评估结果': valuation['error'],
                    '计算方法': 'N/A',
                    '错误信息': valuation['error']
                }
            else:
                row = {
                    '股票代码': valuation['symbol'],
                    '公司名称': valuation.get('name', 'N/A'),
                    '当前价格': valuation['current_price'],
                    '内在价值': valuation['intrinsic_value'],
                    'IRR': valuation['irr'],
                    '隐含增长率': valuation.get('implied_growth_percent', 'N/A'),
                    '评估结果': valuation['evaluation'],
                    '计算方法': valuation.get('calculation_method', 'traditional_dcf'),
                    '错误信息': None
                }
            
            summary_data.append(row)
        
        return pd.DataFrame(summary_data)
    
    def _create_detail_dataframe(self, valuations):
        """创建详细数据表"""
        detail_data = []
        
        for valuation in valuations:
            if 'error' in valuation:
                continue
                
            row = {
                '股票代码': valuation['symbol'],
                '公司名称': valuation.get('name', 'N/A'),
                '当前价格': valuation['current_price'],
                '内在价值': valuation['intrinsic_value'],
                'IRR': valuation['irr'],
                '隐含增长率': valuation.get('implied_growth_percent', 'N/A'),
                '评估结果': valuation['evaluation'],
                '计算方法': valuation.get('calculation_method', 'traditional_dcf'),
                '折现率': valuation['wacc'],
                '永续增长率': valuation['perpetual_growth_rate'],
                '预测年数': valuation['forecast_years'],
                '最新自由现金流': valuation['latest_fcf'],
                '企业价值': valuation['enterprise_value'],
                '终值': valuation['terminal_value'],
                '终值现值': valuation['pv_terminal'],
                '流通股数': valuation['shares_outstanding'],
                '行业分类': valuation.get('damodaran_industry', 'N/A'),
                '板块': valuation.get('sector', 'N/A'),
                '发展阶段': valuation.get('stage_analysis', {}).get('stage', 'N/A') if valuation.get('enhanced_features') else 'N/A',
                '阶段置信度': valuation.get('stage_analysis', {}).get('confidence', 0) if valuation.get('enhanced_features') else 0,
            }
            
            detail_data.append(row)
        
        return pd.DataFrame(detail_data)
    
    def _create_fcf_dataframe(self, valuations):
        """创建现金流预测数据表"""
        fcf_data = []
        
        for valuation in valuations:
            if 'error' in valuation:
                continue
            
            symbol = valuation['symbol']
            future_fcf = valuation['future_fcf']
            pv_fcf = valuation['pv_fcf']
            
            for year, (fcf, pv) in enumerate(zip(future_fcf, pv_fcf), 1):
                row = {
                    '股票代码': symbol,
                    '年份': year,
                    '预测现金流': fcf,
                    '现值': pv
                }
                fcf_data.append(row)
        
        return pd.DataFrame(fcf_data)
    
    def _create_params_dataframe(self):
        """创建参数设置表"""
        from config import PERPETUAL_GROWTH_RATE, FORECAST_YEARS, VALUATION_THRESHOLDS
        
        params_data = [
            {'参数名称': '永续增长率', '参数值': f"{PERPETUAL_GROWTH_RATE:.1%}", '说明': '终值计算中使用的长期增长率'},
            {'参数名称': '预测年数', '参数值': f"{FORECAST_YEARS}年", '说明': '现金流预测的年数'},
            {'参数名称': '高估阈值', '参数值': f"{VALUATION_THRESHOLDS['高估']:.1%}", '说明': 'IRR低于此值被认为高估'},
            {'参数名称': '合理阈值', '参数值': f"{VALUATION_THRESHOLDS['合理']:.1%}", '说明': 'IRR高于此值被认为合理'},
            {'参数名称': '低估阈值', '参数值': f"{VALUATION_THRESHOLDS['低估']:.1%}", '说明': 'IRR高于此值被认为低估'},
        ]
        
        return pd.DataFrame(params_data)
    
    def print_statistics(self, valuations):
        """打印统计信息"""
        if not valuations:
            return
        
        # 过滤掉错误的估值
        valid_valuations = [v for v in valuations if 'error' not in v]
        
        if not valid_valuations:
            print("\n没有有效的估值数据用于统计")
            return
        
        print("\n" + "="*50)
        print("统计信息")
        print("="*50)
        
        # 评估结果统计
        evaluations = [v['evaluation'] for v in valid_valuations]
        eval_counts = pd.Series(evaluations).value_counts()
        
        print("评估结果分布:")
        for eval_type, count in eval_counts.items():
            percentage = count / len(valid_valuations) * 100
            print(f"  {eval_type}: {count}只 ({percentage:.1f}%)")
        
        # IRR统计
        irrs = [v['irr'] for v in valid_valuations if v['irr'] is not None]
        if irrs:
            print(f"\nIRR统计:")
            print(f"  平均IRR: {np.mean(irrs):.1%}")
            print(f"  中位数IRR: {np.median(irrs):.1%}")
            print(f"  最高IRR: {np.max(irrs):.1%}")
            print(f"  最低IRR: {np.min(irrs):.1%}")
        
        print("="*50) 