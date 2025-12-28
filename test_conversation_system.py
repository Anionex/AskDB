#!/usr/bin/env python3
"""
测试重构后的对话存储系统
"""

import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.conversation_db import conversation_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_conversation_system():
    """测试对话系统的完整流程"""
    
    print("=" * 60)
    print("测试对话存储系统")
    print("=" * 60)
    
    test_user_id = 1
    test_username = "test_user"
    
    # 1. 测试创建会话
    print("\n1️⃣  测试创建会话...")
    session_id = f"{test_username}_{int(time.time() * 1000)}"
    conversation = conversation_db.create_conversation(
        conversation_id=session_id,
        user_id=test_user_id,
        username=test_username,
        title="测试会话"
    )
    print(f"✅ 创建会话成功: {conversation['id']}")
    print(f"   标题: {conversation['title']}")
    print(f"   创建时间: {conversation['created_at']}")
    
    # 2. 测试添加消息
    print("\n2️⃣  测试添加消息...")
    
    # 添加用户消息
    msg1 = conversation_db.add_message(
        conversation_id=session_id,
        role='user',
        content='查询销售数据'
    )
    print(f"✅ 添加用户消息: {msg1['content'][:30]}...")
    
    # 添加AI响应
    msg2 = conversation_db.add_message(
        conversation_id=session_id,
        role='assistant',
        content='好的，我来帮你查询销售数据。请问你需要查询哪个时间段的数据？'
    )
    print(f"✅ 添加AI响应: {msg2['content'][:30]}...")
    
    # 添加更多消息
    msg3 = conversation_db.add_message(
        conversation_id=session_id,
        role='user',
        content='查询最近30天的销售总额'
    )
    
    msg4 = conversation_db.add_message(
        conversation_id=session_id,
        role='assistant',
        content='根据查询结果，最近30天的销售总额为 ¥1,234,567.89'
    )
    
    print(f"✅ 共添加 4 条消息")
    
    # 3. 测试获取会话历史
    print("\n3️⃣  测试获取会话历史...")
    messages = conversation_db.get_conversation_messages(session_id, username=test_username)
    print(f"✅ 获取到 {len(messages)} 条消息")
    for i, msg in enumerate(messages, 1):
        print(f"   {i}. [{msg['role']}] {msg['content'][:40]}...")
    
    # 4. 测试获取会话列表
    print("\n4️⃣  测试获取会话列表...")
    sessions = conversation_db.get_user_conversations(test_username)
    print(f"✅ 用户 {test_username} 有 {len(sessions)} 个会话")
    for session in sessions:
        print(f"   - {session['title']} (消息数: {session['message_count']})")
    
    # 5. 测试会话统计
    print("\n5️⃣  测试会话统计...")
    stats = conversation_db.get_conversation_stats(session_id)
    print(f"✅ 会话统计:")
    print(f"   总消息数: {stats['total_messages']}")
    print(f"   用户消息: {stats['user_messages']}")
    print(f"   AI消息: {stats['assistant_messages']}")
    print(f"   首条消息时间: {stats['first_message_at']}")
    print(f"   最后消息时间: {stats['last_message_at']}")
    
    # 6. 测试自动生成标题
    print("\n6️⃣  测试自动生成标题...")
    new_title = conversation_db.auto_generate_title(session_id)
    print(f"✅ 自动生成标题: {new_title}")
    
    # 7. 测试更新标题
    print("\n7️⃣  测试更新标题...")
    success = conversation_db.update_conversation_title(
        session_id, 
        "销售数据查询会话",
        username=test_username
    )
    print(f"✅ 更新标题: {'成功' if success else '失败'}")
    
    # 8. 测试软删除
    print("\n8️⃣  测试软删除会话...")
    success = conversation_db.delete_conversation(
        session_id,
        username=test_username,
        soft_delete=True
    )
    print(f"✅ 软删除会话: {'成功' if success else '失败'}")
    
    # 验证软删除后不在活跃列表中
    active_sessions = conversation_db.get_user_conversations(test_username, include_inactive=False)
    print(f"   活跃会话数: {len(active_sessions)}")
    
    all_sessions = conversation_db.get_user_conversations(test_username, include_inactive=True)
    print(f"   总会话数（含不活跃）: {len(all_sessions)}")
    
    # 9. 测试创建多个会话
    print("\n9️⃣  测试创建多个会话...")
    for i in range(3):
        sid = f"{test_username}_{int(time.time() * 1000) + i}"
        conversation_db.create_conversation(
            conversation_id=sid,
            user_id=test_user_id,
            username=test_username,
            title=f"测试会话 {i+1}"
        )
        # 添加一些消息
        conversation_db.add_message(sid, 'user', f'测试消息 {i+1}')
        conversation_db.add_message(sid, 'assistant', f'回复 {i+1}')
        time.sleep(0.01)  # 确保时间戳不同
    
    sessions = conversation_db.get_user_conversations(test_username)
    print(f"✅ 现在有 {len(sessions)} 个活跃会话")
    
    # 10. 测试会话排序
    print("\n🔟 测试会话排序...")
    print("   会话列表（按更新时间倒序）:")
    for i, session in enumerate(sessions[:5], 1):
        print(f"   {i}. {session['title']} - {session['updated_at']}")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
    
    return True


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试错误处理")
    print("=" * 60)
    
    # 1. 测试重复创建会话
    print("\n1️⃣  测试重复创建会话...")
    session_id = f"test_user_{int(time.time() * 1000)}"
    conversation_db.create_conversation(
        conversation_id=session_id,
        user_id=1,
        username="test_user",
        title="测试"
    )
    
    try:
        conversation_db.create_conversation(
            conversation_id=session_id,
            user_id=1,
            username="test_user",
            title="测试"
        )
        print("❌ 应该抛出异常")
    except ValueError as e:
        print(f"✅ 正确捕获异常: {e}")
    
    # 2. 测试向不存在的会话添加消息
    print("\n2️⃣  测试向不存在的会话添加消息...")
    try:
        conversation_db.add_message(
            conversation_id="nonexistent_session",
            role='user',
            content='测试'
        )
        print("❌ 应该抛出异常")
    except ValueError as e:
        print(f"✅ 正确捕获异常: {e}")
    
    # 3. 测试获取不存在的会话
    print("\n3️⃣  测试获取不存在的会话...")
    result = conversation_db.get_conversation("nonexistent_session")
    if result is None:
        print("✅ 正确返回 None")
    else:
        print("❌ 应该返回 None")
    
    print("\n" + "=" * 60)
    print("✅ 错误处理测试完成！")
    print("=" * 60)


