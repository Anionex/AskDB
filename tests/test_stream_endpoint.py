#!/usr/bin/env python3
"""
测试流式接口是否正确返回工具调用
"""

import asyncio
import json

async def test_stream_endpoint():
    """测试流式端点"""
    print("=" * 60)
    print("测试流式端点 - 检查SSE事件")
    print("=" * 60)
    
    # 模拟前端请求
    import aiohttp
    
    url = "http://localhost:8000/api/protected/chat/stream"
    params = {
        "message": "列出所有数据库表",
        "session_id": "test_session_123"
    }
    
    # 需要登录token
    print("\n注意：此测试需要后端正在运行")
    print("如果需要token，请手动从浏览器复制")
    print()
    
    # 读取token（如果有）
    token = input("请输入token（直接回车跳过）: ").strip()
    
    if not token:
        print("\n跳过实际请求测试")
        print("请在浏览器中测试并查看 Network 面板")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream"
    }
    
    print("\n发送请求...")
    print(f"URL: {url}")
    print(f"Params: {params}")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                print(f"状态码: {response.status}")
                print()
                
                if response.status != 200:
                    text = await response.text()
                    print(f"错误响应: {text}")
                    return
                
                print("接收到的 SSE 事件:")
                print("-" * 60)
                
                event_count = 0
                tool_call_start_count = 0
                tool_call_result_count = 0
                content_count = 0
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line.startswith('data: '):
                        event_count += 1
                        data = json.loads(line[6:])
                        
                        event_type = data.get('type')
                        
                        if event_type == 'tool_call_start':
                            tool_call_start_count += 1
                            print(f"[{event_count}] TOOL_START: {data['data']['name']}")
                            print(f"    参数: {json.dumps(data['data']['arguments'], ensure_ascii=False)}")
                            
                        elif event_type == 'tool_call_result':
                            tool_call_result_count += 1
                            result = str(data['data']['result'])[:100]
                            print(f"[{event_count}] TOOL_RESULT: {data['data']['name']}")
                            print(f"    结果: {result}...")
                            
                        elif event_type == 'content':
                            content_count += 1
                            print(f"[{event_count}] CONTENT: {repr(data['content'][:50])}")
                            
                        elif event_type == 'done':
                            print(f"[{event_count}] DONE")
                            
                        elif event_type == 'error':
                            print(f"[{event_count}] ERROR: {data['content']}")
                
                print()
                print("=" * 60)
                print("统计:")
                print(f"  总事件数: {event_count}")
                print(f"  工具调用开始: {tool_call_start_count}")
                print(f"  工具调用结果: {tool_call_result_count}")
                print(f"  内容块: {content_count}")
                print()
                
                if tool_call_start_count > 0:
                    print("✅ 工具调用事件正常")
                else:
                    print("❌ 没有工具调用事件")
                    
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_stream_endpoint())



