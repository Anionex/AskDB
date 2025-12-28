import React, { useEffect, useRef, useState } from 'react'
import { Layout, Input, Button, Empty, Spin, Typography, Avatar, Tag, Space } from 'antd'
import { SendOutlined, StopOutlined, UserOutlined, RobotOutlined, BulbOutlined } from '@ant-design/icons'
import { useChatStore } from '../store/useChatStore'
import { MixedContentDisplay } from './MixedContentDisplay'
import { ToolCallsDisplay } from './ToolCallsDisplay'
import { DangerConfirmDialog } from './DangerConfirmDialog'

const { Content } = Layout
const { Text } = Typography

export const ChatArea = () => {
  const {
    currentSessionId,
    messages,
    isThinking,
    isLoading,
    sendMessage,
    addMessage,
    recommendations,
    pendingConfirmation,
    confirmDangerousAction,
    rejectDangerousAction
  } = useChatStore()

  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef(null)
  const abortControllerRef = useRef(null)

  const currentMessages = currentSessionId ? (messages[currentSessionId] || []) : []

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentMessages])

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return

    const message = inputValue.trim()
    setInputValue('')
    
    // 清空之前的推荐
    useChatStore.setState({ recommendations: [] })

    // 创建 AbortController 用于取消请求
    const controller = new AbortController()
    abortControllerRef.current = controller

    await sendMessage(message)
    abortControllerRef.current = null
  }
  
  const handleRecommendationClick = (recommendation) => {
    setInputValue(recommendation)
  }

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }
  
  const handleConfirmDangerous = async () => {
    await confirmDangerousAction()
  }
  
  const handleRejectDangerous = () => {
    rejectDangerousAction()
  }

  return (
    <>
      {/* 危险操作确认对话框 */}
      <DangerConfirmDialog
        visible={!!pendingConfirmation}
        onConfirm={handleConfirmDangerous}
        onCancel={handleRejectDangerous}
        sqlStatement={pendingConfirmation?.sql}
        explanation={pendingConfirmation?.explanation}
        expectedImpact={pendingConfirmation?.expected_impact}
      />
      
    <Content style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100vh',
      background: '#fafafa'
    }}>
      <div style={{ 
        flex: 1, 
        overflow: 'auto', 
        padding: '24px',
        background: '#fff',
        margin: '16px',
        borderRadius: '8px'
      }}>
        {currentMessages.length === 0 ? (
          <Empty
            description={
              <div>
                <Text strong style={{ fontSize: '16px' }}>欢迎使用 AskDB</Text>
                <br />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  用自然语言查询你的数据库
                </Text>
              </div>
            }
          />
        ) : (
          currentMessages.map((message) => (
            <div
              key={message.id}
              style={{
                marginBottom: '24px',
                display: 'flex',
                flexDirection: message.type === 'user' ? 'row-reverse' : 'row',
                gap: '12px'
              }}
            >
              <Avatar
                style={{
                  background: message.type === 'user' ? '#1890ff' : '#52c41a',
                  flexShrink: 0
                }}
                icon={message.type === 'user' ? <UserOutlined /> : <RobotOutlined />}
              />
              <div
                style={{
                  maxWidth: '70%',
                  background: message.type === 'user' ? '#1890ff' : '#f0f0f0',
                  color: message.type === 'user' ? '#fff' : '#000',
                  padding: message.type === 'user' ? '12px 16px' : '16px 20px 12px 36px',
                  borderRadius: '8px',
                  wordBreak: 'break-word'
                }}
              >
                {message.type === 'user' ? (
                  <Text style={{ color: '#fff' }}>{message.content}</Text>
                ) : message.type === 'assistant' ? (
                  <MixedContentDisplay 
                    message={message}
                    isStreaming={isThinking && message.id === currentMessages[currentMessages.length - 1]?.id}
                  />
                ) : message.type === 'error' ? (
                  <Text type="danger">{message.content}</Text>
                ) : (
                  <Text>{message.content}</Text>
                )}
                <div style={{ 
                  marginTop: '8px', 
                  fontSize: '11px', 
                  opacity: 0.7 
                }}>
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        )}
        {isThinking && (
          <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
            <Avatar
              style={{ background: '#52c41a' }}
              icon={<RobotOutlined />}
            />
            <div style={{ 
              background: '#f0f0f0', 
              padding: '12px 16px', 
              borderRadius: '8px' 
            }}>
              <Spin size="small" />
              <Text type="secondary" style={{ marginLeft: '8px' }}>
                AI 正在思考中...
              </Text>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div style={{ 
        padding: '16px', 
        borderTop: '1px solid #f0f0f0',
        background: '#fff'
      }}>
        {/* 推荐查询 */}
        {(() => {
          console.log('🔍 [推荐显示检查]', { 
            recommendations, 
            hasRecommendations: recommendations && recommendations.length > 0,
            isThinking,
            shouldShow: recommendations && recommendations.length > 0 && !isThinking
          })
          return null
        })()}
        {recommendations && recommendations.length > 0 && !isThinking && (
          <div style={{ marginBottom: '12px' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <BulbOutlined style={{ color: '#faad14', fontSize: '16px' }} />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                 接下来你可能想问：
                </Text>
              </div>
              <Space size={[8, 8]} wrap>
                {recommendations.map((rec, index) => (
                  <Tag
                    key={index}
                    style={{
                      cursor: 'pointer',
                      padding: '6px 12px',
                      fontSize: '13px',
                      borderRadius: '16px',
                      border: '1px solid #d9d9d9',
                      background: '#fafafa',
                      transition: 'all 0.2s'
                    }}
                    onClick={() => handleRecommendationClick(rec)}
                    onMouseEnter={(e) => {
                      e.target.style.background = '#e6f7ff'
                      e.target.style.borderColor = '#1890ff'
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.background = '#fafafa'
                      e.target.style.borderColor = '#d9d9d9'
                    }}
                  >
                    {rec}
                  </Tag>
                ))}
              </Space>
            </Space>
          </div>
        )}
        
        <Input.Group compact>
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入你的数据库查询问题..."
            disabled={isLoading}
            style={{ flex: 1 }}
          />
          {isThinking ? (
            <Button
              type="default"
              icon={<StopOutlined />}
              onClick={handleStop}
              danger
            >
              停止
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              disabled={!inputValue.trim() || isLoading}
            >
              发送
            </Button>
          )}
        </Input.Group>
      </div>
    </Content>
    </>
  )
}

