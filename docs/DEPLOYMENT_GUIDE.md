# AskDB 增强版部署和使用指南

## 🎯 新功能概述

本次更新为 AskDB 添加了以下重要功能：

### 1. 向量检索系统
- ✅ 自动将数据库表、字段和业务术语转换为向量
- ✅ 使用语义搜索快速定位相关表和字段
- ✅ 支持自然语言查询（如"客户订单"→自动找到 orders, customers 表）

### 2. 增强的 SQL 解释
- ✅ 每条 SQL 都带有自然语言解释
- ✅ 前端清晰展示 SQL 的作用
- ✅ 帮助用户理解和学习 SQL

### 3. 危险操作确认
- ✅ INSERT/UPDATE/DELETE 操作需要用户确认
- ✅ 显示预期影响范围
- ✅ 防止误操作导致数据丢失

### 4. 索引管理界面
- ✅ 管理员可以触发数据库索引
- ✅ 实时显示索引进度
- ✅ 查看索引统计信息

---

## 📦 安装和配置

### 1. 安装新依赖

```bash
# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
.\.venv\Scripts\activate   # Windows

# 安装新增的依赖
uv pip install chromadb>=0.4.0

# 或使用 pip
pip install chromadb>=0.4.0
```

### 2. 环境配置

在 `.env` 文件中确保以下配置：

```env
# LLM 配置
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# 数据库配置
DEFAULT_DB_TYPE=mysql
DEFAULT_DB_HOST=localhost
DEFAULT_DB_PORT=3306
DEFAULT_DB_NAME=your_database
DEFAULT_DB_USER=your_user
DEFAULT_DB_PASSWORD=your_password

# 向量检索配置（可选）
ENABLE_SEMANTIC_SEARCH=true
```

### 3. 启动服务

#### 启动后端

```bash
# 方法1：使用启动脚本
python start_backend.py

# 方法2：直接运行
cd backend
python main.py
```

#### 启动前端

```bash
# 另开一个终端
cd frontend
npm install  # 首次运行需要安装依赖
npm run dev
```

---

## 🚀 首次使用流程

### 步骤 1: 登录系统

1. 打开浏览器访问 `http://localhost:5173`
2. 使用管理员账户登录：
   - 用户名：`admin`
   - 密码：`admin123`
   
   或注册新账户（需要邮箱验证）

### 步骤 2: 建立索引（重要！）

**这是新功能的核心步骤**，必须先建立索引才能使用语义搜索。

1. 登录后，在左侧边栏找到 **"索引管理"** 按钮（仅管理员可见）
2. 点击打开索引管理对话框
3. 点击 **"开始索引"** 按钮
4. 等待索引完成（进度条会实时更新）

索引内容包括：
- **数据库表** - 表名、列信息、主外键关系
- **数据库列** - 列名、数据类型、约束
- **业务术语** - 从 `data/business_metadata.json` 加载

**索引时间**：
- 小型数据库（< 50 表）：1-3 分钟
- 中型数据库（50-200 表）：5-10 分钟
- 大型数据库（> 200 表）：10-30 分钟

**注意**：
- 首次索引会下载 ~80MB 的 AI 模型（`all-MiniLM-L6-v2`）
- 索引数据存储在 `data/vector_db/` 目录
- 数据库结构变更后需要重新索引

### 步骤 3: 开始查询

索引完成后，就可以使用自然语言查询数据库了！

---

## 💬 使用示例

### 基础查询

```
用户问题：有多少个用户？
AI 响应：
  📊 查询结果：共有 1,523 个用户
  
  执行的 SQL：
  SELECT COUNT(*) as user_count FROM users
  
  解释：统计 users 表中的总记录数
```

### 语义搜索示例

