#!/usr/bin/env python3
"""
测试 Agno Agent 返回对象的完整结构
查看 response 对象包含哪些属性和工具调用信息
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 修复导入路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from askdb_agno import create_agent

def inspect_response(response):
    """检查 response 对象的所有属性"""
    print("=" * 60)
    print("Response 对象属性检查")
    print("=" * 60)
    
    print(f"\n类型: {type(response)}")
    print(f"\n所有属性: {dir(response)}")
    
    print("\n" + "-" * 60)
    print("主要属性值:")
    print("-" * 60)
    
    # 检查常见属性
    common_attrs = [
        'content', 'message', 'text', 'response',
        'tool_calls', 'tools', 'tool_uses', 'calls',
        'history', 'messages', 'runs', 'steps',
        'metadata', 'meta', 'info'
    ]
    
    for attr in common_attrs:
        if hasattr(response, attr):
            value = getattr(response, attr)
            print(f"\n{attr}:")
            print(f"  类型: {type(value)}")
            if isinstance(value, (str, int, float, bool, type(None))):
                print(f"  值: {value}")
            elif isinstance(value, (list, dict)):
                print(f"  长度/键数: {len(value)}")
                if isinstance(value, dict) and len(value) < 10:
                    print(f"  内容: {value}")
                elif isinstance(value, list) and len(value) < 10:
                    print(f"  前几项: {value[:3]}")
            else:
                print(f"  值: {str(value)[:200]}")
    
    # 检查 content 属性
    if hasattr(response, 'content'):
        print(f"\ncontent 内容预览:")
        print(f"  {str(response.content)[:500]}...")
    
    # 尝试转换为字典
    print("\n" + "-" * 60)
    print("尝试转换为字典:")
    print("-" * 60)
    try:
        if hasattr(response, '__dict__'):
            print(f"\n__dict__: {response.__dict__}")
        if hasattr(response, 'dict'):
            print(f"\ndict(): {response.dict()}")
        if hasattr(response, 'model_dump'):
            print(f"\nmodel_dump(): {response.model_dump()}")
    except Exception as e:
        print(f"转换失败: {e}")

def main():
    print("创建 Agent...")
    try:
        agent = create_agent(debug=False, enable_memory=False)
        print("✓ Agent 创建成功\n")
        
        # 测试一个简单查询
        test_query = "列出所有表"
        print(f"测试查询: {test_query}")
        print("执行 agent.run()...\n")
        
        response = agent.run(test_query)
        
        # 检查返回对象
        inspect_response(response)
        
        # 检查 agent 对象是否有相关方法
        print("\n" + "=" * 60)
        print("Agent 对象相关方法:")
        print("=" * 60)
        agent_methods = [m for m in dir(agent) if 'tool' in m.lower() or 'run' in m.lower() or 'history' in m.lower()]
        for method in agent_methods:
            print(f"  - {method}")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()







