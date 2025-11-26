# AskDB: LLM-Powered Agent for Natural Language Database Interaction

AskDB is a sophisticated LLM-powered database agent that bridges natural language interaction with relational databases through a ReAct-based cognitive framework, dynamic schema-aware prompting, and multi-layered safety protocols.

## 🚀 Features

- **ReAct-based Cognitive Framework**: Multi-step reasoning and autonomous SQL debugging
- **Dynamic Schema-Aware Prompting**: Vector-based semantic table discovery with context-aware prompt generation
- **Multi-Layered Safety Protocols**: Risk classification, PII detection, and automated guardrails
- **Multi-Database Support**: PostgreSQL, MySQL, SQLite, SQL Server
- **Natural Language to SQL**: Conversation context retention and multi-turn interaction
- **Automated SQL Debugging**: Self-correction capabilities with error analysis
- **Web Search Integration**: External knowledge retrieval for enhanced query understanding
- **Comprehensive Evaluation**: Spider benchmark compatibility
- **Provider-Agnostic LLM Interface**: Gemini integration with extensible architecture
- **Multiple Interfaces**: CLI and optional web-based user interfaces

## 📋 Requirements

### Required Packages
- `openai>=1.0.0` - OpenAI API integration
- `google-generativeai>=0.3.0` - Google Gemini models
- `sqlalchemy>=2.0.0` - Database ORM and connection management
- `psycopg2-binary>=2.9.0` - PostgreSQL adapter
- `pymysql>=1.1.0` - MySQL adapter
- `sentence-transformers>=2.2.0` - Semantic embeddings for schema search
- `numpy>=1.24.0` - Numerical computations
- `scipy>=1.10.0` - Scientific computing
- `pydantic>=2.0.0` - Data validation and settings management
- `python-dotenv>=1.0.0` - Environment variable management
- `rich>=13.0.0` - Rich terminal formatting
- `click>=8.0.0` - CLI framework

### Optional Packages
- `faiss-cpu>=1.7.0` - Efficient vector similarity search
- `aiohttp>=3.8.0` - Async web search capabilities
- `streamlit>=1.28.0` - Web UI option
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async testing support

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd askdb
   ```

2. **Create virtual environment**
   ```bash
   python -m venv askdb_env
   source askdb_env/bin/activate  # On Windows: askdb_env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configurations
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# LLM Configuration
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
DEFAULT_LLM_PROVIDER=openai  # or google

# Database Configuration
DEFAULT_DB_TYPE=postgresql
DEFAULT_DB_HOST=localhost
DEFAULT_DB_PORT=5432
DEFAULT_DB_NAME=your_database
DEFAULT_DB_USER=your_username
DEFAULT_DB_PASSWORD=your_password

# Safety Configuration
ENABLE_SAFETY_CHECKS=true
MAX_RISK_LEVEL=medium
LOG_LEVEL=INFO

# Web Search Configuration
WEB_SEARCH_PROVIDER=duckduckgo
GOOGLE_SEARCH_API_KEY=your_google_search_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
```

### Database Configuration

AskDB supports multiple database engines:

```python
# PostgreSQL
askdb database add postgres --host localhost --port 5432 --database mydb --user myuser --password mypass

# MySQL
askdb database add mysql --host localhost --port 3306 --database mydb --user myuser --password mypass

# SQLite
askdb database add sqlite --database /path/to/database.db

# SQL Server
askdb database add sqlserver --host localhost --port 1433 --database mydb --user myuser --password mypass
```

## 🚀 Quick Start

### Command Line Interface

1. **Interactive Mode**
   ```bash
   askdb interactive
   ```

2. **Single Query**
   ```bash
   askdb query "Show me all customers from California" --database mydb
   ```

3. **Database Management**
   ```bash
   # List databases
   askdb database list
   
   # Test connection
   askdb database test mydb
   
   # Show schema
   askdb database schema mydb
   ```

### Python API

```python
from askdb import create_agent
from askdb.config import DatabaseConfig, DatabaseType

# Configure database
db_config = DatabaseConfig(
    db_type=DatabaseType.POSTGRESQL,
    host="localhost",
    database="mydb",
    username="user",
    password="password"
)

# Create agent
agent = create_agent(database_tool=db_config)

# Process query
result = agent.process_query("Show me all customers from California")
print(result.response)
```

## 📖 Usage Examples

### Natural Language Queries

```bash
# Basic queries
askdb query "How many products do we have?"
askdb query "Show me the top 5 customers by revenue"

# Complex queries with joins
askdb query "Find all orders placed by customers from New York in the last month"

