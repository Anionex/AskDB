<h1 align="center"> AskDB - 自然语言数据库查询助手 </h1>

<div align="center">

**基于 Agno 框架的智能数据库助手**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![Agno](https://img.shields.io/badge/Agno-Framework-green.svg)](https://github.com/agno-agi/agno)
[![LLM](https://img.shields.io/badge/LLM-Powered-orange.svg)](https://github.com/agno-agi/agno)

[快速开始](#快速开始) • [启动指南](#-启动指南) • [功能特性](#功能特性) • [使用示例](#使用示例) • [架构设计](#架构设计)

</div>

---

## 📖 简介

AskDB 是一个智能数据库助手，让你可以用**自然语言**与数据库对话。无需编写 SQL，只需描述你想要什么，AI 会帮你完成！

```
你说: "显示销售额最高的5个产品"
AI 做: SELECT name, sales FROM products ORDER BY sales DESC LIMIT 5
```

### 🏛️ 架构概览

AskDB 采用前后端分离架构：

- **前端** (`frontend/`)：React + Vite + Ant Design，提供现代化的 Web 界面
- **后端** (`backend/`)：FastAPI + Agno 框架，提供 RESTful API 和 AI 智能体服务
- **CLI 工具** (`askdb_agno.py`)：命令行交互模式，适合快速查询和自动化

### 核心特点

- 🤖 **AI 驱动** - 基于大语言模型（LLM），理解你的真实意图
- 🛡️ **多层安全** - 危险操作需要确认，保护你的数据
- 🔍 **智能搜索** - 自动找到相关的表和列，即使你不知道确切名称
- 🔄 **自动调试** - SQL 出错会自动修正，无需人工干预
- 💬 **对话式** - 支持上下文，可以追问和澄清

## 🚀 快速开始

### 1. 创建虚拟环境

#### 方式一：使用 uv（推荐，更快）

[uv](https://docs.astral.sh/uv/) 是一个极快的 Python 包管理器，比 pip 快 10-100 倍。

```bash
# 安装 uv（如果还没有）
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境
uv venv

# 激活虚拟环境
# Windows (PowerShell/CMD)
.\.venv\Scripts\activate

# Windows (Git Bash)
source .venv/Scripts/activate

# Linux / macOS
source .venv/bin/activate
```

#### 方式二：使用传统 venv

如果你不想安装 uv，可以使用 Python 内置的 venv：

**Windows (PowerShell/CMD):**
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\activate
```

**Windows (Git Bash):**
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/Scripts/activate
```

**Linux / macOS:**
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

成功激活后，终端提示符前会显示 `(.venv)` 或 `(venv)`。

### 2. 安装 Python 依赖

在激活的虚拟环境中安装依赖。项目使用 `pyproject.toml` 管理依赖（现代 Python 标准）：

**使用 uv（推荐）：**
```bash
uv sync
```

这会自动安装 `pyproject.toml` 中定义的所有依赖。

**使用传统 pip：**
```bash
pip install -e .
```

**安装可选依赖：**
```bash
# 安装所有可选依赖
uv sync --all-extras
# 或
pip install -e ".[all]"

# 仅安装 vector 依赖（高效向量搜索）
pip install -e ".[vector]"

# 仅安装 web 依赖（Streamlit UI）
pip install -e ".[web]"

# 仅安装开发依赖（测试框架）
pip install -e ".[dev]"
```

### 3. 配置环境变量

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

### 4. 安装前端依赖（可选，使用 Web UI）

如果你想使用 Web 界面，需要先安装前端依赖：

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 返回根目录
cd ..
```

> 📁 前端代码在 `frontend/` 目录下，后端代码在 `backend/` 目录下

### 5. 启动服务


注：需要先启动数据库，下面是一段示例命令，从wsl启动opengauss数据库

```bash
wsl -d CentOS7
su omm
gs_ctl restart -D /opt/software/openGauss/data/single_node/
```


#### 方式一：使用 Web UI（推荐）

**启动后端服务**

```bash
python start_backend.py
```

后端服务将在 `http://localhost:8000` 启动

**启动前端服务**

打开新的终端窗口：

```bash
python start_frontend.py
```

或者直接使用 npm：

```bash
cd frontend
npm run dev
```

前端服务将在 `http://localhost:5173` 启动

然后在浏览器中访问：`http://localhost:5173`

#### 方式二：使用命令行（CLI）

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

#### 🔧 后端技术栈 (Python)

**核心框架**
- **Python 3.9+** - 主要开发语言
- **Agno Framework** - AI Agent 智能体框架（核心）
- **FastAPI** - 高性能异步 Web 框架
- **Uvicorn** - ASGI 异步服务器

**AI & LLM**
- **OpenAI** - GPT 系列模型支持
- **Google Generative AI** - Gemini 系列模型支持
- **Sentence Transformers** - 文本嵌入和语义相似度
- **ChromaDB** - 向量数据库，用于智能语义搜索

**数据库支持**
- **SQLAlchemy 2.0+** - 现代化 ORM 框架
- **SQLite** - 默认轻量级数据库
- **PostgreSQL** - psycopg2-binary 驱动
- **MySQL** - pymysql 驱动
- **OpenGauss** - 自定义方言支持

**安全 & 认证**
- **PyJWT** - JWT Token 认证
- **Python-Multipart** - 文件上传支持
- **Safety Layer** - 自定义安全检查模块

**数据处理 & 工具**
- **Pydantic 2.0+** - 数据验证和配置管理
- **NumPy / SciPy** - 科学计算和向量运算
- **Rich** - 终端美化输出
- **Click** - CLI 命令行工具
- **DuckDuckGo Search (ddgs)** - Web 搜索工具

**异步 & 网络**
- **Aiohttp** - 异步 HTTP 客户端
- **Nest Asyncio** - 异步事件循环管理
- **Requests / Urllib3** - HTTP 请求库

#### 🎨 前端技术栈 (React)

**核心框架**
- **React 18.2** - 声明式 UI 框架
- **Vite 4.4** - 下一代前端构建工具（极速 HMR）

**UI 组件库**
- **Ant Design 6.1** - 企业级 UI 组件库
- **@ant-design/icons** - Ant Design 图标库
- **Lucide React** - 现代化图标库

**状态管理**
- **Zustand 5.0** - 轻量级状态管理库（比 Redux 更简单）

**数据处理 & 渲染**
- **Axios** - Promise 风格的 HTTP 客户端
- **React Markdown** - Markdown 渲染组件
- **React Syntax Highlighter** - 代码语法高亮
- **Remark GFM** - GitHub Flavored Markdown 支持
- **Recharts** - React 图表库

#### 🛠️ 开发工具链

- **UV** - 超快速 Python 包管理器（官方推荐，比 pip 快 10-100 倍）
- **pytest / pytest-asyncio** - Python 测试框架
- **Git** - 版本控制
- **npm** - 前端包管理器
- **ESLint / Prettier** - 代码规范（可选）

#### 📦 架构层次

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
├── .venv/                     # 🐍 虚拟环境（uv 创建）
├── askdb_agno.py              # CLI 主程序入口
├── start_backend.py           # 后端启动脚本
├── start_frontend.py          # 前端启动脚本
├── pyproject.toml             # 项目配置和依赖（uv）
├── .env                       # 环境配置（需创建）
│
├── backend/                   # 🔷 后端服务目录
│   ├── main.py               # FastAPI 应用入口
│   └── agents.py             # Agent 业务逻辑
│
├── frontend/                  # 🔶 前端应用目录
│   ├── package.json          # Node.js 依赖
│   ├── vite_config.js        # Vite 配置
│   ├── index.html            # 入口 HTML
│   └── src/                  # React 源码
│       ├── App.jsx           # 主应用组件
│       ├── components/       # UI 组件
│       ├── store/            # 状态管理
│       └── config/           # 前端配置
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
├── dialects/                  # 数据库方言
│   └── opengauss_dialect.py  # OpenGauss 支持
│
└── data/                      # 数据文件
    └── business_metadata.json # 业务元数据
```

> 💡 `.venv/` 是使用 [uv](https://docs.astral.sh/uv/) 创建的虚拟环境目录，包含所有 Python 依赖。如果使用传统 venv，目录名可能是 `venv/`。

## 🎮 启动指南

> ⚠️ **重要提示**：启动前请确保已激活虚拟环境！
> ```bash
> # uv 环境（推荐）
> # Windows (PowerShell/CMD)
> .\.venv\Scripts\activate
> # Windows (Git Bash)
> source .venv/Scripts/activate
> # Linux / macOS
> source .venv/bin/activate
> 
> # 或传统 venv 环境
> # Windows (PowerShell/CMD)
> .\venv\Scripts\activate
> # Windows (Git Bash)
> source venv/Scripts/activate
> # Linux / macOS
> source venv/bin/activate
> ```

### Web UI 模式（推荐）

Web UI 提供了更友好的图形界面，适合日常使用。前后端分离架构：
- **后端**：`backend/` 目录，FastAPI 服务，提供 API 接口
- **前端**：`frontend/` 目录，React + Vite 应用，提供用户界面

#### 步骤 1: 启动后端服务

在项目根目录的终端中运行：

```bash
# 使用启动脚本（推荐）
python start_backend.py

# 或直接使用 uvicorn
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

你会看到类似输出：

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

后端服务默认运行在：
- 本地访问：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`

#### 步骤 2: 启动前端服务

打开**新的**终端窗口，在项目根目录运行：

```bash
# 方式 1: 使用启动脚本
python start_frontend.py

# 方式 2: 直接使用 npm
cd frontend
npm run dev
```

你会看到类似输出：

```
  VITE v4.4.5  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

#### 步骤 3: 访问 Web UI

在浏览器中打开：`http://localhost:5173`

> 💡 **提示**：前端会自动连接到后端 API (`http://localhost:8000`)，确保两个服务都在运行。

### CLI 命令行模式

适合快速查询和脚本自动化。

#### 交互模式

```bash
python askdb_agno.py interactive
```

进入交互式对话：

```
🤖 AskDB Agent Ready!
Type 'exit' or 'quit' to end the conversation.

You: 显示所有用户
AI: [执行查询并显示结果]

You: 统计每个用户的订单数
AI: [自动生成 SQL 并执行]
```

#### 单次查询模式

```bash
python askdb_agno.py ask "你的问题"
```

示例：

```bash
python askdb_agno.py ask "显示销售额最高的5个产品"
```

#### 其他命令

```bash
# 查看当前状态
python askdb_agno.py status

# 查看表结构
python askdb_agno.py describe users

# 配置向导
python askdb_agno.py setup
```

### 常见启动问题

#### 0. 虚拟环境未激活

**症状**：
- `ModuleNotFoundError: No module named 'xxx'`
- 提示缺少各种包

**解决**：

```bash
# 激活虚拟环境
# uv 环境（推荐）
# Windows (PowerShell/CMD)
.\.venv\Scripts\activate
# Windows (Git Bash)
source .venv/Scripts/activate
# Linux / macOS
source .venv/bin/activate

# 或传统 venv 环境
# Windows (PowerShell/CMD)
.\venv\Scripts\activate
# Windows (Git Bash)
source venv/Scripts/activate
# Linux / macOS
source venv/bin/activate

# 确认激活成功（提示符前应显示 (.venv) 或 (venv)）
# 然后重新安装依赖
uv sync  # 使用 uv
# 或
pip install -e .     # 使用传统 pip
```

#### 1. 后端启动失败

**症状**：`uvicorn: command not found` 或 `ModuleNotFoundError: No module named 'uvicorn'`

**解决**：

```bash
# 确保虚拟环境已激活
uv sync  # 使用 uv
# 或
pip install -e .     # 使用传统 pip
```

#### 2. 前端启动失败

**症状**：`npm: command not found`

**解决**：确保已安装 Node.js

```bash
# 检查 Node.js 版本
node --version

# 如果未安装，请从官网下载
# https://nodejs.org/
```

**症状**：`Cannot find module 'vite'`

**解决**：

```bash
cd frontend
npm install
```

#### 3. 无法连接数据库

**症状**：`Can't connect to database server`

**解决**：

```bash
# 1. 检查配置文件 .env
cat .env

# 2. 测试数据库连接
python askdb_agno.py status

# 3. 确保数据库服务已启动
# MySQL: service mysql start
# PostgreSQL: service postgresql start
```

#### 4. API Key 错误

**症状**：`Invalid API key`

**解决**：

```bash
# 重新配置
python askdb_agno.py setup

# 或手动编辑 .env 文件
nano .env
```

### 端口配置

默认端口：
- **后端**：`8000` (在 `backend/` 目录)
- **前端**：`5173` (在 `frontend/` 目录)

如需修改：

**后端端口**：编辑项目根目录的 `start_backend.py`

```python
uvicorn.run(
    "backend.main:app",
    host="0.0.0.0",
    port=8000,  # 修改此处
    reload=True
)
```

**前端端口**：编辑 `frontend/vite_config.js`

```javascript
export default {
  server: {
    port: 5173,  // 修改此处
    host: '0.0.0.0'
  }
}
```

**前端 API 地址**：如果修改了后端端口，需同步修改前端配置。编辑 `frontend/src/App.jsx` 或相关配置文件中的 API 地址。

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

### Q: 需要创建虚拟环境吗？
**A:** 强烈推荐！虚拟环境可以隔离项目依赖，避免与系统或其他项目的包冲突。推荐使用 [uv](https://docs.astral.sh/uv/)（更快），也可以使用传统的 `python -m venv`。

### Q: uv 和传统 pip 有什么区别？
**A:** uv 是一个用 Rust 编写的超快速 Python 包管理器，速度比 pip 快 10-100 倍，并且有更好的依赖解析。两者都可以用，uv 更推荐用于日常开发。

### Q: 为什么使用 pyproject.toml 而不是 requirements.txt？
**A:** `pyproject.toml` 是现代 Python 项目的标准配置文件（PEP 518/621），可以统一管理项目元数据、依赖、构建系统等。相比 `requirements.txt` 更灵活，支持可选依赖分组，且是 uv 的原生格式。

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

### 虚拟环境问题

```bash
# 1. 检查虚拟环境是否激活（提示符应显示 (.venv) 或 (venv)）
# 如未激活，执行：

# uv 环境（推荐）
# Windows (PowerShell/CMD)
.\.venv\Scripts\activate
# Windows (Git Bash)
source .venv/Scripts/activate
# Linux / macOS
source .venv/bin/activate

# 传统 venv 环境
# Windows (PowerShell/CMD)
.\venv\Scripts\activate
# Windows (Git Bash)
source venv/Scripts/activate
# Linux / macOS
source venv/bin/activate

# 2. 重新安装依赖
uv sync  # 使用 uv（推荐）
# 或
pip install -e .     # 使用传统 pip

# 3. 如果虚拟环境损坏，重新创建
deactivate  # 先退出当前环境

# 删除旧环境
# Windows
rmdir /s .venv   # 如果是 uv 环境
rmdir /s venv    # 如果是传统 venv 环境
# Linux/macOS
rm -rf .venv     # 如果是 uv 环境
rm -rf venv      # 如果是传统 venv 环境

# 重新创建（推荐使用 uv）
uv venv          # 使用 uv（推荐）
# 或
python -m venv venv  # 使用传统 venv

# 然后重新激活并安装依赖
```

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

### 导入错误或模块找不到

```bash
# 1. 确保虚拟环境已激活
# uv 环境
source .venv/Scripts/activate  # Windows (Git Bash)
.\.venv\Scripts\activate       # Windows (PowerShell/CMD)
source .venv/bin/activate      # Linux/macOS

# 传统 venv 环境
source venv/Scripts/activate   # Windows (Git Bash)
.\venv\Scripts\activate        # Windows (PowerShell/CMD)
source venv/bin/activate       # Linux/macOS

# 2. 清理缓存并重新安装
# Windows
rmdir /s /q __pycache__
uv sync  # 使用 uv（推荐）
# 或
pip install -e . --upgrade     # 使用传统 pip

# Linux/macOS
find . -type d -name "__pycache__" -exec rm -rf {} +
uv sync  # 使用 uv（推荐）
# 或
pip install -e . --upgrade     # 使用传统 pip
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
