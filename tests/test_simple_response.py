#!/usr/bin/env python3
"""简化测试：查看 agent.run() 返回对象"""

import os
import sys
from pathlib import Path

# 设置环境变量
os.environ.setdefault('GEMINI_API_KEY', 'test_key')
os.environ.setdefault('DEFAULT_DB_TYPE', 'sqlite')
os.environ.setdefault('DEFAULT_DB_NAME', ':memory:')

sys.path.insert(0, str(Path(__file__).parent))

# 模拟测试
print("=" * 80)
print("Agno RunResponse 对象结构分析")
print("=" * 80)

print("\n根据 Agno 官方文档，agent.run() 返回 RunResponse 对象：")
print("\n主要属性：")
print("  1. content        - 最终文本响应")
print("  2. messages       - 消息列表（包含用户消息和 AI 响应）")
print("  3. tool_calls     - 工具调用列表 ⭐")
print("  4. metrics        - 性能指标（token 使用量等）")

print("\ntool_calls 列表中每个元素包含：")
print("  - name       : 工具名称（如 'execute_query'）")
print("  - arguments  : 调用参数（如 {'sql_query': 'SELECT ...'}）")
print("  - result     : 工具返回结果")

print("\n示例代码：")
print("""
response = agent.run("列出所有表")

# 获取文本响应
print(response.content)

# 获取工具调用
for call in response.tool_calls:
    print(f"工具: {call.name}")
    print(f"参数: {call.arguments}")
    print(f"结果: {call.result}")
""")

print("\n" + "=" * 80)
print("检查当前实现")
print("=" * 80)

# 检查后端实现
backend_file = Path(__file__).parent / "backend" / "main.py"
if backend_file.exists():
    content = backend_file.read_text(encoding='utf-8')
    
    if 'tool_calls' in content and 'response.tool_calls' in content:
        print("\n✅ 后端已实现工具调用信息提取")
        print("   位置: backend/main.py - process_chat_message()")
    else:
        print("\n⚠️  后端未提取 tool_calls")

# 检查 agent 配置
agent_file = Path(__file__).parent / "askdb_agno.py"
if agent_file.exists():
    content = agent_file.read_text(encoding='utf-8')
    
    if '"show_tool_calls": True' in content:
        print("✅ Agent 已启用 show_tool_calls")
    elif '"show_tool_calls": False' in content or '# "show_tool_calls"' in content:
        print("⚠️  Agent 未启用 show_tool_calls")

print("\n" + "=" * 80)







