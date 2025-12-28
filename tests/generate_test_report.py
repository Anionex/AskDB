#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合测试报告生成器
整合所有测试结果并生成完整报告
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 70)
print("AskDB 综合测试报告生成器")
print("=" * 70)

# 读取所有测试结果
test_reports = {
    "backend": "test_results.json",
    "frontend": "test_frontend_results.json",
    "e2e": "test_e2e_results.json"
}

all_results = {}
total_tests = 0
total_passed = 0
total_failed = 0

print("\n📁 正在收集测试报告...")

for test_type, report_file in test_reports.items():
    report_path = Path(report_file)
    if report_path.exists():
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_results[test_type] = data
            total_tests += data.get('total', 0)
            total_passed += data.get('passed', 0)
            total_failed += data.get('failed', 0)
            print(f"   ✅ {test_type.upper()}: {data.get('pass_rate', 'N/A')}")
    else:
        print(f"   ⚠️  {test_type.upper()}: 报告未找到")

# 计算总体通过率
overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

# 生成综合报告
print("\n" + "=" * 70)
print("📋 综合测试报告")
print("=" * 70)

print(f"""
测试执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔢 测试统计
─────────────────────────────────────────────────────────
总测试数:    {total_tests}
通过数:      {total_passed} ✅
失败数:      {total_failed} ❌
总通过率:    {overall_pass_rate:.1f}%

📦 分类测试结果
─────────────────────────────────────────────────────────
""")

# 详细报告
for test_type, data in all_results.items():
    print(f"\n【{test_type.upper()} 测试】")
    print(f"  测试数: {data.get('total', 0)}")
    print(f"  通过: {data.get('passed', 0)}")
    print(f"  失败: {data.get('failed', 0)}")
    print(f"  通过率: {data.get('pass_rate', 'N/A')}")
    
    # 显示失败的测试
    failed_tests = [r for r in data.get('results', []) if not r.get('passed')]
    if failed_tests:
        print(f"\n  失败的测试:")
        for test in failed_tests:
            print(f"    ❌ {test.get('test')}")
            if test.get('message'):
                print(f"       {test.get('message')}")

# 系统健康评分
print("\n" + "=" * 70)
print("🏥 系统健康评估")
print("=" * 70)

health_score = overall_pass_rate

if health_score >= 95:
    health_status = "优秀 ✨"
    health_desc = "系统运行状态非常好，所有核心功能正常"
    recommendations = [
        "✅ 系统已准备好投入生产使用",
        "✅ 定期监控日志和性能指标",
        "✅ 保持依赖包更新"
    ]
elif health_score >= 85:
    health_status = "良好 👍"
    health_desc = "系统基本正常，有少量问题需要关注"
    recommendations = [
        "⚠️ 检查并修复失败的测试",
        "✅ 监控系统运行状态",
        "✅ 考虑优化失败的部分"
    ]
elif health_score >= 70:
    health_status = "一般 ⚠️"
    health_desc = "系统存在一些问题，建议优先处理"
    recommendations = [
        "❌ 立即检查所有失败的测试",
        "⚠️ 修复关键功能问题",
        "⚠️ 暂不建议投入生产"
    ]
else:
    health_status = "差 ❌"
    health_desc = "系统存在严重问题，需要立即处理"
    recommendations = [
        "❌ 立即停止生产部署",
        "❌ 优先修复所有失败测试",
        "❌ 进行全面代码审查"
    ]

print(f"\n健康评分: {health_score:.1f}分")
print(f"健康状态: {health_status}")
print(f"评估说明: {health_desc}")

print("\n💡 建议:")
for rec in recommendations:
    print(f"  {rec}")

# 测试覆盖率分析
print("\n" + "=" * 70)
print("📈 测试覆盖率分析")
print("=" * 70)

coverage_areas = {
    "模块导入": "backend",
    "文件结构": "backend",
    "VectorStore功能": "backend",
    "后端API": "backend",
    "前端组件": "frontend",
    "状态管理": "frontend",
    "用户认证": "e2e",
    "API访问控制": "e2e",
    "CORS配置": "e2e",
    "数据持久化": "e2e",
    "完整工作流": "e2e"
}

