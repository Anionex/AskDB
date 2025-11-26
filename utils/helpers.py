"""
Utility functions and helpers for AskDB.

This module provides a comprehensive collection of helper functions for
query processing, validation, formatting, error handling, and performance
measurement used throughout the AskDB system.
"""

import re
import json
import time
import uuid
import hashlib
import asyncio
import functools
import urllib.parse
import unicodedata
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


def format_query_result(result: Any, format_type: str = "table") -> str:
    """
    Format database query results into different output formats.
    
    Args:
        result: Query result to format
        format_type: Output format ("table", "json", "csv", "markdown")
        
    Returns:
        Formatted result string
    """
    if result is None:
        return "No results"
    
    if format_type.lower() == "json":
        if isinstance(result, (list, dict)):
            return json.dumps(result, indent=2, default=str)
        else:
            return json.dumps({"result": str(result)}, indent=2)
    
    elif format_type.lower() == "csv":
        if isinstance(result, list) and result:
            if isinstance(result[0], dict):
                # List of dictionaries
                headers = list(result[0].keys())
                csv_lines = [",".join(headers)]
                for row in result:
                    csv_lines.append(",".join(str(row.get(h, "")) for h in headers))
                return "\n".join(csv_lines)
            elif isinstance(result[0], (list, tuple)):
                # List of tuples/lists
                csv_lines = [",".join(f"Col{i}" for i in range(len(result[0])))]
                for row in result:
                    csv_lines.append(",".join(str(cell) for cell in row))
                return "\n".join(csv_lines)
        return str(result)
    
    elif format_type.lower() == "markdown":
        if isinstance(result, list) and result:
            if isinstance(result[0], dict):
                # List of dictionaries
                headers = list(result[0].keys())
                md_lines = ["| " + " | ".join(headers) + " |"]
                md_lines.append("|" + "---|" * len(headers))
                for row in result:
                    md_lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
                return "\n".join(md_lines)
        return f"```\n{str(result)}\n```"
    
    else:  # Default table format
        if isinstance(result, list) and result:
            if isinstance(result[0], dict):
                # Calculate column widths
                headers = list(result[0].keys())
                col_widths = {h: len(h) for h in headers}
                for row in result:
                    for h in headers:
                        col_widths[h] = max(col_widths[h], len(str(row.get(h, ""))))
                
                # Build table
                lines = []
                # Header
                header_line = " | ".join(h.ljust(col_widths[h]) for h in headers)
                lines.append(header_line)
                lines.append("-" * len(header_line))
                # Data rows
                for row in result:
                    data_line = " | ".join(str(row.get(h, "")).ljust(col_widths[h]) for h in headers)
                    lines.append(data_line)
                return "\n".join(lines)
        
        return str(result)


def validate_query_input(query: str) -> bool:
    """
    Validate SQL query input for safety and basic syntax.
    
    Args:
        query: SQL query to validate
        
    Returns:
        True if query appears safe, False otherwise
    """
    if not query or not isinstance(query, str):
        return False
    
    query = query.strip()
    if not query:
        return False
    
    # Check for dangerous keywords
    dangerous_patterns = [
        r'\bDROP\s+(DATABASE|TABLE|INDEX|TRIGGER|VIEW|PROCEDURE|FUNCTION)\b',
        r'\bDELETE\s+FROM\b',
        r'\bTRUNCATE\b',
        r'\bALTER\s+(DATABASE|TABLE|INDEX|TRIGGER|VIEW|PROCEDURE|FUNCTION)\b',
        r'\bCREATE\s+(DATABASE|TABLE|INDEX|TRIGGER|VIEW|PROCEDURE|FUNCTION)\b',
        r'\bINSERT\s+INTO\b',
        r'\bUPDATE\s+.+\s+SET\b',
        r'\bGRANT\s+',
        r'\bREVOKE\s+',
        r'\bEXEC\s*\(',
        r'\bEXECUTE\s+',
        r'\bUNION\s+(ALL\s+)?SELECT\b',
        r'\bLOAD\s+DATA\b',
        r'\bOUTFILE\b',
        r'\bDUMPFILE\b',
        r'\bINTO\s+OUTFILE\b',
        r'\bINTO\s+DUMPFILE\b'
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"Dangerous SQL pattern detected: {pattern}")
            return False
    
    # Check for multiple statements
    if ';' in query[:-1]:  # Allow semicolon at the end
        logger.warning("Multiple SQL statements detected")
        return False
    
    # Check for comment injection
    if '--' in query or '/*' in query or '*/' in query:
        logger.warning("SQL comment injection detected")
        return False
    
    # Basic SQL syntax check - should start with SELECT
    if not re.match(r'^\s*SELECT\b', query, re.IGNORECASE):
        logger.warning("Query does not start with SELECT")
        return False
    
    return True


