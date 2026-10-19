import os, asyncio, certifi
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
OPEN_WEATHER_API_KEY = os.getenv("OPEN_WEATHER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

#LLM
llm = ChatGroq(
    model = "openai/gpt-oss-20b",
    api_key= GROQ_API_KEY,
    #max_tokens=900
)





client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "http",  # 'sse' is the correct protocol for remote MCP servers
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={os.getenv('TAVILY_API_KEY', '')}"
        },

        "aviationstack": {
            "transport": "stdio",
            "command": "uvx",
            "args": [
                "aviationstack-mcp"
            ],
            "env": {
                "AVIATION_STACK_API_KEY": AVIATIONSTACK_API_KEY,
                "PATH": os.getenv("PATH", "")
            }
        },

        "weather": {
            "transport": "stdio",
            "command": r"C:\Users\Saish\Desktop\job_stuff\WanderBot-AI-Enterprise-Multi-Agent-Travel-Orchestrator\travel-env\Scripts\python.exe",
            "args": [
                r"C:\Users\Saish\Desktop\job_stuff\WanderBot-AI-Enterprise-Multi-Agent-Travel-Orchestrator\custom_whether_mcp_server.py"
            ],
            "env": {
                "OPEN_WEATHER_API_KEY": OPEN_WEATHER_API_KEY,
                "PATH": os.getenv("PATH", "")
            }
        }
    }
)


async def get_all_tools():
    tools = await client.get_tools()
    print("\nAvailable MCP Tools:\n")

    for tool in tools:
        print(tool.name)


search_tool = None
aviation_tools = {}

async def initialize_mcp():
    global search_tool
    global aviation_tools

    if search_tool is not None and aviation_tools:
        return

    tools = await client.get_tools()
    print("\nAvailable MCP Tools:\n")
    
    for tool in tools:
        print(tool.name)

    search_tool = next(
        tool
        for tool in tools
        if tool.name == "tavily_search"
    )

    aviation_tools = {
        tool.name: tool
        for tool in tools
        if tool.name != "tavily_search"
    }


async def tavily_mcp_search(query: str):
    await initialize_mcp()
    result = await search_tool.ainvoke(
        {
            "query": query
        }
    )
    return result


async def aviation_mcp_call(
        tool_name: str,
        tool_args: dict = None
):

    tools = await client.get_tools()

    tool = next(
        t for t in tools
        if t.name == tool_name
    )

    result = await tool.ainvoke(
        tool_args or {}
    )

    return result


weather_tool = None
forecast_tool = None

async def initialize_weather_tools():

    global weather_tool, forecast_tool

    if weather_tool is not None:
        return

    tools = await client.get_tools()

    weather_tool = next(
        t for t in tools
        if t.name == "get_current_wheather"
    )

    forecast_tool = next(
        t for t in tools
        if t.name == "get_forecast"
    )


async def weather_mcp_search(city: str):

    await initialize_weather_tools()

    return await weather_tool.ainvoke(
        {
            "city": city
        }
    )


async def forecast_mcp_search(city: str):

    await initialize_weather_tools()

    return await forecast_tool.ainvoke(
        {
            "city": city
        }
    )



# ==========================================
#           Destination extractor
# ==========================================

def extract_destination(query: str):
    prompt = f"""
    Extract only the destination city or country.

    Query:
    {query}

    Return only destination name.
    """

    response = llm.invoke(prompt)

    return response.content.strip()