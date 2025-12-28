# 危险操作确认流程说明

## 问题描述
之前的实现中，危险操作（如 DROP TABLE、DELETE 等）直接执行，没有给用户确认的机会。

## 解决方案
实现了完整的前后端确认流程：

### 1. 后端工具层 (`tools/enhanced_tools.py`)
- **修改**: `execute_non_query_with_explanation` 方法
- **行为**: 根据操作类型智能判断是否需要确认
  - **高危操作**（DROP/DELETE/TRUNCATE）→ 返回 `needs_confirmation: true`
  - **低风险操作**（CREATE/INSERT/UPDATE/ALTER）→ 直接执行
- **高危操作返回格式**:
```json
{
  "success": false,
  "needs_confirmation": true,
  "sql": "DROP TABLE coursestats2",
  "explanation": "删除名为 coursestats2 的表。这将永久移除该表及其所有数据。",
  "expected_impact": "将删除表 coursestats2 及其所有数据",
  "message": "⚠️ 这是高危操作（会删除数据），需要用户确认。",
  "risk_level": "critical"
}
```
- **低风险操作返回格式**:
```json
{
  "success": true,
  "explanation": "创建新表 users",
  "expected_impact": "将创建一个新表",
  "sql": "CREATE TABLE users (...)",
  "rows_affected": 0,
  "message": "✅ 操作成功。创建新表 users。实际影响: 0 行"
}
```

### 2. 后端流式处理 (`backend/main.py`)
- **修改**: `process_chat_message_stream` 函数
- **行为**: 检测工具调用结果中的 `needs_confirmation` 字段
- **发送事件**: 
```javascript
{
  type: 'needs_confirmation',
  data: {
    sql: "...",
    explanation: "...",
    expected_impact: "..."
  }
}
```

### 3. 后端确认API (`backend/main.py`)
- **新增路由**: `POST /api/protected/confirm-action`
- **功能**: 处理用户的确认或拒绝
- **请求格式**:
```json
{
  "session_id": "user_123_1234567890",
  "sql": "DROP TABLE coursestats2",
  "explanation": "...",
  "action": "approve" // 或 "reject"
}
```

### 4. 前端状态管理 (`frontend/src/store/useChatStore.js`)
- **新增状态**: `pendingConfirmation` - 存储待确认的操作信息
- **新增方法**:
  - `confirmDangerousAction()` - 确认并执行操作
  - `rejectDangerousAction()` - 拒绝操作
- **事件处理**: 接收 `needs_confirmation` 事件并更新状态

### 5. 前端UI (`frontend/src/components/ChatArea.jsx`)
- **集成**: `DangerConfirmDialog` 组件
- **显示条件**: `pendingConfirmation` 不为空时显示
- **用户交互**: 
  - 确认按钮 → 调用 `confirmDangerousAction()`
  - 取消按钮 → 调用 `rejectDangerousAction()`

## 完整流程

### 高危操作流程（DROP/DELETE/TRUNCATE）
```
用户输入: "删除coursestats2表"
    ↓
AI 分析并调用工具: execute_non_query_with_explanation()
    ↓
工具检测到高危操作 → 返回 needs_confirmation
    ↓
后端流式处理检测到 → 发送 needs_confirmation 事件
    ↓
前端接收事件 → 更新 pendingConfirmation 状态
    ↓
UI 显示确认对话框 (DangerConfirmDialog)
    ↓
用户点击"确认执行"或"取消"
    ↓
前端调用 confirmDangerousAction() 或 rejectDangerousAction()
    ↓
如果确认: POST /api/protected/confirm-action
    ↓
后端执行SQL并返回结果
    ↓
前端显示执行结果
```

### 低风险操作流程（CREATE/INSERT/UPDATE/ALTER）
```
用户输入: "创建一个users表"
    ↓
AI 分析并调用工具: execute_non_query_with_explanation()
    ↓
工具判断为低风险 → 直接执行SQL
    ↓
返回执行结果
    ↓
AI 回复用户操作结果
```

## 安全特性

1. **双重检查**: 工具层和数据库层都有安全检查
2. **明确说明**: 必须提供操作说明和预期影响
3. **用户确认**: 所有危险操作都需要用户明确确认
4. **审计日志**: 所有操作都记录在会话历史中
5. **权限控制**: 基于用户角色的权限检查

## 测试场景

### 高危操作（需要确认）

#### 场景1: 删除表
```
输入: "删除coursestats2表"
预期: ✅ 显示确认对话框，包含SQL和影响说明
```

#### 场景2: 批量删除数据
```
输入: "删除所有2020年的订单"
预期: ✅ 显示确认对话框，说明将删除多少条记录
```

#### 场景3: 清空表
```
输入: "清空日志表"
预期: ✅ 显示确认对话框，警告将删除所有数据
```

### 低风险操作（直接执行）

#### 场景4: 创建表
```
输入: "创建一个新的users表"
预期: ✅ 直接执行，不显示确认对话框
```

#### 场景5: 插入数据
```
输入: "向users表插入一条新记录"
预期: ✅ 直接执行，不显示确认对话框
```

#### 场景6: 更新数据
```
输入: "将用户ID为123的状态改为active"
预期: ✅ 直接执行，不显示确认对话框
```

## 注意事项

1. **命令行模式**: 原有的 `Confirm.ask()` 仍然保留在 `tools/agno_tools.py` 中，用于命令行模式
2. **Web模式**: Web应用使用新的确认流程，不依赖命令行交互
3. **向后兼容**: 不影响只读查询的正常执行

## 相关文件

- `tools/enhanced_tools.py` - 工具层修改
- `backend/main.py` - 后端API和流式处理
- `frontend/src/store/useChatStore.js` - 前端状态管理
- `frontend/src/components/ChatArea.jsx` - UI集成
- `frontend/src/components/DangerConfirmDialog.jsx` - 确认对话框组件

## 测试方法

1. 启动后端: `uv run backend/main.py`
2. 启动前端: `cd frontend && npm run dev`
3. 登录系统
4. 输入危险操作命令（如"删除某个表"）
5. 验证是否弹出确认对话框
6. 测试确认和取消两种情况

