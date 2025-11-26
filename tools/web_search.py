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

from config import get_settings


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
    """Main web search tool that manages different search providers."""
    
    def __init__(self, provider: Optional[str] = None, **kwargs):
        self.settings = get_settings()
        self.provider_name = provider or self.settings.web_search_provider
        self.provider = self._create_provider(**kwargs)
        self._session = None
    
    def _create_provider(self, **kwargs) -> BaseWebSearchProvider:
        """Create search provider based on configuration."""
        provider_config = self.settings.get_web_search_config()
        
        if self.provider_name.lower() == "duckduckgo":
            return DuckDuckGoProvider(**kwargs)
        elif self.provider_name.lower() == "google":
            api_key = provider_config.get("google_api_key")
            search_engine_id = provider_config.get("google_search_engine_id")
            if not api_key or not search_engine_id:
                raise WebSearchError("Google API key and search engine ID required")
            return GoogleSearchProvider(api_key, search_engine_id, **kwargs)
        elif self.provider_name.lower() == "bing":
            api_key = provider_config.get("bing_api_key")
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
    
    async def search_sync(self, query: str, max_results: int = 10, **kwargs) -> List[SearchResult]:
        """Synchronous wrapper for async search."""
        loop = asyncio.get_event_loop()
        return await loop.run_until_complete(self.search(query, max_results, **kwargs))
    
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


class WebSearchManager:
    """Manager for web search tools with caching and rate limiting."""
    
    def __init__(self):
        self.tools: Dict[str, WebSearchTool] = {}
        self.cache: Dict[str, List[SearchResult]] = {}
        self.cache_ttl = 3600  # 1 hour
        self.rate_limits: Dict[str, List[float]] = {}
        self.max_requests_per_minute = 60
    
    def add_tool(self, name: str, tool: WebSearchTool):
        """Add a web search tool."""
        self.tools[name] = tool
        logger.info(f"Added web search tool: {name}")
    
    def get_tool(self, name: str = "default") -> Optional[WebSearchTool]:
        """Get web search tool by name."""
        return self.tools.get(name)
    
    def create_tool(self, name: str = "default", provider: Optional[str] = None, **kwargs) -> WebSearchTool:
        """Create and add a web search tool."""
        tool = WebSearchTool(provider=provider, **kwargs)
        self.add_tool(name, tool)
        return tool
    
    async def search_with_cache(self, tool_name: str, query: str, max_results: int = 10, **kwargs) -> List[SearchResult]:
        """Search with caching support."""
        cache_key = f"{tool_name}:{query}:{max_results}"
        
        # Check cache
        if cache_key in self.cache:
            cached_results, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.info(f"Using cached results for query: {query}")
                return cached_results
        
        # Check rate limit
        if not self._check_rate_limit(tool_name):
            raise WebSearchError(f"Rate limit exceeded for tool: {tool_name}")
        
        # Perform search
        tool = self.get_tool(tool_name)
        if not tool:
            raise WebSearchError(f"Web search tool not found: {tool_name}")
        
        results = await tool.search(query, max_results, **kwargs)
        
        # Cache results
        self.cache[cache_key] = (results, time.time())
        
        return results
    
    def _check_rate_limit(self, tool_name: str) -> bool:
        """Check if tool is within rate limits."""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        if tool_name in self.rate_limits:
            self.rate_limits[tool_name] = [
                req_time for req_time in self.rate_limits[tool_name]
                if req_time > minute_ago
            ]
        else:
            self.rate_limits[tool_name] = []
        
        # Check limit
        if len(self.rate_limits[tool_name]) >= self.max_requests_per_minute:
            return False
        
        # Add current request
        self.rate_limits[tool_name].append(now)
        return True
    
    def clear_cache(self):
        """Clear search cache."""
        self.cache.clear()
        logger.info("Web search cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.cache),
            "cached_queries": list(self.cache.keys()),
            "rate_limits": {
                tool: len(requests) 
                for tool, requests in self.rate_limits.items()
            }
        }


# Global web search manager
_web_search_manager: Optional[WebSearchManager] = None


def get_web_search_manager() -> WebSearchManager:
    """Get global web search manager."""
    global _web_search_manager
    if _web_search_manager is None:
        _web_search_manager = WebSearchManager()
        # Create default tool
        _web_search_manager.create_tool("default")
    return _web_search_manager


def create_web_search_tool(name: str = "default", provider: Optional[str] = None, **kwargs) -> WebSearchTool:
    """Create and register a web search tool."""
    manager = get_web_search_manager()
    return manager.create_tool(name, provider, **kwargs)


def get_web_search_tool(name: str = "default") -> Optional[WebSearchTool]:
    """Get a registered web search tool."""
    manager = get_web_search_manager()
    return manager.get_tool(name)


async def web_search(query: str, max_results: int = 10, tool_name: str = "default", **kwargs) -> List[SearchResult]:
    """Convenience function for web search."""
    manager = get_web_search_manager()
    return await manager.search_with_cache(tool_name, query, max_results, **kwargs)