def sanitize_sql_query(query: str) -> str:
    """
    Clean and sanitize SQL query to prevent injection.
    
    Args:
        query: SQL query to sanitize
        
    Returns:
        Sanitized SQL query
    """
    if not query:
        return ""
    
    # Remove comments
    query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    
    # Remove multiple semicolons
    query = re.sub(r';+', ';', query)
    
    # Remove trailing semicolon
    query = query.rstrip(';')
    
    # Normalize whitespace
    query = re.sub(r'\s+', ' ', query)
    query = query.strip()
    
    return query


def extract_sql_from_text(text: str) -> List[str]:
    """
    Extract SQL statements from text.
    
    Args:
        text: Text containing SQL statements
        
    Returns:
        List of extracted SQL statements
    """
    if not text:
        return []
    
    # Pattern to match SQL statements
    sql_patterns = [
        r'```sql\s*(.*?)\s*```',
        r'```(.*?)```',
        r'\'([^\']*SELECT[^\'\"]*)\'',
        r'"([^"]*SELECT[^\'\"]*)"',
        r'(SELECT\s+.*?)(?:\s*$|;|\n\n)'
    ]
    
    sql_statements = []
    
    for pattern in sql_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            sql = match.strip()
            if sql and sql.upper().startswith('SELECT'):
                sql_statements.append(sanitize_sql_query(sql))
    
    return list(set(sql_statements))  # Remove duplicates


def format_error_message(error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Format error messages consistently.
    
    Args:
        error: Exception to format
        context: Additional context information
        
    Returns:
        Formatted error message
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    formatted = f"[{error_type}] {error_msg}"
    
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        formatted += f" (Context: {context_str})"
    
    return formatted


def calculate_query_complexity(query: str) -> int:
    """
    Analyze query complexity and return a score.
    
    Args:
        query: SQL query to analyze
        
    Returns:
        Complexity score (higher = more complex)
    """
    if not query:
        return 0
    
    complexity = 0
    query_upper = query.upper()
    
    # Base complexity for SELECT
    complexity += 1
    
    # Joins increase complexity
    join_count = len(re.findall(r'\b(INNER|LEFT|RIGHT|FULL|CROSS)\s+JOIN\b', query_upper))
    complexity += join_count * 3
    
    # Subqueries increase complexity
    subquery_count = len(re.findall(r'\bSELECT\b.*?\bFROM\b.*?\(', query_upper))
    complexity += subquery_count * 5
    
    # Aggregates increase complexity
    aggregate_count = len(re.findall(r'\b(COUNT|SUM|AVG|MIN|MAX|GROUP_CONCAT)\s*\(', query_upper))
    complexity += aggregate_count * 2
    
    # GROUP BY increases complexity
    if re.search(r'\bGROUP\s+BY\b', query_upper):
        complexity += 3
    
    # HAVING increases complexity
    if re.search(r'\bHAVING\b', query_upper):
        complexity += 2
    
    # Window functions increase complexity
    if re.search(r'\bOVER\s*\(', query_upper):
        complexity += 5
    
    # CTEs increase complexity
    cte_count = len(re.findall(r'\bWITH\s+\w+\s+AS\s*\(', query_upper))
    complexity += cte_count * 3
    
    # Complex WHERE conditions
    where_conditions = len(re.findall(r'\b(AND|OR)\b', query_upper))
    complexity += min(where_conditions, 5)  # Cap at 5
    
    return complexity


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to specified length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string with error handling.
    
    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"JSON parsing failed: {e}")
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Safely serialize object to JSON with error handling.
    
    Args:
        obj: Object to serialize
        default: Default value if serialization fails
        
    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(obj, default=str, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.warning(f"JSON serialization failed: {e}")
        return default


def generate_unique_id(prefix: str = "") -> str:
    """
    Generate unique identifier.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Unique identifier string
    """
    unique_id = str(uuid.uuid4())
    return f"{prefix}{unique_id}" if prefix else unique_id


def parse_time_duration(duration: str) -> int:
    """
    Parse time duration string to seconds.
    
    Args:
        duration: Duration string (e.g., "1h", "30m", "60s")
        
    Returns:
        Duration in seconds
    """
    if not duration:
        return 0
    
    duration = duration.lower().strip()
    
    # Pattern to match number and unit
    match = re.match(r'^(\d+)([smhd])$', duration)
    if not match:
        return 0
    
    number, unit = match.groups()
    number = int(number)
    
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }
    
    return number * multipliers.get(unit, 1)


