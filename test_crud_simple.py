#!/usr/bin/env python3
"""
简化版CRUD操作权限测试（无emoji，适合Windows）
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lib.permissions import PermissionChecker, PermissionDeniedException


def test_crud_permissions():
    """测试CRUD操作权限"""
    
    print("\n" + "="*80)
    print("测试 CRUD 操作权限控制")
    print("="*80 + "\n")
    
    checker = PermissionChecker()
    
    # 测试场景
    test_cases = [
        # admin 用户
        ("admin", "SELECT * FROM students", True, "admin查询students"),
        ("admin", "INSERT INTO students (sid, name) VALUES ('stu999', 'Test')", True, "admin插入students"),
        ("admin", "UPDATE students SET name = 'Updated' WHERE sid = 'stu001')", True, "admin更新students"),
        ("admin", "DELETE FROM students WHERE sid = 'stu999'", True, "admin删除students"),
        
        # teach 用户
        ("teach001", "SELECT * FROM students", True, "teach查询students"),
        ("teach001", "INSERT INTO students (sid, name) VALUES ('stu888', 'New')", True, "teach插入students"),
        ("teach001", "UPDATE students SET name = 'Modified' WHERE sid = 'stu001'", True, "teach更新students"),
        ("teach001", "DELETE FROM students WHERE sid = 'stu001'", False, "teach删除students - 应拒绝"),
        ("teach001", "INSERT INTO teacher (tid, name) VALUES ('teach999', 'New')", False, "teach插入teacher - 应拒绝"),
        ("teach001", "DELETE FROM choices WHERE course_id = 'CS101'", True, "teach删除choices"),
        
        # stu 用户
        ("stu001", "SELECT * FROM students", True, "stu查询students"),
        ("stu001", "UPDATE students SET name = 'NewName' WHERE sid = 'stu001'", True, "stu更新students"),
        ("stu001", "INSERT INTO students (sid, name) VALUES ('stu999', 'Hacker')", False, "stu插入students - 应拒绝"),
        ("stu001", "DELETE FROM students WHERE sid = 'stu001'", False, "stu删除students - 应拒绝"),
        ("stu001", "SELECT * FROM teacher", False, "stu查询teacher - 应拒绝"),
        ("stu001", "INSERT INTO choices (sid, tid, course_id) VALUES ('stu001', 'teach001', 'CS101')", True, "stu插入choices"),
        ("stu001", "DELETE FROM choices WHERE sid = 'stu001'", True, "stu删除choices"),
        ("stu001", "UPDATE choices SET course_id = 'CS102' WHERE sid = 'stu001'", False, "stu更新choices - 应拒绝"),
    ]
    
    passed = 0
    failed = 0
    
    for username, sql, should_allow, desc in test_cases:
        print(f"\n{'-'*80}")
        print(f"测试: {desc}")
        print(f"用户: {username}")
        print(f"SQL: {sql}")
        print(f"预期: {'允许' if should_allow else '拒绝'}")
        
        try:
            transformed_sql, warnings = checker.check_and_transform_query(sql, username)
            
            # 操作被允许
            if should_allow:
                print(f"结果: [通过] 操作被允许")
                if transformed_sql != sql:
                    print(f"转换: {transformed_sql}")
                passed += 1
            else:
                print(f"结果: [失败] 操作被允许（应该拒绝）")
                failed += 1
                
        except PermissionDeniedException as e:
            # 操作被拒绝
            if not should_allow:
                print(f"结果: [通过] 操作被拒绝")
                print(f"原因: {e}")
                passed += 1
            else:
                print(f"结果: [失败] 操作被拒绝（应该允许）")
                print(f"原因: {e}")
                failed += 1
    
    # 总结
    print("\n" + "="*80)
    print("测试完成！")
    print("="*80)
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")
    print("="*80 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = test_crud_permissions()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n测试已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

