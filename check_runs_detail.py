#!/usr/bin/env python3
"""详细检查runs字段结构"""

import sqlite3
import json
from pathlib import Path

db_path = Path(__file__).parent / "data" / "askdb_sessions.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT session_id, runs FROM agno_sessions WHERE runs IS NOT NULL LIMIT 1")
row = cursor.fetchone()

if row:
    session_id, runs_json = row
    print(f"Session ID: {session_id}")
    print(f"\nRuns JSON type: {type(runs_json)}")
    print(f"Runs JSON length: {len(runs_json) if runs_json else 0}")
    
    if runs_json:
        print(f"\nFirst 500 chars of runs JSON:")
        print(runs_json[:500])
        
        try:
            runs_data = json.loads(runs_json)
            print(f"\nParsed runs type: {type(runs_data)}")
            
            if isinstance(runs_data, dict):
                print(f"Runs dict keys: {list(runs_data.keys())}")
                
                # 如果是字典，可能是 {run_id: run_data} 的格式
                for run_id, run_data in list(runs_data.items())[:2]:
                    print(f"\n  Run ID: {run_id}")
                    print(f"  Run data type: {type(run_data)}")
                    if isinstance(run_data, dict):
                        print(f"  Run data keys: {list(run_data.keys())[:15]}")
                        
                        # 检查messages
                        if 'messages' in run_data:
                            messages = run_data['messages']
                            print(f"  Messages count: {len(messages) if isinstance(messages, list) else 'Not a list'}")
                            if isinstance(messages, list) and len(messages) > 0:
                                print(f"  First message: {messages[0]}")
                        
                        # 检查其他可能的字段
                        for key in ['name', 'response', 'created_at', 'user_message', 'assistant_message']:
                            if key in run_data:
                                value = run_data[key]
                                if isinstance(value, str) and len(value) > 100:
                                    print(f"  {key}: {value[:100]}...")
                                else:
                                    print(f"  {key}: {value}")
                        
        except json.JSONDecodeError as e:
            print(f"\nFailed to parse JSON: {e}")
else:
    print("No sessions with runs data found")

conn.close()



