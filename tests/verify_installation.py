#!/usr/bin/env python3
"""
快速验证 AskDB 增强版安装是否成功
"""

import sys
import os
from pathlib import Path

print("=" * 60)
print("🔍 AskDB 增强版安装验证")
print("=" * 60)

errors = []
warnings = []
success_count = 0

# 1. 检查 Python 版本
print("\n1️⃣ 检查 Python 版本...")
if sys.version_info >= (3, 9):
    print(f"   ✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    success_count += 1
else:
    errors.append(f"Python 版本过低: {sys.version_info.major}.{sys.version_info.minor}")
    print(f"   ❌ 需要 Python >= 3.9")

# 2. 检查必要的包
print("\n2️⃣ 检查必要的 Python 包...")
required_packages = {
    'chromadb': 'ChromaDB',
    'sentence_transformers': 'Sentence Transformers',
    'agno': 'Agno',
    'fastapi': 'FastAPI',
    'sqlalchemy': 'SQLAlchemy',
}

for package, name in required_packages.items():
    try:
        __import__(package)
        print(f"   ✅ {name}")
        success_count += 1
    except ImportError:
        errors.append(f"缺少包: {name}")
        print(f"   ❌ {name} (运行: pip install {package})")

# 3. 检查文件结构
print("\n3️⃣ 检查文件结构...")
required_files = [
    'tools/vector_store.py',
    'tools/enhanced_tools.py',
    'backend/main.py',
    'askdb_agno.py',
    'data/business_metadata.json',
]

for file_path in required_files:
    if Path(file_path).exists():
        print(f"   ✅ {file_path}")
        success_count += 1
    else:
        errors.append(f"缺少文件: {file_path}")
        print(f"   ❌ {file_path}")

# 4. 检查前端文件
print("\n4️⃣ 检查前端组件...")
frontend_files = [
    'frontend/src/components/IndexManagement.jsx',
    'frontend/src/components/DangerConfirmDialog.jsx',
    'frontend/src/components/ChatSidebar.jsx',
]

for file_path in frontend_files:
    if Path(file_path).exists():
        print(f"   ✅ {file_path}")
        success_count += 1
    else:
        warnings.append(f"前端文件缺失: {file_path}")
        print(f"   ⚠️  {file_path}")

# 5. 检查环境配置
print("\n5️⃣ 检查环境配置...")
if Path('.env').exists():
    print("   ✅ .env 文件存在")
    success_count += 1
    
    # 检查必要的配置项
    with open('.env', 'r', encoding='utf-8') as f:
        env_content = f.read()
        
    required_configs = ['GEMINI_API_KEY', 'DEFAULT_DB_TYPE', 'DEFAULT_DB_NAME']
    for config in required_configs:
        if config in env_content:
            print(f"   ✅ {config} 已配置")
            success_count += 1
        else:
            warnings.append(f"环境变量未配置: {config}")
            print(f"   ⚠️  {config} 未配置")
else:
    warnings.append(".env 文件不存在")
    print("   ⚠️  .env 文件不存在（从 env_example.txt 复制）")

# 6. 检查目录
print("\n6️⃣ 检查必要的目录...")
required_dirs = ['logs', 'data']
for dir_path in required_dirs:
    if Path(dir_path).exists():
        print(f"   ✅ {dir_path}/ 目录存在")
        success_count += 1
    else:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {dir_path}/ 目录已创建")
        success_count += 1

# 7. 测试导入核心模块
print("\n7️⃣ 测试导入核心模块...")
try:
    from tools.vector_store import VectorStore
    print("   ✅ VectorStore 导入成功")
    success_count += 1
except Exception as e:
    errors.append(f"VectorStore 导入失败: {str(e)}")
    print(f"   ❌ VectorStore 导入失败")

try:
    from tools.enhanced_tools import EnhancedDatabaseTools
    print("   ✅ EnhancedDatabaseTools 导入成功")
    success_count += 1
except Exception as e:
    errors.append(f"EnhancedDatabaseTools 导入失败: {str(e)}")
    print(f"   ❌ EnhancedDatabaseTools 导入失败")

# 8. 测试 VectorStore 初始化
print("\n8️⃣ 测试 VectorStore 初始化...")
try:
    from tools.vector_store import VectorStore
    vs = VectorStore(persist_directory="data/test_vector_db")
    stats = vs.get_index_stats()
    print(f"   ✅ VectorStore 初始化成功")
    print(f"      - 表索引: {stats['tables']}")
    print(f"      - 列索引: {stats['columns']}")
    print(f"      - 业务术语: {stats['business_terms']}")
    success_count += 1
except Exception as e:
    warnings.append(f"VectorStore 初始化警告: {str(e)}")
    print(f"   ⚠️  VectorStore 初始化失败: {str(e)[:50]}...")

# 总结
print("\n" + "=" * 60)
print("📊 验证结果")
print("=" * 60)
print(f"✅ 成功检查项: {success_count}")
print(f"❌ 错误: {len(errors)}")
print(f"⚠️  警告: {len(warnings)}")

if errors:
    print("\n❌ 发现严重错误:")
    for error in errors:
        print(f"   - {error}")
    print("\n请先解决这些错误再启动系统。")
    sys.exit(1)

if warnings:
    print("\n⚠️  发现警告:")
    for warning in warnings:
        print(f"   - {warning}")
    print("\n这些警告不影响运行，但建议处理。")

if not errors:
    print("\n" + "=" * 60)
    print("🎉 验证通过！AskDB 增强版已准备就绪！")
    print("=" * 60)
    print("\n下一步:")
    print("1. 启动后端: python start_backend.py")
    print("2. 启动前端: cd frontend && npm run dev")
    print("3. 访问: http://localhost:5173")
    print("4. 登录后点击"索引管理"建立索引")
    print("\n详细文档:")
    print("- 快速开始: QUICK_START.md")
    print("- 完整指南: DEPLOYMENT_GUIDE.md")
    print("- 项目交付: PROJECT_DELIVERY.md")
    print("=" * 60)
    sys.exit(0)


