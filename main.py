"""
AskDB Main Application Entry Point

This module provides the command-line interface for AskDB, enabling users to interact
with databases using natural language queries through a sophisticated LLM-powered agent.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import logging

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.markdown import Markdown

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from askdb.config import get_settings, Settings, DatabaseConfig, DatabaseType
from askdb.tools import (
    get_database_tool, get_schema_manager, get_web_search_tool,
    setup_database_tool, setup_schema_manager, setup_web_search_tool,
    initialize_tools, get_available_tools
)
from askdb.agent import create_agent, get_agent, AskDBAgent
from askdb.utils.logging import setup_logging, get_logger
from askdb.utils.helpers import format_query_result, validate_query_input


# Initialize rich console
console = Console()

# Global logger
logger = get_logger(__name__)


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Path to configuration file')
@click.option('--verbose', '-v', is_flag=True, 
              help='Enable verbose logging')
@click.option('--quiet', '-q', is_flag=True, 
              help='Suppress non-error output')
@click.pass_context
def cli(ctx, config, verbose, quiet):
    """
    AskDB - LLM-powered Natural Language Database Interface
    
    Interact with relational databases using natural language queries through
    an intelligent agent that understands your database schema and context.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Setup logging
    log_level_name = "DEBUG" if verbose else ("ERROR" if quiet else "INFO")
    setup_logging(config={"level": log_level_name})
    
    # Load settings
    try:
        settings = get_settings()
        ctx.obj['settings'] = settings
        logger.info("Settings loaded successfully")
    except Exception as e:
        console.print(f"[red]Error loading settings: {e}[/red]")
        ctx.exit(1)
    
    # Initialize tools
    try:
        tool_managers = initialize_tools(settings)
        ctx.obj['tool_managers'] = tool_managers
        logger.info("Tools initialized successfully")
    except Exception as e:
        console.print(f"[red]Error initializing tools: {e}[/red]")
        ctx.exit(1)


@cli.command()
@click.option('--database', '-d', type=str, 
              help='Database configuration name')
@click.option('--query', '-q', type=str, 
              help='Single query to execute (non-interactive mode)')
@click.option('--max-steps', type=int, default=10,
              help='Maximum reasoning steps for the agent')
@click.option('--max-retries', type=int, default=3,
              help='Maximum retry attempts for failed queries')
@click.option('--output-format', type=click.Choice(['table', 'json', 'csv']), 
              default='table', help='Output format for results')
@click.option('--save-results', type=click.Path(), 
              help='Save results to file')
@click.pass_context
def query(ctx, database, query, max_steps, max_retries, output_format, save_results):
    """
    Execute natural language queries against the database
    
    Examples:
        askdb query -d mydb -q "Show me all users from California"
        askdb query -d mydb  # Interactive mode
    """
    settings = ctx.obj['settings']
    
    try:
        # Setup database connection
        if database:
            db_tool = get_database_tool(database)
            if not db_tool:
                console.print(f"[red]Database '{database}' not found[/red]")
                ctx.exit(1)
        else:
            # Try to use default database
            db_tool = get_database_tool()
            if not db_tool:
                console.print("[yellow]No default database configured[/yellow]")
                database = Prompt.ask("Enter database configuration name")
                db_tool = get_database_tool(database)
                if not db_tool:
                    console.print(f"[red]Database '{database}' not found[/red]")
                    ctx.exit(1)
        
        # Setup schema manager
        schema_manager = setup_schema_manager(db_tool)
        
        # Setup web search tool
        web_search_tool = setup_web_search_tool()
        
        # Create agent
        agent = create_agent(
            database_tool=db_tool,
            schema_manager=schema_manager,
            web_search_tool=web_search_tool,
            settings=settings,
            max_steps=max_steps,
            max_retries=max_retries
        )
        
        console.print("[green]✓[/green] Agent initialized successfully")
        
        if query:
            # Single query mode
            _execute_single_query(agent, query, output_format, save_results)
        else:
            # Interactive mode
            _run_interactive_mode(agent, output_format, save_results)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Query execution failed")
        ctx.exit(1)


