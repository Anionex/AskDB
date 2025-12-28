#!/usr/bin/env python3
"""测试历史消息API是否正常工作"""

import requests
import json

API_BASE = "http://localhost:8000/api"

def test_history_api():
    print("=" * 80)
    print("测试会话历史API")
    print("=" * 80)
    
    # 1. 先登录获取token
    print("\n1. 尝试登录...")
    login_response = requests.post(f"{API_BASE}/auth/login", json={
        "username": "test_user",
        "password": "123456"
    })
    
    print(f"   登录响应: {login_response.status_code}")
    print(f"   响应内容: {login_response.text}")
    
    if not login_response.ok:
        print(f"❌ 登录失败: {login_response.status_code}")
        print(f"   尝试使用其他用户...")
        # 尝试perf_test_user
        login_response = requests.post(f"{API_BASE}/auth/login", json={
            "username": "perf_test_user",
            "password": "123456"
        })
        if not login_response.ok:
            print(f"❌ 仍然失败，请检查用户名和密码")
            return
    
    login_data = login_response.json()
    token = login_data.get('token')
    if not token:
        print(f"❌ 登录响应中没有token: {login_data}")
        return
    
    print(f"✅ 登录成功，获取到token: {token[:20]}...")
    
    # 2. 获取会话列表
    print("\n2. 获取会话列表...")
    headers = {"Authorization": f"Bearer {token}"}
    sessions_response = requests.get(f"{API_BASE}/protected/sessions", headers=headers)
    
    if not sessions_response.ok:
        print(f"❌ 获取会话列表失败: {sessions_response.status_code}")
        return
    
    sessions = sessions_response.json().get('sessions', [])
    print(f"✅ 获取到 {len(sessions)} 个会话")
    
    if len(sessions) == 0:
        print("⚠️  没有会话，无法测试")
        return
    
    # 3. 找一个有消息的会话
    target_session = None
    for session in sessions:
        if session['message_count'] > 0:
            target_session = session
            break
    
    if not target_session:
        print("⚠️  没有找到有消息的会话")
        return
    
    print(f"\n3. 测试会话: {target_session['id']}")
    print(f"   标题: {target_session['title']}")
    print(f"   消息数: {target_session['message_count']}")
    
    # 4. 获取历史消息
    print(f"\n4. 获取历史消息...")
    history_response = requests.get(
        f"{API_BASE}/protected/sessions/{target_session['id']}/history",
        headers=headers
    )
    
    print(f"   状态码: {history_response.status_code}")
    print(f"   响应头: {dict(history_response.headers)}")
    
    if not history_response.ok:
        print(f"❌ 获取历史失败: {history_response.text}")
        return
    
    history_data = history_response.json()
    print(f"\n✅ API返回数据:")
    print(f"   success: {history_data.get('success')}")
    print(f"   session_id: {history_data.get('session_id')}")
    print(f"   消息数量: {len(history_data.get('messages', []))}")
    
    messages = history_data.get('messages', [])
    if messages:
        print(f"\n📨 前3条消息预览:")
        for i, msg in enumerate(messages[:3]):
            role_emoji = "👤" if msg['type'] == 'user' else "🤖"
            content_preview = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
            print(f"   {role_emoji} [{msg['type']}] {content_preview}")
        
        print("\n✅✅✅ API正常工作！返回了历史消息！")
        print("\n如果前端看不到，问题在前端加载逻辑。")
    else:
        print("\n❌ API返回成功，但消息列表为空！")
        print("这是个bug - 数据库有数据但API返回空列表")
    
    # 5. 完整响应
    print(f"\n完整JSON响应:")
    print(json.dumps(history_data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    try:
        test_history_api()
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请确保后端正在运行: uv run python backend/main.py")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

