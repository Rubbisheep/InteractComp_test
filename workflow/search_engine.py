#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   workflow/search_engine.py
@Time    :   2025/08/11
@Author  :   Deng Mingyi
@Desc    :   搜索引擎模块：支持Mock/Google/Hybrid，从配置文件加载
"""

import yaml
import aiohttp
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
from utils.logs import logger


class SearchConfig:
    """搜索引擎配置管理"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self.config = config_dict
        self.engines = config_dict.get("search_engines", {})
        self.default_engine = config_dict.get("default_engine", "mock")
        self.safety = config_dict.get("safety", {})
        self.request_settings = config_dict.get("request_settings", {})
        
    @classmethod
    def load(cls, config_path: str = "config/search_config.yaml"):
        """从配置文件加载"""
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"Search config file not found: {config_path}, using defaults")
            return cls._default_config()
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
            logger.info(f"Search config loaded from: {config_path}")
            return cls(config_dict)
        except Exception as e:
            logger.error(f"Failed to load search config: {e}")
            return cls._default_config()
    
    @classmethod
    def _default_config(cls):
        """默认配置"""
        return cls({
            "search_engines": {
                "mock": {"enabled": True}
            },
            "default_engine": "mock",
            "safety": {"max_cost_per_day": 10.0},
            "request_settings": {"timeout": 10}
        })
    
    def get_engine_config(self, engine_name: str) -> Dict[str, Any]:
        """获取指定引擎的配置"""
        return self.engines.get(engine_name, {})
    
    def is_engine_enabled(self, engine_name: str) -> bool:
        """检查引擎是否启用"""
        return self.engines.get(engine_name, {}).get("enabled", False)


class SearchEngine(ABC):
    """搜索引擎抽象基类"""
    
    @abstractmethod
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """执行搜索并返回结果"""
        pass
    
    def format_results_for_agent(self, results: List[Dict[str, Any]]) -> str:
        """格式化搜索结果为Agent可读的文本"""
        if not results:
            return "No search results found."
        
        formatted_text = "Search Results:\n"
        for i, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            snippet = result.get("snippet", "No description available")
            source = result.get("source", "Unknown source")
            
            formatted_text += f"\n{i}. {title}\n"
            formatted_text += f"   {snippet}\n"
            formatted_text += f"   Source: {source}\n"
        
        return formatted_text


