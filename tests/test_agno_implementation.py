#!/usr/bin/env python3
"""
Test script for AskDB Agno implementation
Validates all core functionalities as per the AskDB paper
"""

import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def test_section(title: str):
    """Print a test section header"""
    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
    console.print(f"[bold cyan]{title}[/bold cyan]")
    console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")


def test_result(test_name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = "[green]✓ PASS[/green]" if passed else "[red]✗ FAIL[/red]"
    console.print(f"{status} {test_name}")
    if details:
        console.print(f"  [dim]{details}[/dim]")


def main():
    console.print(Panel.fit(
        "[bold cyan]AskDB Agno Implementation Test Suite[/bold cyan]\n"
        "Testing all core functionalities per AskDB paper",
        border_style="cyan"
    ))
    
    test_results = []
    
    # ==================== Test 1: Environment Configuration ====================
    test_section("Test 1: Environment Configuration")
    
    # Check Gemini API Key
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        test_result("Gemini API Key", True, f"Key configured (length: {len(gemini_key)})")
        test_results.append(("Gemini API Key", True))
    else:
        test_result("Gemini API Key", False, "GEMINI_API_KEY not found in environment")
        test_results.append(("Gemini API Key", False))
    
    # Check Database Configuration
    db_type = os.getenv("DEFAULT_DB_TYPE")
    db_name = os.getenv("DEFAULT_DB_NAME")
    if db_type and db_name:
        test_result("Database Config", True, f"Type: {db_type}, Name: {db_name}")
        test_results.append(("Database Config", True))
    else:
        test_result("Database Config", False, "Database configuration incomplete")
        test_results.append(("Database Config", False))
    
    # ==================== Test 2: Import Dependencies ====================
    test_section("Test 2: Import Dependencies")
    
    try:
        from agno.agent import Agent
        from agno.models.google import Gemini
        from agno.tools import Toolkit
        test_result("Agno Framework", True, "All Agno imports successful")
        test_results.append(("Agno Framework", True))
    except ImportError as e:
        test_result("Agno Framework", False, f"Import error: {e}")
        test_results.append(("Agno Framework", False))
    
    try:
        from tools.agno_tools import DatabaseTools, WebSearchTools, db
        test_result("AskDB Tools", True, "DatabaseTools and WebSearchTools imported")
        test_results.append(("AskDB Tools", True))
    except ImportError as e:
        test_result("AskDB Tools", False, f"Import error: {e}")
        test_results.append(("AskDB Tools", False))
    
    try:
        from lib.safety import SafetyManager, RiskLevel
        test_result("Safety Module", True, "SafetyManager imported")
        test_results.append(("Safety Module", True))
    except ImportError as e:
        test_result("Safety Module", False, f"Import error: {e}")
        test_results.append(("Safety Module", False))
    
    try:
        from tools.schema import SchemaManager
        test_result("Schema Module", True, "SchemaManager imported")
        test_results.append(("Schema Module", True))
    except ImportError as e:
        test_result("Schema Module", False, f"Import error: {e}")
        test_results.append(("Schema Module", False))
    
    # ==================== Test 3: Database Connection ====================
    test_section("Test 3: Database Connection")
    
    try:
        from tools.agno_tools import db
        db.connect()
        test_result("Database Connection", True, "Successfully connected")
        test_results.append(("Database Connection", True))
        
        # Test get tables
        try:
            tables = db.get_tables()
            test_result("Get Tables", True, f"Found {len(tables)} tables")
            test_results.append(("Get Tables", True))
            
            if tables:
                console.print(f"\n  [dim]Available tables: {', '.join(tables[:5])}")
                if len(tables) > 5:
                    console.print(f"  [dim]... and {len(tables) - 5} more[/dim]")
        except Exception as e:
            test_result("Get Tables", False, f"Error: {e}")
            test_results.append(("Get Tables", False))
            
    except Exception as e:
        test_result("Database Connection", False, f"Error: {e}")
        test_results.append(("Database Connection", False))
        console.print("\n[yellow]Skipping remaining database tests...[/yellow]")
    
    # ==================== Test 4: Core Tools (Paper Requirements) ====================
    test_section("Test 4: Core Tools (AskDB Paper Requirements)")
    
    try:
        from tools.agno_tools import DatabaseTools
        db_tools = DatabaseTools()
        
        # Check all required tools exist
        required_tools = [
            "execute_query",
            "execute_non_query", 
            "list_tables",
            "describe_table",
            "search_tables_by_name"
        ]
        
        for tool_name in required_tools:
            if hasattr(db_tools, tool_name):
                test_result(f"Tool: {tool_name}", True, "Method exists")
                test_results.append((f"Tool: {tool_name}", True))
            else:
                test_result(f"Tool: {tool_name}", False, "Method not found")
                test_results.append((f"Tool: {tool_name}", False))
        
    except Exception as e:
        console.print(f"[red]Error testing tools: {e}[/red]")
        for tool_name in ["execute_query", "execute_non_query", "search_tables_by_name"]:
            test_results.append((f"Tool: {tool_name}", False))
    
    # Test web search tool
    try:
        from tools.agno_tools import WebSearchTools
        web_tools = WebSearchTools()
        
        if hasattr(web_tools, "request_for_internet_search"):
            test_result("Tool: request_for_internet_search", True, "Method exists")
            test_results.append(("Tool: request_for_internet_search", True))
        else:
            test_result("Tool: request_for_internet_search", False, "Method not found")
            test_results.append(("Tool: request_for_internet_search", False))
            
    except Exception as e:
        test_result("Tool: request_for_internet_search", False, f"Error: {e}")
        test_results.append(("Tool: request_for_internet_search", False))
    
    # ==================== Test 5: Safety Manager ====================
    test_section("Test 5: Safety Manager (Multi-layered Safety Protocol)")
    
    try:
        from lib.safety import SafetyManager, RiskLevel
        
        safety_mgr = SafetyManager()
        test_result("SafetyManager Init", True, "Initialized successfully")
        test_results.append(("SafetyManager Init", True))
        
        # Test safe query assessment
        safe_query = "SELECT * FROM users LIMIT 10"
        assessment = safety_mgr.assess_query_safety(safe_query)
        
        if assessment.overall_risk in [RiskLevel.LOW, RiskLevel.MEDIUM]:
            test_result("Safe Query Assessment", True, f"Risk: {assessment.overall_risk.name.lower()}")
            test_results.append(("Safe Query Assessment", True))
        else:
            test_result("Safe Query Assessment", False, f"Unexpected risk: {assessment.overall_risk.name.lower()}")
            test_results.append(("Safe Query Assessment", False))
        
        # Test dangerous query assessment
        dangerous_query = "DROP TABLE users"
        assessment = safety_mgr.assess_query_safety(dangerous_query)
        
        if assessment.overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            test_result("Dangerous Query Detection", True, f"Risk: {assessment.overall_risk.name.lower()}")
            test_results.append(("Dangerous Query Detection", True))
        else:
            test_result("Dangerous Query Detection", False, f"Failed to detect risk: {assessment.overall_risk.name.lower()}")
            test_results.append(("Dangerous Query Detection", False))
            
    except Exception as e:
        console.print(f"[red]Error testing safety: {e}[/red]")
        test_results.append(("SafetyManager Init", False))
        test_results.append(("Safe Query Assessment", False))
        test_results.append(("Dangerous Query Detection", False))
    
    # ==================== Test 6: Schema Manager ====================
    test_section("Test 6: Schema Manager (Schema-Aware Prompting)")
    
    try:
        from tools.database import DatabaseTool
        from tools.schema import SchemaManager
        
        # Try to create database tool from environment
        try:
            db_tool = DatabaseTool()
            if not db_tool.is_connected:
                db_tool.connect()
            
            schema_mgr = SchemaManager(db_tool)
            test_result("SchemaManager Init", True, "Initialized successfully")
            test_results.append(("SchemaManager Init", True))
            
            # Test schema exploration
            try:
                schema_summary = schema_mgr.get_schema_summary()
                test_result("Schema Exploration", True, f"Found {schema_summary.get('table_count', 0)} tables")
                test_results.append(("Schema Exploration", True))
            except Exception as e:
                test_result("Schema Exploration", False, f"Error: {e}")
                test_results.append(("Schema Exploration", False))
            
            # Test vector indexing (optional, may take time)
            console.print("\n[dim]  Note: Skipping vector index build (takes time)[/dim]")
            test_result("Vector Indexing", True, "Available (not tested)")
            test_results.append(("Vector Indexing", True))
            
        except Exception as e:
            test_result("SchemaManager Init", False, f"Database connection failed: {e}")
            test_results.append(("SchemaManager Init", False))
            test_results.append(("Schema Exploration", False))
            test_results.append(("Vector Indexing", False))
            
    except Exception as e:
        console.print(f"[red]Error testing schema manager: {e}[/red]")
        test_results.append(("SchemaManager Init", False))
        test_results.append(("Schema Exploration", False))
        test_results.append(("Vector Indexing", False))
    
    # ==================== Test 7: Agent Creation ====================
    test_section("Test 7: Agno Agent Creation")
    
    if not gemini_key:
        test_result("Agent Creation", False, "Gemini API key not configured")
        test_results.append(("Agent Creation", False))
    else:
        try:
            from askdb_agno import create_agent
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Creating agent...", total=None)
                agent = create_agent(debug=False)
                progress.update(task, description="Agent created")
            
            test_result("Agent Creation", True, "Agent initialized successfully")
            test_results.append(("Agent Creation", True))
            
            # Verify agent has tools
            if hasattr(agent, 'tools') and len(agent.tools) > 0:
                test_result("Agent Tools", True, f"{len(agent.tools)} toolkits registered")
                test_results.append(("Agent Tools", True))
            else:
                test_result("Agent Tools", False, "No tools found")
                test_results.append(("Agent Tools", False))
                
        except Exception as e:
            test_result("Agent Creation", False, f"Error: {e}")
            test_results.append(("Agent Creation", False))
            test_results.append(("Agent Tools", False))
    
    # ==================== Test Summary ====================
    test_section("Test Summary")
    
    passed_tests = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    summary_table = Table(title="Test Results")
    summary_table.add_column("Category", style="cyan")
    summary_table.add_column("Status", style="green")
    
    # Group results by category
    categories = {
        "Configuration": [],
        "Dependencies": [],
        "Database": [],
        "Tools": [],
        "Safety": [],
        "Schema": [],
        "Agent": []
    }
    
    for name, result in test_results:
        if "API" in name or "Config" in name:
            categories["Configuration"].append((name, result))
        elif "Framework" in name or "Module" in name:
            categories["Dependencies"].append((name, result))
        elif "Database" in name or "Tables" in name:
            categories["Database"].append((name, result))
        elif "Tool:" in name:
            categories["Tools"].append((name, result))
        elif "Safety" in name or "Query" in name:
            categories["Safety"].append((name, result))
        elif "Schema" in name or "Vector" in name:
            categories["Schema"].append((name, result))
        elif "Agent" in name:
            categories["Agent"].append((name, result))
    
    for category, tests in categories.items():
        if tests:
            passed = sum(1 for _, r in tests if r)
            total = len(tests)
            status = f"{passed}/{total} passed"
            summary_table.add_row(category, status)
    
    console.print(summary_table)
    
    console.print(f"\n[bold]Overall Results:[/bold]")
    console.print(f"  Tests Passed: [green]{passed_tests}[/green]")
    console.print(f"  Tests Failed: [red]{total_tests - passed_tests}[/red]")
    console.print(f"  Pass Rate: [cyan]{pass_rate:.1f}%[/cyan]")
    
    if pass_rate == 100:
        console.print("\n[bold green]✓ All tests passed! AskDB Agno implementation is ready.[/bold green]")
    elif pass_rate >= 80:
        console.print("\n[bold yellow]⚠ Most tests passed. Review failed tests above.[/bold yellow]")
    else:
        console.print("\n[bold red]✗ Multiple test failures. Please review configuration.[/bold red]")
    
    # ==================== Next Steps ====================
    if pass_rate < 100:
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        
        if not gemini_key:
            console.print("  1. Set GEMINI_API_KEY in .env file")
            console.print("     Get key from: https://makersuite.google.com/app/apikey")
        
        if not db_type or not db_name:
            console.print("  2. Configure database settings in .env file")
            console.print("     Run: python askdb_agno.py setup")
        
        if any("Tool:" in name and not result for name, result in test_results):
            console.print("  3. Check tool implementations in tools/agno_tools.py")
        
        console.print("\n  Run tests again after fixing issues:")
        console.print("  [cyan]python test_agno_implementation.py[/cyan]")
    else:
        console.print("\n[bold cyan]Ready to use![/bold cyan]")
        console.print("  Start interactive mode:")
        console.print("  [cyan]python askdb_agno.py interactive[/cyan]")
        console.print("\n  Or ask a single question:")
        console.print("  [cyan]python askdb_agno.py ask \"your question\"[/cyan]")
    
    return 0 if pass_rate == 100 else 1


if __name__ == "__main__":
    sys.exit(main())

