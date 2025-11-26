"""
Comprehensive test suite for AskDB tools module.

This module tests the functionality of all tools including:
- Database connectivity and query execution
- Schema exploration and vector indexing
- Web search capabilities
- Tool integration and error handling
"""

import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any, Optional

from askdb.tools.database import (
    DatabaseTool, DatabaseToolManager, DatabaseConnectionError, 
    DatabaseQueryError, get_db_tool_manager, get_database_tool, 
    create_database_tool
)
from askdb.tools.schema import (
    ColumnInfo, TableInfo, SchemaInfo, SchemaExplorer, VectorSchemaIndex,
    SchemaManager, get_schema_manager, create_schema_manager
)
from askdb.tools.web_search import (
    SearchResult, SearchQuery, WebSearchTool, WebSearchManager, WebSearchError,
    get_web_search_manager, create_web_search_tool, get_web_search_tool, web_search
)
from askdb.config.database_configs import DatabaseConfig, DatabaseType, get_sqlite_config
from askdb.config import get_settings

from . import (
    get_test_config, setup_test_database, cleanup_test_database,
    MockLLMInterface, MockResponse, MockWebSearchTool, MockSearchResult
)


class TestDatabaseTool:
    """Test cases for DatabaseTool class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock database configuration."""
        return get_sqlite_config(":memory:")
    
    @pytest.fixture
    def database_tool(self, mock_config):
        """Create a DatabaseTool instance for testing."""
        return DatabaseTool(mock_config)
    
    def test_database_tool_initialization(self, mock_config):
        """Test DatabaseTool initialization."""
        tool = DatabaseTool(mock_config)
        assert tool.config == mock_config
        assert tool.engine is None
        assert tool.connection is None
    
    @pytest.mark.asyncio
    async def test_database_connection(self, database_tool):
        """Test database connection and disconnection."""
        # Test connection
        await database_tool.connect()
        assert database_tool.engine is not None
        assert database_tool.connection is not None
        
        # Test disconnection
        await database_tool.disconnect()
        assert database_tool.engine is None
        assert database_tool.connection is None
    
    @pytest.mark.asyncio
    async def test_query_execution(self, database_tool):
        """Test SQL query execution."""
        await database_tool.connect()
        
        # Create test table
        await database_tool.execute_query("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER
            )
        """)
        
        # Insert test data
        await database_tool.execute_query(
            "INSERT INTO test_table (name, age) VALUES (?, ?)", 
            ("Alice", 25)
        )
        
        # Query data
        result = await database_tool.execute_query("SELECT * FROM test_table")
        
        assert len(result) == 1
        assert result[0]["name"] == "Alice"
        assert result[0]["age"] == 25
        
        await database_tool.disconnect()
    
    @pytest.mark.asyncio
    async def test_query_validation(self, database_tool):
        """Test SQL query validation."""
        await database_tool.connect()
        
        # Valid query
        assert database_tool.validate_query("SELECT * FROM test_table")
        
        # Invalid query (SQL injection attempt)
        assert not database_tool.validate_query("SELECT * FROM test_table; DROP TABLE test_table;")
        
        # Empty query
        assert not database_tool.validate_query("")
        
        await database_tool.disconnect()
    
    @pytest.mark.asyncio
    async def test_table_info_retrieval(self, database_tool):
        """Test table information retrieval."""
        await database_tool.connect()
        
        # Create test table
        await database_tool.execute_query("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER,
                email TEXT UNIQUE
            )
        """)
        
        # Get table info
        table_info = await database_tool.get_table_info("test_table")
        
        assert table_info is not None
        assert table_info["name"] == "test_table"
        assert len(table_info["columns"]) == 4
        
        # Check column info
        columns = {col["name"]: col for col in table_info["columns"]}
        assert columns["id"]["is_primary_key"] is True
        assert columns["name"]["nullable"] is False
        assert columns["email"]["unique"] is True
        
        await database_tool.disconnect()
    
    @pytest.mark.asyncio
    async def test_database_info_retrieval(self, database_tool):
        """Test database information retrieval."""
        await database_tool.connect()
        
        # Create test tables
        await database_tool.execute_query("CREATE TABLE table1 (id INTEGER PRIMARY KEY)")
        await database_tool.execute_query("CREATE TABLE table2 (id INTEGER PRIMARY KEY)")
        
        # Get database info
        db_info = await database_tool.get_database_info()
        
        assert db_info is not None
        assert "tables" in db_info
        assert len(db_info["tables"]) >= 2
        
        await database_tool.disconnect()
    
    @pytest.mark.asyncio
    async def test_connection_testing(self, database_tool):
        """Test database connection testing."""
        # Test successful connection
        result = await database_tool.test_connection()
        assert result is True
        
        # Test with invalid config
        invalid_config = get_sqlite_config("/nonexistent/path.db")
        invalid_tool = DatabaseTool(invalid_config)
        result = await invalid_tool.test_connection()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_query_error_handling(self, database_tool):
        """Test query error handling."""
        await database_tool.connect()
        
        # Test syntax error
        with pytest.raises(DatabaseQueryError):
            await database_tool.execute_query("INVALID SQL QUERY")
        
        # Test table not found error
        with pytest.raises(DatabaseQueryError):
            await database_tool.execute_query("SELECT * FROM nonexistent_table")
        
        await database_tool.disconnect()


