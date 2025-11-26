"""
AskDB Tools Module

This module provides the core tools used by the AskDB agent for database interaction,
schema exploration, and external information retrieval.

Available Tools:
- DatabaseTool: Database connectivity and SQL query execution
- SchemaManager: Database schema exploration and semantic indexing
- WebSearchTool: External information retrieval via web search

The tools module is designed to be provider-agnostic and supports multiple database
engines and search providers.
"""

from tools.database import (
    DatabaseTool,
    DatabaseToolManager,
    get_db_tool_manager,
    get_database_tool,
    create_database_tool,
    DatabaseConnectionError,
    DatabaseQueryError
)

from tools.schema import (
    ColumnInfo,
    TableInfo,
    SchemaInfo,
    SchemaExplorer,
    VectorSchemaIndex,
    SchemaManager,
    get_schema_manager,
    create_schema_manager
)

from tools.web_search import (
    SearchResult,
    SearchQuery,
    WebSearchTool,
    WebSearchManager,
    get_web_search_manager,
    create_web_search_tool,
    get_web_search_tool,
    web_search,
    WebSearchError
)

__all__ = [
    # Database tools
    "DatabaseTool",
    "DatabaseToolManager", 
    "get_db_tool_manager",
    "get_database_tool",
    "create_database_tool",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    
    # Schema tools
    "ColumnInfo",
    "TableInfo", 
    "SchemaInfo",
    "SchemaExplorer",
    "VectorSchemaIndex",
    "SchemaManager",
    "get_schema_manager",
    "create_schema_manager",
    
    # Web search tools
    "SearchResult",
    "SearchQuery",
    "WebSearchTool",
    "WebSearchManager",
    "get_web_search_manager",
    "create_web_search_tool",
    "get_web_search_tool",
    "web_search",
    "WebSearchError"
]

# Version information
__version__ = "1.0.0"

# Tool registry for easy access
_tool_registry = {
    "database": {
        "class": DatabaseTool,
        "manager": get_db_tool_manager,
        "description": "Database connectivity and SQL query execution"
    },
    "schema": {
        "class": SchemaManager,
        "factory": create_schema_manager,
        "description": "Database schema exploration and semantic indexing"
    },
    "web_search": {
        "class": WebSearchTool,
        "manager": get_web_search_manager,
        "description": "External information retrieval via web search"
    }
}

def get_available_tools():
    """
    Get a list of available tools with their descriptions.
    
    Returns:
        dict: Dictionary mapping tool names to their descriptions
    """
    return {name: info["description"] for name, info in _tool_registry.items()}

def get_tool_info(tool_name):
    """
    Get information about a specific tool.
    
    Args:
        tool_name (str): Name of the tool
        
    Returns:
        dict: Tool information or None if tool not found
    """
    return _tool_registry.get(tool_name)

def initialize_tools(settings=None):
    """
    Initialize all tools with the given settings.
    
    Args:
        settings: Application settings (optional)
        
    Returns:
        dict: Dictionary of initialized tool managers
    """
    if settings is None:
        from config import get_settings
        settings = get_settings()
    
    initialized = {}
    
    # Initialize database tool manager
    try:
        db_manager = get_db_tool_manager()
        initialized["database"] = db_manager
    except Exception as e:
        print(f"Warning: Failed to initialize database tools: {e}")
    
    # Initialize web search manager
    try:
        web_manager = get_web_search_manager()
        initialized["web_search"] = web_manager
    except Exception as e:
        print(f"Warning: Failed to initialize web search tools: {e}")
    
    return initialized

# Convenience functions for common operations
def setup_database_tool(config, name="default"):
    """
    Set up a database tool with the given configuration.
    
    Args:
        config: Database configuration
        name (str): Name for the database tool
        
    Returns:
        DatabaseTool: Configured database tool
    """
    return create_database_tool(name, config, set_as_default=True)

def setup_schema_manager(database_tool=None):
    """
    Set up a schema manager for the given database tool.
    
    Args:
        database_tool: Database tool instance (optional)
        
    Returns:
        SchemaManager: Configured schema manager
    """
    if database_tool is None:
        database_tool = get_database_tool()
    
    if database_tool is None:
        raise ValueError("No database tool available. Please set up a database tool first.")
    
    return create_schema_manager(database_tool)

def setup_web_search_tool(provider="duckduckgo", name="default", **kwargs):
    """
    Set up a web search tool with the given provider.
    
    Args:
        provider (str): Search provider name
        name (str): Name for the web search tool
        **kwargs: Additional provider-specific arguments
        
    Returns:
        WebSearchTool: Configured web search tool
    """
    return create_web_search_tool(name, provider, **kwargs)