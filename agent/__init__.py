"""
AskDB Agent Module

This module provides the core agent functionality for natural language database interaction.
It includes the ReAct-based cognitive framework, dynamic prompting, and safety protocols.
"""

from agent.core import (
    AskDBAgent,
    AgentState,
    ThoughtType,
    AgentThought,
    AgentAction,
    AgentObservation,
    AgentStep
)
from agent.prompting import (
    PromptManager,
    PromptTemplate,
    PromptContext,
    PromptType,
    get_prompt_manager,
    create_prompt_manager
)
from agent.safety import (
    SafetyManager,
    PIIDetector,
    SQLInjectionDetector,
    QueryValidator,
    RiskLevel,
    SafetyCheckType,
    SafetyCheckResult,
    SafetyAssessment,
    get_safety_manager,
    assess_query_safety,
    assess_output_safety
)

__version__ = "1.0.0"
__author__ = "AskDB Development Team"
__description__ = "LLM-powered agent for natural language database interaction"

# Module metadata
__all__ = [
    # Core agent classes
    "AskDBAgent",
    "AgentState", 
    "ThoughtType",
    "AgentThought",
    "AgentAction",
    "AgentObservation",
    "AgentStep",
    
    # Prompting system
    "PromptManager",
    "PromptTemplate", 
    "PromptContext",
    "PromptType",
    "get_prompt_manager",
    "create_prompt_manager",
    
    # Safety system
    "SafetyManager",
    "PIIDetector",
    "SQLInjectionDetector", 
    "QueryValidator",
    "RiskLevel",
    "SafetyCheckType",
    "SafetyCheckResult",
    "SafetyAssessment",
    "get_safety_manager",
    "assess_query_safety",
    "assess_output_safety",
    
    # Module info
    "__version__",
    "__author__",
    "__description__"
]

# Agent factory functions for convenient initialization
def create_agent(
    database_tool=None,
    schema_manager=None, 
    web_search_tool=None,
    llm_interface=None,
    settings=None,
    max_steps: int = 10,
    max_retries: int = 3
) -> AskDBAgent:
    """
    Create a fully configured AskDB agent.
    
    Args:
        database_tool: Database tool for SQL execution
        schema_manager: Schema manager for database exploration
        web_search_tool: Web search tool for external knowledge
        llm_interface: LLM interface for text generation
        settings: Application settings
        max_steps: Maximum number of reasoning steps
        max_retries: Maximum number of retry attempts
        
    Returns:
        Configured AskDBAgent instance
    """
    from config import get_settings
    from tools import get_database_tool, get_schema_manager, get_web_search_tool
    from models.llm_interface import get_llm_interface
    
    # Use provided settings or get global settings
    if settings is None:
        settings = get_settings()
    
    # Initialize components if not provided
    if database_tool is None:
        database_tool = get_database_tool()
    
    if schema_manager is None and database_tool:
        schema_manager = get_schema_manager(database_tool)
    
    if web_search_tool is None:
        web_search_tool = get_web_search_tool()
        
    if llm_interface is None:
        from models.llm_interface import get_llm_interface as get_llm, create_llm_interface_from_settings
        llm_interface = get_llm()
        if llm_interface is None:
            llm_interface = create_llm_interface_from_settings()
    
    # Create and return the agent
    return AskDBAgent(
        settings=settings,
        llm_interface=llm_interface,
        database_tool=database_tool,
        schema_manager=schema_manager,
        web_search_tool=web_search_tool,
        max_steps=max_steps,
        max_retries=max_retries
    )

def get_agent(
    database_tool=None,
    schema_manager=None,
    web_search_tool=None, 
    llm_interface=None,
    settings=None
) -> AskDBAgent:
    """
    Get or create a default AskDB agent instance.
    
    This function provides a convenient way to get a pre-configured agent
    with sensible defaults for common use cases.
    
    Args:
        database_tool: Database tool for SQL execution
        schema_manager: Schema manager for database exploration  
        web_search_tool: Web search tool for external knowledge
        llm_interface: LLM interface for text generation
        settings: Application settings
        
    Returns:
        Configured AskDBAgent instance
    """
    return create_agent(
        database_tool=database_tool,
        schema_manager=schema_manager,
        web_search_tool=web_search_tool,
        llm_interface=llm_interface,
        settings=settings
    )

# Module initialization
def _initialize_agent_module():
    """Initialize the agent module with default configurations."""
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"AskDB Agent Module v{__version__} initialized")
    
    # Initialize safety manager
    try:
        get_safety_manager()
        logger.debug("Safety manager initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize safety manager: {e}")
    
    # Initialize prompt manager
    try:
        get_prompt_manager()
        logger.debug("Prompt manager initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize prompt manager: {e}")

# Auto-initialize module
_initialize_agent_module()