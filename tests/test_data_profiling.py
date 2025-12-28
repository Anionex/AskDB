#!/usr/bin/env python3
"""
测试数据质量评估功能
验证AI能否主动进行数据质量分析
"""

import os
import sys
from pathlib import Path

# 设置路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from askdb_agno import create_agent
from tools.agno_tools import db

def test_data_profiling():
    """测试数据质量评估"""
    print("\n" + "=" * 70)
    print("🧪 测试数据质量评估功能")
    print("=" * 70)
    
    # 连接数据库
    print("\n1️⃣ 连接数据库...")
    try:
        db.connect()
        tables = db.get_tables()
        print(f"   ✅ 数据库已连接，共有 {len(tables)} 个表")
        if tables:
            print(f"   可用表: {', '.join(tables[:5])}{'...' if len(tables) > 5 else ''}")
    except Exception as e:
        print(f"   ❌ 数据库连接失败: {e}")
        return
    
    # 创建 Agent
    print("\n2️⃣ 创建 AI Agent...")
    agent = create_agent(debug=False, enable_memory=False)
    print("   ✅ Agent 创建成功")
    
    # 测试用例
    test_queries = [
        {
            "name": "数据统计查询（应该触发质量评估）",
            "query": "分析一下用户表的数据情况，看看数据质量如何",
            "expected": ["空值", "总数", "统计", "分布", "null", "count"]
        },
        {
            "name": "普通事实查询（可选评估）",
            "query": "有多少个用户？",
            "expected": ["用户", "总数", "count", "SELECT"]
        },
        {
            "name": "复杂分析查询（应该触发质量评估）",
            "query": "计算用户的平均订单金额，并告诉我数据质量如何",
            "expected": ["平均", "质量", "空值", "AVG"]
        }
    ]
    
    print("\n3️⃣ 执行测试查询...")
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n{'─' * 70}")
        print(f"测试 {i}: {test_case['name']}")
        print(f"{'─' * 70}")
        print(f"📝 查询: {test_case['query']}\n")
        
        try:
            # 执行查询
            response = agent.run(test_case['query'])
            answer = response.content
            
            print(f"🤖 AI 回复:")
            print(answer)
            
            # 检查是否包含数据质量相关内容
            quality_keywords = test_case['expected']
            found_keywords = [kw for kw in quality_keywords if kw.lower() in answer.lower()]
            
            if found_keywords:
                print(f"\n✅ 检测到数据质量评估相关内容: {', '.join(found_keywords)}")
            else:
                print(f"\n⚠️  未明显检测到数据质量评估（可能是简单查询）")
            
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)
    
    print("\n💡 观察要点：")
    print("   1. AI 是否在复杂查询前主动执行数据质量分析？")
    print("   2. 是否报告了空值率、数据分布等信息？")
    print("   3. 是否基于数据质量给出了合理建议？")
    print("   4. 对于简单查询，是否避免了不必要的评估？")


if __name__ == "__main__":
    test_data_profiling()

