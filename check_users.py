#!/usr/bin/env python3
import sqlite3
from pathlib import Path

users_db = Path("data/users.db")
if not users_db.exists():
    print("用户数据库不存在")
    exit(1)

conn = sqlite3.connect(users_db)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT username, email, user_type FROM users")
users = cursor.fetchall()

print(f"共有 {len(users)} 个用户:")
for user in users:
    print(f"  - {user['username']} ({user['email']}) - {user['user_type']}")

conn.close()

