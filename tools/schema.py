"""
Schema exploration and vector indexing module for AskDB.

This module provides comprehensive database schema exploration capabilities,
including table discovery, column analysis, and vector-based semantic indexing
for efficient table and column search.
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from tools.database import DatabaseTool

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    data_type: str
    nullable: bool
    default: Optional[str]
    is_primary_key: bool
    is_foreign_key: bool
    foreign_key_target: Optional[str]
    description: Optional[str] = None
    
    def to_text(self) -> str:
        """Convert column info to text representation for embedding."""
        text_parts = [f"Column '{self.name}' of type {self.data_type}"]
        if self.is_primary_key:
            text_parts.append("primary key")
        if self.is_foreign_key and self.foreign_key_target:
            text_parts.append(f"foreign key to {self.foreign_key_target}")
        if not self.nullable:
            text_parts.append("not nullable")
        if self.description:
            text_parts.append(f"description: {self.description}")
        return ". ".join(text_parts)


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    description: Optional[str]
    row_count: Optional[int]
    columns: List[ColumnInfo]
    indexes: List[str]
    foreign_keys: List[str]
    
    def to_text(self) -> str:
        """Convert table info to text representation for embedding."""
        text_parts = [f"Table '{self.name}'"]
        if self.description:
            text_parts.append(f"description: {self.description}")
        if self.row_count is not None:
            text_parts.append(f"rows: {self.row_count}")
        
        column_descriptions = [col.to_text() for col in self.columns]
        text_parts.extend(column_descriptions)
        
        if self.indexes:
            text_parts.append(f"indexes: {', '.join(self.indexes)}")
        
        return ". ".join(text_parts)


@dataclass
class SchemaInfo:
    """Complete database schema information."""
    database_name: str
    database_type: str
    tables: List[TableInfo]
    relationships: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert schema info to dictionary."""
        return {
            'database_name': self.database_name,
            'database_type': self.database_type,
            'tables': [asdict(table) for table in self.tables],
            'relationships': self.relationships
        }


class SchemaExplorer:
    """Database schema exploration and analysis."""
    
    def __init__(self, database_tool: DatabaseTool):
        """
        Initialize schema explorer.
        
        Args:
            database_tool: Database tool instance for schema exploration
        """
        self.database_tool = database_tool
        self._schema_cache: Optional[SchemaInfo] = None
    
    def explore_schema(self, force_refresh: bool = False) -> SchemaInfo:
        """
        Explore and analyze database schema.
        
        Args:
            force_refresh: Force refresh of cached schema
            
        Returns:
            Complete schema information
        """
        if self._schema_cache is not None and not force_refresh:
            return self._schema_cache
        
        if not self.database_tool or not self.database_tool.is_connected:
            raise ValueError("Database connection required for schema exploration")
        
        logger.info("Starting schema exploration...")
        
        try:
            engine = self.database_tool.engine
            inspector = inspect(engine)
            
            # Get database information
            database_name = self._get_database_name(engine)
            # Get database type from engine dialect
            database_type = engine.dialect.name if engine else "unknown"
            
            # Explore tables
            tables = []
            table_names = inspector.get_table_names()
            
            for table_name in table_names:
                table_info = self._explore_table(inspector, table_name)
                tables.append(table_info)
            
            # Explore relationships
            relationships = self._explore_relationships(inspector, table_names)
            
            self._schema_cache = SchemaInfo(
                database_name=database_name,
                database_type=database_type,
                tables=tables,
                relationships=relationships
            )
            
            logger.info(f"Schema exploration completed: {len(tables)} tables found")
            return self._schema_cache
            
        except Exception as e:
            logger.error(f"Schema exploration failed: {e}")
            raise
    
    def _get_database_name(self, engine: Engine) -> str:
        """Get database name from engine."""
        try:
            if engine.dialect.name == 'postgresql':
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT current_database()"))
                    return result.scalar()
            elif engine.dialect.name == 'mysql':
                return engine.url.database or "unknown"
            elif engine.dialect.name == 'sqlite':
                return Path(engine.url.database).stem if engine.url.database else "memory"
            else:
                return engine.url.database or "unknown"
        except Exception:
            return "unknown"
    
    def _explore_table(self, inspector, table_name: str) -> TableInfo:
        """Explore a specific table."""
        try:
            # Get column information
            columns = []
            column_info = inspector.get_columns(table_name)
            primary_keys = set(inspector.get_pk_constraint(table_name)['constrained_columns'])
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            # Build foreign key mapping
            fk_mapping = {}
            for fk in foreign_keys:
                for col in fk['constrained_columns']:
                    fk_mapping[col] = f"{fk['referred_table']}.{', '.join(fk['referred_columns'])}"
            
            for col in column_info:
                column_obj = ColumnInfo(
                    name=col['name'],
                    data_type=str(col['type']),
                    nullable=col.get('nullable', True),
                    default=str(col['default']) if col.get('default') else None,
                    is_primary_key=col['name'] in primary_keys,
                    is_foreign_key=col['name'] in fk_mapping,
                    foreign_key_target=fk_mapping.get(col['name'])
                )
                columns.append(column_obj)
            
            # Get row count
            row_count = self._get_row_count(table_name)
            
            # Get indexes
            indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
            
            return TableInfo(
                name=table_name,
                description=None,  # Could be enhanced with table comments
                row_count=row_count,
                columns=columns,
                indexes=indexes,
                foreign_keys=[fk['name'] for fk in foreign_keys]
            )
            
        except Exception as e:
            logger.warning(f"Failed to explore table {table_name}: {e}")
            return TableInfo(
                name=table_name,
                description=None,
                row_count=None,
                columns=[],
                indexes=[],
                foreign_keys=[]
            )
    
    def _get_row_count(self, table_name: str) -> Optional[int]:
        """Get row count for a table."""
        try:
            result = self.database_tool.execute_query(f"SELECT COUNT(*) FROM {table_name}")
            return result[0][0] if result else None
        except Exception:
            return None
    
    def _explore_relationships(self, inspector, table_names: List[str]) -> List[Dict[str, Any]]:
        """Explore table relationships."""
        relationships = []
        
        for table_name in table_names:
            foreign_keys = inspector.get_foreign_keys(table_name)
            for fk in foreign_keys:
                relationship = {
                    'from_table': table_name,
                    'from_columns': fk['constrained_columns'],
                    'to_table': fk['referred_table'],
                    'to_columns': fk['referred_columns'],
                    'relationship_type': 'foreign_key'
                }
                relationships.append(relationship)
        
        return relationships
    
    def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        """Get information about a specific table."""
        schema = self.explore_schema()
        for table in schema.tables:
            if table.name == table_name:
                return table
        return None
    
    def search_tables(self, query: str) -> List[TableInfo]:
        """Search tables by name (simple text search)."""
        schema = self.explore_schema()
        query_lower = query.lower()
        
        matching_tables = []
        for table in schema.tables:
            if query_lower in table.name.lower():
                matching_tables.append(table)
        
        return matching_tables
    
    def search_columns(self, query: str) -> List[Tuple[TableInfo, ColumnInfo]]:
        """Search columns by name across all tables."""
        schema = self.explore_schema()
        query_lower = query.lower()
        
        matching_columns = []
        for table in schema.tables:
            for column in table.columns:
                if query_lower in column.name.lower():
                    matching_columns.append((table, column))
        
        return matching_columns


