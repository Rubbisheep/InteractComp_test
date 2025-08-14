#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   workflow/search_engine.py
@Time    :   2025/08/11
@Author  :   Deng Mingyi
"""

import yaml
import aiohttp
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
from utils.logs import logger
from utils.async_llm import create_llm_instance
from workflow.prompt import SEARCH_PROMPT

class SearchEngine(ABC):
    
    @classmethod
    def load_config(cls, config_path: str = "config/search_config.yaml") -> Dict[str, Any]:
        config_file = Path(config_path)
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Config loaded from: {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    
    @abstractmethod
    async def search(self, query: str) -> List[Dict[str, Any]]:
        pass
    
    def format_results_for_agent(self, results: List[Dict[str, Any]]) -> str:
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


class LLMKnowledgeSearchEngine(SearchEngine):
    
    def __init__(self, llm_config=None):
        self.llm = create_llm_instance(llm_config)
        logger.info("LLMKnowledgeSearchEngine initialized")
    
    async def search(self, query: str) -> List[Dict[str, Any]]:
        logger.info(f"LLM Search: '{query}'")
        search_prompt = SEARCH_PROMPT.format(query=query)

        try:
            response = await self.llm(search_prompt)
            results = self._parse_llm_response(response, query)
            logger.info(f"LLM search returned {len(results)} knowledge items")
            return results
        except Exception as e:
            logger.error(f"LLM search failed: {e}")
            return [{
                "title": f"Search: {query}",
                "snippet": "LLM search temporarily unavailable. Please try a different search approach.",
                "source": "llm_knowledge_engine",
                "relevance": 0.1
            }]
    
    def _parse_llm_response(self, response: str, query: str) -> List[Dict[str, Any]]:
        text = str(response)
        
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if not paragraphs:
            raise Exception("LLM response parsing failed: no paragraphs found")
        
        results = []
        for i, paragraph in enumerate(paragraphs[:5]):
            title = ' '.join(paragraph.split()[:8]) + "..."
            results.append({
                "title": title,
                "snippet": paragraph,
                "source": "llm_internal_knowledge",
                "relevance": 0.9 - i * 0.1,
                "search_query": query,
            })
        
        return results


class GoogleSearchEngine(SearchEngine):
    
    def __init__(self, config: Dict[str, Any]):
        google_config = config.get("search_engines", {}).get("google", {})
        self.api_key = google_config.get("api_key")
        self.search_engine_id = google_config.get("search_engine_id")  
        self.endpoint = google_config.get("endpoint", "https://www.googleapis.com/customsearch/v1")
        self.timeout = config.get("request_settings", {}).get("timeout", 30)
        logger.info("GoogleSearchEngine initialized")
    
    async def search(self, query: str) -> List[Dict[str, Any]]:
        logger.info(f"Google Search: '{query}'")
        
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": 5,
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
        items = data["items"] 
        results = []
        
        for item in items:
            results.append({
                "title": item["title"],
                "snippet": item["snippet"],
                "source": item["link"],
                "relevance": 0.9
            })
        
        logger.info(f"Google search returned {len(results)} results")
        return results


class WikipediaSearchEngine(SearchEngine):
    
    def __init__(self, config: Dict[str, Any]):
        self.timeout = config.get("request_settings", {}).get("timeout", 10)
        self.search_api = "https://en.wikipedia.org/w/api.php"
        logger.info("WikipediaSearchEngine initialized")
    
    async def search(self, query: str) -> List[Dict[str, Any]]:
        logger.info(f"Wikipedia Search: '{query}'")
        
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 5,
            "format": "json"
        }
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:

            async with session.get(self.search_api, params=search_params) as response:
                data = await response.json()
                search_results = data["query"]["search"] 
                
                if not search_results:
                    return []
                
                page_titles = [result["title"] for result in search_results]
                return await self._get_page_extracts(session, page_titles, query)
    
    async def _get_page_extracts(self, session: aiohttp.ClientSession, titles: List[str], query: str) -> List[Dict[str, Any]]:
        """获取页面摘要"""
        extract_params = {
            "action": "query",
            "prop": "extracts|info",
            "titles": "|".join(titles),
            "exintro": True,
            "explaintext": True,
            "exchars": 300,
            "inprop": "url",
            "format": "json"
        }
        
        async with session.get(self.search_api, params=extract_params) as response:
            data = await response.json()
            pages = data["query"]["pages"]  
            
            results = []
            for page_id, page_data in pages.items():
                if page_id == "-1":  
                    continue
                
                results.append({
                    "title": page_data["title"],
                    "snippet": page_data["extract"][:300],
                    "source": page_data["fullurl"],
                    "relevance": 0.8,
                    "search_query": query
                })
            
            logger.info(f"Wikipedia search returned {len(results)} results")
            return results


def create_search_engine(
    engine_type: str, 
    config_path: str = "config/search_config.yaml",
    llm_config=None
) -> SearchEngine:
    
    config = SearchEngine.load_config(config_path)
    
    logger.info(f"Creating search engine: {engine_type}")
    
    if engine_type == "llm_knowledge":
        return LLMKnowledgeSearchEngine(llm_config=llm_config)
    
    elif engine_type == "google":
        return GoogleSearchEngine(config)
    
    elif engine_type == "wikipedia":
        return WikipediaSearchEngine(config)
    
    else:
        logger.warning(f"Unknown engine type: {engine_type}, using LLM knowledge search")
        return LLMKnowledgeSearchEngine(llm_config=llm_config)