# Agno Agent 返回内容说明

## 概述

Agno Agent 的 `run()` 方法返回一个响应对象，包含以下信息：

## 1. 当前实现（仅提取 content）

```python
response = agent.run(message)
result = {
    "success": True,
    "response": response.content  # 只提取了文本内容
}
```

## 2. Response 对象可能包含的属性

根据 Agno 框架的设计，`response` 对象通常包含：

### 2.1 基本属性
- **`content`** (str): 最终生成的文本响应内容 ✅ **当前已使用**
- **`message`** (str): 消息内容（可能与 content 相同）
- **`text`** (str): 文本内容（别名）

### 2.2 工具调用信息（需要提取）
- **`tool_calls`** (list): 工具调用列表
- **`calls`** (list): 调用记录
- **`tools_used`** (list): 使用的工具列表
- **`runs`** (list): 运行步骤列表（可能包含工具调用）

### 2.3 元数据
- **`metadata`** (dict): 元数据信息
- **`created_at`** (datetime): 创建时间
- **`session_id`** (str): 会话ID

## 3. 工具调用信息的结构

每个工具调用对象可能包含：
- **`tool`** 或 **`name`**: 工具名称（如 "execute_query", "describe_table"）
- **`arguments`** 或 **`args`**: 传递给工具的参数
- **`result`**: 工具执行的结果
- **`timestamp`**: 调用时间

## 4. 从数据库获取工具调用信息

Agno 使用 SQLite 数据库存储会话历史，可以通过查询 `runs` 表获取工具调用信息：

```python
# 查询 runs 表结构
cursor.execute("PRAGMA table_info(runs)")
columns = cursor.fetchall()
# 可能包含：id, session_id, name, response, tool_calls, created_at 等字段
```

## 5. 改进后的实现

已修改 `backend/main.py` 中的 `process_chat_message()` 函数，尝试提取工具调用信息：

```python
# 提取工具调用信息
tool_calls = []
if hasattr(response, 'tool_calls'):
    tool_calls = response.tool_calls
elif hasattr(response, 'calls'):
    tool_calls = response.calls
elif hasattr(response, 'tools_used'):
    tool_calls = response.tools_used
elif hasattr(response, 'runs') and response.runs:
    for run in response.runs:
        if hasattr(run, 'tool_calls'):
            tool_calls.extend(run.tool_calls)

if tool_calls:
    result["tool_calls"] = [
        {
            "tool": getattr(tc, 'tool', getattr(tc, 'name', str(tc))),
            "arguments": getattr(tc, 'arguments', getattr(tc, 'args', {})),
            "result": getattr(tc, 'result', None)
        } for tc in tool_calls
    ]
```

## 6. 启用工具调用显示

在 `askdb_agno.py` 中，有一行被注释的配置：

```python
# "show_tool_calls": True,  # 在 debug 模式下显示工具调用
```

启用此选项可能会在响应中包含工具调用信息。

## 7. 测试工具调用信息提取

运行测试脚本查看实际的 response 对象结构：

```bash
python test_agent_response.py
```

## 8. 从数据库查询工具调用

如果 response 对象中没有工具调用信息，可以从 Agno 的数据库查询：

```python
import sqlite3
db_path = "data/askdb_sessions.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询最近的工具调用
cursor.execute("""
    SELECT name, response, tool_calls, created_at
    FROM runs
    WHERE session_id = ?
    ORDER BY created_at DESC
    LIMIT 1
""", (session_id,))

run = cursor.fetchone()
if run and run['tool_calls']:
    import json
    tool_calls = json.loads(run['tool_calls'])
    print(f"工具调用: {tool_calls}")
```

## 9. 总结

**当前状态：**
- ✅ 已提取 `response.content`（文本响应）
- ⚠️ 工具调用信息提取已实现，但需要验证实际结构
- 📝 可以通过数据库查询获取历史工具调用

**建议：**
1. 运行 `test_agent_response.py` 查看实际的 response 对象结构
2. 根据实际结构调整工具调用信息提取逻辑
3. 如果需要完整的工具调用历史，查询 Agno 的数据库







