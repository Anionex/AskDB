#!/usr/bin/env python3
"""
AskDB with Agno Framework

A natural language database interface using Agno framework.
Implements the complete AskDB architecture with ReAct framework, 
safety protocols, and semantic schema search.
"""

import os
import sys
import json
import logging
from typing import Optional
from pathlib import Path

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
from agno.models.google import Gemini
from agno.db.sqlite import SqliteDb

# Import our custom tools
from tools.agno_tools import DatabaseTools, WebSearchTools, db

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
    instructions = f"""You are AskDB, an intelligent database assistant that helps users query and manage databases using natural language.

## Your Capabilities

You have access to powerful tools that enable you to:

1. **Query Data** - Execute SELECT queries to retrieve information
2. **Modify Data** - Execute INSERT, UPDATE, DELETE operations (with safety checks)
3. **Explore Schema** - Search for tables and understand database structure
4. **External Knowledge** - Search the internet for information when needed

## Database Context
{tables_info}

## Guidelines for Query Processing

### 1. Understanding User Intent
- Carefully analyze what the user wants to achieve
- If the intent is unclear, ask clarifying questions
- Identify relevant tables using the search_tables_by_name tool

### 2. Schema Exploration
- When user mentions concepts (like "customers", "orders"), use search_tables_by_name to find relevant tables
- Always use describe_table to understand column names and types before writing SQL
- Look for relationships between tables (foreign keys)

### 3. SQL Generation
- Write clean, efficient SQL queries
- Use proper JOIN syntax when accessing multiple tables
- Add LIMIT clauses for large result sets
- Use meaningful aliases for readability

### 4. Safety and Risk Management
- READ operations (SELECT) are low-risk and execute directly
- WRITE operations (INSERT, UPDATE, DELETE, DROP) are high-risk:
  * The system will automatically ask for user confirmation
  * Clearly explain what will be modified before execution
  * Never execute destructive operations without explicit user approval

### 5. Error Handling and Debugging
- If a query fails, analyze the error message
- Common issues:
  * Column names (check actual column names with describe_table)
  * Table names (use search_tables_by_name to find correct names)
  * Syntax errors (review SQL syntax for the specific database type)
- Automatically retry with corrections

### 6. Response Format
- Always provide clear, natural language explanations
- Show the SQL query you executed
- Present results in an organized manner
- If results are large, summarize key findings

### 7. When to Use Web Search
- Use request_for_internet_search when:
  * User asks about concepts not in the database
  * Need current information (dates, events, definitions)
  * Require external knowledge to interpret queries
  * Need to understand domain-specific terminology

## Example Workflows

**Simple Query:**
User: "Show me all customers from California"
1. Use search_tables_by_name("customers")
2. Use describe_table to see columns
3. Execute: SELECT * FROM customers WHERE state = 'CA' LIMIT 100
4. Present results clearly

**Complex Query:**
User: "What are the top 5 products by revenue?"
1. Search for relevant tables (products, orders, sales)
2. Describe tables to find column names
3. Build JOIN query with aggregation
4. Execute and explain results

**Data Modification:**
User: "Delete all orders from 2020"
1. Explain what will happen
2. System asks for confirmation (automatic)
3. Execute only if user confirms
4. Report results

Remember: You are helpful, precise, and safe. Always prioritize data integrity and user intent."""

    # Create agent with tools and conversation history
    agent_params = {
        "name": "AskDB",
        "model": Gemini(id=model_id, api_key=api_key),
        "tools": [DatabaseTools(), WebSearchTools()],
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
        console.print("[green]✓ Agent ready![/green]")
        
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
        if not Prompt.ask("Overwrite?", choices=["y", "n"], default="n") == "y":
            console.print("[yellow]Setup cancelled[/yellow]")
            return
    
    # Gemini API Key
    console.print("\n[bold]1. Gemini API Configuration[/bold]")
    console.print("Get your API key from: https://makersuite.google.com/app/apikey")
    gemini_key = Prompt.ask("Gemini API Key", password=True)
    
    # Database configuration
    console.print("\n[bold]2. Database Configuration[/bold]")
    db_type = Prompt.ask(
        "Database Type",
        choices=["mysql", "postgresql", "sqlite"],
        default="mysql"
    )
    
    if db_type == "sqlite":
        db_path = Prompt.ask("Database file path", default="data/askdb.db")
        env_content = f"""# Gemini API Configuration
GEMINI_API_KEY={gemini_key}
GEMINI_MODEL=gemini-2.5-flash

# Database Configuration
DEFAULT_DB_TYPE=sqlite
DEFAULT_DB_NAME={db_path}
"""
    else:
        db_host = Prompt.ask("Database Host", default="localhost")
        db_port = Prompt.ask("Database Port", default="3306" if db_type == "mysql" else "5432")
        db_name = Prompt.ask("Database Name")
        db_user = Prompt.ask("Database User", default="root")
        db_pass = Prompt.ask("Database Password", password=True)
        
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