```
用户问题：查看客户的订单信息
  
AI 流程：
  1️⃣ 语义搜索 "客户 订单"
     → 找到相关表：customers, orders, order_items
     → 找到相关列：customer_id, order_id, order_date
  
  2️⃣ 获取表结构
     → customers (id, name, email, created_at)
     → orders (id, customer_id, total_amount, status)
  
  3️⃣ 生成并执行 SQL
     SELECT c.name, c.email, o.id, o.total_amount, o.status
     FROM customers c
     JOIN orders o ON c.id = o.customer_id
     LIMIT 15
  
  解释：查询客户基本信息及其订单，使用 JOIN 连接两表
```

### 业务术语查询

```
用户问题：本月的 GMV 是多少？

AI 流程：
  1️⃣ 语义搜索 "GMV"
     → 找到业务术语定义：
        GMV = sum(sales_amount + shipping_fee - discount)
        相关表：orders, order_items
  
  2️⃣ 生成 SQL
     SELECT SUM(sales_amount + shipping_fee - discount) as GMV
     FROM orders
     WHERE DATE_FORMAT(created_at, '%Y-%m') = DATE_FORMAT(NOW(), '%Y-%m')
  
  解释：计算本月的总商品交易额（GMV），包含销售额、运费，扣除折扣
```

### 数据修改（带确认）

```
用户问题：将所有未激活用户标记为 inactive

AI 响应：
  ⚠️ 这是一个数据修改操作，需要您确认
  
  操作说明：
  将状态为未激活的用户账户标记为 inactive 状态
  
  预期影响：
  预计将修改约 150 个用户账户的状态
  
  SQL 语句：
  UPDATE users 
  SET status = 'inactive' 
  WHERE is_activated = 0
  
  [前端弹出确认对话框]
  → 用户点击"确认执行"后才会真正执行
```

---

## 🎨 前端功能说明

### 1. 聊天界面

- **消息展示** - 支持 Markdown 格式
- **SQL 高亮** - 代码块自动语法高亮
- **实时流式** - AI 回复逐字显示（如果 LLM 支持）
- **历史记录** - 自动保存会话历史

### 2. 会话管理

- **新建对话** - 创建新的查询会话
- **搜索会话** - 快速找到历史对话
- **删除会话** - 清理不需要的记录

### 3. 索引管理（管理员）

- **触发索引** - 手动开始索引任务
- **查看进度** - 实时显示索引状态
- **查看统计** - 已索引的表、列、术语数量
- **清空索引** - 删除所有索引数据

### 4. 危险操作确认

当 AI 尝试执行 INSERT/UPDATE/DELETE 时：
1. 前端自动弹出确认对话框
2. 显示操作说明和预期影响
3. 显示完整的 SQL 语句
4. 用户必须确认后才会执行

---

## 🔧 高级配置

### 自定义业务术语

编辑 `data/business_metadata.json`：

```json
{
  "新术语名称": {
    "definition": "术语定义",
    "formula": "计算公式（SQL 片段）",
    "related_tables": ["相关表1", "相关表2"],
    "related_columns": ["列1", "列2"]
  }
}
```

示例：

```json
{
  "月活用户": {
    "definition": "过去30天内有登录记录的用户数",
    "formula": "COUNT(DISTINCT user_id) WHERE last_login >= DATE_SUB(NOW(), INTERVAL 30 DAY)",
    "related_tables": ["users", "login_logs"],
    "related_columns": ["user_id", "last_login"]
  }
}
```

添加后需要：
1. 重新触发索引
2. AI 就能识别这个术语并正确计算

### 调整索引参数

在 `tools/vector_store.py` 中可以调整：

```python
# 模型选择
model_name = "all-MiniLM-L6-v2"  # 默认，速度快
# 或使用更强大的模型：
# model_name = "paraphrase-multilingual-mpnet-base-v2"  # 多语言支持更好

# 搜索结果数量
top_k = 5  # 返回前5个最相关结果
```

---

## 🧪 测试

运行测试脚本：

```bash
# 运行所有测试
python test_enhanced_system.py

# 使用 pytest
python test_enhanced_system.py --pytest
```

测试包括：
- ✅ 向量存储初始化
- ✅ 业务术语索引
- ✅ 语义搜索功能
- ✅ 增强工具初始化
- ✅ Agent 创建和查询

