#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端（E2E）集成测试
测试前后端完整工作流程
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 70)
print("AskDB 端到端集成测试")
print("=" * 70)

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
TEST_RESULTS = []

def log_test(test_name, passed, message=""):
    """记录测试结果"""
    status = "✅ 通过" if passed else "❌ 失败"
    TEST_RESULTS.append((test_name, passed, message))
    print(f"\n{status} - {test_name}")
    if message:
        print(f"   {message}")

def wait_for_service(url, name, max_retries=3, delay=2):
    """等待服务启动"""
    for i in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 500:
                return True
        except:
            pass
        if i < max_retries - 1:
            print(f"   等待{name}启动... ({i+1}/{max_retries})")
            time.sleep(delay)
    return False

# 测试1: 服务可用性检查
print("\n" + "=" * 70)
print("测试 1: 服务可用性检查")
print("=" * 70)

backend_available = False
try:
    response = requests.get(f"{BACKEND_URL}/api/public/health", timeout=5)
    backend_available = response.status_code == 200
    if backend_available:
        data = response.json()
        log_test("后端服务可用", True, 
                f"服务: {data.get('service')}, 版本: {data.get('version')}")
    else:
        log_test("后端服务可用", False, f"状态码: {response.status_code}")
except Exception as e:
    log_test("后端服务可用", False, f"无法连接: {str(e)[:50]}")

frontend_available = False
try:
    response = requests.get(FRONTEND_URL, timeout=5)
    frontend_available = response.status_code < 500
    if frontend_available:
        log_test("前端服务可用", True, "前端服务响应正常")
    else:
        log_test("前端服务可用", False, f"状态码: {response.status_code}")
except Exception as e:
    log_test("前端服务可用", False, f"无法连接: {str(e)[:50]}")

# 测试2: 用户认证流程
print("\n" + "=" * 70)
print("测试 2: 用户认证流程")
print("=" * 70)

token = None
if backend_available:
    # 登录测试
    try:
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        response = requests.post(
            f"{BACKEND_URL}/api/auth/login",
            json=login_data,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("token"):
                token = data["token"]
                user = data.get("user", {})
                log_test("管理员登录", True, 
                        f"用户: {user.get('username')}, 类型: {user.get('user_type')}")
            else:
                log_test("管理员登录", False, data.get("message", "登录失败"))
        else:
            log_test("管理员登录", False, f"状态码: {response.status_code}")
    except Exception as e:
        log_test("管理员登录", False, f"错误: {str(e)[:50]}")
    
    # Token验证测试
    if token:
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/auth/verify",
                json={"token": token},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("valid"):
                    log_test("Token验证", True, "Token有效")
                else:
                    log_test("Token验证", False, "Token无效")
            else:
                log_test("Token验证", False, f"状态码: {response.status_code}")
        except Exception as e:
            log_test("Token验证", False, f"错误: {str(e)[:50]}")
else:
    log_test("用户认证流程", False, "后端服务不可用，跳过测试")

# 测试3: 受保护的API访问
print("\n" + "=" * 70)
print("测试 3: 受保护的API访问")
print("=" * 70)

if token:
    headers = {"Authorization": f"Bearer {token}"}
    
    # 数据库状态
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/protected/database/status",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            log_test("数据库状态查询", True, 
                    f"连接: {data.get('connected')}, 类型: {data.get('database_type', 'N/A')}")
        else:
            log_test("数据库状态查询", False, f"状态码: {response.status_code}")
    except Exception as e:
        log_test("数据库状态查询", False, f"错误: {str(e)[:50]}")
    
    # 索引状态
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/protected/index/status",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get('index_stats', {})
            log_test("索引状态查询", True, 
                    f"表: {stats.get('tables', 0)}, 列: {stats.get('columns', 0)}, 术语: {stats.get('business_terms', 0)}")
        else:
            log_test("索引状态查询", False, f"状态码: {response.status_code}")
    except Exception as e:
        log_test("索引状态查询", False, f"错误: {str(e)[:50]}")
    
    # 会话列表
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/protected/sessions",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                sessions = data.get("sessions", [])
                log_test("会话列表查询", True, f"找到 {len(sessions)} 个会话")
            else:
                log_test("会话列表查询", False, "查询失败")
        else:
            log_test("会话列表查询", False, f"状态码: {response.status_code}")
    except Exception as e:
        log_test("会话列表查询", False, f"错误: {str(e)[:50]}")
    
    # 用户列表（管理员功能）
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/protected/users",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            users = response.json()
            log_test("用户列表查询（管理员）", True, f"找到 {len(users)} 个用户")
        else:
            log_test("用户列表查询（管理员）", False, f"状态码: {response.status_code}")
    except Exception as e:
        log_test("用户列表查询（管理员）", False, f"错误: {str(e)[:50]}")
