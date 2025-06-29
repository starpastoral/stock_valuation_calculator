# 股票估值计算器

基于DCF（贴现现金流）模型的股票估值计算器，支持单个股票和批量股票估值。

## 🚀 功能特点

- **DCF模型估值**：10年期现金流预测，2.5%永续增长率
- **行业WACC**：自动从达摩达兰网站获取行业折现率
- **IRR计算**：内部收益率计算和估值评估
- **批量处理**：支持股票组合批量估值
- **多种输出**：命令行报告和Excel报告
- **行业映射**：智能匹配yfinance和达摩达兰行业分类
- **自动更新**：每月自动更新WACC数据

## 📦 安装

1. 安装Python依赖：
```bash
pip install -r requirements.txt
```

2. 创建必要的目录：
```bash
mkdir -p data output
```

### 🤖 AI助手额外要求

如果要使用AI助手功能，还需要：

1. 安装Ollama：
```bash
# macOS
brew install ollama

# 启动服务
ollama serve
```

2. 下载AI模型：
```bash
# 下载推荐模型
ollama pull llama3.1
```

3. 验证安装：
```bash
# 测试AI助手
python ai_chat.py "测试连接"
```

## 🔧 使用方法

### 🤖 AI助手（推荐）

基于Ollama的对话式AI助手，支持自然语言交互：

```bash
# 启动交互式AI助手
python ai_chat.py

# 直接查询模式
python ai_chat.py "估值苹果公司"
python ai_chat.py "分析TSLA和NVDA的估值"
```

AI助手使用示例：
- "估值苹果" → 自动分析AAPL
- "分析AAPL,GOOGL,MSFT三只股票" → 批量估值
- "估值科技股组合" → 组合分析
- "有哪些组合" → 查看所有组合
- "更新数据" → 更新WACC数据

详细使用说明请参考：[AI助手使用指南](AI_GUIDE.md)

### 🔌 MCP服务器（Claude Desktop集成）

将股票估值功能直接集成到Claude Desktop中：

```bash
# 测试MCP服务器
python test_mcp.py

# 配置Claude Desktop后直接在Claude中使用：
# "请帮我估值苹果公司"
# "分析AAPL、GOOGL、MSFT的估值"
```

详细配置说明请参考：[MCP服务器指南](MCP_GUIDE.md)

### 传统命令行

```bash
# 估值单个股票
python valuation.py AAPL

# 估值多个股票
python valuation.py AAPL GOOGL MSFT

# 使用股票组合
python valuation.py --portfolio tech_stocks

# 生成Excel报告
python valuation.py AAPL --excel

# 指定输出文件名
python valuation.py AAPL --excel --output "我的估值报告.xlsx"
```

### 管理功能

```bash
# 列出所有股票组合
python valuation.py --list-portfolios

# 列出所有可用行业
python valuation.py --list-industries

# 设置股票的自定义行业
python valuation.py --set-industry AAPL "计算机与外设"

# 手动更新WACC数据
python valuation.py --update-wacc

# 详细输出
python valuation.py AAPL --verbose
```

## 📊 输出示例

### 命令行输出
```
================================================================================
股票估值报告
================================================================================
生成时间: 2024-01-15 10:30:00
报告股票数量: 1
================================================================================

汇总表格:
股票代码  当前价格   内在价值   涨跌幅    IRR    评估
AAPL    $150.00   $180.00   20.0%   12.5%   合理

详细信息:
--------------------------------------------------------------------------------

📊 AAPL 详细估值
----------------------------------------
当前价格: $150.00
内在价值: $180.00
涨跌幅: 20.0%
IRR: 12.5%
评估结果: 合理

估值参数:
  折现率 (WACC): 8.50%
  增长率: 15.2%
  永续增长率: 2.5%
  预测年数: 10年

财务数据:
  最新自由现金流: $95,000,000,000
  企业价值: $2,850,000,000,000
  终值: $2,100,000,000,000
  流通股数: 15,800,000,000
```

### Excel报告
生成的Excel文件包含以下工作表：
- **汇总**：所有股票的估值汇总
- **详细数据**：完整的财务和估值数据
- **现金流预测**：10年现金流预测详情
- **参数设置**：估值模型参数说明

## ⚙️ 配置

### 股票组合配置
编辑 `data/stock_portfolios.json` 文件：

```json
{
  "portfolios": {
    "tech_stocks": {
      "description": "科技股组合",
      "stocks": ["AAPL", "GOOGL", "MSFT", "NVDA", "TSLA"]
    },
    "my_portfolio": {
      "description": "我的投资组合",
      "stocks": ["AAPL", "AMZN", "JPM"]
    }
  },
  "custom_industries": {
    "AAPL": "计算机与外设",
    "GOOGL": "互联网"
  }
}
```

### 估值参数配置
编辑 `config.py` 文件：

```python
# 基本参数
PERPETUAL_GROWTH_RATE = 0.025  # 永续增长率 2.5%
FORECAST_YEARS = 10  # 预测年数

# 报告评价标准（基于IRR）
VALUATION_THRESHOLDS = {
    "高估": 0.10,  # IRR < 10%
    "合理": 0.15,  # 10% <= IRR < 15%
    "低估": 0.15   # IRR >= 15%
}
```

## 🔄 自动更新

系统会自动处理以下更新：
- **WACC数据**：每月1号自动更新（超过30天会提示更新）
- **股票数据**：每次运行时从yfinance实时获取

## 🏭 行业映射

系统支持智能行业映射：
1. **用户自定义**：优先使用用户在配置文件中的设置
2. **精确匹配**：匹配yfinance的industry到达摩达兰分类
3. **模糊匹配**：基于关键词的智能匹配
4. **行业默认**：使用yfinance的sector默认映射

如果无法自动映射，系统会提示手动设置：
```bash
python valuation.py --set-industry SYMBOL "行业名称"
```

## 📈 估值模型

### DCF模型假设
- **预测期**：10年
- **增长率**：前5年使用历史平均增长率，后5年线性递减至永续增长率
- **永续增长率**：2.5%
- **折现率**：使用达摩达兰行业WACC数据
- **自由现金流**：经营现金流 - 资本支出

### IRR评估标准
- **高估**：IRR < 10%
- **合理**：10% ≤ IRR < 15%
- **低估**：IRR ≥ 15%

## ⚠️ 注意事项

1. **数据限制**：
   - 需要至少3年历史现金流数据
   - 不支持负自由现金流的股票
   - 金融类股票需要特别注意

2. **网络依赖**：
   - 需要网络连接获取yfinance数据
   - WACC数据更新需要访问达摩达兰网站

3. **估值局限**：
   - 仅基于DCF模型，不包含其他估值方法
   - 不考虑市场情绪和技术分析因素
   - 增长率基于历史数据，可能不反映未来变化

## 🛠️ 故障排除

### 常见问题

1. **无法获取股票数据**
   - 检查股票代码是否正确
   - 确认网络连接正常
   - 某些股票可能在yfinance中不可用

2. **行业映射失败**
   - 使用 `--list-industries` 查看可用行业
   - 使用 `--set-industry` 手动设置行业

3. **WACC数据更新失败**
   - 检查网络连接
   - 手动运行 `--update-wacc` 重试

4. **Excel报告生成失败**
   - 确保安装了openpyxl：`pip install openpyxl`
   - 检查output目录是否有写入权限

## 📞 支持

如果遇到问题或有改进建议，请：
1. 检查日志输出（使用 `--verbose` 参数）
2. 确认所有依赖已正确安装
3. 检查配置文件格式是否正确

## 📄 许可证

本项目仅供学习和研究使用。投资有风险，请谨慎决策。 