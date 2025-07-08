# 股票估值计算器 - 智能DCF系统

基于智能增强版DCF（贴现现金流）模型的股票估值计算器，支持单个股票和批量股票估值。

## 🚀 功能特点

### 核心功能
- **智能DCF估值**：基于增强版DCF核心，自动选择最优估值方法
- **发展阶段识别**：自动识别公司发展阶段（高成长、成熟、衰退）
- **动态增长率**：基于历史业绩、行业特征智能调整增长率
- **多场景估值**：保守、中性、激进三种场景分析
- **反向DCF**：计算市场隐含增长率，评估市场预期合理性
- **智能WACC**：优先个股WACC，行业WACC智能fallback
- **批量处理**：支持股票组合批量估值
- **多种输出**：命令行报告和Excel报告

### 增强版DCF特点
- **公司发展阶段自动识别**：基于多维度指标智能识别
- **动态增长率计算**：替代固定增长率的静态模式
- **多场景估值对比**：提供估值区间而非单一数值
- **市场隐含分析**：反向DCF计算市场预期
- **智能投资建议**：基于综合分析提供投资建议

### 技术优势
- **智能缓存机制**：优化的WACC获取策略
- **行业映射**：智能匹配yfinance和达摩达兰行业分类
- **AI助手**：基于Ollama的自然语言交互界面
- **MCP集成**：Claude Desktop直接集成支持

## 🚀 最新优化 - 统一DCF核心

### 优化内容
- **统一架构**: 将增强版DCF作为核心计算引擎
- **智能fallback**: 增强版失败时自动使用传统DCF
- **保持兼容**: 原有接口完全兼容，无需修改调用代码
- **性能提升**: 单一计算器减少重复计算

### 计算逻辑
1. **第一优先级**: 增强版DCF（动态增长率、阶段识别）
2. **第二优先级**: 传统DCF（固定增长率备选）
3. **WACC获取**: 个股WACC > 行业WACC > 默认WACC
4. **结果增强**: 自动附加发展阶段、市场隐含等信息

### 功能集成
- ✅ 发展阶段识别和动态增长率
- ✅ 多场景估值（保守、中性、激进）
- ✅ 反向DCF和市场隐含分析
- ✅ 智能投资建议
- ✅ 完整的错误处理和fallback机制

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

**反向DCF分析:**
- "反向DCF分析苹果" / "市场对TSLA的增长预期"

**管理功能:**
- "有哪些组合" / "更新数据" / "显示行业分类"

#### 🎯 AI助手能力

**✅ 支持功能:**
- 智能DCF估值分析和IRR计算
- 发展阶段识别和动态增长率
- 多场景估值和反向DCF分析
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
"反向DCF分析特斯拉的市场预期"
"生成TSLA和NVDA的Excel估值报告"
```

### 传统命令行

#### 基本估值分析

```bash
# 估值单个股票（现在使用增强版DCF核心）
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

#### 高级分析功能

```bash
# 反向DCF分析（计算市场隐含增长率）
uv run python valuation.py --reverse-dcf AAPL

# 批量反向DCF分析
uv run python valuation.py --reverse-dcf AAPL TSLA GOOGL

# 对比分析（显示计算方法和增强功能）
uv run python valuation.py --compare AAPL

# 管理功能
uv run python valuation.py --portfolios      # 列出所有组合
uv run python valuation.py --industries      # 列出所有行业
uv run python valuation.py --update         # 更新WACC数据
```

## 📊 输出示例

### 智能DCF估值结果

```
📊 估值结果:
--------------------------------------------------------------------------------
📈 AAPL: 估值 $162.80 | 现价 $150.25 | 差距 +8.4%
   IRR: 12.5% | 评估: 低估
   发展阶段: mature (置信度: 85.0%)
--------------------------------------------------------------------------------
📈 GOOGL: 估值 $145.20 | 现价 $138.50 | 差距 +4.8%
   IRR: 11.2% | 评估: 合理
   发展阶段: mature (置信度: 78.0%)
--------------------------------------------------------------------------------
```

### 反向DCF分析结果

```
🔮 反向DCF分析结果:
📊 AAPL: 市场隐含增长率 9.2%
📊 TSLA: 市场隐含增长率 25.3%
📊 GOOGL: 市场隐含增长率 7.8%
```

### 对比分析结果

```
📊 对比分析结果:
📈 AAPL: 估值 $162.80 vs 现价 $150.25 (+8.4%) [方法: enhanced_dcf]
📈 TSLA: 估值 $195.40 vs 现价 $248.50 (-21.4%) [方法: enhanced_dcf]
```

## 🛠️ 技术架构

### 核心类结构

