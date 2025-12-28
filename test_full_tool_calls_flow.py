#!/usr/bin/env python3
"""
完整的工具调用信息流测试
模拟从后端到前端的完整流程
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

# 导入后端处理函数
from backend.main import process_chat_message

def test_full_flow():
    print("=" * 80)
    print("完整工具调用信息流测试")
    print("=" * 80)
    
    # 模拟用户查询
    test_queries = [
        "列出数据库中的所有表",
        "查询students表有多少条记录",
        "告诉我courses表的结构"
    ]
    
    for idx, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"测试 #{idx}: {query}")
        print('=' * 80)
        
        try:
            # 调用后端处理函数
            result = process_chat_message(
                message=query,
                session_id="test_flow_session",
                user_context={'id': 1, 'username': 'test_user'}
            )
            
            # 检查返回结果
            print(f"\n✅ 后端处理成功")
            print(f"   - success: {result.get('success')}")
            print(f"   - response 长度: {len(result.get('response', ''))} 字符")
            print(f"   - tool_calls 数量: {len(result.get('tool_calls', []))}")
            
            # 显示工具调用信息
            tool_calls = result.get('tool_calls', [])
            if tool_calls:
                print(f"\n📦 工具调用详情:")
                for i, call in enumerate(tool_calls, 1):
                    print(f"\n   工具 #{i}:")
                    print(f"     名称: {call.get('name')}")
                    args = call.get('arguments', {})
                    if args:
                        print(f"     参数:")
                        for key, value in args.items():
                            value_str = str(value)
                            if len(value_str) > 100:
                                value_str = value_str[:100] + "..."
                            print(f"       {key}: {value_str}")
                    else:
                        print(f"     参数: (无)")
                
                # 模拟前端接收的JSON
                print(f"\n📡 前端将接收的JSON:")
                print(json.dumps({
                    'success': result.get('success'),
                    'response': result.get('response')[:100] + '...',
                    'tool_calls': tool_calls
                }, ensure_ascii=False, indent=2))
            else:
                print(f"\n⚠️  未检测到工具调用")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 80}")
    print("✅ 所有测试完成")
    print('=' * 80)

if __name__ == "__main__":
    test_full_flow()

