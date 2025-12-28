""" 
 Agent management for Web API 
 """

import threading
from typing import Dict, Optional
from datetime import datetime, timedelta

class AgentManager:
    """Manage agent sessions"""
    
    def __init__(self):
        self.agents: Dict[str, dict] = {}
        self.cleanup_interval = 300  # Cleanup every 5 minutes
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start cleanup thread"""
        def cleanup():
            while True:
                threading.Event().wait(self.cleanup_interval)
                self._cleanup_old_sessions()
        
        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()
    
    def _cleanup_old_sessions(self):
        """Clean up expired sessions"""
        cutoff_time = datetime.now() - timedelta(hours=1)
        expired_sessions = [
            session_id for session_id, session_data in self.agents.items()
            if session_data['last_activity'] < cutoff_time
        ]
        
        for session_id in expired_sessions:
            del self.agents[session_id]
            print(f"Cleaned up expired session: {session_id}")
    
    def get_agent(self, session_id: str, use_memory: bool = True, user_context: Optional[dict] = None):
        """Get or create agent with user context"""
        from askdb_agno import create_agent
        
        if session_id not in self.agents:
            self.agents[session_id] = {
                'agent': create_agent(enable_memory=use_memory, session_id=session_id, user_context=user_context),
                'last_activity': datetime.now(),
                'user_context': user_context
            }
        else:
            self.agents[session_id]['last_activity'] = datetime.now()
            # 更新用户上下文（如果提供）
            if user_context:
                self.agents[session_id]['user_context'] = user_context
        
        return self.agents[session_id]['agent']

# Global agent manager
agent_manager = AgentManager()