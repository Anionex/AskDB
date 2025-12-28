# AskDB - Agno Framework Edition

基于 Agno 智能体框架的 AskDB 实现,提供自然语言数据库查询接口。

## 🌟 主要特性

本实现严格遵循 AskDB 论文架构,包含以下核心功能:

### 1. ReAct 认知框架
- 由 Agno 框架自动封装的 ReAct 循环(Reasoning → Acting → Observation)
- 多步推理和自主决策能力
- 自动 SQL 调试和错误修复

### 2. 四大核心工具

#### execute_query
- 执行 SELECT 查询语句
- 低风险操作,直接执行
- 自动限制返回结果数量(最多15条)

#### execute_non_query
- 执行数据修改操作(INSERT、UPDATE、DELETE等)
- 高风险操作,需要用户确认
- 集成安全评估机制

#### search_tables_by_name
- 基于语义相似度的表搜索
- 使用 sentence-transformers 模型(all-MiniLM-L6-v2)
- 动态模式感知(Schema-Aware Prompting)

#### request_for_internet_search
- 实时网络搜索能力
- 支持 DuckDuckGo、Google、Bing
- 用于获取外部知识辅助查询理解

### 3. 多层安全协议

- **风险分类**: LOW / MEDIUM / HIGH / CRITICAL
- **PII 检测**: 自动检测个人身份信息
- **SQL 注入防护**: 检测潜在的恶意 SQL 模式
- **用户确认机制**: 高风险操作需要显式确认

### 4. 动态模式感知

- 向量索引化的表和列
- 语义搜索相关表结构
- 上下文感知的 Prompt 生成

## 🚀 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境(推荐使用 WSL)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖包
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量示例文件:

```bash
cp .env.example .env
```

编辑 `.env` 文件,配置以下必需项:

```env
# Gemini API 配置
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# 数据库配置
DEFAULT_DB_TYPE=mysql
DEFAULT_DB_HOST=localhost
DEFAULT_DB_PORT=3306
DEFAULT_DB_NAME=your_database
DEFAULT_DB_USER=root
DEFAULT_DB_PASSWORD=your_password
```

**获取 Gemini API Key**: https://makersuite.google.com/app/apikey

### 3. 使用交互式设置向导

```bash
python askdb_agno.py setup
```

这将引导您完成配置过程。

### 4. 启动交互模式

```bash
python askdb_agno.py interactive
```

## 💻 使用方法

### 命令行选项

#### 交互模式
```bash
python askdb_agno.py interactive [--debug]
```

在交互模式中:
- 输入自然语言查询
- 输入 `help` 查看帮助
- 输入 `tables` 列出所有表
- 输入 `exit` 退出

#### 单次查询
```bash
python askdb_agno.py ask "查询语句" [--debug]
```

示例:
```bash
python askdb_agno.py ask "显示所有用户"
python askdb_agno.py ask "统计订单数量"
python askdb_agno.py ask "查找销售额最高的5个产品"
```

#### 查看状态
```bash
python askdb_agno.py status [--debug]
```

显示:
- API 配置状态
- 数据库连接状态
- 可用表列表

#### 查看表结构
```bash
python askdb_agno.py describe <table_name> [--debug]
```

示例:
```bash
python askdb_agno.py describe users
python askdb_agno.py describe orders
```

## 📖 查询示例

### 简单查询
```
> 显示所有用户
> 统计订单总数
> 查找价格最高的产品
```

### 复杂查询
```
> 统计每个用户的订单数量
> 查找2023年销售额最高的5个产品
> 显示加州的客户及其订单总额
```

### 数据修改(需要确认)
```
> 删除状态为"已取消"的订单
> 将产品ID为100的价格更新为99.99
> 插入一个新用户,名字是John,邮箱是john@example.com
```

### 模糊查询(自动表搜索)
```
> 哪个表包含客户信息?
> 显示订单相关的所有表
> 查找包含价格信息的列
```

### 需要外部知识
```
> 什么是SQL注入?
> 解释JOIN操作的类型
> 数据库索引的最佳实践
```

## 🔧 支持的数据库

- **MySQL** - 完全支持
- **PostgreSQL** - 完全支持
- **SQLite** - 完全支持

### MySQL 配置示例
```env
DEFAULT_DB_TYPE=mysql
DEFAULT_DB_HOST=localhost
DEFAULT_DB_PORT=3306
DEFAULT_DB_NAME=mydb
DEFAULT_DB_USER=root
DEFAULT_DB_PASSWORD=password
```

### PostgreSQL 配置示例
```env
DEFAULT_DB_TYPE=postgresql
DEFAULT_DB_HOST=localhost
DEFAULT_DB_PORT=5432
DEFAULT_DB_NAME=mydb
DEFAULT_DB_USER=postgres
DEFAULT_DB_PASSWORD=password
```

### SQLite 配置示例
```env
DEFAULT_DB_TYPE=sqlite
DEFAULT_DB_NAME=data/mydb.db
```

## 🛡️ 安全特性

### 自动风险评估

每个查询都会经过安全评估:

1. **低风险(LOW)** - 简单的 SELECT 查询,直接执行
2. **中风险(MEDIUM)** - 复杂查询或聚合操作,执行时提示
3. **高风险(HIGH)** - 数据修改操作,需要用户确认
4. **危险(CRITICAL)** - 危险操作(DROP、TRUNCATE),强制确认

### 用户确认流程

对于高风险操作,系统会:
1. 显示即将执行的 SQL 语句
2. 说明风险级别
3. 询问是否继续
4. 仅在用户明确同意后执行