class MockSearchEngine(SearchEngine):
    """模拟搜索引擎"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        # 通用知识库
        self.knowledge_base = {
            "general_information": [
                "Search engines can provide information on various topics and subjects",
                "Information retrieval systems help users find relevant content",
                "Knowledge databases contain factual information about different domains",
                "Search results can include multiple perspectives on the same topic"
            ],
            "comparative_analysis": [
                "Many topics have similar concepts that can be distinguished by specific features",
                "Comparative analysis helps identify unique characteristics", 
                "Different entities may share common themes while having distinct properties",
                "Understanding differences requires examining specific details and attributes"
            ],
            "research_methodology": [
                "Effective research involves asking targeted questions",
                "Multiple sources can provide different viewpoints on the same subject",
                "Fact-checking and verification are important for accurate information",
                "Primary sources often provide more reliable information than secondary sources"
            ]
        }
        logger.info("MockSearchEngine initialized")
    
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """模拟搜索过程"""
        await asyncio.sleep(0.1)  # 模拟延迟
        
        logger.info(f"MockSearch: '{query}'")
        query_lower = query.lower()
        
        results = []
        
        # 通用关键词分类
        if any(word in query_lower for word in ["compare", "difference", "distinguish", "unique"]):
            category = "comparative_analysis"
        elif any(word in query_lower for word in ["research", "method", "source", "verify"]):
            category = "research_methodology"
        else:
            category = "general_information"
        
        # 生成搜索结果
        for i, content in enumerate(self.knowledge_base[category]):
            results.append({
                "title": f"Search Result {i+1}: {category.replace('_', ' ').title()}",
                "snippet": content,
                "source": f"knowledge_base_{category}",
                "relevance": 0.8 - i*0.1
            })
        
        # 添加基于查询的通用结果
        results.append({
            "title": f"General Information about: {query}",
            "snippet": f"Search results related to '{query}' may include various relevant sources and perspectives.",
            "source": "general_search_engine",
            "relevance": 0.6
        })
        
        return results[:3]  # 限制结果数量


class GoogleSearchEngine(SearchEngine):
    """Google Custom Search API"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key")
        self.search_engine_id = config.get("search_engine_id")  
        self.endpoint = config.get("endpoint", "https://www.googleapis.com/customsearch/v1")
        self.timeout = config.get("timeout", 10)
        
        if not self.api_key or not self.search_engine_id:
            raise ValueError("Google Search requires api_key and search_engine_id")
        
        logger.info("GoogleSearchEngine initialized")
    
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Google搜索实现"""
        logger.info(f"GoogleSearch: '{query}'")
        
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": 5,  # 最多5个结果
            "safe": "active",  # 安全搜索
            "fields": "items(title,snippet,link)"  # 只获取需要的字段
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.endpoint, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_google_results(data)
                    else:
                        error_text = await response.text()
                        raise Exception(f"Google API error {response.status}: {error_text}")
                        
        except asyncio.TimeoutError:
            raise Exception(f"Google search timeout after {self.timeout}s")
        except aiohttp.ClientError as e:
            raise Exception(f"Google search network error: {e}")
        except Exception as e:
            raise Exception(f"Google search failed: {e}")
    
    def _format_google_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """格式化Google搜索结果"""
        items = data.get("items", [])
        results = []
        
        for item in items:
            results.append({
                "title": item.get("title", "No title"),
                "snippet": item.get("snippet", "No description available"),
                "source": item.get("link", "No link"),
                "relevance": 0.9  # Google结果默认高相关性
            })
        
        logger.info(f"Google search returned {len(results)} results")
        return results


class HybridSearchEngine(SearchEngine):
    """混合搜索引擎"""
    
    def __init__(self, config: Dict[str, Any], search_config: SearchConfig):
        self.config = config
        self.search_config = search_config
        self.real_ratio = config.get("real_search_ratio", 0.3)
        self.primary_engine_name = config.get("primary_engine", "google")
        self.fallback_engine_name = config.get("fallback_engine", "mock")
        
        # 初始化子引擎
        self.mock_engine = MockSearchEngine()
        
        # 初始化主引擎
        primary_config = search_config.get_engine_config(self.primary_engine_name)
        if self.primary_engine_name == "google" and search_config.is_engine_enabled("google"):
            self.primary_engine = GoogleSearchEngine(primary_config)
        else:
            logger.warning(f"Primary engine {self.primary_engine_name} not available, using fallback")
            self.primary_engine = self.mock_engine
        
        logger.info(f"HybridSearchEngine initialized (real_ratio: {self.real_ratio})")
    
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """混合搜索"""
        import random
        
        logger.info(f"HybridSearch: '{query}'")
        
        # 根据比例决定使用真实搜索还是模拟搜索
        if random.random() < self.real_ratio:
            try:
                logger.info("Using primary search engine")
                results = await self.primary_engine.search(query)
                # 标记结果来源
                for result in results:
                    result["source_type"] = "real"
                return results
            except Exception as e:
                logger.warning(f"Primary search failed: {e}, falling back to mock")
                results = await self.mock_engine.search(query)
                for result in results:
                    result["source_type"] = "mock_fallback"
                return results
        else:
            logger.info("Using mock search engine")
            results = await self.mock_engine.search(query)
            for result in results:
                result["source_type"] = "mock"
            return results


def create_search_engine(engine_type: str = None, config_path: str = "config/search_config.yaml") -> SearchEngine:
    """
    工厂函数：根据配置创建搜索引擎
    
    Args:
        engine_type: 指定引擎类型，如果为None则使用配置文件中的默认值
        config_path: 配置文件路径
        
    Returns:
        SearchEngine实例
    """
    # 加载配置
    search_config = SearchConfig.load(config_path)
    
    # 确定要使用的引擎类型
    if engine_type is None:
        engine_type = search_config.default_engine
    
    logger.info(f"Creating search engine: {engine_type}")
    
    # 检查引擎是否启用
    if not search_config.is_engine_enabled(engine_type):
        logger.warning(f"Engine {engine_type} is not enabled, falling back to mock")
        engine_type = "mock"
    
    # 创建对应的搜索引擎
    if engine_type == "mock":
        return MockSearchEngine(search_config.get_engine_config("mock"))
    
    elif engine_type == "google":
        engine_config = search_config.get_engine_config("google")
        try:
            return GoogleSearchEngine(engine_config)
        except Exception as e:
            logger.error(f"Failed to create Google search engine: {e}")
            logger.info("Falling back to mock search engine")
            return MockSearchEngine()
    
    elif engine_type == "hybrid":
        engine_config = search_config.get_engine_config("hybrid")
        return HybridSearchEngine(engine_config, search_config)
    
    else:
        logger.warning(f"Unknown engine type: {engine_type}, using mock")
        return MockSearchEngine()