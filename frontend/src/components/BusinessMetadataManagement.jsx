import React, { useState, useEffect } from 'react'
import { Modal, Button, Typography, Space, message, Alert, Spin, Table, Form, Input, Popconfirm, Tooltip, Tabs } from 'antd'
import { BookOutlined, SaveOutlined, ReloadOutlined, PlusOutlined, DeleteOutlined, EditOutlined, DownloadOutlined, CodeOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import axios from 'axios'

const { Title, Text } = Typography
const { TextArea } = Input

export const BusinessMetadataManagement = ({ visible, onClose }) => {
  const [data, setData] = useState({ business_terms: [] })
  const [originalData, setOriginalData] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [error, setError] = useState(null)
  const [editingKey, setEditingKey] = useState('')
  const [form] = Form.useForm()
  const [activeTab, setActiveTab] = useState('table')
  const [jsonContent, setJsonContent] = useState('')

  // 加载配置
  const loadConfig = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const token = localStorage.getItem('askdb_token')
      const response = await axios.get('http://localhost:8000/api/protected/admin/business-metadata', {
        headers: { Authorization: `Bearer ${token}` }
      })

      if (response.data.success) {
        const loadedData = response.data.data || { business_terms: [] }
        setData(loadedData)
        setOriginalData(JSON.parse(JSON.stringify(loadedData)))
        setJsonContent(JSON.stringify(loadedData, null, 2))
        setHasChanges(false)
      } else {
        setError(response.data.message || '加载配置失败')
      }
    } catch (error) {
      console.error('Failed to load business metadata:', error)
      if (error.response?.status === 403) {
        setError('只有管理员可以查看术语配置')
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
    if (originalData) {
      setHasChanges(JSON.stringify(data) !== JSON.stringify(originalData))
    }
  }, [data, originalData])

  // 保存配置
  const handleSave = async () => {
    setIsSaving(true)
    setError(null)
    try {
      const token = localStorage.getItem('askdb_token')

      // 如果是 JSON 编辑模式，先解析 JSON
      let dataToSave = data
      if (activeTab === 'json') {
        try {
          dataToSave = JSON.parse(jsonContent)
          setData(dataToSave)
        } catch (e) {
          setError('JSON 格式错误: ' + e.message)
          setIsSaving(false)
          return
        }
      }

      const response = await axios.put(
        'http://localhost:8000/api/protected/admin/business-metadata',
        { data: dataToSave },
        { headers: { Authorization: `Bearer ${token}` } }
      )

      if (response.data.success) {
        message.success('术语配置已保存')
        setOriginalData(JSON.parse(JSON.stringify(dataToSave)))
        setHasChanges(false)
      } else {
        setError(response.data.message || '保存失败')
        message.error(response.data.message || '保存失败')
      }
    } catch (error) {
      console.error('Failed to save business metadata:', error)
      const errorMsg = error.response?.data?.detail || error.message
      setError('保存失败: ' + errorMsg)
      message.error('保存失败: ' + errorMsg)
    } finally {
      setIsSaving(false)
    }
  }

  // 导出配置
  const handleExport = async () => {
    try {
      const token = localStorage.getItem('askdb_token')
      const response = await axios.get(
        'http://localhost:8000/api/protected/admin/business-metadata/export',
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      )

      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'business_metadata.json')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      message.success('配置导出成功')
    } catch (error) {
      console.error('Failed to export:', error)
      message.error('导出失败: ' + (error.response?.data?.detail || error.message))
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

  // 编辑相关函数
  const isEditing = (record) => record.name === editingKey

  const edit = (record) => {
    form.setFieldsValue({
      name: '',
      definition: '',
      formula: '',
      related_tables: '',
      related_columns: '',
      ...record,
      related_tables: record.related_tables?.join(', ') || '',
      related_columns: record.related_columns?.join(', ') || ''
    })
    setEditingKey(record.name)
  }

  const cancel = () => {
    setEditingKey('')
  }

  const save = async (originalName) => {
    try {
      const row = await form.validateFields()
      const newData = [...data.business_terms]
      const index = newData.findIndex((item) => originalName === item.name)

      const newItem = {
        name: row.name,
        definition: row.definition,
        formula: row.formula || '',
        related_tables: row.related_tables ? row.related_tables.split(',').map(s => s.trim()).filter(Boolean) : [],
        related_columns: row.related_columns ? row.related_columns.split(',').map(s => s.trim()).filter(Boolean) : []
      }

      if (index > -1) {
        newData.splice(index, 1, newItem)
      } else {
        newData.push(newItem)
      }

      setData({ ...data, business_terms: newData })
      setJsonContent(JSON.stringify({ ...data, business_terms: newData }, null, 2))
      setEditingKey('')
    } catch (errInfo) {
      console.log('Validate Failed:', errInfo)
    }
  }

  const handleDelete = (name) => {
    const newTerms = data.business_terms.filter(item => item.name !== name)
    setData({ ...data, business_terms: newTerms })
    setJsonContent(JSON.stringify({ ...data, business_terms: newTerms }, null, 2))
  }

  const handleAdd = () => {
    const newTerm = {
      name: `新术语_${Date.now()}`,
      definition: '',
      formula: '',
      related_tables: [],
      related_columns: []
    }
    const newTerms = [...data.business_terms, newTerm]
    setData({ ...data, business_terms: newTerms })
    setJsonContent(JSON.stringify({ ...data, business_terms: newTerms }, null, 2))
    edit(newTerm)
  }

  // 表格列定义
  const columns = [
    {
      title: <span><span style={{ color: '#ff4d4f' }}>*</span> 术语名称</span>,
      dataIndex: 'name',
      key: 'name',
      width: 150,
      editable: true,
      render: (text, record) => {
        const editing = isEditing(record)
        return editing ? (
          <Form.Item
            name="name"
            style={{ margin: 0 }}
            rules={[{ required: true, message: '请输入术语名称' }]}
          >
            <Input placeholder="如: GMV、DAU" />
          </Form.Item>
        ) : (
          <Text strong>{text}</Text>
        )
      }
    },
    {
      title: <Tooltip title="可选：术语的中英文解释"><span>定义 <QuestionCircleOutlined style={{ fontSize: 12, color: '#999' }} /></span></Tooltip>,
      dataIndex: 'definition',
      key: 'definition',
      width: 250,
      editable: true,
      render: (text, record) => {
        const editing = isEditing(record)
        return editing ? (
          <Form.Item name="definition" style={{ margin: 0 }}>
            <TextArea rows={2} placeholder="如: Gross Merchandise Volume (商品交易总额)" />
          </Form.Item>
        ) : (
          <Text style={{ fontSize: 12 }}>{text || <Text type="secondary">-</Text>}</Text>
        )
      }
    },
    {
      title: <Tooltip title="可选：推荐填写具体 SQL 表达式，不确定时可填写一般描述"><span>计算公式 <QuestionCircleOutlined style={{ fontSize: 12, color: '#999' }} /></span></Tooltip>,
      dataIndex: 'formula',
      key: 'formula',
      width: 220,
      editable: true,
      render: (text, record) => {
        const editing = isEditing(record)
        return editing ? (
          <Form.Item name="formula" style={{ margin: 0 }} tooltip="推荐填写具体SQL，如不确定可写一般形式">
            <TextArea rows={2} placeholder="推荐: sum(amount)&#10;或一般形式: 销售额总和" />
          </Form.Item>
        ) : (
          text ? (
            <code style={{ fontSize: 11, background: '#f5f5f5', padding: '2px 4px', borderRadius: 2 }}>
              {text}
            </code>
          ) : <Text type="secondary">-</Text>
        )
      }
    },
    {
      title: <Tooltip title="可选：推荐填写具体表名，不确定时可留空"><span>关联表 <QuestionCircleOutlined style={{ fontSize: 12, color: '#999' }} /></span></Tooltip>,
      dataIndex: 'related_tables',
      key: 'related_tables',
      width: 150,
      render: (tables, record) => {
        const editing = isEditing(record)
        return editing ? (
          <Form.Item name="related_tables" style={{ margin: 0 }}>
            <Input placeholder="如: orders, users" />
          </Form.Item>
        ) : (
          tables?.length > 0 ? (
            <Text type="secondary" style={{ fontSize: 11 }}>
              {tables.join(', ')}
            </Text>
          ) : <Text type="secondary">-</Text>
        )
      }
    },
    {
      title: <Tooltip title="可选：推荐填写具体列名，不确定时可留空"><span>关联列 <QuestionCircleOutlined style={{ fontSize: 12, color: '#999' }} /></span></Tooltip>,
      dataIndex: 'related_columns',
      key: 'related_columns',
      width: 150,
      render: (columns, record) => {
        const editing = isEditing(record)
        return editing ? (
          <Form.Item name="related_columns" style={{ margin: 0 }}>
            <Input placeholder="如: amount, user_id" />
          </Form.Item>
        ) : (
          columns?.length > 0 ? (
            <Text type="secondary" style={{ fontSize: 11 }}>
              {columns.join(', ')}
            </Text>
          ) : <Text type="secondary">-</Text>
        )
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right',
      render: (_, record) => {
        const editing = isEditing(record)
        return editing ? (
          <Space size="small">
            <Button type="link" size="small" onClick={() => save(record.name)}>
              保存
            </Button>
            <Button type="link" size="small" onClick={cancel}>
              取消
            </Button>
          </Space>
        ) : (
          <Space size="small">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => edit(record)}
              disabled={editingKey !== ''}
            />
            <Popconfirm
              title="确定删除此术语吗？"
              onConfirm={() => handleDelete(record.name)}
            >
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                disabled={editingKey !== ''}
              />
            </Popconfirm>
          </Space>
        )
      }
    }
  ]

  const handleJsonChange = (e) => {
    setJsonContent(e.target.value)
    try {
      const parsed = JSON.parse(e.target.value)
      if (parsed.business_terms) {
        setData(parsed)
      }
    } catch {
      // JSON 解析失败时不更新 data
    }
  }

  const helpContent = (
    <div style={{ maxWidth: 420, color: 'rgba(255, 255, 255, 0.85)' }}>
      <div style={{ fontWeight: 'bold', fontSize: 14, marginBottom: 8 }}>术语配置说明</div>
      <div style={{ fontSize: 12 }}>
        <strong>字段说明:</strong>
        <ul style={{ marginLeft: 16, marginTop: 8, paddingLeft: 0 }}>
          <li><strong style={{ color: '#ff7875' }}>* name (必填):</strong> 术语名称（如 GMV、DAU）</li>
          <li><strong>definition (可选):</strong> 术语定义和说明</li>
          <li><strong>formula (可选):</strong> 计算公式</li>
          <li><strong>related_tables (可选):</strong> 关联的数据库表</li>
          <li><strong>related_columns (可选):</strong> 关联的数据库列</li>
        </ul>
      </div>
      <div style={{ fontSize: 12, marginTop: 12, padding: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: 4 }}>
        <strong>填写建议:</strong>
        <ul style={{ marginLeft: 16, marginTop: 4, paddingLeft: 0, marginBottom: 0 }}>
          <li>推荐填写具体的 SQL 表达式和列名</li>
          <li>如不确定具体列名，可填写一般描述</li>
          <li>例如: "sum(销售额)" 或 "订单金额总和"</li>
        </ul>
      </div>
    </div>
  )

  return (
    <Modal
      title={
        <Space>
          <BookOutlined />
          <span>术语配置管理</span>
          <Tooltip title={helpContent} overlayStyle={{ maxWidth: 450 }}>
            <QuestionCircleOutlined style={{ color: '#1890ff', cursor: 'help' }} />
          </Tooltip>
        </Space>
      }
      open={visible}
      onCancel={handleClose}
      width={1100}
      footer={[
        <Button key="export" icon={<DownloadOutlined />} onClick={handleExport} disabled={isLoading || isSaving}>
          导出
        </Button>,
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
              <Text>术语数量:</Text>
              <Text strong>{data.business_terms?.length || 0}</Text>
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

          {/* 编辑器 */}
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'table',
                label: (
                  <Space>
                    <EditOutlined />
                    <span>表格编辑</span>
                  </Space>
                ),
                children: (
                  <div>
                    <div style={{ marginBottom: 16 }}>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={handleAdd}
                        disabled={editingKey !== ''}
                      >
                        添加术语
                      </Button>
                    </div>
                    <Form form={form} component={false}>
                      <Table
                        dataSource={data.business_terms}
                        columns={columns}
                        rowKey="name"
                        pagination={false}
                        scroll={{ x: 1000, y: 400 }}
                        size="small"
                        bordered
                      />
                    </Form>
                  </div>
                )
              },
              {
                key: 'json',
                label: (
                  <Space>
                    <CodeOutlined />
                    <span>JSON 编辑</span>
                  </Space>
                ),
                children: (
                  <div>
                    <textarea
                      value={jsonContent}
                      onChange={handleJsonChange}
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
                      placeholder="// 在此编辑 JSON 配置..."
                      spellCheck={false}
                    />
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        提示: 直接编辑 JSON 内容，保持格式正确。
                      </Text>
                    </div>
                  </div>
                )
              }
            ]}
          />

          {/* 提示信息 */}
          <Alert
            message="填写提示"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                <li><strong>必填字段:</strong> 仅"术语名称"为必填，其他均为可选</li>
                <li><strong>计算公式:</strong> 推荐填写具体 SQL（如 <code>sum(order_amount)</code>），不确定时可填写一般描述（如"订单金额总和"）</li>
                <li><strong>关联表/列:</strong> 推荐填写具体名称以提高匹配精度，不确定时可留空</li>
                <li>配置保存后会立即生效，原配置自动备份为 .bak 文件</li>
              </ul>
            }
            type="info"
            showIcon
            style={{ marginTop: 16 }}
          />
        </>
      )}
    </Modal>
  )
}
