#!/usr/bin/env python3
"""
测试工具调用信息提取
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 添加项目路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from askdb_agno import create_agent

def test_tool_calls():
    print("=" * 80)
    print("测试工具调用信息提取")
    print("=" * 80)
    
    # 创建 Agent
    agent = create_agent(debug=False, enable_memory=False, session_id="test_tool_calls")
    
    # 测试查询（会触发工具调用）
    query = "列出数据库中的所有表"
    print(f"\n💬 用户查询: {query}\n")
    
    # 执行查询
    response = agent.run(query)
    
    print("\n" + "=" * 80)
    print("📊 响应分析")
    print("=" * 80)
    
    # 1. 检查响应内容
    print(f"\n✅ 响应内容长度: {len(response.content)} 字符")
    print(f"   前100字符: {response.content[:100]}...")
    
    # 2. 提取工具调用信息（模拟后端逻辑）
    tool_calls = []
    if hasattr(response, 'messages') and response.messages:
        print(f"\n✅ 找到 {len(response.messages)} 条消息")
        for msg_idx, msg in enumerate(response.messages):
            print(f"\n   消息 #{msg_idx}:")
            print(f"     - role: {getattr(msg, 'role', 'N/A')}")
            
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print(f"     - 包含 {len(msg.tool_calls)} 个工具调用")
                for call_idx, call in enumerate(msg.tool_calls):
                    print(f"\n       工具调用对象类型: {type(call)}")
                    print(f"       工具调用对象属性: {[a for a in dir(call) if not a.startswith('_')]}")
                    
                    # 尝试不同的方式提取信息
                    if hasattr(call, 'function'):
                        func = call.function
                        print(f"       ✅ 有 function 属性")
                        print(f"       function 类型: {type(func)}")
                        print(f"       function 属性: {[a for a in dir(func) if not a.startswith('_')]}")
                        
                        args = func.arguments
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except:
                                pass
                        
                        tool_call_info = {
                            'name': func.name,
                            'arguments': args
                        }
                        tool_calls.append(tool_call_info)
                        
                        print(f"\n       工具调用 #{call_idx + 1}:")
                        print(f"         名称: {func.name}")
                        print(f"         参数: {json.dumps(args, ensure_ascii=False, indent=10)[:200]}...")
                    else:
                        # 尝试直接访问属性
                        print(f"       ⚠️  没有 function 属性，尝试其他方式")
                        if hasattr(call, 'name'):
                            print(f"       有 name 属性: {call.name}")
                        if hasattr(call, 'arguments'):
                            print(f"       有 arguments 属性: {call.arguments}")
                        
                        # 尝试转换为字典
                        if hasattr(call, 'to_dict'):
                            call_dict = call.to_dict()
                            print(f"       to_dict(): {json.dumps(call_dict, ensure_ascii=False, indent=10)[:300]}")
                        elif hasattr(call, '__dict__'):
                            print(f"       __dict__: {call.__dict__}")
    else:
        print("\n⚠️  response 没有 messages 属性")
    
    # 3. 输出最终结果
    print("\n" + "=" * 80)
    print("📦 提取的工具调用信息（将发送给前端）")
    print("=" * 80)
    
    if tool_calls:
        print(f"\n✅ 成功提取 {len(tool_calls)} 个工具调用:\n")
        print(json.dumps(tool_calls, ensure_ascii=False, indent=2))
    else:
        print("\n⚠️  未提取到工具调用信息")
        print("   可能原因:")
        print("   1. 该查询不需要调用工具")
        print("   2. 工具调用信息存储在其他位置")
        print("   3. response 结构与预期不同")
    
    # 4. 检查 response 的所有属性
    print("\n" + "=" * 80)
    print("🔍 Response 对象的所有属性")
    print("=" * 80)
    print("\n可用属性:")
    for attr in dir(response):
        if not attr.startswith('_'):
            print(f"  - {attr}")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)

if __name__ == "__main__":
    try:
        test_tool_calls()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

