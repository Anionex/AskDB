"""
Database dialect abstraction layer for multi-database support.
doutble to use
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from sqlalchemy.engine import Engine
from sqlalchemy import text

class DatabaseDialect(ABC):
    """Abstract base class for database dialects."""
    
    @abstractmethod
    def get_database_name(self, engine: Engine) -> str:
        """Get database name."""
        pass
    
    @abstractmethod
    def get_row_count(self, engine: Engine, table_name: str) -> Optional[int]:
        """Get row count for a table."""
        pass
    
    @abstractmethod
    def get_table_comment(self, engine: Engine, table_name: str) -> Optional[str]:
        """Get table comment/description."""
        pass
    
    @abstractmethod
    def get_column_comment(self, engine: Engine, table_name: str, column_name: str) -> Optional[str]:
        """Get column comment."""
        pass
    
    @abstractmethod
    def quote_identifier(self, identifier: str) -> str:
        """Quote identifier for SQL (table/column names)."""
        pass


class PostgreSQLDialect(DatabaseDialect):
    """PostgreSQL dialect implementation."""
    
    def get_database_name(self, engine: Engine) -> str:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            return result.scalar()
    
    def get_row_count(self, engine: Engine, table_name: str) -> Optional[int]:
        try:
            quoted_table = self.quote_identifier(table_name)
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
                return result.scalar()
        except Exception:
            return None
    
    def get_table_comment(self, engine: Engine, table_name: str) -> Optional[str]:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT obj_description('{table_name}'::regclass, 'pg_class')
                """))
                return result.scalar()
        except Exception:
            return None
    
    def get_column_comment(self, engine: Engine, table_name: str, column_name: str) -> Optional[str]:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT col_description('{table_name}'::regclass, 
                    (SELECT attnum FROM pg_attribute 
                     WHERE attrelid = '{table_name}'::regclass AND attname = '{column_name}'))
                """))
                return result.scalar()
        except Exception:
            return None
    
    def quote_identifier(self, identifier: str) -> str:
        return f'"{identifier}"'


class OpenGaussDialect(PostgreSQLDialect):
    """OpenGauss dialect (inherits from PostgreSQL as they're compatible)."""
    
    def get_database_name(self, engine: Engine) -> str:
        # OpenGauss uses same syntax as PostgreSQL
        return super().get_database_name(engine)
    
    # OpenGauss specific overrides can be added here if needed


class MySQLDialect(DatabaseDialect):
    """MySQL dialect implementation."""
    
    def get_database_name(self, engine: Engine) -> str:
        return engine.url.database or "unknown"
    
    def get_row_count(self, engine: Engine, table_name: str) -> Optional[int]:
        try:
            quoted_table = self.quote_identifier(table_name)
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
                return result.scalar()
        except Exception:
            return None
    
    def get_table_comment(self, engine: Engine, table_name: str) -> Optional[str]:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT table_comment 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table_name}'
                """))
                return result.scalar()
        except Exception:
            return None
    
    def get_column_comment(self, engine: Engine, table_name: str, column_name: str) -> Optional[str]:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT column_comment 
                    FROM information_schema.columns 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table_name}' 
                    AND column_name = '{column_name}'
                """))
                return result.scalar()
        except Exception:
            return None
    
    def quote_identifier(self, identifier: str) -> str:
        return f'`{identifier}`'


class SQLiteDialect(DatabaseDialect):
    """SQLite dialect implementation."""
    
    def get_database_name(self, engine: Engine) -> str:
        from pathlib import Path
        return Path(engine.url.database).stem if engine.url.database else "memory"
    
    def get_row_count(self, engine: Engine, table_name: str) -> Optional[int]:
        try:
            quoted_table = self.quote_identifier(table_name)
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
                return result.scalar()
        except Exception:
            return None
    
    def get_table_comment(self, engine: Engine, table_name: str) -> Optional[str]:
        # SQLite doesn't support table comments in standard way
        return None
    
    def get_column_comment(self, engine: Engine, table_name: str, column_name: str) -> Optional[str]:
        # SQLite doesn't support column comments in standard way
        return None
    
    def quote_identifier(self, identifier: str) -> str:
        return f'"{identifier}"'


class DialectManager:
    """Manager for database dialect detection and handling."""
    
    _dialects = {
        'postgresql': PostgreSQLDialect,
        'opengauss': OpenGaussDialect,
        'mysql': MySQLDialect,
        'sqlite': SQLiteDialect
    }
    
    @classmethod
    def get_dialect(cls, engine: Engine) -> DatabaseDialect:
        """Get appropriate dialect for database engine."""
        dialect_name = engine.dialect.name
        dialect_class = cls._dialects.get(dialect_name)
        
        if not dialect_class:
            # Fallback to generic dialect
            return GenericDialect()
        
        return dialect_class()
    
    @classmethod
    def register_dialect(cls, dialect_name: str, dialect_class):
        """Register a new database dialect."""
        cls._dialects[dialect_name] = dialect_class


class GenericDialect(DatabaseDialect):
    """Generic fallback dialect for unsupported databases."""
    
    def get_database_name(self, engine: Engine) -> str:
        return engine.url.database or "unknown"
    
    def get_row_count(self, engine: Engine, table_name: str) -> Optional[int]:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar()
        except Exception:
            return None
    
    def get_table_comment(self, engine: Engine, table_name: str) -> Optional[str]:
        return None
    
    def get_column_comment(self, engine: Engine, table_name: str, column_name: str) -> Optional[str]:
        return None
    
    def quote_identifier(self, identifier: str) -> str:
        return identifier  # No quoting for generic case