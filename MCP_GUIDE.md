# 股票估值MCP服务器使用指南

## 🚀 概述

股票估值MCP服务器将完整的股票估值功能暴露为MCP (Model Context Protocol) 工具，让Claude Desktop等AI客户端可以直接调用股票估值功能。

## 🛠️ 功能特性

### 可用工具

1. **valuate_stock**: 估值单个股票
2. **valuate_multiple_stocks**: 批量估值多个股票
3. **valuate_portfolio**: 估值预设的股票组合
4. **list_portfolios**: 列出所有可用组合
5. **update_wacc_data**: 更新WACC数据
6. **list_industries**: 列出行业分类
7. **generate_excel_report**: 生成Excel报告

## 📦 安装配置

### 1. 安装依赖

```bash
# 确保已安装uv和MCP依赖
uv sync
```

### 2. 配置Claude Desktop

编辑Claude Desktop的配置文件：

**macOS位置**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows位置**: `%APPDATA%\Claude\claude_desktop_config.json`

**配置内容**:
```json
{
  "mcpServers": {
    "stock-valuation-calculator": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/charleslau/stock_valuation_calculator",
        "python",
        "/Users/charleslau/stock_valuation_calculator/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/charleslau/stock_valuation_calculator"
      }
    }
  }
}
```

> ⚠️ **重要**: 请将`cwd`路径修改为您的实际项目路径

### 3. 重启Claude Desktop

配置完成后，重启Claude Desktop以加载MCP服务器。

## 🎯 使用示例

配置成功后，您可以在Claude Desktop中直接使用自然语言来调用股票估值功能：

### 单股票估值
```
请帮我估值苹果公司(AAPL)
```

### 批量估值
```
分析AAPL、GOOGL、MSFT三只股票的估值
```

### 组合估值
```
估值科技股组合
```

### 查看组合
```
显示所有可用的股票组合
```

### 生成报告
```
为AAPL和GOOGL生成Excel估值报告
```

## 🔧 高级配置

### 自定义工作目录

如果您的项目在不同位置，请修改配置中的`cwd`字段：

```json
{
  "mcpServers": {
    "stock-valuation-calculator": {
      "cwd": "/path/to/your/stock_valuation_calculator"
    }
  }
}
```

### 环境变量

您可以在配置中添加额外的环境变量：

```json
{
  "mcpServers": {
    "stock-valuation-calculator": {
      "env": {
        "PYTHONPATH": "/path/to/your/project",
        "DEBUG": "true",
        "CUSTOM_VARIABLE": "value"
      }
    }
  }
}
```

### 使用Python虚拟环境

如果不使用uv，也可以直接使用Python：

```json
{
  "mcpServers": {
    "stock-valuation-calculator": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/project"
    }
  }
}
```

## 🐛 故障排除

### 1. MCP服务器无法启动

**检查步骤:**
```bash
# 1. 验证依赖安装
uv run python -c "import mcp; print('MCP installed')"

# 2. 测试服务器启动
uv run python mcp_server.py

# 3. 检查配置文件语法
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python -m json.tool
```

### 2. 工具不可用

**可能原因:**
- 配置文件路径错误
- Claude Desktop未重启
- 依赖包缺失

**解决方案:**
```bash
# 检查当前目录
pwd

# 验证股票估值系统可用
uv run python -c "from valuation import ValuationSystem; print('System OK')"
```

### 3. 估值数据错误

**检查数据:**
```bash
# 验证WACC数据
uv run python -c "from wacc_updater import WACCUpdater; w=WACCUpdater(); print(w.get_wacc_for_industry('Technology'))"

# 验证股票数据
uv run python -c "from data_fetcher import StockDataFetcher; d=StockDataFetcher(); print(d.get_basic_info('AAPL'))"
```

## 📝 日志和调试

### 启用详细日志

在配置中添加调试环境变量：

```json
{
  "mcpServers": {
    "stock-valuation-calculator": {
      "env": {
        "PYTHONPATH": "/path/to/project",
        "PYTHONUNBUFFERED": "1",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

### 查看日志

Claude Desktop的日志通常位于：
- **macOS**: `~/Library/Logs/Claude/`
- **Windows**: `%LOCALAPPDATA%\Claude\logs\`

## 🔄 更新和维护

### 更新依赖
```bash
uv sync --upgrade
```

### 更新WACC数据
通过Claude Desktop直接调用：
```
更新WACC数据
```

或手动执行：
```bash
uv run python -c "from valuation import ValuationSystem; ValuationSystem().update_wacc_data()"
```

## 🎉 成功标志

配置成功后，您应该能在Claude Desktop中看到：

1. **工具可用**: Claude会提示可以使用股票估值工具
2. **正常响应**: 询问股票估值时会得到详细的分析结果
3. **错误处理**: 输入错误的股票代码时会得到清晰的错误信息

## 📞 支持

如果遇到问题：

1. **检查配置**: 确保路径和格式正确
2. **验证依赖**: 确保所有Python包已安装
3. **查看日志**: 检查Claude Desktop和服务器日志
4. **测试独立运行**: 先确保估值系统本身工作正常

享受您的股票估值MCP服务器！🚀 