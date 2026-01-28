import { create } from 'zustand'
import axios from 'axios'

const API_BASE = '/api'

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
  
  // 推荐查询
  recommendations: [],
  
  // 确认操作状态
  pendingConfirmation: null, // { sql, explanation, expected_impact, session_id }

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
          messages: { ...get().messages, [sessionId]: [] },
          recommendations: []  // 清空推荐
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
    set({
      currentSessionId: sessionId,
      recommendations: []  // 清空推荐
    })
    // 始终从后端加载最新历史
    await get().loadSessionHistory(sessionId)
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
        const historyMessages = response.data.messages || []
        // 直接使用后端数据作为唯一数据源
        set(state => ({
          messages: {
            ...state.messages,
            [sessionId]: historyMessages
          }
        }))
      }
    } catch (error) {
      console.error('加载会话历史失败:', error)
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

  // 更新最后一条消息（用于流式更新）
  updateLastMessage: (updates) => {
    const sessionId = get().currentSessionId
    if (!sessionId) return
    
    const currentMessages = get().messages[sessionId] || []
    if (currentMessages.length === 0) return
    
    const lastIndex = currentMessages.length - 1
    const updatedMessages = [...currentMessages]
    updatedMessages[lastIndex] = {
      ...updatedMessages[lastIndex],
      ...updates
    }
    
    set(state => ({
      messages: {
        ...state.messages,
        [sessionId]: updatedMessages
      }
    }))
  },

  // 添加工具调用到最后一条消息
  addToolCallToLastMessage: (toolCall) => {
    const sessionId = get().currentSessionId
    if (!sessionId) return
    
    const currentMessages = get().messages[sessionId] || []
    if (currentMessages.length === 0) return
    
    const lastIndex = currentMessages.length - 1
    const lastMessage = currentMessages[lastIndex]
    
    // 只更新assistant消息
    if (lastMessage.type !== 'assistant') return
    
    const updatedMessages = [...currentMessages]
    const existingToolCalls = lastMessage.toolCalls || []
    
    updatedMessages[lastIndex] = {
      ...lastMessage,
      toolCalls: [...existingToolCalls, toolCall]
    }
    
    set(state => ({
      messages: {
        ...state.messages,
        [sessionId]: updatedMessages
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

    // 不再预先创建空消息，而是在收到第一个事件时创建
    let aiMessageCreated = false
    let aiMessageId = null
    let currentContentLength = 0

    try {
      // 使用流式接口
      const url = `${API_BASE}/protected/chat/stream?message=${encodeURIComponent(content)}&session_id=${sessionId}`
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream'
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === 'content') {
                // 第一次收到内容时创建消息
                if (!aiMessageCreated) {
                  aiMessageId = Date.now() + 1
                  get().addMessage({
                    id: aiMessageId,
                    type: 'assistant',
                    content: data.content,
                    timestamp: new Date().toISOString(),
                    toolCalls: []
                  })
                  aiMessageCreated = true
                  currentContentLength = data.content.length
                } else {
                  // 后续内容追加
                  const currentMessages = get().messages[sessionId] || []
                  const lastMessage = currentMessages[currentMessages.length - 1]
                  if (lastMessage && lastMessage.type === 'assistant') {
                    get().updateLastMessage({
                      content: (lastMessage.content || '') + data.content
                    })
                    currentContentLength += data.content.length
                  }
                }
              } else if (data.type === 'tool_call_start') {
                // 工具调用开始
                console.log('🔧 [收到工具调用开始]', data.data)
                
                // 如果还没创建消息，先创建
                if (!aiMessageCreated) {
                  aiMessageId = Date.now() + 1
                  get().addMessage({
                    id: aiMessageId,
                    type: 'assistant',
                    content: '',
                    timestamp: new Date().toISOString(),
                    toolCalls: []
                  })
                  aiMessageCreated = true
                }
                
                get().addToolCallToLastMessage({
                  name: data.data.name,
                  arguments: data.data.arguments,
                  result: null,
                  insertPosition: currentContentLength,
                  status: 'started'
                })
              } else if (data.type === 'tool_call_result') {
                // 工具调用结果 - 更新对应的工具调用
                console.log('✅ [收到工具调用结果]', data.data.name)
                const currentMessages = get().messages[sessionId] || []
                const lastMessage = currentMessages[currentMessages.length - 1]
                if (lastMessage && lastMessage.toolCalls && lastMessage.toolCalls.length > 0) {
                  const updatedToolCalls = [...lastMessage.toolCalls]
                  // 找到最后一个名称匹配且结果为空的工具调用
                  for (let i = updatedToolCalls.length - 1; i >= 0; i--) {
                    if (updatedToolCalls[i].name === data.data.name && 
                        (updatedToolCalls[i].result === null || updatedToolCalls[i].result === undefined)) {
                      updatedToolCalls[i].result = data.data.result
                      updatedToolCalls[i].status = 'completed'
                      updatedToolCalls[i].completedPosition = currentContentLength
                      break
                    }
                  }
                  get().updateLastMessage({ toolCalls: updatedToolCalls })
                  console.log('📝 [工具调用已更新]', updatedToolCalls)
                }
              } else if (data.type === 'needs_confirmation') {
                // 🔒 收到确认请求
                console.log('🔒 [收到确认请求]', data.data)
                set({ 
                  pendingConfirmation: {
                    ...data.data,
                    session_id: sessionId
                  },
                  isThinking: false,
                  isLoading: false
                })
              } else if (data.type === 'recommendations') {
                // 收到推荐查询
                console.log('💡 [收到推荐查询]', data.data)
                if (data.data && Array.isArray(data.data) && data.data.length > 0) {
                  set({ recommendations: data.data })
                  console.log('✅ [推荐已设置到状态]', data.data)
                } else {
                  console.warn('⚠️ [推荐数据为空或格式错误]', data.data)
                  set({ recommendations: [] })
                }
              } else if (data.type === 'title_updated') {
                // 收到标题更新通知
                console.log('📝 [收到标题更新]', data.title)
                if (data.title && sessionId) {
                  // 立即更新本地会话列表中的标题
                  const sessions = get().sessions.map(s => 
                    s.id === sessionId ? { ...s, title: data.title, updated_at: new Date().toISOString() } : s
                  )
                  set({ sessions })
                  console.log('✅ [标题已更新到本地状态]', data.title)
                }
              } else if (data.type === 'done') {
                // 完成 - 刷新会话列表以确保同步（标题可能已更新）
                await get().fetchSessions()
                break
              } else if (data.type === 'error') {
                throw new Error(data.content)
              }
            } catch (e) {
              console.error('解析SSE数据失败:', e, line)
            }
          }
        }
      }
      
      // 流式响应完成后，再次刷新会话列表以确保同步（如果done事件中已刷新，这里会再次刷新但不会造成问题）
      await get().fetchSessions()
      
    } catch (error) {
      console.error('流式请求失败:', error)
      
      // 删除空的 AI 消息，添加错误消息
      const currentMessages = get().messages[sessionId] || []
      const filteredMessages = currentMessages.filter(m => m.id !== aiMessageId)
      
      set(state => ({
        messages: {
          ...state.messages,
          [sessionId]: [
            ...filteredMessages,
            {
              id: Date.now(),
              type: 'error',
              content: `错误: ${error.message}`,
              timestamp: new Date().toISOString()
            }
          ]
        }
      }))
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
  
  // 确认危险操作
  confirmDangerousAction: async () => {
    const token = localStorage.getItem('askdb_token')
    const confirmation = get().pendingConfirmation
    
    if (!token || !confirmation) return
    
    try {
      const response = await axios.post(
        `${API_BASE}/protected/confirm-action`,
        {
          session_id: confirmation.session_id,
          sql: confirmation.sql,
          explanation: confirmation.explanation,
          action: 'approve'
        },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      
      if (response.data.success) {
        // 添加成功消息
        get().addMessage({
          id: Date.now(),
          type: 'assistant',
          content: `✅ ${response.data.message}\n\n受影响的行数: ${response.data.rows_affected}`,
          timestamp: new Date().toISOString()
        })
      } else {
        // 添加失败消息
        get().addMessage({
          id: Date.now(),
          type: 'error',
          content: `❌ 操作失败: ${response.data.message}`,
          timestamp: new Date().toISOString()
        })
      }
      
      // 清除待确认状态
      set({ pendingConfirmation: null })
      
    } catch (error) {
      console.error('确认操作失败:', error)
      get().addMessage({
        id: Date.now(),
        type: 'error',
        content: `❌ 确认操作失败: ${error.message}`,
        timestamp: new Date().toISOString()
      })
      set({ pendingConfirmation: null })
    }
  },
  
  // 拒绝危险操作
  rejectDangerousAction: () => {
    const confirmation = get().pendingConfirmation
    if (!confirmation) return
    
    // 添加取消消息
    get().addMessage({
      id: Date.now(),
      type: 'assistant',
      content: '❌ 操作已取消。',
      timestamp: new Date().toISOString()
    })
    
    // 清除待确认状态
    set({ pendingConfirmation: null })
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
      sessionsLoaded: false,
      pendingConfirmation: null
    })
  }
}))