@cli.command()
@click.pass_context
def interactive(ctx):
    """Start interactive mode with the AskDB agent"""
    settings = ctx.obj['settings']
    
    console.print(Panel.fit(
        "[bold blue]AskDB Interactive Mode[/bold blue]\n"
        "Type 'help' for commands, 'exit' to quit",
        border_style="blue"
    ))
    
    try:
        # Setup agent
        agent = get_agent()
        if not agent:
            console.print("[yellow]No agent configured. Setting up default agent...[/yellow]")
            agent = _setup_default_agent(settings)
        
        _run_interactive_mode(agent)
        
    except Exception as e:
        console.print(f"[red]Error in interactive mode: {e}[/red]")
        logger.exception("Interactive mode failed")
        ctx.exit(1)


@cli.group()
def database():
    """Database configuration and management commands"""
    pass


@database.command('list')
@click.pass_context
def list_databases(ctx):
    """List all configured database connections"""
    from askdb.config.database_configs import get_db_config_manager
    
    manager = get_db_config_manager()
    configs = manager.list_configs()
    
    if not configs:
        console.print("[yellow]No database configurations found[/yellow]")
        return
    
    table = Table(title="Database Configurations")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Host", style="green")
    table.add_column("Database", style="blue")
    table.add_column("Default", style="yellow")
    
    for name, config in configs.items():
        is_default = "✓" if name == manager._default_config else ""
        table.add_row(
            name,
            str(config.db_type),
            config.host or "N/A",
            config.database,
            is_default
        )
    
    console.print(table)


@database.command('test')
@click.argument('name')
@click.pass_context
def test_database(ctx, name):
    """Test database connection"""
    try:
        db_tool = get_database_tool(name)
        if not db_tool:
            console.print(f"[red]Database '{name}' not found[/red]")
            ctx.exit(1)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Testing connection...", total=None)
            
            result = db_tool.test_connection()
            
            progress.update(task, description="Connection test complete")
        
        if result['success']:
            console.print(f"[green]✓[/green] Connection to '{name}' successful")
            console.print(f"Database: {result['database_info'].get('database_name', 'Unknown')}")
            console.print(f"Tables: {result['database_info'].get('table_count', 0)}")
        else:
            console.print(f"[red]✗[/red] Connection failed: {result['error']}")
            
    except Exception as e:
        console.print(f"[red]Error testing database: {e}[/red]")
        ctx.exit(1)


