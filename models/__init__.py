"""
AskDB Models Module

This module provides the core model interfaces for LLM interaction and conversation management.
It includes abstractions for different LLM providers and conversation state management.
"""

from .llm_interface import (
    LLMInterface,
    LLMResponse,
    LLMProvider,
    LLMConfig,
    get_llm_interface,
    create_llm_interface,
    GeminiInterface,
    OpenAIInterface
)

from .conversation import (
    ConversationManager,
    ConversationTurn,
    ConversationContext,
    MessageRole,
    MessageType,
    get_conversation_manager,
    create_conversation_manager
)

__version__ = "1.0.0"
__author__ = "AskDB Development Team"
__description__ = "Core models for LLM interaction and conversation management"

# Export all public classes and functions
__all__ = [
    # LLM Interface
    "LLMInterface",
    "LLMResponse", 
    "LLMProvider",
    "LLMConfig",
    "get_llm_interface",
    "create_llm_interface",
    "GeminiInterface",
    "OpenAIInterface",
    
    # Conversation Management
    "ConversationManager",
    "ConversationTurn",
    "ConversationContext",
    "MessageRole",
    "MessageType",
    "get_conversation_manager",
    "create_conversation_manager"
]