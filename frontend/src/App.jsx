import React, { useEffect, useState } from 'react'
import { Layout, Form, Input, Button, Card, Select, Space, message, Typography } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, DatabaseOutlined, UserSwitchOutlined, CrownOutlined } from '@ant-design/icons'
import axios from 'axios'
import { useAuthStore } from './store/useAuthStore'
import { useChatStore } from './store/useChatStore'
import { ChatSidebar } from './components/ChatSidebar'
import { ChatArea } from './components/ChatArea'
import './App.css'

const { Content } = Layout
const { Title, Text } = Typography
const API_BASE = 'http://localhost:8000/api'

function App() {
  const { user, isLoggedIn, checkAuth, login, logout } = useAuthStore()
  const { initialize, fetchDatabaseStatus } = useChatStore()
  const [currentView, setCurrentView] = useState('login')
  const [isSendingCode, setIsSendingCode] = useState(false)
  const [codeSent, setCodeSent] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [registerForm] = Form.useForm()
  const [loginForm] = Form.useForm()

  useEffect(() => {
    checkAuth().then((authenticated) => {
      if (authenticated) {
        initialize()
        fetchDatabaseStatus()
      }
    })
  }, [])

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [countdown])

  const handleLogin = async (values) => {
    const result = await login(values.username, values.password)
    if (result.success) {
      message.success('登录成功')
      initialize()
      fetchDatabaseStatus()
    } else {
      message.error(result.message || '登录失败')
    }
  }

  const handleSendCode = async () => {
    const email = registerForm.getFieldValue('email')
    if (!email) {
      message.error('请输入邮箱地址')
      return
    }

    setIsSendingCode(true)
    try {
      const response = await axios.post(`${API_BASE}/auth/send-code`, { email })
      if (response.data.success) {
        setCodeSent(true)
        setCountdown(60)
        message.success('验证码已发送到您的邮箱')
      } else {
        message.error(response.data.message)
      }
    } catch (error) {
      message.error(error.response?.data?.message || '发送验证码失败')
    } finally {
      setIsSendingCode(false)
    }
  }

  const handleRegister = async (values) => {
    try {
      const response = await axios.post(`${API_BASE}/auth/register`, {
        username: values.username,
        email: values.email,
        password: values.password,
        user_type: values.userType,
        verification_code: values.verificationCode
      })

      if (response.data.success) {
        message.success('注册成功！请登录')
        setCurrentView('login')
        registerForm.resetFields()
        setCodeSent(false)
        setCountdown(0)
      } else {
        message.error(response.data.message)
      }
    } catch (error) {
      message.error(error.response?.data?.message || '注册失败')
    }
  }

  if (!isLoggedIn) {
    return (
      <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
        <Content style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          padding: '24px'
        }}>
          <Card 
            style={{ width: '100%', maxWidth: 400 }}
            title={
              <div style={{ textAlign: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginBottom: '8px' , marginTop: '40px'}}>
                  <DatabaseOutlined style={{ fontSize: '32px', color: '#1890ff' }} />
                  <Title level={2} style={{ margin: 0 }}>AskDB</Title>
                </div>
                <Text type="secondary">
                  {currentView === 'login' ? '智能数据库助手 - 请登录' : '创建新账户'}
                </Text>
              </div>
            }
          >
            {currentView === 'login' ? (
              <Form
                form={loginForm}
                onFinish={handleLogin}
                layout="vertical"
                size="large"
              >
                <Form.Item
                  name="username"
                  rules={[{ required: true, message: '请输入用户名' }]}
                >
                  <Input 
                    prefix={<UserOutlined />} 
                    placeholder="用户名"
                  />
                </Form.Item>
                <Form.Item
                  name="password"
                  rules={[{ required: true, message: '请输入密码' }]}
                >
                  <Input.Password 
                    prefix={<LockOutlined />} 
                    placeholder="密码"
                  />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" block>
                    登录
                  </Button>
                </Form.Item>
                <div style={{ textAlign: 'center' }}>
                  <Button type="link" onClick={() => setCurrentView('register')}>
                    还没有账户？立即注册
                  </Button>
                </div>
              </Form>
            ) : (
              <Form
                form={registerForm}
                onFinish={handleRegister}
                layout="vertical"
                size="large"
              >
                <Form.Item
                  label="用户类型"
                  name="userType"
                  initialValue="student"
                  rules={[{ required: true, message: '请选择用户类型' }]}
                >
                  <Select>
                    <Select.Option value="student">
                      <Space>
                        <UserOutlined />
                        <span>学生</span>
                      </Space>
                    </Select.Option>
                    <Select.Option value="teacher">
                      <Space>
                        <UserSwitchOutlined />
                        <span>教师</span>
                      </Space>
                    </Select.Option>
                    <Select.Option value="manager">
                      <Space>
                        <CrownOutlined />
                        <span>管理员</span>
                      </Space>
                    </Select.Option>
                  </Select>
                </Form.Item>
                <Form.Item
                  name="username"
                  label="学号/工号"
                  rules={[
                    { required: true, message: '请输入学号或工号' },
                    { pattern: /^\d+$/, message: '学号/工号必须为纯数字' }
                  ]}
                  tooltip={
                    registerForm.getFieldValue('userType') === 'student' 
                      ? '请输入学号（纯数字，如：20230101）' 
                      : registerForm.getFieldValue('userType') === 'teacher'
                      ? '请输入工号（纯数字，如：1001）'
                      : '请输入用户名'
                  }
                >
                  <Input 
                    prefix={<UserOutlined />} 
                    placeholder={
                      registerForm.getFieldValue('userType') === 'student' 
                        ? '学号（如：20230101）' 
                        : registerForm.getFieldValue('userType') === 'teacher'
                        ? '工号（如：1001）'
                        : 'admin'
                    }
                  />
                </Form.Item>
                <Form.Item
                  name="email"
                  rules={[
                    { required: true, message: '请输入邮箱地址' },
                    { type: 'email', message: '请输入有效的邮箱地址' }
                  ]}
                >
                  <Space.Compact style={{ width: '100%' }}>
                    <Input 
                      prefix={<MailOutlined />} 
                      placeholder="邮箱地址"
                      disabled={codeSent}
                    />
                    <Button
                      onClick={handleSendCode}
                      disabled={isSendingCode || countdown > 0 || !registerForm.getFieldValue('email')}
                    >
                      {countdown > 0 ? `${countdown}s` : isSendingCode ? '发送中...' : '获取验证码'}
                    </Button>
                  </Space.Compact>
                </Form.Item>
                <Form.Item
                  name="verificationCode"
                  rules={[{ required: true, message: '请输入验证码' }]}
                >
                  <Input placeholder="请输入6位验证码" maxLength={6} />
                </Form.Item>
                <Form.Item
                  name="password"
                  rules={[
                    { required: true, message: '请输入密码' },
                    { min: 6, message: '密码长度至少6位' }
                  ]}
                >
                  <Input.Password prefix={<LockOutlined />} placeholder="至少6位密码" />
                </Form.Item>
                <Form.Item
                  name="confirmPassword"
                  dependencies={['password']}
                  rules={[
                    { required: true, message: '请确认密码' },
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (!value || getFieldValue('password') === value) {
                          return Promise.resolve()
                        }
                        return Promise.reject(new Error('两次输入的密码不一致'))
                      }
                    })
                  ]}
                >
                  <Input.Password prefix={<LockOutlined />} placeholder="请再次输入密码" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" block>
                    注册账户
                  </Button>
                </Form.Item>
                <div style={{ textAlign: 'center' }}>
                  <Button type="link" onClick={() => setCurrentView('login')}>
                    返回登录
                  </Button>
                </div>
              </Form>
            )}
          </Card>
        </Content>
      </Layout>
    )
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <ChatSidebar />
      <ChatArea />
    </Layout>
  )
}

export default App
