"""
Logging utilities for AskDB.

This module provides comprehensive logging configuration and utilities
for the AskDB system, including structured logging, log rotation,
and different log levels for various components.
"""

import logging
import logging.handlers
import os
import sys
import json
import time
from typing import Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime
import threading


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': threading.current_thread().name,
            'process': os.getpid()
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add stack trace if present
        if record.stack_info:
            log_data['stack_trace'] = self.formatStack(record.stack_info)
        
        # Add extra fields if enabled
        if self.include_extra and hasattr(record, '__dict__'):
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info', 'message'
                }:
                    extra_fields[key] = value
            
            if extra_fields:
                log_data['extra'] = extra_fields
        
        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for console logging."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        base_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        if self.use_colors:
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            formatter = logging.Formatter(f'{color}%(asctime)s - %(name)s - %(levelname)s - %(message)s{reset}')
        else:
            formatter = logging.Formatter(base_format)
        
        return formatter.format(record)


class AskDBLogger:
    """Enhanced logger with additional capabilities for AskDB."""
    
    def __init__(self, name: str, logger: logging.Logger):
        self.name = name
        self.logger = logger
        self._context = {}
    
    def set_context(self, **kwargs):
        """Set context information for all subsequent log messages."""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear all context information."""
        self._context.clear()
    
    def _log_with_context(self, level: int, message: str, *args, **kwargs):
        """Log message with current context."""
        if self._context:
            # Add context as extra field
            extra = kwargs.get('extra', {})
            extra['context'] = self._context.copy()
            kwargs['extra'] = extra
        
        self.logger.log(level, message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message."""
        self._log_with_context(logging.INFO, message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message."""
        self._log_with_context(logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """Log exception with traceback."""
        kwargs['exc_info'] = True
        self._log_with_context(logging.ERROR, message, *args, **kwargs)
    
    def log_query(self, query: str, execution_time: float = None, result_count: int = None, error: str = None):
        """Log database query execution."""
        log_data = {
            'query': query,
            'execution_time': execution_time,
            'result_count': result_count,
            'error': error
        }
        
        if error:
            self.error("Query execution failed", extra={'query_info': log_data})
        else:
            self.info("Query executed successfully", extra={'query_info': log_data})
    
    def log_agent_action(self, action_type: str, details: Dict[str, Any]):
        """Log agent action."""
        self.info(f"Agent action: {action_type}", extra={'agent_action': details})
    
    def log_safety_check(self, query: str, risk_level: str, passed: bool, details: Dict[str, Any]):
        """Log safety check results."""
        log_data = {
            'query': query,
            'risk_level': risk_level,
            'passed': passed,
            'details': details
        }
        
        if passed:
            self.info("Safety check passed", extra={'safety_check': log_data})
        else:
            self.warning("Safety check failed", extra={'safety_check': log_data})


class LoggingManager:
    """Central logging manager for AskDB."""
    
    def __init__(self):
        self._loggers: Dict[str, AskDBLogger] = {}
        self._configured = False
        self._config = {}
        self._lock = threading.Lock()
    
    def configure(self, config: Optional[Dict[str, Any]] = None):
        """Configure logging system."""
        with self._lock:
            if self._configured:
                return
            
            # Default configuration
            default_config = {
                'level': 'INFO',
                'format': 'console',  # 'console', 'json', 'both'
                'console_output': True,
                'file_output': False,
                'file_path': 'logs/askdb.log',
                'max_file_size': 10 * 1024 * 1024,  # 10MB
                'backup_count': 5,
                'use_colors': True,
                'structured_format': False,
                'loggers': {
                    'askdb': {'level': 'INFO'},
                    'askdb.agent': {'level': 'INFO'},
                    'askdb.tools': {'level': 'INFO'},
                    'askdb.models': {'level': 'WARNING'},
                    'sqlalchemy.engine': {'level': 'WARNING'},
                    'urllib3.connectionpool': {'level': 'WARNING'}
                }
            }
            
            # Merge with provided config
            self._config = {**default_config, **(config or {})}
            
            # Create logs directory if needed
            if self._config['file_output']:
                log_file = Path(self._config['file_path'])
                log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, self._config['level'].upper()))
            
            # Clear existing handlers
            root_logger.handlers.clear()
            
            # Add console handler if enabled
            if self._config['console_output']:
                console_handler = logging.StreamHandler(sys.stdout)
                
                if self._config['format'] == 'json':
                    console_handler.setFormatter(StructuredFormatter())
                else:
                    console_handler.setFormatter(ColoredFormatter(self._config['use_colors']))
                
                console_handler.setLevel(getattr(logging, self._config['level'].upper()))
                root_logger.addHandler(console_handler)
            
            # Add file handler if enabled
            if self._config['file_output']:
                file_handler = logging.handlers.RotatingFileHandler(
                    self._config['file_path'],
                    maxBytes=self._config['max_file_size'],
                    backupCount=self._config['backup_count']
                )
                
                if self._config['structured_format']:
                    file_handler.setFormatter(StructuredFormatter())
                else:
                    file_handler.setFormatter(
                        logging.Formatter(
                            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                        )
                    )
                
                file_handler.setLevel(getattr(logging, self._config['level'].upper()))
                root_logger.addHandler(file_handler)
            
            # Configure specific loggers
            for logger_name, logger_config in self._config['loggers'].items():
                logger = logging.getLogger(logger_name)
                logger.setLevel(getattr(logging, logger_config['level'].upper()))
            
            self._configured = True
    
    def get_logger(self, name: str) -> AskDBLogger:
        """Get enhanced logger instance."""
        with self._lock:
            if name not in self._loggers:
                if not self._configured:
                    self.configure()
                
                base_logger = logging.getLogger(name)
                self._loggers[name] = AskDBLogger(name, base_logger)
            
            return self._loggers[name]
    
    def get_config(self) -> Dict[str, Any]:
        """Get current logging configuration."""
        return self._config.copy()
    
    def update_config(self, **kwargs):
        """Update logging configuration."""
        with self._lock:
            self._config.update(kwargs)
            # Reconfigure with new settings
            self._configured = False
            self.configure()
    
    def set_level(self, level: Union[str, int], logger_name: Optional[str] = None):
        """Set logging level for specific logger or root logger."""
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        
        if logger_name:
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
        else:
            logging.getLogger().setLevel(level)
    
    def add_file_handler(self, file_path: str, level: str = 'INFO', 
                        structured: bool = False):
        """Add additional file handler."""
        if not self._configured:
            self.configure()
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(file_path)
        
        if structured:
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
        
        handler.setLevel(getattr(logging, level.upper()))
        logging.getLogger().addHandler(handler)
    
    def remove_all_handlers(self):
        """Remove all handlers from root logger."""
        logging.getLogger().handlers.clear()


# Global logging manager instance
_logging_manager = LoggingManager()


def setup_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """Setup logging configuration for the application."""
    _logging_manager.configure(config)


def get_logger(name: str) -> AskDBLogger:
    """Get enhanced logger instance."""
    return _logging_manager.get_logger(name)


def get_log_config() -> Dict[str, Any]:
    """Get current logging configuration."""
    return _logging_manager.get_config()


def configure_logging(config: Dict[str, Any]) -> None:
    """Configure logging with custom settings."""
    _logging_manager.update_config(**config)


def set_log_level(level: Union[str, int], logger_name: Optional[str] = None) -> None:
    """Set logging level for specific logger or root logger."""
    _logging_manager.set_level(level, logger_name)


def add_log_file(file_path: str, level: str = 'INFO', structured: bool = False) -> None:
    """Add additional log file handler."""
    _logging_manager.add_file_handler(file_path, level, structured)


def log_performance(func_name: str, execution_time: float, details: Optional[Dict[str, Any]] = None):
    """Log performance metrics."""
    logger = get_logger('askdb.performance')
    
    log_data = {
        'function': func_name,
        'execution_time': execution_time,
        'details': details or {}
    }
    
    if execution_time > 5.0:  # Log as warning if slow
        logger.warning(f"Slow execution: {func_name}", extra={'performance': log_data})
    else:
        logger.info(f"Performance: {func_name}", extra={'performance': log_data})


class LogContext:
    """Context manager for temporary log context."""
    
    def __init__(self, logger: AskDBLogger, **context):
        self.logger = logger
        self.context = context
        self.old_context = {}
    
    def __enter__(self):
        self.old_context = self.logger._context.copy()
        self.logger.set_context(**self.context)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger._context.clear()
        self.logger.set_context(**self.old_context)


def with_log_context(logger: AskDBLogger, **context):
    """Create log context manager."""
    return LogContext(logger, **context)


# Convenience functions for common logging patterns
def log_function_call(func_name: str, args: tuple = (), kwargs: dict = None):
    """Log function call with arguments."""
    logger = get_logger('askdb.tracing')
    logger.debug(f"Calling function: {func_name}", extra={
        'function_call': {
            'function': func_name,
            'args': args,
            'kwargs': kwargs or {}
        }
    })


def log_function_return(func_name: str, result: Any = None, execution_time: float = None):
    """Log function return with result and timing."""
    logger = get_logger('askdb.tracing')
    logger.debug(f"Function returned: {func_name}", extra={
        'function_return': {
            'function': func_name,
            'result_type': type(result).__name__ if result is not None else None,
            'execution_time': execution_time
        }
    })


def log_error_with_context(error: Exception, context: Dict[str, Any]):
    """Log error with additional context."""
    logger = get_logger('askdb.errors')
    logger.exception(f"Error occurred: {str(error)}", extra={'error_context': context})