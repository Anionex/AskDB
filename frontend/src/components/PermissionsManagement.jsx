import React, { useState, useEffect } from 'react'
import { Modal, Button, Typography, Space, message, Alert, Spin, Switch, Tooltip, Tabs } from 'antd'
import { SafetyOutlined, SaveOutlined, ReloadOutlined, QuestionCircleOutlined, CodeOutlined, InfoCircleOutlined } from '@ant-design/icons'
import axios from 'axios'

const { Title, Text, Paragraph } = Typography

export const PermissionsManagement = ({ visible, onClose }) => {
  const [yamlContent, setYamlContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isEnabled, setIsEnabled] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [error, setError] = useState(null)

  // 加载配置
  const loadConfig = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const token = localStorage.getItem('askdb_token')
      const response = await axios.get('/api/protected/admin/permissions', {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (response.data.success) {
        setYamlContent(response.data.yaml_content || '')
        setOriginalContent(response.data.yaml_content || '')
        setIsEnabled(response.data.enabled || false)
        setHasChanges(false)
      } else {
        setError(response.data.message || '加载配置失败')
      }
    } catch (error) {
      console.error('Failed to load permissions config:', error)
      if (error.response?.status === 403) {
        setError('只有管理员可以查看权限配置')
      } else {
        setError('加载配置失败: ' + (error.response?.data?.detail || error.message))
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (visible) {
      loadConfig()
    }
  }, [visible])

  // 检测内容变化
  useEffect(() => {
    setHasChanges(yamlContent !== originalContent)
  }, [yamlContent, originalContent])

  // 保存配置
  const handleSave = async () => {
    setIsSaving(true)
    setError(null)
    try {
      const token = localStorage.getItem('askdb_token')
      const response = await axios.put(
        '/api/protected/admin/permissions',
        { yaml_content: yamlContent },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      
      if (response.data.success) {
        message.success('权限配置已保存并生效')
        setOriginalContent(yamlContent)
        setIsEnabled(response.data.enabled || false)
        setHasChanges(false)
      } else {
        setError(response.data.message || '保存失败')
        message.error(response.data.message || '保存失败')
      }
    } catch (error) {
      console.error('Failed to save permissions config:', error)
      const errorMsg = error.response?.data?.detail || error.message
      setError('保存失败: ' + errorMsg)
      message.error('保存失败: ' + errorMsg)
    } finally {
      setIsSaving(false)
    }
  }

  // 重新加载配置
  const handleReload = async () => {
    if (hasChanges) {
      Modal.confirm({
        title: '确认重新加载',
        content: '您有未保存的更改，重新加载将丢失这些更改。确定要继续吗？',
        okText: '确定',
        cancelText: '取消',
        onOk: loadConfig
      })
    } else {
      loadConfig()
    }
  }

  // 关闭时检查未保存的更改
  const handleClose = () => {
    if (hasChanges) {
      Modal.confirm({
        title: '未保存的更改',
        content: '您有未保存的更改，确定要关闭吗？',
        okText: '确定关闭',
        cancelText: '继续编辑',
        onOk: onClose
      })
    } else {
      onClose()
    }
  }

  const helpContent = (
    <div style={{ maxWidth: 400, color: 'rgba(255, 255, 255, 0.85)' }}>
      <div style={{ fontWeight: 'bold', fontSize: 14, marginBottom: 8 }}>权限配置说明</div>
      <div style={{ fontSize: 12 }}>
        <strong>permissions:</strong> 表级权限配置列表
        <ul style={{ marginLeft: 16, marginTop: 8, paddingLeft: 0 }}>
          <li><strong>table:</strong> 表名</li>
          <li><strong>roles:</strong> 角色权限列表
            <ul style={{ paddingLeft: 16 }}>
              <li><strong>user_type:</strong> 用户类型 (manager/teacher/student)</li>
              <li><strong>allowed_operations:</strong> 允许的操作 [SELECT, INSERT, UPDATE, DELETE]</li>
              <li><strong>allowed_columns:</strong> 允许访问的列 (null=所有列)</li>
              <li><strong>row_filter:</strong> 行级过滤条件，支持 {'{username}'} 占位符</li>
              <li><strong>forbidden_columns:</strong> 禁止访问的列</li>
            </ul>
          </li>
        </ul>
      </div>
      <div style={{ fontSize: 12, marginTop: 12 }}>
        <strong>global_settings:</strong> 全局设置
        <ul style={{ marginLeft: 16, marginTop: 8, paddingLeft: 0 }}>
          <li><strong>enabled:</strong> 是否启用权限控制</li>
          <li><strong>log_checks:</strong> 是否记录权限检查日志</li>
          <li><strong>verbose_errors:</strong> 是否返回详细错误信息</li>
        </ul>
      </div>
    </div>
  )

  return (
    <Modal
      title={
        <Space>
          <SafetyOutlined />
          <span>权限配置管理</span>
          <Tooltip title={helpContent} overlayStyle={{ maxWidth: 450 }}>
            <QuestionCircleOutlined style={{ color: '#1890ff', cursor: 'help' }} />
          </Tooltip>
        </Space>
      }
      open={visible}
      onCancel={handleClose}
      width={900}
      footer={[
        <Button key="reload" icon={<ReloadOutlined />} onClick={handleReload} disabled={isLoading || isSaving}>
          重新加载
        </Button>,
        <Button key="close" onClick={handleClose}>
          关闭
        </Button>,
        <Button 
          key="save" 
          type="primary" 
          icon={<SaveOutlined />} 
          onClick={handleSave}
          loading={isSaving}
          disabled={!hasChanges || isLoading}
        >
          保存配置
        </Button>
      ]}
      style={{ top: 20 }}
    >
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin tip="加载配置中..." />
        </div>
      ) : (
        <>
          {/* 状态信息 */}
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Text>权限控制状态:</Text>
              <Text strong style={{ color: isEnabled ? '#52c41a' : '#ff4d4f' }}>
                {isEnabled ? '已启用' : '已禁用'}
              </Text>
              <Tooltip title="在配置文件中修改 global_settings.enabled 来启用/禁用权限控制">
                <InfoCircleOutlined style={{ color: '#999' }} />
              </Tooltip>
            </Space>
            {hasChanges && (
              <Text type="warning">* 有未保存的更改</Text>
            )}
          </div>

          {/* 错误提示 */}
          {error && (
            <Alert
              message="错误"
              description={error}
              type="error"
              showIcon
              closable
              onClose={() => setError(null)}
              style={{ marginBottom: 16 }}
            />
          )}

          {/* YAML 编辑器 */}
          <Tabs
            items={[
              {
                key: 'editor',
                label: (
                  <Space>
                    <CodeOutlined />
                    <span>YAML 编辑器</span>
                  </Space>
                ),
                children: (
                  <div>
                    <textarea
                      value={yamlContent}
                      onChange={(e) => setYamlContent(e.target.value)}
                      style={{
                        width: '100%',
                        height: '450px',
                        fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                        fontSize: '13px',
                        lineHeight: '1.5',
                        padding: '12px',
                        border: '1px solid #d9d9d9',
                        borderRadius: '4px',
                        resize: 'vertical',
                        backgroundColor: '#fafafa'
                      }}
                      placeholder="# 在此编辑权限配置..."
                      spellCheck={false}
                    />
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        提示: 使用 Tab 键缩进，保持 YAML 格式正确。配置保存后会立即生效。
                      </Text>
                    </div>
                  </div>
                )
              },
              {
                key: 'help',
                label: (
                  <Space>
                    <QuestionCircleOutlined />
                    <span>配置说明</span>
                  </Space>
                ),
                children: (
                  <div style={{ padding: 16, background: '#f5f5f5', borderRadius: 4, maxHeight: 450, overflow: 'auto' }}>
                    <Title level={5}>权限配置格式说明</Title>
                    
                    <Title level={5} style={{ marginTop: 16 }}>1. 表级权限 (permissions)</Title>
                    <Paragraph>
                      <pre style={{ background: '#fff', padding: 12, borderRadius: 4, fontSize: 12 }}>
{`permissions:
  - table: students          # 表名
    roles:
      - user_type: "manager" # 用户类型
        allowed_operations: ["SELECT", "INSERT", "UPDATE", "DELETE"]
        allowed_columns: null    # null = 所有列
        row_filter: null         # null = 所有行
        forbidden_columns: []    # 禁止访问的列
      
      - user_type: "student"
        allowed_operations: ["SELECT", "UPDATE"]
        row_filter: "sid = {username}"  # 只能访问自己的数据`}
                      </pre>
                    </Paragraph>

                    <Title level={5} style={{ marginTop: 16 }}>2. 默认权限 (default_permission)</Title>
                    <Paragraph>
                      <pre style={{ background: '#fff', padding: 12, borderRadius: 4, fontSize: 12 }}>
{`default_permission:
  allowed_operations: []  # 默认不允许任何操作
  allowed_columns: []
  row_filter: "1=0"       # 默认不返回任何数据
  forbidden_columns: null`}
                      </pre>
                    </Paragraph>

                    <Title level={5} style={{ marginTop: 16 }}>3. 全局设置 (global_settings)</Title>
                    <Paragraph>
                      <pre style={{ background: '#fff', padding: 12, borderRadius: 4, fontSize: 12 }}>
{`global_settings:
  enabled: true           # 是否启用权限控制
  log_checks: true        # 是否记录权限检查日志
  verbose_errors: true    # 是否返回详细错误信息
  access_denied_message: "您没有权限访问此数据"`}
                      </pre>
                    </Paragraph>

                    <Title level={5} style={{ marginTop: 16 }}>4. 用户类型说明</Title>
                    <Paragraph>
                      <ul>
                        <li><strong>manager:</strong> 管理员，通常拥有所有权限</li>
                        <li><strong>teacher:</strong> 教师，可以访问与自己相关的数据</li>
                        <li><strong>student:</strong> 学生，只能访问自己的数据</li>
                      </ul>
                    </Paragraph>

                    <Title level={5} style={{ marginTop: 16 }}>5. 行级过滤 (row_filter)</Title>
                    <Paragraph>
                      <ul>
                        <li>使用 SQL WHERE 子句语法</li>
                        <li><code>{'{username}'}</code> 会被替换为当前用户的用户名（学号/工号）</li>
                        <li>例如: <code>sid = {'{username}'}</code> 表示只能访问 sid 等于用户学号的行</li>
                      </ul>
                    </Paragraph>
                  </div>
                )
              }
            ]}
          />

          {/* 警告信息 */}
          <Alert
            message="注意事项"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                <li>配置保存后会立即生效，请谨慎修改</li>
                <li>原配置会自动备份为 permissions.yaml.bak</li>
                <li>如果配置格式错误，保存将失败</li>
                <li>建议在测试环境验证后再应用到生产环境</li>
              </ul>
            }
            type="warning"
            showIcon
            style={{ marginTop: 16 }}
          />
        </>
      )}
    </Modal>
  )
}
