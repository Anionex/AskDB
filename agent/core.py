"""
AskDB Agent Core Module

This module implements the main AskDB agent class with the ReAct-based cognitive framework
for multi-step reasoning, autonomous SQL debugging, and tool orchestration.
"""

import asyncio
import json
import logging
import re
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from ..config import get_settings, Settings
from ..tools import (
    DatabaseTool, SchemaManager, WebSearchTool,
    get_database_tool, get_schema_manager, get_web_search_tool
)
from ..models.llm_interface import LLMInterface, LLMResponse
from ..models.conversation import ConversationManager, ConversationTurn
from .prompting import PromptManager, PromptType
from .safety import SafetyManager, RiskLevel, SafetyCheckResult, SafetyAssessment

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent execution states"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    ERROR = "error"
    COMPLETED = "completed"


class ThoughtType(Enum):
    """Types of thoughts in the ReAct cycle"""
    REASONING = "reasoning"
    PLANNING = "planning"
    REFLECTION = "reflection"
    DEBUGGING = "debugging"
    QUESTION = "question"


@dataclass
class AgentThought:
    """Represents a single thought in the agent's reasoning process"""
    thought_type: ThoughtType
    content: str
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentAction:
    """Represents an action taken by the agent"""
    tool_name: str
    action: str
    parameters: Dict[str, Any]
    reasoning: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentObservation:
    """Represents an observation from tool execution"""
    tool_name: str
    result: Any
    success: bool
    error_message: Optional[str] = None
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentStep:
    """Represents a complete ReAct step"""
    thought: AgentThought
    action: Optional[AgentAction] = None
    observation: Optional[AgentObservation] = None
    step_number: int = 0


