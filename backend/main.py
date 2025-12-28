#!/usr/bin/env python3
"""
AskDB Backend API Service
"""

import os
import sys
from pathlib import Path
import secrets
import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import hashlib
import re
import jwt

# 修复导入路径
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, validator
import uvicorn
import json
import asyncio
from typing import AsyncGenerator


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from askdb_agno import create_agent
    from tools.agno_tools import db 
    from tools.vector_store import vector_store
    from backend.conversation_db import conversation_db
    HAS_AGENT = True
except ImportError as e:
    HAS_AGENT = False
    logger.error(f"❌ 无法导入AskDB模块: {e}")
    conversation_db = None

# 索引状态存储
indexing_status = {
    "is_indexing": False,
    "progress": 0,
    "total": 0,
    "current_step": "", 
    "completed": False,
    "error": None
}

# 安全配置
security = HTTPBearer(auto_error=False)

# JWT配置
# 使用固定的密钥，确保后端重启后token仍然有效
# 生产环境请通过环境变量 JWT_SECRET_KEY 设置自己的密钥
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "askdb-jwt-secret-key-please-change-in-production-environment-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 30  # JWT令牌有效期30天

# 数据库配置
DB_PATH = Path(__file__).parent.parent / "data" / "users.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 邮箱配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 587,
    "sender_email": "3524109744@qq.com",
    "sender_password": "utmygpocxzyfcjch",
    "company_name": "AskDB"
}

# 验证码存储（仍然使用内存存储，因为验证码是短期的）
verification_codes: Dict[str, Dict] = {}

