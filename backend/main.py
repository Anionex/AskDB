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

# 修复导入路径
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
import uvicorn


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from askdb_agno import create_agent
    from tools.agno_tools import db 
    HAS_AGENT = True
except ImportError as e:
    HAS_AGENT = False
    logger.error(f"❌ 无法导入AskDB模块: {e}")

# 安全配置
security = HTTPBearer()

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

# 验证码存储
verification_codes: Dict[str, Dict] = {}

# 令牌存储
active_tokens: Dict[str, Dict] = {}

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

class DatabaseStatusResponse(BaseModel):
    connected: bool
    database_type: Optional[str] = None
    table_count: Optional[int] = None
    tables: Optional[List[str]] = None
    error: Optional[str] = None

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

# 令牌管理
def create_access_token(username: str) -> str:
    """创建访问令牌"""
    token = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(hours=24)
    
    active_tokens[token] = {
        "username": username,
        "expires": expires
    }
    
    return token

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """验证令牌"""
    token = credentials.credentials
    
    if token not in active_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )
    
    token_data = active_tokens[token]
    if datetime.now() > token_data["expires"]:
        del active_tokens[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期"
        )
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE username = ?', 
        (token_data["username"],)
    ).fetchone()
    conn.close()
    
    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )
    
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

def process_chat_message(message: str, session_id: str = "web-session"):
    """处理聊天消息"""
    try:
        if not HAS_AGENT:
            return {
                "success": False,
                "response": "AskDB Agent模块未加载，无法处理查询"
            }
        
        # 创建AI代理
        agent = create_agent(
            debug=False,
            enable_memory=True,
            session_id=session_id
        )
        
        # 处理消息
        response = agent.run(message)
        
        return {
            "success": True,
            "response": response.content
        }
        
    except Exception as e:
        logger.error(f"AI处理失败: {e}")
        # 检查是否是web搜索相关的错误
        if "event loop" in str(e).lower() or "coroutine" in str(e).lower():
            return {
                "success": False,
                "response": f"Web搜索功能暂时不可用: {str(e)}"
            }
        else:
            return {
                "success": False,
                "response": f"处理查询时出错: {str(e)}"
            }

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
    
    # 创建令牌
    token = create_access_token(user["username"])
    
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
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """用户登出"""
    token = credentials.credentials
    if token in active_tokens:
        del active_tokens[token]
    
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
        # 使用真实的AI处理
        result = process_chat_message(request.message, request.session_id)
        
        return ChatResponse(
            success=result["success"],
            response=result["response"],
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        return ChatResponse(
            success=False,
            response=f"处理查询时出错: {str(e)}",
            session_id=request.session_id
        )

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)