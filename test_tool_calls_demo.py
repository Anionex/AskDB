#!/usr/bin/env python3
"""
演示如何从 Agno Agent 获取工具调用信息
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from askdb_agno import create_agent

def main():
    print("=" * 80)
    print("Agno Agent 工具调用信息获取演示")
    print("=" * 80)
    
    # 创建 Agent（启用调试和工具调用显示）
    agent = create_agent(debug=False, enable_memory=True, session_id="tool_demo")
    
    # 测试查询（会触发工具调用）
    query = "列出数据库中的所有表"
    print(f"\n💬 用户查询: {query}\n")
    
    # 执行查询
    response = agent.run(query)
    
    print("\n" + "=" * 80)
    print("📊 获取到的信息")
    print("=" * 80)
    
    # 1. 获取文本响应
    print("\n【1. 文本响应】")
    print(f"content: {response.content[:200]}..." if len(response.content) > 200 else response.content)
    
    # 2. 获取工具调用信息
    print("\n【2. 工具调用信息】")
    tool_calls_found = False
    
    # 方法A: 直接从 response
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print("\n✅ 从 response.tool_calls 获取:")
        for i, call in enumerate(response.tool_calls, 1):
            print(f"\n  工具调用 #{i}:")
            if hasattr(call, 'function'):
                print(f"    工具名称: {call.function.name}")
                print(f"    调用参数: {call.function.arguments}")
            else:
                print(f"    {call}")
        tool_calls_found = True
    
    # 方法B: 从 messages 提取
    if hasattr(response, 'messages') and response.messages:
        for msg_idx, msg in enumerate(response.messages):
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                if not tool_calls_found:
                    print("\n✅ 从 response.messages 获取:")
                for i, call in enumerate(msg.tool_calls, 1):
                    print(f"\n  消息[{msg_idx}] 工具调用 #{i}:")
                    if hasattr(call, 'function'):
                        func = call.function
                        print(f"    🔧 工具名称: {func.name}")
                        
                        # 解析参数（可能是字符串或字典）
                        if isinstance(func.arguments, str):
                            try:
                                args = json.loads(func.arguments)
                            except:
                                args = func.arguments
                        else:
                            args = func.arguments
                        
                        print(f"    📝 调用参数:")
                        if isinstance(args, dict):
                            for key, value in args.items():
                                # 截断长参数
                                value_str = str(value)
                                if len(value_str) > 100:
                                    value_str = value_str[:100] + "..."
                                print(f"        {key}: {value_str}")
                        else:
                            print(f"        {args}")
                    else:
                        print(f"    {call}")
                tool_calls_found = True
    
    if not tool_calls_found:
        print("\n⚠️  在 response 对象中未找到工具调用信息")
        print("   可能原因: 该查询不需要调用工具，或信息存储在数据库中")
    
    # 3. 从数据库查询工具调用历史
    print("\n【3. 从数据库查询工具调用历史】")
    try:
        import sqlite3
        db_path = current_dir / "data" / "askdb_sessions.db"
        
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 查询最新的运行记录
            cursor.execute("""
                SELECT run_id, run_name, tools, created_at
                FROM agent_runs
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 3
            """, ("tool_demo",))
            
            runs = cursor.fetchall()
            if runs:
                print(f"\n✅ 找到 {len(runs)} 条运行记录:")
                for run in runs:
                    run_id, run_name, tools, created_at = run
                    print(f"\n  运行ID: {run_id}")
                    print(f"  名称: {run_name}")
                    print(f"  时间: {created_at}")
                    if tools:
                        try:
                            tools_data = json.loads(tools)
                            print(f"  工具调用:")
                            for tool in tools_data:
                                print(f"    - {tool}")
                        except:
                            print(f"  工具: {tools[:100]}...")
            else:
                print("\n⚠️  数据库中暂无记录")
            
            conn.close()
        else:
            print(f"\n⚠️  数据库文件不存在: {db_path}")
    
    except Exception as e:
        print(f"\n❌ 查询数据库失败: {e}")
    
    # 4. 其他有用的属性
    print("\n【4. 其他信息】")
    if hasattr(response, 'metrics'):
        print(f"  执行指标: {response.metrics}")
    if hasattr(response, 'session_id'):
        print(f"  会话ID: {response.session_id}")
    
    print("\n" + "=" * 80)
    print("✅ 演示完成")
    print("=" * 80)

if __name__ == "__main__":
    main()