app = FastAPI(
    title="AskDB API",
    description="智能数据库助手API",
    version="2.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class SendCodeRequest(BaseModel):
    email: EmailStr

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    user_type: str
    verification_code: str

    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 20:
            raise ValueError('用户名长度必须在3-20字符之间')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v

    @validator('user_type')
    def validate_user_type(cls, v):
        if v not in ['manager', 'user']:
            raise ValueError('用户类型必须是manager或user')
        return v

class LoginRequest(BaseModel):
    username: str
    password: str

class VerifyRequest(BaseModel):
    token: str

class ChatRequest(BaseModel):
    message: str
    session_id: str = "web-session"

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    user_type: str
    created_at: str
    is_active: bool

class LoginResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[Dict] = None

class RegisterResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None

class CodeResponse(BaseModel):
    success: bool
    message: str

class VerifyResponse(BaseModel):
    success: bool
    valid: bool
    user: Optional[Dict] = None

class ChatResponse(BaseModel):
    success: bool
    response: str
    session_id: str

class SessionInfo(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0
    is_active: bool = True

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "新对话"

class UpdateSessionTitleRequest(BaseModel):
    title: str

class SessionListResponse(BaseModel):
    success: bool
    sessions: list[SessionInfo]

class SessionHistoryResponse(BaseModel):
    success: bool
    messages: list[dict]
    session_id: str

class DatabaseStatusResponse(BaseModel):
    connected: bool
    database_type: Optional[str] = None
    table_count: Optional[int] = None
    tables: Optional[List[str]] = None
    error: Optional[str] = None

class IndexStatusResponse(BaseModel):
    is_indexing: bool
    progress: int
    total: int
    current_step: str
    completed: bool
    error: Optional[str] = None
    index_stats: Optional[Dict[str, int]] = None

class IndexTriggerResponse(BaseModel):
    success: bool
    message: str

class VectorSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    search_types: Optional[List[str]] = None  # ["table", "column", "business_term"]

class SearchResultItem(BaseModel):
    name: str
    type: str  # table, column, business_term
    similarity: float
    metadata: Dict[str, Any]

class VectorSearchResponse(BaseModel):
    success: bool
    query: str
    results: List[SearchResultItem]
    total: int
    message: Optional[str] = None

class ConfirmActionRequest(BaseModel):
    session_id: str
    sql: str
    explanation: str
    action: str  # "approve" or "reject"

# 数据库初始化
def init_database():
    """初始化用户数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            user_type VARCHAR(10) NOT NULL CHECK (user_type IN ('manager', 'user')),
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # 创建默认管理员账户（如果不存在）
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        password_hash = hash_password('admin123')
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, user_type) 
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin@askdb.com', password_hash, 'manager'))
        logger.info("创建默认管理员账户: admin/admin123")
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return hash_password(plain_password) == hashed_password

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 邮箱功能
def send_verification_code(email: str, code: str):
    """发送验证码邮件"""
    try:
        subject = f"{EMAIL_CONFIG['company_name']} - 邮箱验证码"
        body = f'''
        您好！
        
        您的验证码是：{code}
        
        此验证码用于注册 {EMAIL_CONFIG['company_name']} 账户，有效期为10分钟。
        
        如果不是您本人操作，请忽略此邮件。
        
        {EMAIL_CONFIG['company_name']} 团队
        '''
        
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = email
        
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.send_message(msg)
        server.quit()
        
        logger.info(f"验证码发送成功: {email}")
        return True
    except Exception as e:
        logger.error(f"发送验证码失败: {e}")
        return False

def generate_verification_code() -> str:
    """生成6位数字验证码"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

# JWT令牌管理
def create_access_token(username: str, user_id: int) -> str:
    """创建JWT访问令牌"""
    expires = datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
    
    payload = {
        "sub": username,  # subject: 用户名
        "user_id": user_id,
        "exp": expires,  # expiration: 过期时间
        "iat": datetime.utcnow()  # issued at: 签发时间
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token

def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict:
    """验证JWT令牌"""
    if not credentials:
        logger.error("缺少Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌，请先登录"
        )
    
    token = credentials.credentials
    
    try:
        # 解码JWT token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌"
            )
        
        logger.info(f"验证JWT token成功: {username}")
        
    except jwt.ExpiredSignatureError:
        logger.warning(f"JWT token已过期")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期，请重新登录"
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"无效的JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )
    
    # 从数据库验证用户是否存在且处于活跃状态
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE username = ?', 
        (username,)
    ).fetchone()
    conn.close()
    
    if not user or not user["is_active"]:
        logger.warning(f"用户不存在或已禁用: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )
    
    logger.info(f"用户验证成功: {username}")
    return dict(user)

# AskDB AI 功能
def get_database_status():
    """获取数据库状态"""
    try:
        if not HAS_AGENT:
            return {
                "connected": False,
                "error": "AskDB Agent模块未加载"
            }
        
        # 连接数据库
        db.connect()
        tables = db.get_tables()
        
        return {
            "connected": True,
            "database_type": os.getenv("DEFAULT_DB_TYPE", "openGauss"),
            "table_count": len(tables),
            "tables": tables[:20]  # 只返回前20个表
        }
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return {
            "connected": False,
            "error": str(e)
        }

def process_chat_message(message: str, session_id: str = "web-session", user_context: dict = None):
    """处理聊天消息"""
    try:
        if not HAS_AGENT:
            return {
                "success": False,
                "response": "AskDB Agent模块未加载，无法处理查询"
            }
        
        # 保存用户消息到数据库
        if conversation_db and user_context:
            try:
                conversation_db.add_message(
                    conversation_id=session_id,
                    role='user',
                    content=message
                )
            except ValueError:
                # 会话不存在，先创建会话
                logger.warning(f"会话不存在，自动创建: {session_id}")
                conversation_db.create_conversation(
                    conversation_id=session_id,
                    user_id=user_context.get('id'),
                    username=user_context.get('username'),
                    title='新对话'
                )
                conversation_db.add_message(
                    conversation_id=session_id,
                    role='user',
                    content=message
                )
        
        # 使用 AgentManager 获取或创建 agent
        from backend.agents import agent_manager
        agent = agent_manager.get_agent(session_id, use_memory=True)
        
        # 处理消息
        response = agent.run(message)
        ai_response = response.content
        
        # 提取工具调用信息
        tool_calls = []
        if hasattr(response, 'messages') and response.messages:
            for msg in response.messages:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for call in msg.tool_calls:
                        if hasattr(call, 'function'):
                            func = call.function
                            # 解析参数（可能是字符串或字典）
                            args = func.arguments
                            if isinstance(args, str):
                                try:
                                    args = json.loads(args)
                                except:
                                    pass
                            
                            tool_calls.append({
                                'name': func.name,
                                'arguments': args
                            })
        
        # 保存AI响应到数据库（包含工具调用信息）
        if conversation_db:
            metadata = {}
            if tool_calls:
                metadata['tool_calls'] = tool_calls
            
            conversation_db.add_message(
                conversation_id=session_id,
                role='assistant',
                content=ai_response,
                metadata=metadata if metadata else None
            )
            
            # 如果是第一条消息，自动生成标题
            stats = conversation_db.get_conversation_stats(session_id)
            if stats['user_messages'] == 1:
                conversation_db.auto_generate_title(session_id)
        
        return {
            "success": True,
            "response": ai_response,
            "tool_calls": tool_calls
        }
        
    except Exception as e:
        logger.error(f"AI处理失败: {e}")
        error_msg = f"处理查询时出错: {str(e)}"
        
        # 保存错误消息
        if conversation_db:
            try:
                conversation_db.add_message(
                    conversation_id=session_id,
                    role='error',
                    content=error_msg
                )
            except:
                pass
        
        # 检查是否是web搜索相关的错误
        if "event loop" in str(e).lower() or "coroutine" in str(e).lower():
            error_msg = f"Web搜索功能暂时不可用: {str(e)}"
        
        return {
            "success": False,
            "response": error_msg
        }

async def process_chat_message_stream(message: str, session_id: str, user_context: dict = None) -> AsyncGenerator[str, None]:
    """流式处理聊天消息"""
    try:
        if not HAS_AGENT:
            yield f"data: {json.dumps({'type': 'error', 'content': 'AskDB Agent模块未加载'})}\n\n"
            return
        
        from backend.agents import agent_manager
        agent = agent_manager.get_agent(session_id, use_memory=True)
        
        # 使用 Agno 的流式输出
        try:
            # Agno 支持 stream=True 参数
            if hasattr(agent, 'run_stream'):
                for chunk in agent.run_stream(message):
                    if hasattr(chunk, 'content'):
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk.content})}\n\n"
                    elif isinstance(chunk, str):
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            elif hasattr(agent, 'run') and hasattr(agent.run(message), '__iter__'):
                # 尝试迭代响应
                response = agent.run(message)
                if hasattr(response, 'content'):
                    # 模拟流式输出，逐字符发送
                    content = response.content
                    chunk_size = 10
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i+chunk_size]
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                        await asyncio.sleep(0.05)  # 模拟流式延迟
                else:
                    yield f"data: {json.dumps({'type': 'content', 'content': str(response)})}\n\n"
            else:
                # 回退到普通模式
                response = agent.run(message)
                yield f"data: {json.dumps({'type': 'content', 'content': response.content if hasattr(response, 'content') else str(response)})}\n\n"
        except Exception as e:
            logger.error(f"流式处理异常: {e}")
            # 回退到普通模式
            response = agent.run(message)
            yield f"data: {json.dumps({'type': 'content', 'content': response.content if hasattr(response, 'content') else str(response)})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
    except Exception as e:
        logger.error(f"流式处理失败: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

def get_user_sessions(username: str) -> list[SessionInfo]:
    """获取用户的所有会话"""
    try:
        if not conversation_db:
            return []
        
        conversations = conversation_db.get_user_conversations(username, limit=100)
        
        sessions = []
        for conv in conversations:
            sessions.append(SessionInfo(
                id=conv['id'],
                title=conv['title'],
                created_at=conv['created_at'],
                updated_at=conv['updated_at'],
                message_count=conv['message_count'],
                is_active=bool(conv['is_active'])
            ))
        
        return sessions
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        return []

def fetch_session_history(session_id: str, username: str) -> list[dict]:
    """获取会话历史消息（内部辅助函数）"""
    try:
        if not conversation_db:
            return []
        
        messages = conversation_db.get_conversation_messages(
            session_id, 
            username=username,
            limit=200
        )
        
        # 转换为前端需要的格式
        result = []
        for msg in messages:
            message_data = {
                'id': msg['id'],
                'type': msg['role'],  # user, assistant, system, error
                'content': msg['content'],
                'timestamp': msg['created_at'],
                'metadata': msg.get('metadata', {})
            }
            
            # 提取工具调用信息（如果有）
            metadata = msg.get('metadata', {})
            if isinstance(metadata, dict) and 'tool_calls' in metadata:
                message_data['toolCalls'] = metadata['tool_calls']
            
            result.append(message_data)
        
        return result
    except Exception as e:
        logger.error(f"获取会话历史失败: {e}")
        return []

# 路由
@app.on_event("startup")
async def startup_event():
    """启动时初始化数据库"""
    init_database()
    
    # 检查AI模块
    if HAS_AGENT:
        logger.info("✅ AskDB AI模块已加载")
    else:
        logger.warning("⚠️ AskDB AI模块未加载，将使用模拟响应")

@app.get("/")
async def root():
    return {"message": "AskDB API Server", "status": "running", "version": "2.0.0"}

@app.get("/api/public/health")
async def public_health():
    """公开健康检查"""
    return {
        "status": "healthy", 
        "service": "AskDB API",
        "version": "2.0.0",
        "has_agent": HAS_AGENT
    }

@app.post("/api/auth/send-code", response_model=CodeResponse)
async def send_verification_code_endpoint(request: SendCodeRequest, background_tasks: BackgroundTasks):
    """发送验证码"""
    # 检查邮箱是否已注册
    conn = get_db_connection()
    existing_user = conn.execute(
        'SELECT * FROM users WHERE email = ?', (request.email,)
    ).fetchone()
    conn.close()
    
    if existing_user:
        return CodeResponse(success=False, message="该邮箱已被注册")
    
    # 生成验证码
    code = generate_verification_code()
    expires = datetime.now() + timedelta(minutes=10)
    
    # 存储验证码
    verification_codes[request.email] = {
        "code": code,
        "expires": expires,
        "attempts": 0
    }
    
    # 后台发送邮件
    background_tasks.add_task(send_verification_code, request.email, code)
    
    return CodeResponse(
        success=True, 
        message=f"验证码已发送到 {request.email}，有效期为10分钟"
    )

@app.post("/api/auth/verify-code", response_model=CodeResponse)
async def verify_code_endpoint(request: VerifyCodeRequest):
    """验证验证码"""
    if request.email not in verification_codes:
        return CodeResponse(success=False, message="验证码已过期或未发送")
    
    code_data = verification_codes[request.email]
    
    if datetime.now() > code_data["expires"]:
        del verification_codes[request.email]
        return CodeResponse(success=False, message="验证码已过期")
    
    if code_data["attempts"] >= 3:
        del verification_codes[request.email]
        return CodeResponse(success=False, message="验证失败次数过多，请重新获取验证码")
    
    if code_data["code"] != request.code:
        code_data["attempts"] += 1
        return CodeResponse(success=False, message="验证码错误")
    
    # 验证成功，删除验证码
    del verification_codes[request.email]
    return CodeResponse(success=True, message="验证码正确")

@app.post("/api/auth/register", response_model=RegisterResponse)
async def register_user(request: RegisterRequest):
    """用户注册"""
    # 检查验证码
    if request.email not in verification_codes:
        return RegisterResponse(success=False, message="请先获取验证码")
    
    code_data = verification_codes[request.email]
    
    if datetime.now() > code_data["expires"]:
        del verification_codes[request.email]
        return RegisterResponse(success=False, message="验证码已过期")
    
    if code_data["attempts"] >= 3:
        del verification_codes[request.email]
        return RegisterResponse(success=False, message="验证失败次数过多，请重新获取验证码")
    
    if code_data["code"] != request.verification_code:
        code_data["attempts"] += 1
        return RegisterResponse(success=False, message="验证码错误")
    
    # 检查用户名是否已存在
    conn = get_db_connection()
    existing_user = conn.execute(
        'SELECT * FROM users WHERE username = ? OR email = ?', 
        (request.username, request.email)
    ).fetchone()
    
    if existing_user:
        conn.close()
        if existing_user["username"] == request.username:
            return RegisterResponse(success=False, message="用户名已存在")
        else:
            return RegisterResponse(success=False, message="邮箱已被注册")
    
    # 创建用户
    password_hash = hash_password(request.password)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, user_type) 
            VALUES (?, ?, ?, ?)
        ''', (request.username, request.email, password_hash, request.user_type))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        logger.info(f"新用户注册: {request.username} ({request.user_type})")
        
        # 验证成功后删除验证码
        del verification_codes[request.email]
        
        return RegisterResponse(
            success=True,
            message="注册成功",
            user_id=user_id
        )
        
    except Exception as e:
        conn.rollback()
        logger.error(f"注册失败: {e}")
        return RegisterResponse(success=False, message="注册失败")
    finally:
        conn.close()

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """用户登录"""
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE username = ?', (login_data.username,)
    ).fetchone()
    conn.close()
    
    if not user:
        return LoginResponse(success=False, message="用户名或密码错误")
    
    if not user["is_active"]:
        return LoginResponse(success=False, message="账户已被禁用")
    
    if not verify_password(login_data.password, user["password_hash"]):
        return LoginResponse(success=False, message="用户名或密码错误")
    
    # 更新最后登录时间
    conn = get_db_connection()
    conn.execute(
        'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
        (user["id"],)
    )
    conn.commit()
    conn.close()
    
    # 创建JWT令牌
    token = create_access_token(user["username"], user["id"])
    
    return LoginResponse(
        success=True,
        message="登录成功",
        token=token,
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "user_type": user["user_type"],
            "created_at": user["created_at"]
        }
    )

@app.post("/api/auth/verify", response_model=VerifyResponse)
async def verify_token_endpoint(request: VerifyRequest):
    """验证令牌"""
    try:
        # 模拟验证令牌
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=request.token)
        user = verify_token(credentials)
        return VerifyResponse(
            success=True,
            valid=True,
            user=user
        )
    except HTTPException:
        return VerifyResponse(
            success=True,
            valid=False,
            user=None
        )

@app.post("/api/auth/logout")
async def logout(user: Dict = Depends(verify_token)):
    """
    用户登出
    
    注意：使用JWT后，登出只需要客户端删除token即可。
    服务器端无需维护token状态。
    """
    logger.info(f"用户 {user['username']} 登出")
    return {"success": True, "message": "登出成功"}

# 受保护的路由
@app.get("/api/protected/database/status", response_model=DatabaseStatusResponse)
async def protected_database_status(user: Dict = Depends(verify_token)):
    """受保护的数据库状态"""
    try:
        db_status = get_database_status()
        return DatabaseStatusResponse(**db_status)
    except Exception as e:
        return DatabaseStatusResponse(
            connected=False,
            error=str(e)
        )

@app.post("/api/protected/chat", response_model=ChatResponse)
async def protected_chat_endpoint(
    request: ChatRequest, 
    user: Dict = Depends(verify_token)
):
    """受保护的聊天接口 - 连接到真实AI"""
    try:
        logger.info(f"收到聊天请求: 用户={user.get('username')}, 消息={request.message[:50]}...")
        
        # 统一的会话ID格式：username_timestamp
        # 如果前端传来的session_id已经有前缀，直接使用；否则添加前缀
        if request.session_id.startswith(f"{user['username']}_"):
            session_id = request.session_id
        else:
            session_id = f"{user['username']}_{request.session_id}"
        
        # 验证或创建会话
        if conversation_db:
            conversation = conversation_db.get_conversation(session_id, user['username'])
            if not conversation:
                # 会话不存在，创建新会话
                logger.info(f"创建新会话: {session_id}")
                conversation_db.create_conversation(
                    conversation_id=session_id,
                    user_id=user['id'],
                    username=user['username'],
                    title='新对话'
                )
        
        # 使用真实的AI处理
        result = process_chat_message(request.message, session_id, user_context=user)
        
        logger.info(f"聊天处理完成: success={result['success']}")
        return ChatResponse(
            success=result["success"],
            response=result["response"],
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"聊天处理失败: {e}", exc_info=True)
        return ChatResponse(
            success=False,
            response=f"处理查询时出错: {str(e)}",
            session_id=request.session_id
        )

@app.get("/api/protected/chat/stream")
async def protected_chat_stream_endpoint(
    message: str,
    session_id: str,
    user: Dict = Depends(verify_token)
):
    """流式聊天接口 - 使用 SSE"""
    session_id = f"{user['username']}_{session_id}"
    return StreamingResponse(
        process_chat_message_stream(message, session_id, user_context=user),
        media_type="text/event-stream"
    )

@app.post("/api/protected/sessions", response_model=Dict)
async def create_new_session(
    request: CreateSessionRequest,
    user: Dict = Depends(verify_token)
):
    """创建新会话"""
    try:
        if not conversation_db:
            raise HTTPException(status_code=503, detail="会话数据库未初始化")
        
        # 生成会话ID: username_timestamp
        session_id = f"{user['username']}_{int(datetime.now().timestamp() * 1000)}"
        
        conversation = conversation_db.create_conversation(
            conversation_id=session_id,
            user_id=user['id'],
            username=user['username'],
            title=request.title
        )
        
        return {
            "success": True,
            "session_id": conversation['id'],
            "message": "会话创建成功"
        }
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")

@app.get("/api/protected/sessions", response_model=SessionListResponse)
async def get_sessions(user: Dict = Depends(verify_token)):
    """获取用户的所有会话列表"""
    try:
        sessions = get_user_sessions(user['username'])
        return SessionListResponse(success=True, sessions=sessions)
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        return SessionListResponse(success=False, sessions=[])

@app.get("/api/protected/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    user: Dict = Depends(verify_token)
):
    """获取指定会话的历史消息"""
    try:
        messages = fetch_session_history(session_id, user['username'])
        return SessionHistoryResponse(
            success=True,
            messages=messages,
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"获取会话历史失败: {e}")
        return SessionHistoryResponse(
            success=False,
            messages=[],
            session_id=session_id
        )

@app.put("/api/protected/sessions/{session_id}/title")
async def update_session_title(
    session_id: str,
    request: UpdateSessionTitleRequest,
    user: Dict = Depends(verify_token)
):
    """更新会话标题"""
    try:
        if not conversation_db:
            raise HTTPException(status_code=503, detail="会话数据库未初始化")
        
        # 验证 session_id 属于该用户
        if not session_id.startswith(f"{user['username']}_"):
            raise HTTPException(status_code=403, detail="无权访问此会话")
        
        success = conversation_db.update_conversation_title(
            session_id, 
            request.title,
            username=user['username']
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return {"success": True, "message": "标题更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新标题失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新标题失败: {str(e)}")

@app.delete("/api/protected/sessions/{session_id}")
async def delete_session(
    session_id: str,
    hard_delete: bool = False,
    user: Dict = Depends(verify_token)
):
    """删除会话"""
    try:
        if not conversation_db:
            raise HTTPException(status_code=503, detail="会话数据库未初始化")
        
        # 验证 session_id 属于该用户
        if not session_id.startswith(f"{user['username']}_"):
            raise HTTPException(status_code=403, detail="无权访问此会话")
        
        success = conversation_db.delete_conversation(
            session_id,
            username=user['username'],
            soft_delete=not hard_delete
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return {
            "success": True, 
            "message": "会话已删除" if hard_delete else "会话已归档"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")

@app.get("/api/protected/users", response_model=List[UserResponse])
async def get_users(user: Dict = Depends(verify_token)):
    """获取用户列表（仅管理员）"""
    if user["user_type"] != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )
    
    conn = get_db_connection()
    users = conn.execute('''
        SELECT id, username, email, user_type, created_at, is_active 
        FROM users ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    
    return [dict(user) for user in users]

