import { create } from 'zustand'
import axios from 'axios'

const API_BASE = 'http://localhost:8000/api'

export const useChatStore = create((set, get) => ({
  // 会话列表
  sessions: [],
  currentSessionId: null,
  
  // 当前会话的消息（缓存）
  messages: {},
  
  // UI 状态
  isThinking: false,
  isLoading: false,
  error: null,
  
  // 数据库信息
  databaseInfo: null,
  
  // 会话加载状态
  sessionsLoaded: false,

  // 获取会话列表
  fetchSessions: async () => {
    const token = localStorage.getItem('askdb_token')
    if (!token) return

    try {
      const response = await axios.get(`${API_BASE}/protected/sessions`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.data.success) {
        set({ 
          sessions: response.data.sessions || [],
          sessionsLoaded: true
        })
      }
    } catch (error) {
      console.error('获取会话列表失败:', error)
      set({ sessionsLoaded: true })
    }
  },

  // 创建新会话
  createSession: async () => {
    const token = localStorage.getItem('askdb_token')
    if (!token) {
      console.error('未登录，无法创建会话')
      return null
    }

    try {
      const response = await axios.post(
        `${API_BASE}/protected/sessions`,
        { title: '新对话' },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      
      if (response.data.success) {
        const sessionId = response.data.session_id
        
        // 刷新会话列表
        await get().fetchSessions()
        
        // 切换到新会话
        set({ 
          currentSessionId: sessionId,
          messages: { ...get().messages, [sessionId]: [] }
        })
        
        return sessionId
      }
    } catch (error) {
      console.error('创建会话失败:', error)
      set({ error: '创建会话失败' })
      return null
    }
  },

  // 切换会话
  switchSession: async (sessionId) => {
    set({ currentSessionId: sessionId })
    // 如果该会话没有消息缓存或消息为空，加载历史
    const cachedMessages = get().messages[sessionId]
    if (!cachedMessages || cachedMessages.length === 0) {
      await get().loadSessionHistory(sessionId)
    }
  },

  // 加载会话历史
  loadSessionHistory: async (sessionId) => {
    const token = localStorage.getItem('askdb_token')
    if (!token) return

    try {
      const response = await axios.get(
        `${API_BASE}/protected/sessions/${sessionId}/history`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      
      if (response.data.success) {
        set(state => ({
          messages: { 
            ...state.messages, 
            [sessionId]: response.data.messages || [] 
          }
        }))
      }
    } catch (error) {
      console.error('加载会话历史失败:', error)
      // 如果加载失败，初始化为空数组
      set(state => ({
        messages: { ...state.messages, [sessionId]: [] }
      }))
    }
  },

  // 删除会话
  deleteSession: async (sessionId) => {
    const token = localStorage.getItem('askdb_token')
    if (!token) return

    try {
      await axios.delete(
        `${API_BASE}/protected/sessions/${sessionId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      
      // 从本地状态移除
      const sessions = get().sessions.filter(s => s.id !== sessionId)
      const messages = { ...get().messages }
      delete messages[sessionId]
      
      set({ sessions, messages })
      
      // 如果删除的是当前会话，切换到第一个或创建新会话
      if (get().currentSessionId === sessionId) {
        if (sessions.length > 0) {
          await get().switchSession(sessions[0].id)
        } else {
          await get().createSession()
        }
      }
    } catch (error) {
      console.error('删除会话失败:', error)
      set({ error: '删除会话失败' })
    }
  },

  // 更新会话标题
  updateSessionTitle: async (sessionId, title) => {
    const token = localStorage.getItem('askdb_token')
    if (!token) return

    try {
      await axios.put(
        `${API_BASE}/protected/sessions/${sessionId}/title`,
        { title },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      
      // 更新本地状态
      const sessions = get().sessions.map(s => 
        s.id === sessionId ? { ...s, title, updated_at: new Date().toISOString() } : s
      )
      set({ sessions })
    } catch (error) {
      console.error('更新会话标题失败:', error)
    }
  },

  // 添加消息（仅本地缓存，实际存储由后端处理）
  addMessage: (message) => {
    const sessionId = get().currentSessionId
    if (!sessionId) return
    
    const currentMessages = get().messages[sessionId] || []
    
    set(state => ({
      messages: {
        ...state.messages,
        [sessionId]: [...currentMessages, message]
      }
    }))
  },

  // 发送消息
  sendMessage: async (content) => {
    const token = localStorage.getItem('askdb_token')
    if (!token) {
      set({ error: '请先登录' })
      return
    }

    let sessionId = get().currentSessionId
    if (!sessionId) {
      // 创建新会话
      sessionId = await get().createSession()
      if (!sessionId) {
        set({ error: '创建会话失败' })
        return
      }
    }
    
    // 添加用户消息到本地缓存
    get().addMessage({
      id: Date.now(),
      type: 'user',
      content,
      timestamp: new Date().toISOString()
    })

    set({ isThinking: true, isLoading: true, error: null })

    try {
      const response = await axios.post(
        `${API_BASE}/protected/chat`,
        { message: content, session_id: sessionId },
        {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 60000
        }
      )

      // 添加 AI 响应到本地缓存
      get().addMessage({
        id: Date.now() + 1,
        type: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString(),
        success: response.data.success,
        toolCalls: response.data.tool_calls || []
      })
      
      // 刷新会话列表（更新消息计数和时间）
      get().fetchSessions()
      
    } catch (error) {
      if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
        get().addMessage({
          id: Date.now() + 1,
          type: 'system',
          content: '思考已停止',
          timestamp: new Date().toISOString()
        })
      } else if (error.response?.status === 401) {
        set({ error: '登录已过期，请重新登录' })
        window.location.reload()
      } else {
        get().addMessage({
          id: Date.now() + 1,
          type: 'error',
          content: `错误: ${error.response?.data?.detail || error.message}`,
          timestamp: new Date().toISOString()
        })
      }
    } finally {
      set({ isThinking: false, isLoading: false })
    }
  },

  // 清空当前会话（删除并创建新会话）
  clearCurrentSession: async () => {
    const sessionId = get().currentSessionId
    if (sessionId) {
      await get().deleteSession(sessionId)
      await get().createSession()
    }
  },

  // 获取数据库状态
  fetchDatabaseStatus: async () => {
    const token = localStorage.getItem('askdb_token')
    if (!token) return

    try {
      const response = await axios.get(`${API_BASE}/protected/database/status`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      set({ databaseInfo: response.data })
    } catch (error) {
      console.error('获取数据库状态失败:', error)
      set({ databaseInfo: { connected: false, error: '无法获取数据库状态' } })
    }
  },

  // 初始化：加载会话列表和数据库状态
  initialize: async () => {
    await get().fetchSessions()
    await get().fetchDatabaseStatus()
    
    // 如果没有会话，创建第一个
    if (get().sessions.length === 0) {
      await get().createSession()
    } else {
      // 切换到最新的会话（会自动加载历史消息）
      const latestSession = get().sessions.sort((a, b) => 
        new Date(b.updated_at) - new Date(a.updated_at)
      )[0]
      await get().switchSession(latestSession.id)
    }
  },
  
  // 清理：登出时清空所有状态
  cleanup: () => {
    set({
      sessions: [],
      currentSessionId: null,
      messages: {},
      isThinking: false,
      isLoading: false,
      error: null,
      databaseInfo: null,
      sessionsLoaded: false
    })
  }
}))

