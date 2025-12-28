import React, { useState, useEffect } from 'react'
import { Layout, Menu, Button, Input, Typography, Space, Tag, Popconfirm } from 'antd'
import { 
  DeleteOutlined,
  EditOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  MessageOutlined,
  PlusOutlined,
  LogoutOutlined,
  UserOutlined,
  CrownOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons'
import { useChatStore } from '../store/useChatStore'
import { useAuthStore } from '../store/useAuthStore'
import { IndexManagement } from './IndexManagement'

const { Sider } = Layout
const { Text } = Typography

export const ChatSidebar = () => {
  const { 
    sessions, 
    currentSessionId, 
    databaseInfo,
    fetchSessions, 
    createSession, 
    switchSession, 
    deleteSession,
    initialize
  } = useChatStore()
  
  const { user, logout } = useAuthStore()
  const [searchText, setSearchText] = useState('')
  const [showIndexManagement, setShowIndexManagement] = useState(false)

  useEffect(() => {
    if (user) {
      initialize()
    }
  }, [user])

  const filteredSessions = sessions.filter(session =>
    session.title.toLowerCase().includes(searchText.toLowerCase())
  )

  const menuItems = [
    {
      key: 'new',
      icon: <PlusOutlined />,
      label: '新建对话',
      onClick: () => createSession()
    },
    ...filteredSessions.map(session => ({
      key: session.id,
      icon: <MessageOutlined />,
      label: (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {session.title}
          </span>
          <Space size="small" onClick={(e) => e.stopPropagation()}>
            <Popconfirm
              title="确定删除此会话吗？"
              onConfirm={() => deleteSession(session.id)}
              onCancel={(e) => e.stopPropagation()}
            >
              <Button
                type="text"
                size="small"
                icon={<DeleteOutlined />}
                danger
                onClick={(e) => e.stopPropagation()}
              />
            </Popconfirm>
          </Space>
        </div>
      )
    }))
  ]

  return (
    <Sider 
      width={280} 
      style={{ 
        background: '#fff',
        borderRight: '1px solid #f0f0f0'
      }}
    >
      <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0' }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <DatabaseOutlined style={{ fontSize: '20px', color: '#1890ff' }} />
            <Text strong style={{ fontSize: '18px' }}>AskDB</Text>
          </div>
          {user && (
            <div>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                欢迎, {user.username}
              </Text>
              <Tag 
                icon={user.user_type === 'manager' ? <CrownOutlined /> : <UserOutlined />}
                color={user.user_type === 'manager' ? 'gold' : 'blue'}
                style={{ marginLeft: '8px' }}
              >
                {user.user_type === 'manager' ? '管理员' : '员工'}
              </Tag>
            </div>
          )}
        </Space>
      </div>

      <div style={{ padding: '12px', borderBottom: '1px solid #f0f0f0' }}>
        <Input
          placeholder="搜索会话..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
        />
      </div>

      <Menu
        mode="inline"
        selectedKeys={currentSessionId ? [currentSessionId] : []}
        items={menuItems}
        onClick={({ key }) => {
          if (key !== 'new') {
            switchSession(key)
          }
        }}
        style={{ borderRight: 0, height: 'calc(100vh - 200px)', overflow: 'auto' }}
      />

      <div style={{ 
        padding: '16px', 
        borderTop: '1px solid #f0f0f0',
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        background: '#fff'
      }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {databaseInfo?.connected ? (
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: '14px' }} />
            ) : (
              <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: '14px' }} />
            )}
            <Text type={databaseInfo?.connected ? 'success' : 'danger'} style={{ fontSize: '12px' }}>
              {databaseInfo?.connected ? '数据库已连接' : '数据库未连接'}
            </Text>
          </div>
          {databaseInfo && (
            <Text type="secondary" style={{ fontSize: '11px' }}>
              类型: {databaseInfo.database_type} | 表数: {databaseInfo.table_count || 0}
            </Text>
          )}
          {user && user.user_type === 'manager' && (
            <Button
              type="default"
              icon={<ThunderboltOutlined />}
              onClick={() => setShowIndexManagement(true)}
              block
              style={{ marginTop: '8px' }}
            >
              索引管理
            </Button>
          )}
          <Button
            type="text"
            danger
            icon={<LogoutOutlined />}
            onClick={logout}
            block
            style={{ marginTop: '8px' }}
          >
            登出
          </Button>
        </Space>
      </div>

      {/* 索引管理对话框 */}
      <IndexManagement
        visible={showIndexManagement}
        onClose={() => setShowIndexManagement(false)}
      />
    </Sider>
  )
}

