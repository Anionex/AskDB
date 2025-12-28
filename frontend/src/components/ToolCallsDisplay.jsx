import React from 'react'
import { Collapse, Tag, Typography, Space } from 'antd'
import { ToolOutlined, ApiOutlined } from '@ant-design/icons'

const { Text } = Typography

export const ToolCallsDisplay = ({ toolCalls }) => {
  if (!toolCalls || toolCalls.length === 0) {
    return null
  }

  // 工具名称映射为中文
  const toolNameMap = {
    'semantic_search_schema': '语义检索数据库结构',
    'get_table_ddl': '获取表结构',
    'execute_query_with_explanation': '执行查询',
    'execute_non_query_with_explanation': '执行修改操作',
    'list_all_tables': '列出所有表',
    'get_table_info': '获取表信息',
    'duckduckgo_search': 'DuckDuckGo搜索',
    'exa_search': 'Exa搜索',
    'web_search': '网络搜索',
  }

  const getToolDisplayName = (name) => {
    return toolNameMap[name] || name
  }

  // 格式化参数显示
  const formatArguments = (args) => {
    if (typeof args === 'string') {
      return args
    }
    
    if (typeof args === 'object' && args !== null) {
      return Object.entries(args).map(([key, value]) => {
        // 对于长字符串，进行截断
        let displayValue = value
        if (typeof value === 'string' && value.length > 200) {
          displayValue = value.substring(0, 200) + '...'
        } else if (typeof value === 'object') {
          displayValue = JSON.stringify(value, null, 2)
        }
        
        return (
          <div key={key} style={{ marginBottom: '8px' }}>
            <Text strong style={{ color: '#1890ff' }}>{key}: </Text>
            <Text code style={{ whiteSpace: 'pre-wrap' }}>{String(displayValue)}</Text>
          </div>
        )
      })
    }
    
    return String(args)
  }

  // 使用 Antd 5+ 的 items 配置方式
  const collapseItems = [
    {
      key: '1',
      label: (
        <Space>
          <ToolOutlined style={{ color: '#1890ff' }} />
          <Text style={{ fontSize: '12px', color: '#1890ff' }}>
            调用了 {toolCalls.length} 个工具
          </Text>
        </Space>
      ),
      children: (
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          {toolCalls.map((call, index) => (
            <div 
              key={index}
              style={{
                marginBottom: index < toolCalls.length - 1 ? '16px' : 0,
                padding: '12px',
                background: '#fff',
                borderRadius: '4px',
                border: '1px solid #f0f0f0'
              }}
            >
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <div>
                  <Tag icon={<ApiOutlined />} color="blue">
                    工具 {index + 1}
                  </Tag>
                  <Text strong style={{ fontSize: '13px' }}>
                    {getToolDisplayName(call.name)}
                  </Text>
                </div>
                
                {call.arguments && (
                  <div style={{ 
                    marginTop: '8px',
                    padding: '8px',
                    background: '#fafafa',
                    borderRadius: '4px',
                    fontSize: '12px'
                  }}>
                    <Text type="secondary" style={{ fontSize: '11px' }}>调用参数:</Text>
                    <div style={{ marginTop: '6px' }}>
                      {formatArguments(call.arguments)}
                    </div>
                  </div>
                )}
              </Space>
            </div>
          ))}
        </div>
      )
    }
  ]

  return (
    <div style={{ marginTop: '12px' }}>
      <Collapse 
        ghost 
        size="small"
        expandIconPosition="end"
        items={collapseItems}
        style={{ 
          background: 'rgba(24, 144, 255, 0.05)',
          borderRadius: '4px',
          border: '1px solid rgba(24, 144, 255, 0.2)'
        }}
      />
    </div>
  )
}

