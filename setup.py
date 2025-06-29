#!/usr/bin/env python3
# 股票估值计算器数据设置脚本
import os
import sys
import argparse
from pathlib import Path
from data_processor import DataProcessor

def main():
    """主数据设置函数"""
    parser = argparse.ArgumentParser(description='股票估值计算器数据设置')
    parser.add_argument('--stock-file', 
                       help='大型股票行业映射文件路径（28.6MB的xls/xlsx文件）')
    parser.add_argument('--data-dir', default='data',
                       help='数据目录路径（默认: data）')
    parser.add_argument('--force', action='store_true',
                       help='强制重新处理所有数据')
    
    args = parser.parse_args()
    
    print("🚀 股票估值计算器数据设置")
    print("=" * 50)
    
    # 初始化数据处理器
    processor = DataProcessor(args.data_dir)
    
    # 检查WACC文件
    data_dir = Path(args.data_dir)
    wacc_files = ['waccUS.xls', 'waccChina.xls', 'waccJapan.xls']
    missing_files = []
    
    for file_name in wacc_files:
        file_path = data_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
    
    if missing_files:
        print(f"❌ 缺少WACC文件: {', '.join(missing_files)}")
        print("请确保以下文件存在于data目录中:")
        for file_name in missing_files:
            print(f"  - {file_name}")
        return False
    
    print("✅ WACC文件检查通过")
    
    # 处理WACC数据
    print("\n📊 处理WACC数据...")
    try:
        if args.force or not processor.wacc_cache.exists():
            wacc_data = processor.convert_wacc_files()
            if wacc_data is not None:
                print(f"✅ WACC数据处理完成: {len(wacc_data)} 行")
            else:
                print("❌ WACC数据处理失败")
                return False
        else:
            print("✅ WACC数据缓存已存在，跳过处理")
    except Exception as e:
        print(f"❌ WACC数据处理失败: {e}")
        return False
    
    # 处理股票行业映射文件
    if args.stock_file:
        stock_file_path = Path(args.stock_file)
        
        if not stock_file_path.exists():
            print(f"❌ 股票文件不存在: {args.stock_file}")
            return False
        
        print(f"\n📋 处理股票行业映射文件: {args.stock_file}")
        file_size_mb = stock_file_path.stat().st_size / (1024 * 1024)
        print(f"文件大小: {file_size_mb:.1f} MB")
        
        try:
            if args.force or not processor.stock_industry_cache.exists():
                print("⏳ 处理大型文件，请耐心等待...")
                stock_data = processor.process_large_stock_file(args.stock_file)
                
                if stock_data is not None:
                    print(f"✅ 股票数据处理完成: {len(stock_data)} 行")
                else:
                    print("❌ 股票数据处理失败")
                    return False
            else:
                print("✅ 股票数据缓存已存在，跳过处理")
        except Exception as e:
            print(f"❌ 股票数据处理失败: {e}")
            return False
    else:
        print("\n⚠️  未提供股票行业映射文件")
        print("如果您有28.6MB的股票行业映射文件，请使用 --stock-file 参数指定")
    
    # 创建快速查找索引
    print("\n🔍 创建快速查找索引...")
    try:
        if processor.create_fast_lookup_index():
            print("✅ 索引创建完成")
        else:
            print("❌ 索引创建失败")
            return False
    except Exception as e:
        print(f"❌ 索引创建失败: {e}")
        return False
    
    # 显示数据统计
    print("\n📈 数据统计:")
    cached_data = processor.load_cached_data()
    
    if 'wacc' in cached_data:
        wacc_df = cached_data['wacc']
        regions = wacc_df['region'].value_counts().to_dict()
        print(f"  WACC数据: {len(wacc_df)} 个行业")
        for region, count in regions.items():
            print(f"    {region}: {count} 个行业")
    
    if 'stock_industry' in cached_data:
        stock_df = cached_data['stock_industry']
        print(f"  股票数据: {len(stock_df)} 个股票")
        if 'country' in stock_df.columns:
            countries = stock_df['country'].value_counts().head(5).to_dict()
            print(f"    主要国家: {dict(list(countries.items())[:3])}")
    
    print("\n🎉 数据设置完成！")
    print("\n💡 使用建议:")
    print("  1. 运行股票估值: python valuation.py AAPL")
    print("  2. 查看可用行业: python valuation.py --list-industries")
    print("  3. 查看WACC摘要: python valuation.py --wacc-summary")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 