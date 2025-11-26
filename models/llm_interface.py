"""
LLM Interface Module

Provides abstraction layer for different LLM providers including
Gemini, OpenAI, and future provider implementations.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from dataclasses import dataclass, field
import asyncio

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import openai
    from openai import AsyncOpenAI, OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from config import get_settings


class LLMProvider(Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


@dataclass
class LLMConfig:
    """Configuration for LLM instances."""
    provider: LLMProvider
    model_name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 0.9
    top_k: Optional[int] = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    safety_settings: Optional[Dict[str, Any]] = None
    generation_config: Optional[Dict[str, Any]] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.provider == LLMProvider.GEMINI and not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package is required for Gemini provider")
        if self.provider == LLMProvider.OPENAI and not OPENAI_AVAILABLE:
            raise ImportError("openai package is required for OpenAI provider")


@dataclass
class LLMResponse:
    """Response structure for LLM outputs."""
    content: str
    model: str
    provider: LLMProvider
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    response_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider.value,
            "tokens_used": self.tokens_used,
            "finish_reason": self.finish_reason,
            "response_time": self.response_time,
            "metadata": self.metadata
        }


class LLMInterface(ABC):
    """Abstract base class for LLM interfaces."""
    
    def __init__(self, config: LLMConfig):
        """Initialize LLM interface with configuration."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._client = None
        self._model = None
        
    @abstractmethod
    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response asynchronously."""
        pass
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response synchronously."""
        pass
    
    @abstractmethod
    async def generate_stream_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response asynchronously."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate the configuration."""
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "provider": self.config.provider.value,
            "model_name": self.config.model_name,
            "configured": self._client is not None
        }


