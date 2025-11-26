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

# Legacy config imports removed - using environment variables directly

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
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize database tool with database URL.
        
        Args:
            db_url: SQLAlchemy database URL. If None, builds from environment variables.
        """
        if db_url is None:
            # Build URL from environment variables
            import os
            db_type = os.getenv("DEFAULT_DB_TYPE", "mysql")
            host = os.getenv("DEFAULT_DB_HOST", "localhost")
            port = os.getenv("DEFAULT_DB_PORT", "3306")
            database = os.getenv("DEFAULT_DB_NAME", "")
            user = os.getenv("DEFAULT_DB_USER", "root")
            password = os.getenv("DEFAULT_DB_PASSWORD", "")
            
            if db_type == "mysql":
                db_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
            elif db_type == "postgresql":
                db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            elif db_type == "sqlite":
                db_url = f"sqlite:///{database}"
            else:
                raise DatabaseConnectionError(f"Unsupported database type: {db_type}")
        
        self.db_url = db_url
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
            logger.info(f"Connecting to database: {self.db_url.split('@')[0].split('//')[1].split(':')[0]}")
            
            # Create SQLAlchemy engine
            self.engine = create_engine(self.db_url)
            
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
            
            # Try to get database version
            try:
                version_result = self.execute_query("SELECT version() as version")
                version = version_result["data"][0]["version"] if (version_result["success"] and version_result["data"]) else "Unknown"
            except:
                version = "Unknown"
            
            # Extract database info from URL
            import os
            return {
                "database_type": os.getenv("DEFAULT_DB_TYPE", "unknown"),
                "database_name": self.engine.url.database or "unknown",
                "host": self.engine.url.host or "unknown",
                "port": self.engine.url.port or "unknown",
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


# Legacy functions kept for backward compatibility
# Agno version uses DatabaseConnection in agno_tools.py directly

def get_database_tool(name: Optional[str] = None) -> Optional[DatabaseTool]:
    """
    Get database tool instance.
    
    Note: In Agno version, this creates a new instance from environment variables.
    Legacy function kept for compatibility with schema.py.
    
    Args:
        name: Ignored in Agno version
        
    Returns:
        DatabaseTool instance or None on error
    """
    try:
        tool = DatabaseTool()
        return tool
    except Exception as e:
        logger.warning(f"Failed to create database tool: {e}")
        return None