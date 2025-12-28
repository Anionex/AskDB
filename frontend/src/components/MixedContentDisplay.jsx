import React, { useState } from 'react'
import { Tag, Typography, Spin, Collapse } from 'antd'
import { ApiOutlined, LoadingOutlined, CheckCircleOutlined, DownOutlined } from '@ant-design/icons'
import { StreamingMarkdown } from './StreamingMarkdown'

const { Text } = Typography

/**
 * 混合渲染组件：按时间顺序显示内容和工具调用
 * 
 * 数据结构：
 * message.content: "完整的回复内容"
 * message.toolCalls: [
 *   {
 *     name: "tool_name",
 *     arguments: {...},
 *     result: "...",
 *     insertPosition: 50,  // 在内容的第50个字符后插入
 *     completedPosition: 150,  // 在内容的第150个字符后显示完成
 *     status: "started" | "completed"
 *   }
 * ]
 */
export const MixedContentDisplay = ({ message, isStreaming }) => {
  const { content = '', toolCalls = [] } = message

  // 如果没有工具调用，直接显示内容
  if (!toolCalls || toolCalls.length === 0) {
    return <StreamingMarkdown content={content} isStreaming={isStreaming} />
  }

  // 创建插入点列表
  const insertions = []
  
  toolCalls.forEach((tool, index) => {
    // 工具调用开始
    if (tool.insertPosition !== undefined) {
      insertions.push({
        position: tool.insertPosition,
        type: 'tool_start',
        tool,
        index
      })
    }
    
    // 工具调用完成
    if (tool.completedPosition !== undefined && tool.status === 'completed') {
      insertions.push({
        position: tool.completedPosition,
        type: 'tool_complete',
        tool,
        index
      })
    }
  })

  // 按位置排序
  insertions.sort((a, b) => a.position - b.position)

  // 如果没有位置信息，回退到旧的显示方式（底部显示）
  if (insertions.length === 0) {
    return (
      <>
        <StreamingMarkdown content={content} isStreaming={isStreaming} />
        <div style={{ marginTop: '12px', opacity: 0.8 }}>
          {toolCalls.map((tool, idx) => (
            <ToolCallBadge key={idx} tool={tool} />
          ))}
        </div>
      </>
    )
  }

  // 按位置切分内容并插入工具调用
  const segments = []
  let lastPosition = 0

  insertions.forEach((insertion, idx) => {
    const { position, type, tool } = insertion

    // 添加位置之前的内容
    if (position > lastPosition) {
      const textSegment = content.substring(lastPosition, position)
      if (textSegment) {
        segments.push({
          type: 'content',
          content: textSegment,
          key: `content-${idx}`
        })
      }
    }

    // 添加工具调用标记
    segments.push({
      type: type,
      tool: tool,
      key: `${type}-${idx}`
    })

    lastPosition = position
  })

  // 添加最后剩余的内容
  if (lastPosition < content.length) {
    segments.push({
      type: 'content',
      content: content.substring(lastPosition),
      key: `content-end`
    })
  }

  // 渲染所有片段
  return (
    <div>
      {segments.map(segment => {
        if (segment.type === 'content') {
          return (
            <StreamingMarkdown 
              key={segment.key}
              content={segment.content} 
              isStreaming={isStreaming && segment.key === `content-end`}
            />
          )
        } else if (segment.type === 'tool_start') {
          return <ToolCallBadge key={segment.key} tool={segment.tool} type="start" />
        } else if (segment.type === 'tool_complete') {
          return <ToolCallBadge key={segment.key} tool={segment.tool} type="complete" />
        }
        return null
      })}
    </div>
  )
}

/**
 * 工具调用徽章组件 - 支持展开查看详情
 */
