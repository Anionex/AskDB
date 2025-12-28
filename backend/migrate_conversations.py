#!/usr/bin/env python3
"""
对话数据迁移脚本
将旧的 Agno runs 表数据迁移到新的 conversations 系统
"""

import sqlite3
from pathlib import Path
import logging
from typing import Dict, List
import re
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库路径
OLD_DB_PATH = Path(__file__).parent.parent / "data" / "askdb_sessions.db"
NEW_DB_PATH = Path(__file__).parent.parent / "data" / "conversations.db"
USERS_DB_PATH = Path(__file__).parent.parent / "data" / "users.db"


def get_user_id_by_username(username: str) -> int:
    """从users.db获取用户ID"""
    if not USERS_DB_PATH.exists():
        logger.warning(f"用户数据库不存在: {USERS_DB_PATH}")
        return 999  # 默认ID
    
    conn = sqlite3.connect(USERS_DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return row[0]
        else:
            logger.warning(f"用户不存在: {username}，使用默认ID")
            return 999
    finally:
        conn.close()


def extract_username_from_session_id(session_id: str) -> str:
    """从session_id中提取用户名"""
    # session_id 格式: username_timestamp 或 username_session_timestamp
    parts = session_id.split('_')
    if len(parts) >= 2:
        # 第一部分通常是用户名
        return parts[0]
    return "unknown"


def migrate_conversations():
    """迁移对话数据"""
    
    if not OLD_DB_PATH.exists():
        logger.info(f"旧数据库不存在，无需迁移: {OLD_DB_PATH}")
        return
    
    logger.info("=" * 60)
    logger.info("开始迁移对话数据...")
    logger.info("=" * 60)
    
    # 连接旧数据库
    old_conn = sqlite3.connect(OLD_DB_PATH)
    old_conn.row_factory = sqlite3.Row
    old_cursor = old_conn.cursor()
    
    # 检查agno_sessions表是否存在
    old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agno_sessions'")
    if not old_cursor.fetchone():
        logger.info("旧数据库中没有agno_sessions表，无需迁移")
        old_conn.close()
        return
    
    # 连接新数据库
    new_conn = sqlite3.connect(NEW_DB_PATH)
    new_conn.row_factory = sqlite3.Row
    new_cursor = new_conn.cursor()
    
    try:
        # 1. 获取所有session
        old_cursor.execute("""
            SELECT session_id, runs, created_at, updated_at
            FROM agno_sessions
            WHERE runs IS NOT NULL AND runs != '[]' AND runs != 'null'
            ORDER BY created_at ASC
        """)
        
        sessions = old_cursor.fetchall()
        logger.info(f"发现 {len(sessions)} 个会话需要迁移")
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for session_row in sessions:
            session_id = session_row['session_id']
            runs_json = session_row['runs']
            created_at_ts = session_row['created_at']
            updated_at_ts = session_row['updated_at']
            
            try:
                # 检查是否已经迁移
                new_cursor.execute("SELECT id FROM conversations WHERE id = ?", (session_id,))
                if new_cursor.fetchone():
                    logger.debug(f"会话已存在，跳过: {session_id}")
                    skipped_count += 1
                    continue
                
                # 解析runs JSON（需要double parse）
                try:
                    runs_data = json.loads(json.loads(runs_json))
                except:
                    # 尝试单次parse
                    runs_data = json.loads(runs_json)
                
                if not isinstance(runs_data, list) or len(runs_data) == 0:
                    logger.debug(f"会话无有效runs数据，跳过: {session_id}")
                    skipped_count += 1
                    continue
                
                # 提取用户名
                username = extract_username_from_session_id(session_id)
                user_id = get_user_id_by_username(username)
                
                # 从runs中提取消息
                all_messages = []
                for run in runs_data:
                    if 'messages' in run and isinstance(run['messages'], list):
                        for msg in run['messages']:
                            if isinstance(msg, dict):
                                role = msg.get('role', '')
                                content = msg.get('content', '')
                                
                                # 跳过系统消息和空消息
                                if role in ['user', 'assistant'] and content:
                                    all_messages.append({
                                        'role': role,
                                        'content': content,
                                        'timestamp': run.get('created_at', created_at_ts)
                                    })
                
                if not all_messages:
                    logger.debug(f"会话无有效消息，跳过: {session_id}")
                    skipped_count += 1
                    continue
                
                # 生成标题（从第一条用户消息）
                title = '对话'
                for msg in all_messages:
                    if msg['role'] == 'user':
                        title = msg['content'][:30]
                        if len(msg['content']) > 30:
                            title += '...'
                        break
                
                # 转换时间戳为datetime字符串
                created_at = datetime.fromtimestamp(created_at_ts).strftime('%Y-%m-%d %H:%M:%S')
                updated_at = datetime.fromtimestamp(updated_at_ts).strftime('%Y-%m-%d %H:%M:%S')
                
                # 创建会话
                new_cursor.execute("""
                    INSERT INTO conversations 
                    (id, user_id, username, title, created_at, updated_at, message_count, is_active, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, 0, 1, '{}')
                """, (session_id, user_id, username, title, created_at, updated_at))
                
                # 迁移消息
                message_count = 0
                for msg in all_messages:
                    msg_time = datetime.fromtimestamp(msg['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    new_cursor.execute("""
                        INSERT INTO messages 
                        (conversation_id, role, content, created_at, metadata)
                        VALUES (?, ?, ?, ?, '{}')
                    """, (session_id, msg['role'], msg['content'], msg_time))
                    message_count += 1
                
                # 更新消息计数
                new_cursor.execute("""
                    UPDATE conversations 
                    SET message_count = ?
                    WHERE id = ?
                """, (message_count, session_id))
                
                logger.info(f"✅ 迁移会话: {session_id} ({message_count} 条消息)")
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"❌ 迁移会话失败 {session_id}: {e}")
                error_count += 1
                continue
        
        # 提交事务
        new_conn.commit()
        
        logger.info("=" * 60)
        logger.info(f"迁移完成！")
        logger.info(f"  ✅ 成功迁移: {migrated_count} 个会话")
        logger.info(f"  ⏭️  跳过已存在: {skipped_count} 个会话")
        logger.info(f"  ❌ 迁移失败: {error_count} 个会话")
        logger.info("=" * 60)
        
        # 显示迁移后的统计
        new_cursor.execute("SELECT COUNT(*) as count FROM conversations")
        total_conversations = new_cursor.fetchone()['count']
        
        new_cursor.execute("SELECT COUNT(*) as count FROM messages")
        total_messages = new_cursor.fetchone()['count']
        
        logger.info(f"新数据库统计:")
        logger.info(f"  总会话数: {total_conversations}")
        logger.info(f"  总消息数: {total_messages}")
        
    except Exception as e:
        logger.error(f"迁移过程出错: {e}", exc_info=True)
        new_conn.rollback()
        raise
    finally:
        old_conn.close()
        new_conn.close()


def verify_migration():
    """验证迁移结果"""
    logger.info("\n" + "=" * 60)
    logger.info("验证迁移结果...")
    logger.info("=" * 60)
    
    if not NEW_DB_PATH.exists():
        logger.error("新数据库不存在！")
        return False
    
    conn = sqlite3.connect(NEW_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 检查会话
        cursor.execute("SELECT COUNT(*) as count FROM conversations")
        conv_count = cursor.fetchone()['count']
        
        # 检查消息
        cursor.execute("SELECT COUNT(*) as count FROM messages")
        msg_count = cursor.fetchone()['count']
        
        # 按用户统计
        cursor.execute("""
            SELECT username, COUNT(*) as conv_count, SUM(message_count) as msg_count
            FROM conversations
            GROUP BY username
            ORDER BY conv_count DESC
        """)
        
        user_stats = cursor.fetchall()
        
        logger.info(f"✅ 总会话数: {conv_count}")
        logger.info(f"✅ 总消息数: {msg_count}")
        logger.info(f"\n用户统计:")
        for stat in user_stats:
            logger.info(f"  - {stat['username']}: {stat['conv_count']} 个会话, {stat['msg_count']} 条消息")
        
        return True
        
    finally:
        conn.close()


def backup_old_database():
    """备份旧数据库"""
    if not OLD_DB_PATH.exists():
        return
    
    import shutil
    from datetime import datetime
    
    backup_path = OLD_DB_PATH.parent / f"askdb_sessions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(OLD_DB_PATH, backup_path)
    logger.info(f"✅ 旧数据库已备份到: {backup_path}")


if __name__ == "__main__":
    try:
        # 1. 备份旧数据库
        logger.info("步骤 1: 备份旧数据库...")
        backup_old_database()
        
        # 2. 执行迁移
        logger.info("\n步骤 2: 执行数据迁移...")
        migrate_conversations()
        
        # 3. 验证迁移结果
        logger.info("\n步骤 3: 验证迁移结果...")
        verify_migration()
        
        logger.info("\n" + "🎉" * 30)
        logger.info("数据迁移成功完成！")
        logger.info("🎉" * 30)
        
    except Exception as e:
        logger.error(f"数据迁移失败: {e}", exc_info=True)
        exit(1)

