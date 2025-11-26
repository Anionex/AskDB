"""
Database tools for AskDB - Handles database connections and SQL query execution.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from contextlib import contextmanager
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError
from sqlalchemy.orm import sessionmaker, Session

from ..config import DatabaseConfig, get_db_config_manager

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass


class DatabaseQueryError(Exception):
    """Raised when database query execution fails."""
    pass


class DatabaseTool:
    """
    Database tool for executing SQL queries and managing database connections.
    Supports multiple database engines through SQLAlchemy.
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize database tool with configuration.
        
        Args:
            config: Database configuration. If None, uses default config.
        """
        self.config = config or get_db_config_manager().get_default()
        if not self.config:
            raise DatabaseConnectionError("No database configuration provided")
        
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None
        self._connected = False
        
    def connect(self) -> bool:
        """
        Establish database connection.
        
        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            logger.info(f"Connecting to database: {self.config.db_type}")
            
            # Create SQLAlchemy engine
            self.engine = create_engine(
                self.config.get_sqlalchemy_url(),
                **self.config.get_engine_kwargs()
            )
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Create session factory
            self.session_factory = sessionmaker(bind=self.engine)
            self._connected = True
            
            logger.info("Database connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            self._connected = False
            raise DatabaseConnectionError(f"Connection failed: {str(e)}")
    
    def disconnect(self):
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
        self.session_factory = None
        self._connected = False
        logger.info("Database connection closed")
    
    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected and self.engine is not None
    
    @contextmanager
    def get_session(self):
        """
        Get database session context manager.
        
        Yields:
            Session: SQLAlchemy session
        """
        if not self.is_connected:
            raise DatabaseConnectionError("Database not connected")
        
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise DatabaseQueryError(f"Session error: {str(e)}")
        finally:
            session.close()
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute SQL query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Dict containing query results and metadata
        """
        if not self.is_connected:
            raise DatabaseConnectionError("Database not connected")
        
        start_time = time.time()
        
        try:
            with self.engine.connect() as conn:
                # Execute query
                result = conn.execute(text(query), params or {})
                
                # Get column names
                if result.returns_rows:
                    columns = list(result.keys())
                    rows = result.fetchall()
                    
                    # Convert to list of dictionaries
                    data = [dict(zip(columns, row)) for row in rows]
                    
                    # Get row count
                    row_count = len(rows)
                else:
                    data = []
                    columns = []
                    row_count = result.rowcount
                
                execution_time = time.time() - start_time
                
                logger.info(f"Query executed successfully in {execution_time:.3f}s, {row_count} rows affected")
                
                return {
                    "success": True,
                    "data": data,
                    "columns": columns,
                    "row_count": row_count,
                    "execution_time": execution_time,
                    "query": query,
                    "error": None
                }
                
        except SQLAlchemyError as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Query execution failed: {error_msg}")
            
            return {
                "success": False,
                "data": [],
                "columns": [],
                "row_count": 0,
                "execution_time": execution_time,
                "query": query,
                "error": error_msg
            }
    
    def validate_query(self, query: str) -> Dict[str, Any]:
        """
        Validate SQL query syntax without executing.
        
        Args:
            query: SQL query string
            
        Returns:
            Dict containing validation results
        """
        try:
            # Parse query using SQLAlchemy
            compiled = text(query).compile()
            
            # Basic validation checks
            query_lower = query.lower().strip()
            
            # Check for dangerous operations
            dangerous_keywords = ['drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update']
            is_readonly = not any(keyword in query_lower for keyword in dangerous_keywords)
            
            return {
                "valid": True,
                "readonly": is_readonly,
                "error": None,
                "compiled_query": str(compiled)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "readonly": False,
                "error": str(e),
                "compiled_query": None
            }
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dict containing table information
        """
        if not self.is_connected:
            raise DatabaseConnectionError("Database not connected")
        
        try:
            inspector = inspect(self.engine)
            
            # Check if table exists
            if table_name not in inspector.get_table_names():
                return {
                    "exists": False,
                    "error": f"Table '{table_name}' not found"
                }
            
            # Get column information
            columns = inspector.get_columns(table_name)
            
            # Get primary keys
            primary_keys = inspector.get_pk_constraint(table_name)['constrained_columns']
            
            # Get foreign keys
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            # Get indexes
            indexes = inspector.get_indexes(table_name)
            
            # Get row count
            row_count_result = self.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
            row_count = row_count_result["data"][0]["count"] if row_count_result["success"] else 0
            
            return {
                "exists": True,
                "table_name": table_name,
                "columns": columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "indexes": indexes,
                "row_count": row_count,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error getting table info for '{table_name}': {str(e)}")
            return {
                "exists": False,
                "error": str(e)
            }
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get general database information.
        
        Returns:
            Dict containing database information
        """
        if not self.is_connected:
            raise DatabaseConnectionError("Database not connected")
        
        try:
            inspector = inspect(self.engine)
            
            # Get all table names
            table_names = inspector.get_table_names()
            
            # Get view names if supported
            try:
                view_names = inspector.get_view_names()
            except:
                view_names = []
            
            # Get database version
            version_result = self.execute_query("SELECT version() as version")
            version = version_result["data"][0]["version"] if (version_result["success"] and version_result["data"]) else "Unknown"
            
            return {
                "database_type": str(self.config.db_type),
                "database_name": self.config.database,
                "host": self.config.host,
                "port": self.config.port,
                "version": version,
                "table_count": len(table_names),
                "tables": table_names,
                "view_count": len(view_names),
                "views": view_names,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error getting database info: {str(e)}")
            return {
                "error": str(e)
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test database connection and return status.
        
        Returns:
            Dict containing connection test results
        """
        try:
            if not self.is_connected:
                self.connect()
            
            # Get database info
            db_info = self.get_database_info()
            
            return {
                "success": True,
                "database_info": db_info,
                "error": None
            }
                
        except Exception as e:
            return {
                "success": False,
                "database_info": {},
                "error": str(e)
            }
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class DatabaseToolManager:
    """
    Manager for multiple database tool instances.
    """
    
    def __init__(self):
        self._tools: Dict[str, DatabaseTool] = {}
        self._default_tool: Optional[str] = None
    
    def add_tool(self, name: str, config: DatabaseConfig, set_as_default: bool = False) -> DatabaseTool:
        """
        Add a database tool.
        
        Args:
            name: Tool name
            config: Database configuration
            set_as_default: Whether to set as default tool
            
        Returns:
            DatabaseTool: Created database tool
        """
        tool = DatabaseTool(config)
        self._tools[name] = tool
        
        if set_as_default or self._default_tool is None:
            self._default_tool = name
        
        logger.info(f"Added database tool: {name}")
        return tool
    
    def get_tool(self, name: Optional[str] = None) -> Optional[DatabaseTool]:
        """
        Get database tool by name.
        
        Args:
            name: Tool name. If None, returns default tool.
            
        Returns:
            DatabaseTool or None if not found
        """
        if name is None:
            name = self._default_tool
        
        return self._tools.get(name) if name else None
    
    def list_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self._tools.keys())
    
    def remove_tool(self, name: str) -> bool:
        """
        Remove database tool.
        
        Args:
            name: Tool name
            
        Returns:
            bool: True if removed, False if not found
        """
        if name in self._tools:
            tool = self._tools[name]
            if tool.is_connected:
                tool.disconnect()
            del self._tools[name]
            
            if self._default_tool == name:
                self._default_tool = next(iter(self._tools.keys()), None)
            
            logger.info(f"Removed database tool: {name}")
            return True
        return False
    
    def disconnect_all(self):
        """Disconnect all database tools."""
        for tool in self._tools.values():
            if tool.is_connected:
                tool.disconnect()
        logger.info("Disconnected all database tools")


# Global database tool manager instance
_db_tool_manager = DatabaseToolManager()
_db_tool_manager_initialized = False


def get_db_tool_manager() -> DatabaseToolManager:
    """Get global database tool manager."""
    global _db_tool_manager_initialized
    
    # Initialize tools from config manager on first access
    if not _db_tool_manager_initialized:
        try:
            config_manager = get_db_config_manager()
            configs = config_manager.list_configs()
            
            # Add tools for all configured databases
            for name, config in configs.items():
                is_default = (name == config_manager._default_config)
                _db_tool_manager.add_tool(name, config, set_as_default=is_default)
            
            _db_tool_manager_initialized = True
        except Exception as e:
            logger.warning(f"Failed to initialize database tools from config: {e}")
    
    return _db_tool_manager


def get_database_tool(name: Optional[str] = None) -> Optional[DatabaseTool]:
    """
    Get database tool by name.
    
    Args:
        name: Tool name. If None, returns default tool.
        
    Returns:
        DatabaseTool or None if not found
    """
    return _db_tool_manager.get_tool(name)


def create_database_tool(name: str, config: DatabaseConfig, set_as_default: bool = False) -> DatabaseTool:
    """
    Create and add a database tool.
    
    Args:
        name: Tool name
        config: Database configuration
        set_as_default: Whether to set as default tool
        
    Returns:
        DatabaseTool: Created database tool
    """
    return _db_tool_manager.add_tool(name, config, set_as_default)