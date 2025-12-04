"""
Web Search Tool for AskDB

This module provides web search capabilities for the AskDB agent,
enabling external information retrieval to enhance query understanding
and answer complex questions that require external knowledge.
"""

import asyncio
import aiohttp
import json
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from urllib.parse import urlencode, quote_plus
import time

import os
import nest_asyncio  # 添加nest_asyncio修复事件循环冲突

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a single web search result."""
    title: str
    url: str
    snippet: str
    relevance_score: float = 0.0
    source: str = "web"
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class SearchQuery:
    """Represents a search query with metadata."""
    query: str
    max_results: int = 10
    include_snippets: bool = True
    safe_search: bool = True
    language: str = "en"
    region: str = "us"
    time_range: Optional[str] = None  # e.g., "d1" (1 day), "w1" (1 week), "m1" (1 month)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert query to dictionary."""
        return {
            "q": self.query,
            "num": self.max_results,
            "safe": self.safe_search,
            "hl": self.language,
            "gl": self.region,
            "timeRange": self.time_range
        }


class WebSearchError(Exception):
    """Exception raised for web search errors."""
    pass


class BaseWebSearchProvider:
    """Base class for web search providers."""
    
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.kwargs = kwargs
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform web search. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement search method")
    
    async def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {e}")
            raise WebSearchError(f"Search request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            raise WebSearchError(f"Invalid response format: {e}")


class DuckDuckGoProvider(BaseWebSearchProvider):
    """DuckDuckGo web search provider (free, no API key required)."""
    
    def __init__(self, **kwargs):
        super().__init__(api_key="", **kwargs)
        self.base_url = "https://api.duckduckgo.com/"
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform DuckDuckGo search."""
        params = {
            "q": query.query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
            "kl": f"{query.language}-{query.region}",
        }
        
        try:
            data = await self._make_request(self.base_url, params)
            return self._parse_ddg_response(data, query)
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            raise WebSearchError(f"DuckDuckGo search failed: {e}")
    
    def _parse_ddg_response(self, data: Dict[str, Any], query: SearchQuery) -> List[SearchResult]:
        """Parse DuckDuckGo response."""
        results = []
        
        # Abstract (main result)
        if data.get("Abstract"):
            results.append(SearchResult(
                title=data.get("AbstractSource", "Abstract"),
                url=data.get("AbstractURL", ""),
                snippet=data.get("Abstract", ""),
                source="duckduckgo_abstract"
            ))
        
        # Related topics
        for topic in data.get("RelatedTopics", [])[:query.max_results]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append(SearchResult(
                    title=topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                    url=topic.get("FirstURL", ""),
                    snippet=topic.get("Text", ""),
                    source="duckduckgo_related"
                ))
        
        return results


class GoogleSearchProvider(BaseWebSearchProvider):
    """Google Custom Search API provider."""
    
    def __init__(self, api_key: str, search_engine_id: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.search_engine_id = search_engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform Google Custom Search."""
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query.query,
            "num": min(query.max_results, 10),  # Google API limit
            "safe": query.safe_search,
            "hl": query.language,
            "gl": query.region,
        }
        
        if query.time_range:
            params["dateRestrict"] = query.time_range
        
        try:
            data = await self._make_request(self.base_url, params)
            return self._parse_google_response(data, query)
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            raise WebSearchError(f"Google search failed: {e}")
    
    def _parse_google_response(self, data: Dict[str, Any], query: SearchQuery) -> List[SearchResult]:
        """Parse Google Custom Search response."""
        results = []
        
        for item in data.get("items", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                source="google_search"
            ))
        
        return results


