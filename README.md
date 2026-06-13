# Mining Rights Daily Agent

An evidence-first MCP Agent for the Lingyun Zhikuang interview task. It generates a cited mining rights daily brief from three tool domains: mining news, NI 43-101-style resource data, and metal price trends.

## What It Demonstrates

- Three MCP servers: `mining-news-mcp`, `mineral-pdf-mcp`, and `lme-price-mcp`.
- Deterministic Agent orchestration before LLM writing, with tool calls routed through MCP stdio by default.
- Ollama Gemma local LLM generation with mock fallback.
- TypeScript CLI and React Web Dashboard.
- Explicit citations, tool trace, fallback flags, warnings, and data quality disclosure.

## Quick Start

Docker path:

```bash
docker compose up --build
```

Open http://localhost:5173.

Local development path:

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

Use a custom local or HTTP PDF report:

```bash
pnpm cli report "给我生成一份关于 Pilbara 锂矿的今日简报" --pdf data/pdfs/your-report.pdf
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
  -d "{\"query\":\"给我生成一份关于 Pilbara 锂矿的今日简报\",\"pdf_url\":\"data/pdfs/your-report.pdf\"}"
```

## MCP Servers

The MCP servers are defined in `mcp-config.json` and can be connected to Claude Desktop or Cursor from the repository root:

```json
{
  "mcpServers": {
    "mining-news-mcp": {
      "command": "python",
      "args": ["-m", "mcp_servers.mining_news.server"]
    },
    "mineral-pdf-mcp": {
      "command": "python",
      "args": ["-m", "mcp_servers.mineral_pdf.server"]
    },
    "lme-price-mcp": {
      "command": "python",
      "args": ["-m", "mcp_servers.lme_price.server"]
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

The Agent uses a deterministic workflow instead of unrestricted ReAct planning because local Gemma is better suited for summarization than strict tool planning. The system calls the three MCP servers through stdio, builds an evidence pack, then asks the model to write only from that evidence. If a data source fails, fixture data is used and disclosed.
