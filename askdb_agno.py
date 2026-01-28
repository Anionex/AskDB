#!/usr/bin/env python3
"""
AskDB with Agno Framework - Core Module
Natural language database interface using Agno framework.
Implements the complete AskDB architecture with ReAct framework, 
safety protocols, and semantic schema search.
"""

import os
import sys
import logging
from pathlib import Path

# 注册opengauss方言
dialects_path = Path(__file__).parent / "dialects"
sys.path.insert(0, str(dialects_path))
from dialects.opengauss_dialect import OpenGaussDialect

# Load environment variables
from dotenv import load_dotenv
load_dotenv(override=True)

from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

# Import our custom tools
from tools.agno_tools import DatabaseTools, db
from tools.enhanced_tools import EnhancedDatabaseTools
from config.prompts import get_agent_instructions
TOOLS_AVAILABLE = True

logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/askdb.log'),
            logging.StreamHandler()
        ]
    )
    # Suppress verbose logs from libraries
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)


def create_agent(debug: bool = False, enable_memory: bool = True, session_id: str = None, user_context: dict = None) -> Agent:
    """Create the AskDB Agno Agent with all tools and instructions.
    
    Args:
        debug: Enable debug mode
        enable_memory: Enable conversation history (requires database storage)
        session_id: Session ID for conversation history (auto-generated if not provided)
        user_context: User context for permission control (optional)
    """
    
    # Get LLM provider configuration
    llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    # Initialize model based on provider
    if llm_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        model_id = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENAI_BASE_URL")
        
        # Create OpenAI model with optional base_url
        model_kwargs = {
            "id": model_id,
            "api_key": api_key
        }
        if base_url:
            model_kwargs["base_url"] = base_url
            logger.info(f"Using OpenAI-compatible API at: {base_url}")
        
        model = OpenAIChat(**model_kwargs)
        logger.info(f"Using OpenAI model: {model_id}")
    else:
        # Default to Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        model_id = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        model = Gemini(id=model_id, api_key=api_key)
        logger.info(f"Using Gemini model: {model_id}")
    
    # Setup session storage for conversation history
    storage_db = None
    if enable_memory:
        # Create SQLite database for session storage
        db_path = os.path.join(os.path.dirname(__file__), "data", "askdb_sessions.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        storage_db = SqliteDb(db_file=db_path)
        logger.info(f"Session storage enabled: {db_path}")
    
    # Connect to database and get table info
    # 注释掉：不在 prompt 中放入表信息，让模型通过工具动态获取
    # try:
    #     db.connect()
    #     tables = db.get_tables()
    #     tables_info = f"\n\nAvailable database tables: {', '.join(tables)}"
    #     
    #     # Get brief schema info
    #     schema_details = []
    #     for table in tables[:5]:  # Show details for first 5 tables
    #         try:
    #             info = db.get_table_info(table)
    #             columns = [col['name'] for col in info['columns'][:5]]
    #             schema_details.append(f"  - {table}: {', '.join(columns)}")
    #         except:
    #             pass
    #     
    #     if schema_details:
    #         tables_info += "\n\nTable schema preview:\n" + "\n".join(schema_details)
    #         
    # except Exception as e:
    #     logger.warning(f"Could not connect to database: {e}")
    #     tables_info = "\n\nDatabase connection not available. Please check your configuration."
    
    # 不在 prompt 中放入表信息，模型需要时会调用 list_tables 工具
    tables_info = ""
    
    # 获取数据库类型，从 prompts 模块获取对应的 instructions
    db_type = os.getenv("DEFAULT_DB_TYPE", "mysql").lower()
    instructions = get_agent_instructions(db_type)

    # 创建工具列表
    tools_list = [
        DuckDuckGoTools(),  # 保留一个搜索工具即可
    ]
    
    # 添加工具
    if TOOLS_AVAILABLE:
        try:
            # 添加增强版数据库工具（集成向量检索和权限控制）
            enhanced_db_tools = EnhancedDatabaseTools(user_context=user_context)
            tools_list.append(enhanced_db_tools)
            
            if user_context:
                logger.info(f"✅ Enhanced database tools loaded with user context: {user_context.get('username')}")
            else:
                logger.info("✅ Enhanced database tools with vector retrieval loaded")
            
        except Exception as e:
            logger.error(f"❌ 添加工具失败: {e}")
    
    # Create agent with tools and conversation history
    agent_params = {
        "name": "AskDB",
        "model": model,
        "tools": tools_list,  
        "instructions": instructions,
        "markdown": True,
        "debug_mode": debug,
    }

    # Add session storage and history features if enabled
    if enable_memory and storage_db:
        agent_params.update({
            "db": storage_db,  # Required for all history features
            "add_history_to_context": True,  # Automatically add recent conversation to context
            "num_history_runs": 5,  # Include last 5 conversation turns
            "read_chat_history": False,  # Give agent tool to search full history
        })
        if session_id:
            agent_params["session_id"] = session_id
    
    agent = Agent(**agent_params)
    
    return agent


if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Initialize logging
    setup_logging()
    
    logger.info("AskDB Core Module - Use via Web API")
    logger.info("Run: python start_backend.py")
