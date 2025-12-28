#!/usr/bin/env python3
"""
测试真正的流式实现
"""

import asyncio
import json
from askdb_agno import create_agent
from agno.agent import RunContentEvent, ToolCallStartedEvent, ToolCallCompletedEvent

async def test_streaming():
    """测试流式响应"""
    print("=" * 60)
    print("测试 Agno 真正的流式实现")
    print("=" * 60)
    
    # 创建 agent（不使用memory以简化测试）
    agent = create_agent(debug=False, enable_memory=False)
    
    # 测试查询
    query = "列出所有数据库表"
    print(f"\n📝 查询: {query}")
    print("-" * 60)
    
    # 使用流式API
    print("\n⏱️  开始流式处理...")
    stream = agent.run(query, stream=True)
    
    content_chunks = []
    tool_calls = []
    
    print("\n📡 流式事件:")
    print("-" * 60)
    
    for chunk in stream:
        if isinstance(chunk, RunContentEvent):
            # 内容流
            content = chunk.content
            if content:
                content_chunks.append(content)
                print(f"📝 [CONTENT] {content}", end="", flush=True)
        
        elif isinstance(chunk, ToolCallStartedEvent):
            # 工具调用开始
            tool = chunk.tool
            tool_name = getattr(tool, 'tool_name', 'unknown')
            tool_args = getattr(tool, 'tool_args', {})
            
            print(f"\n🔧 [TOOL_START] {tool_name}")
            print(f"   参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}")
            
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
            result_preview = str(tool_result)[:200]
            if len(str(tool_result)) > 200:
                result_preview += "... (截断)"
            
            print(f"\n✅ [TOOL_DONE] {tool_name}")
            print(f"   结果: {result_preview}")
            
            # 更新工具调用结果
            for tc in tool_calls:
                if tc['name'] == tool_name and tc['result'] is None:
                    tc['result'] = tool_result
                    break
    
    print("\n")
    print("=" * 60)
    print("✅ 流式处理完成")
    print("=" * 60)
    
    # 输出统计
    full_content = ''.join(content_chunks)
    print(f"\n📊 统计信息:")
    print(f"   - 内容块数量: {len(content_chunks)}")
    print(f"   - 总内容长度: {len(full_content)} 字符")
    print(f"   - 工具调用次数: {len(tool_calls)}")
    
    if tool_calls:
        print(f"\n🔧 工具调用详情:")
        for i, tc in enumerate(tool_calls, 1):
            print(f"   {i}. {tc['name']}")
            print(f"      - 有参数: {bool(tc['arguments'])}")
            print(f"      - 有结果: {tc['result'] is not None}")
    
    print(f"\n💬 完整回复:")
    print("-" * 60)
    print(full_content)
    print("-" * 60)
    
    # 验证流式特性
    print(f"\n✅ 验证结果:")
    if len(content_chunks) > 1:
        print("   ✅ 内容是分块流式输出的")
    else:
        print("   ⚠️  内容不是流式的（只有1个块）")
    
    if tool_calls:
        print("   ✅ 工具调用被正确捕获")
        
        has_results = all(tc['result'] is not None for tc in tool_calls)
        if has_results:
            print("   ✅ 所有工具调用都有结果")
        else:
            print("   ⚠️  某些工具调用没有结果")
    else:
        print("   ⚠️  没有工具调用")

if __name__ == '__main__':
    asyncio.run(test_streaming())