@database.command('schema')
@click.argument('name')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def show_schema(ctx, name, output_format):
    """Display database schema information"""
    try:
        db_tool = get_database_tool(name)
        if not db_tool:
            console.print(f"[red]Database '{name}' not found[/red]")
            ctx.exit(1)
        
        # Connect to database if not already connected
        if not db_tool.is_connected:
            db_tool.connect()
        
        schema_manager = setup_schema_manager(db_tool)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Exploring schema...", total=None)
            
            schema_summary = schema_manager.get_schema_summary()
            
            progress.update(task, description="Schema exploration complete")
        
        if output_format == 'json':
            console.print(json.dumps(schema_summary, indent=2))
        else:
            _display_schema_table(schema_summary)
            
    except Exception as e:
        console.print(f"[red]Error exploring schema: {e}[/red]")
        ctx.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status and configuration"""
    settings = ctx.obj['settings']
    
    # System information
    system_table = Table(title="System Status")
    system_table.add_column("Component", style="cyan")
    system_table.add_column("Status", style="green")
    system_table.add_column("Details", style="blue")
    
    # Check LLM configuration
    llm_config = settings.get_llm_config()
    llm_status = "✓ Configured" if llm_config.get('provider') else "✗ Not configured"
    system_table.add_row(
        "LLM Interface",
        llm_status,
        f"Provider: {llm_config.get('provider', 'None')}"
    )
    
    # Check database configurations
    from askdb.config.database_configs import get_db_config_manager
    db_manager = get_db_config_manager()
    db_configs = db_manager.list_configs()
    db_status = f"✓ {len(db_configs)} configured" if db_configs else "✗ None configured"
    system_table.add_row(
        "Database Connections",
        db_status,
        f"Default: {db_manager._default_config or 'None'}"
    )
    
    # Check tools
    tools = get_available_tools()
    tool_status = f"✓ {len(tools)} available"
    system_table.add_row(
        "Tools",
        tool_status,
        ", ".join(tools.keys())
    )
    
    console.print(system_table)


@cli.command()
@click.argument('query_text')
@click.option('--database', '-d', type=str, 
              help='Database configuration name')
@click.option('--explain', is_flag=True, 
              help='Show explanation of the generated SQL')
@click.pass_context
def explain(ctx, query_text, database, explain):
    """Explain how a natural language query would be processed"""
    settings = ctx.obj['settings']
    
    try:
        # Setup agent
        agent = _setup_default_agent(settings, database)
        
        console.print(f"[blue]Analyzing query:[/blue] {query_text}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing query...", total=None)
            
            # Get the reasoning process without executing
            reasoning_steps = []
            
            # Simulate the reasoning process
            prompt_context = agent.prompt_manager.create_context(
                user_query=query_text,
                database_schema=agent.schema_manager.get_schema_summary(),
                conversation_history=[]
            )
            
            # Generate schema-aware prompt
            prompt = agent.prompt_manager.generate_schema_aware_prompt(prompt_context)
            
            progress.update(task, description="Analysis complete")
        
        # Display analysis
        console.print(Panel(
            f"[bold]Query Analysis[/bold]\n\n"
            f"Original Query: {query_text}\n"
            f"Intent: {prompt_context.user_intent or 'Unknown'}\n"
            f"Complexity: {prompt_context.query_complexity or 'Unknown'}\n"
            f"Risk Level: {prompt_context.risk_level or 'Unknown'}",
            title="Query Analysis",
            border_style="blue"
        ))
        
        if explain:
            console.print("\n[bold]Generated Prompt:[/bold]")
            console.print(Syntax(prompt[:1000] + "..." if len(prompt) > 1000 else prompt, 
                               "text", theme="monokai", line_numbers=False))
        
        # Show relevant tables if found
        if prompt_context.relevant_tables:
            console.print("\n[bold]Relevant Tables:[/bold]")
            for table in prompt_context.relevant_tables:
                console.print(f"  • {table}")
        
    except Exception as e:
        console.print(f"[red]Error explaining query: {e}[/red]")
        ctx.exit(1)


def _execute_single_query(agent: AskDBAgent, query: str, output_format: str, save_results: Optional[str]):
    """Execute a single query and display results"""
    console.print(f"[blue]Executing query:[/blue] {query}")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processing query...", total=None)
        
        try:
            result = asyncio.run(agent.process_query(query))
            progress.update(task, description="Query execution complete")
        except Exception as e:
            progress.update(task, description="Query failed")
            raise e
    
    # Display results
    if result['success']:
        console.print("[green]✓[/green] Query executed successfully")
        
        if result.get('data'):
            formatted_result = format_query_result(result['data'], output_format)
            
            if output_format == 'table':
                console.print(formatted_result)
            else:
                console.print(formatted_result)
            
            # Save results if requested
            if save_results:
                with open(save_results, 'w') as f:
                    f.write(formatted_result)
                console.print(f"[green]Results saved to {save_results}[/green]")
        
        # Show execution summary
        if result.get('execution_summary'):
            _display_execution_summary(result['execution_summary'])
            
    else:
        console.print(f"[red]✗[/red] Query failed: {result.get('error', 'Unknown error')}")
        
        if result.get('execution_summary'):
            _display_execution_summary(result['execution_summary'])


def _run_interactive_mode(agent: AskDBAgent, output_format: str = 'table', save_results: Optional[str] = None):
    """Run interactive mode with the agent"""
    console.print("\n[bold green]AskDB Interactive Mode[/bold green]")
    console.print("Type your natural language queries or 'help' for commands.")
    console.print("Type 'exit' or 'quit' to leave.\n")
    
    while True:
        try:
            query = Prompt.ask("\n[bold blue]AskDB[/bold blue]")
            
            if query.lower() in ['exit', 'quit']:
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if query.lower() == 'help':
                _show_interactive_help()
                continue
            
            if query.lower() == 'clear':
                agent.reset()
                console.print("[yellow]Conversation history cleared[/yellow]")
                continue
            
            if query.lower() == 'status':
                summary = agent.get_execution_summary()
                _display_execution_summary(summary)
                continue
            
            if not query.strip():
                continue
            
            # Execute query
            console.print(f"[blue]Processing:[/blue] {query}")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("Thinking...", total=None)
                
                try:
                    result = asyncio.run(agent.process_query(query))
                    progress.update(task, description="Complete")
                except Exception as e:
                    progress.update(task, description="Failed")
                    console.print(f"[red]Error: {e}[/red]")
                    continue
            
            # Display results
            if result['success']:
                console.print("[green]✓[/green] Success!")
                
                if result.get('data'):
                    formatted_result = format_query_result(result['data'], output_format)
                    console.print(formatted_result)
                
                # Show SQL if available
                if result.get('sql_query'):
                    console.print("\n[bold]Generated SQL:[/bold]")
                    console.print(Syntax(result['sql_query'], "sql", theme="monokai", line_numbers=False))
                
            else:
                console.print(f"[red]✗[/red] {result.get('error', 'Query failed')}")
                
                # Show suggestions if available
                if result.get('suggestions'):
                    console.print("\n[yellow]Suggestions:[/yellow]")
                    for suggestion in result['suggestions']:
                        console.print(f"  • {suggestion}")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit[/yellow]")
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            logger.exception("Interactive mode error")


def _setup_default_agent(settings: Settings, database_name: Optional[str] = None) -> AskDBAgent:
    """Setup a default agent with available tools"""
    # Setup database tool
    if database_name:
        db_tool = get_database_tool(database_name)
        if not db_tool:
            raise ValueError(f"Database '{database_name}' not found")
    else:
        db_tool = get_database_tool()
        if not db_tool:
            raise ValueError("No default database configured")
    
    # Setup other tools
    schema_manager = setup_schema_manager(db_tool)
    web_search_tool = setup_web_search_tool()
    
    # Create agent
    return create_agent(
        database_tool=db_tool,
        schema_manager=schema_manager,
        web_search_tool=web_search_tool,
        settings=settings
    )


def _display_execution_summary(summary: Dict[str, Any]):
    """Display execution summary in a formatted table"""
    if not summary:
        return
    
    table = Table(title="Execution Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    # Add common metrics
    metrics = [
        ("Total Steps", str(summary.get('total_steps', 0))),
        ("Execution Time", f"{summary.get('execution_time', 0):.2f}s"),
        ("Queries Executed", str(summary.get('queries_executed', 0))),
        ("Success Rate", f"{summary.get('success_rate', 0):.1%}"),
        ("Errors", str(summary.get('errors', 0))),
    ]
    
    for metric, value in metrics:
        table.add_row(metric, value)
    
    console.print(table)


def _display_schema_table(schema_summary: Dict[str, Any]):
    """Display schema information in a formatted table"""
    if not schema_summary or 'tables' not in schema_summary:
        console.print("[yellow]No schema information available[/yellow]")
        return
    
    tables = schema_summary['tables']
    
    # Create summary table
    summary_table = Table(title=f"Database Schema: {schema_summary.get('database_name', 'Unknown')}")
    summary_table.add_column("Table", style="cyan")
    summary_table.add_column("Columns", style="magenta")
    summary_table.add_column("Rows", style="green")
    summary_table.add_column("Primary Key", style="yellow")
    summary_table.add_column("Foreign Keys", style="blue")
    
    for table_info in tables:
        summary_table.add_row(
            table_info.get('name', 'Unknown'),
            str(table_info.get('column_count', 0)),
            str(table_info.get('row_count', 'N/A')) if table_info.get('row_count') is not None else 'N/A',
            "✓" if table_info.get('has_primary_key') else "✗",
            "✓" if table_info.get('has_foreign_keys') else "✗"
        )
    
    console.print(summary_table)


def _show_interactive_help():
    """Show help for interactive mode"""
    help_text = """
[bold]Interactive Mode Commands:[/bold]

  [cyan]help[/cyan]     - Show this help message
  [cyan]clear[/cyan]    - Clear conversation history
  [cyan]status[/cyan]   - Show execution summary
  [cyan]exit[/cyan]     - Exit interactive mode

[bold]Query Examples:[/bold]

  • "Show me all users from California"
  • "What are the top 5 products by sales?"
  • "Count orders by customer"
  • "Find employees with salary > 50000"

[bold]Tips:[/bold]

  • Be specific about what you want to see
  • Use natural language - no need to write SQL
  • The agent will ask for clarification if needed
  • Complex queries may take longer to process
    """
    
    console.print(Panel(help_text, title="Interactive Mode Help", border_style="blue"))


def main():
    """Main entry point for the CLI application"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        logger.exception("Fatal error in main")
        sys.exit(1)


if __name__ == '__main__':
    main()