"""
AskDB Test Suite

This module contains comprehensive tests for the AskDB LLM-powered database agent.
The test suite covers all major components including:

- Agent functionality and ReAct framework
- Database tools and schema exploration
- Safety protocols and risk assessment
- LLM interface and conversation management
- Integration tests and end-to-end scenarios

Test Structure:
- test_agent.py: Core agent functionality tests
- test_tools.py: Database, schema, and web search tool tests
- test_safety.py: Safety protocol and risk assessment tests

Running Tests:
    # Run all tests
    python -m pytest askdb/tests/
    
    # Run specific test file
    python -m pytest askdb/tests/test_agent.py
    
    # Run with coverage
    python -m pytest askdb/tests/ --cov=askdb
    
    # Run with verbose output
    python -m pytest askdb/tests/ -v
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_CONFIG = {
    "database": {
        "test_db_url": "sqlite:///test_askdb.db",
        "test_schema": {
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True},
                        {"name": "name", "type": "VARCHAR(100)", "nullable": False},
                        {"name": "email", "type": "VARCHAR(255)", "unique": True},
                        {"name": "age", "type": "INTEGER"},
                        {"name": "created_at", "type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP"}
                    ]
                },
                {
                    "name": "products",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True},
                        {"name": "name", "type": "VARCHAR(200)", "nullable": False},
                        {"name": "price", "type": "DECIMAL(10,2)", "nullable": False},
                        {"name": "category", "type": "VARCHAR(100)"},
                        {"name": "stock", "type": "INTEGER", "default": 0}
                    ]
                },
                {
                    "name": "orders",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "primary_key": True},
                        {"name": "user_id", "type": "INTEGER", "foreign_key": "users.id"},
                        {"name": "product_id", "type": "INTEGER", "foreign_key": "products.id"},
                        {"name": "quantity", "type": "INTEGER", "nullable": False},
                        {"name": "total_price", "type": "DECIMAL(10,2)", "nullable": False},
                        {"name": "order_date", "type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP"}
                    ]
                }
            ]
        }
    },
    "llm": {
        "mock_responses": {
            "simple_query": "SELECT COUNT(*) FROM users;",
            "complex_query": "SELECT u.name, COUNT(o.id) as order_count FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name ORDER BY order_count DESC;",
            "explanation": "This query retrieves user names along with their order counts by joining the users and orders tables."
        }
    },
    "safety": {
        "safe_queries": [
            "SELECT * FROM users WHERE age > 18;",
            "SELECT COUNT(*) FROM products;",
            "SELECT name, price FROM products WHERE category = 'electronics';"
        ],
        "unsafe_queries": [
            "DROP TABLE users;",
            "DELETE FROM users WHERE 1=1;",
            "UPDATE users SET name = 'Hacked' WHERE 1=1;",
            "INSERT INTO users (name) VALUES (''); SELECT * FROM users; --"
        ],
        "pii_samples": [
            "My email is john.doe@example.com",
            "Call me at 555-123-4567",
            "My SSN is 123-45-6789",
            "Credit card: 4111-1111-1111-1111"
        ]
    }
}

# Test utilities
def get_test_config():
    """Get test configuration dictionary."""
    return TEST_CONFIG

def setup_test_database():
    """Set up test database with sample schema."""
    from askdb.tools.database import DatabaseTool
    from askdb.config.database_configs import get_sqlite_config
    
    config = get_sqlite_config(TEST_CONFIG["database"]["test_db_url"])
    db_tool = DatabaseTool(config)
    
    # Create tables
    create_statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE,
            age INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            category VARCHAR(100),
            stock INTEGER DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER NOT NULL,
            total_price DECIMAL(10,2) NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """
    ]
    
    try:
        db_tool.connect()
        for statement in create_statements:
            db_tool.execute_query(statement)
        
        # Insert sample data
        sample_data = [
            "INSERT INTO users (name, email, age) VALUES ('John Doe', 'john@example.com', 30), ('Jane Smith', 'jane@example.com', 25), ('Bob Johnson', 'bob@example.com', 35);",
            "INSERT INTO products (name, price, category, stock) VALUES ('Laptop', 999.99, 'Electronics', 50), ('Book', 19.99, 'Books', 100), ('Coffee', 4.99, 'Food', 200);",
            "INSERT INTO orders (user_id, product_id, quantity, total_price) VALUES (1, 1, 1, 999.99), (2, 2, 2, 39.98), (1, 3, 5, 24.95);"
        ]
        
        for data in sample_data:
            db_tool.execute_query(data)
            
        return db_tool
    except Exception as e:
        print(f"Error setting up test database: {e}")
        return None

def cleanup_test_database():
    """Clean up test database."""
    import os
    db_path = TEST_CONFIG["database"]["test_db_url"].replace("sqlite:///", "")
    if os.path.exists(db_path):
        os.remove(db_path)

