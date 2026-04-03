import os
import sys
import asyncio
from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from browser import ChatGPTBrowser

mcp = FastMCP("gpt-search")

@mcp.tool()
async def gpt_search(query: str) -> str:
    """Search the web or research a topic using ChatGPT. Pass your full query as the prompt — it will be sent directly to ChatGPT and the response returned."""
    bot = ChatGPTBrowser()
    await bot.start()
    try:
        result = ""
        async for chunk in bot.stream_message(query):
            if chunk["type"] == "final":
                result = chunk["content"]
        import re
        result = re.sub(r'\s*\[\d+\]', '', result)
        return result
    finally:
        await bot.close()

if __name__ == "__main__":
    mcp.run(transport="stdio")
