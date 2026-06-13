# Mining Rights Daily Agent

An evidence-first MCP Agent for the Lingyun Zhikuang interview task. It generates a cited mining rights daily brief from three tool domains: mining news, NI 43-101-style resource data, and metal price trends.

## What It Demonstrates

- Three MCP servers: `mining-news-mcp`, `mineral-pdf-mcp`, and `lme-price-mcp`.
- Deterministic Agent orchestration before LLM writing.
- Ollama Gemma local LLM generation with mock fallback.
- TypeScript CLI and React Web Dashboard.
- Explicit citations, tool trace, fallback flags, warnings, and data quality disclosure.

## Quick Start

```bash
cp .env.example .env
python -m pip install -e ".[dev]"
pnpm install
python -m uvicorn app.main:app --app-dir apps/agent-api --reload --port 8000
```

Open another terminal:

```bash
pnpm cli report "给我生成一份关于 Pilbara 锂矿的今日简报"
```

Run the Web Dashboard:

```bash
pnpm --filter web-dashboard dev
```

Open http://localhost:5173.

## API

```bash
curl -X POST http://localhost:8000/reports ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"给我生成一份关于 Pilbara 锂矿的今日简报\"}"
```

## MCP Servers

The MCP servers are defined in `mcp-config.json` and can be connected to Claude Desktop or Cursor from the repository root:

```json
{
  "mcpServers": {
    "mining-news": {
      "command": "python",
      "args": ["mcp_servers/mining_news/server.py"]
    },
    "mineral-pdf": {
      "command": "python",
      "args": ["mcp_servers/mineral_pdf/server.py"]
    },
    "lme-price": {
      "command": "python",
      "args": ["mcp_servers/lme_price/server.py"]
    }
  }
}
```

## Verification

```bash
python -m pytest
pnpm --recursive test
pnpm --recursive build
docker compose config
```

## Design Choice

The Agent uses a deterministic workflow instead of unrestricted ReAct planning because local Gemma is better suited for summarization than strict tool planning. The system first builds an evidence pack, then asks the model to write only from that evidence. If a data source fails, fixture data is used and disclosed.
