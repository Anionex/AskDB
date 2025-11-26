"""
AskDB Application Settings Configuration

This module defines the core application settings using Pydantic for type safety,
environment variable loading, and validation. It provides centralized configuration
management for the entire AskDB system.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Main application settings class using Pydantic BaseSettings for
    automatic environment variable loading and validation.
    """
    
    # Application Core Settings
    app_name: str = Field(default="AskDB", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # LLM Configuration
    llm_provider: str = Field(default="gemini", description="Primary LLM provider")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Gemini model name")
    openai_model: str = Field(default="gpt-4", description="OpenAI model name")
    max_tokens: int = Field(default=4096, description="Maximum tokens for LLM responses")
    temperature: float = Field(default=0.1, description="LLM temperature parameter")
    
    # Database Settings
    default_database_url: Optional[str] = Field(
        default=None, 
        description="Default database connection URL"
    )
    database_timeout: int = Field(default=30, description="Database connection timeout")
    max_query_results: int = Field(default=1000, description="Maximum query results to return")
    
    # Vector and Embedding Settings
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence transformer model for embeddings"
    )
    vector_dimension: int = Field(default=384, description="Vector embedding dimension")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold for matching")
    use_faiss: bool = Field(default=True, description="Use FAISS for vector search")
    
    # Safety and Security Settings
    enable_safety_checks: bool = Field(default=True, description="Enable safety protocols")
    pii_detection_enabled: bool = Field(default=True, description="Enable PII detection")
    risk_classification_enabled: bool = Field(default=True, description="Enable risk classification")
    max_query_complexity: int = Field(default=10, description="Maximum query complexity score")
    allowed_operations: List[str] = Field(
        default=["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"],
        description="Allowed SQL operations"
    )
    
    # Web Search Settings
    enable_web_search: bool = Field(default=False, description="Enable web search capability")
    web_search_provider: str = Field(default="duckduckgo", description="Web search provider")
    web_search_timeout: int = Field(default=10, description="Web search timeout")
    max_web_results: int = Field(default=5, description="Maximum web search results")
    google_search_api_key: Optional[str] = Field(default=None, description="Google Search API key")
    google_search_engine_id: Optional[str] = Field(default=None, description="Google Search Engine ID")
    
    # Conversation and Context Settings
    max_conversation_length: int = Field(default=20, description="Maximum conversation turns")
    context_window_size: int = Field(default=10, description="Context window size")
    enable_conversation_memory: bool = Field(default=True, description="Enable conversation memory")
    
    # Performance Settings
    max_parallel_queries: int = Field(default=3, description="Maximum parallel queries")
    query_cache_size: int = Field(default=100, description="Query cache size")
    enable_query_cache: bool = Field(default=True, description="Enable query caching")
    
    # File and Path Settings
    data_dir: Path = Field(default=Path("./data"), description="Data directory path")
    cache_dir: Path = Field(default=Path("./cache"), description="Cache directory path")
    log_dir: Path = Field(default=Path("./logs"), description="Log directory path")
    
    # Spider Benchmark Settings
    spider_data_path: Optional[Path] = Field(
        default=None, 
        description="Path to Spider benchmark data"
    )
    enable_spider_evaluation: bool = Field(default=False, description="Enable Spider evaluation")
    
    @field_validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level is one of the standard logging levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("temperature")
    def validate_temperature(cls, v):
        """Validate temperature is within valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v
    
    @field_validator("similarity_threshold")
    def validate_similarity_threshold(cls, v):
        """Validate similarity threshold is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        return v
    
    @field_validator("llm_provider")
    def validate_llm_provider(cls, v):
        """Validate LLM provider is supported."""
        valid_providers = ["gemini", "openai"]
        if v.lower() not in valid_providers:
            raise ValueError(f"llm_provider must be one of {valid_providers}")
        return v.lower()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra='ignore',  # Ignore extra fields from .env
    )
        
    def __init__(self, **data):
        """Initialize settings and create necessary directories."""
        super().__init__(**data)
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [self.data_dir, self.cache_dir, self.log_dir]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration as dictionary."""
        if self.llm_provider == "gemini":
            return {
                "provider": "gemini",
                "api_key": self.gemini_api_key,
                "model": self.gemini_model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
        elif self.llm_provider == "openai":
            return {
                "provider": "openai",
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """Get embedding configuration as dictionary."""
        return {
            "model_name": self.embedding_model,
            "dimension": self.vector_dimension,
            "use_faiss": self.use_faiss
        }
    
    def get_safety_config(self) -> Dict[str, Any]:
        """Get safety configuration as dictionary."""
        return {
            "enabled": self.enable_safety_checks,
            "pii_detection": self.pii_detection_enabled,
            "risk_classification": self.risk_classification_enabled,
            "max_complexity": self.max_query_complexity,
            "allowed_operations": self.allowed_operations
        }
    
    def get_web_search_config(self) -> Dict[str, Any]:
        """Get web search configuration as dictionary."""
        return {
            "provider": self.web_search_provider,
            "enabled": self.enable_web_search,
            "timeout": self.web_search_timeout,
            "max_results": self.max_web_results,
            "google_api_key": self.google_search_api_key,
            "google_search_engine_id": self.google_search_engine_id
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance (singleton pattern).
    
    Returns:
        Settings: The global settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment variables.
    
    Returns:
        Settings: The new settings instance
    """
    global _settings
    _settings = Settings()
    return _settings


def update_settings(**kwargs) -> Settings:
    """
    Update specific settings values.
    
    Args:
        **kwargs: Settings to update
        
    Returns:
        Settings: The updated settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    
    # Create new settings with updated values
    current_dict = _settings.model_dump()
    current_dict.update(kwargs)
    _settings = Settings(**current_dict)
    return _settings