def format_bytes(bytes_count: int) -> str:
    """
    Format bytes in human-readable format.
    
    Args:
        bytes_count: Number of bytes
        
    Returns:
        Formatted string
    """
    if bytes_count == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    
    while bytes_count >= 1024 and unit_index < len(units) - 1:
        bytes_count /= 1024
        unit_index += 1
    
    return f"{bytes_count:.1f} {units[unit_index]}"


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False
    
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def clean_text(text: str) -> str:
    """
    Clean and normalize text.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    
    # Remove control characters
    text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C')
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """
    Extract important keywords from text.
    
    Args:
        text: Text to extract keywords from
        min_length: Minimum keyword length
        
    Returns:
        List of keywords
    """
    if not text:
        return []
    
    # Simple keyword extraction - remove common words and extract remaining words
    common_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
    }
    
    # Extract words
    words = re.findall(r'\b[a-zA-Z]{' + str(min_length) + ',}\b', text.lower())
    
    # Filter common words
    keywords = [word for word in words if word not in common_words]
    
    # Remove duplicates and return
    return list(set(keywords))


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate text similarity using sequence matcher.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score between 0 and 1
    """
    if not text1 or not text2:
        return 0.0
    
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple = (Exception,)
) -> Any:
    """
    Retry function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        base_delay: Base delay between retries
        max_delay: Maximum delay
        exceptions: Exception types to catch
        
    Returns:
        Function result
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt == max_retries:
                break
            
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
            time.sleep(delay)
    
    raise last_exception


def timeout_handler(func: Callable, timeout: float) -> Any:
    """
    Handle function execution timeout.
    
    Args:
        func: Function to execute
        timeout: Timeout in seconds
        
    Returns:
        Function result
        
    Raises:
        TimeoutError if function exceeds timeout
    """
    if asyncio.iscoroutinefunction(func):
        async def async_wrapper():
            try:
                return await asyncio.wait_for(func(), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Function timed out after {timeout} seconds")
        return asyncio.run(async_wrapper())
    else:
        # For synchronous functions, we can't easily implement timeout without threading
        # This is a simplified version
        start_time = time.time()
        result = func()
        execution_time = time.time() - start_time
        if execution_time > timeout:
            logger.warning(f"Function exceeded timeout: {execution_time}s > {timeout}s")
        return result


def rate_limiter(func: Callable, rate_limit: float) -> Callable:
    """
    Apply rate limiting to function.
    
    Args:
        func: Function to rate limit
        rate_limit: Minimum time between calls in seconds
        
    Returns:
        Rate-limited function
    """
    last_call_time = [0]  # Use list to allow modification in closure
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        current_time = time.time()
        time_since_last = current_time - last_call_time[0]
        
        if time_since_last < rate_limit:
            sleep_time = rate_limit - time_since_last
            time.sleep(sleep_time)
        
        last_call_time[0] = time.time()
        return func(*args, **kwargs)
    
    return wrapper


def cache_result(func: Callable, cache_duration: float = 300.0) -> Callable:
    """
    Cache function results for specified duration.
    
    Args:
        func: Function to cache
        cache_duration: Cache duration in seconds
        
    Returns:
        Cached function
    """
    cache = {}
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create cache key
        key = str(args) + str(sorted(kwargs.items()))
        current_time = time.time()
        
        # Check cache
        if key in cache:
            result, timestamp = cache[key]
            if current_time - timestamp < cache_duration:
                return result
        
        # Execute and cache
        result = func(*args, **kwargs)
        cache[key] = (result, current_time)
        
        return result
    
    return wrapper


def measure_time(func: Callable) -> Callable:
    """
    Measure function execution time.
    
    Args:
        func: Function to measure
        
    Returns:
        Function that returns (result, execution_time)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        return result, execution_time
    
    return wrapper


