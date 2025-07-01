# 股票估值计算器

基于DCF（贴现现金流）模型的股票估值计算器，支持单个股票和批量股票估值。

## 🚀 功能特点

- **DCF模型估值**：10年期现金流预测，2.5%永续增长率
- **行业WACC**：自动从达摩达兰网站获取行业折现率
- **IRR计算**：内部收益率计算和估值评估
- **批量处理**：支持股票组合批量估值
- **多种输出**：命令行报告和Excel报告
- **行业映射**：智能匹配yfinance和达摩达兰行业分类
- **AI助手**：基于Ollama的自然语言交互界面
- **MCP集成**：Claude Desktop直接集成支持

## 📦 安装

### 基本安装

1. 确保已安装Python 3.10+和uv：
```bash
# 安装uv（如果未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用Homebrew（macOS）
brew install uv
```

2. 安装项目依赖：
```bash
# 安装所有依赖
uv sync

# 仅安装基本功能
uv sync --no-group dev
```

3. 创建必要的目录：
```bash
mkdir -p data output
```

### 🤖 AI助手安装

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

3. 安装AI依赖：
```bash
uv sync --group ai
```

4. 验证安装：
```bash
# 测试AI助手
uv run python ai_chat.py "测试连接"
```

### 🔌 MCP服务器安装

要在Claude Desktop中使用：

1. 安装MCP依赖：
```bash
uv sync --group mcp
```

2. 测试MCP服务器：
```bash
uv run python test_mcp.py
```

3. 配置Claude Desktop（将以下内容添加到Claude Desktop配置文件）：
```json
{
  "mcpServers": {
    "stock-valuation-calculator": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/project",
        "run",
        "python",
        "mcp_server.py"
      ]
    }
  }
}
```

配置文件位置：
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

## 🔧 使用方法

### 🤖 AI助手（推荐）

基于Ollama的对话式AI助手，通过自然语言交互使用所有功能：

```bash
# 启动交互式AI助手
uv run python ai_chat.py

# 直接查询模式
uv run python ai_chat.py "估值苹果公司"
uv run python ai_chat.py "分析TSLA和NVDA的估值"
```

#### 💬 使用示例

**单股票估值:**
- "估值苹果" / "分析AAPL" / "NVDA的估值怎么样"

**批量估值:**
- "分析AAPL,GOOGL,MSFT三只股票"
- "帮我估值苹果、谷歌、微软"

**组合分析:**
- "估值科技股组合" / "tech_stocks组合的估值怎么样"

**管理功能:**
- "有哪些组合" / "更新数据" / "显示行业分类"

#### 🎯 AI助手能力

**✅ 支持功能:**
- DCF估值分析和IRR计算
- 多股票批量处理和组合分析
- 中英文混合输入和意图理解
- WACC数据管理和行业查询

**❌ 使用限制:**
- 仅提供估值分析，不提供投资建议
- 依赖网络连接和数据质量
- 需要Ollama服务运行

### 🔌 MCP服务器（Claude Desktop集成）

配置完成后，直接在Claude Desktop中使用：

```
# 在Claude中直接使用自然语言：
"请帮我估值苹果公司"
"分析AAPL、GOOGL、MSFT的估值"
"生成TSLA和NVDA的Excel估值报告"
```

### 传统命令行

```bash
# 估值单个股票
uv run python valuation.py AAPL

# 估值多个股票
uv run python valuation.py AAPL GOOGL MSFT

# 使用股票组合
uv run python valuation.py --portfolio tech_stocks

# 生成Excel报告
uv run python valuation.py AAPL --excel

# 指定输出文件名
uv run python valuation.py AAPL --excel --output "我的估值报告.xlsx"
```

### 管理功能

```bash
# 列出所有股票组合
uv run python valuation.py --list-portfolios

# 列出所有可用行业（主要用于调试）
uv run python valuation.py --list-industries

# 设置股票的自定义行业（通常不需要，Turbo缓存自动处理）
uv run python valuation.py --set-industry AAPL "计算机与外设"

# 手动更新WACC数据
uv run python valuation.py --update-wacc

# 详细输出
uv run python valuation.py AAPL --verbose
```

## 📊 输出示例

### 命令行输出
```
================================================================================
股票估值报告
================================================================================
生成时间: 2025-07-01 21:21:31
报告股票数量: 1
================================================================================

汇总表格:
股票代码    当前价格    内在价值  IRR 评估
AAPL $205.17 $110.01 1.1% 高估

详细信息:
--------------------------------------------------------------------------------

📊 AAPL 详细估值
----------------------------------------
当前价格: $205.17
内在价值: $110.01
IRR: 1.1%
评估结果: 高估

估值参数:
  折现率 (WACC): 9.29%
  永续增长率: 2.5%
  预测年数: 10年

财务数据:
  最新自由现金流: $108,807,000,000
  企业价值: $1,643,160,299,840
  终值: $2,103,384,103,463
  流通股数: 14,935,799,808

==================================================
统计信息
==================================================
评估结果分布:
  高估: 1只 (100.0%)

IRR统计:
  平均IRR: 1.1%
  中位数IRR: 1.1%
  最高IRR: 1.1%
  最低IRR: 1.1%
==================================================
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
  }
}
```

