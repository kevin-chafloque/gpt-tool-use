# GPT Search MCP Server

An MCP tool for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that routes queries through ChatGPT via Playwright browser automation. Returns clean markdown responses with citation artifacts stripped out.

## Why

Claude Code can use MCP tools. This lets it delegate web search and research queries to ChatGPT, which has live web access. Responses come back as clean text — no bloated citation UI, no source links unless you ask for them.

### Token efficiency

When Claude does web research natively, it burns tokens on search results, page fetches, and reasoning about what it found. With this tool, ChatGPT does all the thinking — it searches, reads sources, reasons through the answer, and uses its own thinking tokens. Claude just gets back a clean result. You pay for fewer Claude tokens overall.

The tradeoff is speed. Browser automation is slower than a direct API call — ChatGPT needs to search, think, and stream its response. But if you're multitasking and don't need the answer immediately, it doesn't matter. Claude kicks off the query and you come back to a finished result.

## Setup

```bash
git clone https://github.com/kevin-chafloque/gpt-tool-use.git
cd gpt-tool-use
pip install -r requirements.txt
playwright install chromium
```

Run once to log into ChatGPT (opens a browser window):

```bash
python mcp_server.py
```

Then add to your Claude Code MCP config (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "gpt-search": {
      "command": "python",
      "args": ["/absolute/path/to/gpt-tool-use/mcp_server.py"]
    }
  }
}
```

## How it works

1. Your query is sent directly to ChatGPT as a prompt (no system prompt — you control the output)
2. Playwright waits for the response to finish streaming
3. JavaScript DOM evaluation strips citation buttons, SVGs, accordion dropdowns, and other UI artifacts
4. The cleaned HTML is converted to markdown via `markdownify`
5. Inline citation markers (`[1]`, `[2]`, etc.) are stripped before returning to Claude

## Files

| File | Purpose |
|------|---------|
| `mcp_server.py` | MCP server entry point (stdio transport) |
| `browser.py` | Playwright ChatGPT automation & DOM cleanup |
| `gpt_search.py` | Standalone CLI wrapper |

## Notes

- The `chatgpt_profile/` directory stores your persistent Chromium session. It's gitignored — you need to log in on each machine.
- Browser runs headed by default so you can complete the ChatGPT login on first run.
