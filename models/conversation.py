"""
Conversation management module for AskDB.

This module provides conversation state management, context retention,
and multi-turn interaction support for the AskDB agent.
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from ..config import get_settings


class MessageRole(Enum):
    """Enumeration for message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageType(Enum):
    """Enumeration for message types."""
    QUERY = "query"
    RESPONSE = "response"
    CLARIFICATION = "clarification"
    ERROR = "error"
    SYSTEM_INFO = "system_info"
    TOOL_RESULT = "tool_result"
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"


@dataclass
class ConversationMessage:
    """Represents a single message in a conversation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole = MessageRole.USER
    message_type: MessageType = MessageType.QUERY
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    tokens_used: Optional[int] = None
    execution_time: Optional[float] = None
    related_query_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'id': self.id,
            'role': self.role.value,
            'message_type': self.message_type.value,
            'content': self.content,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'tokens_used': self.tokens_used,
            'execution_time': self.execution_time,
            'related_query_id': self.related_query_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create message from dictionary."""
        data = data.copy()
        data['role'] = MessageRole(data['role'])
        data['message_type'] = MessageType(data['message_type'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation (user query + agent response)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_query: Optional[ConversationMessage] = None
    agent_response: Optional[ConversationMessage] = None
    thoughts: List[ConversationMessage] = field(default_factory=list)
    actions: List[ConversationMessage] = field(default_factory=list)
    observations: List[ConversationMessage] = field(default_factory=list)
    tool_results: List[ConversationMessage] = field(default_factory=list)
    errors: List[ConversationMessage] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    success: bool = False
    sql_generated: Optional[str] = None
    sql_results: Optional[List[Dict[str, Any]]] = None
    context_used: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """Get duration of the turn in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens used in this turn."""
        total = 0
        for msg in [self.user_query, self.agent_response] + self.thoughts + self.actions + self.observations:
            if msg and msg.tokens_used:
                total += msg.tokens_used
        return total
    
    def add_message(self, message: ConversationMessage) -> None:
        """Add a message to the appropriate list based on its type."""
        if message.role == MessageRole.USER:
            self.user_query = message
        elif message.role == MessageRole.ASSISTANT:
            if message.message_type == MessageType.RESPONSE:
                self.agent_response = message
            elif message.message_type == MessageType.THOUGHT:
                self.thoughts.append(message)
            elif message.message_type == MessageType.ACTION:
                self.actions.append(message)
            elif message.message_type == MessageType.OBSERVATION:
                self.observations.append(message)
            elif message.message_type == MessageType.ERROR:
                self.errors.append(message)
        elif message.role == MessageRole.TOOL:
            self.tool_results.append(message)
    
    def complete(self, success: bool = True) -> None:
        """Mark the turn as completed."""
        self.end_time = datetime.now()
        self.success = success
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert turn to dictionary."""
        return {
            'id': self.id,
            'user_query': self.user_query.to_dict() if self.user_query else None,
            'agent_response': self.agent_response.to_dict() if self.agent_response else None,
            'thoughts': [msg.to_dict() for msg in self.thoughts],
            'actions': [msg.to_dict() for msg in self.actions],
            'observations': [msg.to_dict() for msg in self.observations],
            'tool_results': [msg.to_dict() for msg in self.tool_results],
            'errors': [msg.to_dict() for msg in self.errors],
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'success': self.success,
            'sql_generated': self.sql_generated,
            'sql_results': self.sql_results,
            'context_used': self.context_used,
            'duration': self.duration,
            'total_tokens': self.total_tokens
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTurn':
        """Create turn from dictionary."""
        data = data.copy()
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        if data['end_time']:
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        
        # Convert messages back to objects
        if data['user_query']:
            data['user_query'] = ConversationMessage.from_dict(data['user_query'])
        if data['agent_response']:
            data['agent_response'] = ConversationMessage.from_dict(data['agent_response'])
        
        data['thoughts'] = [ConversationMessage.from_dict(msg) for msg in data['thoughts']]
        data['actions'] = [ConversationMessage.from_dict(msg) for msg in data['actions']]
        data['observations'] = [ConversationMessage.from_dict(msg) for msg in data['observations']]
        data['tool_results'] = [ConversationMessage.from_dict(msg) for msg in data['tool_results']]
        data['errors'] = [ConversationMessage.from_dict(msg) for msg in data['errors']]
        
        return cls(**data)


@dataclass
class ConversationContext:
    """Maintains conversation context and state."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    database_context: Dict[str, Any] = field(default_factory=dict)
    schema_context: Dict[str, Any] = field(default_factory=dict)
    query_history: List[str] = field(default_factory=list)
    sql_history: List[str] = field(default_factory=list)
    error_history: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_timestamp(self) -> None:
        """Update the last updated timestamp."""
        self.last_updated = datetime.now()
    
    def add_query(self, query: str) -> None:
        """Add a query to the history."""
        self.query_history.append(query)
        if len(self.query_history) > 50:  # Keep last 50 queries
            self.query_history.pop(0)
        self.update_timestamp()
    
    def add_sql(self, sql: str) -> None:
        """Add SQL to the history."""
        self.sql_history.append(sql)
        if len(self.sql_history) > 20:  # Keep last 20 SQL queries
            self.sql_history.pop(0)
        self.update_timestamp()
    
    def add_error(self, error: str) -> None:
        """Add an error to the history."""
        self.error_history.append(error)
        if len(self.error_history) > 10:  # Keep last 10 errors
            self.error_history.pop(0)
        self.update_timestamp()
    
    def get_recent_queries(self, count: int = 5) -> List[str]:
        """Get recent queries."""
        return self.query_history[-count:]
    
    def get_recent_sql(self, count: int = 3) -> List[str]:
        """Get recent SQL queries."""
        return self.sql_history[-count:]
    
    def get_recent_errors(self, count: int = 3) -> List[str]:
        """Get recent errors."""
        return self.error_history[-count:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'database_context': self.database_context,
            'schema_context': self.schema_context,
            'query_history': self.query_history,
            'sql_history': self.sql_history,
            'error_history': self.error_history,
            'preferences': self.preferences,
            'variables': self.variables,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Create context from dictionary."""
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)


class ConversationManager:
    """Manages conversation state and context."""
    
    def __init__(self, max_turns: int = 100, max_context_age_hours: int = 24):
        self.max_turns = max_turns
        self.max_context_age_hours = max_context_age_hours
        self.conversations: Dict[str, List[ConversationTurn]] = {}
        self.contexts: Dict[str, ConversationContext] = {}
        self.settings = get_settings()
    
    def create_conversation(self, user_id: Optional[str] = None, 
                          session_id: Optional[str] = None) -> str:
        """Create a new conversation."""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        self.conversations[session_id] = []
        self.contexts[session_id] = ConversationContext(
            session_id=session_id,
            user_id=user_id
        )
        
        return session_id
    
    def get_conversation(self, session_id: str) -> Optional[List[ConversationTurn]]:
        """Get conversation by session ID."""
        return self.conversations.get(session_id)
    
    def get_context(self, session_id: str) -> Optional[ConversationContext]:
        """Get context by session ID."""
        return self.contexts.get(session_id)
    
    def add_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """Add a turn to the conversation."""
        if session_id not in self.conversations:
            self.create_conversation(session_id=session_id)
        
        self.conversations[session_id].append(turn)
        
        # Maintain max turns limit
        if len(self.conversations[session_id]) > self.max_turns:
            self.conversations[session_id].pop(0)
        
        # Update context
        context = self.contexts[session_id]
        if turn.user_query:
            context.add_query(turn.user_query.content)
        if turn.sql_generated:
            context.add_sql(turn.sql_generated)
        if turn.errors:
            for error_msg in turn.errors:
                context.add_error(error_msg.content)
    
    def get_recent_turns(self, session_id: str, count: int = 5) -> List[ConversationTurn]:
        """Get recent turns from conversation."""
        conversation = self.get_conversation(session_id)
        if conversation:
            return conversation[-count:]
        return []
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of conversation."""
        conversation = self.get_conversation(session_id)
        context = self.get_context(session_id)
        
        if not conversation or not context:
            return {}
        
        successful_turns = sum(1 for turn in conversation if turn.success)
        total_turns = len(conversation)
        total_tokens = sum(turn.total_tokens for turn in conversation)
        
        return {
            'session_id': session_id,
            'user_id': context.user_id,
            'total_turns': total_turns,
            'successful_turns': successful_turns,
            'success_rate': successful_turns / total_turns if total_turns > 0 else 0,
            'total_tokens': total_tokens,
            'average_tokens_per_turn': total_tokens / total_turns if total_turns > 0 else 0,
            'queries_asked': len(context.query_history),
            'sql_generated': len(context.sql_history),
            'errors_encountered': len(context.error_history),
            'session_duration': (datetime.now() - context.created_at).total_seconds(),
            'last_activity': context.last_updated.isoformat()
        }
    
    def clear_conversation(self, session_id: str) -> None:
        """Clear conversation history."""
        if session_id in self.conversations:
            self.conversations[session_id] = []
        if session_id in self.contexts:
            self.contexts[session_id] = ConversationContext(
                session_id=session_id,
                user_id=self.contexts[session_id].user_id
            )
    
    def delete_conversation(self, session_id: str) -> None:
        """Delete conversation completely."""
        self.conversations.pop(session_id, None)
        self.contexts.pop(session_id, None)
    
    def cleanup_old_conversations(self) -> int:
        """Clean up old conversations based on age."""
        current_time = datetime.now()
        sessions_to_delete = []
        
        for session_id, context in self.contexts.items():
            age_hours = (current_time - context.last_updated).total_seconds() / 3600
            if age_hours > self.max_context_age_hours:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            self.delete_conversation(session_id)
        
        return len(sessions_to_delete)
    
    def export_conversation(self, session_id: str, format: str = 'json') -> str:
        """Export conversation in specified format."""
        conversation = self.get_conversation(session_id)
        context = self.get_context(session_id)
        
        if not conversation or not context:
            return ""
        
        data = {
            'context': context.to_dict(),
            'turns': [turn.to_dict() for turn in conversation],
            'summary': self.get_conversation_summary(session_id)
        }
        
        if format.lower() == 'json':
            return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def import_conversation(self, data: str, format: str = 'json') -> str:
        """Import conversation from data."""
        if format.lower() == 'json':
            parsed_data = json.loads(data)
            
            context = ConversationContext.from_dict(parsed_data['context'])
            session_id = context.session_id
            
            self.contexts[session_id] = context
            self.conversations[session_id] = [
                ConversationTurn.from_dict(turn_data) 
                for turn_data in parsed_data['turns']
            ]
            
            return session_id
        else:
            raise ValueError(f"Unsupported import format: {format}")
    
    def get_all_sessions(self) -> List[str]:
        """Get all session IDs."""
        return list(self.conversations.keys())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics."""
        total_sessions = len(self.conversations)
        total_turns = sum(len(conv) for conv in self.conversations.values())
        total_tokens = sum(
            sum(turn.total_tokens for turn in conv)
            for conv in self.conversations.values()
        )
        
        return {
            'total_sessions': total_sessions,
            'total_turns': total_turns,
            'total_tokens': total_tokens,
            'average_turns_per_session': total_turns / total_sessions if total_sessions > 0 else 0,
            'average_tokens_per_session': total_tokens / total_sessions if total_sessions > 0 else 0
        }


# Global conversation manager instance
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager(max_turns: int = 100, 
                           max_context_age_hours: int = 24) -> ConversationManager:
    """Get the global conversation manager instance."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager(max_turns, max_context_age_hours)
    return _conversation_manager


def create_conversation_manager(max_turns: int = 100, 
                              max_context_age_hours: int = 24) -> ConversationManager:
    """Create a new conversation manager instance."""
    return ConversationManager(max_turns, max_context_age_hours)