def async_measure_time(func: Callable) -> Callable:
    """
    Measure async function execution time.
    
    Args:
        func: Async function to measure
        
    Returns:
        Async function that returns (result, execution_time)
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        execution_time = time.time() - start_time
        return result, execution_time
    
    return wrapper


def hash_string(text: str, algorithm: str = "sha256") -> str:
    """
    Hash string using specified algorithm.
    
    Args:
        text: Text to hash
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)
        
    Returns:
        Hashed string
    """
    if not text:
        return ""
    
    try:
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(text.encode('utf-8'))
        return hash_obj.hexdigest()
    except ValueError:
        logger.warning(f"Unknown hash algorithm: {algorithm}")
        return ""


def format_timestamp(timestamp: Optional[float] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format timestamp to readable string.
    
    Args:
        timestamp: Unix timestamp (None for current time)
        format_str: Format string
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = time.time()
    
    return datetime.fromtimestamp(timestamp).strftime(format_str)


def parse_timestamp(timestamp_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[float]:
    """
    Parse timestamp string to Unix timestamp.
    
    Args:
        timestamp_str: Timestamp string
        format_str: Format string
        
    Returns:
        Unix timestamp or None if parsing fails
    """
    try:
        dt = datetime.strptime(timestamp_str, format_str)
        return dt.timestamp()
    except ValueError:
        return None


def is_valid_identifier(name: str) -> bool:
    """
    Check if string is a valid identifier.
    
    Args:
        name: String to check
        
    Returns:
        True if valid identifier
    """
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))


def escape_sql_string(value: str) -> str:
    """
    Escape string for SQL to prevent injection.
    
    Args:
        value: String to escape
        
    Returns:
        Escaped string
    """
    if not value:
        return ""
    
    # Basic SQL escaping
    value = value.replace("'", "''")
    value = value.replace("\\", "\\\\")
    value = value.replace("\n", "\\n")
    value = value.replace("\r", "\\r")
    value = value.replace("\t", "\\t")
    
    return value


def compress_whitespace(text: str) -> str:
    """
    Compress multiple whitespace characters to single space.
    
    Args:
        text: Text to compress
        
    Returns:
        Compressed text
    """
    return re.sub(r'\s+', ' ', text).strip()


def count_tokens(text: str) -> int:
    """
    Estimate token count for text (rough approximation).
    
    Args:
        text: Text to count tokens for
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    # Simple approximation: split on whitespace and punctuation
    tokens = re.findall(r'\b\w+\b', text)
    return len(tokens)


def format_list(items: List[Any], separator: str = ", ", max_items: int = 10) -> str:
    """
    Format list of items as string.
    
    Args:
        items: List of items
        separator: Separator between items
        max_items: Maximum items to show
        
    Returns:
        Formatted string
    """
    if not items:
        return ""
    
    items_str = [str(item) for item in items[:max_items]]
    
    if len(items) > max_items:
        items_str.append(f"... and {len(items) - max_items} more")
    
    return separator.join(items_str)


def deep_merge_dict(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """
    Flatten nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator between keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    
    for key, value in d.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, sep).items())
        else:
            items.append((new_key, value))
    
    return dict(items)


def get_nested_value(d: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get value from nested dictionary using dot notation.
    
    Args:
        d: Dictionary
        key_path: Dot-separated key path
        default: Default value if key not found
        
    Returns:
        Value or default
    """
    keys = key_path.split('.')
    current = d
    
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default


def set_nested_value(d: Dict[str, Any], key_path: str, value: Any) -> None:
    """
    Set value in nested dictionary using dot notation.
    
    Args:
        d: Dictionary
        key_path: Dot-separated key path
        value: Value to set
    """
    keys = key_path.split('.')
    current = d
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.duration = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        logger.debug(f"{self.name} completed in {self.duration:.3f}s")
    
    def get_duration(self) -> Optional[float]:
        """Get the duration of the timed operation."""
        return self.duration


class ProgressTracker:
    """Simple progress tracker for long-running operations."""
    
    def __init__(self, total: int, description: str = "Progress"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
    
    def update(self, increment: int = 1) -> None:
        """Update progress."""
        self.current += increment
        self._log_progress()
    
    def set_current(self, current: int) -> None:
        """Set current progress."""
        self.current = current
        self._log_progress()
    
    def _log_progress(self) -> None:
        """Log current progress."""
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        elapsed = time.time() - self.start_time
        
        if self.current > 0:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f", ETA: {eta:.1f}s"
        else:
            eta_str = ""
        
        logger.info(f"{self.description}: {self.current}/{self.total} ({percentage:.1f}%, {elapsed:.1f}s{eta_str})")
    
    def finish(self) -> None:
        """Mark as finished."""
        self.current = self.total
        elapsed = time.time() - self.start_time
        logger.info(f"{self.description} completed in {elapsed:.1f}s")