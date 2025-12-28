#!/usr/bin/env python3
"""
权限控制功能演示脚本
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


def demo_permission_control():
    """演示权限控制功能"""
    
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]AskDB 数据脱敏与行级权限控制功能演示[/bold cyan]",
        border_style="cyan"
    ))
    
    checker = PermissionChecker()
    
    # 演示场景
    scenarios = [
        {
            "title": "场景1: 管理员查询所有学生",
            "username": "admin",
            "sql": "SELECT * FROM students",
            "description": "admin用户可以看到所有数据，无任何限制"
        },
        {
            "title": "场景2: 学生查询学生表",
            "username": "stu001",
            "sql": "SELECT * FROM students",
            "description": "stu001只能看到自己的记录，系统自动添加 WHERE sid = 'stu001'"
        },
        {
            "title": "场景3: 学生查询选课记录",
            "username": "stu002",
            "sql": "SELECT * FROM choices WHERE course_id = 'CS101'",
            "description": "stu002只能看到自己的选课记录"
        },
        {
            "title": "场景4: 教师查询教师表",
            "username": "teach001",
            "sql": "SELECT * FROM teacher",
            "description": "teach001只能看到自己的教师信息"
        },
        {
            "title": "场景5: 教师查询选课记录",
            "username": "teach002",
            "sql": "SELECT * FROM choices",
            "description": "teach002只能看到选了他课程的学生"
        },
        {
            "title": "场景6: 学生尝试访问教师表",
            "username": "stu003",
            "sql": "SELECT * FROM teacher",
            "description": "stu003没有权限访问teacher表，会被拒绝"
        },
        {
            "title": "场景7: 复杂JOIN查询",
            "username": "stu004",
            "sql": "SELECT s.name, c.course_id FROM students s JOIN choices c ON s.sid = c.sid",
            "description": "复杂查询也会被正确过滤"
        },
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        console.print(f"\n[bold yellow]{'='*80}[/bold yellow]")
        console.print(f"[bold cyan]{scenario['title']}[/bold cyan]")
        console.print(f"[dim]{scenario['description']}[/dim]")
        console.print(f"[bold yellow]{'='*80}[/bold yellow]\n")
        
        # 创建表格显示信息
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("项目", style="cyan", width=15)
        table.add_column("内容", style="white")
        
        table.add_row("用户名", f"[green]{scenario['username']}[/green]")
        table.add_row("原始SQL", f"[yellow]{scenario['sql']}[/yellow]")
        
        try:
            transformed_sql, warnings = checker.check_and_transform_query(
                scenario['sql'],
                scenario['username']
            )
            
            # 检查SQL是否被修改
            if transformed_sql != scenario['sql']:
                table.add_row(
                    "转换后SQL", 
                    f"[green]{transformed_sql}[/green]"
                )
                table.add_row(
                    "状态", 
                    "[green]✅ 权限控制已应用[/green]"
                )
            else:
                table.add_row(
                    "转换后SQL", 
                    f"[white]{transformed_sql}[/white]"
                )
                table.add_row(
                    "状态", 
                    "[blue]ℹ️  无需过滤（用户有完全访问权限）[/blue]"
                )
            
            if warnings:
                table.add_row("警告", f"[yellow]{', '.join(warnings)}[/yellow]")
            
        except PermissionDeniedException as e:
            table.add_row(
                "状态", 
                f"[red]🚫 权限被拒绝[/red]"
            )
            table.add_row(
                "错误信息", 
                f"[red]{str(e)}[/red]"
            )
        
        console.print(table)
        
        # 暂停以便查看
        if i < len(scenarios):
            console.print("\n[dim]按Enter继续...[/dim]")
            input()
    
    # 总结
    console.print("\n")
    console.print(Panel.fit(
        "[bold green]✅ 演示完成！[/bold green]\n\n"
        "权限控制功能特点：\n"
        "• 透明的SQL转换\n"
        "• 基于角色的访问控制\n"
        "• 行级数据过滤\n"
        "• 自动权限检查\n"
        "• 配置文件管理",
        title="[bold cyan]功能总结[/bold cyan]",
        border_style="green"
    ))


def show_config():
    """显示当前权限配置"""
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]当前权限配置概览[/bold cyan]",
        border_style="cyan"
    ))
    
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("表名", style="cyan", width=15)
    table.add_column("角色模式", style="yellow", width=15)
    table.add_column("行级过滤", style="green", width=30)
    table.add_column("说明", style="white")
    
    # students表
    table.add_row(
        "students",
        "^admin$",
        "无限制",
        "管理员可以看到所有学生"
    )
    table.add_row(
        "",
        "^teach.*",
        "无限制",
        "教师可以看到所有学生"
    )
    table.add_row(
        "",
        "^stu.*",
        "sid = '{username}'",
        "学生只能看到自己"
    )
    
    # teacher表
    table.add_row(
        "teacher",
        "^admin$",
        "无限制",
        "管理员可以看到所有教师"
    )
    table.add_row(
        "",
        "^teach.*",
        "tid = '{username}'",
        "教师只能看到自己"
    )
    table.add_row(
        "",
        "^stu.*",
        "拒绝访问",
        "学生不能访问教师表"
    )
    
    # choices表
    table.add_row(
        "choices",
        "^admin$",
        "无限制",
        "管理员可以看到所有选课"
    )
    table.add_row(
        "",
        "^teach.*",
        "tid = '{username}'",
        "教师只能看到自己的课程"
    )
    table.add_row(
        "",
        "^stu.*",
        "sid = '{username}'",
        "学生只能看到自己的选课"
    )
    
    console.print(table)
    console.print("\n[dim]配置文件位置: config/permissions.yaml[/dim]")


if __name__ == "__main__":
    try:
        console.clear()
        
        # 显示配置
        show_config()
        
        console.print("\n[bold cyan]准备开始演示...[/bold cyan]")
        console.print("[dim]按Enter开始[/dim]")
        input()
        
        # 运行演示
        demo_permission_control()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]演示已取消[/yellow]")
    except Exception as e:
        console.print(f"\n[red]错误: {e}[/red]")
        import traceback
        traceback.print_exc()

