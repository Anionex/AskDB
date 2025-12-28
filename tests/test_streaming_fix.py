#!/usr/bin/env python3
"""
测试修复后的流式实现（包含工具调用）
"""

import asyncio
import json
from askdb_agno import create_agent
from agno.agent import RunEvent

async def test_streaming_with_tools_fixed():
    """测试流式响应（修复后）"""
    print("=" * 60)
    print("测试修复后的流式实现 - 工具调用")
    print("=" * 60)
    
    # 创建 agent
    agent = create_agent(debug=False, enable_memory=False)
    
    # 测试查询 - 应该会触发语义检索
    query = "查询一下数据库中有哪些表"
    print(f"\n[查询] {query}")
    print("-" * 60)
    
    # 使用真正的流式API - 关键是 stream_events=True
    print("\n[开始] 流式处理（stream=True, stream_events=True）...")
    stream = agent.run(query, stream=True, stream_events=True)
    
    content_chunks = []
    tool_calls = []
    event_count = 0
    
    print("\n[事件流]")
    print("-" * 60)
    
    try:
        for chunk in stream:
            event_count += 1
            
            # 内容事件
            if chunk.event == RunEvent.run_content:
                content = chunk.content
                if content:
                    content_chunks.append(content)
                    print(content, end='', flush=True)
            
            # 工具调用开始
            elif chunk.event == RunEvent.tool_call_started:
                tool_name = getattr(chunk.tool, 'tool_name', 'unknown')
                tool_args = getattr(chunk.tool, 'tool_args', {})
                
                print(f"\n\n[TOOL_START] {tool_name}")
                print(f"   参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}\n")
                
                tool_calls.append({
                    'name': tool_name,
                    'arguments': tool_args,
                    'result': None
                })
            
            # 工具调用完成
            elif chunk.event == RunEvent.tool_call_completed:
                tool_name = getattr(chunk.tool, 'tool_name', 'unknown')
                tool_result = getattr(chunk.tool, 'result', '')
                
                result_preview = str(tool_result)[:200]
                if len(str(tool_result)) > 200:
                    result_preview += "..."
                
                print(f"\n[TOOL_DONE] {tool_name}")
                print(f"   结果: {result_preview}\n")
                
                # 更新结果
                for tc in tool_calls:
                    if tc['name'] == tool_name and tc['result'] is None:
                        tc['result'] = tool_result
                        break
    
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    print("\n\n")
    print("=" * 60)
    print("[完成]")
    print("=" * 60)
    
    # 统计
    full_content = ''.join(content_chunks)
    print(f"\n[统计]")
    print(f"   - 总事件数: {event_count}")
    print(f"   - 内容块数量: {len(content_chunks)}")
    print(f"   - 总内容长度: {len(full_content)} 字符")
    print(f"   - 工具调用次数: {len(tool_calls)}")
    
    if tool_calls:
        print(f"\n[工具调用详情]")
        for i, tc in enumerate(tool_calls, 1):
            print(f"   {i}. {tc['name']}")
            print(f"      - 参数: {tc['arguments']}")
            print(f"      - 有结果: {tc['result'] is not None}")
    
    # 验证
    print(f"\n[验证]")
    
    if len(content_chunks) > 1:
        print("   [OK] 内容是流式的")
    else:
        print("   [WARN] 内容不是流式的")
    
    if tool_calls:
        print("   [OK] 工具调用被捕获")
        
        has_results = all(tc['result'] is not None for tc in tool_calls)
        if has_results:
            print("   [OK] 所有工具都有结果")
        else:
            print("   [WARN] 某些工具没有结果")
    else:
        print("   [WARN] 没有工具调用")
    
    # 最终判断
    success = len(content_chunks) > 1 and len(tool_calls) > 0
    
    if success:
        print("\n" + "=" * 60)
        print("[SUCCESS] 流式实现修复成功！")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[INFO] 测试完成")
        print("=" * 60)
    
    return success

if __name__ == '__main__':
    success = asyncio.run(test_streaming_with_tools_fixed())
    exit(0 if success else 1)

