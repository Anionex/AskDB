import React, { useState } from 'react'
import { Collapse, Tag, Typography, Space, Button, Tooltip } from 'antd'
import { ToolOutlined, ApiOutlined, ExpandOutlined, CompressOutlined, CopyOutlined, CheckOutlined } from '@ant-design/icons'

const { Text } = Typography

// 单个结果显示组件（支持展开/收起）
const ResultDisplay = ({ result }) => {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  
  const resultStr = typeof result === 'string' ? result : JSON.stringify(result, null, 2)
  const isLong = resultStr.length > 500
  const displayText = expanded || !isLong ? resultStr : resultStr.substring(0, 500) + '\n\n... (结果过长，点击"展开"查看完整内容)'
  
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(resultStr)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('复制失败:', err)
    }
  }
  
  return (
    <div>
      <div style={{ 
        marginTop: '6px',
        maxHeight: expanded ? '600px' : '200px',
        overflowY: 'auto',
        overflowX: 'auto',
        transition: 'max-height 0.3s ease'
      }}>
        <Text code style={{ 
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          fontSize: '11px'
        }}>
          {displayText}
        </Text>
      </div>
      {(isLong || resultStr.length > 100) && (
        <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
          {isLong && (
            <Tooltip title={expanded ? '收起结果' : '展开完整结果'}>
              <Button 
                type="link" 
                size="small"
                icon={expanded ? <CompressOutlined /> : <ExpandOutlined />}
                onClick={() => setExpanded(!expanded)}
                style={{ padding: '0 4px', fontSize: '11px' }}
              >
                {expanded ? '收起' : `展开 (${resultStr.length} 字符)`}
              </Button>
            </Tooltip>
          )}
          <Tooltip title="复制完整结果">
            <Button 
              type="link" 
              size="small"
              icon={copied ? <CheckOutlined style={{ color: '#52c41a' }} /> : <CopyOutlined />}
              onClick={handleCopy}
              style={{ padding: '0 4px', fontSize: '11px' }}
            >
              {copied ? '已复制' : '复制'}
            </Button>
          </Tooltip>
        </div>
      )}
    </div>
  )
}

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

  // 格式化参数显示（支持展开）
  const formatArguments = (args) => {
    if (!args) {
      return <Text type="secondary">(无)</Text>
    }
    
    if (typeof args === 'string') {
      return args.trim() ? args : <Text type="secondary">(无)</Text>
    }
    
    if (typeof args === 'object' && args !== null) {
      const entries = Object.entries(args)
      
      // 如果是空对象，显示"(无)"
      if (entries.length === 0) {
        return <Text type="secondary">(无)</Text>
      }
      
      return entries.map(([key, value]) => {
        let displayValue = value
        if (typeof value === 'object') {
          displayValue = JSON.stringify(value, null, 2)
        }
        
        const valueStr = String(displayValue)
        const isLong = valueStr.length > 200
        
        return (
          <div key={key} style={{ marginBottom: '8px' }}>
            <Text strong style={{ color: '#1890ff' }}>{key}: </Text>
            <Text code style={{ whiteSpace: 'pre-wrap' }}>
              {isLong ? valueStr.substring(0, 200) + '...' : valueStr}
            </Text>
            {isLong && (
              <ExpandableText text={valueStr} />
            )}
          </div>
        )
      })
    }
    
    return String(args)
  }
  
  // 可展开的长文本组件
  const ExpandableText = ({ text }) => {
    const [expanded, setExpanded] = useState(false)
    
    if (!expanded) {
      return (
        <Button 
          type="link" 
          size="small"
          onClick={() => setExpanded(true)}
          style={{ padding: '0 4px', fontSize: '11px' }}
        >
          展开完整内容
        </Button>
      )
    }
    
    return (
      <div style={{ marginTop: '4px' }}>
        <Text code style={{ whiteSpace: 'pre-wrap', fontSize: '11px' }}>{text}</Text>
        <Button 
          type="link" 
          size="small"
          onClick={() => setExpanded(false)}
          style={{ padding: '0 4px', fontSize: '11px', display: 'block', marginTop: '4px' }}
        >
          收起
        </Button>
      </div>
    )
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
                
                {call.result && (
                  <div style={{ 
                    marginTop: '8px',
                    padding: '8px',
                    background: '#f6ffed',
                    borderRadius: '4px',
                    fontSize: '12px',
                    border: '1px solid #b7eb8f'
                  }}>
                    <Text type="secondary" style={{ fontSize: '11px', color: '#52c41a' }}>
                      返回结果:
                    </Text>
                    <ResultDisplay result={call.result} />
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