else:
    log_test("受保护的API访问", False, "未获取到有效Token，跳过测试")

# 测试4: CORS和跨域访问
print("\n" + "=" * 70)
print("测试 4: CORS 配置检查")
print("=" * 70)

if backend_available:
    try:
        response = requests.options(
            f"{BACKEND_URL}/api/public/health",
            headers={"Origin": "http://localhost:5173"},
            timeout=5
        )
        
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers")
        }
        
        has_cors = any(cors_headers.values())
        if has_cors:
            log_test("CORS 配置", True, "跨域访问已正确配置")
        else:
            log_test("CORS 配置", False, "未检测到CORS头")
    except Exception as e:
        log_test("CORS 配置", False, f"错误: {str(e)[:50]}")

# 测试5: 数据持久化检查
print("\n" + "=" * 70)
print("测试 5: 数据持久化检查")
print("=" * 70)

data_files = {
    "data/users.db": "用户数据库",
    "data/askdb_sessions.db": "会话数据库",
    "data/business_metadata.json": "业务元数据"
}

for file_path, description in data_files.items():
    exists = Path(file_path).exists()
    if exists:
        size = Path(file_path).stat().st_size
        log_test(description, True, f"{file_path} ({size} 字节)")
    else:
        log_test(description, False, f"{file_path} 不存在")

# 测试6: 日志文件检查
print("\n" + "=" * 70)
print("测试 6: 日志文件检查")
print("=" * 70)

log_files = [
    "backend.log",
    "frontend.log"
]

for log_file in log_files:
    if Path(log_file).exists():
        size = Path(log_file).stat().st_size
        log_test(f"日志文件: {log_file}", True, f"{size} 字节")
    else:
        log_test(f"日志文件: {log_file}", False, "文件不存在（可能未启用日志）")

# 测试7: 完整工作流模拟
print("\n" + "=" * 70)
print("测试 7: 完整工作流模拟")
print("=" * 70)

workflow_passed = False
if backend_available and token:
    try:
        # 步骤1: 获取数据库状态
        response = requests.get(
            f"{BACKEND_URL}/api/protected/database/status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        step1 = response.status_code == 200
        
        # 步骤2: 获取索引状态
        response = requests.get(
            f"{BACKEND_URL}/api/protected/index/status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        step2 = response.status_code == 200
        
        # 步骤3: 获取会话列表
        response = requests.get(
            f"{BACKEND_URL}/api/protected/sessions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        step3 = response.status_code == 200
        
        workflow_passed = step1 and step2 and step3
        
        if workflow_passed:
            log_test("完整工作流", True, "登录 → 查询状态 → 获取会话")
        else:
            failed_steps = []
            if not step1: failed_steps.append("数据库状态")
            if not step2: failed_steps.append("索引状态")
            if not step3: failed_steps.append("会话列表")
            log_test("完整工作流", False, f"失败步骤: {', '.join(failed_steps)}")
            
    except Exception as e:
        log_test("完整工作流", False, f"错误: {str(e)[:50]}")
else:
    log_test("完整工作流", False, "服务不可用或认证失败")

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
    for name, passed_test, message in TEST_RESULTS:
        if not passed_test:
            print(f"  ❌ {name}")
            if message:
                print(f"     {message}")

# 系统健康评分
print("\n" + "=" * 70)
print("🏥 系统健康评分")
print("=" * 70)

health_score = passed / total * 100

if health_score >= 90:
    health_status = "优秀 ✨"
    health_desc = "系统运行状态良好，所有核心功能正常"
elif health_score >= 75:
    health_status = "良好 👍"
    health_desc = "系统基本正常，部分功能可能需要注意"
elif health_score >= 60:
    health_status = "一般 ⚠️"
    health_desc = "系统存在一些问题，建议检查失败的测试"
else:
    health_status = "差 ❌"
    health_desc = "系统存在严重问题，需要立即处理"

print(f"\n健康评分: {health_score:.1f}分")
print(f"健康状态: {health_status}")
print(f"说明: {health_desc}")

# 保存测试报告
report_path = "test_e2e_results.json"
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed/total*100:.1f}%",
        "health_score": health_score,
        "health_status": health_status,
        "backend_available": backend_available,
        "frontend_available": frontend_available,
        "results": [
            {"test": name, "passed": p, "message": msg}
            for name, p, msg in TEST_RESULTS
        ]
    }, f, indent=2, ensure_ascii=False)

print(f"\n📄 E2E测试报告已保存: {report_path}")

print("\n" + "=" * 70)
print("测试完成！")
print("=" * 70)

# 退出码
sys.exit(0 if health_score >= 75 else 1)

