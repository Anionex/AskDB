<h1 align="center"> AskDB - 自然语言数据库查询助手 </h1>

<div align="center">

**基于 Agno 框架的智能数据库助手**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![Agno](https://img.shields.io/badge/Agno-Framework-green.svg)](https://github.com/agno-agi/agno)
[![LLM](https://img.shields.io/badge/LLM-Powered-orange.svg)](https://github.com/agno-agi/agno)

[快速开始](#快速开始) • [功能特性](#功能特性) • [使用示例](#使用示例) • [架构设计](#架构设计)

</div>

---

## 📖 简介

AskDB 是一个智能数据库助手，让你可以用**自然语言**与数据库对话。无需编写 SQL，只需描述你想要什么，AI 会帮你完成！

```
你说: "显示销售额最高的5个产品"
AI 做: SELECT name, sales FROM products ORDER BY sales DESC LIMIT 5
```

### 核心特点

- 🤖 **AI 驱动** - 基于大语言模型（LLM），理解你的真实意图
- 🛡️ **多层安全** - 危险操作需要确认，保护你的数据
- 🔍 **智能搜索** - 自动找到相关的表和列，即使你不知道确切名称
- 🔄 **自动调试** - SQL 出错会自动修正，无需人工干预
- 💬 **对话式** - 支持上下文，可以追问和澄清

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

运行交互式配置向导：

```bash
python askdb_agno.py setup
```

或手动创建 `.env` 文件：

```env
# LLM API 配置 (使用 Gemini 作为示例)
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# 数据库配置
DEFAULT_DB_TYPE=mysql
DEFAULT_DB_HOST=localhost
DEFAULT_DB_PORT=3306
DEFAULT_DB_NAME=your_database
DEFAULT_DB_USER=root
DEFAULT_DB_PASSWORD=your_password

# 功能开关
ENABLE_SEMANTIC_SEARCH=false  # 设为 true 启用语义表搜索（all-MiniLM-L6-v2）
```

**获取 API Key**: https://makersuite.google.com/app/apikey

### 3. 开始使用

```bash
# 启动交互模式
python askdb_agno.py interactive

# 单次查询
python askdb_agno.py ask "显示所有用户"

# 查看状态
python askdb_agno.py status

# 查看表结构
python askdb_agno.py describe users
```

## ✨ 功能特性

### 🎯 核心功能

| 功能 | 说明 |
|------|------|
| **自然语言查询** | 用中文或英文提问，无需 SQL 知识 |
| **智能表搜索** | 模糊搜索表名，即使不知道确切名称也能找到 |
| **自动生成 SQL** | AI 理解意图后自动生成优化的 SQL |
| **安全确认机制** | 修改数据前自动要求确认 |
| **错误自动修复** | SQL 错误会自动分析和重试 |
| **上下文记忆** | 记住对话内容，支持追问 |

### 🛡️ 安全特性

#### 三层安全防护

1. **PII 检测** - 防止泄露个人敏感信息
2. **查询复杂度检查** - 阻止过于复杂或危险的操作
3. **数据访问控制** - 标记敏感表和列的访问

#### 风险分级

```
🟢 LOW      → 普通查询，直接执行
🟡 MEDIUM   → 复杂查询，显示提示
🟠 HIGH     → 数据修改，需要确认
🔴 CRITICAL → 危险操作，强制确认
```

#### 确认示例

```
> 删除所有测试订单

⚠️  High-risk operation detected!
Risk Level: high
SQL: DELETE FROM orders WHERE status = 'test'

Do you want to proceed? (y/n): 
```

### 🔧 支持的数据库

- ✅ MySQL / MariaDB
- ✅ PostgreSQL
- ✅ SQLite

## 💡 使用示例

### 基础查询

```
> 显示所有用户
> 统计订单总数
> 查找价格大于100的产品
```

### 复杂查询

```
> 统计每个用户的订单数量
> 查找2023年销售额最高的5个产品
> 显示加州客户的总消费金额
```

### 数据修改（需确认）

```
> 删除状态为"已取消"的订单
> 将产品ID为100的价格更新为99.99
> 创建一个新用户，名字是张三
```

### 模糊搜索

```
> 哪个表包含客户信息？
> 显示所有与订单相关的表
> 查找包含价格的列
```

### 寻求帮助

```
> 什么是JOIN操作？
> 如何优化这个查询？
> 解释一下刚才的SQL
```

## 🏗️ 架构设计

### 技术栈

```
┌─────────────────────────────────────┐
│         Agno Framework              │  智能体框架
│  (ReAct: 推理 → 行动 → 观察)         │
└──────────┬──────────────────────────┘
           │
┌──────────┴──────────────────────────┐
│            LLM                      │  语言模型
└──────────┬──────────────────────────┘
           │
┌──────────┴──────────────────────────┐
│         Tool Layer                  │
│  ┌────────────────────────────┐    │
│  │ DatabaseTools              │    │  核心工具
│  │ - execute_query            │    │
│  │ - execute_non_query        │    │
│  │ - search_tables_by_name    │    │
│  │ - list_tables              │    │
│  │ - describe_table           │    │
│  └────────────────────────────┘    │
│  ┌────────────────────────────┐    │
│  │ WebSearchTools             │    │  扩展工具
│  │ - request_internet_search  │    │
│  └────────────────────────────┘    │
└──────────┬──────────────────────────┘
           │
┌──────────┴──────────────────────────┐
│     Safety Layer                    │
│  - PII Detection                    │  安全层
│  - Query Validation                 │
│  - Risk Assessment                  │
└──────────┬──────────────────────────┘
           │
┌──────────┴──────────────────────────┐
│    Database Layer                   │
│  - MySQL / PostgreSQL / SQLite      │  数据库层
│  - Connection Management            │
│  - Schema Exploration               │
└─────────────────────────────────────┘
```

### 工作流程

```
用户输入
    ↓
自然语言理解
    ↓
安全评估 → [高风险?] → 是 → 用户确认
    ↓               ↓
   否              取消
    ↓
查找相关表
    ↓
生成 SQL
    ↓
执行查询
    ↓
[出错?] → 是 → 自动调试 → 重试
    ↓
   否
    ↓
返回结果
```

### 项目结构

```
askdb/
├── askdb_agno.py              # 主程序入口
├── requirements.txt           # 项目依赖
├── .env.example              # 配置示例
│
├── lib/                       # 核心库
│   └── safety.py             # 安全管理器
│
├── tools/                     # 工具模块
│   ├── agno_tools.py         # Agno 工具集（核心）
│   ├── database.py           # 数据库操作
│   ├── schema.py             # 模式管理
│   └── web_search.py         # 网络搜索
│
└── archive/                   # 归档的原版实现
```

## 🎓 进阶使用

### 命令行选项

```bash
# 交互模式（推荐）
python askdb_agno.py interactive [--debug]

# 单次查询
python askdb_agno.py ask "你的问题" [--debug]

# 查看状态
python askdb_agno.py status

# 查看表结构
python askdb_agno.py describe <表名>

# 配置向导
python askdb_agno.py setup
```

### 调试模式

启用调试模式可以看到 AI 的思考过程：

```bash
python askdb_agno.py interactive --debug
```

会显示：
- 工具调用详情
- SQL 生成步骤
- 错误调试过程

### 环境变量配置

```env
# 基础配置
GEMINI_API_KEY=xxx              # Gemini API 密钥（必需）
GEMINI_MODEL=gemini-2.5-flash  # 模型版本

# 数据库配置
DEFAULT_DB_TYPE=mysql           # 数据库类型
DEFAULT_DB_HOST=localhost       # 主机地址
DEFAULT_DB_PORT=3306           # 端口号
DEFAULT_DB_NAME=mydb           # 数据库名
DEFAULT_DB_USER=root           # 用户名
DEFAULT_DB_PASSWORD=pass       # 密码

# 高级配置
MAX_QUERY_COMPLEXITY=100       # 最大查询复杂度
WEB_SEARCH_PROVIDER=duckduckgo # 搜索引擎
```

## 🔍 常见问题

### Q: 需要什么样的 API Key？
**A:** 当前使用 Gemini API（免费获取：https://makersuite.google.com/app/apikey）。也可以扩展支持其他 LLM（OpenAI、Claude 等）。

### Q: 支持哪些数据库？
**A:** MySQL、PostgreSQL、SQLite。其他数据库可以通过 SQLAlchemy 扩展。

### Q: 会不会误删数据？
**A:** 不会！所有数据修改操作（DELETE、UPDATE、DROP 等）都需要用户明确确认。

### Q: 如何处理复杂查询？
**A:** 尽量用自然语言描述需求，AI 会自动处理 JOIN、GROUP BY 等复杂逻辑。

### Q: 出错了怎么办？
**A:** AI 会自动分析错误并重试。如果持续失败，会给出具体的错误信息。

### Q: 能记住上下文吗？
**A:** 可以！在交互模式下，AI 会记住对话历史，支持追问。

### Q: 性能如何？
**A:** 简单查询 1-3秒，复杂查询 3-10秒。首次运行需要下载模型。

## 🛠️ 故障排除

### 无法连接数据库

```bash
# 1. 检查配置
python askdb_agno.py status

# 2. 测试网络
ping your_database_host

# 3. 检查权限
mysql -u user -p -h host database
```

### API 调用失败

- 检查 API Key 是否正确
- 确认网络可以访问 Google API
- 查看是否超出配额限制

### 导入错误

```bash
# 清理缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
pip install -r requirements.txt --upgrade
```

## 📊 对比原版

| 特性 | 原版实现 | Agno 版本 |
|------|---------|-----------|
| 代码量 | ~5000 行 | ~3000 行 |
| 依赖复杂度 | 高 | 低 |
| ReAct 实现 | 手动 | 框架自动 |
| 配置方式 | 复杂配置文件 | 简单环境变量 |
| 学习曲线 | 陡峭 | 平缓 |
| 功能完整性 | 完整 | 完整 |
| 维护难度 | 高 | 低 |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

<div align="center">

**AskDB - 让数据库查询像对话一样简单** 💬

Made with ❤️ using [Agno Framework](https://github.com/agno-agi/agno)

</div>
