# 数据处理模块 - 处理xls文件转换和优化
import pandas as pd
import numpy as np
import os
import json
import logging
from pathlib import Path
import polars as pl
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    """数据处理器 - 优化xls文件读取和查询"""
    
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.cache_dir = self.data_dir / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # 缓存文件路径
        self.wacc_cache = self.cache_dir / "wacc_data.parquet"
        self.industry_cache = self.cache_dir / "industry_mapping.parquet"
        self.stock_industry_cache = self.cache_dir / "stock_industry_mapping.parquet"
    
    def convert_wacc_files(self):
        """转换WACC xls文件为高效的parquet格式"""
        logger.info("转换WACC文件...")
        
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
                # 读取xls文件
                df = pd.read_excel(file_path, engine='xlrd')
                
                # 添加地区标识
                df['region'] = region
                
                # 清理数据
                df = self._clean_wacc_data(df)
                
                all_wacc_data.append(df)
                logger.info(f"成功读取 {region} WACC数据: {len(df)} 行")
                
            except Exception as e:
                logger.error(f"读取 {region} WACC文件失败: {e}")
        
        if all_wacc_data:
            # 合并所有数据
            combined_df = pd.concat(all_wacc_data, ignore_index=True)
            
            # 转换为polars以获得更好的性能
            pl_df = pl.from_pandas(combined_df)
            
            # 保存为parquet
            pl_df.write_parquet(self.wacc_cache)
            logger.info(f"WACC数据已缓存到: {self.wacc_cache}")
            
            return combined_df
        
        return None
    
    def _clean_wacc_data(self, df):
        """清理WACC数据 - 处理复杂的Excel格式"""
        # 查找表头行（包含'Industry Name'的行）
        header_row = None
        for idx, row in df.iterrows():
            if any('Industry Name' in str(cell) for cell in row.values if pd.notna(cell)):
                header_row = idx
                break
        
        if header_row is not None:
            # 使用找到的表头行作为列名
            new_columns = df.iloc[header_row].fillna('').astype(str).tolist()
            
            # 获取表头行之后的数据
            df = df.iloc[header_row + 1:].copy()
            df.columns = new_columns
            
            # 清理列名
            df.columns = [col.strip() for col in df.columns]
        
        # 标准化列名
        column_mapping = {}
        for col in df.columns:
            col_lower = col.lower()
            if 'industry name' in col_lower:
                column_mapping[col] = 'industry'
            elif 'cost of capital (local currency)' in col_lower:
                column_mapping[col] = 'wacc'  # 优先使用本地货币的WACC
            elif 'cost of capital' in col_lower and 'wacc' not in column_mapping.keys():
                column_mapping[col] = 'wacc'
        
        # 应用列名映射
        if column_mapping:
            df.rename(columns=column_mapping, inplace=True)
        
        # 确保有必要的列
        if 'industry' not in df.columns or 'wacc' not in df.columns:
            logger.warning(f"未找到必要的列，现有列: {list(df.columns)}")
            return pd.DataFrame()  # 返回空DataFrame
        
        # 移除缺失的行
        df = df.dropna(subset=['industry', 'wacc'])
        
        # 过滤掉非数据行（如总计行等）
        df = df[df['industry'].astype(str).str.len() > 0]
        df = df[~df['industry'].astype(str).str.contains('Total|Average|NaN|nan', case=False, na=False)]
        
        # 转换WACC为数值
        if len(df) > 0:
            try:
                # 确保WACC列存在且不为空
                if 'wacc' in df.columns:
                    # 处理WACC列的数值转换
                    wacc_series = df['wacc'].copy()
                    
                    # 如果是Series类型，直接转换
                    if isinstance(wacc_series, pd.Series):
                        df['wacc'] = pd.to_numeric(wacc_series, errors='coerce')
                    else:
                        logger.error(f"WACC列数据类型异常: {type(wacc_series)}")
                        return pd.DataFrame()
                    
                    # 移除转换失败的行
                    df = df.dropna(subset=['wacc'])
                    
                    # 检查数值范围（WACC通常在0-1之间，如果大于1可能是百分比格式）
                    if len(df) > 0 and df['wacc'].max() > 1:
                        logger.info("检测到百分比格式，转换为小数")
                        df['wacc'] = df['wacc'] / 100
                        
                else:
                    logger.error("未找到WACC列")
                    return pd.DataFrame()
                
            except Exception as e:
                logger.error(f"WACC数据转换失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return pd.DataFrame()
        
        logger.info(f"清理后的WACC数据: {len(df)} 行")
        return df
    
    def process_large_stock_file(self, file_path):
        """高效处理大型股票行业映射文件"""
        logger.info(f"处理大型股票文件: {file_path}")
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            return None
        
        try:
            # 使用polars读取大文件，速度更快，内存使用更少
            if file_path.suffix.lower() == '.xlsx':
                # 对于xlsx文件，先用pandas读取少量行确定结构
                sample_df = pd.read_excel(file_path, nrows=10)
                logger.info(f"文件列名: {list(sample_df.columns)}")
                
                # 批量读取文件
                chunk_size = 50000  # 每次读取5万行
                chunks = []
                
                for chunk in pd.read_excel(file_path, chunksize=chunk_size):
                    # 清理数据
                    chunk = self._clean_stock_industry_data(chunk)
                    chunks.append(pl.from_pandas(chunk))
                
                # 合并所有chunks
                if chunks:
                    combined_df = pl.concat(chunks)
                    
                    # 保存为parquet格式以加速后续读取
                    combined_df.write_parquet(self.stock_industry_cache)
                    logger.info(f"股票行业映射已缓存到: {self.stock_industry_cache}")
                    
                    return combined_df.to_pandas()
            
            elif file_path.suffix.lower() == '.xls':
                # 对于xls文件，直接读取
                df = pd.read_excel(file_path, engine='xlrd')
                df = self._clean_stock_industry_data(df)
                
                # 转换为polars并缓存
                pl_df = pl.from_pandas(df)
                pl_df.write_parquet(self.stock_industry_cache)
                
                return df
                
        except Exception as e:
            logger.error(f"处理文件失败: {e}")
            return None
    
    def _clean_stock_industry_data(self, df):
        """清理股票行业数据"""
        # 标准化列名 - 针对indname.xls文件格式
        column_mapping = {
            'Exchange:Ticker': 'symbol',
            'Symbol': 'symbol',
            'Ticker': 'symbol', 
            'Stock Symbol': 'symbol',
            'Company Name': 'company_name',
            'Name': 'company_name',
            'Industry Group': 'industry',
            'Industry': 'industry',
            'Industry Name': 'industry',
            'Primary Sector': 'sector',
            'Sector': 'sector',
            'Market Cap': 'market_cap',
            'Country': 'country',
            'SIC Code': 'sic_code',
            'Broad Group': 'broad_group',
            'Sub Group': 'sub_group'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df.rename(columns={old_col: new_col}, inplace=True)
        
        # 处理symbol列 - 从Exchange:Ticker格式中提取纯股票代码
        if 'symbol' in df.columns:
            # 如果是Exchange:Ticker格式，提取Ticker部分
            def extract_ticker(symbol_str):
                if pd.isna(symbol_str):
                    return ''
                symbol_str = str(symbol_str)
                if ':' in symbol_str:
                    return symbol_str.split(':')[-1]  # 取冒号后的部分
                return symbol_str
            
            df['symbol'] = df['symbol'].apply(extract_ticker)
            df['symbol'] = df['symbol'].astype(str).str.upper().str.strip()
            df = df.dropna(subset=['symbol'])
            df = df[df['symbol'] != '']
            df = df[df['symbol'] != 'NAN']
        
        return df
    
    def load_cached_data(self):
        """加载缓存的数据"""
        data = {}
        
        # 加载WACC数据
        if self.wacc_cache.exists():
            try:
                wacc_df = pl.read_parquet(self.wacc_cache).to_pandas()
                data['wacc'] = wacc_df
                logger.info(f"加载WACC缓存数据: {len(wacc_df)} 行")
            except Exception as e:
                logger.error(f"加载WACC缓存失败: {e}")
        
        # 加载股票行业映射
        if self.stock_industry_cache.exists():
            try:
                stock_df = pl.read_parquet(self.stock_industry_cache).to_pandas()
                data['stock_industry'] = stock_df
                logger.info(f"加载股票行业缓存数据: {len(stock_df)} 行")
            except Exception as e:
                logger.error(f"加载股票行业缓存失败: {e}")
        
        return data
    
    def get_stock_industry(self, symbol, stock_df=None):
        """快速查询股票行业"""
        if stock_df is None:
            if not self.stock_industry_cache.exists():
                return None
            stock_df = pl.read_parquet(self.stock_industry_cache).to_pandas()
        
        # 查询股票
        result = stock_df[stock_df['symbol'] == symbol.upper()]
        
        if not result.empty:
            return {
                'symbol': symbol,
                'company_name': result.iloc[0].get('company_name', ''),
                'industry': result.iloc[0].get('industry', ''),
                'sector': result.iloc[0].get('sector', ''),
                'country': result.iloc[0].get('country', '')
            }
        
        return None
    
    def get_industry_wacc(self, industry, region='US', wacc_df=None):
        """快速查询行业WACC"""
        if wacc_df is None:
            if not self.wacc_cache.exists():
                return None
            wacc_df = pl.read_parquet(self.wacc_cache).to_pandas()
        
        # 查询WACC
        result = wacc_df[
            (wacc_df['industry'].str.contains(industry, case=False, na=False)) &
            (wacc_df['region'] == region)
        ]
        
        if not result.empty:
            return result.iloc[0]['wacc']
        
        # 如果找不到精确匹配，尝试模糊匹配
        result = wacc_df[
            wacc_df['industry'].str.contains(industry.split()[0], case=False, na=False) &
            (wacc_df['region'] == region)
        ]
        
        if not result.empty:
            return result.iloc[0]['wacc']
        
        return None
    
    def create_fast_lookup_index(self):
        """创建快速查找索引"""
        logger.info("创建快速查找索引...")
        
        try:
            # 为股票行业映射创建索引
            if self.stock_industry_cache.exists():
                stock_df = pl.read_parquet(self.stock_industry_cache)
                
                # 创建symbol索引字典
                stock_index = {}
                for row in stock_df.iter_rows(named=True):
                    symbol = row.get('symbol', '').upper()
                    if symbol:
                        stock_index[symbol] = {
                            'industry': row.get('industry', ''),
                            'sector': row.get('sector', ''),
                            'company_name': row.get('company_name', ''),
                            'country': row.get('country', '')
                        }
                
                # 保存索引
                index_file = self.cache_dir / "stock_index.json"
                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump(stock_index, f, ensure_ascii=False, indent=2)
                
                logger.info(f"股票索引已创建: {len(stock_index)} 个股票")
            
            # 为WACC数据创建索引
            if self.wacc_cache.exists():
                wacc_df = pl.read_parquet(self.wacc_cache)
                
                wacc_index = {}
                for row in wacc_df.iter_rows(named=True):
                    industry = row.get('industry', '')
                    region = row.get('region', 'US')
                    wacc = row.get('wacc', 0)
                    
                    if industry:
                        key = f"{region}:{industry}"
                        wacc_index[key] = wacc
                
                # 保存WACC索引
                wacc_index_file = self.cache_dir / "wacc_index.json"
                with open(wacc_index_file, 'w', encoding='utf-8') as f:
                    json.dump(wacc_index, f, ensure_ascii=False, indent=2)
                
                logger.info(f"WACC索引已创建: {len(wacc_index)} 个行业")
            
            return True
            
        except Exception as e:
            logger.error(f"创建索引失败: {e}")
            return False
    
    def setup_data(self, large_stock_file=None):
        """初始化数据设置"""
        logger.info("开始数据设置...")
        
        # 1. 转换WACC文件
        wacc_data = self.convert_wacc_files()
        
        # 2. 处理大型股票文件（如果提供）
        if large_stock_file and Path(large_stock_file).exists():
            stock_data = self.process_large_stock_file(large_stock_file)
        
        # 3. 创建快速查找索引
        self.create_fast_lookup_index()
        
        logger.info("数据设置完成！")
        return True

if __name__ == "__main__":
    # 测试数据处理器
    processor = DataProcessor()
    
    # 如果用户有大型股票文件，请在这里指定路径
    # large_file = "data/large_stock_industry_mapping.xlsx"
    
    processor.setup_data() 