# Mock classes for testing
class MockLLMInterface:
    """Mock LLM interface for testing."""
    
    def __init__(self, config=None):
        self.config = config
        self.call_count = 0
        self.last_prompt = None
        self.responses = TEST_CONFIG["llm"]["mock_responses"]
    
    async def generate_async(self, prompt, **kwargs):
        """Mock async generation."""
        self.call_count += 1
        self.last_prompt = prompt
        
        # Simple keyword-based response selection
        prompt_lower = prompt.lower()
        if "count" in prompt_lower and "users" in prompt_lower:
            return MockResponse(self.responses["simple_query"])
        elif "join" in prompt_lower or "order" in prompt_lower:
            return MockResponse(self.responses["complex_query"])
        elif "explain" in prompt_lower:
            return MockResponse(self.responses["explanation"])
        else:
            return MockResponse("SELECT * FROM users LIMIT 10;")
    
    def generate(self, prompt, **kwargs):
        """Mock sync generation."""
        import asyncio
        return asyncio.run(self.generate_async(prompt, **kwargs))
    
    def validate_config(self):
        """Mock config validation."""
        return True

class MockResponse:
    """Mock LLM response."""
    
    def __init__(self, content, model="mock-model", provider="mock"):
        self.content = content
        self.model = model
        self.provider = provider
        self.tokens_used = len(content.split())
        self.finish_reason = "stop"
        self.metadata = {"mock": True}

class MockWebSearchTool:
    """Mock web search tool for testing."""
    
    def __init__(self, provider="mock"):
        self.provider = provider
        self.search_count = 0
    
    async def search(self, query, max_results=5, **kwargs):
        """Mock search."""
        self.search_count += 1
        return [
            MockSearchResult(
                title=f"Result {i} for '{query}'",
                url=f"https://example.com/result{i}",
                snippet=f"This is snippet {i} for the search query.",
                relevance_score=1.0 - (i * 0.1)
            )
            for i in range(min(max_results, 3))
        ]

class MockSearchResult:
    """Mock search result."""
    
    def __init__(self, title, url, snippet, relevance_score=1.0):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.relevance_score = relevance_score
        self.source = "mock"
        self.timestamp = None

# Test fixtures and utilities
def create_mock_agent():
    """Create a mock agent for testing."""
    from askdb.agent.core import AskDBAgent
    from askdb.models.conversation import ConversationManager
    from askdb.agent.safety import SafetyManager
    from askdb.agent.prompting import PromptManager
    
    # Set up test database
    db_tool = setup_test_database()
    if not db_tool:
        raise RuntimeError("Failed to set up test database")
    
    # Create mock components
    llm_interface = MockLLMInterface()
    conversation_manager = ConversationManager()
    safety_manager = SafetyManager()
    prompt_manager = PromptManager()
    
    # Create agent
    agent = AskDBAgent(
        settings=None,
        llm_interface=llm_interface,
        database_tool=db_tool,
        schema_manager=None,
        web_search_tool=MockWebSearchTool(),
        max_steps=5,
        max_retries=2
    )
    
    # Replace managers with mocks
    agent.conversation_manager = conversation_manager
    agent.safety_manager = safety_manager
    agent.prompt_manager = prompt_manager
    
    return agent, db_tool

def assert_query_result(result, expected_columns=None, min_rows=0):
    """Assert query result meets expectations."""
    assert result is not None, "Query result should not be None"
    assert "data" in result, "Result should contain data"
    assert "columns" in result, "Result should contain columns"
    
    if expected_columns:
        for col in expected_columns:
            assert col in result["columns"], f"Expected column '{col}' not found"
    
    if min_rows > 0:
        assert len(result["data"]) >= min_rows, f"Expected at least {min_rows} rows, got {len(result['data'])}"

def assert_safety_assessment(assessment, expected_risk_level=None, should_be_safe=None):
    """Assert safety assessment meets expectations."""
    assert assessment is not None, "Safety assessment should not be None"
    assert hasattr(assessment, 'risk_level'), "Assessment should have risk_level"
    assert hasattr(assessment, 'is_safe'), "Assessment should have is_safe"
    
    if expected_risk_level:
        assert assessment.risk_level == expected_risk_level, f"Expected risk level {expected_risk_level}, got {assessment.risk_level}"
    
    if should_be_safe is not None:
        assert assessment.is_safe == should_be_safe, f"Expected is_safe={should_be_safe}, got {assessment.is_safe}"

# Export test utilities
__all__ = [
    "TEST_CONFIG",
    "get_test_config",
    "setup_test_database",
    "cleanup_test_database",
    "MockLLMInterface",
    "MockResponse",
    "MockWebSearchTool",
    "MockSearchResult",
    "create_mock_agent",
    "assert_query_result",
    "assert_safety_assessment"
]

# Version info
__version__ = "1.0.0"
__author__ = "AskDB Development Team"
__description__ = "Test suite for AskDB LLM-powered database agent"