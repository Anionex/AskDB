#!/usr/bin/env python3
"""
测试JWT认证功能
验证后端重启后token仍然有效
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_jwt_authentication():
    """测试JWT认证流程"""
    print("=" * 60)
    print("JWT 认证测试")
    print("=" * 60)
    
    # 1. 登录获取token
    print("\n1. 测试登录...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    print(f"状态码: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ 登录失败: {response.text}")
        return
    
    result = response.json()
    print(f"✅ 登录成功")
    print(f"   用户: {result['user']['username']}")
    print(f"   类型: {result['user']['user_type']}")
    
    token = result['token']
    print(f"\n获得JWT Token (前30字符): {token[:30]}...")
    
    # 2. 使用token访问受保护的API
    print("\n2. 测试使用token访问受保护的API...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(f"{BASE_URL}/api/protected/database/status", headers=headers)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Token验证成功，可以访问受保护的API")
        db_status = response.json()
        print(f"   数据库连接状态: {db_status.get('connected')}")
    else:
        print(f"❌ Token验证失败: {response.text}")
        return
    
    # 3. 验证token
    print("\n3. 测试token验证接口...")
    verify_data = {"token": token}
    response = requests.post(f"{BASE_URL}/api/auth/verify", json=verify_data)
    
    if response.status_code == 200:
        result = response.json()
        if result['valid']:
            print("✅ Token验证通过")
            print(f"   用户信息: {result['user']['username']}")
        else:
            print("❌ Token无效")
    else:
        print(f"❌ 验证请求失败: {response.text}")
    
    # 4. 保存token供后续测试使用
    print("\n4. 保存token到文件...")
    with open("test_token.txt", "w") as f:
        f.write(token)
    print("✅ Token已保存到 test_token.txt")
    
    print("\n" + "=" * 60)
    print("测试说明：")
    print("1. 现在可以重启后端服务")
    print("2. 重启后运行 test_jwt_auth_after_restart.py")
    print("3. 验证token在后端重启后仍然有效")
    print("=" * 60)

def test_token_from_file():
    """从文件读取token并测试"""
    print("\n" + "=" * 60)
    print("测试保存的Token")
    print("=" * 60)
    
    try:
        with open("test_token.txt", "r") as f:
            token = f.read().strip()
        
        print(f"\n从文件读取Token (前30字符): {token[:30]}...")
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        print("\n测试访问受保护的API...")
        response = requests.get(f"{BASE_URL}/api/protected/database/status", headers=headers)
        
        if response.status_code == 200:
            print("✅ Token仍然有效！后端重启不影响认证")
            db_status = response.json()
            print(f"   数据库连接状态: {db_status.get('connected')}")
        else:
            print(f"❌ Token已失效: {response.text}")
            
    except FileNotFoundError:
        print("❌ 未找到 test_token.txt 文件")
        print("   请先运行 test_jwt_authentication() 生成token")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "after-restart":
        # 测试后端重启后token是否有效
        test_token_from_file()
    else:
        # 完整的认证测试
        test_jwt_authentication()

