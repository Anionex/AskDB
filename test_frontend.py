#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frontend 组件测试
测试前端文件完整性和基本结构
"""

import os
import sys
import json
from pathlib import Path
import subprocess

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 70)
print("AskDB 前端测试")
print("=" * 70)

TEST_RESULTS = []

def log_test(test_name, passed, message=""):
    """记录测试结果"""
    status = "✅ 通过" if passed else "❌ 失败"
    TEST_RESULTS.append((test_name, passed, message))
    print(f"\n{status} - {test_name}")
    if message:
        print(f"   {message}")

# 测试1: 检查前端依赖
print("\n" + "=" * 70)
print("测试 1: 前端依赖检查")
print("=" * 70)

package_json_path = Path("frontend/package.json")
if package_json_path.exists():
    with open(package_json_path, 'r', encoding='utf-8') as f:
        package_data = json.load(f)
    
    log_test("package.json 存在", True, "前端配置文件存在")
    
    # 检查关键依赖
    required_deps = [
        "react",
        "react-dom",
        "antd",
        "axios",
        "react-markdown",
        "zustand"
    ]
    
    deps = package_data.get("dependencies", {})
    for dep in required_deps:
        if dep in deps:
            log_test(f"依赖: {dep}", True, f"版本: {deps[dep]}")
        else:
            log_test(f"依赖: {dep}", False, "缺失")
else:
    log_test("package.json", False, "文件不存在")

# 测试2: 检查前端核心文件
print("\n" + "=" * 70)
print("测试 2: 前端核心文件检查")
print("=" * 70)

core_files = {
    "frontend/src/main.jsx": "应用入口",
    "frontend/src/App.jsx": "主应用组件",
    "frontend/src/App.css": "主样式文件",
    "frontend/index.html": "HTML模板",
    "frontend/vite_config.js": "Vite配置"
}

for file_path, description in core_files.items():
    exists = Path(file_path).exists()
    if exists:
        size = Path(file_path).stat().st_size
        log_test(description, True, f"{file_path} ({size} 字节)")
    else:
        log_test(description, False, f"{file_path} 不存在")

# 测试3: 检查组件文件
print("\n" + "=" * 70)
print("测试 3: React 组件检查")
print("=" * 70)

components = {
    "frontend/src/components/ChatArea.jsx": "聊天区域组件",
    "frontend/src/components/ChatSidebar.jsx": "侧边栏组件",
    "frontend/src/components/IndexManagement.jsx": "索引管理组件",
    "frontend/src/components/DangerConfirmDialog.jsx": "危险操作确认对话框",
    "frontend/src/components/StreamingMarkdown.jsx": "流式Markdown渲染组件"
}

for file_path, description in components.items():
    exists = Path(file_path).exists()
    if exists:
        size = Path(file_path).stat().st_size
        # 简单检查组件是否导出
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            has_export = 'export' in content
        
        log_test(description, has_export, 
                f"{file_path} ({size} 字节, 包含export)")
    else:
        log_test(description, False, f"{file_path} 不存在")

# 测试4: 检查状态管理
print("\n" + "=" * 70)
print("测试 4: 状态管理 Store 检查")
print("=" * 70)

stores = {
    "frontend/src/store/useAuthStore.js": "认证状态管理",
    "frontend/src/store/useChatStore.js": "聊天状态管理"
}

for file_path, description in stores.items():
    exists = Path(file_path).exists()
    if exists:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            has_zustand = 'zustand' in content or 'create' in content
        
        log_test(description, has_zustand, 
                f"{file_path} (使用 Zustand)")
    else:
        log_test(description, False, f"{file_path} 不存在")

# 测试5: 检查配置文件
print("\n" + "=" * 70)
print("测试 5: 配置文件检查")
print("=" * 70)

config_files = {
    "frontend/src/config/antd-theme.js": "Ant Design 主题配置"
}

for file_path, description in config_files.items():
    exists = Path(file_path).exists()
    log_test(description, exists, file_path)

# 测试6: 检查 node_modules（如果已安装）
print("\n" + "=" * 70)
print("测试 6: 依赖安装检查")
print("=" * 70)

node_modules_path = Path("frontend/node_modules")
if node_modules_path.exists():
    log_test("node_modules 存在", True, "前端依赖已安装")
    
    # 检查关键包是否已安装
    key_packages = ["react", "antd", "axios", "zustand"]
    for pkg in key_packages:
        pkg_path = node_modules_path / pkg
        if pkg_path.exists():
            log_test(f"包已安装: {pkg}", True)
        else:
            log_test(f"包已安装: {pkg}", False, "可能需要重新安装")
else:
    log_test("node_modules", False, 
            "依赖未安装。运行: cd frontend && npm install")

# 测试7: 尝试检查前端是否运行
print("\n" + "=" * 70)
print("测试 7: 前端服务检查")
print("=" * 70)

try:
    import requests
    response = requests.get("http://localhost:5173", timeout=2)
    if response.status_code == 200:
        log_test("前端服务运行", True, "前端在 http://localhost:5173 运行")
    else:
        log_test("前端服务运行", False, f"状态码: {response.status_code}")
except requests.exceptions.ConnectionError:
    log_test("前端服务", False, 
            "前端未运行。启动方式: cd frontend && npm run dev")
except Exception as e:
    log_test("前端服务检查", False, f"错误: {str(e)}")

# 测试总结
print("\n" + "=" * 70)
print("📊 测试总结")
print("=" * 70)

passed = sum(1 for _, p, _ in TEST_RESULTS if p)
failed = sum(1 for _, p, _ in TEST_RESULTS if not p)
total = len(TEST_RESULTS)

print(f"\n总测试数: {total}")
print(f"✅ 通过: {passed}")
print(f"❌ 失败: {failed}")
print(f"通过率: {passed/total*100:.1f}%")

if failed > 0:
    print("\n失败的测试:")
    for name, passed, message in TEST_RESULTS:
        if not passed:
            print(f"  ❌ {name}")
            if message:
                print(f"     {message}")

# 保存测试报告
report_path = "test_frontend_results.json"
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump({
        "timestamp": __import__('time').strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "passed": int(passed),
        "failed": int(failed),
        "pass_rate": f"{passed/total*100:.1f}%",
        "results": [
            {"test": name, "passed": p, "message": msg}
            for name, p, msg in TEST_RESULTS
        ]
    }, f, indent=2, ensure_ascii=False)

print(f"\n📄 前端测试报告已保存: {report_path}")

print("\n" + "=" * 70)
print("测试完成！")
print("=" * 70)