class GeminiInterface(LLMInterface):
    """Gemini LLM implementation."""
    
    def __init__(self, config: LLMConfig):
        """Initialize Gemini interface."""
        super().__init__(config)
        self._setup_client()
    
    def _setup_client(self):
        """Setup Gemini client."""
        try:
            if not GEMINI_AVAILABLE:
                raise ImportError("google-generativeai package is not installed")
            
            genai.configure(api_key=self.config.api_key)
            
            # Configure safety settings
            safety_settings = self.config.safety_settings or {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # Configure generation settings
            generation_config = {
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "top_k": self.config.top_k,
                "max_output_tokens": self.config.max_tokens,
                "stop_sequences": self.config.stop_sequences,
            }
            
            # Update with any extra generation config
            if self.config.generation_config:
                generation_config.update(self.config.generation_config)
            
            self._model = genai.GenerativeModel(
                model_name=self.config.model_name,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            self._client = genai
            self.logger.info(f"Initialized Gemini model: {self.config.model_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    def validate_config(self) -> bool:
        """Validate Gemini configuration."""
        if not self.config.api_key:
            self.logger.error("API key is required for Gemini")
            return False
        return True
    
    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response asynchronously using Gemini."""
        start_time = time.time()
        
        try:
            # Build conversation
            contents = []
            
            # Add system prompt if provided
            if system_prompt:
                contents.append({"role": "user", "parts": [system_prompt]})
                contents.append({"role": "model", "parts": ["Understood. I'll follow these instructions."]})
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append({"role": role, "parts": [msg["content"]]})
            
            # Add current prompt
            contents.append({"role": "user", "parts": [prompt]})
            
            # Generate response
            response = await self._model.generate_content_async(contents)
            
            response_time = time.time() - start_time
            
            # Extract metadata
            metadata = {
                "candidates": len(response.candidates) if hasattr(response, 'candidates') else 1,
                "prompt_feedback": getattr(response, 'prompt_feedback', None),
            }
            
            if hasattr(response, 'candidates') and response.candidates:
                finish_reason = response.candidates[0].finish_reason.name if hasattr(response.candidates[0], 'finish_reason') else None
                tokens_used = getattr(response.candidates[0], 'token_count', None)
            else:
                finish_reason = None
                tokens_used = None
            
            return LLMResponse(
                content=response.text,
                model=self.config.model_name,
                provider=self.config.provider,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                response_time=response_time,
                metadata=metadata,
                raw_response=response
            )
            
        except Exception as e:
            self.logger.error(f"Error generating response with Gemini: {e}")
            response_time = time.time() - start_time
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.config.model_name,
                provider=self.config.provider,
                response_time=response_time,
                metadata={"error": str(e)}
            )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response synchronously using Gemini."""
        return asyncio.run(self.generate_async(prompt, system_prompt, conversation_history, **kwargs))
    
    async def generate_stream_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response asynchronously using Gemini."""
        try:
            # Build conversation
            contents = []
            
            if system_prompt:
                contents.append({"role": "user", "parts": [system_prompt]})
                contents.append({"role": "model", "parts": ["Understood. I'll follow these instructions."]})
            
            if conversation_history:
                for msg in conversation_history:
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append({"role": role, "parts": [msg["content"]]})
            
            contents.append({"role": "user", "parts": [prompt]})
            
            # Generate streaming response
            response = await self._model.generate_content_async(contents, stream=True)
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            self.logger.error(f"Error in streaming generation with Gemini: {e}")
            yield f"Error: {str(e)}"


class OpenAIInterface(LLMInterface):
    """OpenAI LLM implementation."""
    
    def __init__(self, config: LLMConfig):
        """Initialize OpenAI interface."""
        super().__init__(config)
        self._setup_client()
    
    def _setup_client(self):
        """Setup OpenAI client."""
        try:
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package is not installed")
            
            client_kwargs = {
                "api_key": self.config.api_key,
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries
            }
            
            if self.config.api_base:
                client_kwargs["base_url"] = self.config.api_base
            
            self._client = AsyncOpenAI(**client_kwargs)
            self._sync_client = OpenAI(**client_kwargs)
            
            self.logger.info(f"Initialized OpenAI client for model: {self.config.model_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    def validate_config(self) -> bool:
        """Validate OpenAI configuration."""
        if not self.config.api_key:
            self.logger.error("API key is required for OpenAI")
            return False
        return True
    
    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response asynchronously using OpenAI."""
        start_time = time.time()
        
        try:
            # Build messages
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current prompt
            messages.append({"role": "user", "content": prompt})
            
            # Prepare generation parameters
            generation_params = {
                "model": self.config.model_name,
                "messages": messages,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty,
            }
            
            if self.config.max_tokens:
                generation_params["max_tokens"] = self.config.max_tokens
            
            if self.config.stop_sequences:
                generation_params["stop"] = self.config.stop_sequences
            
            # Add extra parameters
            generation_params.update(self.config.extra_params)
            
            # Generate response
            response = await self._client.chat.completions.create(**generation_params)
            
            response_time = time.time() - start_time
            
            # Extract response data
            choice = response.choices[0]
            content = choice.message.content or ""
            finish_reason = choice.finish_reason
            tokens_used = response.usage.total_tokens if response.usage else None
            
            metadata = {
                "choices": len(response.choices),
                "usage": response.usage.model_dump() if response.usage else None,
                "system_fingerprint": getattr(response, 'system_fingerprint', None),
            }
            
            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider=self.config.provider,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                response_time=response_time,
                metadata=metadata,
                raw_response=response
            )
            
        except Exception as e:
            self.logger.error(f"Error generating response with OpenAI: {e}")
            response_time = time.time() - start_time
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.config.model_name,
                provider=self.config.provider,
                response_time=response_time,
                metadata={"error": str(e)}
            )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response synchronously using OpenAI."""
        start_time = time.time()
        
        try:
            # Build messages
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            if conversation_history:
                messages.extend(conversation_history)
            
            messages.append({"role": "user", "content": prompt})
            
            # Prepare generation parameters
            generation_params = {
                "model": self.config.model_name,
                "messages": messages,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty,
            }
            
            if self.config.max_tokens:
                generation_params["max_tokens"] = self.config.max_tokens
            
            if self.config.stop_sequences:
                generation_params["stop"] = self.config.stop_sequences
            
            generation_params.update(self.config.extra_params)
            
            # Generate response
            response = self._sync_client.chat.completions.create(**generation_params)
            
            response_time = time.time() - start_time
            
            # Extract response data
            choice = response.choices[0]
            content = choice.message.content or ""
            finish_reason = choice.finish_reason
            tokens_used = response.usage.total_tokens if response.usage else None
            
            metadata = {
                "choices": len(response.choices),
                "usage": response.usage.model_dump() if response.usage else None,
                "system_fingerprint": getattr(response, 'system_fingerprint', None),
            }
            
            return LLMResponse(
                content=content,
                model=self.config.model_name,
                provider=self.config.provider,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                response_time=response_time,
                metadata=metadata,
                raw_response=response
            )
            
        except Exception as e:
            self.logger.error(f"Error generating response with OpenAI: {e}")
            response_time = time.time() - start_time
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.config.model_name,
                provider=self.config.provider,
                response_time=response_time,
                metadata={"error": str(e)}
            )
    
    async def generate_stream_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response asynchronously using OpenAI."""
        try:
            # Build messages
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            if conversation_history:
                messages.extend(conversation_history)
            
            messages.append({"role": "user", "content": prompt})
            
            # Prepare generation parameters
            generation_params = {
                "model": self.config.model_name,
                "messages": messages,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty,
                "stream": True,
            }
            
            if self.config.max_tokens:
                generation_params["max_tokens"] = self.config.max_tokens
            
            if self.config.stop_sequences:
                generation_params["stop"] = self.config.stop_sequences
            
            generation_params.update(self.config.extra_params)
            
            # Generate streaming response
            stream = await self._client.chat.completions.create(**generation_params)
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            self.logger.error(f"Error in streaming generation with OpenAI: {e}")
            yield f"Error: {str(e)}"


# Global LLM interface registry
_llm_interfaces: Dict[str, LLMInterface] = {}


def create_llm_interface(config: LLMConfig, name: str = "default") -> LLMInterface:
    """Create a new LLM interface instance."""
    if config.provider == LLMProvider.GEMINI:
        interface = GeminiInterface(config)
    elif config.provider == LLMProvider.OPENAI:
        interface = OpenAIInterface(config)
    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")
    
    # Validate configuration
    if not interface.validate_config():
        raise ValueError(f"Invalid configuration for {config.provider.value}")
    
    _llm_interfaces[name] = interface
    return interface


def get_llm_interface(name: str = "default") -> Optional[LLMInterface]:
    """Get an existing LLM interface instance."""
    return _llm_interfaces.get(name)


def create_llm_interface_from_settings(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    name: str = "default"
) -> LLMInterface:
    """Create LLM interface from application settings."""
    settings = get_settings()
    
    # Use provided values or fall back to settings
    provider_name = provider or settings.llm_provider
    
    try:
        provider_enum = LLMProvider(provider_name.lower())
    except ValueError:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")
    
    # Get provider-specific configuration
    if provider_enum == LLMProvider.GEMINI:
        api_key = settings.gemini_api_key
        model = model_name or settings.gemini_model
        api_base = None
    elif provider_enum == LLMProvider.OPENAI:
        api_key = settings.openai_api_key
        model = model_name or settings.openai_model
        api_base = getattr(settings, 'openai_api_base', None)
    else:
        raise ValueError(f"Provider {provider_name} not configured in settings")
    
    if not api_key:
        raise ValueError(f"API key not configured for provider {provider_name}")
    
    config = LLMConfig(
        provider=provider_enum,
        model_name=model,
        api_key=api_key,
        api_base=api_base,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        top_p=getattr(settings, 'top_p', 0.9),
        timeout=getattr(settings, 'llm_timeout', 30),
        max_retries=getattr(settings, 'llm_max_retries', 3),
        safety_settings=getattr(settings, 'llm_safety_settings', None),
        generation_config=getattr(settings, 'llm_generation_config', None)
    )
    
    return create_llm_interface(config, name)


def list_llm_interfaces() -> Dict[str, Dict[str, Any]]:
    """List all registered LLM interfaces."""
    return {
        name: interface.get_model_info() 
        for name, interface in _llm_interfaces.items()
    }


def remove_llm_interface(name: str) -> bool:
    """Remove an LLM interface instance."""
    if name in _llm_interfaces:
        del _llm_interfaces[name]
        return True
    return False


def clear_llm_interfaces():
    """Clear all LLM interface instances."""
    _llm_interfaces.clear()