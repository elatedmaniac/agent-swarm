# Use the correct import path for FastMCP
from mcp.server.fastmcp import FastMCP
import arxiv
import os
import logging
import asyncio
import dotenv
# Import for SerpAPI 1.5.0
from serpapi.google_search import GoogleSearch

dotenv.load_dotenv()
serp_api_key = os.environ.get("SERP_API_KEY")

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the MCP server without specifying transport in constructor
mcp = FastMCP("ResearchAssistant", transport="streamable-http")

# Tool: Search arXiv for academic papers
@mcp.tool()
def search_arxiv(query: str, max_results: int = 5) -> list[dict]:
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
@mcp.tool()
def search_serp(query: str, num_results: int = 5) -> list[dict]:
    if not serp_api_key:
        logger.error("SERP_API_KEY environment variable not set")
        return [{"error": "API key not configured"}]
    
    params = {
        "q": query,
        "api_key": serp_api_key,
        "num": num_results
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        return results.get("organic_results", [])
    except Exception as e:
        logger.error(f"Error with SERP API: {e}")
        return [{"error": str(e)}]

# Health check endpoint for Docker
@mcp.tool()
def health_check() -> dict:
    return {"status": "ok"}

# Run the MCP server
if __name__ == "__main__":
    # Check if SERP API key is available
    if not os.environ.get("SERP_API_KEY"):
        logger.warning("SERP_API_KEY is not set! Search functionality will be limited.")
    
    # Log startup information
    logger.info("Starting MCP server with streamable-http transport")
    
    # Set UVICORN_HOST and UVICORN_PORT as environment variables
    # These are used by the MCP server when it starts the Uvicorn server internally
    os.environ["UVICORN_HOST"] = "0.0.0.0"
    os.environ["UVICORN_PORT"] = "8000"
    
    # Run the server with streamable-http transport
    # Using asyncio.run to properly handle the event loop
    mcp.run()
