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
    
    def __init__(self):
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
            
            # 提取最相关的表名
            relevant_tables = list(set([t["table_name"] for t in tables] + 
                                      [c["table"] for c in columns]))
            
            response = {
                "success": True,
                "found": True,
                "query": query,
                "relevant_tables": relevant_tables[:5],
                "tables": tables[:3],
                "columns": columns[:5],
                "business_terms": business_terms[:2],
                "next_step": f"使用 get_table_ddl 获取这些表的完整结构: {', '.join(relevant_tables[:3])}"
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
            
            # 执行查询
            result = self.db.execute_query(sql_query, allow_modifications=False)
            
            if result["success"]:
                data = result["data"]
                row_count = result["row_count"]
                
                # 限制返回数据量
                if len(data) > 15:
                    data = data[:15]
                    truncated = True
                else:
                    truncated = False
                
                return json.dumps({
                    "success": True,
                    "explanation": explanation,
                    "sql": sql_query,
                    "data": data,
                    "row_count": row_count,
                    "truncated": truncated,
                    "message": f"查询成功。{explanation}"
                }, ensure_ascii=False, default=str, indent=2)
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
        
        **警告**: 这是危险操作！必须提供清晰的解释和影响评估。
        
        Args:
            sql_statement: SQL 修改语句
            explanation: 用自然语言解释这个操作在做什么（必须提供！）
            expected_impact: 预期影响，例如 "将修改约10条记录" （必须提供！）
        
        Returns:
            包含执行结果、解释和影响的 JSON
        """
        try:
            if not explanation or len(explanation.strip()) < 15:
                return json.dumps({
                    "success": False,
                    "error": "必须提供详细的操作解释（至少15个字符）"
                }, ensure_ascii=False, indent=2)
            
            if not expected_impact or len(expected_impact.strip()) < 10:
                return json.dumps({
                    "success": False,
                    "error": "必须提供预期影响说明（至少10个字符）"
                }, ensure_ascii=False, indent=2)
            
            # 执行修改操作（会触发安全检查和用户确认）
            result = self.db.execute_query(sql_statement, allow_modifications=True)
            
            if result.get("safety_blocked"):
                return json.dumps({
                    "success": False,
                    "blocked": True,
                    "explanation": explanation,
                    "expected_impact": expected_impact,
                    "sql": sql_statement,
                    "error": "操作被用户或安全系统阻止",
                    "message": "用户拒绝执行此危险操作"
                }, ensure_ascii=False, indent=2)
            
            if result["success"]:
                return json.dumps({
                    "success": True,
                    "explanation": explanation,
                    "expected_impact": expected_impact,
                    "sql": sql_statement,
                    "rows_affected": result.get("row_count", 0),
                    "message": f"操作成功。{explanation}。实际影响: {result.get('row_count', 0)} 行"
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



