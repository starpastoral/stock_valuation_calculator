# 股票估值计算器配置文件

# 基本参数
PERPETUAL_GROWTH_RATE = 0.025  # 永续增长率 2.5%
FORECAST_YEARS = 10  # 预测年数

# 数据源
DAMODARAN_WACC_URL = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html"
WACC_DATA_FILE = "data/wacc_data.json"
PORTFOLIOS_FILE = "data/stock_portfolios.json"
INDUSTRY_MAPPING_FILE = "data/industry_mapping.json"
OUTPUT_DIR = "output"

# 更新频率
WACC_UPDATE_DAY = 1  # 每月1号更新WACC数据

# 默认值
DEFAULT_WACC = 0.0892  # 如果找不到行业WACC，使用总市场的8.92%

# 报告评价标准（基于IRR）
VALUATION_THRESHOLDS = {
    "高估": 0.10,  # IRR < 10%
    "合理": 0.15,  # 10% <= IRR < 15%
    "低估": 0.15   # IRR >= 15%
} 