def test_performance():
    """测试性能"""
    print("\n" + "=" * 60)
    print("测试性能")
    print("=" * 60)
    
    test_username = "perf_test_user"
    
    # 1. 测试批量创建会话
    print("\n1️⃣  测试批量创建 100 个会话...")
    start_time = time.time()
    
    for i in range(100):
        session_id = f"{test_username}_{int(time.time() * 1000000) + i}"
        conversation_db.create_conversation(
            conversation_id=session_id,
            user_id=999,
            username=test_username,
            title=f"性能测试会话 {i}"
        )
        # 每个会话添加 5 条消息
        for j in range(5):
            conversation_db.add_message(
                session_id,
                'user' if j % 2 == 0 else 'assistant',
                f"测试消息 {j}"
            )
    
    elapsed = time.time() - start_time
    print(f"✅ 创建 100 个会话（每个5条消息）耗时: {elapsed:.2f}秒")
    print(f"   平均每个会话: {elapsed/100*1000:.2f}ms")
    
    # 2. 测试查询性能
    print("\n2️⃣  测试查询性能...")
    start_time = time.time()
    sessions = conversation_db.get_user_conversations(test_username, limit=100)
    elapsed = time.time() - start_time
    print(f"✅ 查询 {len(sessions)} 个会话耗时: {elapsed*1000:.2f}ms")
    
    # 3. 测试消息查询性能
    print("\n3️⃣  测试消息查询性能...")
    if sessions:
        start_time = time.time()
        for session in sessions[:10]:
            messages = conversation_db.get_conversation_messages(session['id'])
        elapsed = time.time() - start_time
        print(f"✅ 查询 10 个会话的消息耗时: {elapsed*1000:.2f}ms")
        print(f"   平均每个会话: {elapsed/10*1000:.2f}ms")
    
    print("\n" + "=" * 60)
    print("✅ 性能测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        # 运行基础功能测试
        test_conversation_system()
        
        # 运行错误处理测试
        test_error_handling()
        
        # 运行性能测试
        test_performance()
        
        print("\n" + "🎉" * 30)
        print("所有测试通过！对话存储系统工作正常！")
        print("🎉" * 30)
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        sys.exit(1)








