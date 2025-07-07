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

# 报告评价标准（基于Total Return IRR和内在价值倍数）
# IRR = (内在价值 / 当前价格)^(1/年数) - 1
VALUATION_THRESHOLDS = {
    "高估": 0.08,   # IRR < 8% - 年化收益率低于市场平均水平
    "合理_下限": 0.08,  # 8% <= IRR < 12% - 合理的年化收益率区间
    "合理_上限": 0.12,
    "低估": 0.12    # IRR >= 12% - 年化收益率较高，值得投资
}

# 基于内在价值倍数的评估标准
VALUE_RATIO_THRESHOLDS = {
    "严重高估": 0.5,    # 内在价值 < 当前价格的50%
    "高估": 0.8,        # 内在价值 < 当前价格的80%
    "合理_下限": 0.8,   # 80% <= 内在价值/当前价格 < 150%
    "合理_上限": 1.5,
    "低估": 1.5,        # 内在价值 >= 当前价格的150%
    "严重低估": 2.0     # 内在价值 >= 当前价格的200%
} 