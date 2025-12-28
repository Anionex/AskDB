#!/usr/bin/env python3
"""
测试数据脱敏与行级权限控制功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lib.permissions import PermissionChecker, PermissionDeniedException


def test_permission_checker():
    """测试权限检查器"""
    print("=" * 80)
    print("测试数据脱敏与行级权限控制")
    print("=" * 80)
    
    checker = PermissionChecker()
    
    # 测试用例
    test_cases = [
        {
            "name": "admin用户查询students表",
            "username": "admin",
            "sql": "SELECT * FROM students",
            "expected": "不应该被修改"
        },
        {
            "name": "teach开头用户查询students表",
            "username": "teach001",
            "sql": "SELECT * FROM students",
            "expected": "不应该被修改（可以看到所有students）"
        },
        {
            "name": "stu开头用户查询students表",
            "username": "stu001",
            "sql": "SELECT * FROM students",
            "expected": "应该添加 WHERE sid = 'stu001'"
        },
        {
            "name": "teach开头用户查询teacher表",
            "username": "teach001",
            "sql": "SELECT * FROM teacher",
            "expected": "应该添加 WHERE tid = 'teach001'"
        },
        {
            "name": "stu开头用户查询teacher表",
            "username": "stu001",
            "sql": "SELECT * FROM teacher",
            "expected": "应该被拒绝或返回空结果"
        },
        {
            "name": "teach开头用户查询choices表",
            "username": "teach001",
            "sql": "SELECT * FROM choices",
            "expected": "应该添加 WHERE tid = 'teach001'"
        },
        {
            "name": "stu开头用户查询choices表",
            "username": "stu001",
            "sql": "SELECT * FROM choices",
            "expected": "应该添加 WHERE sid = 'stu001'"
        },
        {
            "name": "复杂查询 - stu用户JOIN查询",
            "username": "stu002",
            "sql": "SELECT s.*, c.* FROM students s JOIN choices c ON s.sid = c.sid",
            "expected": "应该添加权限过滤条件"
        },
        {
            "name": "带WHERE子句的查询",
            "username": "stu003",
            "sql": "SELECT * FROM students WHERE age > 18",
            "expected": "应该在现有WHERE基础上添加 AND sid = 'stu003'"
        },
    ]
    
    print("\n开始测试...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"测试 {i}: {test_case['name']}")
        print(f"{'='*80}")
        print(f"用户名: {test_case['username']}")
        print(f"原始SQL: {test_case['sql']}")
        print(f"预期结果: {test_case['expected']}")
        print()
        
        try:
            transformed_sql, warnings = checker.check_and_transform_query(
                test_case['sql'],
                test_case['username']
            )
            
            print(f"✅ 转换成功")
            print(f"转换后SQL: {transformed_sql}")
            
            if warnings:
                print(f"警告信息: {warnings}")
            
            if transformed_sql != test_case['sql']:
                print(f"🔒 SQL已被修改（权限控制生效）")
            else:
                print(f"ℹ️  SQL未被修改")
                
        except PermissionDeniedException as e:
            print(f"🚫 权限被拒绝: {e}")
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()


def test_column_access():
    """测试列级访问控制"""
    print("\n" + "=" * 80)
    print("测试列级访问控制")
    print("=" * 80)
    
    checker = PermissionChecker()
    
    test_cases = [
        ("admin", "students", "sid", True),
        ("teach001", "students", "name", True),
        ("stu001", "students", "age", True),
        ("stu001", "teacher", "tid", False),  # stu用户不能访问teacher表
    ]
    
    for username, table, column, expected in test_cases:
        result = checker.check_column_access(table, column, username)
        status = "✅" if result == expected else "❌"
        print(f"{status} 用户 {username} 访问 {table}.{column}: {result} (预期: {expected})")


def test_config_reload():
    """测试配置重新加载"""
    print("\n" + "=" * 80)
    print("测试配置重新加载")
    print("=" * 80)
    
    from lib.permissions import reload_permissions
    
    print("重新加载权限配置...")
    reload_permissions()
    print("✅ 配置重新加载成功")


if __name__ == "__main__":
    try:
        test_permission_checker()
        test_column_access()
        test_config_reload()
        
        print("\n" + "=" * 80)
        print("✅ 所有测试完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