# ==================== 索引管理 API ====================

def progress_callback(current: int, total: int, message: str):
    """索引进度回调"""
    indexing_status["progress"] = current
    indexing_status["total"] = total
    indexing_status["current_step"] = message
    logger.info(f"Indexing progress: {current}/{total} - {message}")

async def run_indexing():
    """后台运行索引任务"""
    try:
        indexing_status["is_indexing"] = True
        indexing_status["progress"] = 0
        indexing_status["error"] = None
        indexing_status["completed"] = False
        
        # 连接数据库
        if not db.is_connected:
            db.connect()
        
        # 索引表
        indexing_status["current_step"] = "正在索引数据库表..."
        table_count = vector_store.index_tables(db.engine, progress_callback)
        logger.info(f"Indexed {table_count} tables")
        
        # 索引列
        indexing_status["current_step"] = "正在索引数据库列..."
        column_count = vector_store.index_columns(db.engine, progress_callback)
        logger.info(f"Indexed {column_count} columns")
        
        # 索引业务术语
        indexing_status["current_step"] = "正在索引业务术语..."
        term_count = vector_store.index_business_terms(progress_callback=progress_callback)
        logger.info(f"Indexed {term_count} business terms")
        
        indexing_status["completed"] = True
        indexing_status["current_step"] = "索引完成"
        logger.info("✅ All indexing completed successfully")
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        indexing_status["error"] = str(e)
        indexing_status["current_step"] = f"索引失败: {str(e)}"
    finally:
        indexing_status["is_indexing"] = False

