import arxiv
import os
import logging
import asyncio
import os
import dotenv
import ollama
# Import for SerpAPI 1.5.0
from serpapi.google_search import GoogleSearch
# To install: pip install tavily-python
from tavily import TavilyClient

dotenv.load_dotenv()

SERP_API_KEY = os.getenv("SERP_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def arxiv_search(query: str, max_results: int = 5) -> list[dict]:
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    results = []
    for result in search.results():
        results.append({
            "title": result.title,
            "authors": [author.name for author in result.authors],
            "summary": result.summary,
            "pdf_url": result.pdf_url
        })
    return results

# Tool: Search Google using SerpApi
def serp_search(query: str, num_results: int = 5) -> list[dict]:
    if not SERP_API_KEY:
        return [{"error": "API key not configured"}]
    
    params = {
        "q": query,
        "api_key": SERP_API_KEY,
        "num": num_results
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        return results.get("organic_results", [])
    except Exception as e:
        return [{"error": str(e)}]
    
# Tool: Search Google using Tavily
def tavily_search(query: str, num_results: int = 5) -> list[dict]:
    if not TAVILY_API_KEY:
        return [{"error": "API key not configured"}]

    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(query=query, num_results=num_results)
    return response.get("results", [])