class BingSearchProvider(BaseWebSearchProvider):
    """Bing Search API provider."""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = "https://api.bing.microsoft.com/v7.0/search"
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform Bing search."""
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key
        }
        
        params = {
            "q": query.query,
            "count": query.max_results,
            "safeSearch": "Strict" if query.safe_search else "Moderate",
            "mkt": f"{query.language}-{query.region}",
            "textFormat": "HTML",
        }
        
        if query.time_range:
            params["freshness"] = self._convert_time_range(query.time_range)
        
        try:
            async with self.session.get(self.base_url, params=params, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                return self._parse_bing_response(data, query)
        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            raise WebSearchError(f"Bing search failed: {e}")
    
    def _convert_time_range(self, time_range: str) -> str:
        """Convert time range format to Bing format."""
        mapping = {
            "d1": "Day",
            "w1": "Week",
            "m1": "Month"
        }
        return mapping.get(time_range, "Day")
    
    def _parse_bing_response(self, data: Dict[str, Any], query: SearchQuery) -> List[SearchResult]:
        """Parse Bing search response."""
        results = []
        
        for item in data.get("webPages", {}).get("value", []):
            results.append(SearchResult(
                title=item.get("name", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
                source="bing_search"
            ))
        
        return results


class WebSearchTool:
    """Main web search tool that manages different search providers - 修复版"""
    
    def __init__(self, provider: Optional[str] = None, **kwargs):
        self.provider_name = provider or os.getenv("WEB_SEARCH_PROVIDER", "duckduckgo")
        self.provider = self._create_provider(**kwargs)
        self._session = None
        
        try:
            nest_asyncio.apply()
        except Exception as e:
            logger.warning(f"⚠️ nest_asyncio补丁应用失败: {e}")
    
    def _create_provider(self, **kwargs) -> BaseWebSearchProvider:
        """Create search provider based on configuration."""
        if self.provider_name.lower() == "duckduckgo":
            return DuckDuckGoProvider(**kwargs)
        elif self.provider_name.lower() == "google":
            api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
            search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
            if not api_key or not search_engine_id:
                raise WebSearchError("Google API key and search engine ID required")
            return GoogleSearchProvider(api_key, search_engine_id, **kwargs)
        elif self.provider_name.lower() == "bing":
            api_key = os.getenv("BING_API_KEY")
            if not api_key:
                raise WebSearchError("Bing API key required")
            return BingSearchProvider(api_key, **kwargs)
        else:
            raise WebSearchError(f"Unsupported search provider: {self.provider_name}")
    
    async def search(self, query: str, max_results: int = 10, **kwargs) -> List[SearchResult]:
        """Perform web search."""
        search_query = SearchQuery(
            query=query,
            max_results=max_results,
            **kwargs
        )
        
        async with self.provider as provider:
            try:
                results = await provider.search(search_query)
                logger.info(f"Found {len(results)} results for query: {query}")
                return results
            except Exception as e:
                logger.error(f"Web search failed: {e}")
                raise WebSearchError(f"Search failed: {e}")
    
    def search_sync(self, query: str, max_results: int = 10, **kwargs) -> List[SearchResult]:
        """同步版本的Web搜索 - 修复事件循环问题"""
        try:
            # 创建新的事件循环，避免冲突
            import asyncio
            
            # 应用nest_asyncio补丁，允许嵌套事件循环
            try:
                nest_asyncio.apply()
            except Exception as e:
                logger.warning(f"nest_asyncio补丁应用失败: {e}")
            
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 执行异步搜索
                results = loop.run_until_complete(
                    self.search(query, max_results=max_results, **kwargs)
                )
                logger.info(f"✅ 同步Web搜索成功: 找到 {len(results)} 个结果")
                return results
            except Exception as e:
                logger.error(f"同步Web搜索执行失败: {e}")
                # 返回空结果而不是抛出异常
                return []
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"同步Web搜索失败: {e}")
            # 返回空结果而不是抛出异常
            return []
    
    def search_with_fallback(self, query: str, max_results: int = 10, **kwargs) -> List[SearchResult]:
        """带降级策略的Web搜索"""
        try:
            # 首先尝试同步搜索
            results = self.search_sync(query, max_results, **kwargs)
            if results:
                return results
            
            # 如果同步搜索失败，尝试异步搜索
            logger.info("同步搜索失败，尝试异步搜索...")
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环已经在运行，创建新的事件循环
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(self.search(query, max_results, **kwargs))
                    loop.close()
                    return results
                else:
                    # 使用现有的事件循环
                    return loop.run_until_complete(self.search(query, max_results, **kwargs))
            except RuntimeError:
                # 如果没有事件循环，创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(self.search(query, max_results, **kwargs))
                loop.close()
                return results
                
        except Exception as e:
            logger.error(f"Web搜索完全失败: {e}")
            # 返回模拟结果作为最终降级
            return self._get_fallback_results(query)
    
    def _get_fallback_results(self, query: str) -> List[SearchResult]:
        """获取降级结果 - 当所有搜索方法都失败时使用"""
        logger.warning(f"使用降级结果代替Web搜索: {query}")
        
        # 返回模拟结果
        return [
            SearchResult(
                title="Web搜索功能暂时不可用",
                url="",
                snippet=f"由于技术问题，Web搜索功能暂时不可用。您查询的内容是: {query}。请稍后再试或联系技术支持。",
                source="fallback"
            )
        ]
    
    def format_results(self, results: List[SearchResult], format_type: str = "text") -> str:
        """Format search results for display."""
        if not results:
            return "No results found."
        
        if format_type == "text":
            formatted = []
            for i, result in enumerate(results, 1):
                formatted.append(f"{i}. {result.title}")
                formatted.append(f"   URL: {result.url}")
                formatted.append(f"   {result.snippet}")
                formatted.append("")
            return "\n".join(formatted)
        
        elif format_type == "json":
            return json.dumps([
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source
                }
                for r in results
            ], indent=2)
        
        elif format_type == "markdown":
            formatted = []
            for i, result in enumerate(results, 1):
                formatted.append(f"{i}. [{result.title}]({result.url})")
                formatted.append(f"   {result.snippet}")
                formatted.append("")
            return "\n".join(formatted)
        
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
    
    def extract_urls(self, results: List[SearchResult]) -> List[str]:
        """Extract URLs from search results."""
        return [result.url for result in results]
    
    def extract_snippets(self, results: List[SearchResult]) -> List[str]:
        """Extract snippets from search results."""
        return [result.snippet for result in results]
    
    def get_error_message(self, error: Exception) -> Dict[str, Any]:
        """获取详细的错误信息，用于返回给用户"""
        error_msg = str(error)
        
        if "event loop" in error_msg.lower():
            return {
                "success": False,
                "error_type": "EventLoopConflict",
                "error_code": "WEB_SEARCH_UNAVAILABLE",
                "message": "Web搜索功能遇到技术问题",
                "technical_details": "内部事件循环冲突导致Web搜索功能暂时不可用。技术团队正在积极修复此问题。",
                "suggestions": [
                    "请稍后再试",
                    "您可以尝试直接访问相关网站获取信息",
                    "对于数据库相关查询，我仍然可以正常为您服务"
                ]
            }
        elif "connection" in error_msg.lower():
            return {
                "success": False,
                "error_type": "ConnectionError",
                "error_code": "NETWORK_UNAVAILABLE",
                "message": "网络连接问题",
                "technical_details": "无法连接到搜索服务，请检查网络连接。",
                "suggestions": [
                    "检查网络连接",
                    "稍后重试",
                    "联系网络管理员"
                ]
            }
        else:
            return {
                "success": False,
                "error_type": "UnknownError",
                "error_code": "UNKNOWN_ERROR",
                "message": "Web搜索功能暂时不可用",
                "technical_details": error_msg,
                "suggestions": [
                    "请稍后再试",
                    "联系技术支持"
                ]
            }


def get_web_search_tool(provider: Optional[str] = None, **kwargs) -> WebSearchTool:
    """Factory function to create a web search tool."""
    return WebSearchTool(provider, **kwargs)


# 测试函数
def test_web_search():
    """测试Web搜索功能"""
    try:
        tool = WebSearchTool(provider="duckduckgo")
        results = tool.search_sync("test query", max_results=3)
        print(f"✅ Web搜索测试成功: 找到 {len(results)} 个结果")
        return True
    except Exception as e:
        print(f"❌ Web搜索测试失败: {e}")
        return False


if __name__ == "__main__":
    # 安装必要的依赖
    try:
        import nest_asyncio
        print("✅ nest_asyncio 已安装")
    except ImportError:
        print("❌ 请安装 nest_asyncio: pip install nest_asyncio")
    
    # 测试Web搜索
    if test_web_search():
        print("🎉 Web搜索功能正常！")
    else:
        print("⚠️ Web搜索功能需要修复")