@app.post("/api/protected/index/trigger", response_model=IndexTriggerResponse)
async def trigger_indexing(
    background_tasks: BackgroundTasks,
    user: Dict = Depends(verify_token)
):
    """
    触发数据库索引（管理员功能）
    
    这会在后台运行索引任务，索引数据库的表、列和业务术语到向量数据库。
    """
    # 只有管理员可以触发索引
    if user.get("user_type") != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以触发索引"
        )
    
    # 检查是否正在索引
    if indexing_status["is_indexing"]:
        return IndexTriggerResponse(
            success=False,
            message="索引任务正在进行中，请稍后再试"
        )
    
    # 检查数据库连接
    if not HAS_AGENT:
        return IndexTriggerResponse(
            success=False,
            message="Agent 模块未加载"
        )
    
    # 启动后台索引任务
    background_tasks.add_task(run_indexing)
    
    return IndexTriggerResponse(
        success=True,
        message="索引任务已启动，请使用 /api/protected/index/status 查看进度"
    )

@app.get("/api/protected/index/status", response_model=IndexStatusResponse)
async def get_index_status(user: Dict = Depends(verify_token)):
    """
    获取索引状态和统计信息
    """
    try:
        stats = vector_store.get_index_stats()
        
        return IndexStatusResponse(
            is_indexing=indexing_status["is_indexing"],
            progress=indexing_status["progress"],
            total=indexing_status["total"],
            current_step=indexing_status["current_step"],
            completed=indexing_status["completed"],
            error=indexing_status["error"],
            index_stats=stats
        )
    except Exception as e:
        logger.error(f"Failed to get index status: {e}")
        return IndexStatusResponse(
            is_indexing=False,
            progress=0,
            total=0,
            current_step="",
            completed=False,
            error=str(e),
            index_stats={"tables": 0, "columns": 0, "business_terms": 0}
        )