# Analytical queries
askdb query "What is the average order value by product category?"
askdb query "Show me monthly sales trends for this year"
```

### Interactive Mode Features

- **Multi-turn conversations**: Context is maintained across queries
- **Clarification requests**: Agent asks for clarification when needed
- **Error explanations**: Detailed feedback when queries fail
- **Result formatting**: Multiple output formats (table, json, csv)

```bash
$ askdb interactive
AskDB Interactive Mode
Type 'exit' to quit, 'help' for commands

> Show me all customers
Found 150 customers. Would you like to see them all or apply a filter?
> Show me only active customers
Found 92 active customers. Displaying first 10:
+----+----------------+-------------------+---------+
| ID | Name           | Email             | Status  |
+----+----------------+-------------------+---------+
| 1  | John Doe       | john@example.com  | Active  |
| 2  | Jane Smith     | jane@example.com  | Active  |
+----+----------------+-------------------+---------+

> What's the total revenue from these customers?
The total revenue from active customers is $1,234,567.89
```

## 🔧 Advanced Configuration

### Custom LLM Providers

```python
from askdb.models import LLMInterface
from askdb.config import get_settings

settings = get_settings()
llm_config = settings.get_llm_config()

# Configure custom provider
llm_interface = LLMInterface(
    provider="custom",
    model="custom-model",
    api_key="your-api-key",
    **llm_config
)
```

### Safety Configuration

```python
from askdb.agent.safety import SafetyManager, RiskLevel

safety_manager = SafetyManager()
safety_manager.max_risk_level = RiskLevel.MEDIUM
safety_manager.enable_pii_detection = True
safety_manager.enable_sql_injection_check = True
```

### Schema Indexing

```python
from askdb.tools import SchemaManager

schema_manager = SchemaManager(database_tool)
schema_manager.build_search_index()

# Semantic search for relevant tables
relevant_tables = schema_manager.find_relevant_tables("customer orders")
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_agent.py
pytest tests/test_tools.py
pytest tests/test_safety.py

# Run with coverage
pytest --cov=askdb tests/
```

### Spider Benchmark Compatibility

AskDB includes evaluation framework compatible with Spider benchmark:

```python
from askdb.evaluation import SpiderEvaluator

evaluator = SpiderEvaluator()
results = evaluator.evaluate_on_spider(
    dataset_path="path/to/spider/dataset",
    output_dir="evaluation_results"
)
```

## 🏗️ Architecture

### Core Components

1. **Agent Core** (`askdb/agent/core.py`)
   - ReAct-based cognitive framework
   - Multi-step reasoning and planning
   - Tool orchestration and execution

2. **Dynamic Prompting** (`askdb/agent/prompting.py`)
   - Schema-aware prompt generation
   - Context-aware template system
   - Semantic table discovery

3. **Safety Protocols** (`askdb/agent/safety.py`)
   - Risk classification and assessment
   - PII detection and filtering
   - SQL injection prevention

4. **Tool System** (`askdb/tools/`)
   - Database connectivity and query execution
   - Schema exploration and indexing
   - Web search integration

5. **Model Interface** (`askdb/models/`)
   - LLM provider abstraction
   - Conversation management
   - Response handling

### Data Flow

```
User Query → Safety Check → Schema Analysis → Prompt Generation → LLM Processing → Tool Execution → Result Validation → Response
```

## 🔒 Security Features

- **Multi-layered Safety**: Risk assessment, PII detection, SQL injection prevention
- **Query Validation**: Syntax checking, complexity analysis, permission verification
- **Output Filtering**: Sensitive data redaction, result sanitization
- **Audit Logging**: Complete query execution history with security events

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
pytest

# Run linting
flake8 askdb/
black askdb/

# Run type checking
mypy askdb/
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Test database connection
   askdb database test your_db_name
   
   # Check configuration
   askdb status
   ```

2. **LLM API Errors**
   - Verify API keys in `.env` file
   - Check network connectivity
   - Review API rate limits

3. **Schema Indexing Issues**
   ```bash
   # Rebuild schema index
   askdb database schema your_db_name --rebuild
   ```

4. **Safety Check Failures**
   - Review query complexity
   - Check for potential PII or injection patterns
   - Adjust risk level settings

### Debug Mode

Enable debug logging:

```bash
askdb --verbose query "your query"
```

Or set in `.env`:
```env
LOG_LEVEL=DEBUG
```

## 📚 Additional Resources

- [API Documentation](docs/api.md)
- [Configuration Guide](docs/configuration.md)
- [Safety Protocols](docs/safety.md)
- [Benchmark Results](docs/benchmarks.md)
- [Frequently Asked Questions](docs/faq.md)

## 🌟 Acknowledgments

- Built with inspiration from ReAct (Reasoning and Acting) framework
- Integrates state-of-the-art LLM models for natural language understanding
- Leverages sentence-transformers for semantic search capabilities
- Compatible with Spider benchmark for text-to-SQL evaluation

---

**AskDB Development Team**  
*Making databases accessible through natural language*