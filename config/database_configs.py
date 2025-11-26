"""
Database configuration module for AskDB.

This module provides configuration classes and utilities for managing
database connections across different database engines (PostgreSQL, MySQL, SQLite, SQL Server).
"""

from enum import Enum
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
import os


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    SQLSERVER = "sqlserver"


class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    
    # Core connection parameters
    db_type: DatabaseType = Field(..., description="Database type")
    host: Optional[str] = Field(None, description="Database host (not for SQLite)")
    port: Optional[int] = Field(None, description="Database port (not for SQLite)")
    database: str = Field(..., description="Database name")
    username: Optional[str] = Field(None, description="Database username (not for SQLite)")
    password: Optional[str] = Field(None, description="Database password (not for SQLite)")
    
    # Connection options
    ssl_mode: Optional[str] = Field("prefer", description="SSL mode for connection")
    connection_timeout: int = Field(30, description="Connection timeout in seconds")
    pool_size: int = Field(5, description="Connection pool size")
    max_overflow: int = Field(10, description="Maximum overflow connections")
    
    # Additional options
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional connection options")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        case_sensitive = False
    
    @validator('port', pre=True, always=True)
    def set_default_port(cls, v, values):
        """Set default port based on database type."""
        if v is not None:
            return v
        
        db_type = values.get('db_type')
        if db_type == DatabaseType.POSTGRESQL:
            return 5432
        elif db_type == DatabaseType.MYSQL:
            return 3306
        elif db_type == DatabaseType.SQLSERVER:
            return 1433
        elif db_type == DatabaseType.SQLITE:
            return None
        
        return v
    
    @validator('username', pre=True, always=True)
    def validate_username(cls, v, values):
        """Validate username requirement."""
        db_type = values.get('db_type')
        if db_type != DatabaseType.SQLITE and not v:
            raise ValueError(f"Username is required for {db_type}")
        return v
    
    @validator('password', pre=True, always=True)
    def validate_password(cls, v, values):
        """Validate password requirement."""
        db_type = values.get('db_type')
        if db_type != DatabaseType.SQLITE and not v:
            raise ValueError(f"Password is required for {db_type}")
        return v
    
    @validator('host', pre=True, always=True)
    def validate_host(cls, v, values):
        """Validate host requirement."""
        db_type = values.get('db_type')
        if db_type != DatabaseType.SQLITE and not v:
            raise ValueError(f"Host is required for {db_type}")
        return v
    
    def get_connection_string(self) -> str:
        """Generate database connection string."""
        if self.db_type == DatabaseType.SQLITE:
            return f"sqlite:///{self.database}"
        
        elif self.db_type == DatabaseType.POSTGRESQL:
            return (
                f"postgresql://{self.username}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}"
            )
        
        elif self.db_type == DatabaseType.MYSQL:
            return (
                f"mysql+pymysql://{self.username}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}"
            )
        
        elif self.db_type == DatabaseType.SQLSERVER:
            return (
                f"mssql+pyodbc://{self.username}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}"
                f"?driver=ODBC+Driver+17+for+SQL+Server"
            )
        
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def get_sqlalchemy_url(self) -> str:
        """Get SQLAlchemy-compatible URL."""
        return self.get_connection_string()
    
    def get_engine_kwargs(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine keyword arguments."""
        kwargs = {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.connection_timeout,
            "pool_recycle": 3600,  # Recycle connections after 1 hour
        }
        
        # Add SSL configuration for PostgreSQL
        if self.db_type == DatabaseType.POSTGRESQL and self.ssl_mode:
            kwargs["connect_args"] = {"sslmode": self.ssl_mode}
        
        # Add any additional options
        kwargs.update(self.options)
        
        return kwargs


class DatabaseConfigManager:
    """Manager for database configurations."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self._configs: Dict[str, DatabaseConfig] = {}
        self._default_config: Optional[str] = None
    
    def add_config(self, name: str, config: DatabaseConfig, set_default: bool = False) -> None:
        """Add a database configuration."""
        self._configs[name] = config
        if set_default or self._default_config is None:
            self._default_config = name
    
    def get_config(self, name: Optional[str] = None) -> DatabaseConfig:
        """Get a database configuration."""
        if name is None:
            name = self._default_config
        
        if name is None:
            raise ValueError("No database configuration specified and no default set")
        
        if name not in self._configs:
            raise ValueError(f"Database configuration '{name}' not found")
        
        return self._configs[name]
    
    def get_default(self) -> Optional[DatabaseConfig]:
        """Get the default database configuration."""
        if self._default_config and self._default_config in self._configs:
            return self._configs[self._default_config]
        return None
    
    def list_configs(self) -> Dict[str, DatabaseConfig]:
        """List all database configurations."""
        return self._configs.copy()
    
    def remove_config(self, name: str) -> None:
        """Remove a database configuration."""
        if name in self._configs:
            del self._configs[name]
            if self._default_config == name:
                self._default_config = next(iter(self._configs.keys()), None)
    
    def set_default(self, name: str) -> None:
        """Set the default configuration."""
        if name not in self._configs:
            raise ValueError(f"Database configuration '{name}' not found")
        self._default_config = name
    
    @classmethod
    def from_environment(cls, prefix: str = "ASKDB_DB_") -> "DatabaseConfigManager":
        """Create configuration manager from environment variables."""
        manager = cls()
        
        # First, try to load default database config from DEFAULT_DB_* variables
        default_db_type = os.getenv("DEFAULT_DB_TYPE")
        if default_db_type:
            try:
                default_config = DatabaseConfig(
                    db_type=DatabaseType(default_db_type.lower()),
                    host=os.getenv("DEFAULT_DB_HOST"),
                    port=int(os.getenv("DEFAULT_DB_PORT")) if os.getenv("DEFAULT_DB_PORT") else None,
                    database=os.getenv("DEFAULT_DB_NAME", ""),
                    username=os.getenv("DEFAULT_DB_USER"),
                    password=os.getenv("DEFAULT_DB_PASSWORD")
                )
                manager.add_config("default", default_config, set_default=True)
            except Exception as e:
                print(f"Warning: Failed to create default database config: {e}")
        
        # Look for database configurations in environment
        # Format: ASKDB_DB_CONFIG_NAME_TYPE, ASKDB_DB_CONFIG_NAME_HOST, etc.
        env_configs = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix):].split("_", 2)
                if len(parts) >= 3:
                    config_name, param_name = parts[0], "_".join(parts[1:])
                    if config_name not in env_configs:
                        env_configs[config_name] = {}
                    env_configs[config_name][param_name.lower()] = value
        
        # Create DatabaseConfig objects
        for config_name, params in env_configs.items():
            try:
                config = DatabaseConfig(**params)
                is_default = params.get("default", "false").lower() == "true"
                manager.add_config(config_name, config, set_default=is_default)
            except Exception as e:
                print(f"Warning: Failed to create database config '{config_name}': {e}")
        
        return manager


