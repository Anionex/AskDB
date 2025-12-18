#!/usr/bin/env python3
"""
AskDB with Agno Framework - 完整版
Natural language database interface using Agno framework.
Implements the complete AskDB architecture with ReAct framework, 
safety protocols, and semantic schema search.
"""

import os
import sys
import json
import logging
from typing import Optional
from pathlib import Path

# 注册opengauss方言
dialects_path = Path(__file__).parent / "dialects"
sys.path.insert(0, str(dialects_path))
from dialects.opengauss_dialect import OpenGaussDialect

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.markdown import Markdown

from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.exa import ExaTools
from agno.models.google import Gemini
from agno.db.sqlite import SqliteDb

# Import our custom tools
from tools.agno_tools import DatabaseTools, WebSearchTools, db
TOOLS_AVAILABLE = True

console = Console()
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
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    model_id = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Setup session storage for conversation history
    storage_db = None
    if enable_memory:
        # Create SQLite database for session storage
        db_path = os.path.join(os.path.dirname(__file__), "data", "askdb_sessions.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        storage_db = SqliteDb(db_file=db_path)
        logger.info(f"Session storage enabled: {db_path}")
    
    # Connect to database and get table info
    try:
        db.connect()
        tables = db.get_tables()
        tables_info = f"\n\nAvailable database tables: {', '.join(tables)}"
        
        # Get brief schema info
        schema_details = []
        for table in tables[:5]:  # Show details for first 5 tables
            try:
                info = db.get_table_info(table)
                columns = [col['name'] for col in info['columns'][:5]]
                schema_details.append(f"  - {table}: {', '.join(columns)}")
            except:
                pass
        
        if schema_details:
            tables_info += "\n\nTable schema preview:\n" + "\n".join(schema_details)
            
    except Exception as e:
        console.print(f"[yellow]Warning: Could not connect to database: {e}[/yellow]")
        tables_info = "\n\nDatabase connection not available. Please check your configuration."
    
    # Create comprehensive instructions following AskDB paper
    instructions = f"""你是 AskDB —— 一个智能数据库助手，可以帮助用户用自然语言查询和管理数据库。

## 你的能力

你拥有强大的工具，可以实现：

1. **数据查询** - 执行 SELECT 语句获取信息
2. **数据修改** - 执行 INSERT、UPDATE、DELETE 操作（带安全检查）
3. **结构探索** - 搜索表结构和理解数据库架构
4. **外部知识** - 在需要时搜索互联网信息

## 查询处理规范

### 1. 理解用户意图
- 仔细分析用户想要实现的目标
- 如果意图不清楚，主动提出澄清问题
- 使用 search_tables_by_name 工具定位相关表

### 2. 模式/结构探索
- 当用户提到概念（如"客户"、"订单"）时，用 search_tables_by_name 找到相关表
  * 该工具支持用语义相似度把概念映射到表名
  * 例如："customer data" 会匹配到"users"、"clients"、"accounts"等表
- 编写 SQL 前，一定要用 describe_table 查明字段名和类型
- 注意表之间的关联关系（如外键）

### 3. SQL 生成
- 编写简洁、高效的 SQL 查询
- 多表查询时请用正确的 JOIN 语法
- 对大查询结果集加入 LIMIT 限制
- 合理使用别名提升可读性

### 4. 安全与风险管理
- 读取操作（SELECT）风险低，可直接执行
- 写入操作（INSERT、UPDATE、DELETE、DROP）为高风险操作：
  * 系统会自动向用户确认
  * 在执行前清晰说明将要修改的内容
  * 未经用户明确批准，绝不执行破坏性操作

### 5. 错误处理与调试
- 查询失败时，分析报错信息
- 常见问题包括：
  * 字段名错误（用 describe_table 核查列名）
  * 表名错误（用 search_tables_by_name 查找正确表名）
  * 语法问题（结合当前数据库类型复查 SQL 语法）
- 自动尝试修正并重试

### 6. 响应格式
- 总是提供清晰自然语言的说明
- 展示执行过的 SQL 语句
- 用有条理的方式展示结果
- 若结果集较大，请总结关键内容，并用自然语言解释查询逻辑
- 对于事实性问题，直接给出准确答案，不解释

请牢记：你要做到助人为本，精准且安全。始终以数据安全与用户意图为最高原则。"""

    # 创建工具列表
    tools_list = [
        DuckDuckGoTools(),
        ExaTools(api_key="058a2ec7-6142-493d-a8bd-40db70742d23"),
    ]
    
    # 添加工具
    if TOOLS_AVAILABLE:
        try:
            # 添加数据库工具
            db_tools = DatabaseTools()
            tools_list.append(db_tools)
            
            # 添加Web搜索工具
            web_tools = WebSearchTools()
            tools_list.append(web_tools)
            
        except Exception as e:
            logger.error(f"❌ 添加工具失败: {e}")
    
    # Create agent with tools and conversation history
    agent_params = {
        "name": "AskDB",
        "model": Gemini(id=model_id, api_key=api_key),
        "tools": tools_list,  
        "instructions": instructions,
        "markdown": True,
        "debug_mode": debug,
        # "show_tool_calls": True,  # 在 debug 模式下显示工具调用
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


@click.group()
def cli():
    """AskDB - Natural Language Database Interface powered by Agno + Gemini"""
    pass


@cli.command()
@click.option('--debug', '-d', is_flag=True, help='Enable debug mode')
@click.option('--no-memory', is_flag=True, help='Disable conversation memory')
@click.option('--session-id', '-s', help='Session ID for conversation history')
def interactive(debug, no_memory, session_id):
    """Start interactive chat mode with conversation memory"""
    setup_logging(debug)
    
    # Generate session ID if not provided
    if not session_id and not no_memory:
        from datetime import datetime
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    console.print(Panel.fit(
        "[bold cyan]AskDB Interactive Mode[/bold cyan]\n"
        "[dim]Powered by Agno + Gemini 2.0[/dim]\n\n"
        "Ask questions about your database in natural language.\n"
        "Type 'exit' or 'quit' to leave.\n"
        "Type 'help' for usage tips."
        + (f"\n[dim]💾 Session: {session_id}[/dim]" if session_id else ""),
        border_style="cyan"
    ))
    
    try:
        agent = create_agent(debug, enable_memory=not no_memory, session_id=session_id)
        console.print("[green]✓ Agent ready[/green]")
        
        # Check if memory is actually enabled
        has_storage = hasattr(agent, 'db') and agent.db is not None
        if not no_memory and has_storage:
            console.print("[dim]💾 Conversation history enabled - I'll remember our chat[/dim]")
            console.print(f"[dim]📂 Session ID: {session_id}[/dim]\n")
        else:
            console.print("[dim]Each query is independent (no history)[/dim]\n")
        
        while True:
            try:
                query = Prompt.ask("\n[bold cyan]You[/bold cyan]")
                
                if query.lower() in ['exit', 'quit', 'q']:
                    console.print("\n[yellow]Goodbye! 👋[/yellow]")
                    break
                
                if query.lower() == 'help':
                    show_help()
                    continue
                
                if query.lower() == 'tables':
                    show_tables()
                    continue
                
                if query.lower() in ['clear', 'reset', 'new']:
                    # Start a new session by creating a new agent
                    from datetime import datetime
                    new_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    agent = create_agent(debug, enable_memory=not no_memory, session_id=new_session_id)
                    console.print(f"[yellow]🔄 Started new session: {new_session_id}[/yellow]")
                    continue
                
                if not query.strip():
                    continue
                
                console.print()
                
                # Print response with tool calls visible
                with console.status("[bold cyan]思考中...[/bold cyan]") as status:
                    agent.print_response(query, stream=True)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Type 'exit' to quit[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                if debug:
                    import traceback
                    console.print(traceback.format_exc())
                
    except Exception as e:
        console.print(f"[red]Failed to start: {e}[/red]")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument('question')
@click.option('--debug', '-d', is_flag=True, help='Enable debug mode')
def ask(question, debug):
    """Ask a single question about your database"""
    setup_logging(debug)
    
    try:
        agent = create_agent(debug)
        agent.print_response(question, stream=True)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.option('--debug', '-d', is_flag=True, help='Enable debug mode')
def status(debug):
    """Show database connection status and configuration"""
    setup_logging(debug)
    
    console.print("\n[bold]AskDB Status[/bold]\n")
    
    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        console.print(f"  Gemini API: [green]✓ Configured[/green]")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        console.print(f"  Model: [cyan]{model}[/cyan]")
    else:
        console.print(f"  Gemini API: [red]✗ Not configured[/red]")
        console.print(f"  [yellow]Set GEMINI_API_KEY in .env file[/yellow]")
    
    # Check database
    db_type = os.getenv("DEFAULT_DB_TYPE", "not set")
    db_name = os.getenv("DEFAULT_DB_NAME", "not set")
    db_host = os.getenv("DEFAULT_DB_HOST", "not set")
    
    console.print(f"\n  Database Type: [cyan]{db_type}[/cyan]")
    console.print(f"  Database Name: [cyan]{db_name}[/cyan]")
    console.print(f"  Host: [cyan]{db_host}[/cyan]")
    
    # Test connection
    try:
        db.connect()
        tables = db.get_tables()
        console.print(f"  Connection: [green]✓ Connected[/green]")
        console.print(f"  Tables: [green]{len(tables)} found[/green]")
        
        if tables:
            console.print(f"\n  [bold]Available Tables:[/bold]")
            for i, table in enumerate(tables[:10], 1):
                console.print(f"    {i}. {table}")
            if len(tables) > 10:
                console.print(f"    ... and {len(tables) - 10} more")
    except Exception as e:
        console.print(f"  Connection: [red]✗ Failed[/red]")
        console.print(f"  Error: [red]{e}[/red]")


@cli.command()
@click.argument('table_name')
@click.option('--debug', '-d', is_flag=True, help='Enable debug mode')
def describe(table_name, debug):
    """Show detailed information about a table"""
    setup_logging(debug)
    
    try:
        db.connect()
        table_info = db.get_table_info(table_name)
        
        console.print(f"\n[bold cyan]Table: {table_name}[/bold cyan]\n")
        
        # Create columns table
        table = Table(title="Columns")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Nullable", style="yellow")
        table.add_column("Key", style="green")
        
        for col in table_info['columns']:
            key_type = ""
            if col.get('primary_key'):
                key_type = "PK"
            
            table.add_row(
                col['name'],
                col['type'],
                "✓" if col['nullable'] else "✗",
                key_type
            )
        
        console.print(table)
        
        # Show foreign keys
        if table_info.get('foreign_keys'):
            console.print(f"\n[bold]Foreign Keys:[/bold]")
            for fk in table_info['foreign_keys']:
                console.print(f"  {', '.join(fk['columns'])} → {fk['referred_table']}.{', '.join(fk['referred_columns'])}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def show_help():
    """Show help information"""
    help_text = """
[bold]Interactive Mode Commands:[/bold]

  [cyan]help[/cyan]     - Show this help message
  [cyan]tables[/cyan]   - List all database tables
  [cyan]new[/cyan]      - Start a new conversation session
  [cyan]clear[/cyan]    - Start a new conversation session (alias for 'new')
  [cyan]exit[/cyan]     - Exit interactive mode

[bold]Query Examples:[/bold]

  • "Show me all users from California"
  • "What are the top 5 products by sales?"
  • "Count orders by status"
  • "Find employees with salary > 50000"
  • "Which table contains customer information?"

[bold]Advanced Features:[/bold]

  • The agent automatically searches for relevant tables
  • High-risk operations require confirmation
  • Failed queries are automatically debugged
  • You can ask follow-up questions

[bold]Tips:[/bold]

  • Be specific about what you want to see
  • Use natural language - no need to write SQL
  • The agent will ask for clarification if needed
  • Complex queries may take longer to process
    """
    
    console.print(Panel(help_text, title="Help", border_style="blue"))


def show_tables():
    """Show all tables in the database"""
    try:
        db.connect()
        tables = db.get_tables()
        
        console.print(f"\n[bold]Database Tables ({len(tables)}):[/bold]\n")
        
        for i, table in enumerate(tables, 1):
            console.print(f"  {i}. {table}")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def setup():
    """Interactive setup wizard for configuring AskDB"""
    console.print(Panel.fit(
        "[bold cyan]AskDB Setup Wizard[/bold cyan]\n"
        "This will help you configure AskDB",
        border_style="cyan"
    ))
    
    # Check for .env file
    env_file = Path(".env")
    if env_file.exists():
        console.print("\n[yellow]Found existing .env file[/yellow]")
        if not click.confirm("Overwrite?"):
            console.print("[yellow]Setup cancelled[/yellow]")
            return
    
    # Gemini API Key
    console.print("\n[bold]1. Gemini API Configuration[/bold]")
    console.print("Get your API key from: https://makersuite.google.com/app/apikey")
    gemini_key = click.prompt("Gemini API Key", hide_input=True)
    
    # Database configuration
    console.print("\n[bold]2. Database Configuration[/bold]")
    db_type = click.prompt(
        "Database Type",
        type=click.Choice(["mysql", "postgresql", "sqlite"]),
        default="mysql"
    )
    
    if db_type == "sqlite":
        db_path = click.prompt("Database file path", default="data/askdb.db")
        env_content = f"""# Gemini API Configuration
GEMINI_API_KEY={gemini_key}
GEMINI_MODEL=gemini-2.5-flash

# Database Configuration
DEFAULT_DB_TYPE=sqlite
DEFAULT_DB_NAME={db_path}
"""
    else:
        db_host = click.prompt("Database Host", default="localhost")
        db_port = click.prompt("Database Port", default="3306" if db_type == "mysql" else "5432")
        db_name = click.prompt("Database Name")
        db_user = click.prompt("Database User", default="root")
        db_pass = click.prompt("Database Password", hide_input=True)
        
        env_content = f"""# Gemini API Configuration
GEMINI_API_KEY={gemini_key}
GEMINI_MODEL=gemini-2.5-flash

# Database Configuration
DEFAULT_DB_TYPE={db_type}
DEFAULT_DB_HOST={db_host}
DEFAULT_DB_PORT={db_port}
DEFAULT_DB_NAME={db_name}
DEFAULT_DB_USER={db_user}
DEFAULT_DB_PASSWORD={db_pass}
"""
    
    # Write .env file
    with open(".env", "w") as f:
        f.write(env_content)
    
    console.print("\n[green]✓ Configuration saved to .env[/green]")
    
    # Test connection
    console.print("\n[bold]Testing connection...[/bold]")
    load_dotenv(override=True)
    
    try:
        db.connect()
        tables = db.get_tables()
        console.print(f"[green]✓ Successfully connected! Found {len(tables)} tables.[/green]")
    except Exception as e:
        console.print(f"[red]✗ Connection failed: {e}[/red]")
        console.print("[yellow]Please check your configuration and try again.[/yellow]")
        return
    
    console.print("\n[green]Setup complete! You can now use AskDB.[/green]")
    console.print("Run: [cyan]python askdb_agno.py interactive[/cyan]")


if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    cli()