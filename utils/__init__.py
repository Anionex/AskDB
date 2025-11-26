"""
AskDB Utilities Module

This module provides utility functions and helpers for the AskDB system,
including logging configuration, helper functions, and common utilities.
"""

from utils.logging import setup_logging, get_logger, get_log_config, configure_logging
from utils.helpers import (
    format_query_result,
    validate_query_input,
    sanitize_sql_query,
    extract_sql_from_text,
    format_error_message,
    calculate_query_complexity,
    truncate_text,
    safe_json_loads,
    safe_json_dumps,
    generate_unique_id,
    parse_time_duration,
    format_bytes,
    validate_email,
    validate_url,
    clean_text,
    extract_keywords,
    calculate_similarity,
    retry_with_backoff,
    timeout_handler,
    rate_limiter,
    cache_result,
    measure_time,
    async_measure_time
)

__version__ = "1.0.0"
__author__ = "AskDB Development Team"
__description__ = "Utility functions and helpers for AskDB"

# Export all utility functions and classes
__all__ = [
    # Logging utilities
    "setup_logging",
    "get_logger", 
    "get_log_config",
    "configure_logging",
    
    # Helper functions
    "format_query_result",
    "validate_query_input",
    "sanitize_sql_query",
    "extract_sql_from_text",
    "format_error_message",
    "calculate_query_complexity",
    "truncate_text",
    "safe_json_loads",
    "safe_json_dumps",
    "generate_unique_id",
    "parse_time_duration",
    "format_bytes",
    "validate_email",
    "validate_url",
    "clean_text",
    "extract_keywords",
    "calculate_similarity",
    "retry_with_backoff",
    "timeout_handler",
    "rate_limiter",
    "cache_result",
    "measure_time",
    "async_measure_time"
]

# Module initialization
def _initialize_utils():
    """Initialize the utils module."""
    try:
        # Setup default logging if not already configured
        import logging
        if not logging.getLogger().handlers:
            setup_logging()
        
        # Log module initialization
        logger = get_logger(__name__)
        logger.info("AskDB Utils module initialized successfully")
        
    except Exception as e:
        # Fallback logging if setup fails
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.warning(f"Utils module initialization completed with warnings: {e}")

# Initialize the module
_initialize_utils()