# Global configuration manager instance
_db_config_manager: Optional[DatabaseConfigManager] = None


def get_db_config_manager() -> DatabaseConfigManager:
    """Get the global database configuration manager."""
    global _db_config_manager
    if _db_config_manager is None:
        # Ensure .env is loaded
        from dotenv import load_dotenv
        load_dotenv()
        _db_config_manager = DatabaseConfigManager.from_environment()
    return _db_config_manager


def create_database_config(
    db_type: Union[str, DatabaseType],
    database: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs
) -> DatabaseConfig:
    """Create a database configuration."""
    if isinstance(db_type, str):
        db_type = DatabaseType(db_type.lower())
    
    return DatabaseConfig(
        db_type=db_type,
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        **kwargs
    )


# Predefined configurations for common use cases
def get_sqlite_config(database_path: str) -> DatabaseConfig:
    """Get SQLite configuration for a given database path."""
    return DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        database=database_path
    )


def get_postgresql_config(
    host: str,
    database: str,
    username: str,
    password: str,
    port: int = 5432,
    **kwargs
) -> DatabaseConfig:
    """Get PostgreSQL configuration."""
    return DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        **kwargs
    )


def get_mysql_config(
    host: str,
    database: str,
    username: str,
    password: str,
    port: int = 3306,
    **kwargs
) -> DatabaseConfig:
    """Get MySQL configuration."""
    return DatabaseConfig(
        db_type=DatabaseType.MYSQL,
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
        **kwargs
    )