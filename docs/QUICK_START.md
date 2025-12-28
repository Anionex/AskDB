# 🚀 AskDB 快速启动指南

## 5分钟快速上手

### 步骤 1: 安装依赖（首次）

```bash
# 1. 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
.\.venv\Scripts\activate   # Windows

# 2. 安装新增依赖
uv pip install chromadb>=0.4.0
```

### 步骤 2: 配置环境

复制并编辑 `.env` 文件：

```bash
cp env_example.txt .env
nano .env  # 或使用你喜欢的编辑器
```

**最小配置**：

```env
# LLM API
GEMINI_API_KEY=你的_API_密钥

# 数据库
DEFAULT_DB_TYPE=mysql
DEFAULT_DB_HOST=localhost
DEFAULT_DB_PORT=3306
DEFAULT_DB_NAME=你的数据库名
DEFAULT_DB_USER=你的用户名
DEFAULT_DB_PASSWORD=你的密码
```

### 步骤 3: 启动服务

**终端 1 - 后端：**

```bash
python start_backend.py
```

看到这个就成功了：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ AskDB AI模块已加载
```

**终端 2 - 前端：**

```bash
cd frontend
npm install  # 首次需要
npm run dev
```

看到这个就成功了：
```
VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

### 步骤 4: 登录和索引

1. **打开浏览器** → `http://localhost:5173`

2. **登录系统**
   - 用户名：`admin`
   - 密码：`admin123`

3. **建立索引**（重要！）
   - 点击左侧 **"索引管理"** 按钮
   - 点击 **"开始索引"**
   - 等待完成（1-10 分钟）

### 步骤 5: 开始查询

索引完成后，就可以开始查询了！

**尝试这些问题：**

```
💬 "有多少个用户？"
💬 "查看最近的10个订单"
💬 "本月的销售总额是多少？"
💬 "哪些用户上个月没有登录？"
```

---

## 🎯 核心功能演示

### 1. 自然语言查询

```
你问：上个月注册的新用户有多少？

AI 回答：
📊 上个月共注册了 156 个新用户

执行的 SQL：
SELECT COUNT(*) FROM users 
WHERE DATE_FORMAT(created_at, '%Y-%m') = DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%Y-%m')

解释：统计 users 表中创建时间为上个月的记录数
```

### 2. 语义搜索

```
你问：客户订单信息

AI 自动：
1️⃣ 搜索相关表 → customers, orders
2️⃣ 获取表结构 → customer_id, order_id, amount
3️⃣ 生成 JOIN 查询
4️⃣ 返回结果
```

### 3. 危险操作确认

```
你问：删除所有测试用户

AI 响应：
⚠️ 需要确认的危险操作

操作说明：删除用户名包含 'test' 的所有用户记录
预期影响：将删除约 15 个用户账户

[弹出确认对话框]
→ 必须确认后才会执行
```

---

## ❓ 快速问题排查

### 问题：索引失败

```bash
# 检查数据库连接
python -c "
from tools.agno_tools import db
db.connect()
print('✅ 数据库连接成功' if db.is_connected else '❌ 连接失败')
"
```

### 问题：前端无法访问后端

```bash
# 检查后端是否运行
curl http://localhost:8000/api/public/health

# 应该返回：
# {"status":"healthy","service":"AskDB API",...}
```

### 问题：AI 响应慢

**原因**：
- Gemini API 在海外，可能较慢
- 数据库查询复杂

**解决**：
- 考虑使用本地 LLM（需要配置）
- 优化数据库索引

---

## 📚 更多文档

- 完整部署指南：[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- 功能说明：[README.md](README.md)
- API 文档：访问 `http://localhost:8000/docs`

---

## 🎉 成功标志

如果你看到：

✅ 后端启动成功（端口 8000）  
✅ 前端启动成功（端口 5173）  
✅ 能够登录系统  
✅ 索引完成（显示表数、列数）  
✅ AI 能够回答你的问题  

**恭喜！你已经成功部署 AskDB！** 🚀

现在可以尽情探索了！

---

**小贴士**：

- 💡 复杂问题分步提问效果更好
- 💡 使用完整的句子而不是关键词
- 💡 定期重新索引保持数据新鲜
- 💡 数据库变更后记得重新索引

Happy Querying! 🎊