> 注意：使用Turbo缓存系统后，不再需要手动配置行业映射

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

## 🚀 Turbo缓存系统

系统采用高性能Turbo缓存技术，实现：

### 核心优势
- **毫秒级查询**：41,082个全球股票的WACC数据预计算
- **多国支持**：美国、中国、日本、香港、台湾等交易所
- **直接映射**：股票代码直接对应WACC，无需复杂行业匹配
- **智能兜底**：多级匹配策略确保数据覆盖

### 查询优先级
1. **精确匹配**：股票代码对应国家的行业WACC
2. **模糊匹配**：同国家内的相似行业WACC  
3. **跨国兜底**：使用美国同行业WACC
4. **默认值**：系统默认WACC (8.92%)

### 支持的交易所
- **美国**: NYSE, NASDAQ, AMEX (无后缀)
- **中国**: 上交所(.SS), 深交所(.SZ), 港交所(.HK)  
- **日本**: 东京证交所(.T)
- **台湾**: 台交所(.TW)
- **其他**: 伦敦(.L), 法兰克福(.F)等

## 📈 估值模型

### DCF模型假设
- **预测期**：10年
- **增长率**：使用永续增长率2.5%预测所有未来现金流
- **永续增长率**：2.5%（固定为名义GDP增长率）
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

4. **AI助手限制**：
   - 需要Ollama服务运行
   - 不提供投资建议，仅提供估值分析
   - 依赖模型的自然语言理解能力

## 🛠️ 故障排除

### 常见问题

1. **依赖安装失败**
   - 确保已安装uv：`curl -LsSf https://astral.sh/uv/install.sh | sh`
   - 运行：`uv sync`

2. **无法获取股票数据**
   - 检查股票代码是否正确
   - 确认网络连接正常
   - 某些股票可能在yfinance中不可用

3. **AI助手连接失败**
   - 检查Ollama服务：`ollama serve` 或 `brew services start ollama`
   - 确认模型已下载：`ollama list` 
   - 重新下载模型：`ollama pull llama3.1`
   - 检查AI依赖：`uv sync --group ai`

4. **MCP服务器无法启动**
   - 运行测试：`uv run python test_mcp.py`
   - 检查配置路径是否正确
   - 重启Claude Desktop
   - 确认MCP依赖：`uv sync --group mcp`

5. **Turbo缓存问题**
   - 缺少indname.xls文件，请联系开发者获取
   - 缓存重建：删除 `data/turbo_cache` 文件夹后重新运行

6. **WACC数据更新失败**
   - 检查网络连接
   - 手动运行 `--update-wacc` 重试

7. **Excel报告生成失败**
   - 确保安装了openpyxl：`uv add openpyxl`
   - 检查output目录是否有写入权限

### AI助手专属问题

**Q: AI回复不准确或无关？**
- 使用准确的股票代码而非公司名称
- 尝试更详细地描述需求
- 重新开始对话清除上下文

**Q: "模型下载慢或失败"？**
- 检查网络连接状态
- 尝试不同的模型：`ollama pull qwen2.5:7b`
- 清除缓存：`ollama rm llama3.1` 后重新下载

**Q: 想要更换AI模型？**
```bash
# 下载其他模型
ollama pull qwen2.5:7b
ollama pull gemma2:9b

# 修改 ai_assistant.py 中的模型名称
```

## 🔧 开发

### 项目结构
```
stock_valuation_calculator/
├── pyproject.toml          # 项目配置和依赖
├── config.py              # 估值参数配置
├── valuation.py           # 主程序入口
├── ai_chat.py             # AI助手启动脚本
├── mcp_server.py          # MCP服务器
├── data_fetcher.py        # 数据获取模块
├── dcf_calculator.py      # DCF计算模块
├── report_generator.py    # 报告生成模块
├── data/                  # 数据文件夹
│   ├── stock_portfolios.json
│   └── wacc_data.json
└── output/                # 输出文件夹
```

### 开发环境设置
```bash
# 安装开发依赖
uv sync --group dev

# 运行测试
uv run pytest

# 代码格式化
uv run black .

# 类型检查
uv run mypy .
```

## 📞 支持

如果遇到问题或有改进建议，请：
1. 检查日志输出（使用 `--verbose` 参数）
2. 确认所有依赖已正确安装（运行 `uv sync`）
3. 检查配置文件格式是否正确

## 📄 许可证

本项目仅供学习和研究使用。投资有风险，请谨慎决策。 