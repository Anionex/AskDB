"""
Dynamic Schema-Aware Prompting Mechanism for AskDB

This module implements the dynamic prompting system that adapts prompts
based on database schema, user context, and conversation history.
Includes vector-based semantic table discovery and context-aware prompt generation.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
import re

from ..config import get_settings
from ..tools import SchemaManager, DatabaseTool

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """Types of prompts used by the agent."""
    
    SYSTEM = "system"
    USER_QUERY = "user_query"
    SQL_GENERATION = "sql_generation"
    SCHEMA_AWARE = "schema_aware"
    DEBUGGING = "debugging"
    CLARIFICATION = "clarification"
    RESULT_FORMATTING = "result_formatting"
    SAFETY_CHECK = "safety_check"
    WEB_SEARCH = "web_search"
    CONVERSATION = "conversation"


@dataclass
class PromptContext:
    """Context information for prompt generation."""
    
    user_query: str
    database_schema: Optional[Dict[str, Any]] = None
    relevant_tables: List[str] = field(default_factory=list)
    relevant_columns: List[str] = field(default_factory=list)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    previous_queries: List[str] = field(default_factory=list)
    previous_errors: List[str] = field(default_factory=list)
    user_intent: Optional[str] = None
    query_complexity: str = "medium"  # simple, medium, complex
    risk_level: str = "low"  # low, medium, high
    external_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "user_query": self.user_query,
            "database_schema": self.database_schema,
            "relevant_tables": self.relevant_tables,
            "relevant_columns": self.relevant_columns,
            "conversation_history": self.conversation_history,
            "previous_queries": self.previous_queries,
            "previous_errors": self.previous_errors,
            "user_intent": self.user_intent,
            "query_complexity": self.query_complexity,
            "risk_level": self.risk_level,
            "external_context": self.external_context
        }


@dataclass
class PromptTemplate:
    """Template for generating prompts."""
    
    name: str
    prompt_type: PromptType
    template: str
    variables: List[str] = field(default_factory=list)
    description: str = ""
    examples: List[Dict[str, str]] = field(default_factory=list)
    
    def render(self, **kwargs) -> str:
        """Render the template with provided variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing variable {e} in template {self.name}")
            raise ValueError(f"Missing required variable: {e}")
    
    def validate_variables(self, **kwargs) -> bool:
        """Check if all required variables are provided."""
        missing_vars = [var for var in self.variables if var not in kwargs]
        if missing_vars:
            logger.warning(f"Missing variables for template {self.name}: {missing_vars}")
            return False
        return True


