"""
Test suite for AskDB agent core functionality.

This module provides comprehensive tests for the AskDB agent including:
- Agent initialization and configuration
- ReAct framework execution
- Query processing and response generation
- Tool integration and orchestration
- Error handling and recovery
- Conversation management
- Safety protocol integration
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import tempfile
import os

from askdb.agent.core import (
    AskDBAgent, AgentState, ThoughtType, AgentThought, 
    AgentAction, AgentObservation, AgentStep
)
from askdb.agent.safety import SafetyManager, RiskLevel, SafetyAssessment
from askdb.agent.prompting import PromptManager, PromptContext
from askdb.models.conversation import ConversationManager, ConversationTurn
from askdb.models.llm_interface import LLMInterface, LLMResponse, LLMProvider
from askdb.tools.database import DatabaseTool
from askdb.tools.schema import SchemaManager
from askdb.tools.web_search import WebSearchTool
from askdb.config import Settings, get_settings

from . import (
    MockLLMInterface, MockResponse, MockWebSearchTool, 
    create_mock_agent, get_test_config, assert_query_result
)


class TestAskDBAgent:
    """Test cases for AskDB agent core functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        return Settings(
            llm_provider="gemini",
            llm_model="gemini-2.5-flash",
            llm_api_key="test_key",
            database_url="sqlite:///:memory:",
            max_agent_steps=5,
            max_agent_retries=2,
            enable_safety_checks=True,
            enable_web_search=True
        )

    @pytest.fixture
    def mock_llm_interface(self):
        """Create mock LLM interface for testing."""
        mock_llm = MockLLMInterface(None)
        mock_llm.generate_async = AsyncMock(return_value=MockResponse(
            content="SELECT * FROM users WHERE age > 25",
            model="gemini-2.5-flash",
            provider="gemini"
        ))
        return mock_llm

    @pytest.fixture
    def mock_database_tool(self):
        """Create mock database tool for testing."""
        mock_db = Mock(spec=DatabaseTool)
        mock_db.connect = Mock()
        mock_db.execute_query = Mock(return_value=[
            {"id": 1, "name": "John", "age": 30},
            {"id": 2, "name": "Jane", "age": 28}
        ])
        mock_db.test_connection = Mock(return_value=True)
        mock_db.get_table_info = Mock(return_value={
            "users": {
                "columns": ["id", "name", "age", "email"],
                "row_count": 100
            }
        })
        return mock_db

    @pytest.fixture
    def mock_schema_manager(self):
        """Create mock schema manager for testing."""
        mock_schema = Mock(spec=SchemaManager)
        mock_schema.get_schema_summary = Mock(return_value={
            "tables": ["users", "orders", "products"],
            "total_tables": 3
        })
        mock_schema.find_relevant_tables = Mock(return_value=["users"])
        return mock_schema

    @pytest.fixture
    def mock_web_search_tool(self):
        """Create mock web search tool for testing."""
        mock_search = MockWebSearchTool("duckduckgo")
        mock_search.search = AsyncMock(return_value=[
            MockSearchResult(
                title="Test Result",
                url="https://example.com",
                snippet="Test snippet",
                relevance_score=0.9
            )
        ])
        return mock_search

    @pytest.fixture
    def mock_safety_manager(self):
        """Create mock safety manager for testing."""
        mock_safety = Mock(spec=SafetyManager)
        mock_safety.assess_query_safety = Mock(return_value=SafetyAssessment(
            is_safe=True,
            risk_level=RiskLevel.LOW,
            confidence=0.95,
            checks_performed=["sql_injection", "pii_detection"],
            warnings=[],
            blocked_patterns=[],
            recommendations=[]
        ))
        mock_safety.is_safe_to_execute = Mock(return_value=True)
        return mock_safety

    @pytest.fixture
    def mock_prompt_manager(self):
        """Create mock prompt manager for testing."""
        mock_prompt = Mock(spec=PromptManager)
        mock_prompt.generate_schema_aware_prompt = Mock(return_value="Test prompt")
        mock_prompt.generate_prompt = Mock(return_value="Test prompt")
        return mock_prompt

    @pytest.fixture
    def agent(self, mock_settings, mock_llm_interface, mock_database_tool, 
              mock_schema_manager, mock_web_search_tool):
        """Create AskDB agent instance for testing."""
        return AskDBAgent(
            settings=mock_settings,
            llm_interface=mock_llm_interface,
            database_tool=mock_database_tool,
            schema_manager=mock_schema_manager,
            web_search_tool=mock_web_search_tool,
            max_steps=5,
            max_retries=2
        )

    def test_agent_initialization(self, agent):
        """Test agent initialization with all components."""
        assert agent.settings is not None
        assert agent.llm_interface is not None
        assert agent.database_tool is not None
        assert agent.schema_manager is not None
        assert agent.web_search_tool is not None
        assert agent.max_steps == 5
        assert agent.max_retries == 2
        assert agent.state == AgentState.IDLE
        assert agent.conversation_manager is not None

    def test_agent_state_transitions(self, agent):
        """Test agent state transitions during processing."""
        # Initial state should be IDLE
        assert agent.state == AgentState.IDLE
        
        # Test state setting
        agent.state = AgentState.THINKING
        assert agent.state == AgentState.THINKING
        
        agent.state = AgentState.ACTING
        assert agent.state == AgentState.ACTING
        
        agent.state = AgentState.OBSERVING
        assert agent.state == AgentState.OBSERVING
        
        agent.state = AgentState.COMPLETED
        assert agent.state == AgentState.COMPLETED

    @pytest.mark.asyncio
    async def test_simple_query_processing(self, agent):
        """Test processing a simple natural language query."""
        query = "Show me all users older than 25"
        
        result = await agent.process_query(query)
        
        assert result is not None
        assert "success" in result
        assert result["success"] is True
        assert "response" in result
        assert "sql_generated" in result
        assert "execution_time" in result
        assert "steps" in result

    @pytest.mark.asyncio
    async def test_query_with_safety_check(self, agent, mock_safety_manager):
        """Test query processing with safety checks enabled."""
        agent.safety_manager = mock_safety_manager
        query = "SELECT * FROM users"
        
        result = await agent.process_query(query)
        
        # Verify safety check was called
        mock_safety_manager.assess_query_safety.assert_called_once()
        mock_safety_manager.is_safe_to_execute.assert_called_once()
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_query_blocked_by_safety(self, agent, mock_safety_manager):
        """Test query processing when safety check blocks the query."""
        # Configure safety manager to block query
        mock_safety_manager.assess_query_safety.return_value = SafetyAssessment(
            is_safe=False,
            risk_level=RiskLevel.HIGH,
            confidence=0.9,
            checks_performed=["sql_injection"],
            warnings=["Potential SQL injection detected"],
            blocked_patterns=["DROP TABLE"],
            recommendations=["Remove dangerous SQL keywords"]
        )
        mock_safety_manager.is_safe_to_execute.return_value = False
        
        agent.safety_manager = mock_safety_manager
        query = "DROP TABLE users"
        
        result = await agent.process_query(query)
        
        assert result["success"] is False
        assert "error" in result
        assert "safety" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_query_with_web_search(self, agent):
        """Test query processing that requires web search."""
        query = "What is the population of New York City?"
        
        result = await agent.process_query(query)
        
        # Verify web search was called
        agent.web_search_tool.search.assert_called()
        
        assert result is not None
        assert "response" in result

    @pytest.mark.asyncio
    async def test_complex_multi_step_query(self, agent):
        """Test processing a complex query requiring multiple steps."""
        # Configure LLM to return different responses for different steps
        responses = [
            "I need to find users who made recent purchases",
            "SELECT u.* FROM users u JOIN orders o ON u.id = o.user_id WHERE o.created_at > '2024-01-01'",
            "The query returned 15 users who made purchases this year"
        ]
        
        agent.llm_interface.generate_async = AsyncMock(side_effect=[
            MockResponse(content=response, model="gemini-2.5-flash", provider="gemini")
            for response in responses
        ])
        
        query = "Show me users who made purchases this year"
        
        result = await agent.process_query(query)
        
        assert result["success"] is True
        assert len(result["steps"]) > 1
        assert result["sql_generated"] is not None

    @pytest.mark.asyncio
    async def test_query_error_handling(self, agent):
        """Test error handling during query processing."""
        # Configure database tool to raise an error
        agent.database_tool.execute_query.side_effect = Exception("Database connection failed")
        
        query = "SELECT * FROM users"
        
        result = await agent.process_query(query)
        
        assert result["success"] is False
        assert "error" in result
        assert "database connection failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_query_retry_mechanism(self, agent):
        """Test retry mechanism for failed queries."""
        # Configure database to fail first time, succeed second time
        agent.database_tool.execute_query.side_effect = [
            Exception("Connection timeout"),
            [{"id": 1, "name": "John"}]
        ]
        
        query = "SELECT * FROM users"
        
        result = await agent.process_query(query)
        
        # Should succeed after retry
        assert result["success"] is True
        assert agent.database_tool.execute_query.call_count == 2

    @pytest.mark.asyncio
    async def test_max_steps_limit(self, agent):
        """Test that agent respects maximum steps limit."""
        # Configure LLM to keep requesting more steps
        agent.llm_interface.generate_async = AsyncMock(return_value=MockResponse(
            content="I need more information to answer this question",
            model="gemini-2.5-flash",
            provider="gemini"
        ))
        
        query = "Very complex query requiring many steps"
        
        result = await agent.process_query(query)
        
        # Should stop after max_steps
        assert len(result["steps"]) <= agent.max_steps
        assert result["success"] is False
        assert "max steps" in result["error"].lower()

    def test_thought_creation(self, agent):
        """Test creation of agent thoughts."""
        thought = AgentThought(
            thought_type=ThoughtType.REASONING,
            content="I need to analyze the user's query",
            confidence=0.8,
            metadata={"step": 1}
        )
        
        assert thought.thought_type == ThoughtType.REASONING
        assert thought.content == "I need to analyze the user's query"
        assert thought.confidence == 0.8
        assert thought.metadata["step"] == 1
        assert thought.timestamp is not None

    def test_action_creation(self, agent):
        """Test creation of agent actions."""
        action = AgentAction(
            action_type="database_query",
            description="Execute SQL query",
            parameters={"query": "SELECT * FROM users"},
            tool_used="database_tool"
        )
        
        assert action.action_type == "database_query"
        assert action.description == "Execute SQL query"
        assert action.parameters["query"] == "SELECT * FROM users"
        assert action.tool_used == "database_tool"
        assert action.timestamp is not None

    def test_observation_creation(self, agent):
        """Test creation of agent observations."""
        observation = AgentObservation(
            observation_type="query_result",
            content="Query returned 5 rows",
            data={"rows": [{"id": 1, "name": "John"}]},
            success=True
        )
        
        assert observation.observation_type == "query_result"
        assert observation.content == "Query returned 5 rows"
        assert observation.success is True
        assert observation.data["rows"][0]["name"] == "John"
        assert observation.timestamp is not None

    def test_step_creation_and_serialization(self, agent):
        """Test creation and serialization of agent steps."""
        thought = AgentThought(
            thought_type=ThoughtType.REASONING,
            content="Analyzing query",
            confidence=0.9
        )
        action = AgentAction(
            action_type="database_query",
            description="Execute query",
            parameters={"query": "SELECT * FROM users"}
        )
        observation = AgentObservation(
            observation_type="query_result",
            content="Success",
            success=True
        )
        
        step = AgentStep(
            step_number=1,
            thought=thought,
            action=action,
            observation=observation,
            success=True
        )
        
        # Test serialization
        step_dict = step.to_dict()
        
        assert step_dict["step_number"] == 1
        assert step_dict["success"] is True
        assert "thought" in step_dict
        assert "action" in step_dict
        assert "observation" in step_dict

    def test_execution_summary(self, agent):
        """Test generation of execution summary."""
        # Add some steps to the agent
        thought = AgentThought(
            thought_type=ThoughtType.REASONING,
            content="Test thought",
            confidence=0.8
        )
        action = AgentAction(
            action_type="database_query",
            description="Test action",
            parameters={}
        )
        observation = AgentObservation(
            observation_type="query_result",
            content="Test observation",
            success=True
        )
        
        step = AgentStep(
            step_number=1,
            thought=thought,
            action=action,
            observation=observation,
            success=True
        )
        
        agent.execution_steps.append(step)
        agent.start_time = 1.0
        agent.end_time = 2.5
        
        summary = agent.get_execution_summary()
        
        assert summary["total_steps"] == 1
        assert summary["successful_steps"] == 1
        assert summary["execution_time"] == 1.5
        assert summary["success_rate"] == 1.0

    def test_agent_reset(self, agent):
        """Test resetting agent state."""
        # Add some execution data
        agent.execution_steps.append(AgentStep(
            step_number=1,
            thought=AgentThought(ThoughtType.REASONING, "test", 0.8),
            action=AgentAction("test", "test", {}),
            observation=AgentObservation("test", "test", True),
            success=True
        ))
        agent.state = AgentState.COMPLETED
        agent.start_time = 1.0
        agent.end_time = 2.0
        
        # Reset agent
        agent.reset()
        
        assert agent.state == AgentState.IDLE
        assert len(agent.execution_steps) == 0
        assert agent.start_time is None
        assert agent.end_time is None

    @pytest.mark.asyncio
    async def test_conversation_context_integration(self, agent):
        """Test integration with conversation context."""
        query1 = "Show me users from California"
        query2 = "How many are there?"  # Follow-up question
        
        # Process first query
        result1 = await agent.process_query(query1)
        assert result1["success"] is True
        
        # Process follow-up query
        result2 = await agent.process_query(query2)
        assert result2["success"] is True
        
        # Verify conversation context was maintained
        conversation = agent.conversation_manager.get_conversation("default")
        assert len(conversation.turns) == 2

    @pytest.mark.asyncio
    async def test_schema_aware_query_processing(self, agent):
        """Test query processing with schema awareness."""
        query = "Find users who placed orders"
        
        result = await agent.process_query(query)
        
        # Verify schema manager was consulted
        agent.schema_manager.find_relevant_tables.assert_called()
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, agent):
        """Test handling of empty or invalid queries."""
        # Test empty query
        result = await agent.process_query("")
        assert result["success"] is False
        assert "empty" in result["error"].lower()
        
        # Test whitespace-only query
        result = await agent.process_query("   ")
        assert result["success"] is False
        assert "empty" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_very_long_query_handling(self, agent):
        """Test handling of very long queries."""
        long_query = "Show me " + "users " * 1000  # Very long query
        
        result = await agent.process_query(long_query)
        
        # Should either succeed or fail gracefully
        assert result is not None
        assert "success" in result

    def test_agent_configuration_validation(self):
        """Test agent configuration validation."""
        # Test with missing required components
        with pytest.raises(ValueError):
            AskDBAgent(
                settings=None,
                llm_interface=None,
                database_tool=None,
                schema_manager=None,
                web_search_tool=None
            )

    @pytest.mark.asyncio
    async def test_concurrent_query_processing(self, agent):
        """Test handling of concurrent queries."""
        queries = [
            "SELECT * FROM users",
            "SELECT * FROM orders",
            "SELECT * FROM products"
        ]
        
        # Process queries concurrently
        tasks = [agent.process_query(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All queries should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert result["success"] is True

    def test_agent_memory_cleanup(self, agent):
        """Test memory cleanup functionality."""
        # Add some data to agent
        agent.execution_steps.extend([
            AgentStep(
                step_number=i,
                thought=AgentThought(ThoughtType.REASONING, f"thought {i}", 0.8),
                action=AgentAction("test", "test", {}),
                observation=AgentObservation("test", "test", True),
                success=True
            ) for i in range(100)
        ])
        
        # Cleanup old steps
        agent._cleanup_old_steps(max_steps=10)
        
        assert len(agent.execution_steps) <= 10


class TestAgentIntegration:
    """Integration tests for AskDB agent with real components."""

    @pytest.mark.asyncio
    async def test_end_to_end_query_processing(self):
        """Test complete end-to-end query processing."""
        # Create agent with mock components
        agent, db_tool = create_mock_agent()
        
        query = "Show me all users older than 25"
        result = await agent.process_query(query)
        
        assert result["success"] is True
        assert "response" in result
        assert "execution_time" in result

    @pytest.mark.asyncio
    async def test_agent_with_database_errors(self):
        """Test agent behavior when database errors occur."""
        agent, db_tool = create_mock_agent()
        
        # Configure database to raise error
        db_tool.execute_query.side_effect = Exception("Table not found")
        
        query = "SELECT * FROM nonexistent_table"
        result = await agent.process_query(query)
        
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_agent_performance_metrics(self):
        """Test agent performance metrics collection."""
        agent, _ = create_mock_agent()
        
        query = "SELECT COUNT(*) FROM users"
        result = await agent.process_query(query)
        
        summary = agent.get_execution_summary()
        
        assert "execution_time" in summary
        assert "total_steps" in summary
        assert "success_rate" in summary
        assert summary["execution_time"] > 0


if __name__ == "__main__":
    # Run tests if this file is executed directly
    pytest.main([__file__, "-v"])