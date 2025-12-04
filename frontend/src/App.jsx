import React, { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import './App.css'

const API_BASE = 'http://localhost:8000/api'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [user, setUser] = useState(null)
  const [currentView, setCurrentView] = useState('login') // 'login', 'register'
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [registerForm, setRegisterForm] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    userType: 'user',
    verificationCode: ''
  })
  const [loginError, setLoginError] = useState('')
  const [registerError, setRegisterError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSendingCode, setIsSendingCode] = useState(false)
  const [codeSent, setCodeSent] = useState(false)
  const [countdown, setCountdown] = useState(0)
  
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [databaseInfo, setDatabaseInfo] = useState(null)
  const [isThinking, setIsThinking] = useState(false) // 新增：思考状态
  const [abortController, setAbortController] = useState(null) // 新增：用于取消请求
  const messagesEndRef = useRef(null)

  useEffect(() => {
    scrollToBottom()
    checkAuthentication()
  }, [])

  useEffect(() => {
    if (isLoggedIn) {
      checkDatabaseStatus()
    }
  }, [isLoggedIn])

  // 倒计时效果
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [countdown])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const checkAuthentication = async () => {
    const token = localStorage.getItem('askdb_token')
    if (!token) return

    try {
      const response = await axios.post(`${API_BASE}/auth/verify`, {
        token: token
      })
      
      if (response.data.success && response.data.valid) {
        setIsLoggedIn(true)
        setUser(response.data.user)
      } else {
        localStorage.removeItem('askdb_token')
      }
    } catch (error) {
      console.error('认证检查失败:', error)
      localStorage.removeItem('askdb_token')
    }
  }

  const handleLogin = async (e) => {
    if (e) e.preventDefault()
    setIsLoading(true)
    setLoginError('')

    try {
      const response = await axios.post(`${API_BASE}/auth/login`, loginForm)
      
      if (response.data.success) {
        localStorage.setItem('askdb_token', response.data.token)
        setIsLoggedIn(true)
        setUser(response.data.user)
        setLoginError('')
        setLoginForm({ username: '', password: '' })
      } else {
        setLoginError(response.data.message || '登录失败')
      }
    } catch (error) {
      console.error('登录错误:', error)
      if (error.response) {
        setLoginError(error.response.data?.message || `登录失败: ${error.response.status}`)
      } else if (error.request) {
        setLoginError('无法连接到服务器，请检查：\n1. 后端服务是否运行在 localhost:8000\n2. 网络连接是否正常')
      } else {
        setLoginError(`登录失败: ${error.message}`)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleSendCode = async () => {
    if (!registerForm.email) {
      setRegisterError('请输入邮箱地址')
      return
    }

    // 邮箱格式验证
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(registerForm.email)) {
      setRegisterError('请输入有效的邮箱地址')
      return
    }

    setIsSendingCode(true)
    setRegisterError('')

    try {
      const response = await axios.post(`${API_BASE}/auth/send-code`, {
        email: registerForm.email
      })
      
      if (response.data.success) {
        setCodeSent(true)
        setCountdown(60) // 60秒倒计时
        setRegisterError('✅ 验证码已发送到您的邮箱')
      } else {
        setRegisterError(response.data.message)
      }
    } catch (error) {
      console.error('发送验证码失败:', error)
      if (error.response) {
        setRegisterError(error.response.data?.message || '发送验证码失败')
      } else if (error.request) {
        setRegisterError('无法连接到服务器，请检查网络连接')
      } else {
        setRegisterError('发送验证码失败，请重试')
      }
    } finally {
      setIsSendingCode(false)
    }
  }

  const handleRegister = async (e) => {
    if (e) e.preventDefault()
    setIsLoading(true)
    setRegisterError('')

    // 表单验证
    if (registerForm.username.length < 3 || registerForm.username.length > 20) {
      setRegisterError('用户名长度必须在3-20字符之间')
      setIsLoading(false)
      return
    }

    if (!/^[a-zA-Z0-9_]+$/.test(registerForm.username)) {
      setRegisterError('用户名只能包含字母、数字和下划线')
      setIsLoading(false)
      return
    }

    if (registerForm.password.length < 6) {
      setRegisterError('密码长度至少6位')
      setIsLoading(false)
      return
    }

    if (registerForm.password !== registerForm.confirmPassword) {
      setRegisterError('两次输入的密码不一致')
      setIsLoading(false)
      return
    }

    if (!registerForm.verificationCode) {
      setRegisterError('请输入验证码')
      setIsLoading(false)
      return
    }

    try {
      const response = await axios.post(`${API_BASE}/auth/register`, {
        username: registerForm.username,
        email: registerForm.email,
        password: registerForm.password,
        user_type: registerForm.userType,
        verification_code: registerForm.verificationCode
      })
      
      if (response.data.success) {
        setRegisterError('🎉 注册成功！请登录')
        setCurrentView('login')
        // 清空注册表单
        setRegisterForm({
          username: '',
          email: '',
          password: '',
          confirmPassword: '',
          userType: 'user',
          verificationCode: ''
        })
        setCodeSent(false)
        setCountdown(0)
      } else {
        setRegisterError(response.data.message)
      }
    } catch (error) {
      console.error('注册失败:', error)
      if (error.response) {
        setRegisterError(error.response.data?.message || '注册失败')
      } else if (error.request) {
        setRegisterError('无法连接到服务器，请检查网络连接')
      } else {
        setRegisterError('注册失败，请重试')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogout = async () => {
    const token = localStorage.getItem('askdb_token')
    if (token) {
      try {
        await axios.post(`${API_BASE}/auth/logout`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        })
      } catch (error) {
        console.error('登出失败:', error)
      }
    }
    
    localStorage.removeItem('askdb_token')
    setIsLoggedIn(false)
    setUser(null)
    setMessages([])
    setCurrentView('login')
  }

  const checkDatabaseStatus = async () => {
    const token = localStorage.getItem('askdb_token')
    if (!token) return

    try {
      const response = await axios.get(`${API_BASE}/protected/database/status`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setDatabaseInfo(response.data)
    } catch (error) {
      console.error('检查数据库状态失败:', error)
      setDatabaseInfo({ 
        connected: false, 
        error: '无法获取数据库状态' 
      })
    }
  }

  // 新增：暂停AI思考
  const stopThinking = () => {
    if (abortController) {
      abortController.abort()
      setIsThinking(false)
      setAbortController(null)
      
      // 添加暂停提示消息
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        type: 'system',
        content: '思考已停止',
        timestamp: new Date().toISOString()
      }])
    }
  }

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return

    const token = localStorage.getItem('askdb_token')
    if (!token) {
      setLoginError('请先登录')
      return
    }

    const userMessage = inputMessage.trim()
    setInputMessage('')
    setIsLoading(true)
    setIsThinking(true) // 开始思考

    // 创建AbortController用于取消请求
    const controller = new AbortController()
    setAbortController(controller)

    // 添加用户消息
    setMessages(prev => [...prev, {
      id: Date.now(),
      type: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    }])

    try {
      const response = await axios.post(`${API_BASE}/protected/chat`, {
        message: userMessage,
        session_id: 'web-session'
      }, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal, // 添加取消信号
        timeout: 30000 // 30秒超时
      })

      // 添加AI响应
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        type: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString(),
        success: response.data.success
      }])
      
    } catch (error) {
      if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
        // 请求被取消，不显示错误消息
        console.log('请求已被用户取消')
      } else if (error.response?.status === 401) {
        // 令牌失效
        handleLogout()
        setLoginError('登录已过期，请重新登录')
      } else {
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          type: 'error',
          content: `错误: ${error.response?.data?.error || error.message}`,
          timestamp: new Date().toISOString()
        }])
      }
    } finally {
      setIsLoading(false)
      setIsThinking(false)
      setAbortController(null)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  const handleExampleClick = (exampleText) => {
    setInputMessage(exampleText)
  }

  // 登录界面
  if (!isLoggedIn) {
    if (currentView === 'register') {
      return (
        <div className="login-container">
          <div className="login-form">
            <div className="login-header">
              <h1>🤖 AskDB</h1>
              <p>创建新账户</p>
            </div>
            
            <form onSubmit={handleRegister}>
              <div className="form-group">
                <label htmlFor="username">用户名</label>
                <input
                  type="text"
                  id="username"
                  value={registerForm.username}
                  onChange={(e) => setRegisterForm(prev => ({
                    ...prev,
                    username: e.target.value
                  }))}
                  placeholder="3-20位字母、数字、下划线"
                  required
                  disabled={isLoading}
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="email">邮箱地址</label>
                <div className="email-input-group">
                  <input
                    type="email"
                    id="email"
                    value={registerForm.email}
                    onChange={(e) => setRegisterForm(prev => ({
                      ...prev,
                      email: e.target.value
                    }))}
                    placeholder="请输入邮箱地址"
                    required
                    disabled={isLoading || codeSent}
                  />
                  <button
                    type="button"
                    onClick={handleSendCode}
                    disabled={isSendingCode || countdown > 0 || !registerForm.email}
                    className="send-code-btn"
                  >
                    {countdown > 0 ? `${countdown}s` : 
                     isSendingCode ? '发送中...' : '获取验证码'}
                  </button>
                </div>
              </div>
              
              <div className="form-group">
                <label htmlFor="verificationCode">验证码</label>
                <input
                  type="text"
                  id="verificationCode"
                  value={registerForm.verificationCode}
                  onChange={(e) => setRegisterForm(prev => ({
                    ...prev,
                    verificationCode: e.target.value
                  }))}
                  placeholder="请输入6位验证码"
                  required
                  disabled={isLoading}
                  maxLength={6}
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="userType">账户类型</label>
                <select
                  id="userType"
                  value={registerForm.userType}
                  onChange={(e) => setRegisterForm(prev => ({
                    ...prev,
                    userType: e.target.value
                  }))}
                  disabled={isLoading}
                >
                  <option value="user">👤 普通员工</option>
                  <option value="manager">👑 管理员</option>
                </select>
                <small className="role-hint">
                  {registerForm.userType === 'user' 
                    ? '普通员工：可以查询数据，无法修改数据库' 
                    : '管理员：拥有完整权限，可以管理用户和数据'}
                </small>
              </div>
              
              <div className="form-group">
                <label htmlFor="password">密码</label>
                <input
                  type="password"
                  id="password"
                  value={registerForm.password}
                  onChange={(e) => setRegisterForm(prev => ({
                    ...prev,
                    password: e.target.value
                  }))}
                  placeholder="至少6位密码"
                  required
                  disabled={isLoading}
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="confirmPassword">确认密码</label>
                <input
                  type="password"
                  id="confirmPassword"
                  value={registerForm.confirmPassword}
                  onChange={(e) => setRegisterForm(prev => ({
                    ...prev,
                    confirmPassword: e.target.value
                  }))}
                  placeholder="请再次输入密码"
                  required
                  disabled={isLoading}
                />
              </div>
              
              {registerError && (
                <div className={`message ${registerError.includes('✅') || registerError.includes('🎉') ? 'success' : 'error'}`}>
                  {registerError}
                </div>
              )}
              
              <div className="form-actions">
                <button 
                  type="submit" 
                  className="login-button"
                  disabled={isLoading}
                >
                  {isLoading ? '注册中...' : '注册账户'}
                </button>
                
                <button 
                  type="button"
                  onClick={() => {
                    setCurrentView('login')
                    setRegisterError('')
                  }}
                  className="back-button"
                >
                  返回登录
                </button>
              </div>
            </form>
            
            <div className="login-hint">
              <p><strong>提示：</strong></p>
              <p>• 管理员账户需要审核才能获得完整权限</p>
              <p>• 验证码10分钟内有效</p>
              <p>• 账户信息将永久保存在数据库中</p>
            </div>
          </div>
        </div>
      )
    }

    // 登录界面
    return (
      <div className="login-container">
        <div className="login-form">
          <div className="login-header">
            <h1>🤖 AskDB</h1>
            <p>智能数据库助手 - 请登录</p>
          </div>
          
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label htmlFor="loginUsername">用户名</label>
              <input
                type="text"
                id="loginUsername"
                value={loginForm.username}
                onChange={(e) => setLoginForm(prev => ({
                  ...prev,
                  username: e.target.value
                }))}
                placeholder="请输入用户名"
                required
                disabled={isLoading}
                autoComplete="username"
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="loginPassword">密码</label>
              <input
                type="password"
                id="loginPassword"
                value={loginForm.password}
                onChange={(e) => setLoginForm(prev => ({
                  ...prev,
                  password: e.target.value
                }))}
                placeholder="请输入密码"
                required
                disabled={isLoading}
                autoComplete="current-password"
              />
            </div>
            
            {loginError && (
              <div className="error-message">{loginError}</div>
            )}
            
            <button 
              type="submit" 
              className="login-button"
              disabled={isLoading}
            >
              {isLoading ? '登录中...' : '登录'}
            </button>
          </form>
          
          <div className="login-actions">
            <button 
              onClick={() => {
                setCurrentView('register')
                setLoginError('')
              }}
              className="register-link"
            >
              还没有账户？立即注册
            </button>
          </div>
          
        </div>
      </div>
    )
  }

  // 主界面
  return (
    <div className="app">
      <div className="sidebar">
        <div className="sidebar-header">
          <h1>🤖 AskDB</h1>
          <p>智能数据库助手</p>
          <div className="user-info">
            <span>欢迎, {user?.username}</span>
            <span className="user-badge">
              {user?.user_type === 'manager' ? '👑 管理员' : '👤 员工'}
            </span>
            <button onClick={handleLogout} className="logout-btn">登出</button>
          </div>
        </div>

        <div className={`status ${databaseInfo?.connected ? 'connected' : 'disconnected'}`}>
          {databaseInfo?.connected ? '✅ 数据库已连接' : '❌ 数据库未连接'}
        </div>

        {databaseInfo && (
          <div className="database-info">
            <h3>数据库信息</h3>
            <div className="info-item">
              <span>类型:</span>
              <span>{databaseInfo.database_type}</span>
            </div>
            <div className="info-item">
              <span>表数量:</span>
              <span>{databaseInfo.table_count}</span>
            </div>
            <div className="info-item">
              <span>状态:</span>
              <span className={databaseInfo.connected ? 'connected' : 'disconnected'}>
                {databaseInfo.connected ? '已连接' : '未连接'}
              </span>
            </div>
          </div>
        )}

        <button onClick={clearChat} className="clear-btn">
          新对话
        </button>
      </div>

      <div className="main-content">
        <div className="chat-header">
          <h2>智能数据库查询</h2>
          {isThinking && (
            <div className="thinking-controls">
              <span className="thinking-text">AI正在思考中...</span>
              <button onClick={stopThinking} className="stop-thinking-btn">
                ⏹️ 停止思考
              </button>
            </div>
          )}
        </div>

        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h2>欢迎使用 AskDB</h2>
              <p>用自然语言查询你的数据库</p>
              <div className="examples">
                <div className="example" onClick={() => handleExampleClick("显示所有学生")}>
                  显示所有学生
                </div>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id} className={`message ${message.type}`}>
                <div className="message-avatar">
                  {message.type === 'user' ? '👤' : 
                   message.type === 'assistant' ? '🤖' : 
                   message.type === 'system' ? 'ℹ️' : '❌'}
                </div>
                <div className="message-content">
                  <div className="message-text">{message.content}</div>
                  <div className="message-time">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))
          )}
          {isThinking && (
            <div className="message assistant thinking">
              <div className="message-avatar">
                <div className="spinner"></div>
              </div>
              <div className="message-content">
                <div className="thinking-text">AI正在思考中...</div>
                <div className="thinking-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input">
          <div className="input-wrapper">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入你的数据库查询问题..."
              disabled={isLoading}
            />
            <button 
              onClick={sendMessage} 
              disabled={isLoading || !inputMessage.trim()}
              className="send-button"
            >
              {isLoading ? '发送中...' : '发送'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App