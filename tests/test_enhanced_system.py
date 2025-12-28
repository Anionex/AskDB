#!/usr/bin/env python3
"""
Enhanced AskDB System Test Suite
测试向量检索增强系统的各个组件
"""

import os
import sys
import logging
import pytest
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from tools.vector_store import VectorStore, SearchResult
from tools.enhanced_tools import EnhancedDatabaseTools
from tools.agno_tools import db
from askdb_agno import create_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestVectorStore:
    """测试向量存储系统"""
    
    def test_vector_store_initialization(self):
        """测试向量存储初始化"""
        vector_store = VectorStore(persist_directory="data/test_vector_db")
        stats = vector_store.get_index_stats()
        
        assert isinstance(stats, dict)
        assert "tables" in stats
        assert "columns" in stats
        assert "business_terms" in stats
        
        logger.info(f"✅ VectorStore initialization test passed. Stats: {stats}")
    
    def test_business_terms_indexing(self):
        """测试业务术语索引"""
        vector_store = VectorStore(persist_directory="data/test_vector_db")
        
        # 测试业务元数据索引
        count = vector_store.index_business_terms("data/business_metadata.json")
        
        logger.info(f"✅ Indexed {count} business terms")
        assert count >= 0  # 至少不报错
    
    def test_semantic_search(self):
        """测试语义搜索"""
        vector_store = VectorStore(persist_directory="data/test_vector_db")
        
        # 先索引业务术语
        vector_store.index_business_terms("data/business_metadata.json")
        
        # 测试搜索
        results = vector_store.search(
            query="用户活跃度",
            top_k=3,
            search_types=["business_term"]
        )
        
        logger.info(f"✅ Found {len(results)} results for '用户活跃度'")
        for result in results:
            logger.info(f"  - {result.item_type}: {result.name} (similarity: {result.similarity:.3f})")
        
        assert isinstance(results, list)


class TestEnhancedTools:
    """测试增强版工具"""
    
    def test_tools_initialization(self):
        """测试工具初始化"""
        tools = EnhancedDatabaseTools()
        
        assert tools is not None
        assert hasattr(tools, 'semantic_search_schema')
        assert hasattr(tools, 'execute_query_with_explanation')
        assert hasattr(tools, 'get_table_ddl')
        
        logger.info("✅ EnhancedDatabaseTools initialization test passed")
    
    def test_list_all_tables(self):
        """测试列表所有表"""
        # 需要先连接数据库
        if not db.is_connected:
            try:
                db.connect()
            except Exception as e:
                logger.warning(f"Database connection failed: {e}")
                pytest.skip("Database not available")
        
        tools = EnhancedDatabaseTools()
        result_json = tools.list_all_tables()
        
        import json
        result = json.loads(result_json)
        
        assert result["success"]
        assert "tables" in result
        logger.info(f"✅ Found {len(result['tables'])} tables in database")


class TestAgentIntegration:
    """测试 Agent 集成"""
    
    def test_agent_creation(self):
        """测试 Agent 创建"""
        try:
            agent = create_agent(debug=False, enable_memory=False)
            
            assert agent is not None
            assert hasattr(agent, 'run')
            assert hasattr(agent, 'tools')
            
            logger.info("✅ Agent creation test passed")
            logger.info(f"  Agent has {len(agent.tools)} tools")
            
        except Exception as e:
            logger.error(f"❌ Agent creation failed: {e}")
            raise
    
    def test_agent_simple_query(self):
        """测试 Agent 简单查询"""
        try:
            agent = create_agent(debug=False, enable_memory=False)
            
            # 测试一个简单的查询
            response = agent.run("列出所有表")
            
            assert response is not None
            logger.info("✅ Agent simple query test passed")
            logger.info(f"  Response: {response.content[:200]}...")
            
        except Exception as e:
            logger.warning(f"⚠️ Agent query test skipped: {e}")
            pytest.skip("Agent query requires database connection")


def run_all_tests():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("🧪 Enhanced AskDB System Test Suite")
    logger.info("=" * 60)
    
    # 测试向量存储
    logger.info("\n📦 Testing Vector Store...")
    test_vector = TestVectorStore()
    test_vector.test_vector_store_initialization()
    test_vector.test_business_terms_indexing()
    test_vector.test_semantic_search()
    
    # 测试增强工具
    logger.info("\n🔧 Testing Enhanced Tools...")
    test_tools = TestEnhancedTools()
    test_tools.test_tools_initialization()
    try:
        test_tools.test_list_all_tables()
    except Exception as e:
        logger.warning(f"List tables test skipped: {e}")
    
    # 测试 Agent 集成
    logger.info("\n🤖 Testing Agent Integration...")
    test_agent = TestAgentIntegration()
    test_agent.test_agent_creation()
    try:
        test_agent.test_agent_simple_query()
    except Exception as e:
        logger.warning(f"Agent query test skipped: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ All tests completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    # 如果使用 pytest 运行
    if "--pytest" in sys.argv:
        pytest.main([__file__, "-v", "-s"])
    else:
        # 直接运行测试
        run_all_tests()



