#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实时服务验证测试"""

import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json

print("=" * 70)
print("实时服务验证测试")
print("=" * 70)

tests_passed = 0
tests_total = 0

# 测试后端
print("\n[1] 测试后端服务...")
tests_total += 1
try:
    r = requests.get("http://localhost:8000/api/public/health", timeout=3)
    if r.status_code == 200:
        data = r.json()
        print(f"  ✅ 后端运行正常")
        print(f"     服务: {data.get('service')}")
        print(f"     版本: {data.get('version')}")
        tests_passed += 1
    else:
        print(f"  ❌ 后端响应异常: {r.status_code}")
except Exception as e:
    print(f"  ❌ 后端连接失败: {e}")

# 测试登录
print("\n[2] 测试用户登录...")
tests_total += 1
try:
    r = requests.post(
        "http://localhost:8000/api/auth/login",
        json={"username": "admin", "password": "admin123"},
        timeout=3
    )
    if r.status_code == 200:
        data = r.json()
        if data.get("success") and data.get("token"):
            print(f"  ✅ 登录成功")
            print(f"     用户: {data['user']['username']}")
            print(f"     类型: {data['user']['user_type']}")
            token = data["token"]
            tests_passed += 1
            
            # 测试受保护的API
            print("\n[3] 测试受保护的API...")
            tests_total += 1
            try:
                r = requests.get(
                    "http://localhost:8000/api/protected/database/status",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=3
                )
                if r.status_code == 200:
                    data = r.json()
                    print(f"  ✅ API访问正常")
                    print(f"     数据库连接: {data.get('connected')}")
                    tests_passed += 1
                else:
                    print(f"  ❌ API响应异常: {r.status_code}")
            except Exception as e:
                print(f"  ❌ API请求失败: {e}")
        else:
            print(f"  ❌ 登录失败: {data.get('message')}")
    else:
        print(f"  ❌ 登录请求失败: {r.status_code}")
except Exception as e:
    print(f"  ❌ 登录测试失败: {e}")
    tests_total += 1  # 跳过的API测试

# 测试前端
print("\n[4] 测试前端服务...")
tests_total += 1
frontend_ports = [5173, 5174, 5175]
frontend_ok = False
for port in frontend_ports:
    try:
        r = requests.get(f"http://localhost:{port}", timeout=2)
        if r.status_code < 500:
            print(f"  ✅ 前端运行在端口 {port}")
            frontend_ok = True
            tests_passed += 1
            break
    except:
        pass

if not frontend_ok:
    print(f"  ⚠️  前端服务未完全就绪")
    print(f"     可能端口: {', '.join(map(str, frontend_ports))}")
    print(f"     建议: 在浏览器中手动访问测试")

# 总结
print("\n" + "=" * 70)
print(f"测试完成: {tests_passed}/{tests_total} 通过")
print(f"通过率: {tests_passed/tests_total*100:.1f}%")

if tests_passed >= tests_total * 0.75:
    print("状态: ✅ 系统运行正常")
else:
    print("状态: ⚠️  系统存在问题")

print("=" * 70)