class VectorSchemaIndex:
    """Vector-based semantic indexing for schema search."""
    
    def __init__(self, schema_explorer: Optional[SchemaExplorer] = None, 
                 model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize vector schema index.
        
        Args:
            schema_explorer: Schema explorer instance
            model_name: Sentence transformer model name
        """
        self.schema_explorer = schema_explorer
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.table_embeddings: Optional[np.ndarray] = None
        self.column_embeddings: Optional[np.ndarray] = None
        self.table_texts: List[str] = []
        self.column_texts: List[str] = []
        self._index_built = False
    
    def _load_model(self):
        """Load the sentence transformer model."""
        if self.model is None:
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
    
    def build_index(self, force_rebuild: bool = False):
        """
        Build vector index for semantic search.
        
        Args:
            force_rebuild: Force rebuild of existing index
        """
        if self._index_built and not force_rebuild:
            return
        
        if not self.schema_explorer:
            raise ValueError("Schema explorer required for building index")
        
        logger.info("Building vector schema index...")
        self._load_model()
        
        # Get schema information
        schema = self.schema_explorer.explore_schema()
        
        # Prepare text representations
        self.table_texts = [table.to_text() for table in schema.tables]
        self.column_texts = []
        for table in schema.tables:
            for column in table.columns:
                self.column_texts.append(f"Table {table.name}: {column.to_text()}")
        
        # Generate embeddings
        logger.info("Generating embeddings for tables...")
        self.table_embeddings = self.model.encode(self.table_texts)
        
        logger.info("Generating embeddings for columns...")
        self.column_embeddings = self.model.encode(self.column_texts)
        
        self._index_built = True
        logger.info("Vector schema index built successfully")
    
    def search_tables_semantic(self, query: str, top_k: int = 5) -> List[Tuple[TableInfo, float]]:
        """
        Search tables using semantic similarity.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of (table_info, similarity_score) tuples
        """
        if not self._index_built:
            self.build_index()
        
        self._load_model()
        
        # Encode query
        query_embedding = self.model.encode([query])
        
        # Calculate similarities
        similarities = []
        for i, table_embedding in enumerate(self.table_embeddings):
            similarity = 1 - cosine(query_embedding[0], table_embedding)
            similarities.append((i, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top results
        schema = self.schema_explorer.explore_schema()
        results = []
        for i, similarity in similarities[:top_k]:
            table_info = schema.tables[i]
            results.append((table_info, similarity))
        
        return results
    
    def search_columns_semantic(self, query: str, top_k: int = 10) -> List[Tuple[TableInfo, ColumnInfo, float]]:
        """
        Search columns using semantic similarity.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of (table_info, column_info, similarity_score) tuples
        """
        if not self._index_built:
            self.build_index()
        
        self._load_model()
        
        # Encode query
        query_embedding = self.model.encode([query])
        
        # Calculate similarities
        similarities = []
        for i, column_embedding in enumerate(self.column_embeddings):
            similarity = 1 - cosine(query_embedding[0], column_embedding)
            similarities.append((i, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top results
        schema = self.schema_explorer.explore_schema()
        results = []
        column_index = 0
        
        for i, similarity in similarities[:top_k]:
            # Find the corresponding table and column
            for table in schema.tables:
                if i < column_index + len(table.columns):
                    column_idx = i - column_index
                    column_info = table.columns[column_idx]
                    results.append((table, column_info, similarity))
                    break
                column_index += len(table.columns)
        
        return results
    
    def save_index(self, file_path: Union[str, Path]):
        """Save vector index to file."""
        if not self._index_built:
            raise ValueError("No index built to save")
        
        file_path = Path(file_path)
        index_data = {
            'table_texts': self.table_texts,
            'column_texts': self.column_texts,
            'table_embeddings': self.table_embeddings.tolist(),
            'column_embeddings': self.column_embeddings.tolist(),
            'model_name': self.model_name
        }
        
        with open(file_path, 'w') as f:
            json.dump(index_data, f)
        
        logger.info(f"Vector index saved to {file_path}")
    
    def load_index(self, file_path: Union[str, Path]):
        """Load vector index from file."""
        file_path = Path(file_path)
        
        with open(file_path, 'r') as f:
            index_data = json.load(f)
        
        self.table_texts = index_data['table_texts']
        self.column_texts = index_data['column_texts']
        self.table_embeddings = np.array(index_data['table_embeddings'])
        self.column_embeddings = np.array(index_data['column_embeddings'])
        self.model_name = index_data['model_name']
        
        self._index_built = True
        logger.info(f"Vector index loaded from {file_path}")


class SchemaManager:
    """High-level schema management interface."""
    
    def __init__(self, database_tool: DatabaseTool):
        """
        Initialize schema manager.
        
        Args:
            database_tool: Database tool instance
        """
        self.database_tool = database_tool
        self.explorer = SchemaExplorer(self.database_tool)
        self.vector_index = VectorSchemaIndex(self.explorer)
    
    def get_schema_summary(self) -> Dict[str, Any]:
        """Get a summary of the database schema."""
        schema = self.explorer.explore_schema()
        
        summary = {
            'database_name': schema.database_name,
            'database_type': schema.database_type,
            'table_count': len(schema.tables),
            'tables': []
        }
        
        for table in schema.tables:
            table_summary = {
                'name': table.name,
                'column_count': len(table.columns),
                'row_count': table.row_count,
                'has_primary_key': any(col.is_primary_key for col in table.columns),
                'has_foreign_keys': any(col.is_foreign_key for col in table.columns)
            }
            summary['tables'].append(table_summary)
        
        return summary
    
    def find_relevant_tables(self, query: str, use_semantic: bool = True, 
                           top_k: int = 5) -> List[TableInfo]:
        """
        Find tables relevant to a query.
        
        Args:
            query: Search query
            use_semantic: Use semantic search if True, otherwise text search
            top_k: Number of results to return
            
        Returns:
            List of relevant table information
        """
        if use_semantic:
            results = self.vector_index.search_tables_semantic(query, top_k)
            return [table for table, _ in results]
        else:
            return self.explorer.search_tables(query)[:top_k]
    
    def find_relevant_columns(self, query: str, use_semantic: bool = True,
                            top_k: int = 10) -> List[Tuple[TableInfo, ColumnInfo]]:
        """
        Find columns relevant to a query.
        
        Args:
            query: Search query
            use_semantic: Use semantic search if True, otherwise text search
            top_k: Number of results to return
            
        Returns:
            List of (table_info, column_info) tuples
        """
        if use_semantic:
            results = self.vector_index.search_columns_semantic(query, top_k)
            return [(table, column) for table, column, _ in results]
        else:
            return self.explorer.search_columns(query)[:top_k]
    
    def build_search_index(self, force_rebuild: bool = False):
        """Build the search index for semantic queries."""
        self.vector_index.build_index(force_rebuild)
    
    def export_schema(self, file_path: Union[str, Path], format: str = 'json'):
        """
        Export schema to file.
        
        Args:
            file_path: Output file path
            format: Export format ('json' or 'yaml')
        """
        schema = self.explorer.explore_schema()
        file_path = Path(file_path)
        
        if format.lower() == 'json':
            with open(file_path, 'w') as f:
                json.dump(schema.to_dict(), f, indent=2)
        elif format.lower() == 'yaml':
            try:
                import yaml
                with open(file_path, 'w') as f:
                    yaml.dump(schema.to_dict(), f, default_flow_style=False)
            except ImportError:
                raise ImportError("PyYAML required for YAML export")
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Schema exported to {file_path}")


# Legacy function removed - create SchemaManager directly in Agno version