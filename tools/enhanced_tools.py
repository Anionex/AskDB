#!/usr/bin/env python3
"""
Enhanced Agent Tools with Vector Retrieval
集成向量检索的增强版数据库工具
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from agno.tools import Toolkit
from tools.agno_tools import db, DatabaseConnection
from tools.vector_store import vector_store, SearchResult

logger = logging.getLogger(__name__)


class EnhancedDatabaseTools(Toolkit):
    """增强版数据库工具集 - 集成向量检索"""
    
    def __init__(self, user_context: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="enhanced_database",
            tools=[
                self.semantic_search_schema,
                self.execute_query_with_explanation,
                self.execute_non_query_with_explanation,
                self.get_table_ddl,
                self.list_all_tables,
            ]
        )
        self.db = db
        self.vector_store = vector_store
        self.user_context = user_context
        if user_context:
            db.set_user_context(user_context)
    
    def semantic_search_schema(self, query: str, top_k: int = 5) -> str:
        """
        语义搜索数据库架构（表、列、业务术语）
        
        使用向量检索找到与查询最相关的表和字段。
        这是查询前的第一步 - 先找到相关的表和字段，再获取完整的 DDL。
        
        Args:
            query: 自然语言查询，例如 "客户订单信息"、"用户消费金额"
            top_k: 返回前 K 个最相关的结果
        
        Returns:
            JSON 格式的搜索结果，包含相关的表、列、业务术语
        """
        try:
            # 执行向量检索
            results = self.vector_store.search(
                query=query,
                top_k=top_k,
                search_types=["table", "column", "business_term"]
            )
            
            if not results:
                return json.dumps({
                    "success": True,
                    "found": False,
                    "message": "未找到相关的表或字段",
                    "suggestion": "请尝试使用不同的关键词，或使用 list_all_tables 查看所有可用的表"
                }, ensure_ascii=False, indent=2)
            
            # 分类整理结果
            tables = []
            columns = []
            business_terms = []
            
            for result in results:
                if result.item_type == "table":
                    tables.append({
                        "table_name": result.name,
                        "relevance": round(result.similarity, 3),
                        "column_count": result.metadata.get("column_count", 0),
                        "has_foreign_keys": result.metadata.get("has_foreign_keys", False)
                    })
                elif result.item_type == "column":
                    columns.append({
                        "full_name": result.name,
                        "table": result.metadata.get("table_name"),
                        "column": result.metadata.get("column_name"),
                        "data_type": result.metadata.get("data_type"),
                        "relevance": round(result.similarity, 3),
                        "is_primary_key": result.metadata.get("is_primary_key", False),
                        "is_foreign_key": result.metadata.get("is_foreign_key", False)
                    })
                elif result.item_type == "business_term":
                    business_terms.append({
                        "term": result.name,
                        "definition": result.metadata.get("definition", ""),
                        "formula": result.metadata.get("formula", ""),
                        "related_tables": json.loads(result.metadata.get("related_tables", "[]")),
                        "related_columns": json.loads(result.metadata.get("related_columns", "[]")),
                        "relevance": round(result.similarity, 3)
                    })
            
            # 提取最相关的表名（从 tables 和 columns 中提取，保持顺序）
            seen_tables = set()
            relevant_tables = []
            for t in tables:
                if t["table_name"] not in seen_tables:
                    relevant_tables.append(t["table_name"])
                    seen_tables.add(t["table_name"])
            for c in columns:
                if c["table"] not in seen_tables:
                    relevant_tables.append(c["table"])
                    seen_tables.add(c["table"])
            
            response = {
                "success": True,
                "found": True,
                "query": query,
                "relevant_tables": relevant_tables[:8],  # 增加返回数量
                "tables": tables[:5],  # 增加返回数量
                "columns": columns[:5],
                "business_terms": business_terms[:3],
                "next_step": f"使用 get_table_ddl 获取这些表的完整结构: {', '.join(relevant_tables[:5])}"
            }
            
            return json.dumps(response, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": "语义搜索失败，请使用 list_all_tables 查看所有表"
            }, ensure_ascii=False, indent=2)
    
    def get_table_ddl(self, table_names: str) -> str:
        """
        获取表的完整 DDL（包含主键、外键、索引等详细信息）
        
        在语义搜索找到相关表后，使用此工具获取完整的表结构信息。
        
        Args:
            table_names: 逗号分隔的表名列表，例如 "users,orders"
        
        Returns:
            JSON 格式的完整表结构信息
        """
        try:
            tables = [t.strip() for t in table_names.split(',')]
            results = []
            
            for table_name in tables:
                try:
                    table_info = self.db.get_table_info(table_name)
                    
                    # 格式化列信息
                    columns_detail = []
                    for col in table_info.get("columns", []):
                        col_str = f"{col['name']} {col['type']}"
                        if col.get('primary_key'):
                            col_str += " PRIMARY KEY"
                        if not col.get('nullable', True):
                            col_str += " NOT NULL"
                        columns_detail.append(col_str)
                    
                    # 格式化外键信息
                    foreign_keys_detail = []
                    for fk in table_info.get("foreign_keys", []):
                        fk_desc = f"FK: {','.join(fk['columns'])} -> {fk['referred_table']}.{','.join(fk['referred_columns'])}"
                        foreign_keys_detail.append(fk_desc)
                    
                    results.append({
                        "table_name": table_name,
                        "columns": columns_detail,
                        "primary_key": table_info.get("primary_key", []),
                        "foreign_keys": foreign_keys_detail,
                        "column_count": len(table_info.get("columns", []))
                    })
                    
                except Exception as e:
                    results.append({
                        "table_name": table_name,
                        "error": f"无法获取表信息: {str(e)}"
                    })
            
            return json.dumps({
                "success": True,
                "tables": results
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False, indent=2)
    
    def execute_query_with_explanation(self, sql_query: str, explanation: str) -> str:
        """
        执行 SELECT 查询并提供解释
        
        Args:
            sql_query: SQL SELECT 语句
            explanation: 用自然语言解释这个查询在做什么（必须提供！）
        
        Returns:
            包含查询结果和解释的 JSON
        """
        try:
            if not explanation or len(explanation.strip()) < 10:
                return json.dumps({
                    "success": False,
                    "error": "必须提供清晰的查询解释（至少10个字符）"
                }, ensure_ascii=False, indent=2)
            
            # 执行查询（带权限控制）
            result = self.db.execute_query(sql_query, allow_modifications=False, user_context=self.user_context)
            
            # 检查权限拒绝
            if result.get("permission_denied"):
                return json.dumps({
                    "success": False,
                    "explanation": explanation,
                    "sql": sql_query,
                    "error": result.get("error", "权限被拒绝"),
                    "permission_denied": True,
                    "message": "您没有权限执行此查询"
                }, ensure_ascii=False, indent=2)
            
            if result["success"]:
                data = result["data"]
                row_count = result["row_count"]
                
                # 限制返回数据量
                if len(data) > 15:
                    data = data[:15]
                    truncated = True
                else:
                    truncated = False
                
                response = {
                    "success": True,
                    "explanation": explanation,
                    "sql": sql_query,
                    "data": data,
                    "row_count": row_count,
                    "truncated": truncated,
                    "message": f"查询成功。{explanation}"
                }
                
                # 添加权限警告
                if result.get("warnings"):
                    response["warnings"] = result["warnings"]
                if result.get("transformed"):
                    response["security_note"] = "查询已根据您的权限进行过滤"
                
                return json.dumps(response, ensure_ascii=False, default=str, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "explanation": explanation,
                    "sql": sql_query,
                    "error": result.get("error", "未知错误"),
                    "message": f"查询失败: {result.get('error', '未知错误')}"
                }, ensure_ascii=False, indent=2)
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "sql": sql_query,
                "explanation": explanation
            }, ensure_ascii=False, indent=2)
    
    def execute_non_query_with_explanation(self, sql_statement: str, explanation: str, 
                                          expected_impact: str) -> str:
        """
        执行数据修改操作（INSERT/UPDATE/DELETE）并提供详细解释
        
        **重要**: 对于Web应用，此方法会返回需要用户确认的请求，而不是直接执行。
        
        Args:
            sql_statement: SQL 修改语句
            explanation: 用自然语言解释这个操作在做什么（必须提供！）
            expected_impact: 预期影响，例如 "将修改约10条记录" （必须提供！）
        
        Returns:
            包含确认请求信息的 JSON
        """
        try:
            # 参数验证：如果缺少解释，使用默认值而不是返回错误
            if not explanation or len(explanation.strip()) < 5:
                explanation = f"执行SQL操作: {sql_statement[:50]}..."
                logger.warning("缺少详细解释，使用默认值")
            
            if not expected_impact or len(expected_impact.strip()) < 5:
                # 尝试从SQL推断影响
                sql_upper = sql_statement.upper()
                if 'DROP' in sql_upper:
                    expected_impact = "将删除表及其所有数据"
                elif 'DELETE' in sql_upper:
                    expected_impact = "将删除符合条件的数据行"
                elif 'TRUNCATE' in sql_upper:
                    expected_impact = "将清空表中的所有数据"
                elif 'UPDATE' in sql_upper:
                    expected_impact = "将更新符合条件的数据行"
                elif 'INSERT' in sql_upper:
                    expected_impact = "将插入新的数据行"
                elif 'CREATE' in sql_upper:
                    expected_impact = "将创建新的数据库对象"
                elif 'ALTER' in sql_upper:
                    expected_impact = "将修改表结构"
                else:
                    expected_impact = "将执行数据库修改操作"
                logger.warning(f"缺少影响说明，自动生成: {expected_impact}")
            
            # 🔒 先进行权限检查
            # 创建一个测试查询来检查权限（不实际执行）
            from lib.permissions import get_permission_checker, PermissionDeniedException
            try:
                permission_checker = get_permission_checker()
                if self.user_context and self.user_context.get('username'):
                    # 只进行权限检查，不转换SQL
                    _, warnings = permission_checker.check_and_transform_query(
                        sql_statement,
                        self.user_context.get('username'),
                        self.user_context.get('user_type')
                    )
            except PermissionDeniedException as e:
                return json.dumps({
                    "success": False,
                    "explanation": explanation,
                    "expected_impact": expected_impact,
                    "sql": sql_statement,
                    "error": str(e),
                    "permission_denied": True,
                    "message": "您没有权限执行此操作"
                }, ensure_ascii=False, indent=2)
            
            # 🔒 根据操作类型判断是否需要确认
            sql_upper = sql_statement.upper()
            
            # 真正的高危操作：会删除或清空数据
            is_critical = any(keyword in sql_upper for keyword in ['DROP', 'DELETE', 'TRUNCATE'])
            
            if is_critical:
                # 高危操作：需要用户确认
                return json.dumps({
                    "success": False,
                    "needs_confirmation": True,
                    "sql": sql_statement,
                    "explanation": explanation,
                    "expected_impact": expected_impact,
                    "message": "⚠️ 这是高危操作（会删除数据），需要用户确认。",
                    "risk_level": "critical"
                }, ensure_ascii=False, indent=2)
            else:
                # 低风险操作（CREATE/INSERT/UPDATE/ALTER）：直接执行
                logger.info(f"执行低风险操作: {sql_statement[:100]}...")
                result = self.db.execute_query(sql_statement, allow_modifications=True)
                
                if result.get("safety_blocked"):
                    return json.dumps({
                        "success": False,
                        "blocked": True,
                        "explanation": explanation,
                        "expected_impact": expected_impact,
                        "sql": sql_statement,
                        "error": "操作被安全系统阻止",
                        "message": "操作被安全系统阻止"
                    }, ensure_ascii=False, indent=2)
                
                if result["success"]:
                    return json.dumps({
                        "success": True,
                        "explanation": explanation,
                        "expected_impact": expected_impact,
                        "sql": sql_statement,
                        "rows_affected": result.get("row_count", 0),
                        "message": f"✅ 操作成功。{explanation}。实际影响: {result.get('row_count', 0)} 行"
                    }, ensure_ascii=False, indent=2)
                else:
                    return json.dumps({
                        "success": False,
                        "explanation": explanation,
                        "expected_impact": expected_impact,
                        "sql": sql_statement,
                        "error": result.get("error", "未知错误")
                    }, ensure_ascii=False, indent=2)
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "sql": sql_statement,
                "explanation": explanation,
                "expected_impact": expected_impact
            }, ensure_ascii=False, indent=2)
    
    def list_all_tables(self) -> str:
        """
        列出数据库中的所有表
        
        Returns:
            JSON 格式的表列表
        """
        try:
            tables = self.db.get_tables()
            return json.dumps({
                "success": True,
                "tables": tables,
                "count": len(tables),
                "message": f"数据库中共有 {len(tables)} 个表"
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False, indent=2)



