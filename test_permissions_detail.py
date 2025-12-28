#!/usr/bin/env python3
"""
详细测试权限控制 - 查看转换后的SQL
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lib.permissions import PermissionChecker, PermissionDeniedException


def test_sql_transformation():
    """详细测试SQL转换"""
    print("=" * 80)
    print("详细测试SQL转换")
    print("=" * 80)
    
    checker = PermissionChecker()
    
    test_cases = [
        ("stu001", "SELECT * FROM students"),
        ("stu001", "SELECT * FROM students WHERE age > 18"),
        ("stu001", "SELECT sid, name FROM students ORDER BY sid"),
        ("teach001", "SELECT * FROM teacher"),
        ("teach001", "SELECT * FROM choices WHERE course_id = 'CS101'"),
        ("stu002", "SELECT s.*, c.* FROM students s JOIN choices c ON s.sid = c.sid"),
    ]
    
    for username, sql in test_cases:
        print(f"\n{'='*80}")
        print(f"用户: {username}")
        print(f"原始SQL:\n  {sql}")
        
        try:
            transformed_sql, warnings = checker.check_and_transform_query(sql, username)
            print(f"转换后SQL:\n  {transformed_sql}")
            if warnings:
                print(f"警告: {warnings}")
        except PermissionDeniedException as e:
            print(f"🚫 权限被拒绝: {e}")


if __name__ == "__main__":
    test_sql_transformation()

