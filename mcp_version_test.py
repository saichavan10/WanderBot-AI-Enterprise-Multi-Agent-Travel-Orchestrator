import asyncio
from mcp_client import get_all_tools, tavily_mcp_search


if __name__ == "__main__":
    asyncio.run(get_all_tools())
    #query = "latest news about ai"
    #asyncio.run(tavily_mcp_search(query))