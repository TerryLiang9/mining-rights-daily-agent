from mcp.server.fastmcp import FastMCP

from mcp_servers.mining_news.tools import fetch_article as fetch_article_tool
from mcp_servers.mining_news.tools import search as search_tool

mcp = FastMCP("mining-news-mcp")


@mcp.tool()
def search(query: str, days: int = 7, limit: int = 5) -> dict:
    """Search mining news for a topic."""
    return search_tool(query=query, days=days, limit=limit).model_dump()


@mcp.tool()
def fetch_article(url: str) -> dict:
    """Fetch article text by URL."""
    return fetch_article_tool(url=url).model_dump()


if __name__ == "__main__":
    mcp.run()
