# AI 行为优化说明

## 问题描述

用户反馈：当要求删除字段时，AI会反问用户"请提供详细的解释和预期影响"，这是不合理的行为。

### 错误示例
```
用户: "删除averagescore字段"
AI: "您想删除 averagescore 字段吗？删除字段是一个数据修改操作，
     请提供详细的解释和预期影响，例如"从 coursestats 表中永久删除 
     averagescore 字段，这可能影响依赖此字段的查询或功能。"
```

## 问题根源

1. **工具参数验证过严**: `execute_non_query_with_explanation` 要求必须提供至少15个字符的解释和10个字符的影响说明
2. **错误消息误导AI**: 当参数不足时返回错误，AI误以为需要向用户询问这些信息
3. **Prompt指导不明确**: 没有明确告诉AI应该自己生成解释，而不是问用户

## 解决方案

### 1. 放宽参数验证 (`tools/enhanced_tools.py`)

**修改前**:
```python
if not explanation or len(explanation.strip()) < 15:
    return json.dumps({
        "success": False,
        "error": "必须提供详细的操作解释（至少15个字符）"
    }, ensure_ascii=False, indent=2)
```

**修改后**:
```python
# 如果缺少解释，自动生成而不是返回错误
if not explanation or len(explanation.strip()) < 5:
    explanation = f"执行SQL操作: {sql_statement[:50]}..."
    logger.warning("缺少详细解释，使用默认值")

if not expected_impact or len(expected_impact.strip()) < 5:
    # 根据SQL类型自动生成影响说明
    sql_upper = sql_statement.upper()
    if 'DROP' in sql_upper:
        expected_impact = "将删除表及其所有数据"
    elif 'DELETE' in sql_upper:
        expected_impact = "将删除符合条件的数据行"
    # ... 其他类型
```

### 2. 更新 AI Prompt (`askdb_agno.py`)

**关键修改**:
```python
### 关于危险操作
1. **DROP/DELETE/TRUNCATE** 会触发用户确认对话框（高危）
2. **CREATE/INSERT/UPDATE/ALTER** 会直接执行（低风险）
3. 调用工具时你必须提供：
   - **explanation**: 你自己生成的详细解释（不要问用户！）
   - **expected_impact**: 你自己生成的影响说明（不要问用户！）
4. 示例：用户说"删除averagescore字段"
   - ✅ 正确：你分析后调用工具，自己生成explanation="从coursestats表中删除averagescore字段"
   - ❌ 错误：反问用户"请提供详细的解释和预期影响"
```

### 3. 增强示例说明

在Prompt中添加了具体的正确/错误示例：

```python
# 用户问："删除averagescore字段"
# 你的分析：这是ALTER TABLE DROP COLUMN操作
execute_non_query_with_explanation(
    sql_statement="ALTER TABLE coursestats DROP COLUMN averagescore",
    explanation="从coursestats表中删除averagescore字段，该字段存储课程的平均分数",
    expected_impact="将永久删除averagescore字段，可能影响依赖此字段的查询和报表"
)
```

## 预期效果

### 优化后的行为

```
用户: "删除averagescore字段"
AI: "好的，我将从coursestats表中删除averagescore字段。
     [调用工具，自动生成解释]
     [对于ALTER操作，直接执行]
     ✅ 操作成功。已删除averagescore字段。"
```

或者（如果是DROP TABLE这种高危操作）：

```
用户: "删除coursestats2表"
AI: "我检测到这是一个高危操作。
     [调用工具，自动生成解释]
     [系统弹出确认对话框]
     [等待用户确认]"
```

## 核心原则

1. **AI应该智能**: 根据用户意图自己生成合理的解释，而不是反问用户
2. **用户体验优先**: 不要让用户提供技术细节，AI应该处理这些
3. **安全与便利平衡**: 
   - 高危操作（DROP/DELETE/TRUNCATE）→ 需要确认
   - 低风险操作（CREATE/INSERT/UPDATE/ALTER）→ 直接执行
4. **容错性**: 即使AI没有提供完美的参数，系统也应该能够正常工作

## 相关文件

- `tools/enhanced_tools.py` - 工具参数验证逻辑
- `askdb_agno.py` - AI Prompt和指导说明
- `DANGER_CONFIRMATION_FLOW.md` - 危险操作确认流程
- `test_confirmation.md` - 测试指南

## 测试验证

测试以下场景确认优化生效：

1. ✅ "删除averagescore字段" - 应该直接执行，不反问用户
2. ✅ "创建一个test表" - 应该直接执行
3. ✅ "删除coursestats2表" - 应该弹出确认框（但不反问用户）
4. ✅ "插入一条测试数据" - 应该直接执行
5. ✅ "删除所有测试数据" - 应该弹出确认框（但不反问用户）

所有情况下，AI都应该**自己生成解释**，而不是向用户询问技术细节。

