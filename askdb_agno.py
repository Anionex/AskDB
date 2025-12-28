#!/usr/bin/env python3
"""
AskDB with Agno Framework - Core Module
Natural language database interface using Agno framework.
Implements the complete AskDB architecture with ReAct framework, 
safety protocols, and semantic schema search.
"""

import os
import sys
import logging
from pathlib import Path

# 注册opengauss方言
dialects_path = Path(__file__).parent / "dialects"
sys.path.insert(0, str(dialects_path))
from dialects.opengauss_dialect import OpenGaussDialect

# Load environment variables
from dotenv import load_dotenv
load_dotenv(override=True)

from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.exa import ExaTools
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

# Import our custom tools
from tools.agno_tools import DatabaseTools, WebSearchTools, db
from tools.enhanced_tools import EnhancedDatabaseTools
TOOLS_AVAILABLE = True

logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/askdb.log'),
            logging.StreamHandler()
        ]
    )
    # Suppress verbose logs from libraries
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)


def create_agent(debug: bool = False, enable_memory: bool = True, session_id: str = None) -> Agent:
    """Create the AskDB Agno Agent with all tools and instructions.
    
    Args:
        debug: Enable debug mode
        enable_memory: Enable conversation history (requires database storage)
        session_id: Session ID for conversation history (auto-generated if not provided)
    """
    
    # Get LLM provider configuration
    llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    # Initialize model based on provider
    if llm_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        model_id = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_BASE_URL")
        
        # Create OpenAI model with optional base_url
        model_kwargs = {
            "id": model_id,
            "api_key": api_key
        }
        if base_url:
            model_kwargs["base_url"] = base_url
            logger.info(f"Using OpenAI-compatible API at: {base_url}")
        
        model = OpenAIChat(**model_kwargs)
        logger.info(f"Using OpenAI model: {model_id}")
    else:
        # Default to Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        model_id = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        model = Gemini(id=model_id, api_key=api_key)
        logger.info(f"Using Gemini model: {model_id}")
    
    # Setup session storage for conversation history
    storage_db = None
    if enable_memory:
        # Create SQLite database for session storage
        db_path = os.path.join(os.path.dirname(__file__), "data", "askdb_sessions.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        storage_db = SqliteDb(db_file=db_path)
        logger.info(f"Session storage enabled: {db_path}")
    
    # Connect to database and get table info
    # 注释掉：不在 prompt 中放入表信息，让模型通过工具动态获取
    # try:
    #     db.connect()
    #     tables = db.get_tables()
    #     tables_info = f"\n\nAvailable database tables: {', '.join(tables)}"
    #     
    #     # Get brief schema info
    #     schema_details = []
    #     for table in tables[:5]:  # Show details for first 5 tables
    #         try:
    #             info = db.get_table_info(table)
    #             columns = [col['name'] for col in info['columns'][:5]]
    #             schema_details.append(f"  - {table}: {', '.join(columns)}")
    #         except:
    #             pass
    #     
    #     if schema_details:
    #         tables_info += "\n\nTable schema preview:\n" + "\n".join(schema_details)
    #         
    # except Exception as e:
    #     logger.warning(f"Could not connect to database: {e}")
    #     tables_info = "\n\nDatabase connection not available. Please check your configuration."
    
    # 不在 prompt 中放入表信息，模型需要时会调用 list_tables 工具
    tables_info = ""
    
    # Create comprehensive instructions following AskDB paper
    instructions = f"""你是 AskDB —— 一个智能数据库助手，使用向量检索和语义理解帮助用户查询和管理数据库。

## 你的能力

你拥有强大的工具，可以实现：

1. **语义检索** - 使用向量检索找到与用户问题最相关的表和字段
2. **数据查询** - 执行 SELECT 语句获取信息（必须带解释）
3. **数据修改** - 执行 INSERT、UPDATE、DELETE 操作（必须带解释和影响评估）
4. **结构探索** - 获取表的完整 DDL 信息
5. **业务术语理解** - 理解业务术语（如 GMV、活跃用户）并映射到数据库表
6. **外部知识** - 在需要时搜索互联网信息

## 查询处理标准流程（必须遵循！）

### 步骤 1: 语义检索相关表和字段
**首先**使用 `semantic_search_schema` 工具，将用户的自然语言查询转换为向量，检索最相关的：
- 数据库表
- 数据库列
- 业务术语定义

示例：
用户问："上个月新客户的消费金额"
→ 调用 semantic_search_schema("新客户 消费金额 上个月")
→ 返回相关表：customers, orders, order_items
→ 返回相关列：customer_id, created_at, amount
→ 返回业务术语：可能包含"新客户"的定义

### 步骤 2: 获取完整表结构
基于步骤 1 找到的相关表，使用 `get_table_ddl` 获取完整的表结构：
- 所有列及其数据类型
- 主键信息
- 外键关系
- 索引信息

示例：
→ 调用 get_table_ddl("customers,orders,order_items")
→ 获取完整的列定义、主外键关系

### 步骤 3: 生成 SQL 并提供解释
**重要**：执行任何 SQL 都必须提供清晰的解释！

对于 SELECT 查询，使用 `execute_query_with_explanation`:
- 第一个参数：SQL 语句
- 第二个参数：**必须**提供解释，说明查询在做什么

示例：
```python
execute_query_with_explanation(
    sql_query="SELECT COUNT(DISTINCT customer_id) FROM orders WHERE created_at >= '2024-01-01'",
    explanation="查询2024年1月以来有过订单的不同客户数量，用于统计新客户数"
)
```

对于修改操作（INSERT/UPDATE/DELETE），使用 `execute_non_query_with_explanation`:
- 第一个参数：SQL 语句
- 第二个参数：**必须**提供详细解释
- 第三个参数：**必须**提供预期影响说明

示例：
```python
execute_non_query_with_explanation(
    sql_statement="UPDATE users SET status='inactive' WHERE last_login < '2023-01-01'",
    explanation="将2023年前未登录的用户标记为不活跃状态",
    expected_impact="预计影响约150个用户账户"
)
```

## 重要规则

### 关于解释的要求
1. **每个 SQL 都必须有解释** - 这不是可选的！
2. 解释要清晰、具体，让非技术用户也能理解
3. 对于事实性查询（如"有多少用户？"），直接给出答案，然后展示 SQL 和解释
4. 对于复杂查询，解释应该包括：
   - 查询的目的
   - 使用了哪些表
   - JOIN 的逻辑
   - 过滤条件的含义

### 关于危险操作
1. INSERT/UPDATE/DELETE 需要用户确认
2. 必须提供：
   - 详细解释（≥15字符）
   - 预期影响（≥10字符，如"将修改约100条记录"）
3. 系统会自动触发前端确认对话框
4. 用户拒绝时，不要重复尝试，而是询问用户意图

### 关于业务术语
- 如果语义检索返回了业务术语，优先使用其定义的公式
- 例如："GMV" → 使用定义中的 "sum(sales_amount + shipping_fee - discount)"

### 错误处理
- 如果语义检索没有找到相关表，使用 `list_all_tables` 查看所有表
- 如果 SQL 执行失败，分析错误信息并重试
- 常见错误：列名拼写、JOIN 条件错误、聚合函数使用不当

## 响应格式要求

给用户的最终回复应该包含：
1. **自然语言答案**（如果是事实性问题）
2. **执行的 SQL 语句**（代码块格式）
3. **SQL 解释**（系统会在前端显示）
4. **查询结果**（格式化的表格或列表）
5. **进一步建议**（如果适用）

请始终记住：安全第一，解释清晰，用户体验优先！"""

    # 创建工具列表
    tools_list = [
        DuckDuckGoTools(),
        ExaTools(api_key="058a2ec7-6142-493d-a8bd-40db70742d23"),
    ]
    
    # 添加工具
    if TOOLS_AVAILABLE:
        try:
            # 添加增强版数据库工具（集成向量检索）
            enhanced_db_tools = EnhancedDatabaseTools()
            tools_list.append(enhanced_db_tools)
            
            # 添加Web搜索工具
            web_tools = WebSearchTools()
            tools_list.append(web_tools)
            
            logger.info("✅ Enhanced database tools with vector retrieval loaded")
            
        except Exception as e:
            logger.error(f"❌ 添加工具失败: {e}")
    
    # Create agent with tools and conversation history
    agent_params = {
        "name": "AskDB",
        "model": model,
        "tools": tools_list,  
        "instructions": instructions,
        "markdown": True,
        "debug_mode": debug,
    }

    # Add session storage and history features if enabled
    if enable_memory and storage_db:
        agent_params.update({
            "db": storage_db,  # Required for all history features
            "add_history_to_context": True,  # Automatically add recent conversation to context
            "num_history_runs": 5,  # Include last 5 conversation turns
            "read_chat_history": False,  # Give agent tool to search full history
        })
        if session_id:
            agent_params["session_id"] = session_id
    
    agent = Agent(**agent_params)
    
    return agent


if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Initialize logging
    setup_logging()
    
    logger.info("AskDB Core Module - Use via Web API")
    logger.info("Run: python start_backend.py")
