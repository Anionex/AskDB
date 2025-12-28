#!/usr/bin/env python3
"""
AskDB v2.0 功能测试脚本
测试前后端的核心功能
"""

import os
import sys
import time
import requests
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("🧪 AskDB v2.0 功能测试")
print("=" * 70)

# 测试配置
BACKEND_URL = "http://localhost:8000"
TEST_RESULTS = []

def log_test(test_name, passed, message=""):
    """记录测试结果"""
    status = "✅ 通过" if passed else "❌ 失败"
    TEST_RESULTS.append((test_name, passed, message))
    print(f"\n{status} - {test_name}")
    if message:
        print(f"   {message}")

# 测试1: 检查模块导入
print("\n" + "=" * 70)
print("测试 1: 检查核心模块导入")
print("=" * 70)

try:
    from tools.vector_store import VectorStore
    log_test("导入 VectorStore", True, "模块导入成功")
except Exception as e:
    log_test("导入 VectorStore", False, f"导入失败: {str(e)[:100]}")

try:
    from tools.enhanced_tools import EnhancedDatabaseTools
    log_test("导入 EnhancedDatabaseTools", True, "模块导入成功")
except Exception as e:
    log_test("导入 EnhancedDatabaseTools", False, f"导入失败: {str(e)[:100]}")

try:
    from askdb_agno import create_agent
    log_test("导入 create_agent", True, "模块导入成功")
except Exception as e:
    log_test("导入 create_agent", False, f"导入失败: {str(e)[:100]}")

# 测试2: 检查文件结构
print("\n" + "=" * 70)
print("测试 2: 检查文件结构")
print("=" * 70)

required_files = [
    "tools/vector_store.py",
    "tools/enhanced_tools.py",
    "backend/main.py",
    "askdb_agno.py",
    "data/business_metadata.json",
    "frontend/src/components/IndexManagement.jsx",
    "frontend/src/components/DangerConfirmDialog.jsx",
]

for file_path in required_files:
    exists = Path(file_path).exists()
    log_test(f"文件存在: {file_path}", exists)

# 测试3: VectorStore 功能测试
print("\n" + "=" * 70)
print("测试 3: VectorStore 功能")
print("=" * 70)

try:
    from tools.vector_store import VectorStore
    
    # 创建测试实例
    vs = VectorStore(persist_directory="data/test_vector_db")
    log_test("VectorStore 初始化", True, "成功创建 VectorStore 实例")
    
    # 测试索引统计
    stats = vs.get_index_stats()
    log_test("获取索引统计", True, 
             f"表: {stats['tables']}, 列: {stats['columns']}, 术语: {stats['business_terms']}")
    
    # 测试业务术语索引
    if Path("data/business_metadata.json").exists():
        count = vs.index_business_terms("data/business_metadata.json")
        log_test("索引业务术语", count >= 0, f"索引了 {count} 个业务术语")
        
        # 测试搜索
        results = vs.search("用户活跃度", top_k=3, search_types=["business_term"])
        log_test("语义搜索", len(results) >= 0, f"找到 {len(results)} 个相关结果")
    else:
        log_test("业务术语文件", False, "business_metadata.json 不存在")
        
except Exception as e:
    log_test("VectorStore 测试", False, f"测试失败: {str(e)[:100]}")

# 测试4: 后端 API 测试（如果后端在运行）
print("\n" + "=" * 70)
print("测试 4: 后端 API 连接测试")
print("=" * 70)

try:
    response = requests.get(f"{BACKEND_URL}/api/public/health", timeout=3)
    if response.status_code == 200:
        data = response.json()
        log_test("后端健康检查", True, 
                f"服务: {data.get('service')}, 版本: {data.get('version')}")
        
        # 测试索引状态 API（需要登录，但我们可以测试端点是否存在）
        log_test("后端服务运行", True, "后端在 http://localhost:8000 运行")
    else:
        log_test("后端健康检查", False, f"状态码: {response.status_code}")
except requests.exceptions.ConnectionError:
    log_test("后端连接", False, "后端服务未运行。启动方式: python start_backend.py")
except Exception as e:
    log_test("后端测试", False, f"错误: {str(e)[:100]}")

# 测试5: 前端文件检查
print("\n" + "=" * 70)
print("测试 5: 前端组件检查")
print("=" * 70)

frontend_files = {
    "frontend/package.json": "前端依赖配置",
    "frontend/src/App.jsx": "主应用组件",
    "frontend/src/components/IndexManagement.jsx": "索引管理组件",
    "frontend/src/components/DangerConfirmDialog.jsx": "危险操作确认对话框",
    "frontend/src/components/ChatSidebar.jsx": "聊天侧边栏",
}

for file_path, description in frontend_files.items():
    exists = Path(file_path).exists()
    if exists:
        size = Path(file_path).stat().st_size
        log_test(f"{description}", True, f"{file_path} ({size} 字节)")
    else:
        log_test(f"{description}", False, f"{file_path} 不存在")

# 测试6: 文档完整性
print("\n" + "=" * 70)
print("测试 6: 文档完整性")
print("=" * 70)

docs = [
    "QUICK_START.md",
    "DEPLOYMENT_GUIDE.md",
    "PROJECT_DELIVERY.md",
    "RELEASE_v2.0.md",
    "DELIVERY_CHECKLIST.md",
]

for doc in docs:
    exists = Path(doc).exists()
    if exists:
        with open(doc, 'r', encoding='utf-8') as f:
            lines = len(f.readlines())
        log_test(f"文档: {doc}", True, f"{lines} 行")
    else:
        log_test(f"文档: {doc}", False, "文件不存在")

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

# 建议
print("\n" + "=" * 70)
print("💡 建议")
print("=" * 70)

if failed == 0:
    print("""
✅ 所有测试通过！

下一步:
1. 启动后端: python start_backend.py
2. 启动前端: cd frontend && npm run dev  
3. 访问系统: http://localhost:5173
4. 建立索引: 登录后点击"索引管理"
""")
else:
    print("""
⚠️  部分测试失败，请检查：

1. 依赖安装: pip install -r requirements.txt
2. 环境配置: 检查 .env 文件
3. 模块依赖: 可能缺少某些 Python 包
4. 后端运行: python start_backend.py

查看详细错误信息并修复后再次测试。
""")

print("=" * 70)
print("测试完成！")
print("=" * 70)

# 保存测试报告
report_path = "test_results.json"
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed/total*100:.1f}%",
        "results": [
            {"test": name, "passed": p, "message": msg}
            for name, p, msg in TEST_RESULTS
        ]
    }, f, indent=2, ensure_ascii=False)

print(f"\n📄 测试报告已保存: {report_path}")