@app.delete("/api/protected/index/clear")
async def clear_index(user: Dict = Depends(verify_token)):
    """
    清空所有索引（管理员功能）
    """
    if user.get("user_type") != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以清空索引"
        )
    
    try:
        vector_store.clear_all_indexes()
        indexing_status["completed"] = False
        return {"success": True, "message": "索引已清空"}
    except Exception as e:
        logger.error(f"Failed to clear indexes: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/protected/index/auto-check")
async def auto_check_index(user: Dict = Depends(verify_token)):
    """
    自动检查索引状态，如果没有索引则提示用户
    """
    try:
        stats = vector_store.get_index_stats()
        has_index = stats["tables"] > 0 or stats["columns"] > 0
        
        return {
            "has_index": has_index,
            "stats": stats,
            "should_index": not has_index,
            "message": "数据库未索引，建议先进行索引以获得更好的查询体验" if not has_index else "索引已就绪"
        }
    except Exception as e:
        return {
            "has_index": False,
            "stats": {"tables": 0, "columns": 0, "business_terms": 0},
            "should_index": True,
            "error": str(e)
        }

@app.post("/api/protected/vector/search", response_model=VectorSearchResponse)
async def vector_search(
    request: VectorSearchRequest,
    user: Dict = Depends(verify_token)
):
    """
    向量语义搜索API
    
    直接搜索已索引的表、列和业务术语，无需通过agent。
    
    参数:
        - query: 搜索查询（支持中英文）
        - top_k: 返回结果数量（默认5）
        - search_types: 搜索类型列表，可选 ["table", "column", "business_term"]
    
    返回:
        匹配的表、列、业务术语列表，按相似度排序
    
    示例:
        {
            "query": "用户活跃度",
            "top_k": 3,
            "search_types": ["business_term", "table"]
        }
    """
    if not HAS_AGENT:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="向量搜索服务未加载"
        )
    
    try:
        # 检查索引是否存在
        stats = vector_store.get_index_stats()
        total_indexed = stats.get("tables", 0) + stats.get("columns", 0) + stats.get("business_terms", 0)
        
        if total_indexed == 0:
            return VectorSearchResponse(
                success=False,
                query=request.query,
                results=[],
                total=0,
                message="索引为空，请先进行索引操作"
            )
        
        # 执行搜索
        search_results = vector_store.search(
            query=request.query,
            top_k=request.top_k or 5,
            search_types=request.search_types
        )
        
        # 转换结果格式
        result_items = []
        for result in search_results:
            result_items.append(SearchResultItem(
                name=result.name,
                type=result.item_type,
                similarity=round(result.similarity, 4),
                metadata=result.metadata
            ))
        
        return VectorSearchResponse(
            success=True,
            query=request.query,
            results=result_items,
            total=len(result_items),
            message=f"找到 {len(result_items)} 个相关结果"
        )
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)