const ToolCallBadge = ({ tool, type }) => {
  const [expanded, setExpanded] = useState(false)
  
  const toolNameMap = {
    'semantic_search_schema': '语义检索',
    'get_table_ddl': '获取表结构',
    'execute_query_with_explanation': '执行查询',
    'execute_non_query_with_explanation': '执行修改',
    'list_all_tables': '列出所有表',
    'get_table_info': '获取表信息',
    'duckduckgo_search': 'DuckDuckGo搜索',
    'exa_search': 'Exa搜索',
    'web_search': '网络搜索',
  }

  const displayName = toolNameMap[tool.name] || tool.name
  
  // 格式化参数显示
  const formatArguments = (args) => {
    if (!args || Object.keys(args).length === 0) {
      return <Text type="secondary" style={{ fontSize: '11px' }}>(无参数)</Text>
    }
    
    return Object.entries(args).map(([key, value]) => {
      let displayValue = value
      if (typeof value === 'string' && value.length > 100) {
        displayValue = value.substring(0, 100) + '...'
      } else if (typeof value === 'object') {
        displayValue = JSON.stringify(value, null, 2)
      }
      
      return (
        <div key={key} style={{ marginBottom: '4px' }}>
          <Text strong style={{ fontSize: '11px', color: '#666' }}>{key}: </Text>
          <Text code style={{ fontSize: '10px', whiteSpace: 'pre-wrap' }}>{String(displayValue)}</Text>
        </div>
      )
    })
  }
  
  // 提取 explanation 字段
  const getExplanation = (result) => {
    if (!result) return null
    
    // 如果结果是字符串，尝试解析为 JSON
    let parsedResult = result
    if (typeof result === 'string') {
      try {
        parsedResult = JSON.parse(result)
      } catch {
        return null
      }
    }
    
    // 提取 explanation 字段
    if (typeof parsedResult === 'object' && parsedResult.explanation) {
      return parsedResult.explanation
    }
    
    return null
  }
  
  // 格式化结果显示（排除 explanation，因为它会单独显示）
  const formatResult = (result) => {
    if (!result) return null
    
    let displayResult = result
    
    // 如果是对象且包含 explanation，创建副本并移除它
    if (typeof result === 'string') {
      try {
        const parsed = JSON.parse(result)
        if (parsed.explanation) {
          const { explanation, ...rest } = parsed
          displayResult = JSON.stringify(rest, null, 2)
        }
      } catch {
        // 如果无法解析，直接显示原始字符串
      }
    } else if (typeof result === 'object' && result.explanation) {
      const { explanation, ...rest } = result
      displayResult = JSON.stringify(rest, null, 2)
    } else if (typeof result === 'object') {
      displayResult = JSON.stringify(result, null, 2)
    }
    
    // 截断过长的结果
    if (typeof displayResult === 'string' && displayResult.length > 200) {
      displayResult = displayResult.substring(0, 200) + '\n... (结果过长，已截断)'
    }
    
    return (
      <Text code style={{ 
        fontSize: '10px', 
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word'
      }}>
        {String(displayResult)}
      </Text>
    )
  }

  if (type === 'start') {
    // 工具开始调用
    return (
      <div style={{ margin: '8px 0' }}>
        <div 
          onClick={() => setExpanded(!expanded)}
          style={{ 
            padding: '6px 12px',
            background: 'rgba(24, 144, 255, 0.1)',
            border: '1px solid rgba(24, 144, 255, 0.3)',
            borderRadius: '4px',
            fontSize: '12px',
            display: 'inline-flex',
            alignItems: 'center',
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
        >
          <ApiOutlined style={{ color: '#1890ff', marginRight: '6px' }} />
          <Text style={{ fontSize: '12px', color: '#1890ff' }}>
            {tool.status === 'started' ? (
              <>
                <Spin indicator={<LoadingOutlined style={{ fontSize: 12 }} />} style={{ marginRight: '6px' }} />
                正在调用: {displayName}...
              </>
            ) : (
              <>开始调用: {displayName}</>
            )}
          </Text>
          {(tool.arguments && Object.keys(tool.arguments).length > 0) && (
            <DownOutlined 
              style={{ 
                marginLeft: '8px', 
                fontSize: '10px',
                transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform 0.2s'
              }} 
            />
          )}
        </div>
        
        {/* 展开的详情 */}
        {expanded && tool.arguments && Object.keys(tool.arguments).length > 0 && (
          <div style={{
            marginTop: '4px',
            padding: '8px',
            background: '#fafafa',
            border: '1px solid #e8e8e8',
            borderRadius: '4px',
            fontSize: '11px'
          }}>
            <Text type="secondary" style={{ fontSize: '11px' }}>调用参数:</Text>
            <div style={{ marginTop: '6px' }}>
              {formatArguments(tool.arguments)}
            </div>
          </div>
        )}
      </div>
    )
  } else if (type === 'complete') {
    // 工具调用完成
    const explanation = getExplanation(tool.result)
    
    return (
      <div style={{ margin: '8px 0' }}>
        <div 
          onClick={() => setExpanded(!expanded)}
          style={{ 
            padding: '6px 12px',
            background: 'rgba(82, 196, 26, 0.1)',
            border: '1px solid rgba(82, 196, 26, 0.3)',
            borderRadius: '4px',
            fontSize: '12px',
            display: 'inline-flex',
            alignItems: 'center',
            cursor: tool.result ? 'pointer' : 'default',
            transition: 'all 0.2s',
            flexDirection: 'column',
            alignItems: 'flex-start'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', width: '100%' }}>
            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: '6px' }} />
            <Text style={{ fontSize: '12px', color: '#52c41a' }}>
              {displayName} 完成
            </Text>
            {tool.result && (
              <DownOutlined 
                style={{ 
                  marginLeft: '8px', 
                  fontSize: '10px',
                  transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s'
                }} 
              />
            )}
          </div>
          
          {/* 直接显示 explanation */}
          {explanation && (
            <div style={{
              marginTop: '6px',
              fontSize: '11px',
              color: '#666',
              fontStyle: 'italic',
              paddingLeft: '20px'
            }}>
              {explanation}
            </div>
          )}
        </div>
        
        {/* 展开的详细结果（不包含 explanation） */}
        {expanded && tool.result && (
          <div style={{
            marginTop: '4px',
            padding: '8px',
            background: '#f6ffed',
            border: '1px solid #b7eb8f',
            borderRadius: '4px',
            fontSize: '11px',
            maxHeight: '300px',
            overflowY: 'auto'
          }}>
            <Text type="secondary" style={{ fontSize: '11px', color: '#52c41a' }}>
              详细结果:
            </Text>
            <div style={{ marginTop: '6px' }}>
              {formatResult(tool.result)}
            </div>
          </div>
        )}
      </div>
    )
  }

  // 默认显示（无类型）- 兼容旧数据
  return (
    <Tag 
      icon={<ApiOutlined />} 
      color={tool.status === 'completed' ? 'success' : 'processing'}
      style={{ margin: '4px' }}
    >
      {displayName}
      {tool.status === 'started' && ' (执行中)'}
    </Tag>
  )
}

