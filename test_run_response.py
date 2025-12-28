#!/usr/bin/env python3
"""
测试 Agno Agent 的 RunResponse 对象
查看 agent.run() 返回的完整结构和工具调用信息
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()

# 修复导入路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from askdb_agno import create_agent

def main():
    print("=" * 80)
    print("测试 Agno Agent RunResponse 对象")
    print("=" * 80)
    
    print("\n创建 Agent (启用 show_tool_calls)...")
    try:
        agent = create_agent(debug=False, enable_memory=True, session_id="test_session")
        print("✓ Agent 创建成功\n")
        
        # 测试一个会调用工具的查询
        test_query = "列出所有数据库表"
        print(f"测试查询: {test_query}")
        print("=" * 80)
        print()
        
        # 执行查询
        response = agent.run(test_query)
        
        print("\n" + "=" * 80)
        print("RunResponse 对象分析")
        print("=" * 80)
        
        # 1. 基本信息
        print(f"\n【类型】: {type(response)}")
        print(f"【类名】: {response.__class__.__name__}")
        
        # 2. 所有属性
        print("\n【所有属性】:")
        attrs = [attr for attr in dir(response) if not attr.startswith('_')]
        for i, attr in enumerate(attrs, 1):
            print(f"  {i:2d}. {attr}")
        
        # 3. 关键属性值
        print("\n" + "=" * 80)
        print("【关键属性详情】")
        print("=" * 80)
        
        # content - 最终响应文本
        if hasattr(response, 'content'):
            content = response.content
            print(f"\n📝 content (响应文本):")
            print(f"   类型: {type(content)}")
            print(f"   长度: {len(content) if content else 0}")
            if content:
                print(f"   预览: {content[:200]}...")
        
        # messages - 消息列表
        if hasattr(response, 'messages'):
            messages = response.messages
            print(f"\n💬 messages (消息列表):")
            print(f"   类型: {type(messages)}")
            print(f"   数量: {len(messages) if messages else 0}")
            if messages:
                for i, msg in enumerate(messages, 1):
                    print(f"\n   消息 {i}:")
                    if hasattr(msg, 'role'):
                        print(f"     role: {msg.role}")
                    if hasattr(msg, 'content'):
                        print(f"     content: {str(msg.content)[:100]}...")
                    if hasattr(msg, 'tool_calls'):
                        print(f"     tool_calls: {msg.tool_calls}")
        
        # tools - 工具调用（可能的属性名）
        for attr_name in ['tools', 'tool_calls', 'tools_used', 'tool_results']:
            if hasattr(response, attr_name):
                tools = getattr(response, attr_name)
                print(f"\n🔧 {attr_name} (工具信息):")
                print(f"   类型: {type(tools)}")
                if tools:
                    print(f"   内容: {json.dumps(tools, ensure_ascii=False, indent=2, default=str)}")
        
        # runs - 运行步骤
        if hasattr(response, 'runs'):
            runs = response.runs
            print(f"\n🏃 runs (运行步骤):")
            print(f"   类型: {type(runs)}")
            print(f"   数量: {len(runs) if runs else 0}")
        
        # metrics - 指标信息
        if hasattr(response, 'metrics'):
            metrics = response.metrics
            print(f"\n📊 metrics (指标):")
            print(f"   类型: {type(metrics)}")
            if metrics and hasattr(metrics, '__dict__'):
                print(f"   内容: {json.dumps(metrics.__dict__, ensure_ascii=False, indent=2, default=str)}")
        
        # 4. 尝试访问嵌套的工具调用信息
        print("\n" + "=" * 80)
        print("【工具调用信息提取】")
        print("=" * 80)
        
        tool_calls_found = []
        
        # 方法1: 直接从 response
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_calls_found.append(("response.tool_calls", response.tool_calls))
        
        # 方法2: 从 messages
        if hasattr(response, 'messages') and response.messages:
            for i, msg in enumerate(response.messages):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tool_calls_found.append((f"messages[{i}].tool_calls", msg.tool_calls))
        
        # 方法3: 从 runs
        if hasattr(response, 'runs') and response.runs:
            for i, run in enumerate(response.runs):
                if hasattr(run, 'tool_calls') and run.tool_calls:
                    tool_calls_found.append((f"runs[{i}].tool_calls", run.tool_calls))
        
        if tool_calls_found:
            print("\n✅ 找到工具调用信息:")
            for location, calls in tool_calls_found:
                print(f"\n📍 位置: {location}")
                print(f"   数量: {len(calls) if isinstance(calls, list) else 1}")
                print(f"   内容:")
                for j, call in enumerate(calls if isinstance(calls, list) else [calls], 1):
                    print(f"\n   工具调用 {j}:")
                    if hasattr(call, '__dict__'):
                        for key, value in call.__dict__.items():
                            if key == 'function' and hasattr(value, '__dict__'):
                                print(f"     {key}:")
                                for fkey, fvalue in value.__dict__.items():
                                    print(f"       {fkey}: {fvalue}")
                            else:
                                print(f"     {key}: {value}")
                    else:
                        print(f"     {call}")
        else:
            print("\n⚠️  未找到工具调用信息")
            print("   可能的原因:")
            print("   1. 该查询没有调用工具")
            print("   2. 工具调用信息存储在其他位置")
            print("   3. 需要查看数据库中的历史记录")
        
        # 5. 完整对象转储
        print("\n" + "=" * 80)
        print("【完整对象结构 (__dict__)】")
        print("=" * 80)
        
        if hasattr(response, '__dict__'):
            print(json.dumps(response.__dict__, ensure_ascii=False, indent=2, default=str))
        
        # 6. 从数据库查询工具调用
        print("\n" + "=" * 80)
        print("【从数据库查询工具调用】")
        print("=" * 80)
        
        try:
            import sqlite3
            db_path = Path(__file__).parent / "data" / "askdb_sessions.db"
            if db_path.exists():
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 查看表结构
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                print(f"\n数据库表: {[t[0] for t in tables]}")
                
                # 查询 runs 表
                cursor.execute("SELECT * FROM runs WHERE session_id = ? ORDER BY created_at DESC LIMIT 1", 
                              ("test_session",))
                run = cursor.fetchone()
                
                if run:
                    cursor.execute("PRAGMA table_info(runs)")
                    columns = [col[1] for col in cursor.fetchall()]
                    run_dict = dict(zip(columns, run))
                    
                    print(f"\n最新的 run 记录:")
                    for key, value in run_dict.items():
                        if key in ['name', 'response', 'tools', 'tool_calls']:
                            print(f"  {key}: {str(value)[:200]}...")
                        else:
                            print(f"  {key}: {value}")
                
                conn.close()
            else:
                print(f"\n数据库文件不存在: {db_path}")
        except Exception as e:
            print(f"\n查询数据库失败: {e}")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()







