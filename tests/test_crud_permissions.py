#!/usr/bin/env python3
"""
测试CRUD操作权限控制
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lib.permissions import PermissionChecker, PermissionDeniedException
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def test_crud_permissions():
    """测试CRUD操作权限"""
    
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]测试 CRUD 操作权限控制[/bold cyan]",
        border_style="cyan"
    ))
    
    checker = PermissionChecker()
    
    # 测试场景
    test_cases = [
        # ========== admin 用户 ==========
        {
            "title": "admin - SELECT students",
            "username": "admin",
            "sql": "SELECT * FROM students",
            "expected": "允许（admin有完全权限）"
        },
        {
            "title": "admin - INSERT students",
            "username": "admin",
            "sql": "INSERT INTO students (sid, name) VALUES ('stu999', 'Test')",
            "expected": "允许"
        },
        {
            "title": "admin - UPDATE students",
            "username": "admin",
            "sql": "UPDATE students SET name = 'Updated' WHERE sid = 'stu001'",
            "expected": "允许"
        },
        {
            "title": "admin - DELETE students",
            "username": "admin",
            "sql": "DELETE FROM students WHERE sid = 'stu999'",
            "expected": "允许"
        },
        
        # ========== teach 用户 ==========
        {
            "title": "teach001 - SELECT students",
            "username": "teach001",
            "sql": "SELECT * FROM students",
            "expected": "允许（teach可以查看所有学生）"
        },
        {
            "title": "teach001 - INSERT students",
            "username": "teach001",
            "sql": "INSERT INTO students (sid, name) VALUES ('stu888', 'New')",
            "expected": "允许（teach可以添加学生）"
        },
        {
            "title": "teach001 - UPDATE students",
            "username": "teach001",
            "sql": "UPDATE students SET name = 'Modified' WHERE sid = 'stu001'",
            "expected": "允许（teach可以修改学生信息）"
        },
        {
            "title": "teach001 - DELETE students",
            "username": "teach001",
            "sql": "DELETE FROM students WHERE sid = 'stu001'",
            "expected": "🚫 拒绝（teach不能删除学生）"
        },
        {
            "title": "teach001 - SELECT teacher (自己)",
            "username": "teach001",
            "sql": "SELECT * FROM teacher",
            "expected": "允许（只能看到自己，SQL会被过滤）"
        },
        {
            "title": "teach001 - UPDATE teacher (自己)",
            "username": "teach001",
            "sql": "UPDATE teacher SET name = 'Updated' WHERE tid = 'teach001'",
            "expected": "允许（只能修改自己，SQL会被过滤）"
        },
        {
            "title": "teach001 - INSERT teacher",
            "username": "teach001",
            "sql": "INSERT INTO teacher (tid, name) VALUES ('teach999', 'New')",
            "expected": "🚫 拒绝（teach不能添加教师）"
        },
        {
            "title": "teach001 - DELETE choices",
            "username": "teach001",
            "sql": "DELETE FROM choices WHERE course_id = 'CS101'",
            "expected": "允许（teach可以删除选课记录，SQL会被过滤）"
        },
        
        # ========== stu 用户 ==========
        {
            "title": "stu001 - SELECT students (自己)",
            "username": "stu001",
            "sql": "SELECT * FROM students",
            "expected": "允许（只能看到自己，SQL会被过滤）"
        },
        {
            "title": "stu001 - UPDATE students (自己)",
            "username": "stu001",
            "sql": "UPDATE students SET name = 'NewName' WHERE sid = 'stu001'",
            "expected": "允许（只能修改自己，SQL会被过滤）"
        },
        {
            "title": "stu001 - INSERT students",
            "username": "stu001",
            "sql": "INSERT INTO students (sid, name) VALUES ('stu999', 'Hacker')",
            "expected": "🚫 拒绝（stu不能添加学生）"
        },
        {
            "title": "stu001 - DELETE students",
            "username": "stu001",
            "sql": "DELETE FROM students WHERE sid = 'stu001'",
            "expected": "🚫 拒绝（stu不能删除学生）"
        },
        {
            "title": "stu001 - SELECT teacher",
            "username": "stu001",
            "sql": "SELECT * FROM teacher",
            "expected": "🚫 拒绝（stu完全不能访问teacher表）"
        },
        {
            "title": "stu001 - INSERT choices (自己)",
            "username": "stu001",
            "sql": "INSERT INTO choices (sid, tid, course_id) VALUES ('stu001', 'teach001', 'CS101')",
            "expected": "允许（stu可以添加自己的选课）"
        },
        {
            "title": "stu001 - DELETE choices (自己)",
            "username": "stu001",
            "sql": "DELETE FROM choices WHERE sid = 'stu001' AND course_id = 'CS101'",
            "expected": "允许（stu可以删除自己的选课，SQL会被过滤）"
        },
        {
            "title": "stu001 - UPDATE choices",
            "username": "stu001",
            "sql": "UPDATE choices SET course_id = 'CS102' WHERE sid = 'stu001'",
            "expected": "🚫 拒绝（stu不能修改选课记录）"
        },
    ]
    
    print("\n开始测试 CRUD 操作权限...\n")
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        console.print(f"\n[bold yellow]{'='*80}[/bold yellow]")
        console.print(f"[bold cyan]测试 {i}: {test_case['title']}[/bold cyan]")
        console.print(f"[bold yellow]{'='*80}[/bold yellow]\n")
        
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("项目", style="cyan", width=15)
        table.add_column("内容", style="white")
        
        table.add_row("用户名", f"[green]{test_case['username']}[/green]")
        table.add_row("SQL", f"[yellow]{test_case['sql']}[/yellow]")
        table.add_row("预期结果", test_case['expected'])
        
        try:
            transformed_sql, warnings = checker.check_and_transform_query(
                test_case['sql'],
                test_case['username']
            )
            
            # 操作被允许
            if "🚫 拒绝" in test_case['expected']:
                # 预期拒绝但实际允许 - 测试失败
                table.add_row("实际结果", "[red]❌ 测试失败：操作被允许（应该拒绝）[/red]")
                failed += 1
            else:
                # 预期允许且实际允许 - 测试通过
                table.add_row("实际结果", "[green]✅ 测试通过：操作被允许[/green]")
                
                if transformed_sql != test_case['sql']:
                    table.add_row("转换后SQL", f"[green]{transformed_sql}[/green]")
                    table.add_row("", "[dim]（SQL已根据权限过滤）[/dim]")
                
                if warnings:
                    table.add_row("警告", f"[yellow]{', '.join(warnings)}[/yellow]")
                
                passed += 1
                
        except PermissionDeniedException as e:
            # 操作被拒绝
            if "🚫 拒绝" in test_case['expected']:
                # 预期拒绝且实际拒绝 - 测试通过
                table.add_row("实际结果", "[green]✅ 测试通过：操作被拒绝[/green]")
                table.add_row("拒绝原因", f"[yellow]{str(e)}[/yellow]")
                passed += 1
            else:
                # 预期允许但实际拒绝 - 测试失败
                table.add_row("实际结果", "[red]❌ 测试失败：操作被拒绝（应该允许）[/red]")
                table.add_row("拒绝原因", f"[red]{str(e)}[/red]")
                failed += 1
        
        console.print(table)
    
    # 总结
    console.print("\n")
    console.print(Panel.fit(
        f"[bold]测试完成！[/bold]\n\n"
        f"[green]✅ 通过: {passed}[/green]\n"
        f"[red]❌ 失败: {failed}[/red]\n"
        f"[cyan]总计: {passed + failed}[/cyan]",
        title="[bold cyan]测试结果[/bold cyan]",
        border_style="green" if failed == 0 else "red"
    ))


def show_crud_permission_summary():
    """显示CRUD权限配置总结"""
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]CRUD 操作权限配置总结[/bold cyan]",
        border_style="cyan"
    ))
    
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("用户类型", style="cyan", width=12)
    table.add_column("表", style="yellow", width=12)
    table.add_column("SELECT", style="white", width=8)
    table.add_column("INSERT", style="white", width=8)
    table.add_column("UPDATE", style="white", width=8)
    table.add_column("DELETE", style="white", width=8)
    table.add_column("说明", style="dim", width=30)
    
    # admin
    table.add_row(
        "admin", "students", "✅", "✅", "✅", "✅", "完全权限"
    )
    table.add_row(
        "", "teacher", "✅", "✅", "✅", "✅", ""
    )
    table.add_row(
        "", "choices", "✅", "✅", "✅", "✅", ""
    )
    
    # teach
    table.add_row(
        "teach*", "students", "✅", "✅", "✅", "❌", "可增改查，不能删"
    )
    table.add_row(
        "", "teacher", "✅", "❌", "✅", "❌", "只能查改自己"
    )
    table.add_row(
        "", "choices", "✅", "✅", "❌", "✅", "可增删查，不能改"
    )
    
    # stu
    table.add_row(
        "stu*", "students", "✅", "❌", "✅", "❌", "只能查改自己"
    )
    table.add_row(
        "", "teacher", "❌", "❌", "❌", "❌", "完全禁止"
    )
    table.add_row(
        "", "choices", "✅", "✅", "❌", "✅", "可增删查，不能改"
    )
    
    console.print(table)
    console.print("\n[dim]注：带 * 的表示该用户的操作会被自动过滤，只能操作与自己相关的数据[/dim]")


if __name__ == "__main__":
    try:
        console.clear()
        
        # 显示权限配置
        show_crud_permission_summary()
        
        console.print("\n[bold cyan]准备开始测试 CRUD 操作权限...[/bold cyan]")
        console.print("[dim]按Enter开始[/dim]")
        input()
        
        # 运行测试
        test_crud_permissions()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]测试已取消[/yellow]")
    except Exception as e:
        console.print(f"\n[red]错误: {e}[/red]")
        import traceback
        traceback.print_exc()