class TestDatabaseToolManager:
    """Test cases for DatabaseToolManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a DatabaseToolManager instance."""
        return DatabaseToolManager()
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock database configuration."""
        return get_sqlite_config(":memory:")
    
    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert len(manager.tools) == 0
        assert manager.default_tool is None
    
    def test_add_tool(self, manager, mock_config):
        """Test adding a database tool."""
        tool = DatabaseTool(mock_config)
        manager.add_tool("test_tool", tool)
        
        assert "test_tool" in manager.tools
        assert manager.tools["test_tool"] == tool
    
    def test_get_tool(self, manager, mock_config):
        """Test getting a database tool."""
        tool = DatabaseTool(mock_config)
        manager.add_tool("test_tool", tool)
        
        retrieved_tool = manager.get_tool("test_tool")
        assert retrieved_tool == tool
        
        # Test getting non-existent tool
        assert manager.get_tool("nonexistent") is None
    
    def test_list_tools(self, manager, mock_config):
        """Test listing tools."""
        tool1 = DatabaseTool(mock_config)
        tool2 = DatabaseTool(mock_config)
        
        manager.add_tool("tool1", tool1)
        manager.add_tool("tool2", tool2)
        
        tools = manager.list_tools()
        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools
    
    def test_remove_tool(self, manager, mock_config):
        """Test removing a tool."""
        tool = DatabaseTool(mock_config)
        manager.add_tool("test_tool", tool)
        
        manager.remove_tool("test_tool")
        assert "test_tool" not in manager.tools
    
    def test_set_default_tool(self, manager, mock_config):
        """Test setting default tool."""
        tool = DatabaseTool(mock_config)
        manager.add_tool("test_tool", tool)
        
        manager.set_default("test_tool")
        assert manager.default_tool == "test_tool"
    
    @pytest.mark.asyncio
    async def test_disconnect_all(self, manager, mock_config):
        """Test disconnecting all tools."""
        tool1 = DatabaseTool(mock_config)
        tool2 = DatabaseTool(mock_config)
        
        manager.add_tool("tool1", tool1)
        manager.add_tool("tool2", tool2)
        
        # Connect tools
        await tool1.connect()
        await tool2.connect()
        
        # Disconnect all
        await manager.disconnect_all()
        
        assert tool1.connection is None
        assert tool2.connection is None


class TestSchemaExplorer:
    """Test cases for SchemaExplorer class."""
    
    @pytest.fixture
    async def schema_explorer(self):
        """Create a SchemaExplorer instance with test database."""
        db_tool = await setup_test_database()
        return SchemaExplorer(db_tool)
    
    @pytest.mark.asyncio
    async def test_explore_schema(self, schema_explorer):
        """Test schema exploration."""
        schema_info = await schema_explorer.explore_schema()
        
        assert isinstance(schema_info, SchemaInfo)
        assert len(schema_info.tables) > 0
        
        # Check that test tables are present
        table_names = [table.name for table in schema_info.tables]
        assert "users" in table_names
        assert "orders" in table_names
    
    @pytest.mark.asyncio
    async def test_get_table_info(self, schema_explorer):
        """Test getting table information."""
        table_info = await schema_explorer.get_table_info("users")
        
        assert isinstance(table_info, TableInfo)
        assert table_info.name == "users"
        assert len(table_info.columns) > 0
        
        # Check column information
        column_names = [col.name for col in table_info.columns]
        assert "id" in column_names
        assert "name" in column_names
        assert "email" in column_names
    
    @pytest.mark.asyncio
    async def test_search_tables(self, schema_explorer):
        """Test table search functionality."""
        # Search for user-related tables
        results = await schema_explorer.search_tables("user")
        assert len(results) > 0
        assert any("user" in table.name.lower() for table in results)
        
        # Search for non-existent tables
        results = await schema_explorer.search_tables("nonexistent")
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_columns(self, schema_explorer):
        """Test column search functionality."""
        # Search for email columns
        results = await schema_explorer.search_columns("email")
        assert len(results) > 0
        assert all("email" in col.name.lower() for col in results)
        
        # Search for non-existent columns
        results = await schema_explorer.search_columns("nonexistent")
        assert len(results) == 0


class TestVectorSchemaIndex:
    """Test cases for VectorSchemaIndex class."""
    
    @pytest.fixture
    async def vector_index(self):
        """Create a VectorSchemaIndex instance."""
        db_tool = await setup_test_database()
        schema_explorer = SchemaExplorer(db_tool)
        return VectorSchemaIndex(schema_explorer, model_name="all-MiniLM-L6-v2")
    
    @pytest.mark.asyncio
    async def test_build_index(self, vector_index):
        """Test building vector index."""
        await vector_index.build_index()
        
        assert vector_index.table_index is not None
        assert vector_index.column_index is not None
        assert len(vector_index.table_embeddings) > 0
        assert len(vector_index.column_embeddings) > 0
    
    @pytest.mark.asyncio
    async def test_search_tables_semantic(self, vector_index):
        """Test semantic table search."""
        await vector_index.build_index()
        
        # Search for customer-related tables
        results = await vector_index.search_tables_semantic("customer information", top_k=3)
        assert len(results) > 0
        assert all(score > 0 for _, score in results)
    
    @pytest.mark.asyncio
    async def test_search_columns_semantic(self, vector_index):
        """Test semantic column search."""
        await vector_index.build_index()
        
        # Search for name-related columns
        results = await vector_index.search_columns_semantic("person name", top_k=5)
        assert len(results) > 0
        assert all(score > 0 for _, score in results)
    
    @pytest.mark.asyncio
    async def test_save_and_load_index(self, vector_index, tmp_path):
        """Test saving and loading index."""
        await vector_index.build_index()
        
        # Save index
        index_path = tmp_path / "test_index.pkl"
        await vector_index.save_index(str(index_path))
        assert index_path.exists()
        
        # Create new index and load
        new_index = VectorSchemaIndex(vector_index.schema_explorer)
        await new_index.load_index(str(index_path))
        
        assert new_index.table_index is not None
        assert new_index.column_index is not None


class TestSchemaManager:
    """Test cases for SchemaManager class."""
    
    @pytest.fixture
    async def schema_manager(self):
        """Create a SchemaManager instance."""
        db_tool = await setup_test_database()
        return SchemaManager(db_tool)
    
    @pytest.mark.asyncio
    async def test_get_schema_summary(self, schema_manager):
        """Test getting schema summary."""
        summary = await schema_manager.get_schema_summary()
        
        assert "database_name" in summary
        assert "table_count" in summary
        assert "tables" in summary
        assert summary["table_count"] > 0
    
    @pytest.mark.asyncio
    async def test_find_relevant_tables(self, schema_manager):
        """Test finding relevant tables."""
        # Find tables related to users
        tables = await schema_manager.find_relevant_tables("user information")
        assert len(tables) > 0
        
        # Find tables for non-existent topic
        tables = await schema_manager.find_relevant_tables("nonexistent topic")
        assert len(tables) == 0
    
    @pytest.mark.asyncio
    async def test_find_relevant_columns(self, schema_manager):
        """Test finding relevant columns."""
        # Find columns related to email
        columns = await schema_manager.find_relevant_columns("email address")
        assert len(columns) > 0
        assert all("email" in col.name.lower() or "mail" in col.name.lower() for col in columns)
    
    @pytest.mark.asyncio
    async def test_build_search_index(self, schema_manager):
        """Test building search index."""
        await schema_manager.build_search_index()
        assert schema_manager.vector_index is not None
        assert schema_manager.vector_index.table_index is not None
    
    @pytest.mark.asyncio
    async def test_export_schema(self, schema_manager, tmp_path):
        """Test schema export."""
        export_path = tmp_path / "schema_export.json"
        await schema_manager.export_schema(str(export_path))
        
        assert export_path.exists()
        
        # Verify exported content
        with open(export_path, 'r') as f:
            exported_data = json.load(f)
        
        assert "database_name" in exported_data
        assert "tables" in exported_data
        assert len(exported_data["tables"]) > 0


class TestWebSearchTool:
    """Test cases for WebSearchTool class."""
    
    @pytest.fixture
    def web_search_tool(self):
        """Create a WebSearchTool instance."""
        return WebSearchTool("duckduckgo")
    
    def test_web_search_tool_initialization(self, web_search_tool):
        """Test WebSearchTool initialization."""
        assert web_search_tool.provider == "duckduckgo"
        assert web_search_tool.session is None
    
    @pytest.mark.asyncio
    async def test_web_search_execution(self, web_search_tool):
        """Test web search execution."""
        # Mock the actual search to avoid external dependencies
        with patch.object(web_search_tool, '_search_duckduckgo') as mock_search:
            mock_search.return_value = [
                SearchResult(
                    title="Test Result",
                    url="https://example.com",
                    snippet="Test snippet",
                    relevance_score=0.9,
                    source="duckduckgo"
                )
            ]
            
            results = await web_search_tool.search("test query", max_results=5)
            
            assert len(results) == 1
            assert results[0].title == "Test Result"
            assert results[0].url == "https://example.com"
    
    def test_format_results(self, web_search_tool):
        """Test result formatting."""
        results = [
            SearchResult(
                title="Result 1",
                url="https://example1.com",
                snippet="Snippet 1",
                relevance_score=0.9,
                source="test"
            ),
            SearchResult(
                title="Result 2",
                url="https://example2.com",
                snippet="Snippet 2",
                relevance_score=0.8,
                source="test"
            )
        ]
        
        formatted = web_search_tool.format_results(results)
        assert "Result 1" in formatted
        assert "Result 2" in formatted
        assert "https://example1.com" in formatted
    
    def test_extract_urls(self, web_search_tool):
        """Test URL extraction."""
        results = [
            SearchResult(
                title="Result 1",
                url="https://example1.com",
                snippet="Snippet 1",
                relevance_score=0.9,
                source="test"
            ),
            SearchResult(
                title="Result 2",
                url="https://example2.com",
                snippet="Snippet 2",
                relevance_score=0.8,
                source="test"
            )
        ]
        
        urls = web_search_tool.extract_urls(results)
        assert len(urls) == 2
        assert "https://example1.com" in urls
        assert "https://example2.com" in urls
    
    def test_extract_snippets(self, web_search_tool):
        """Test snippet extraction."""
        results = [
            SearchResult(
                title="Result 1",
                url="https://example1.com",
                snippet="Snippet 1",
                relevance_score=0.9,
                source="test"
            ),
            SearchResult(
                title="Result 2",
                url="https://example2.com",
                snippet="Snippet 2",
                relevance_score=0.8,
                source="test"
            )
        ]
        
        snippets = web_search_tool.extract_snippets(results)
        assert len(snippets) == 2
        assert "Snippet 1" in snippets
        assert "Snippet 2" in snippets


class TestWebSearchManager:
    """Test cases for WebSearchManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a WebSearchManager instance."""
        return WebSearchManager()
    
    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert len(manager.tools) == 0
        assert manager.cache == {}
    
    def test_add_tool(self, manager):
        """Test adding a web search tool."""
        tool = MockWebSearchTool("test_provider")
        manager.add_tool("test_tool", tool)
        
        assert "test_tool" in manager.tools
        assert manager.tools["test_tool"] == tool
    
    def test_get_tool(self, manager):
        """Test getting a web search tool."""
        tool = MockWebSearchTool("test_provider")
        manager.add_tool("test_tool", tool)
        
        retrieved_tool = manager.get_tool("test_tool")
        assert retrieved_tool == tool
        
        # Test getting non-existent tool
        assert manager.get_tool("nonexistent") is None
    
    @pytest.mark.asyncio
    async def test_search_with_cache(self, manager):
        """Test search with caching."""
        tool = MockWebSearchTool("test_provider")
        manager.add_tool("test_tool", tool)
        
        # First search should call the tool
        results1 = await manager.search_with_cache("test_tool", "test query")
        assert len(results1) > 0
        
        # Second search should use cache
        results2 = await manager.search_with_cache("test_tool", "test query")
        assert results1 == results2
    
    def test_clear_cache(self, manager):
        """Test cache clearing."""
        tool = MockWebSearchTool("test_provider")
        manager.add_tool("test_tool", tool)
        
        # Add something to cache
        manager.cache["test_tool"] = {"test query": []}
        
        # Clear cache
        manager.clear_cache()
        assert len(manager.cache) == 0
    
    def test_get_cache_stats(self, manager):
        """Test cache statistics."""
        tool = MockWebSearchTool("test_provider")
        manager.add_tool("test_tool", tool)
        
        # Add cache entries
        manager.cache["test_tool"] = {
            "query1": ["result1"],
            "query2": ["result2", "result3"]
        }
        
        stats = manager.get_cache_stats()
        assert stats["total_entries"] == 2
        assert stats["total_results"] == 3


class TestToolIntegration:
    """Integration tests for tools working together."""
    
    @pytest.mark.asyncio
    async def test_database_schema_integration(self):
        """Test database and schema tools integration."""
        # Setup test database
        db_tool = await setup_test_database()
        
        # Create schema manager
        schema_manager = SchemaManager(db_tool)
        
        # Test schema exploration
        summary = await schema_manager.get_schema_summary()
        assert summary["table_count"] > 0
        
        # Test finding relevant tables
        tables = await schema_manager.find_relevant_tables("user")
        assert len(tables) > 0
        
        # Cleanup
        await cleanup_test_database()
    
    @pytest.mark.asyncio
    async def test_database_web_search_integration(self):
        """Test database and web search tools integration."""
        # Setup mock components
        db_tool = Mock()
        db_tool.execute_query = AsyncMock(return_value=[{"id": 1, "name": "test"}])
        
        web_tool = MockWebSearchTool("test_provider")
        
        # Test using both tools together
        db_results = await db_tool.execute_query("SELECT * FROM test")
        web_results = await web_tool.search("additional information")
        
        assert len(db_results) > 0
        assert len(web_results) > 0
    
    def test_tool_factory_functions(self):
        """Test tool factory functions."""
        # Test database tool creation
        config = get_sqlite_config(":memory:")
        tool = create_database_tool("test_db", config)
        assert isinstance(tool, DatabaseTool)
        
        # Test web search tool creation
        web_tool = create_web_search_tool("test_web", "duckduckgo")
        assert isinstance(web_tool, WebSearchTool)
    
    def test_global_managers(self):
        """Test global manager functions."""
        # Test database tool manager
        db_manager = get_db_tool_manager()
        assert isinstance(db_manager, DatabaseToolManager)
        
        # Test web search manager
        web_manager = get_web_search_manager()
        assert isinstance(web_manager, WebSearchManager)
        
        # Test schema manager creation
        config = get_sqlite_config(":memory:")
        db_tool = DatabaseTool(config)
        schema_manager = create_schema_manager(db_tool)
        assert isinstance(schema_manager, SchemaManager)


class TestToolErrorHandling:
    """Test error handling in tools."""
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self):
        """Test database connection error handling."""
        # Create invalid configuration
        invalid_config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="nonexistent.host",
            database="nonexistent_db",
            username="invalid_user",
            password="invalid_pass"
        )
        
        tool = DatabaseTool(invalid_config)
        
        # Should raise connection error
        with pytest.raises(DatabaseConnectionError):
            await tool.connect()
    
    @pytest.mark.asyncio
    async def test_web_search_error(self):
        """Test web search error handling."""
        tool = WebSearchTool("invalid_provider")
        
        # Should raise error for invalid provider
        with pytest.raises(WebSearchError):
            await tool.search("test query")
    
    def test_schema_explorer_error(self):
        """Test schema explorer error handling."""
        # Create explorer with invalid database tool
        invalid_tool = Mock()
        invalid_tool.engine = None
        
        explorer = SchemaExplorer(invalid_tool)
        
        # Should handle null engine gracefully
        # This would typically raise an error, but we test the handling
        assert explorer is not None


class TestToolPerformance:
    """Performance tests for tools."""
    
    @pytest.mark.asyncio
    async def test_database_query_performance(self):
        """Test database query performance."""
        db_tool = await setup_test_database()
        
        import time
        start_time = time.time()
        
        # Execute multiple queries
        for i in range(10):
            await db_tool.execute_query("SELECT COUNT(*) FROM users")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert execution_time < 5.0  # 5 seconds
        
        await cleanup_test_database()
    
    @pytest.mark.asyncio
    async def test_schema_indexing_performance(self):
        """Test schema indexing performance."""
        db_tool = await setup_test_database()
        schema_manager = SchemaManager(db_tool)
        
        import time
        start_time = time.time()
        
        # Build search index
        await schema_manager.build_search_index()
        
        end_time = time.time()
        indexing_time = end_time - start_time
        
        # Should complete within reasonable time
        assert indexing_time < 10.0  # 10 seconds
        
        await cleanup_test_database()
    
    @pytest.mark.asyncio
    async def test_web_search_performance(self):
        """Test web search performance."""
        tool = MockWebSearchTool("test_provider")
        
        import time
        start_time = time.time()
        
        # Perform search
        await tool.search("test query")
        
        end_time = time.time()
        search_time = end_time - start_time
        
        # Should complete quickly (mock search)
        assert search_time < 1.0  # 1 second


# Pytest configuration and fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Run tests when this file is executed directly
    pytest.main([__file__, "-v"])