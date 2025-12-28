#!/usr/bin/env python3
"""
测试向量搜索API
"""

import requests
import json

BACKEND_URL = "http://localhost:8000"

def test_vector_search():
    """测试向量搜索API"""
    
    # 1. 先登录获取token
    print("1️⃣  登录获取token...")
    login_response = requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    
    if not login_response.ok:
        print("❌ 登录失败")
        print(login_response.json())
        return
    
    token = login_response.json().get("token")
    print(f"✅ 登录成功，token: {token[:20]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 检查索引状态
    print("\n2️⃣  检查索引状态...")
    status_response = requests.get(
        f"{BACKEND_URL}/api/protected/index/status",
        headers=headers
    )
    
    if status_response.ok:
        status_data = status_response.json()
        stats = status_data.get("index_stats", {})
        print(f"✅ 索引状态: 表={stats.get('tables', 0)}, 列={stats.get('columns', 0)}, 业务术语={stats.get('business_terms', 0)}")
    else:
        print("❌ 获取索引状态失败")
        return
    
    # 3. 测试各种搜索
    test_cases = [
        {
            "name": "搜索业务术语（中文）",
            "query": "用户活跃度",
            "top_k": 3,
            "search_types": ["business_term"]
        },
        {
            "name": "搜索业务术语（英文）",
            "query": "GMV",
            "top_k": 3,
            "search_types": ["business_term"]
        },
        {
            "name": "搜索表",
            "query": "user information",
            "top_k": 3,
            "search_types": ["table"]
        },
        {
            "name": "搜索列",
            "query": "email address",
            "top_k": 3,
            "search_types": ["column"]
        },
        {
            "name": "混合搜索",
            "query": "订单金额",
            "top_k": 5,
            "search_types": None  # 搜索所有类型
        },
        {
            "name": "搜索指标相关",
            "query": "转化率 KPI",
            "top_k": 3,
            "search_types": ["business_term"]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i + 2}️⃣  {test_case['name']}")
        print(f"   查询: '{test_case['query']}'")
        
        search_response = requests.post(
            f"{BACKEND_URL}/api/protected/vector/search",
            headers=headers,
            json={
                "query": test_case["query"],
                "top_k": test_case["top_k"],
                "search_types": test_case["search_types"]
            }
        )
        
        if search_response.ok:
            data = search_response.json()
            if data["success"]:
                print(f"   ✅ {data['message']}")
                for j, result in enumerate(data["results"], 1):
                    print(f"      {j}. [{result['type']}] {result['name']} (相似度: {result['similarity']:.4f})")
                    if result['type'] == 'business_term':
                        metadata = result['metadata']
                        if metadata.get('definition'):
                            print(f"         定义: {metadata['definition']}")
                    elif result['type'] == 'table':
                        metadata = result['metadata']
                        if metadata.get('comment'):
                            print(f"         说明: {metadata['comment']}")
            else:
                print(f"   ⚠️  {data['message']}")
        else:
            print(f"   ❌ 搜索失败: {search_response.status_code}")
            print(f"      {search_response.text}")
    
    print("\n" + "="*60)
    print("🎉 测试完成！")
    print("\n💡 提示:")
    print("   - 使用 search_types=['business_term'] 只搜索业务术语")
    print("   - 使用 search_types=['table'] 只搜索表")
    print("   - 使用 search_types=['column'] 只搜索列")
    print("   - 不指定 search_types 则搜索所有类型")
    print("   - top_k 参数控制返回结果数量")

if __name__ == "__main__":
    try:
        test_vector_search()
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请确保后端正在运行 (http://localhost:8000)")
    except Exception as e:
        print(f"❌ 测试失败: {e}")








