#!/bin/bash

echo "════════════════════════════════════════════════════════"
echo "��� AskDB v2.0 API 功能测试"
echo "════════════════════════════════════════════════════════"

BASE_URL="http://localhost:8000"

echo ""
echo "测试 1: 健康检查 API"
echo "─────────────────────────────────────────────────────────"
curl -s $BASE_URL/api/public/health | python -m json.tool

echo ""
echo ""
echo "测试 2: 根路径"
echo "─────────────────────────────────────────────────────────"
curl -s $BASE_URL/ | python -m json.tool

echo ""
echo ""
echo "测试 3: 登录测试（默认管理员账户）"
echo "─────────────────────────────────────────────────────────"
TOKEN=$(curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | \
  python -c "import sys, json; data=json.load(sys.stdin); print(data.get('token', ''))")

if [ ! -z "$TOKEN" ]; then
    echo "✅ 登录成功！Token 获取成功"
    echo "Token 前20个字符: ${TOKEN:0:20}..."
    
    echo ""
    echo ""
    echo "测试 4: 数据库状态检查（需要认证）"
    echo "─────────────────────────────────────────────────────────"
    curl -s $BASE_URL/api/protected/database/status \
      -H "Authorization: Bearer $TOKEN" | python -m json.tool
    
    echo ""
    echo ""
    echo "测试 5: 索引状态检查（新功能）"
    echo "─────────────────────────────────────────────────────────"
    curl -s $BASE_URL/api/protected/index/status \
      -H "Authorization: Bearer $TOKEN" | python -m json.tool
    
    echo ""
    echo ""
    echo "测试 6: 索引自动检查（新功能）"
    echo "─────────────────────────────────────────────────────────"
    curl -s $BASE_URL/api/protected/index/auto-check \
      -H "Authorization: Bearer $TOKEN" | python -m json.tool
else
    echo "❌ 登录失败，跳过认证测试"
fi

echo ""
echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ API 测试完成"
echo "════════════════════════════════════════════════════════"