---

## 📊 性能优化建议

### 1. 数据库优化

- 为常查询的列添加索引
- 优化复杂查询的执行计划
- 定期更新表统计信息

### 2. 向量索引优化

- 大型数据库（>1000表）考虑分批索引
- 使用 SSD 存储向量数据库
- 定期清理无用的向量索引

### 3. 前端性能

- 聊天记录过多时清理旧会话
- 大量数据查询时使用分页
- 启用浏览器缓存

---

## 🐛 常见问题

### Q1: 索引失败怎么办？

**可能原因**：
- 数据库连接失败
- 磁盘空间不足
- 模型下载失败

**解决方法**：
1. 检查数据库连接配置
2. 确保有足够磁盘空间（至少 500MB）
3. 检查网络连接（首次需要下载模型）
4. 查看后端日志：`logs/askdb.log`

### Q2: 语义搜索不准确？

**优化方法**：
1. 增加相关的业务术语定义
2. 为表和列添加注释（如果数据库支持）
3. 调整搜索结果数量（修改 `top_k`）
4. 考虑使用更强大的嵌入模型

### Q3: SQL 解释不清晰？

**这需要调整 Agent 的提示词**：

在 `askdb_agno.py` 中修改 `instructions`，增加：

```python
### 解释要求
- 解释要具体、清晰，避免技术术语
- 说明每个 JOIN 的目的
- 解释 WHERE 条件的含义
- 对于复杂查询，分步骤说明
```

### Q4: 前端报错 "Cannot find module"？

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Q5: 后端启动失败？

检查：
1. Python 版本（需要 >=3.9）
2. 虚拟环境是否激活
3. 依赖是否安装：`pip list | grep chromadb`
4. 端口 8000 是否被占用

---

## 📈 监控和维护

### 日志位置

- 后端日志：`logs/askdb.log`
- 前端日志：浏览器开发者工具 Console

### 定期维护

1. **每周**：检查索引状态，必要时重新索引
2. **每月**：清理旧的会话记录
3. **季度**：更新业务术语定义
4. **年度**：评估是否需要升级模型

### 数据备份

重要数据：
- `data/users.db` - 用户信息
- `data/askdb_sessions.db` - 会话历史
- `data/vector_db/` - 向量索引
- `data/business_metadata.json` - 业务术语

建议定期备份到异地存储。

---

## 🎓 最佳实践

### 1. 查询最佳实践

- ✅ 使用自然、完整的语句（"查询上个月的新客户数量"）
- ✅ 提供足够的上下文（"订单"比"它"更清晰）
- ✅ 复杂查询分步骤提问
- ❌ 避免过于简短的问题（"数据"）
- ❌ 不要一次询问多个不相关的问题

### 2. 索引最佳实践

- ✅ 首次使用前必须建立索引
- ✅ 数据库结构变更后重新索引
- ✅ 定期（每月）重新索引保持数据新鲜
- ❌ 不要在数据库繁忙时索引
- ❌ 避免频繁重复索引（浪费资源）

### 3. 安全最佳实践

- ✅ 仔细阅读危险操作的说明
- ✅ 在测试环境先验证 SQL
- ✅ 定期备份数据
- ❌ 不要在生产环境随意执行修改操作
- ❌ 不要跳过确认步骤

---

## 📞 技术支持

遇到问题？

1. **查看日志**：`logs/askdb.log`
2. **运行测试**：`python test_enhanced_system.py`
3. **检查配置**：`.env` 文件
4. **查看文档**：`README.md`, `AGNO_RESPONSE_INFO.md`

---

## 🚀 下一步计划

未来可能添加的功能：

- [ ] 支持更多数据库类型（PostgreSQL, SQL Server）
- [ ] 数据可视化（图表、报表）
- [ ] 批量查询和导出
- [ ] API 接口供其他系统调用
- [ ] 多语言支持
- [ ] 自定义 SQL 模板

---

**祝使用愉快！** 🎉

如有任何问题或建议，欢迎反馈。



