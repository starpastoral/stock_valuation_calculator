# wacc_processor.py - 专门处理WACC数据的处理器
import pandas as pd
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class WACCProcessor:
    """专门处理WACC Excel文件的处理器"""
    
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
    
    def process_all_wacc_files(self):
        """处理所有WACC文件并合并"""
        wacc_files = {
            'US': self.data_dir / 'waccUS.xls',
            'China': self.data_dir / 'waccChina.xls', 
            'Japan': self.data_dir / 'waccJapan.xls'
        }
        
        all_wacc_data = []
        
        for region, file_path in wacc_files.items():
            if not file_path.exists():
                logger.warning(f"WACC文件不存在: {file_path}")
                continue
            
            try:
                wacc_data = self._process_single_wacc_file(file_path, region)
                if wacc_data is not None and len(wacc_data) > 0:
                    all_wacc_data.append(wacc_data)
                    logger.info(f"✅ {region}: 成功处理 {len(wacc_data)} 个行业")
                else:
                    logger.warning(f"⚠️ {region}: 没有获取到有效数据")
                    
            except Exception as e:
                logger.error(f"❌ {region}: 处理失败 - {e}")
        
        if all_wacc_data:
            combined_df = pd.concat(all_wacc_data, ignore_index=True)
            logger.info(f"🎯 合并完成: {len(combined_df)} 个行业WACC数据")
            return combined_df
        else:
            logger.error("❌ 没有成功处理任何WACC文件")
            return None
    
    def _process_single_wacc_file(self, file_path, region):
        """处理单个WACC文件"""
        logger.info(f"处理 {region} WACC文件: {file_path}")
        
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path, engine='xlrd')
            
            if region == 'US':
                return self._process_us_wacc(df, region)
            else:
                return self._process_international_wacc(df, region)
                
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return None
    
    def _process_us_wacc(self, df, region):
        """处理美国WACC文件（有多个工作表）"""
        try:
            # 美国文件的真实数据在"Industry Averages"工作表中
            file_path = self.data_dir / 'waccUS.xls'
            df_us = pd.read_excel(file_path, sheet_name='Industry Averages', engine='xlrd')
            
            # 使用和国际文件相同的处理逻辑
            return self._process_international_wacc(df_us, region)
            
        except Exception as e:
            logger.error(f"处理美国WACC文件失败: {e}")
            return pd.DataFrame()
    
    def _process_international_wacc(self, df, region):
        """处理国际WACC文件（中国/日本）"""
        # 查找表头行
        header_row = None
        for idx, row in df.iterrows():
            if any('Industry Name' in str(cell) for cell in row.values if pd.notna(cell)):
                header_row = idx
                break
        
        if header_row is None:
            logger.error(f"未找到表头行")
            return None
        
        # 提取表头和数据
        header = df.iloc[header_row].fillna('').astype(str).tolist()
        data_df = df.iloc[header_row + 1:].copy()
        data_df.columns = [col.strip() for col in header]
        
        # 查找关键列
        industry_col = None
        wacc_col = None
        
        for col in data_df.columns:
            col_lower = col.lower()
            if 'industry name' in col_lower:
                industry_col = col
            elif 'cost of capital (local currency)' in col_lower:
                wacc_col = col
                break  # 优先使用本地货币版本
            elif 'cost of capital' in col_lower and wacc_col is None:
                wacc_col = col
        
        if not industry_col or not wacc_col:
            logger.error(f"未找到关键列: industry={industry_col}, wacc={wacc_col}")
            return None
        
        # 提取有效数据
        result_data = []
        for _, row in data_df.iterrows():
            industry = row[industry_col]
            wacc_value = row[wacc_col]
            
            # 跳过无效行
            if pd.isna(industry) or pd.isna(wacc_value):
                continue
            
            industry = str(industry).strip()
            if not industry or industry.lower() in ['nan', 'total', 'average']:
                continue
            
            # 转换WACC值
            try:
                if isinstance(wacc_value, (int, float)):
                    wacc_float = float(wacc_value)
                else:
                    wacc_float = float(str(wacc_value).replace('%', ''))
                
                # 确保WACC在合理范围内 (0-1)
                if wacc_float > 1:
                    wacc_float = wacc_float / 100
                
                if 0 <= wacc_float <= 1:
                    result_data.append({
                        'industry': industry,
                        'wacc': wacc_float,
                        'region': region
                    })
                    
            except (ValueError, TypeError):
                continue
        
        if result_data:
            result_df = pd.DataFrame(result_data)
            logger.info(f"{region}: 提取到 {len(result_df)} 个有效行业WACC")
            return result_df
        else:
            logger.warning(f"{region}: 没有提取到有效数据")
            return None

if __name__ == "__main__":
    # 测试WACC处理器
    processor = WACCProcessor()
    result = processor.process_all_wacc_files()
    
    if result is not None:
        print(f"✅ 处理成功: {len(result)} 个行业")
        print(f"国家分布: {result['region'].value_counts().to_dict()}")
        print(f"WACC范围: {result['wacc'].min():.3f} - {result['wacc'].max():.3f}")
        print("\n样本数据:")
        print(result.head(10).to_string())
    else:
        print("❌ 处理失败") 