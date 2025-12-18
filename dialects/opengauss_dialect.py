"""
Custom SQLAlchemy dialect for openGauss database.
Fixes version parsing issues with openGauss 6.0.0+
"""

from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
from sqlalchemy import text
import re
import logging

logger = logging.getLogger(__name__)

class OpenGaussDialect(PGDialect_psycopg2):
    """Custom dialect for Huawei openGauss database."""
    
    name = 'opengauss'
    driver = 'psycopg2'

    supports_statement_cache = True
    
    # 🆕 覆盖版本解析方法
    def _get_server_version_info(self, connection):
        """
        Fix openGauss version string parsing.
        openGauss returns: '(openGauss 6.0.0 build aee4abd5) compiled at ...'
        But SQLAlchemy expects: 'PostgreSQL 14.5 on ...'
        """
        try:
            # 执行版本查询
            version_str = connection.scalar(text("SELECT version()"))
            
            if not version_str:
                logger.warning("Empty version string, using default version 6.0.0")
                return (6, 0, 0)  # 默认版本
                
            # 🎯 解析 openGauss 特有的版本格式
            # 示例: '(openGauss 6.0.0 build aee4abd5) compiled at ...'
            match = re.search(r'openGauss\s+(\d+)\.(\d+)\.(\d+)', version_str)
            if match:
                major, minor, patch = match.groups()
                version_info = (int(major), int(minor), int(patch))
                return version_info
            else:
                # 尝试其他可能的格式
                match = re.search(r'(\d+)\.(\d+)\.(\d+)', version_str)
                if match:
                    major, minor, patch = match.groups()
                    version_info = (int(major), int(minor), int(patch))
                    return version_info
                
                logger.warning(f"Could not parse version string, using default 6.0.0. String: {version_str}")
                return (6, 0, 0)  # 默认版本
                
        except Exception as e:
            logger.warning(f"Version parsing failed, using default 6.0.0. Error: {e}")
            return (6, 0, 0)  # 出错时返回默认版本

# 🆕 简化的注册方式
def register_dialect():  # ✅ 正确的函数名
    """注册方言到 SQLAlchemy"""
    try:
        from sqlalchemy.dialects import registry
        # 注册方言
        registry.register("opengauss", __name__, "OpenGaussDialect")
        registry.register("opengauss.psycopg2", __name__, "OpenGaussDialect")
        print("✅ openGauss dialect registered successfully")
    except Exception as e:
        print(f"❌ Failed to register openGauss dialect: {e}")

# 自动注册
register_dialect()  # ✅ 正确的函数调用