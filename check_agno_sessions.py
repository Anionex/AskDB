#!/usr/bin/env python3
"""检查Agno sessions数据库结构"""

import sqlite3
import json
from pathlib import Path

db_path = Path(__file__).parent / "data" / "askdb_sessions.db"

if not db_path.exists():
    print(f"数据库不存在: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tables: {tables}")

# 检查agno_sessions表结构
cursor.execute("PRAGMA table_info(agno_sessions)")
columns = cursor.fetchall()
print(f"\nagno_sessions columns:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# 检查数据量
cursor.execute("SELECT COUNT(*) FROM agno_sessions")
count = cursor.fetchone()[0]
print(f"\nTotal sessions: {count}")

# 查看示例数据
if count > 0:
    cursor.execute("SELECT session_id, runs, created_at, updated_at FROM agno_sessions ORDER BY updated_at DESC LIMIT 3")
    rows = cursor.fetchall()
    
    print(f"\n最近的 {len(rows)} 个会话:")
    for row in rows:
        session_id, runs_json, created_at, updated_at = row
        print(f"\n  Session ID: {session_id}")
        print(f"  Created: {created_at}")
        print(f"  Updated: {updated_at}")
        
        if runs_json:
            try:
                runs = json.loads(runs_json)
                print(f"  Runs count: {len(runs) if isinstance(runs, list) else 'Not a list'}")
                
                if isinstance(runs, list) and len(runs) > 0:
                    first_run = runs[0]
                    print(f"  First run keys: {list(first_run.keys())[:10]}")
                    
                    # 显示第一条消息
                    if 'messages' in first_run:
                        messages = first_run['messages']
                        if messages and len(messages) > 0:
                            first_msg = messages[0]
                            print(f"  First message role: {first_msg.get('role', 'N/A')}")
                            content = first_msg.get('content', '')
                            if isinstance(content, str):
                                print(f"  First message content: {content[:50]}...")
                            
            except json.JSONDecodeError as e:
                print(f"  Failed to parse runs JSON: {e}")
        else:
            print(f"  No runs data")

conn.close()



