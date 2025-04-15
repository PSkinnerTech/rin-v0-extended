import os
import json
import aiohttp
import logging
import urllib.parse
from abc import ABC, abstractmethod
from rin.config import RIN_DIR
from rin.logging_config import loggers
from rin.llm import LLMInterface

logger = loggers.get('core', logging.getLogger('rin.search'))

# --- Search Provider Abstraction ---

class SearchProvider(ABC):
    """Abstract base class for search providers."""
    @abstractmethod
    async def search(self, query, num_results=5):
        """Perform search and return structured results or error dict."""
        pass

class SerpAPISearch(SearchProvider):
    """Search provider using SerpAPI."""
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
        if not self.api_key:
            raise ValueError("SERPAPI_KEY not found in environment variables.")
        logger.info("Initialized SerpAPISearch provider.")

    async def search(self, query, num_results=5):
        encoded_query = urllib.parse.quote(query)
        url = f"https://serpapi.com/search.json?q={encoded_query}&num={num_results}&api_key={self.api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error from SerpAPI ({response.status}): {error_text}")
                        return {"error": f"Search API error: {response.status}"}
                    
                    data = await response.json()
                    
                    # Basic result parsing
                    if "organic_results" not in data or not data["organic_results"]:
                        return {"results": []} # Return empty list if no organic results
                        
                    results = []
                    for res in data["organic_results"][:num_results]:
                         results.append({
                            "title": res.get("title", "No title"),
                            "link": res.get("link", "#"),
                            "snippet": res.get("snippet", "No description available.")
                        })
                    return {"results": results}
                    
        except Exception as e:
            logger.error(f"Error during SerpAPI search: {str(e)}", exc_info=True)
            return {"error": f"Failed to execute search: {str(e)}"}

class PlaceholderSearch(SearchProvider):
    """Placeholder for other search providers like SearxNG or DuckDuckGo."""
    async def search(self, query, num_results=5):
        logger.warning(f"PlaceholderSearch used for query: {query}. No actual search performed.")
        return {"error": "Search provider not fully implemented or API key not provided."}
        # Example structure if implemented:
        # return {"results": [{"title": "Example", "link": "#", "snippet": "..."}]}

# --- Factory Function --- 

def create_search_provider() -> SearchProvider:
    """Creates the configured search provider instance."""
    provider_name = os.getenv("SEARCH_PROVIDER", "serpapi").lower()
    
    if provider_name == "serpapi":
        try:
            return SerpAPISearch()
        except ValueError as e:
             logger.error(f"Failed to initialize SerpAPI: {e}. Falling back to placeholder.")
             return PlaceholderSearch()
    # Add elif for "searxng", "duckduckgo", etc. here
    # elif provider_name == "searxng":
    #    return SearxNGSearch() # Assuming SearxNGSearch class exists
    else:
        logger.warning(f"Unknown SEARCH_PROVIDER '{provider_name}'. Using placeholder.")
        return PlaceholderSearch()

# --- Web Search Manager ---

class WebSearchManager:
    """Manages web search and summarization using a configured SearchProvider."""
    
    def __init__(self):
        self.search_provider = create_search_provider()
        self.llm = LLMInterface.create() # Assuming LLMInterface factory exists
        logger.info(f"Web Search Manager initialized with provider: {self.search_provider.__class__.__name__}")
    
    async def search_and_summarize(self, query, num_results=5):
        """Search the web using the configured provider and summarize results."""
        try:
            # Perform the search using the provider
            search_result = await self.search_provider.search(query, num_results)
            
            if "error" in search_result:
                return {"error": search_result["error"]}
                
            results_list = search_result.get("results", [])
            if not results_list:
                 return {"summary": "I couldn't find any relevant web results for that query.", "results": []}
            
            # Format results for LLM summarization
            search_context = f"Search query: {query}\n\nTop {len(results_list)} results:\n"
            for i, result in enumerate(results_list):
                search_context += f"{i+1}. {result['title']}\n"
                search_context += f"   URL: {result['link']}\n"
                search_context += f"   Snippet: {result['snippet']}\n\n"
            
            # Generate a summary using the LLM
            prompt = f"""Please provide a concise summary of these search results for the query \"{query}\". 
            Focus on extracting the most relevant information that answers the query.
            If the results don't seem to address the query well, mention that.
            
            {search_context}
            
            Summary:"""
            
            summary = await self.llm.generate_response(prompt)
            
            return {
                "query": query,
                "results": results_list, # Return the structured results
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error in search and summarize: {str(e)}", exc_info=True)
            return {"error": f"An unexpected error occurred during search and summarization: {str(e)}"}

    async def raw_search(self, query, num_results=5):
         """Performs a raw search without summarization."""
         return await self.search_provider.search(query, num_results) 