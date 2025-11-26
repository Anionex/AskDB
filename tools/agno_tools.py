"""
AskDB Agno Tools - Database toolkit for Agno Agent

This module provides the database tools for the Agno framework,
implementing the four core tools described in the AskDB paper:
1. execute_query - Execute SELECT statements
2. execute_non_query - Execute data modification statements
3. search_tables_by_name - Semantic table search
4. request_for_internet_search - Web search
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List

from agno.tools import Toolkit
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine

from lib.safety import SafetyManager, RiskLevel
from tools.schema import SchemaManager
from tools.web_search import WebSearchTool
from rich.prompt import Confirm
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


class DatabaseConnection:
    """Simple database connection manager."""
    
    def __init__(self):
        self.engine: Optional[Engine] = None
        self._connected = False
        self.safety_manager = SafetyManager()
        self.schema_manager: Optional[SchemaManager] = None
    
    def connect(self) -> bool:
        """Connect to database using environment variables."""
        db_type = os.getenv("DEFAULT_DB_TYPE", "mysql")
        host = os.getenv("DEFAULT_DB_HOST", "localhost")
        port = os.getenv("DEFAULT_DB_PORT", "3306")
        database = os.getenv("DEFAULT_DB_NAME", "")
        user = os.getenv("DEFAULT_DB_USER", "root")
        password = os.getenv("DEFAULT_DB_PASSWORD", "")
        
        if db_type == "mysql":
            url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        elif db_type == "postgresql":
            url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        elif db_type == "sqlite":
            url = f"sqlite:///{database}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        try:
            self.engine = create_engine(url)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self._connected = True
            logger.info(f"Connected to {db_type} database: {database}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._connected = False
            raise
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self.engine is not None
    
    def execute_query(self, sql: str, allow_modifications: bool = False) -> dict:
        """Execute SQL query with safety checks."""
        if not self.is_connected:
            self.connect()
        
        # Safety assessment
        safety_result = self.safety_manager.assess_query_safety(sql)
        
        # Check if query modifies data
        is_modification = any(keyword in sql.upper() for keyword in 
                            ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"])
        
        # High-risk queries require confirmation
        if safety_result.overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL] or is_modification:
            if not allow_modifications:
                console.print(f"\n[yellow]⚠️  High-risk operation detected![/yellow]")
                console.print(f"[yellow]Risk Level: {safety_result.overall_risk.name.lower()}[/yellow]")
                console.print(f"[yellow]SQL: {sql}[/yellow]")
                
                if not Confirm.ask("Do you want to proceed?"):
                    return {
                        "success": False,
                        "error": "Operation cancelled by user",
                        "safety_blocked": True
                    }
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                
                if result.returns_rows:
                    columns = list(result.keys())
                    rows = result.fetchall()
                    data = [dict(zip(columns, row)) for row in rows]
                    return {
                        "success": True,
                        "data": data,
                        "row_count": len(data),
                        "sql": sql
                    }
                else:
                    conn.commit()
                    return {
                        "success": True,
                        "data": [],
                        "row_count": result.rowcount,
                        "sql": sql
                    }
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "sql": sql
            }
    
    def get_tables(self) -> list:
        """Get list of tables."""
        if not self.is_connected:
            self.connect()
        inspector = inspect(self.engine)
        return inspector.get_table_names()
    
    def get_table_info(self, table_name: str) -> dict:
        """Get table schema info."""
        if not self.is_connected:
            self.connect()
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_name)
        pk = inspector.get_pk_constraint(table_name)
        fks = inspector.get_foreign_keys(table_name)
        
        return {
            "table_name": table_name,
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "primary_key": col["name"] in pk.get("constrained_columns", [])
                }
                for col in columns
            ],
            "primary_key": pk.get("constrained_columns", []) if pk else [],
            "foreign_keys": [
                {
                    "columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"]
                }
                for fk in fks
            ]
        }


# Global database connection
db = DatabaseConnection()


class DatabaseTools(Toolkit):
    """Database toolkit for Agno Agent - implements core AskDB tools."""
    
    def __init__(self):
        super().__init__(
            name="database",
            tools=[
                self.execute_query,
                self.execute_non_query,
                self.list_tables,
                self.describe_table,
                self.search_tables_by_name,
            ]
        )
        self.safety_manager = db.safety_manager
    
    def execute_query(self, sql_query: str) -> str:
        """
        Execute a SELECT SQL query against the database.
        Use this for read-only data retrieval operations.
        
        Args:
            sql_query: The SELECT SQL statement to execute.
        
        Returns:
            JSON string with query results or error.
        """
        try:
            result = db.execute_query(sql_query, allow_modifications=False)
            if result["success"]:
                data = result["data"]
                if len(data) > 15:
                    data = data[:15]
                    return json.dumps({
                        "success": True,
                        "data": data,
                        "total_rows": result["row_count"],
                        "note": f"Showing 15 of {result['row_count']} rows"
                    }, ensure_ascii=False, default=str, indent=2)
                return json.dumps({
                    "success": True,
                    "data": data,
                    "row_count": result["row_count"]
                }, ensure_ascii=False, default=str, indent=2)
            return json.dumps({"success": False, "error": result.get("error", "Unknown error")})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def execute_non_query(self, sql_statement: str) -> str:
        """
        Execute a data modification SQL statement (INSERT, UPDATE, DELETE, etc.).
        This requires user confirmation for safety.
        
        Args:
            sql_statement: The SQL statement that modifies data.
        
        Returns:
            JSON string with execution results or error.
        """
        try:
            # This will trigger safety checks and user confirmation
            result = db.execute_query(sql_statement, allow_modifications=True)
            
            if result.get("safety_blocked"):
                return json.dumps({
                    "success": False,
                    "error": "Operation blocked by user or safety system",
                    "blocked": True
                })
            
            if result["success"]:
                return json.dumps({
                    "success": True,
                    "rows_affected": result.get("row_count", 0),
                    "message": "Statement executed successfully"
                }, ensure_ascii=False, indent=2)
            return json.dumps({"success": False, "error": result.get("error", "Unknown error")})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def list_tables(self) -> str:
        """
        Get a list of all tables in the database.
        
        Returns:
            JSON string with list of table names.
        """
        try:
            tables = db.get_tables()
            return json.dumps({
                "success": True,
                "tables": tables,
                "count": len(tables)
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def describe_table(self, table_name: str) -> str:
        """
        Get detailed schema information about a specific table.
        
        Args:
            table_name: Name of the table to describe.
        
        Returns:
            JSON string with table schema information.
        """
        try:
            table_info = db.get_table_info(table_name)
            return json.dumps({
                "success": True,
                "table_info": table_info
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def search_tables_by_name(self, search_query: str, top_k: int = 5) -> str:
        """
        Search for tables using semantic similarity matching.
        This is useful when the user's query mentions concepts that might 
        map to table names (e.g., "customer data" → "users" table).
        
        Args:
            search_query: Natural language description or keyword to search for.
            top_k: Number of top matching tables to return (default: 5).
        
        Returns:
            JSON string with matching table names and their relevance scores.
        """
        # Try to use schema manager for semantic search
        if db.schema_manager is not None:
            try:
                # Perform semantic search using schema manager
                relevant_tables = db.schema_manager.find_relevant_tables(
                    search_query,
                    use_semantic=True,
                    top_k=top_k
                )
                
                # Format results with detailed info
                results = []
                for table in relevant_tables:
                    results.append({
                        "table_name": table.name,
                        "columns": [col.name for col in table.columns][:10],  # First 10 columns
                        "column_count": len(table.columns),
                        "row_count": table.row_count,
                        "description": table.description or f"Table with {len(table.columns)} columns"
                    })
                
                return json.dumps({
                    "success": True,
                    "matching_tables": results,
                    "count": len(results),
                    "search_method": "semantic"
                }, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back to simple matching: {e}")
                # Fall through to simple name matching
        
        # Fallback: Simple name-based matching
        # This is used when semantic search is unavailable or fails
        try:
            tables = db.get_tables()
            search_lower = search_query.lower()
            
            # Find tables that contain the search term
            matching = [t for t in tables if search_lower in t.lower()][:top_k]
            
            # If no direct matches, find tables that partially match any word in the query
            if not matching:
                search_words = search_lower.split()
                for table in tables:
                    table_lower = table.lower()
                    if any(word in table_lower for word in search_words):
                        matching.append(table)
                        if len(matching) >= top_k:
                            break
            
            # Get detailed info for matched tables
            results = []
            for table_name in matching:
                try:
                    table_info = db.get_table_info(table_name)
                    results.append({
                        "table_name": table_name,
                        "columns": [col["name"] for col in table_info.get("columns", [])][:10],
                        "column_count": len(table_info.get("columns", [])),
                        "primary_key": table_info.get("primary_key", [])
                    })
                except:
                    # If getting table info fails, just return table name
                    results.append({"table_name": table_name})
            
            return json.dumps({
                "success": True,
                "matching_tables": results,
                "count": len(results),
                "search_method": "simple_name_matching",
                "note": "Using simple name matching (semantic search not available)"
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
                logger.error(f"Table search completely failed: {e}")
                return json.dumps({
                    "success": False,
                    "error": str(e),
                    "message": "Unable to search tables. Please check database connection."
                })


class WebSearchTools(Toolkit):
    """Web search toolkit for Agno Agent."""
    
    def __init__(self):
        super().__init__(
            name="web_search",
            tools=[
                self.request_for_internet_search,
            ]
        )
        self.web_search_tool: Optional[WebSearchTool] = None
    
    def request_for_internet_search(self, search_query: str, max_results: int = 5) -> str:
        """
        Perform an internet search to retrieve external information.
        Use this when you need current information or knowledge beyond the database.
        
        Args:
            search_query: The search query string.
            max_results: Maximum number of results to return (default: 5).
        
        Returns:
            JSON string with search results.
        """
        try:
            # Initialize web search tool if needed
            if self.web_search_tool is None:
                try:
                    from tools.web_search import get_web_search_tool
                    self.web_search_tool = get_web_search_tool()
                except Exception:
                    # Fallback: use DuckDuckGo without API key
                    from tools.web_search import WebSearchTool
                    self.web_search_tool = WebSearchTool(provider="duckduckgo")
            
            # Perform search (async)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            results = loop.run_until_complete(
                self.web_search_tool.search(search_query, max_results=max_results)
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                    "source": result.source
                })
            
            return json.dumps({
                "success": True,
                "results": formatted_results,
                "count": len(formatted_results),
                "query": search_query
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": "Web search is currently unavailable"
            })