class PromptManager:
    """Manages dynamic prompt generation and template management."""
    
    def __init__(self, settings=None, schema_manager: Optional[SchemaManager] = None):
        self.settings = settings or get_settings()
        self.schema_manager = schema_manager
        self.templates: Dict[str, PromptTemplate] = {}
        self._initialize_default_templates()
        
    def _initialize_default_templates(self):
        """Initialize default prompt templates."""
        
        # System prompt
        self.templates["system"] = PromptTemplate(
            name="system",
            prompt_type=PromptType.SYSTEM,
            template="""You are AskDB, an intelligent database assistant that helps users interact with relational databases using natural language.

Your capabilities:
- Convert natural language questions to SQL queries
- Execute queries and explain results
- Debug and fix SQL errors
- Explore database schemas
- Provide insights from data

Guidelines:
- Always consider the database schema when generating SQL
- Use appropriate joins and aggregations
- Handle NULL values properly
- Optimize queries for performance
- Explain your reasoning clearly
- Ask for clarification when queries are ambiguous

Database Context:
{database_context}

Safety Rules:
- Never generate queries that could modify data without explicit confirmation
- Protect sensitive information and PII
- Validate all queries before execution
- Follow the principle of least privilege""",
            variables=["database_context"],
            description="Main system prompt establishing agent capabilities and guidelines"
        )
        
        # Schema-aware SQL generation (detailed version)
        self.templates["schema_aware_sql"] = PromptTemplate(
            name="schema_aware_sql",
            prompt_type=PromptType.SQL_GENERATION,
            template="""Generate a SQL query to answer this question: "{user_query}"

Relevant Database Schema:
{schema_info}

Relevant Tables:
{relevant_tables}

Relevant Columns:
{relevant_columns}

Previous Context:
{previous_context}

Requirements:
1. Use only the tables and columns mentioned in the schema
2. Generate valid SQL for {database_type}
3. Handle edge cases and NULL values appropriately
4. Use appropriate joins and aggregations
5. Consider performance optimization

Provide your response in the following format:
SQL Query:
```sql
[your SQL query here]
```

Explanation:
[brief explanation of the query]""",
            variables=["user_query", "schema_info", "relevant_tables", "relevant_columns", 
                     "previous_context", "database_type"],
            description="Schema-aware SQL generation template"
        )
        
        # Simple SQL generation (alias for compatibility)
        self.templates["sql_generation"] = PromptTemplate(
            name="sql_generation",
            prompt_type=PromptType.SQL_GENERATION,
            template="""You are a SQL expert. Generate a SQL query to answer the following question:

Question: {user_query}

Database Context:
{database_context}

Available Tables and Columns:
{schema_info}

Relevant Tables: {relevant_tables}

Instructions:
1. Write ONLY valid SQL syntax
2. Use appropriate table and column names from the schema
3. Include proper WHERE clauses if needed
4. Use LIMIT clause for "show first N" or "top N" requests
5. Return the SQL query without explanation

Generate the SQL query now:""",
            variables=["user_query", "database_context", "schema_info", "relevant_tables"],
            description="Simple SQL generation template"
        )
        
        # Query debugging
        self.templates["debug_query"] = PromptTemplate(
            name="debug_query",
            prompt_type=PromptType.DEBUGGING,
            template="""The following SQL query failed to execute:

Query:
```sql
{failed_query}
```

Error:
{error_message}

Database Schema:
{schema_info}

Please analyze the error and provide a corrected query:

1. Identify the root cause of the error
2. Explain what went wrong
3. Provide the corrected query
4. Explain the fix

Corrected Query:
```sql
{corrected_query}
```

Explanation:
{explanation}""",
            variables=["failed_query", "error_message", "schema_info", "corrected_query", "explanation"],
            description="SQL query debugging template"
        )
        
        # Clarification prompt
        self.templates["clarification"] = PromptTemplate(
            name="clarification",
            prompt_type=PromptType.CLARIFICATION,
            template="""I need clarification to better understand your request: "{user_query}"

Available Tables and Columns:
{available_schema}

Previous Context:
{previous_context}

Please specify:
1. Which specific tables or columns you're interested in
2. Any specific conditions or filters
3. The desired output format
4. Any time periods or date ranges

For example, instead of "show me sales data", you could say:
- "Show me total sales by month for the year 2023"
- "List the top 10 customers by total purchase amount"
- "Show products with inventory less than 50 units"

What would you like to know specifically?""",
            variables=["user_query", "available_schema", "previous_context"],
            description="Clarification request template"
        )
        
        # Result formatting
        self.templates["format_results"] = PromptTemplate(
            name="format_results",
            prompt_type=PromptType.RESULT_FORMATTING,
            template="""Query Results:
{query_results}

Original Question: "{user_query}"

Please provide a clear, human-readable summary of these results. Include:
1. Direct answer to the question
2. Key insights or patterns
3. Any notable exceptions or edge cases
4. Recommendations for further analysis

Summary:
{summary}""",
            variables=["query_results", "user_query", "summary"],
            description="Result formatting and summarization template"
        )
        
        # Web search integration
        self.templates["web_search_context"] = PromptTemplate(
            name="web_search_context",
            prompt_type=PromptType.WEB_SEARCH,
            template="""External Context from Web Search:
{web_search_results}

User Query: "{user_query}"

Database Schema:
{schema_info}

Use this external context to enhance your understanding and provide a more comprehensive answer. Consider:
1. How the external information relates to the database query
2. Additional insights that complement the data
3. Context that helps interpret the results

Enhanced Analysis:
{enhanced_analysis}""",
            variables=["web_search_results", "user_query", "schema_info", "enhanced_analysis"],
            description="Web search context integration template"
        )
        
        # Conversation context
        self.templates["conversation_context"] = PromptTemplate(
            name="conversation_context",
            prompt_type=PromptType.CONVERSATION,
            template="""Conversation History:
{conversation_history}

Current Query: "{user_query}"

Database Context:
{database_context}

Consider the conversation flow and previous exchanges when formulating your response. Maintain context and build upon previous discussions.

Contextual Response:
{contextual_response}""",
            variables=["conversation_history", "user_query", "database_context", "contextual_response"],
            description="Conversation-aware response template"
        )
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name."""
        return self.templates.get(name)
    
    def add_template(self, template: PromptTemplate):
        """Add a new prompt template."""
        self.templates[template.name] = template
        logger.info(f"Added prompt template: {template.name}")
    
    def generate_prompt(self, template_name: str, context: PromptContext, **kwargs) -> str:
        """Generate a prompt using a template and context."""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # Prepare template variables from context
        template_vars = self._prepare_template_variables(context, **kwargs)
        
        # Validate required variables
        if not template.validate_variables(**template_vars):
            missing = [var for var in template.variables if var not in template_vars]
            raise ValueError(f"Missing required variables: {missing}")
        
        return template.render(**template_vars)
    
    def _prepare_template_variables(self, context: PromptContext, **kwargs) -> Dict[str, Any]:
        """Prepare template variables from context and additional kwargs."""
        variables = context.to_dict()
        variables.update(kwargs)
        
        # Add derived variables with defaults
        variables["schema_info"] = self._format_schema_info(context.relevant_tables) if context.relevant_tables else "No schema information available"
        variables["relevant_tables"] = self._format_relevant_tables(context.relevant_tables)
        variables["relevant_columns"] = self._format_relevant_columns(context.relevant_columns)
        variables["database_context"] = self._get_database_context()
        variables["previous_context"] = self._format_previous_context(context)
        variables["conversation_history"] = self._format_conversation_history(context.conversation_history)
        
        # Add database type
        variables["database_type"] = self._get_database_type()
        
        # Add empty placeholders for optional variables
        variables.setdefault("sql_query", "")
        variables.setdefault("explanation", "")
        variables.setdefault("corrected_query", "")
        variables.setdefault("summary", "")
        variables.setdefault("enhanced_analysis", "")
        variables.setdefault("contextual_response", "")
        variables.setdefault("available_schema", variables.get("schema_info", ""))
        variables.setdefault("query_results", "")
        variables.setdefault("web_search_results", "")
        
        return variables
    
    def _format_schema_info(self, table_names: List[str]) -> str:
        """Format schema information for relevant tables."""
        if not self.schema_manager:
            return "Schema information not available"
        
        schema_info = []
        for table_name in table_names:
            table_info = self.schema_manager.get_table_info(table_name)
            if table_info:
                schema_info.append(table_info.to_text())
        
        return "\n\n".join(schema_info) if schema_info else "No schema information available"
    
    def _format_relevant_tables(self, table_names: List[str]) -> str:
        """Format relevant tables list."""
        return ", ".join(table_names) if table_names else "None identified"
    
    def _format_relevant_columns(self, column_names: List[str]) -> str:
        """Format relevant columns list."""
        return ", ".join(column_names) if column_names else "None identified"
    
    def _get_database_context(self) -> str:
        """Get general database context information."""
        if not self.schema_manager:
            return "Database connection not established"
        
        try:
            summary = self.schema_manager.get_schema_summary()
            return (f"Database: {summary.get('database_name', 'Unknown')}\n"
                   f"Type: {summary.get('database_type', 'Unknown')}\n"
                   f"Tables: {summary.get('table_count', 0)}")
        except Exception as e:
            logger.error(f"Error getting database context: {e}")
            return "Database context unavailable"
    
    def _get_database_type(self) -> str:
        """Get the database type."""
        if not self.schema_manager:
            return "Unknown"
        
        try:
            summary = self.schema_manager.get_schema_summary()
            return summary.get('database_type', 'MySQL')
        except Exception as e:
            logger.error(f"Error getting database type: {e}")
            return "MySQL"
    
    def _format_previous_context(self, context: PromptContext) -> str:
        """Format previous queries and errors."""
        context_parts = []
        
        if context.previous_queries:
            context_parts.append("Previous Queries:")
            for i, query in enumerate(context.previous_queries[-3:], 1):  # Last 3 queries
                context_parts.append(f"  {i}. {query}")
        
        if context.previous_errors:
            context_parts.append("Previous Errors:")
            for i, error in enumerate(context.previous_errors[-2:], 1):  # Last 2 errors
                context_parts.append(f"  {i}. {error}")
        
        return "\n".join(context_parts) if context_parts else "No previous context"
    
    def _format_conversation_history(self, history: List[Dict[str, str]]) -> str:
        """Format conversation history."""
        if not history:
            return "No conversation history"
        
        formatted = []
        for turn in history[-5:]:  # Last 5 turns
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            formatted.append(f"{role.title()}: {content}")
        
        return "\n".join(formatted)
    
    def create_context_from_query(self, query: str, 
                                 schema_manager: Optional[SchemaManager] = None,
                                 conversation_history: Optional[List[Dict[str, str]]] = None,
                                 **kwargs) -> PromptContext:
        """Create prompt context from a user query."""
        context = PromptContext(
            user_query=query,
            conversation_history=conversation_history or [],
            **kwargs
        )
        
        # Use provided schema manager or default
        sm = schema_manager or self.schema_manager
        if sm:
            try:
                # Find relevant tables and columns using semantic search
                relevant_tables = sm.find_relevant_tables(query, top_k=5)
                relevant_columns = sm.find_relevant_columns(query, top_k=10)
                
                context.relevant_tables = [t.name for t in relevant_tables]
                context.relevant_columns = [c.name for c in relevant_columns]
                
                # Estimate query complexity
                context.query_complexity = self._estimate_query_complexity(
                    query, len(context.relevant_tables), len(context.relevant_columns)
                )
                
            except Exception as e:
                logger.error(f"Error analyzing query for context: {e}")
        
        return context
    
    def _estimate_query_complexity(self, query: str, num_tables: int, num_columns: int) -> str:
        """Estimate query complexity based on various factors."""
        complexity_score = 0
        
        # Base complexity from query length and structure
        query_lower = query.lower()
        
        # Check for complex operations
        complex_keywords = [
            'join', 'group by', 'having', 'subquery', 'window', 'partition',
            'case when', 'union', 'intersect', 'except', 'with', 'recursive'
        ]
        
        for keyword in complex_keywords:
            if keyword in query_lower:
                complexity_score += 2
        
        # Check for aggregations
        agg_keywords = ['sum(', 'avg(', 'count(', 'max(', 'min(', 'stddev(']
        for keyword in agg_keywords:
            if keyword in query_lower:
                complexity_score += 1
        
        # Factor in table and column count
        complexity_score += min(num_tables, 5)  # Cap at 5 points for tables
        complexity_score += min(num_columns / 10, 3)  # Cap at 3 points for columns
        
        # Factor in query length
        complexity_score += min(len(query) / 100, 2)  # Cap at 2 points for length
        
        # Determine complexity level
        if complexity_score <= 3:
            return "simple"
        elif complexity_score <= 7:
            return "medium"
        else:
            return "complex"
    
    def generate_schema_aware_prompt(self, query: str, 
                                   schema_manager: Optional[SchemaManager] = None,
                                   **kwargs) -> str:
        """Generate a schema-aware prompt for SQL generation."""
        context = self.create_context_from_query(query, schema_manager, **kwargs)
        return self.generate_prompt("schema_aware_sql", context, **kwargs)
    
    def generate_debugging_prompt(self, failed_query: str, error_message: str,
                                schema_manager: Optional[SchemaManager] = None,
                                **kwargs) -> str:
        """Generate a debugging prompt for failed SQL queries."""
        context = PromptContext(
            user_query="Debug failed SQL query",
            previous_errors=[error_message]
        )
        
        kwargs.update({
            "failed_query": failed_query,
            "error_message": error_message,
            "schema_info": self._format_schema_info([]) if schema_manager else "Schema not available"
        })
        
        return self.generate_prompt("debug_query", context, **kwargs)
    
    def generate_clarification_prompt(self, query: str,
                                    schema_manager: Optional[SchemaManager] = None,
                                    **kwargs) -> str:
        """Generate a clarification prompt."""
        context = self.create_context_from_query(query, schema_manager, **kwargs)
        return self.generate_prompt("clarification", context, **kwargs)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates."""
        return [
            {
                "name": template.name,
                "type": template.prompt_type.value,
                "description": template.description,
                "variables": template.variables
            }
            for template in self.templates.values()
        ]


# Global prompt manager instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager(schema_manager: Optional[SchemaManager] = None) -> PromptManager:
    """Get the global prompt manager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager(schema_manager)
    return _prompt_manager


def create_prompt_manager(schema_manager: Optional[SchemaManager] = None) -> PromptManager:
    """Create a new prompt manager instance."""
    return PromptManager(schema_manager)