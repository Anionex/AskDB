"""
Tools package for AskDB.
Simplified for Agno framework version.
"""

# Re-export for legacy compatibility only
from tools.database import DatabaseTool
from tools.schema import SchemaManager  
from tools.web_search import WebSearchTool

__all__ = [
    'DatabaseTool',
    'SchemaManager',
    'WebSearchTool',
]
