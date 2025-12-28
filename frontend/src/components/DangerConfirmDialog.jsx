import React from 'react'
import { Modal, Typography, Alert, Space, Divider } from 'antd'
import { WarningOutlined, ExclamationCircleOutlined } from '@ant-design/icons'

const { Text, Paragraph, Title } = Typography

export const DangerConfirmDialog = ({ 
  visible, 
  onConfirm, 
  onCancel, 
  sqlStatement, 
  explanation, 
  expectedImpact 
}) => {
  return (
    <Modal
      title={
        <Space>
          <WarningOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />
          <span>危险操作确认</span>
        </Space>
      }
      open={visible}
      onOk={onConfirm}
      onCancel={onCancel}
      okText="确认执行"
      cancelText="取消"
      okButtonProps={{ danger: true }}
      width={600}
    >
      <Alert
        message="警告：此操作将修改数据库数据"
        description="请仔细确认以下信息后再执行。此操作可能不可逆！"
        type="error"
        icon={<ExclamationCircleOutlined />}
        showIcon
        style={{ marginBottom: 16 }}
      />

      <div style={{ marginBottom: 16 }}>
        <Title level={5}>📝 操作说明</Title>
        <Paragraph style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
          {explanation || '未提供说明'}
        </Paragraph>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Title level={5}>⚠️ 预期影响</Title>
        <Paragraph style={{ background: '#fff7e6', padding: 12, borderRadius: 4, border: '1px solid #ffd591' }}>
          {expectedImpact || '未提供影响说明'}
        </Paragraph>
      </div>

      <Divider style={{ margin: '12px 0' }} />

      <div>
        <Title level={5}>💻 SQL 语句</Title>
        <pre style={{ 
          background: '#1f1f1f', 
          color: '#d4d4d4', 
          padding: 12, 
          borderRadius: 4,
          overflow: 'auto',
          maxHeight: 200
        }}>
          {sqlStatement || 'N/A'}
        </pre>
      </div>

      <Alert
        message="请确认您了解此操作的后果"
        type="warning"
        showIcon
        style={{ marginTop: 16 }}
      />
    </Modal>
  )
}



