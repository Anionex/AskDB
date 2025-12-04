#!/usr/bin/env python3
"""
AskDB Agno Tools - 修复版

修复Web搜索工具的异步冲突问题
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List

from agno.tools import Toolkit
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine

from lib.safety import SafetyManager, RiskLevel
from tools.schema import SchemaManager
from tools.web_search import WebSearchTool, WebSearchError  # 导入修复后的web_search
from rich.prompt import Confirm
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


class DatabaseConnection:
    """数据库连接管理器"""
    
    def __init__(self):
        self.engine: Optional[Engine] = None
        self._connected = False
        self.safety_manager = SafetyManager()
        self.schema_manager: Optional[SchemaManager] = None
        self._semantic_search_enabled = os.getenv("ENABLE_SEMANTIC_SEARCH", "false").lower() == "true"
        self._schema_initialized = False
    
    def connect(self) -> bool:
        """连接数据库"""
        try:
            from dialects.opengauss_dialect import OpenGaussDialect
        except ImportError:
            pass  # 静默失败
        
        db_type = os.getenv("DEFAULT_DB_TYPE", "mysql").lower()
        host = os.getenv("DEFAULT_DB_HOST", "localhost")
        port = os.getenv("DEFAULT_DB_PORT", "3306")
        database = os.getenv("DEFAULT_DB_NAME", "")
        user = os.getenv("DEFAULT_DB_USER", "root")
        password = os.getenv("DEFAULT_DB_PASSWORD", "")
        
        if db_type == "mysql":
            url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        elif db_type == "postgresql":
            url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
        elif db_type == "opengauss":
            url = f"opengauss+psycopg2://{user}:{password}@{host}:{port}/{database}"
        elif db_type == "sqlite":
            url = f"sqlite:///{database}"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
        
        try:
            if db_type == "opengauss":
                self.engine = create_engine(
                    url,
                    connect_args={
                        'sslmode': 'prefer',
                        'application_name': 'AskDB Agent',
                        'connect_timeout': 10,
                        'options': '-c statement_timeout=30000' 
                    },
                    pool_pre_ping=True,  
                    echo=False,  
                    future=True   
                )
            else:
                self.engine = create_engine(url)
            
            # 测试连接
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    self._connected = True
                    return True
                else:
                    raise Exception("连接测试失败")
                    
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            self._connected = False
            return False
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self.engine is not None
    
    def execute_query(self, sql: str, allow_modifications: bool = False) -> dict:
        """执行SQL查询"""
        if not self.is_connected:
            self.connect()
        
        # 安全检查
        safety_result = self.safety_manager.assess_query_safety(sql)
        
        # 检查是否为数据修改操作
        is_modification = any(keyword in sql.upper() for keyword in 
                            ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"])
        
        # 高风险操作需要确认
        if safety_result.overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL] or is_modification:
            if not allow_modifications:
                console.print(f"\n[yellow]⚠️  检测到高风险操作![/yellow]")
                console.print(f"[yellow]风险等级: {safety_result.overall_risk.name.lower()}[/yellow]")
                console.print(f"[yellow]SQL: {sql}[/yellow]")
                
                if not Confirm.ask("是否继续执行?"):
                    return {
                        "success": False,
                        "error": "用户取消操作",
                        "safety_blocked": True
                    }
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                
                if result.returns_rows:
                    columns = list(result.keys())
                    rows = result.fetchall()
                    data = [dict(zip(columns, row)) for row in rows]
                    return {
                        "success": True,
                        "data": data,
                        "row_count": len(data),
                        "sql": sql
                    }
                else:
                    conn.commit()
                    return {
                        "success": True,
                        "data": [],
                        "row_count": result.rowcount,
                        "sql": sql
                    }
        except Exception as e:
            logger.error(f"❌ 查询执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "sql": sql
            }
    
    def get_tables(self) -> list:
        """获取表列表"""
        if not self.is_connected:
            self.connect()
        inspector = inspect(self.engine)
        return inspector.get_table_names()
    
    def get_table_info(self, table_name: str) -> dict:
        """获取表信息"""
        if not self.is_connected:
            self.connect()
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_name)
        pk = inspector.get_pk_constraint(table_name)
        fks = inspector.get_foreign_keys(table_name)
        
        return {
            "table_name": table_name,
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "primary_key": col["name"] in pk.get("constrained_columns", [])
                }
                for col in columns
            ],
            "primary_key": pk.get("constrained_columns", []) if pk else [],
            "foreign_keys": [
                {
                    "columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"]
                }
                for fk in fks
            ]
        }


# 全局数据库连接
db = DatabaseConnection()


class DatabaseTools(Toolkit):
    """数据库工具集"""
    
    def __init__(self):
        super().__init__(
            name="database",
            tools=[
                self.execute_query,
                self.execute_non_query,
                self.list_tables,
                self.describe_table,
                self.search_tables_by_name,
            ]
        )
        self.safety_manager = db.safety_manager
    
    def execute_query(self, sql_query: str) -> str:
        """执行SELECT查询"""
        try:
            result = db.execute_query(sql_query, allow_modifications=False)
            if result["success"]:
                data = result["data"]
                if len(data) > 15:
                    data = data[:15]
                    return json.dumps({
                        "success": True,
                        "data": data,
                        "total_rows": result["row_count"],
                        "note": f"显示前15条，共{result['row_count']}条记录"
                    }, ensure_ascii=False, default=str, indent=2)
                return json.dumps({
                    "success": True,
                    "data": data,
                    "row_count": result["row_count"]
                }, ensure_ascii=False, default=str, indent=2)
            return json.dumps({"success": False, "error": result.get("error", "未知错误")})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def execute_non_query(self, sql_statement: str) -> str:
        """执行数据修改操作"""
        try:
            result = db.execute_query(sql_statement, allow_modifications=True)
            
            if result.get("safety_blocked"):
                return json.dumps({
                    "success": False,
                    "error": "操作被用户或安全系统阻止",
                    "blocked": True
                })
            
            if result["success"]:
                return json.dumps({
                    "success": True,
                    "rows_affected": result.get("row_count", 0),
                    "message": "语句执行成功"
                }, ensure_ascii=False, indent=2)
            return json.dumps({"success": False, "error": result.get("error", "未知错误")})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def list_tables(self) -> str:
        """获取所有表"""
        try:
            tables = db.get_tables()
            return json.dumps({
                "success": True,
                "tables": tables,
                "count": len(tables)
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def describe_table(self, table_name: str) -> str:
        """获取表结构信息"""
        try:
            table_info = db.get_table_info(table_name)
            return json.dumps({
                "success": True,
                "table_info": table_info
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def search_tables_by_name(self, search_query: str, top_k: int = 5) -> str:
        """搜索表"""
        try:
            tables = db.get_tables()
            search_lower = search_query.lower()
            
            # 查找包含搜索词的表
            matching = [t for t in tables if search_lower in t.lower()][:top_k]
            
            # 如果没有直接匹配，查找部分匹配
            if not matching:
                search_words = search_lower.split()
                for table in tables:
                    table_lower = table.lower()
                    if any(word in table_lower for word in search_words):
                        matching.append(table)
                        if len(matching) >= top_k:
                            break
            
            # 获取匹配表的详细信息
            results = []
            for table_name in matching:
                try:
                    table_info = db.get_table_info(table_name)
                    results.append({
                        "table_name": table_name,
                        "columns": [col["name"] for col in table_info.get("columns", [])][:10],
                        "column_count": len(table_info.get("columns", [])),
                        "primary_key": table_info.get("primary_key", [])
                    })
                except:
                    results.append({"table_name": table_name})
            
            return json.dumps({
                "success": True,
                "matching_tables": results,
                "count": len(results),
                "search_method": "simple_name_matching"
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"❌ 表搜索失败: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": "无法搜索表，请检查数据库连接"
            })


class WebSearchTools(Toolkit):
    """修复版Web搜索工具集"""
    
    def __init__(self):
        super().__init__(
            name="web_search",
            tools=[
                self.request_for_internet_search,
            ]
        )
        # 使用修复后的WebSearchTool
        self.web_search_tool = WebSearchTool()
        logger.info("✅ Web搜索工具已初始化（修复版）")

    def request_for_internet_search(self, search_query: str, max_results: int = 5) -> str:
        """修复的Web搜索方法"""
        try:
            # 使用同步搜索避免异步冲突
            results = self.web_search_tool.search_sync(search_query, max_results)
            
            if not results:
                return json.dumps({
                    "success": True,
                    "results": [],
                    "count": 0,
                    "message": "未找到相关结果",
                    "query": search_query
                }, ensure_ascii=False, indent=2)
            
            # 格式化结果
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                    "source": result.source,
                    "relevance_score": result.relevance_score
                })
            
            response_data = {
                "success": True,
                "results": formatted_results,
                "count": len(formatted_results),
                "query": search_query,
                "message": f"成功找到 {len(formatted_results)} 个相关结果"
            }
            
            logger.info(f"✅ Web搜索成功: {search_query}")
            return json.dumps(response_data, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"❌ Web搜索失败: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": "Web搜索功能暂时不可用",
                "query": search_query,
                "results": []
            }, ensure_ascii=False, indent=2)