class AskDBAgent:
    """
    Main AskDB agent implementing the ReAct-based cognitive framework.
    
    This agent enables natural language interaction with relational databases
    through multi-step reasoning, dynamic schema-aware prompting, and
    multi-layered safety protocols.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_interface: Optional[LLMInterface] = None,
        database_tool: Optional[DatabaseTool] = None,
        schema_manager: Optional[SchemaManager] = None,
        web_search_tool: Optional[WebSearchTool] = None,
        max_steps: int = 10,
        max_retries: int = 3
    ):
        """
        Initialize the AskDB agent.
        
        Args:
            settings: Application settings
            llm_interface: LLM interface for natural language processing
            database_tool: Database interaction tool
            schema_manager: Schema exploration and management
            web_search_tool: Web search for external knowledge
            max_steps: Maximum number of ReAct steps per query
            max_retries: Maximum number of retries for failed actions
        """
        self.settings = settings or get_settings()
        # Import here to avoid circular import
        from ..models.llm_interface import get_llm_interface, create_llm_interface_from_settings
        if llm_interface is None:
            llm_interface = get_llm_interface()
            if llm_interface is None:
                llm_interface = create_llm_interface_from_settings()
        self.llm_interface = llm_interface
        self.database_tool = database_tool or get_database_tool()
        self.schema_manager = schema_manager or (get_schema_manager(self.database_tool) if self.database_tool else None)
        self.web_search_tool = web_search_tool or get_web_search_tool()
        
        self.max_steps = max_steps
        self.max_retries = max_retries
        
        # Initialize managers
        self.prompt_manager = PromptManager(self.settings)
        self.safety_manager = SafetyManager(self.settings)
        self.conversation_manager = ConversationManager(self.settings)
        
        # Agent state
        self.state = AgentState.IDLE
        self.current_step = 0
        self.steps: List[AgentStep] = []
        self.execution_context: Dict[str, Any] = {}
        
        # Tool registry
        self.tools = {
            "database": self.database_tool,
            "schema": self.schema_manager,
            "web_search": self.web_search_tool
        }
        
        logger.info("AskDB agent initialized")
    
    async def process_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query using the ReAct framework.
        
        Args:
            query: Natural language query from user
            context: Additional context for the query
            conversation_id: ID for conversation continuity
            
        Returns:
            Dictionary containing the response and execution details
        """
        logger.info(f"Processing query: {query[:100]}...")
        
        # Initialize execution
        self.state = AgentState.THINKING
        self.current_step = 0
        self.steps = []
        self.execution_context = context or {}
        
        try:
            # Safety check
            safety_result = await self._safety_check_query(query)
            if safety_result.blocked or safety_result.overall_risk == RiskLevel.CRITICAL:
                return {
                    "success": False,
                    "error": "Query blocked due to safety concerns",
                    "safety_result": safety_result.to_dict(),
                    "steps": [step.to_dict() for step in self.steps]
                }
            
            # Add to conversation
            if conversation_id:
                self.conversation_manager.add_user_message(conversation_id, query, context)
            
            # Get conversation context
            conversation_context = self.conversation_manager.get_context(conversation_id) if conversation_id else None
            
            # Execute ReAct cycle
            result = await self._execute_react_cycle(query, conversation_context)
            
            # Add response to conversation
            if conversation_id and result.get("success"):
                self.conversation_manager.add_agent_response(
                    conversation_id, 
                    result.get("response", ""),
                    result.get("sql_query"),
                    result.get("data")
                )
            
            self.state = AgentState.COMPLETED
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            self.state = AgentState.ERROR
            return {
                "success": False,
                "error": str(e),
                "steps": [step.to_dict() for step in self.steps]
            }
    
    async def _execute_react_cycle(
        self,
        query: str,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the ReAct (Reasoning, Acting, Observing) cycle.
        
        Args:
            query: The user's query
            conversation_context: Previous conversation context
            
        Returns:
            Result dictionary with response and execution details
        """
        for step_num in range(self.max_steps):
            self.current_step = step_num + 1
            
            # Phase 1: Reasoning (Thought)
            thought = await self._generate_thought(query, conversation_context)
            self.steps.append(AgentStep(thought=thought, step_number=self.current_step))
            
            # Check if we have a final answer
            if self._is_final_answer(thought):
                return self._extract_final_response(thought)
            
            # Phase 2: Acting (Action)
            action = await self._generate_action(thought)
            if action:
                self.steps[-1].action = action
                
                # Phase 3: Observing (Observation)
                observation = await self._execute_action(action)
                self.steps[-1].observation = observation
                
                # Update context with observation
                self._update_execution_context(observation)
                
                # If database query was successful with data, return the result
                if observation.success and observation.result:
                    result_data = observation.result
                    if isinstance(result_data, dict) and result_data.get("success"):
                        return {
                            "success": True,
                            "data": result_data.get("data", []),
                            "sql_query": action.parameters.get("query", ""),
                            "row_count": result_data.get("row_count", 0),
                            "response": f"Query executed successfully. Found {result_data.get('row_count', 0)} records.",
                            "steps": [step.to_dict() for step in self.steps]
                        }
                
                # Check for errors and potentially retry
                if not observation.success and self.current_step < self.max_steps:
                    await self._handle_error(observation)
        
        # If we reach here, we couldn't complete the query
        return {
            "success": False,
            "error": "Maximum steps reached without resolution",
            "steps": [step.to_dict() for step in self.steps]
        }
    
    async def _safety_check_query(self, query: str) -> SafetyAssessment:
        """
        Perform safety checks on the query.
        
        Args:
            query: The query to check
            
        Returns:
            Safety assessment result
        """
        return self.safety_manager.assess_query_safety(query)
    
    async def _generate_thought(
        self,
        query: str,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> AgentThought:
        """
        Generate a thought based on the current state and query.
        
        Args:
            query: Original user query
            conversation_context: Previous conversation context
            
        Returns:
            Generated thought
        """
        self.state = AgentState.THINKING
        
        # Ensure database is connected
        if self.database_tool and not self.database_tool.is_connected:
            try:
                self.database_tool.connect()
            except Exception as e:
                logger.warning(f"Could not connect to database: {e}")
        
        # Create PromptContext for SQL generation
        from .prompting import PromptContext
        prompt_context = PromptContext(
            user_query=query,
            conversation_history=conversation_context.get("history", []) if conversation_context else [],
            previous_queries=self.execution_context.get("previous_queries", []),
            previous_errors=self.execution_context.get("previous_errors", [])
        )
        
        # Get relevant schema info if available
        if self.schema_manager:
            try:
                relevant_tables = self.schema_manager.find_relevant_tables(query, top_k=5)
                prompt_context.relevant_tables = [t.name for t in relevant_tables]
            except Exception as e:
                logger.warning(f"Error getting schema info: {e}")
        
        # Generate prompt for SQL generation
        prompt = self.prompt_manager.generate_prompt(
            "sql_generation",
            prompt_context
        )
        
        # Get LLM response
        llm_response = await self.llm_interface.generate_async(prompt)
        
        # Parse thought
        thought_content = self._parse_thought_content(llm_response.content)
        thought_type = self._classify_thought_type(thought_content)
        confidence = self._extract_confidence(llm_response.content)
        
        return AgentThought(
            thought_type=thought_type,
            content=thought_content,
            confidence=confidence,
            metadata={"llm_response": llm_response.to_dict()}
        )
    
    async def _generate_action(self, thought: AgentThought) -> Optional[AgentAction]:
        """
        Generate an action based on the current thought.
        
        Args:
            thought: Current thought
            
        Returns:
            Generated action or None if no action needed
        """
        self.state = AgentState.ACTING
        
        # If thought indicates we have a final answer, no action needed
        if thought.thought_type == ThoughtType.REFLECTION and "final answer" in thought.content.lower():
            return None
        
        # Extract SQL query from thought content
        sql_query = self._extract_sql_from_content(thought.content)
        
        if sql_query:
            # Create database query action
            return AgentAction(
                tool_name="database",
                action="execute_query",
                parameters={"query": sql_query},
                reasoning=f"Executing SQL query extracted from thought",
                metadata={"thought": thought.content}
            )
        
        # If no SQL found, parse action from content
        action_data = self._parse_action_content(thought.content)
        if not action_data:
            return None
        
        return AgentAction(
            tool_name=action_data.get("tool", "database"),
            action=action_data.get("action", "execute_query"),
            parameters=action_data.get("parameters", {}),
            reasoning=action_data.get("reasoning", ""),
            metadata={"thought": thought.content}
        )
    
    async def _execute_action(self, action: AgentAction) -> AgentObservation:
        """
        Execute the specified action.
        
        Args:
            action: Action to execute
            
        Returns:
            Observation from action execution
        """
        self.state = AgentState.ACTING
        start_time = time.time()
        
        try:
            # Get the tool
            tool = self.tools.get(action.tool_name)
            if not tool:
                raise ValueError(f"Tool '{action.tool_name}' not available")
            
            # Execute the action
            result = await self._call_tool_method(tool, action.action, action.parameters)
            
            execution_time = time.time() - start_time
            
            return AgentObservation(
                tool_name=action.tool_name,
                result=result,
                success=True,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing action {action.action}: {str(e)}")
            
            return AgentObservation(
                tool_name=action.tool_name,
                result=None,
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _call_tool_method(
        self,
        tool: Any,
        action: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """
        Call a method on a tool with the given parameters.
        
        Args:
            tool: The tool instance
            action: Method name to call
            parameters: Parameters for the method
            
        Returns:
            Result from the method call
        """
        # Map action names to actual method calls
        action_mapping = {
            # Database actions
            "execute_query": "execute_query",
            "validate_query": "validate_query",
            "get_table_info": "get_table_info",
            
            # Schema actions
            "search_tables": "search_tables",
            "search_columns": "search_columns",
            "get_schema_summary": "get_schema_summary",
            
            # Web search actions
            "search": "search"
        }
        
        method_name = action_mapping.get(action, action)
        
        if hasattr(tool, method_name):
            method = getattr(tool, method_name)
            
            # Handle both sync and async methods
            if asyncio.iscoroutinefunction(method):
                return await method(**parameters)
            else:
                return method(**parameters)
        else:
            raise ValueError(f"Method '{method_name}' not found on tool {type(tool).__name__}")
    
    def _update_execution_context(self, observation: AgentObservation):
        """Update execution context with observation results."""
        if observation.success:
            self.execution_context[f"last_{observation.tool_name}_result"] = observation.result
            self.execution_context[f"last_{observation.tool_name}_timestamp"] = observation.timestamp
    
    async def _handle_error(self, observation: AgentObservation):
        """Handle errors from action execution."""
        if observation.tool_name == "database" and "syntax error" in str(observation.error_message).lower():
            # Generate debugging thought
            debug_thought = await self._generate_debugging_thought(observation)
            self.steps.append(AgentStep(
                thought=debug_thought,
                step_number=self.current_step + 1
            ))
    
    async def _generate_debugging_thought(self, observation: AgentObservation) -> AgentThought:
        """Generate a debugging thought when SQL execution fails."""
        context = {
            "error_message": observation.error_message,
            "last_query": self.execution_context.get("last_database_result"),
            "original_query": self.execution_context.get("original_query")
        }
        
        prompt = await self.prompt_manager.generate_prompt(
            PromptType.DEBUGGING,
            context
        )
        
        llm_response = await self.llm_interface.generate_response(prompt)
        
        return AgentThought(
            thought_type=ThoughtType.DEBUGGING,
            content=llm_response.content,
            confidence=0.7,
            metadata={"error_observation": observation.to_dict()}
        )
    
    def _get_relevant_schema_info(self, query: str) -> Optional[Dict[str, Any]]:
        """Get schema information relevant to the query."""
        if not self.schema_manager:
            return None
        
        try:
            # Find relevant tables and columns
            relevant_tables = self.schema_manager.find_relevant_tables(query, top_k=5)
            relevant_columns = self.schema_manager.find_relevant_columns(query, limit=10)
            
            return {
                "relevant_tables": relevant_tables,
                "relevant_columns": relevant_columns
            }
        except Exception as e:
            logger.warning(f"Error getting schema info: {str(e)}")
            return None
    
    def _parse_thought_content(self, llm_response: str) -> str:
        """Parse thought content from LLM response."""
        # Extract content between <thought> tags or use full response
        thought_match = re.search(r'<thought>(.*?)</thought>', llm_response, re.DOTALL)
        if thought_match:
            return thought_match.group(1).strip()
        return llm_response.strip()
    
    def _extract_sql_from_content(self, content: str) -> Optional[str]:
        """Extract SQL query from content."""
        # Try to extract SQL from markdown code blocks
        sql_match = re.search(r'```sql\s+(.*?)\s+```', content, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        
        # Try to extract SQL from generic code blocks
        code_match = re.search(r'```\s+(SELECT.*?)\s+```', content, re.DOTALL | re.IGNORECASE)
        if code_match:
            return code_match.group(1).strip()
        
        # Try to find SQL keywords at the start of lines
        lines = content.split('\n')
        for i, line in enumerate(lines):
            line_stripped = line.strip().upper()
            if line_stripped.startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH')):
                # Take this line and subsequent lines until we hit something that looks like end of SQL
                sql_lines = [lines[i]]
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not lines[j].strip().startswith('#'):
                        sql_lines.append(lines[j])
                    else:
                        break
                return '\n'.join(sql_lines).strip()
        
        return None
    
    def _classify_thought_type(self, content: str) -> ThoughtType:
        """Classify the type of thought based on content."""
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ["final answer", "conclusion", "result"]):
            return ThoughtType.REFLECTION
        elif any(keyword in content_lower for keyword in ["debug", "error", "fix", "correct"]):
            return ThoughtType.DEBUGGING
        elif any(keyword in content_lower for keyword in ["plan", "steps", "approach"]):
            return ThoughtType.PLANNING
        elif any(keyword in content_lower for keyword in ["question", "unclear", "need more"]):
            return ThoughtType.QUESTION
        else:
            return ThoughtType.REASONING
    
    def _extract_confidence(self, llm_response: str) -> float:
        """Extract confidence score from LLM response."""
        confidence_match = re.search(r'confidence[:\s]*(\d+(?:\.\d+)?)', llm_response.lower())
        if confidence_match:
            confidence = float(confidence_match.group(1))
            return min(max(confidence, 0.0), 1.0)
        return 0.5  # Default confidence
    
    def _parse_action_content(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """Parse action content from LLM response."""
        # Try to extract JSON action
        json_match = re.search(r'<action>(.*?)</action>', llm_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # Try to extract structured action
        tool_match = re.search(r'tool[:\s]*(\w+)', llm_response.lower())
        action_match = re.search(r'action[:\s]*(\w+)', llm_response.lower())
        
        if tool_match:
            return {
                "tool": tool_match.group(1),
                "action": action_match.group(1) if action_match else "execute",
                "parameters": {},
                "reasoning": llm_response.strip()
            }
        
        return None
    
    def _is_final_answer(self, thought: AgentThought) -> bool:
        """Check if the thought indicates a final answer."""
        return (
            thought.thought_type == ThoughtType.REFLECTION and
            any(keyword in thought.content.lower() for keyword in ["final answer", "conclusion", "result"])
        )
    
    def _extract_final_response(self, thought: AgentThought) -> Dict[str, Any]:
        """Extract final response from a concluding thought."""
        # Try to extract structured response
        response_match = re.search(r'response[:\s]*(.*?)(?:\n|$)', thought.content, re.IGNORECASE)
        sql_match = re.search(r'sql[:\s]*(.*?)(?:\n|$)', thought.content, re.IGNORECASE)
        
        response = response_match.group(1).strip() if response_match else thought.content.strip()
        sql_query = sql_match.group(1).strip() if sql_match else None
        
        # Get actual data if SQL query was executed
        data = None
        if sql_query and "last_database_result" in self.execution_context:
            data = self.execution_context["last_database_result"]
        
        return {
            "success": True,
            "response": response,
            "sql_query": sql_query,
            "data": data,
            "steps": [step.to_dict() for step in self.steps],
            "execution_time": sum(
                step.observation.execution_time for step in self.steps
                if step.observation
            )
        }
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of the current execution."""
        return {
            "state": self.state.value,
            "current_step": self.current_step,
            "total_steps": len(self.steps),
            "execution_context": self.execution_context,
            "steps": [step.to_dict() for step in self.steps]
        }
    
    def reset(self):
        """Reset the agent state for a new query."""
        self.state = AgentState.IDLE
        self.current_step = 0
        self.steps = []
        self.execution_context = {}
        logger.info("Agent state reset")


# Add to_dict methods to dataclasses for serialization
def agent_step_to_dict(self) -> Dict[str, Any]:
    """Convert AgentStep to dictionary."""
    return {
        "step_number": self.step_number,
        "thought": {
            "type": self.thought.thought_type.value,
            "content": self.thought.content,
            "confidence": self.thought.confidence,
            "metadata": self.thought.metadata,
            "timestamp": self.thought.timestamp
        },
        "action": {
            "tool_name": self.action.tool_name,
            "action": self.action.action,
            "parameters": self.action.parameters,
            "reasoning": self.action.reasoning,
            "timestamp": self.action.timestamp
        } if self.action else None,
        "observation": {
            "tool_name": self.observation.tool_name,
            "result": self.observation.result,
            "success": self.observation.success,
            "error_message": self.observation.error_message,
            "execution_time": self.observation.execution_time,
            "timestamp": self.observation.timestamp
        } if self.observation else None
    }


# Monkey patch the to_dict method
AgentStep.to_dict = agent_step_to_dict

# Add to_dict method for other dataclasses
def agent_observation_to_dict(self) -> Dict[str, Any]:
    """Convert AgentObservation to dictionary."""
    return {
        "tool_name": self.tool_name,
        "result": self.result,
        "success": self.success,
        "error_message": self.error_message,
        "execution_time": self.execution_time,
        "timestamp": self.timestamp
    }


AgentObservation.to_dict = agent_observation_to_dict

# Add to_dict method for AgentAction
def agent_action_to_dict(self) -> Dict[str, Any]:
    """Convert AgentAction to dictionary."""
    return {
        "tool_name": self.tool_name,
        "action": self.action,
        "parameters": self.parameters,
        "reasoning": self.reasoning,
        "timestamp": self.timestamp
    }


AgentAction.to_dict = agent_action_to_dict

# Add to_dict method for AgentThought
def agent_thought_to_dict(self) -> Dict[str, Any]:
    """Convert AgentThought to dictionary."""
    return {
        "thought_type": self.thought_type.value,
        "content": self.content,
        "confidence": self.confidence,
        "metadata": self.metadata,
        "timestamp": self.timestamp
    }


AgentThought.to_dict = agent_thought_to_dict

# Add to_dict method for SafetyCheckResult (if not already defined)
if hasattr(SafetyCheckResult, 'to_dict'):
    pass
else:
    def safety_check_result_to_dict(self) -> Dict[str, Any]:
        """Convert SafetyCheckResult to dictionary."""
        return {
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "blocked": self.blocked
        }
    
    SafetyCheckResult.to_dict = safety_check_result_to_dict