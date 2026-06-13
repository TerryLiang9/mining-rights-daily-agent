# 5-Minute Run Guide

## Prerequisites

- Python 3.11
- Node.js 24+
- pnpm 10+
- Optional: Ollama running locally with Gemma available

The system can still run without Ollama because it falls back to a deterministic mock provider when model generation fails.

## Run API

```bash
cp .env.example .env
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --app-dir apps/agent-api --reload --port 8000
```

## Run CLI

```bash
pnpm install
pnpm cli report "给我生成一份关于 Pilbara 锂矿的今日简报"
```

## Run Web

```bash
pnpm --filter web-dashboard dev
```

Open http://localhost:5173.

## Run MCP Servers Directly

```bash
python mcp_servers/mining_news/server.py
python mcp_servers/mineral_pdf/server.py
python mcp_servers/lme_price/server.py
```

For Claude Desktop or Cursor, copy the server entries from `mcp-config.json`.

## Verify

```bash
python -m pytest
pnpm --recursive test
pnpm --recursive build
docker compose config
```