print("\n覆盖的功能区域:")
for area, test_type in coverage_areas.items():
    print(f"  ✅ {area} ({test_type})")

# 已知问题
print("\n" + "=" * 70)
print("⚠️  已知问题")
print("=" * 70)

known_issues = []
for test_type, data in all_results.items():
    failed_tests = [r for r in data.get('results', []) if not r.get('passed')]
    for test in failed_tests:
        known_issues.append({
            "type": test_type,
            "test": test.get('test'),
            "message": test.get('message', '')
        })

if known_issues:
    print(f"\n发现 {len(known_issues)} 个问题:")
    for i, issue in enumerate(known_issues, 1):
        print(f"\n  {i}. [{issue['type'].upper()}] {issue['test']}")
        if issue['message']:
            print(f"     原因: {issue['message']}")
else:
    print("\n  ✅ 未发现问题！")

# 环境信息
print("\n" + "=" * 70)
print("🔧 环境信息")
print("=" * 70)

import sys
import platform

print(f"""
Python版本:  {sys.version.split()[0]}
操作系统:    {platform.system()} {platform.release()}
架构:        {platform.machine()}
工作目录:    {Path.cwd()}
""")

# 生成JSON报告
comprehensive_report = {
    "generated_at": datetime.now().isoformat(),
    "summary": {
        "total_tests": total_tests,
        "passed": total_passed,
        "failed": total_failed,
        "pass_rate": f"{overall_pass_rate:.1f}%",
        "health_score": health_score,
        "health_status": health_status
    },
    "test_results": all_results,
    "known_issues": known_issues,
    "recommendations": recommendations,
    "coverage_areas": list(coverage_areas.keys()),
    "environment": {
        "python_version": sys.version.split()[0],
        "platform": platform.system(),
        "architecture": platform.machine()
    }
}

report_path = "COMPREHENSIVE_TEST_REPORT.json"
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(comprehensive_report, f, indent=2, ensure_ascii=False)

print(f"📄 综合测试报告已保存: {report_path}")

# 生成Markdown报告
md_report_path = "TEST_REPORT_SUMMARY.md"
with open(md_report_path, 'w', encoding='utf-8') as f:
    f.write("# AskDB 测试报告\n\n")
    f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    f.write("## 📊 测试概览\n\n")
    f.write(f"| 指标 | 数值 |\n")
    f.write(f"|------|------|\n")
    f.write(f"| 总测试数 | {total_tests} |\n")
    f.write(f"| 通过数 | {total_passed} ✅ |\n")
    f.write(f"| 失败数 | {total_failed} ❌ |\n")
    f.write(f"| 通过率 | {overall_pass_rate:.1f}% |\n")
    f.write(f"| 健康评分 | {health_score:.1f}分 |\n")
    f.write(f"| 健康状态 | {health_status} |\n\n")
    
    f.write("## 📦 分类测试结果\n\n")
    for test_type, data in all_results.items():
        f.write(f"### {test_type.upper()} 测试\n\n")
        f.write(f"- **测试数**: {data.get('total', 0)}\n")
        f.write(f"- **通过**: {data.get('passed', 0)}\n")
        f.write(f"- **失败**: {data.get('failed', 0)}\n")
        f.write(f"- **通过率**: {data.get('pass_rate', 'N/A')}\n\n")
    
    f.write("## 💡 建议\n\n")
    for rec in recommendations:
        f.write(f"- {rec}\n")
    
    f.write("\n## ⚠️ 已知问题\n\n")
    if known_issues:
        for i, issue in enumerate(known_issues, 1):
            f.write(f"{i}. **[{issue['type'].upper()}]** {issue['test']}\n")
            if issue['message']:
                f.write(f"   - {issue['message']}\n")
    else:
        f.write("✅ 未发现问题！\n")
    
    f.write(f"\n---\n")
    f.write(f"*报告由 AskDB 测试系统自动生成*\n")

print(f"📄 Markdown报告已保存: {md_report_path}")

print("\n" + "=" * 70)
print("✅ 报告生成完成！")
print("=" * 70)

# 返回状态码
sys.exit(0 if health_score >= 85 else 1)

