# WACC数据更新模块 - 使用本地xls文件
import json
import os
from datetime import datetime
import logging
from pathlib import Path
from data_processor import DataProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WACCUpdater:
    """WACC数据更新器 - 使用本地xls文件"""
    
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.processor = DataProcessor(data_dir)
        self.wacc_index_file = self.data_dir / "cache" / "wacc_index.json"
        self.wacc_data = None
        self.wacc_index = None
        
        # 加载数据
        self._load_data()
    
    def _load_data(self):
        """加载WACC数据"""
        try:
            # 优先使用JSON索引（更快）
            if self.wacc_index_file.exists():
                with open(self.wacc_index_file, 'r', encoding='utf-8') as f:
                    self.wacc_index = json.load(f)
                logger.info(f"加载WACC索引: {len(self.wacc_index)} 个行业")
            
            # 加载完整数据作为备份
            cached_data = self.processor.load_cached_data()
            self.wacc_data = cached_data.get('wacc')
            
            if self.wacc_data is not None:
                logger.info(f"加载WACC数据: {len(self.wacc_data)} 行")
                
        except Exception as e:
            logger.error(f"加载WACC数据失败: {e}")
    
    def ensure_wacc_data(self):
        """确保WACC数据可用"""
        if self.wacc_index is None and self.wacc_data is None:
            logger.info("WACC数据不存在，正在从xls文件加载...")
            
            # 从xls文件转换数据
            if self.processor.convert_wacc_files() is not None:
                self.processor.create_fast_lookup_index()
                self._load_data()
                return True
            else:
                logger.error("无法从xls文件加载WACC数据")
                return False
        
        return True
    
    def get_wacc_for_industry(self, industry, region='US'):
        """
        获取特定行业的WACC
        
        Args:
            industry: 行业名称
            region: 地区 ('US', 'China', 'Japan')
        
        Returns:
            float: WACC值，如果找不到返回None
        """
        if not self.ensure_wacc_data():
            return self._get_default_wacc(industry)
        
        # 1. 使用快速索引查找（如果可用）
        if self.wacc_index:
            # 直接匹配
            key = f"{region}:{industry}"
            if key in self.wacc_index:
                return self.wacc_index[key]
            
            # 模糊匹配
            for index_key, wacc_value in self.wacc_index.items():
                if index_key.startswith(f"{region}:") and industry.lower() in index_key.lower():
                    return wacc_value
        
        # 2. 使用数据处理器查找
        if self.wacc_data is not None and 'industry' in self.wacc_data.columns:
            wacc_result = self.processor.get_industry_wacc(industry, region, self.wacc_data)
            if wacc_result is not None:
                return wacc_result
        
        # 3. 使用默认WACC值
        return self._get_default_wacc(industry)
    
    def _get_default_wacc(self, industry=None):
        """获取默认WACC值"""
        # 行业默认WACC映射
        default_wacc_mapping = {
            'software': 0.095,       # 软件 9.5%
            'technology': 0.095,     # 科技 9.5%
            'internet': 0.11,        # 互联网 11%
            'advertising': 0.085,    # 广告 8.5%
            'banking': 0.075,        # 银行 7.5%
            'insurance': 0.08,       # 保险 8%
            'retail': 0.09,          # 零售 9%
            'energy': 0.08,          # 能源 8%
            'healthcare': 0.085,     # 医疗 8.5%
            'manufacturing': 0.085,  # 制造业 8.5%
            'real estate': 0.075,    # 房地产 7.5%
            'utilities': 0.065,      # 公用事业 6.5%
            'telecom': 0.07,         # 电信 7%
            'consumer': 0.085,       # 消费品 8.5%
            'media': 0.09,           # 媒体 9%
            'pharma': 0.085,         # 制药 8.5%
            'biotech': 0.12,         # 生物技术 12%
            'auto': 0.09,            # 汽车 9%
            'transportation': 0.085, # 运输 8.5%
            'industrial': 0.085      # 工业 8.5%
        }
        
        if industry:
            industry_lower = industry.lower()
            # 精确匹配
            if industry_lower in default_wacc_mapping:
                return default_wacc_mapping[industry_lower]
            
            # 模糊匹配
            for key, wacc in default_wacc_mapping.items():
                if key in industry_lower or industry_lower in key:
                    return wacc
        
        # 总市场默认值
        return 0.09  # 9%
    
    def list_available_industries(self, region='US'):
        """列出可用的行业"""
        if not self.ensure_wacc_data():
            return []
        
        industries = []
        
        if self.wacc_index:
            for key in self.wacc_index.keys():
                if key.startswith(f"{region}:"):
                    industry = key.split(':', 1)[1]
                    industries.append(industry)
        elif self.wacc_data is not None:
            region_data = self.wacc_data[self.wacc_data['region'] == region]
            industries = region_data['industry'].tolist()
        
        return sorted(set(industries))
    
    def get_wacc_summary(self):
        """获取WACC数据摘要"""
        if not self.ensure_wacc_data():
            return None
        
        summary = {
            'total_industries': 0,
            'regions': {},
            'last_updated': None
        }
        
        if self.wacc_index:
            # 从索引统计
            for key in self.wacc_index.keys():
                region = key.split(':', 1)[0]
                if region not in summary['regions']:
                    summary['regions'][region] = 0
                summary['regions'][region] += 1
                summary['total_industries'] += 1
        
        elif self.wacc_data is not None:
            # 从数据统计
            summary['total_industries'] = len(self.wacc_data)
            region_counts = self.wacc_data['region'].value_counts().to_dict()
            summary['regions'] = region_counts
        
        # 检查缓存文件的修改时间
        if self.wacc_index_file.exists():
            mtime = os.path.getmtime(self.wacc_index_file)
            summary['last_updated'] = datetime.fromtimestamp(mtime).isoformat()
        
        return summary
    
    def update_wacc_data(self):
        """更新WACC数据（从xls文件重新加载）"""
        logger.info("从xls文件更新WACC数据...")
        
        try:
            # 重新转换xls文件
            if self.processor.convert_wacc_files() is not None:
                self.processor.create_fast_lookup_index()
                self._load_data()
                logger.info("WACC数据更新成功")
                return True
            else:
                logger.error("WACC数据更新失败")
                return False
                
        except Exception as e:
            logger.error(f"更新WACC数据时出错: {e}")
            return False
    
    def search_industry(self, query, region='US'):
        """搜索匹配的行业"""
        if not self.ensure_wacc_data():
            return []
        
        query_lower = query.lower()
        matches = []
        
        if self.wacc_index:
            for key, wacc in self.wacc_index.items():
                if key.startswith(f"{region}:") and query_lower in key.lower():
                    industry = key.split(':', 1)[1]
                    matches.append({
                        'industry': industry,
                        'wacc': wacc,
                        'region': region
                    })
        
        elif self.wacc_data is not None:
            region_data = self.wacc_data[self.wacc_data['region'] == region]
            matched_data = region_data[
                region_data['industry'].str.contains(query, case=False, na=False)
            ]
            
            for _, row in matched_data.iterrows():
                matches.append({
                    'industry': row['industry'],
                    'wacc': row['wacc'],
                    'region': row['region']
                })
        
        return matches

if __name__ == "__main__":
    # 测试WACC更新器
    updater = WACCUpdater()
    
    # 测试功能
    print("WACC数据摘要:")
    summary = updater.get_wacc_summary()
    if summary:
        print(f"总行业数: {summary['total_industries']}")
        print(f"地区分布: {summary['regions']}")
    
    # 测试查询
    wacc = updater.get_wacc_for_industry("Software", "US")
    print(f"软件行业WACC: {wacc}")
    
    # 测试搜索
    matches = updater.search_industry("software", "US")
    print(f"搜索'software'的结果: {len(matches)} 个匹配") 