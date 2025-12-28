"""
会话和消息数据库管理模块
专门用于管理用户的AI对话会话和消息历史
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "conversations.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class ConversationDB:
    """会话数据库管理类"""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 创建会话表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                metadata TEXT DEFAULT '{}'
            )
        ''')
        
        # 创建消息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'error')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversations_user 
            ON conversations(username, is_active, updated_at DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id, created_at ASC)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ 会话数据库初始化完成")
    
    def create_conversation(
        self, 
        conversation_id: str,
        user_id: int,
        username: str, 
        title: str = "新对话",
        metadata: Dict = None
    ) -> Dict:
        """创建新会话"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO conversations (id, user_id, username, title, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                conversation_id,
                user_id,
                username,
                title,
                json.dumps(metadata or {})
            ))
            
            conn.commit()
            
            # 获取创建的会话
            cursor.execute('SELECT * FROM conversations WHERE id = ?', (conversation_id,))
            conversation = dict(cursor.fetchone())
            
            logger.info(f"✅ 创建会话: {conversation_id} by {username}")
            return conversation
            
        except sqlite3.IntegrityError as e:
            logger.error(f"会话ID已存在: {conversation_id}")
            raise ValueError(f"会话ID已存在: {conversation_id}")
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            raise
        finally:
            conn.close()
    
    def get_user_conversations(
        self, 
        username: str, 
        limit: int = 50,
        include_inactive: bool = False
    ) -> List[Dict]:
        """获取用户的所有会话列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if include_inactive:
                cursor.execute('''
                    SELECT * FROM conversations 
                    WHERE username = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                ''', (username, limit))
            else:
                cursor.execute('''
                    SELECT * FROM conversations 
                    WHERE username = ? AND is_active = 1
                    ORDER BY updated_at DESC
                    LIMIT ?
                ''', (username, limit))
            
            conversations = [dict(row) for row in cursor.fetchall()]
            
            # 解析metadata
            for conv in conversations:
                conv['metadata'] = json.loads(conv.get('metadata', '{}'))
            
            return conversations
            
        finally:
            conn.close()
    
    def get_conversation(self, conversation_id: str, username: str = None) -> Optional[Dict]:
        """获取单个会话信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if username:
                # 验证会话属于该用户
                cursor.execute('''
                    SELECT * FROM conversations 
                    WHERE id = ? AND username = ?
                ''', (conversation_id, username))
            else:
                cursor.execute('SELECT * FROM conversations WHERE id = ?', (conversation_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            conversation = dict(row)
            conversation['metadata'] = json.loads(conversation.get('metadata', '{}'))
            return conversation
            
        finally:
            conn.close()
    
    def update_conversation_title(
        self, 
        conversation_id: str, 
        title: str,
        username: str = None
    ) -> bool:
        """更新会话标题"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if username:
                cursor.execute('''
                    UPDATE conversations 
                    SET title = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND username = ?
                ''', (title, conversation_id, username))
            else:
                cursor.execute('''
                    UPDATE conversations 
                    SET title = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (title, conversation_id))
            
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                logger.info(f"更新会话标题: {conversation_id} -> {title}")
            
            return success
            
        finally:
            conn.close()
    
    def delete_conversation(
        self, 
        conversation_id: str, 
        username: str = None,
        soft_delete: bool = True
    ) -> bool:
        """删除会话（软删除或硬删除）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if soft_delete:
                # 软删除：只标记为不活跃
                if username:
                    cursor.execute('''
                        UPDATE conversations 
                        SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND username = ?
                    ''', (conversation_id, username))
                else:
                    cursor.execute('''
                        UPDATE conversations 
                        SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (conversation_id,))
            else:
                # 硬删除：彻底删除（会级联删除消息）
                if username:
                    cursor.execute('''
                        DELETE FROM conversations 
                        WHERE id = ? AND username = ?
                    ''', (conversation_id, username))
                else:
                    cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
            
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                logger.info(f"删除会话: {conversation_id} (soft={soft_delete})")
            
            return success
            
        finally:
            conn.close()
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Dict = None
    ) -> Dict:
        """添加消息到会话"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 插入消息
            cursor.execute('''
                INSERT INTO messages (conversation_id, role, content, metadata)
                VALUES (?, ?, ?, ?)
            ''', (
                conversation_id,
                role,
                content,
                json.dumps(metadata or {})
            ))
            
            message_id = cursor.lastrowid
            
            # 更新会话的消息计数和更新时间
            cursor.execute('''
                UPDATE conversations 
                SET message_count = message_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (conversation_id,))
            
            conn.commit()
            
            # 获取插入的消息
            cursor.execute('SELECT * FROM messages WHERE id = ?', (message_id,))
            message = dict(cursor.fetchone())
            message['metadata'] = json.loads(message.get('metadata', '{}'))
            
            return message
            
        except sqlite3.IntegrityError as e:
            logger.error(f"会话不存在: {conversation_id}")
            raise ValueError(f"会话不存在: {conversation_id}")
        except Exception as e:
            logger.error(f"添加消息失败: {e}")
            raise
        finally:
            conn.close()
    
    def get_conversation_messages(
        self,
        conversation_id: str,
        username: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """获取会话的消息历史"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 验证会话存在且属于该用户
            if username:
                cursor.execute('''
                    SELECT id FROM conversations 
                    WHERE id = ? AND username = ?
                ''', (conversation_id, username))
                if not cursor.fetchone():
                    return []
            
            # 获取消息
            cursor.execute('''
                SELECT * FROM messages 
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                LIMIT ? OFFSET ?
            ''', (conversation_id, limit, offset))
            
            messages = [dict(row) for row in cursor.fetchall()]
            
            # 解析metadata
            for msg in messages:
                msg['metadata'] = json.loads(msg.get('metadata', '{}'))
            
            return messages
            
        finally:
            conn.close()
    
    def get_conversation_stats(self, conversation_id: str) -> Dict:
        """获取会话统计信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_messages,
                    COALESCE(SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END), 0) as user_messages,
                    COALESCE(SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END), 0) as assistant_messages,
                    MIN(created_at) as first_message_at,
                    MAX(created_at) as last_message_at
                FROM messages
                WHERE conversation_id = ?
            ''', (conversation_id,))
            
            stats = dict(cursor.fetchone())
            # 确保数值字段不为 None
            stats['user_messages'] = stats.get('user_messages') or 0
            stats['assistant_messages'] = stats.get('assistant_messages') or 0
            stats['total_messages'] = stats.get('total_messages') or 0
            return stats
            
        finally:
            conn.close()
    
    def auto_generate_title(self, conversation_id: str) -> Optional[str]:
        """自动从第一条用户消息生成标题"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT content FROM messages 
                WHERE conversation_id = ? AND role = 'user'
                ORDER BY created_at ASC
                LIMIT 1
            ''', (conversation_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            content = row['content']
            # 截取前30个字符作为标题
            title = content[:30] + ('...' if len(content) > 30 else '')
            
            # 更新标题
            self.update_conversation_title(conversation_id, title)
            
            return title
            
        finally:
            conn.close()
    
    def cleanup_old_conversations(self, days: int = 30) -> int:
        """清理旧的不活跃会话"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                DELETE FROM conversations
                WHERE is_active = 0 
                AND updated_at < datetime('now', '-' || ? || ' days')
            ''', (days,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 个旧会话")
            
            return deleted_count
            
        finally:
            conn.close()


# 全局实例
conversation_db = ConversationDB()