示例:
```
> 删除所有2020年的订单

⚠️  High-risk operation detected!
Risk Level: high
SQL: DELETE FROM orders WHERE YEAR(created_at) = 2020

Do you want to proceed? (y/n): 
```

### PII 检测

自动检测以下类型的敏感信息:
- 电子邮件地址
- 电话号码
- 社会安全号码
- 信用卡号
- IP 地址

### SQL 注入防护

检测常见的注入模式:
- UNION 注入
- 注释符注入
- 布尔盲注
- 时间盲注
- 堆叠查询

## 🎯 核心架构

### 1. 工具层 (tools/agno_tools.py)

```python
class DatabaseTools(Toolkit):
    """数据库工具集"""
    - execute_query()       # 查询执行
    - execute_non_query()   # 数据修改
    - list_tables()         # 列出表
    - describe_table()      # 表结构
    - search_tables_by_name() # 语义搜索

class WebSearchTools(Toolkit):
    """网络搜索工具集"""
    - request_for_internet_search() # 网络搜索
```

### 2. Agent 层 (askdb_agno.py)

```python
agent = Agent(
    name="AskDB",
    model=Gemini(id="gemini-2.5-flash"),
    tools=[DatabaseTools(), WebSearchTools()],
    instructions="..." # 详细的系统提示
)
```

### 3. 安全层 (agent/safety.py)

```python
class SafetyManager:
    - assess_query_safety()  # 查询安全评估
    - assess_output_safety() # 输出安全检查
    - PII检测
    - SQL注入检测
    - 风险分类
```

### 4. 模式管理层 (tools/schema.py)

```python
class SchemaManager:
    - explore_schema()        # 探索数据库模式
    - find_relevant_tables()  # 查找相关表
    - build_search_index()    # 构建向量索引
```

## 📊 工作流程

### 典型查询流程

```
1. 用户输入自然语言查询
   ↓
2. 安全评估(SafetyManager)
   ↓
3. 表搜索(search_tables_by_name)
   ↓
4. 模式获取(describe_table)
   ↓
5. SQL 生成(Gemini LLM)
   ↓
6. SQL 执行(execute_query)
   ↓
7. 结果返回
   ↓
8. 自然语言响应
```

### ReAct 循环(由 Agno 管理)

```
思考(Reasoning) → 行动(Acting) → 观察(Observation) → [循环]
```

Agent 自动:
- 分析用户意图
- 选择合适的工具
- 执行操作
- 根据结果调整策略
- 自动调试失败的 SQL

## 🔍 调试模式

启用详细日志:

```bash
python askdb_agno.py interactive --debug
```

调试模式显示:
- 工具调用详情
- LLM 思考过程
- SQL 生成步骤
- 错误堆栈跟踪

## 🚨 常见问题

### 1. 连接数据库失败

**检查清单:**
- `.env` 文件配置是否正确
- 数据库服务是否运行
- 网络连接是否正常
- 用户权限是否足够

```bash
# 测试连接
python askdb_agno.py status
```

### 2. Gemini API 错误

**可能原因:**
- API Key 无效或过期
- 超出速率限制
- 区域限制

**解决方案:**
- 检查 API Key: https://makersuite.google.com/app/apikey
- 查看配额和限制
- 尝试切换模型(在 .env 中修改 GEMINI_MODEL)

### 3. 表搜索不准确

**原因:** 向量索引未构建或过时

**解决方案:**
```python
# 手动构建索引
from tools.database import DatabaseTool
from tools.schema import SchemaManager
from config import get_db_config_manager

config = get_db_config_manager().get_default()
db_tool = DatabaseTool(config)
db_tool.connect()

schema_manager = SchemaManager(db_tool)
schema_manager.build_search_index(force_rebuild=True)
```

### 4. 高风险操作被阻止

这是正常的安全机制。如果需要执行:
- 在交互模式中,按提示确认
- 确保操作意图正确
- 检查 SQL 语句是否符合预期

## 📝 与原版对比

| 特性 | 原版实现 | Agno 版本 |
|------|---------|-----------|
| ReAct 框架 | 手动实现 | Agno 自动封装 |
| 工具定义 | 自定义类 | Agno Toolkit |
| 模型接口 | 抽象接口 | Gemini 直接集成 |
| 代码量 | ~2000 行 | ~600 行 |
| 配置复杂度 | 高 | 低 |
| 功能完整性 | 完整 | 完整 |
| 扩展性 | 好 | 优秀 |

## 🎓 进阶使用

### 自定义工具

创建新的工具:

```python
from agno.tools import Toolkit

class CustomTools(Toolkit):
    def __init__(self):
        super().__init__(
            name="custom",
            tools=[self.my_tool]
        )
    
    def my_tool(self, param: str) -> str:
        """工具描述"""
        # 实现逻辑
        return "result"

# 添加到 agent
agent = Agent(
    model=Gemini(...),
    tools=[DatabaseTools(), WebSearchTools(), CustomTools()],
    ...
)
```

### 修改系统提示

编辑 `askdb_agno.py` 中的 `instructions` 变量来定制 Agent 行为。

### 集成到自己的项目

```python
from askdb_agno import create_agent

# 创建 agent
agent = create_agent(debug=False)

# 处理查询
response = agent.run("你的查询")

# 获取结果
print(response.content)
```

## 📦 依赖项

主要依赖:
- `agno` - Agno 智能体框架
- `google-generativeai` - Gemini API
- `sqlalchemy` - 数据库 ORM
- `sentence-transformers` - 语义搜索
- `rich` - 终端美化
- `click` - CLI 框架

完整依赖列表见 `requirements.txt`。

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议!

## 📄 许可证

MIT License

---

**AskDB Agno Edition**  
*让数据库查询像对话一样自然*