```python
# 统一DCF计算器（增强版核心）
DCFCalculator
├── calculate_dcf_valuation()           # 主要接口（兼容原版）
├── _convert_to_compatible_format()     # 结果格式转换
├── _calculate_traditional_dcf()        # 传统DCF备选
├── is_enhanced_calculation()           # 检查计算方法
└── get_enhanced_analysis()             # 获取增强分析

# 增强版DCF组件
EnhancedDCFCalculator
├── analyze_stock_comprehensive()       # 综合分析
├── CompanyStageIdentifier              # 发展阶段识别
├── DynamicGrowthCalculator             # 动态增长率
└── ReverseDCFCalculator                # 反向DCF

# 估值系统
ValuationSystem
├── valuate_single_stock()              # 单股票估值
├── valuate_multiple_stocks()           # 批量估值
├── analyze_stock_reverse_dcf()         # 反向DCF分析
└── compare_traditional_vs_enhanced()   # 对比分析
```

### 增长率计算逻辑

```python
def calculate_growth_scenarios(symbol, stage_info, financial_data):
    """
    智能增长率计算：
    1. 分析历史3-5年营收增长趋势
    2. 识别公司发展阶段
    3. 考虑行业成长性和市场环境
    4. 生成分阶段动态增长率
    5. 提供保守、中性、激进三种场景
    """
```

### WACC获取策略

```python
def get_wacc_for_stock(symbol, sector, industry):
    """
    智能WACC获取：
    1. 优先尝试个股WACC计算
    2. 失败时使用行业WACC（智能缓存）
    3. 最后使用默认WACC
    """
```

## 🎯 使用建议

### 新用户入门
1. **快速开始**: 使用AI助手进行自然语言交互
2. **了解功能**: 先用单个股票测试各种分析功能
3. **批量分析**: 熟悉后使用组合功能批量处理

### 日常使用场景
1. **估值分析**: 使用标准估值命令获取智能DCF结果
2. **市场预期**: 使用反向DCF分析市场隐含增长率
3. **深度研究**: 结合多场景估值和发展阶段分析
4. **投资决策**: 综合估值结果、市场预期和风险评估

### 最佳实践
1. **数据质量**: 定期使用`--update`更新WACC数据
2. **结果验证**: 对比多个场景估值，关注估值区间
3. **市场对比**: 使用反向DCF了解市场预期的合理性
4. **风险控制**: 重点关注发展阶段识别和风险评估

## 🔧 配置文件

### 估值参数配置 (config.py)

```python
# DCF参数
FORECAST_YEARS = 10              # 预测年数
PERPETUAL_GROWTH_RATE = 0.025    # 永续增长率
DEFAULT_WACC = 0.10              # 默认WACC

# 估值阈值
VALUATION_THRESHOLDS = {
    '严重低估': 0.15,
    '低估': 0.10,
    '高估': 0.05
}

VALUE_RATIO_THRESHOLDS = {
    '严重低估': 2.0,
    '低估': 1.3,
    '高估': 0.8,
    '严重高估': 0.5
}
```

### 股票组合配置 (data/stock_portfolios.json)

```json
{
  "portfolios": {
    "tech_stocks": {
      "description": "科技股组合",
      "stocks": ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
    },
    "dividend_stocks": {
      "description": "股息股组合", 
      "stocks": ["JNJ", "PG", "KO", "PEP", "WMT"]
    }
  }
}
```

## 📈 演示和测试

### 运行演示脚本

```bash
# 运行完整演示
uv run python demo_enhanced_dcf.py

# 调试特定功能
uv run python debug_enhanced_dcf.py
```

### 测试MCP服务器

```bash
# 测试MCP连接
uv run python test_mcp.py

# 启动MCP服务器
uv run python mcp_server.py
```

## 🚀 开始使用

1. **安装依赖**:
   ```bash
   uv sync
   ```

2. **快速体验**:
   ```bash
   # 使用AI助手
   uv run python ai_chat.py "估值苹果公司"
   
   # 或直接命令行
   uv run python valuation.py AAPL
   ```

3. **高级功能**:
   ```bash
   # 反向DCF分析
   uv run python valuation.py --reverse-dcf AAPL
   
   # 批量分析
   uv run python valuation.py AAPL GOOGL MSFT --excel
   ```

## 📚 更多资源

- [DCF估值模型理论](DCF估值模型探讨.html)
- [项目GitHub仓库](https://github.com/your-repo/stock-valuation-calculator)
- [技术文档](docs/)
- [问题反馈](https://github.com/your-repo/stock-valuation-calculator/issues)

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📄 许可证

MIT License - 详见[LICENSE](LICENSE)文件。

---

⭐ 如果这个项目对您有帮助，请给一个Star！ 