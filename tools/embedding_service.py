#!/usr/bin/env python3
"""
Embedding Service - 统一的 embedding 服务抽象层
支持本地模型和 OpenAI 格式的远程 API
"""

import os
import logging
from typing import List, Optional, Union
from abc import ABC, abstractmethod
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService(ABC):
    """Embedding 服务抽象基类"""
    
    @abstractmethod
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        将文本编码为向量
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            numpy 数组，形状为 (n_texts, embedding_dim)
        """
        pass
    
    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """返回 embedding 维度"""
        pass


class OpenAIEmbeddingService(EmbeddingService):
    """OpenAI 格式的 embedding 服务（支持 OpenAI 及兼容 API）"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "text-embedding-3-small",
        embedding_dim: int = 1536
    ):
        """
        初始化 OpenAI embedding 服务
        
        Args:
            api_key: API 密钥，默认从环境变量 EMBEDDING_API_KEY 或 OPENAI_API_KEY 获取
            base_url: API 基础 URL，默认从环境变量 EMBEDDING_BASE_URL 或 OPENAI_BASE_URL 获取
            model: 模型名称，默认从环境变量 EMBEDDING_MODEL 获取
            embedding_dim: embedding 维度
        """
        from openai import OpenAI
        
        self.api_key = api_key or os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("EMBEDDING_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        self.model = os.getenv("EMBEDDING_MODEL") or model
        self._embedding_dim = int(os.getenv("EMBEDDING_DIM", str(embedding_dim)))
        
        if not self.api_key:
            raise ValueError("Embedding API key not found. Set EMBEDDING_API_KEY or OPENAI_API_KEY")
        
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
            
        self.client = OpenAI(**client_kwargs)
        logger.info(f"✅ OpenAI Embedding Service initialized (model: {self.model}, dim: {self._embedding_dim})")
    
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        使用 OpenAI API 编码文本
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            numpy 数组
        """
        if isinstance(texts, str):
            texts = [texts]
        
        # OpenAI API 有批次大小限制，分批处理
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Embedding API error: {e}")
                raise
        
        return np.array(all_embeddings)
    
    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim


class LocalEmbeddingService(EmbeddingService):
    """本地 sentence-transformers 模型服务"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化本地 embedding 服务
        
        Args:
            model_name: sentence-transformers 模型名称
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install it with: uv sync --extra local-embedding"
            )
        
        self.model_name = model_name
        logger.info(f"Loading local embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self._embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"✅ Local Embedding Service initialized (model: {model_name}, dim: {self._embedding_dim})")
    
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        使用本地模型编码文本
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            numpy 数组
        """
        if isinstance(texts, str):
            texts = [texts]
        
        return self.model.encode(texts)
    
    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim


class EmbeddingServiceFactory:
    """Embedding 服务工厂"""
    
    _instance: Optional[EmbeddingService] = None
    
    @classmethod
    def get_service(cls, force_new: bool = False) -> EmbeddingService:
        """
        获取 embedding 服务实例（单例模式）
        
        根据环境变量 EMBEDDING_PROVIDER 选择服务类型：
        - "openai": 使用 OpenAI 格式 API
        - "local": 使用本地 sentence-transformers 模型
        
        Args:
            force_new: 是否强制创建新实例
            
        Returns:
            EmbeddingService 实例
        """
        if cls._instance is not None and not force_new:
            return cls._instance
        
        provider = os.getenv("EMBEDDING_PROVIDER", "local").lower()
        
        if provider == "openai":
            cls._instance = OpenAIEmbeddingService()
        elif provider == "local":
            model_name = os.getenv("LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            cls._instance = LocalEmbeddingService(model_name=model_name)
        else:
            raise ValueError(f"Unknown embedding provider: {provider}. Use 'openai' or 'local'")
        
        return cls._instance
    
    @classmethod
    def reset(cls):
        """重置服务实例"""
        cls._instance = None


def get_embedding_service() -> EmbeddingService:
    """获取 embedding 服务的便捷函数"""
    return EmbeddingServiceFactory.get_service()


# ChromaDB 自定义 embedding 函数
try:
    from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
    
    class ChromaEmbeddingFunction(EmbeddingFunction[Documents]):
        """ChromaDB 兼容的 embedding 函数包装器
        
        继承 ChromaDB 的 EmbeddingFunction 基类
        """
        
        def __init__(self, embedding_service: Optional[EmbeddingService] = None):
            """
            初始化 ChromaDB embedding 函数
            
            Args:
                embedding_service: embedding 服务实例，默认自动获取
            """
            self._service = embedding_service
        
        @property
        def service(self) -> EmbeddingService:
            """延迟加载 embedding 服务"""
            if self._service is None:
                self._service = get_embedding_service()
            return self._service
        
        def __call__(self, input: Documents) -> Embeddings:
            """
            ChromaDB 调用接口
            
            Args:
                input: 文本列表
                
            Returns:
                embedding 列表
            """
            embeddings = self.service.encode(list(input))
            return embeddings.tolist()

except ImportError:
    # 如果 chromadb 未安装，提供一个占位类
    class ChromaEmbeddingFunction:
        """ChromaDB 未安装时的占位类"""
        def __init__(self, *args, **kwargs):
            raise ImportError("chromadb is not installed")
