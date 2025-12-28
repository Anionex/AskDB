#!/usr/bin/env python3
"""
数据脱敏与行级权限控制模块

实现基于用户角色的动态权限控制和数据脱敏
"""

import os
import re
import logging
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
import yaml
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Token
from sqlparse.tokens import Keyword, DML

logger = logging.getLogger(__name__)


class PermissionDeniedException(Exception):
    """权限被拒绝异常"""
    pass


class PermissionConfig:
    """权限配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化权限配置
        
        Args:
            config_path: 配置文件路径，默认为 config/permissions.yaml
        """
        if config_path is None:
            # 默认配置文件路径
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "permissions.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.enabled = self.config.get("global_settings", {}).get("enabled", True)
        self.log_checks = self.config.get("global_settings", {}).get("log_checks", True)
        self.verbose_errors = self.config.get("global_settings", {}).get("verbose_errors", True)
        
        logger.info(f"权限配置已加载: {self.config_path} (启用: {self.enabled})")
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                logger.warning(f"权限配置文件不存在: {self.config_path}")
                return self._get_default_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config or self._get_default_config()
        
        except Exception as e:
            logger.error(f"加载权限配置失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "permissions": [],
            "default_permission": {
                "allowed_columns": [],
                "row_filter": "1=0",
                "forbidden_columns": None
            },
            "global_settings": {
                "enabled": True,
                "log_checks": True,
                "verbose_errors": True,
                "access_denied_message": "您没有权限访问此数据"
            }
        }
    
    def reload(self):
        """重新加载配置"""
        self.config = self._load_config()
        logger.info("权限配置已重新加载")
    
    def get_table_permissions(self, table_name: str, username: str) -> Dict[str, Any]:
        """
        获取用户对指定表的权限
        
        Args:
            table_name: 表名
            username: 用户名
            
        Returns:
            权限配置字典
        """
        # 查找表的权限配置
        for table_perm in self.config.get("permissions", []):
            if table_perm["table"].lower() == table_name.lower():
                # 查找匹配的角色
                for role in table_perm.get("roles", []):
                    role_pattern = role.get("role_pattern", "")
                    if re.match(role_pattern, username):
                        permission = {
                            "allowed_columns": role.get("allowed_columns"),
                            "row_filter": role.get("row_filter"),
                            "forbidden_columns": role.get("forbidden_columns", [])
                        }
                        
                        # 替换占位符
                        if permission["row_filter"]:
                            permission["row_filter"] = permission["row_filter"].replace(
                                "{username}", username
                            )
                        
                        if self.log_checks:
                            logger.info(
                                f"权限匹配: 用户={username}, 表={table_name}, "
                                f"角色模式={role_pattern}, 行过滤={permission['row_filter']}"
                            )
                        
                        return permission
        
        # 没有找到匹配的权限，返回默认权限
        default_perm = self.config.get("default_permission", {})
        if self.log_checks:
            logger.warning(
                f"未找到权限配置，使用默认权限: 用户={username}, 表={table_name}"
            )
        return default_perm


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化权限检查器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = PermissionConfig(config_path)
    
    def check_and_transform_query(
        self, 
        sql: str, 
        username: str,
        user_type: Optional[str] = None
    ) -> Tuple[str, List[str]]:
        """
        检查SQL查询并应用权限控制
        
        Args:
            sql: 原始SQL查询
            username: 用户名
            user_type: 用户类型（可选）
            
        Returns:
            (转换后的SQL, 警告信息列表)
            
        Raises:
            PermissionDeniedException: 当用户没有权限时
        """
        if not self.config.enabled:
            return sql, []
        
        # 解析SQL
        parsed = sqlparse.parse(sql)
        if not parsed:
            return sql, []
        
        statement = parsed[0]
        
        # 检查SQL类型
        sql_type = statement.get_type()
        
        # 只处理SELECT查询的权限控制
        if sql_type != 'SELECT':
            # 对于非SELECT查询，可以在这里添加额外的权限检查
            if self.config.log_checks:
                logger.info(f"非SELECT查询，跳过行级权限控制: {sql_type}")
            return sql, []
        
        # 提取表名
        tables = self._extract_tables(statement)
        
        if not tables:
            return sql, []
        
        # 转换查询
        transformed_sql, warnings = self._transform_query(sql, tables, username)
        
        return transformed_sql, warnings
    
    def _extract_tables(self, statement) -> List[str]:
        """从SQL语句中提取表名"""
        tables = []
        from_seen = False
        
        for token in statement.tokens:
            if from_seen:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        tables.append(self._extract_table_name(identifier))
                elif isinstance(token, Identifier):
                    tables.append(self._extract_table_name(token))
                elif token.ttype is Keyword:
                    # 遇到其他关键字，停止提取
                    break
            
            if token.ttype is Keyword and token.value.upper() == 'FROM':
                from_seen = True
        
        return tables
    
    def _extract_table_name(self, identifier) -> str:
        """从Identifier中提取表名"""
        name = str(identifier)
        # 移除别名
        if ' ' in name:
            name = name.split()[0]
        # 移除引号
        name = name.strip('`"\'[]')
        return name
    
    def _transform_query(
        self, 
        sql: str, 
        tables: List[str], 
        username: str
    ) -> Tuple[str, List[str]]:
        """
        转换查询以应用权限控制
        
        Args:
            sql: 原始SQL
            tables: 表名列表
            username: 用户名
            
        Returns:
            (转换后的SQL, 警告信息列表)
        """
        warnings = []
        
        # 获取所有表的权限
        table_permissions = {}
        for table in tables:
            perm = self.config.get_table_permissions(table, username)
            table_permissions[table] = perm
            
            # 检查是否完全禁止访问
            allowed_columns = perm.get("allowed_columns")
            if allowed_columns is not None and len(allowed_columns) == 0:
                raise PermissionDeniedException(
                    f"您没有权限访问表 '{table}'"
                )
        
        # 应用行级过滤
        transformed_sql = self._apply_row_filters(sql, table_permissions)
        
        # 记录转换
        if self.config.log_checks and transformed_sql != sql:
            logger.info(f"SQL已转换:\n原始: {sql}\n转换后: {transformed_sql}")
            warnings.append("已应用行级权限过滤")
        
        return transformed_sql, warnings
    
    def _apply_row_filters(
        self, 
        sql: str, 
        table_permissions: Dict[str, Dict]
    ) -> str:
        """
        应用行级过滤条件
        
        Args:
            sql: 原始SQL
            table_permissions: 表权限字典
            
        Returns:
            转换后的SQL
        """
        # 收集所有需要应用的过滤条件
        filters = []
        for table, perm in table_permissions.items():
            row_filter = perm.get("row_filter")
            if row_filter:
                filters.append(f"({row_filter})")
        
        if not filters:
            return sql
        
        # 组合过滤条件
        combined_filter = " AND ".join(filters)
        
        # 使用简单的字符串处理方法（更可靠）
        sql_upper = sql.upper()
        
        # 查找WHERE关键字的位置
        where_pos = sql_upper.find(' WHERE ')
        
        if where_pos != -1:
            # 已有WHERE子句，在WHERE后面添加AND条件
            # 找到WHERE后的位置
            where_end = where_pos + 7  # len(' WHERE ')
            
            # 查找是否有ORDER BY, GROUP BY, HAVING, LIMIT等子句
            # 这些子句应该在WHERE条件之后
            order_pos = sql_upper.find(' ORDER BY', where_end)
            group_pos = sql_upper.find(' GROUP BY', where_end)
            having_pos = sql_upper.find(' HAVING', where_end)
            limit_pos = sql_upper.find(' LIMIT', where_end)
            
            # 找到最早出现的子句位置
            end_positions = [p for p in [order_pos, group_pos, having_pos, limit_pos] if p != -1]
            
            if end_positions:
                # 在WHERE和下一个子句之间插入条件
                insert_pos = min(end_positions)
                existing_condition = sql[where_end:insert_pos].strip()
                new_sql = (
                    sql[:where_end] + 
                    f" ({existing_condition}) AND {combined_filter} " +
                    sql[insert_pos:]
                )
            else:
                # WHERE子句后面没有其他子句
                existing_condition = sql[where_end:].strip()
                new_sql = sql[:where_end] + f" ({existing_condition}) AND {combined_filter}"
            
            return new_sql
        else:
            # 没有WHERE子句，需要添加
            # 查找合适的插入位置（在FROM子句之后，ORDER BY等之前）
            order_pos = sql_upper.find(' ORDER BY')
            group_pos = sql_upper.find(' GROUP BY')
            having_pos = sql_upper.find(' HAVING')
            limit_pos = sql_upper.find(' LIMIT')
            union_pos = sql_upper.find(' UNION')
            
            # 找到最早出现的子句位置
            end_positions = [p for p in [order_pos, group_pos, having_pos, limit_pos, union_pos] if p != -1]
            
            if end_positions:
                insert_pos = min(end_positions)
                new_sql = sql[:insert_pos] + f" WHERE {combined_filter} " + sql[insert_pos:]
            else:
                # 没有其他子句，直接在末尾添加WHERE
                new_sql = sql.rstrip() + f" WHERE {combined_filter}"
            
            return new_sql
    
    def check_column_access(
        self,
        table_name: str,
        column_name: str,
        username: str
    ) -> bool:
        """
        检查用户是否有权访问特定列
        
        Args:
            table_name: 表名
            column_name: 列名
            username: 用户名
            
        Returns:
            是否允许访问
        """
        perm = self.config.get_table_permissions(table_name, username)
        
        # 检查是否在禁止列表中
        forbidden_columns = perm.get("forbidden_columns", [])
        if forbidden_columns and column_name in forbidden_columns:
            return False
        
        # 检查是否在允许列表中
        allowed_columns = perm.get("allowed_columns")
        if allowed_columns is None:
            # None表示允许所有列
            return True
        elif len(allowed_columns) == 0:
            # 空列表表示不允许任何列
            return False
        else:
            # 检查是否在允许列表中
            return column_name in allowed_columns


# 全局权限检查器实例
_permission_checker: Optional[PermissionChecker] = None


def get_permission_checker() -> PermissionChecker:
    """获取全局权限检查器实例"""
    global _permission_checker
    if _permission_checker is None:
        _permission_checker = PermissionChecker()
    return _permission_checker


def reload_permissions():
    """重新加载权限配置"""
    global _permission_checker
    if _permission_checker is not None:
        _permission_checker.config.reload()
    else:
        _permission_checker = PermissionChecker()

