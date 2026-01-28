import React, { useState, useEffect } from 'react'
import { 
  Modal, 
  Table, 
  List, 
  Typography, 
  Space, 
  Spin, 
  Empty, 
  Tag, 
  message,
  Input,
  Card,
  Statistic,
  Row,
  Col,
  Tooltip
} from 'antd'
import { 
  TableOutlined, 
  DatabaseOutlined, 
  ReloadOutlined,
  SearchOutlined,
  ColumnWidthOutlined
} from '@ant-design/icons'
import axios from 'axios'

const { Text, Title } = Typography
const { Search } = Input

const API_BASE = '/api'

export const TableDataPreview = ({ visible, onClose }) => {
  const [tables, setTables] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedTable, setSelectedTable] = useState(null)
  const [tableData, setTableData] = useState(null)
  const [dataLoading, setDataLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 50,
    total: 0
  })

  // 获取表列表
  const fetchTables = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('askdb_token')
      const response = await axios.get(`${API_BASE}/protected/admin/tables`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.data.success) {
        setTables(response.data.tables)
      } else {
        message.error('获取表列表失败')
      }
    } catch (error) {
      message.error(error.response?.data?.detail || '获取表列表失败')
    } finally {
      setLoading(false)
    }
  }

  // 获取表数据预览
  const fetchTableData = async (tableName, page = 1, pageSize = 50) => {
    setDataLoading(true)
    try {
      const token = localStorage.getItem('askdb_token')
      const response = await axios.get(
        `${API_BASE}/protected/admin/tables/${tableName}/preview`,
        {
          params: { page, page_size: pageSize },
          headers: { Authorization: `Bearer ${token}` }
        }
      )
      if (response.data.success) {
        setTableData(response.data)
        setPagination({
          current: response.data.page,
          pageSize: response.data.page_size,
          total: response.data.total_rows
        })
      } else {
        message.error('获取表数据失败')
      }
    } catch (error) {
      message.error(error.response?.data?.detail || '获取表数据失败')
    } finally {
      setDataLoading(false)
    }
  }

  useEffect(() => {
    if (visible) {
      fetchTables()
    } else {
      // 关闭时重置状态
      setSelectedTable(null)
      setTableData(null)
      setSearchText('')
    }
  }, [visible])

  // 选择表
  const handleSelectTable = (tableName) => {
    setSelectedTable(tableName)
    setPagination({ current: 1, pageSize: 50, total: 0 })
    fetchTableData(tableName, 1, 50)
  }

  // 分页变化
  const handleTableChange = (paginationInfo) => {
    fetchTableData(selectedTable, paginationInfo.current, paginationInfo.pageSize)
  }

  // 过滤表
  const filteredTables = tables.filter(table => 
    table.name.toLowerCase().includes(searchText.toLowerCase())
  )

  // 生成表格列
  const generateColumns = () => {
    if (!tableData?.columns) return []
    
    return tableData.columns.map(col => ({
      title: col,
      dataIndex: col,
      key: col,
      ellipsis: true,
      width: 150,
      render: (value) => {
        if (value === null || value === undefined) {
          return <Text type="secondary" italic>NULL</Text>
        }
        if (typeof value === 'object') {
          return <Text code>{JSON.stringify(value)}</Text>
        }
        const strValue = String(value)
        if (strValue.length > 100) {
          return (
            <Tooltip title={strValue}>
              <Text>{strValue.substring(0, 100)}...</Text>
            </Tooltip>
          )
        }
        return strValue
      }
    }))
  }

  // 计算总行数和列数
  const totalRows = tables.reduce((sum, t) => sum + (t.row_count || 0), 0)
  const totalColumns = tables.reduce((sum, t) => sum + (t.column_count || 0), 0)

  return (
    <Modal
      title={
        <Space>
          <DatabaseOutlined style={{ color: '#1890ff' }} />
          <span>数据库表预览</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width="90%"
      style={{ top: 20 }}
      footer={null}
      bodyStyle={{ padding: 0, height: 'calc(100vh - 150px)', overflow: 'hidden' }}
    >
      <div style={{ display: 'flex', height: '100%' }}>
        {/* 左侧表列表 */}
        <div style={{ 
          width: 280, 
          borderRight: '1px solid #f0f0f0',
          display: 'flex',
          flexDirection: 'column',
          height: '100%'
        }}>
          {/* 统计信息 */}
          <div style={{ padding: '12px', borderBottom: '1px solid #f0f0f0', background: '#fafafa' }}>
            <Row gutter={8}>
              <Col span={8}>
                <Statistic 
                  title="表数" 
                  value={tables.length} 
                  valueStyle={{ fontSize: '16px' }}
                />
              </Col>
              <Col span={8}>
                <Statistic 
                  title="总行数" 
                  value={totalRows} 
                  valueStyle={{ fontSize: '16px' }}
                />
              </Col>
              <Col span={8}>
                <Statistic 
                  title="总列数" 
                  value={totalColumns} 
                  valueStyle={{ fontSize: '16px' }}
                />
              </Col>
            </Row>
          </div>

          {/* 搜索框 */}
          <div style={{ padding: '12px' }}>
            <Search
              placeholder="搜索表名..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
          </div>

          {/* 表列表 */}
          <div style={{ flex: 1, overflow: 'auto' }}>
            {loading ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <Spin tip="加载表列表..." />
              </div>
            ) : (
              <List
                size="small"
                dataSource={filteredTables}
                renderItem={(table) => (
                  <List.Item
                    onClick={() => handleSelectTable(table.name)}
                    style={{
                      cursor: 'pointer',
                      padding: '8px 16px',
                      background: selectedTable === table.name ? '#e6f7ff' : 'transparent',
                      borderLeft: selectedTable === table.name ? '3px solid #1890ff' : '3px solid transparent'
                    }}
                  >
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Space>
                          <TableOutlined style={{ color: '#1890ff' }} />
                          <Text strong={selectedTable === table.name}>
                            {table.name}
                          </Text>
                        </Space>
                      </div>
                      <div style={{ marginTop: 4, marginLeft: 22 }}>
                        <Space size="small">
                          <Tag color="blue" style={{ fontSize: '11px' }}>
                            {table.row_count || 0} 行
                          </Tag>
                          <Tag color="green" style={{ fontSize: '11px' }}>
                            {table.column_count || 0} 列
                          </Tag>
                        </Space>
                      </div>
                    </div>
                  </List.Item>
                )}
                locale={{
                  emptyText: <Empty description="没有找到表" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                }}
              />
            )}
          </div>
        </div>

        {/* 右侧数据预览 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {!selectedTable ? (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              height: '100%',
              background: '#fafafa'
            }}>
              <Empty 
                description="请从左侧选择一个表查看数据"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            </div>
          ) : (
            <>
              {/* 表信息头部 */}
              <div style={{ 
                padding: '12px 16px', 
                borderBottom: '1px solid #f0f0f0',
                background: '#fafafa',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <Space>
                  <Title level={5} style={{ margin: 0 }}>
                    {selectedTable}
                  </Title>
                  {tableData && (
                    <Text type="secondary">
                      {tableData.message}
                    </Text>
                  )}
                </Space>
                <Space>
                  <Tag icon={<ColumnWidthOutlined />} color="processing">
                    {tableData?.columns?.length || 0} 列
                  </Tag>
                </Space>
              </div>

              {/* 数据表格 */}
              <div style={{ flex: 1, overflow: 'auto', padding: '0' }}>
                <Table
                  columns={generateColumns()}
                  dataSource={tableData?.data?.map((row, index) => ({ ...row, _key: index })) || []}
                  rowKey="_key"
                  loading={dataLoading}
                  pagination={{
                    ...pagination,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    pageSizeOptions: ['20', '50', '100', '200'],
                    showTotal: (total) => `共 ${total} 条`
                  }}
                  onChange={handleTableChange}
                  scroll={{ x: 'max-content', y: 'calc(100vh - 350px)' }}
                  size="small"
                  bordered
                />
              </div>
            </>
          )}
        </div>
      </div>
    </Modal>
  )
}
