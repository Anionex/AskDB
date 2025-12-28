import React, { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

export const StreamingMarkdown = ({ content, isStreaming = false }) => {
  const contentRef = useRef(null)

  useEffect(() => {
    if (contentRef.current && isStreaming) {
      contentRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [content, isStreaming])

  return (
    <div ref={contentRef} className="streaming-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            return !inline && match ? (
              <SyntaxHighlighter
                style={vscDarkPlus}
                language={match[1]}
                PreTag="div"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            )
          },
          table({ children }) {
            return (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  {children}
                </table>
              </div>
            )
          },
          th({ children }) {
            return (
              <th style={{ 
                border: '1px solid #d9d9d9', 
                padding: '8px', 
                background: '#fafafa',
                textAlign: 'left'
              }}>
                {children}
              </th>
            )
          },
          td({ children }) {
            return (
              <td style={{ 
                border: '1px solid #d9d9d9', 
                padding: '8px'
              }}>
                {children}
              </td>
            )
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

