# 股票估值AI助手使用指南

## 🤖 简介

股票估值AI助手是一个基于Ollama的自然语言交互界面，让您可以通过对话的方式来使用股票估值计算器的各种功能。无需记忆复杂的命令行参数，只需用自然语言描述您的需求即可。

## 🛠️ 环境准备

### 1. 安装Ollama

**macOS（推荐）:**
```bash
# 方法1: 使用Homebrew
brew install ollama

# 方法2: 直接下载安装包
# 访问 https://ollama.ai 下载安装
```

**启动Ollama服务:**
```bash
# 启动服务
ollama serve

# 或者设置为系统服务自动启动
brew services start ollama
```

### 2. 下载AI模型

```bash
# 下载默认模型 llama3.1（推荐）
ollama pull llama3.1

# 或者下载其他模型
ollama pull qwen2.5:7b
ollama pull gemma2:9b
```

### 3. 安装Python依赖

```bash
# 确保已安装ollama Python库
pip install ollama rich
```

## 🚀 快速开始

### 交互式模式（推荐）

```bash
# 启动交互式AI助手
python ai_chat.py
```

### 单次查询模式

```bash
# 直接查询（非交互模式）
python ai_chat.py "估值苹果公司"
python ai_chat.py "分析TSLA和NVDA的估值"
```

## 💬 使用示例

### 1. 估值单个股票

**用户输入:**
- "估值苹果"
- "帮我分析一下特斯拉"
- "NVDA的估值怎么样"
- "分析AAPL"

**AI助手会自动:**
- 获取股票最新财务数据
- 计算DCF内在价值
- 计算IRR
- 给出评估结论（合理/低估/高估）

### 2. 批量估值

**用户输入:**
- "分析AAPL,GOOGL,MSFT三只股票"
- "帮我估值苹果、谷歌、微软"
- "TSLA,NVDA,AMD的估值对比"

**AI助手会:**
- 同时估值多只股票
- 显示对比表格
- 给出各自的评估结论

### 3. 组合估值

**用户输入:**
- "估值科技股组合"
- "分析我的银行股投资组合"
- "tech_stocks组合的估值怎么样"

**AI助手会:**
- 加载预设的股票组合
- 批量估值组合内所有股票
- 显示组合整体表现

### 4. 管理功能

**查看组合:**
- "有哪些组合"
- "显示所有投资组合"
- "list portfolios"

**更新数据:**
- "更新数据"
- "刷新WACC数据" 
- "update wacc"

**查看行业:**
- "显示行业分类"
- "有哪些行业"

## 🎯 AI助手能力

### ✅ 支持的功能

1. **股票估值分析**
   - DCF模型计算
   - IRR计算
   - 估值评估（合理/低估/高估）

2. **批量处理**
   - 多股票同时估值
   - 投资组合分析

3. **数据管理**
   - WACC数据更新
   - 组合信息查看
   - 行业分类信息

4. **自然语言理解**
   - 中英文混合输入支持
   - 股票代码和公司名称识别
   - 意图理解和函数调用

### ❌ 限制说明

1. **不提供投资建议**
   - 仅提供估值分析结果
   - 不推荐买入/卖出时机

2. **数据依赖性**
   - 依赖yfinance数据质量
   - 需要良好的网络连接

3. **计算局限性**
   - 仅基于DCF模型
   - 不考虑市场情绪等因素

## 🔧 高级配置

### 更换AI模型

```bash
# 使用不同的模型
python ai_assistant.py --model qwen2.5:7b
python ai_assistant.py --model gemma2:9b
```

### 调试模式

```bash
# 启用详细日志
export PYTHONPATH=$PWD
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from ai_assistant import StockValuationAI
ai = StockValuationAI()
ai.run_interactive()
"
```

## 🐛 常见问题

### Q1: "Ollama服务未运行"错误
**解决方案:**
```bash
ollama serve
# 或者
brew services start ollama
```

### Q2: 模型下载慢或失败
**解决方案:**
```bash
# 检查网络连接
ollama list
# 重新下载模型
ollama pull llama3.1
```

### Q3: 股票数据获取失败
**解决方案:**
- 检查网络连接
- 验证股票代码是否正确
- 稍后重试（可能是API限制）

### Q4: AI回复不准确
**解决方案:**
- 尝试更详细地描述需求
- 使用股票代码而非公司名称
- 重新启动对话（clear context）

## 📖 示例对话

```
🤖 股票估值AI助手

我可以帮您进行股票估值分析，支持以下功能：
• 估值单个股票（如：估值苹果、分析TSLA）
• 批量估值（如：分析AAPL,GOOGL,MSFT）
• 组合估值（如：估值科技股组合）
• 查看组合列表（如：有哪些组合）
• 更新数据（如：更新WACC数据）

您> 估值苹果公司

🤖 AI助手> 我来为您估值苹果公司(AAPL)。

valuate_stock("AAPL")

✅ AAPL (Apple Inc.) 估值结果：
当前价格: $189.25
内在价值: $205.43
涨跌幅: +8.6%
IRR: 12.4%
评估结果: 低估

估值参数：
  折现率: 9.2%
  增长率: 8.5%
  最新FCF: $84,726,000,000

根据分析，苹果公司当前股价相对于内在价值被低估约8.6%，IRR为12.4%，显示出不错的投资价值。

您> 有哪些组合

🤖 AI助手> 让我为您查看所有可用的投资组合。

list_portfolios()

📁 可用的股票组合：
========================================
组合名称: tech_stocks
描述: 主要科技股投资组合
股票数量: 5
股票列表: AAPL, GOOGL, MSFT, NVDA, TSLA
------------------------------
组合名称: bank_stocks  
描述: 银行股投资组合
股票数量: 3
股票列表: JPM, BAC, WFC
------------------------------

您> 估值科技股组合

🤖 AI助手> 我来为您估值科技股组合。

valuate_portfolio("tech_stocks")

📊 批量估值结果：
============================================================
✅ AAPL (Apple Inc.)
   当前价格: $189.25
   内在价值: $205.43
   涨跌幅: +8.6%
   IRR: 12.4%
   评估: 低估
----------------------------------------
✅ GOOGL (Alphabet Inc.)
   当前价格: $138.45
   内在价值: $162.80
   涨跌幅: +17.6%
   IRR: 15.2%
   评估: 低估
----------------------------------------
[... 其他股票结果 ...]

📁 组合: tech_stocks
```

## 🎉 开始使用

准备就绪？现在就开始使用AI助手吧！

```bash
python ai_chat.py
```

享受与AI助手的对话式股票估值体验！ 