import React, { useState, useEffect } from 'react'
import { Modal, Button, Progress, Typography, Statistic, Row, Col, Space, message, Alert, Input, Select, Card, Tag, Divider, List, Empty, Spin } from 'antd'
import { DatabaseOutlined, SyncOutlined, CheckCircleOutlined, CloseCircleOutlined, SearchOutlined, TableOutlined, ColumnWidthOutlined, FileTextOutlined } from '@ant-design/icons'
import axios from 'axios'

const { Title, Text } = Typography
const { Search } = Input

export const IndexManagement = ({ visible, onClose }) => {
  const [indexStatus, setIndexStatus] = useState({
    is_indexing: false,
    progress: 0,
    total: 0,
    current_step: '',
    completed: false,
    error: null,
    index_stats: { tables: 0, columns: 0, business_terms: 0 }
  })
  const [isTriggering, setIsTriggering] = useState(false)
  
  // 搜索相关状态
  const [searchQuery, setSearchQuery] = useState('')
  const [searchTypes, setSearchTypes] = useState(['table', 'column', 'business_term'])
  const [searchResults, setSearchResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  // 轮询索引状态
  useEffect(() => {
    if (!visible) return

    const fetchStatus = async () => {
      try {
        const token = localStorage.getItem('askdb_token')
        const response = await axios.get('http://localhost:8000/api/protected/index/status', {
          headers: { Authorization: `Bearer ${token}` }
        })
        setIndexStatus(response.data)
      } catch (error) {
        console.error('Failed to fetch index status:', error)
      }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 2000) // 每2秒刷新一次

    return () => clearInterval(interval)
  }, [visible])

  const handleTriggerIndex = async () => {
    setIsTriggering(true)
    try {
      const token = localStorage.getItem('askdb_token')
      const response = await axios.post(
        'http://localhost:8000/api/protected/index/trigger',
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      )
      
      if (response.data.success) {
        message.success(response.data.message)
      } else {
        message.error(response.data.message)
      }
    } catch (error) {
      if (error.response?.status === 403) {
        message.error('只有管理员可以触发索引')
      } else {
        message.error('触发索引失败: ' + (error.response?.data?.message || error.message))
      }
    } finally {
      setIsTriggering(false)
    }
  }

  const handleClearIndex = async () => {
    Modal.confirm({
      title: '确认清空索引',
      content: '这将删除所有已建立的索引数据，之后需要重新索引。确定要继续吗？',
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const token = localStorage.getItem('askdb_token')
          await axios.delete('http://localhost:8000/api/protected/index/clear', {
            headers: { Authorization: `Bearer ${token}` }
          })
          message.success('索引已清空')
          // 刷新状态
          const response = await axios.get('http://localhost:8000/api/protected/index/status', {
            headers: { Authorization: `Bearer ${token}` }
          })
          setIndexStatus(response.data)
        } catch (error) {
          if (error.response?.status === 403) {
            message.error('只有管理员可以清空索引')
          } else {
            message.error('清空索引失败')
          }
        }
      }
    })
  }

  const handleSearch = async (query) => {
    if (!query || !query.trim()) {
      message.warning('请输入搜索关键词')
      return
    }

    setIsSearching(true)
    setHasSearched(true)
    
    try {
      const token = localStorage.getItem('askdb_token')
      const response = await axios.post(
        'http://localhost:8000/api/protected/vector/search',
        {
          query: query.trim(),
          top_k: 10,
          search_types: searchTypes.length > 0 ? searchTypes : null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      )

      if (response.data.success) {
        setSearchResults(response.data.results)
        if (response.data.results.length === 0) {
          message.info('未找到相关结果')
        } else {
          message.success(response.data.message)
        }
      } else {
        message.error(response.data.message || '搜索失败')
        setSearchResults([])
      }
    } catch (error) {
      console.error('Search failed:', error)
      message.error('搜索失败: ' + (error.response?.data?.detail || error.message))
      setSearchResults([])
    } finally {
      setIsSearching(false)
    }
  }

  const getTypeIcon = (type) => {
    switch (type) {
      case 'table': return <TableOutlined style={{ color: '#52c41a' }} />
      case 'column': return <ColumnWidthOutlined style={{ color: '#1890ff' }} />
      case 'business_term': return <FileTextOutlined style={{ color: '#f5222d' }} />
      default: return <DatabaseOutlined />
    }
  }

  const getTypeColor = (type) => {
    switch (type) {
      case 'table': return 'green'
      case 'column': return 'blue'
      case 'business_term': return 'red'
      default: return 'default'
    }
  }

  const getTypeLabel = (type) => {
    switch (type) {
      case 'table': return '表'
      case 'column': return '列'
      case 'business_term': return '业务术语'
      default: return type
    }
  }

  const progressPercent = indexStatus.total > 0 
    ? Math.round((indexStatus.progress / indexStatus.total) * 100) 
    : 0

  const hasIndex = indexStatus.index_stats.tables > 0 || indexStatus.index_stats.columns > 0

  return (
    <Modal
      title={
        <Space>
          <DatabaseOutlined />
          <span>数据库索引管理</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>
      ]}
      style={{ top: 20 }}
    >
      {/* 状态信息 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Statistic
            title="已索引表"
            value={indexStatus.index_stats.tables}
            prefix={<DatabaseOutlined />}
            valueStyle={{ color: '#3f8600' }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="已索引列"
            value={indexStatus.index_stats.columns}
            prefix={<DatabaseOutlined />}
            valueStyle={{ color: '#1890ff' }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="业务术语"
            value={indexStatus.index_stats.business_terms}
            prefix={<DatabaseOutlined />}
            valueStyle={{ color: '#cf1322' }}
          />
        </Col>
      </Row>

      {/* 索引状态 */}
      {!hasIndex && !indexStatus.is_indexing && !indexStatus.completed && (
        <Alert
          message="未检测到索引"
          description="建议先建立索引以获得更好的查询体验。索引过程会遍历数据库表和字段，生成向量用于语义搜索。"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {indexStatus.error && (
        <Alert
          message="索引失败"
          description={indexStatus.error}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          closable
        />
      )}

      {indexStatus.completed && !indexStatus.is_indexing && (
        <Alert
          message="索引完成"
          description="数据库索引已成功建立，现在可以使用语义搜索功能了！"
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 进度显示 */}
      {indexStatus.is_indexing && (
        <div style={{ marginBottom: 24 }}>
          <Title level={5}>索引进度</Title>
          <Progress
            percent={progressPercent}
            status={indexStatus.error ? 'exception' : 'active'}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
          <div style={{ marginTop: 8 }}>
            <Text type="secondary">
              {indexStatus.current_step} ({indexStatus.progress}/{indexStatus.total})
            </Text>
          </div>
        </div>
      )}

      {/* 操作按钮 */}
      <Space size="middle" style={{ width: '100%', justifyContent: 'center' }}>
        <Button
          type="primary"
          icon={<SyncOutlined spin={indexStatus.is_indexing} />}
          onClick={handleTriggerIndex}
          loading={isTriggering}
          disabled={indexStatus.is_indexing}
          size="large"
        >
          {indexStatus.is_indexing ? '索引中...' : hasIndex ? '重新索引' : '开始索引'}
        </Button>
        
        {hasIndex && (
          <Button
            danger
            icon={<CloseCircleOutlined />}
            onClick={handleClearIndex}
            disabled={indexStatus.is_indexing}
            size="large"
          >
            清空索引
          </Button>
        )}
      </Space>

      {/* 搜索功能 */}
      {hasIndex && !indexStatus.is_indexing && (
        <>
          <Divider orientation="left">
            <Space>
              <SearchOutlined />
              <span>索引搜索</span>
            </Space>
          </Divider>

          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {/* 搜索类型选择 */}
            <div>
              <Text type="secondary" style={{ marginRight: 8 }}>搜索类型:</Text>
              <Select
                mode="multiple"
                style={{ minWidth: 300 }}
                placeholder="选择搜索类型"
                value={searchTypes}
                onChange={setSearchTypes}
                options={[
                  { label: '📊 表', value: 'table' },
                  { label: '📝 列', value: 'column' },
                  { label: '💼 业务术语', value: 'business_term' }
                ]}
              />
            </div>

            {/* 搜索框 */}
            <Search
              placeholder="输入关键词搜索（支持中英文、语义搜索）"
              enterButton="搜索"
              size="large"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onSearch={handleSearch}
              loading={isSearching}
              disabled={searchTypes.length === 0}
            />

            {/* 搜索结果 */}
            {isSearching && (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <Spin tip="搜索中..." />
              </div>
            )}

            {!isSearching && hasSearched && (
              <Card 
                size="small" 
                style={{ maxHeight: 400, overflow: 'auto' }}
                title={
                  <Space>
                    <Text strong>搜索结果</Text>
                    <Text type="secondary">({searchResults.length} 项)</Text>
                  </Space>
                }
              >
                {searchResults.length > 0 ? (
                  <List
                    dataSource={searchResults}
                    renderItem={(item) => (
                      <List.Item>
                        <List.Item.Meta
                          avatar={getTypeIcon(item.type)}
                          title={
                            <Space>
                              <Text strong>{item.name}</Text>
                              <Tag color={getTypeColor(item.type)}>
                                {getTypeLabel(item.type)}
                              </Tag>
                              <Tag color="purple">
                                相似度: {(item.similarity * 100).toFixed(1)}%
                              </Tag>
                            </Space>
                          }
                          description={
                            <div>
                              {item.metadata.definition && (
                                <div><Text type="secondary">定义: {item.metadata.definition}</Text></div>
                              )}
                              {item.metadata.formula && (
                                <div><Text code style={{ fontSize: 11 }}>{item.metadata.formula}</Text></div>
                              )}
                              {item.metadata.comment && (
                                <div><Text type="secondary">{item.metadata.comment}</Text></div>
                              )}
                              {item.metadata.data_type && (
                                <div><Text type="secondary">类型: {item.metadata.data_type}</Text></div>
                              )}
                              {item.metadata.related_tables && (
                                <div>
                                  <Text type="secondary">相关表: </Text>
                                  {JSON.parse(item.metadata.related_tables).map((table, idx) => (
                                    <Tag key={idx} size="small">{table}</Tag>
                                  ))}
                                </div>
                              )}
                            </div>
                          }
                        />
                      </List.Item>
                    )}
                  />
                ) : (
                  <Empty 
                    description="未找到相关结果" 
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                )}
              </Card>
            )}
          </Space>
        </>
      )}

      {/* 说明 */}
      <div style={{ marginTop: 24, padding: 16, background: '#f5f5f5', borderRadius: 4 }}>
        <Title level={5}> 关于索引</Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          • 索引会将数据库表、列和业务术语转换为向量，用于语义搜索
          <br />
          • 首次索引可能需要几分钟，具体取决于数据库大小
          <br />
          • 建议在数据库结构变更后重新索引
          <br />
          • 索引数据存储在本地，不会上传到任何服务器
          <br />
          {hasIndex && '• 使用上方搜索框可以快速查找已索引的表、列和业务术语'}
        </Text>
      </div>
    </Modal>
  )
}



