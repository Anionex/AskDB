#!/usr/bin/env python3
"""
测试带Web搜索工具调用的流式实现
"""

import asyncio
import json
from askdb_agno import create_agent
from agno.agent import RunContentEvent, ToolCallStartedEvent, ToolCallCompletedEvent

async def test_web_search_streaming():
    """测试流式响应（Web搜索工具）"""
    print("=" * 60)
    print("测试 Agno 流式实现 - Web搜索工具调用")
    print("=" * 60)
    
    # 创建 agent（不使用memory以简化测试）
    agent = create_agent(debug=False, enable_memory=False)
    
    # 测试查询 - 明确需要搜索网络
    query = "搜索一下Python编程语言的最新版本"
    print(f"\n[查询] {query}")
    print("-" * 60)
    
    # 使用流式API
    print("\n[开始] 流式处理...")
    stream = agent.run(query, stream=True)
    
    content_chunks = []
    tool_calls = []
    event_count = 0
    
    print("\n[事件流]")
    print("-" * 60)
    
    try:
        for chunk in stream:
            event_count += 1
            
            if isinstance(chunk, RunContentEvent):
                # 内容流
                content = chunk.content
                if content:
                    content_chunks.append(content)
                    # 显示内容但不换行，模拟真实流式效果
                    print(content, end='', flush=True)
            
            elif isinstance(chunk, ToolCallStartedEvent):
                # 工具调用开始
                tool = chunk.tool
                tool_name = getattr(tool, 'tool_name', 'unknown')
                tool_args = getattr(tool, 'tool_args', {})
                
                print(f"\n\n[TOOL_START] {tool_name}")
                print(f"   参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}")
                print()
                
                tool_calls.append({
                    'name': tool_name,
                    'arguments': tool_args,
                    'result': None
                })
            
            elif isinstance(chunk, ToolCallCompletedEvent):
                # 工具调用完成
                tool = chunk.tool
                tool_name = getattr(tool, 'tool_name', 'unknown')
                tool_result = getattr(tool, 'result', '')
                
                # 截断长结果
                result_preview = str(tool_result)[:300]
                if len(str(tool_result)) > 300:
                    result_preview += "\n... (结果过长，已截断)"
                
                print(f"\n[TOOL_DONE] {tool_name}")
                print(f"   结果预览: {result_preview}\n")
                
                # 更新工具调用结果
                for tc in tool_calls:
                    if tc['name'] == tool_name and tc['result'] is None:
                        tc['result'] = tool_result
                        break
    except Exception as e:
        print(f"\n[ERROR] 流式处理出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n\n")
    print("=" * 60)
    print("[完成] 流式处理完成")
    print("=" * 60)
    
    # 输出统计
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
            if tc['result']:
                result_len = len(str(tc['result']))
                print(f"      - 结果长度: {result_len} 字符")
    
    # 验证流式特性
    print(f"\n[验证结果]")
    
    success_checks = []
    
    if len(content_chunks) > 1:
        print("   [OK] 内容是分块流式输出的")
        success_checks.append(True)
    else:
        print("   [WARN] 内容不是流式的（只有1个块）")
        success_checks.append(False)
    
    if tool_calls:
        print("   [OK] 工具调用被正确捕获")
        success_checks.append(True)
        
        has_results = all(tc['result'] is not None for tc in tool_calls)
        if has_results:
            print("   [OK] 所有工具调用都有结果")
            success_checks.append(True)
        else:
            print("   [WARN] 某些工具调用没有结果")
            success_checks.append(False)
    else:
        print("   [INFO] 此查询未触发工具调用")
    
    if all(success_checks) and tool_calls:
        print("\n" + "=" * 60)
        print("[SUCCESS] 流式实现测试通过！")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("[INFO] 测试完成（部分功能未触发）")
        print("=" * 60)
        return False

if __name__ == '__main__':
    success = asyncio.run(test_web_search_streaming())
    exit(0 if success else 1)

