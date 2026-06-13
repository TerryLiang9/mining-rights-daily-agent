# 5-Minute Run Guide

## Prerequisites

- Python 3.11
- Node.js 24+
- pnpm 10+
- Optional: Ollama running locally with Gemma available

The system can still run without Ollama because it falls back to a deterministic mock provider when model generation fails.

## Run With Docker Compose

```bash
docker compose up --build
```

Open http://localhost:5173.

If Docker Compose v5 fails during the build phase with a Docker session or bake error, build the same two images directly and then start Compose without rebuilding:

```bash
docker build -f apps/agent-api/Dockerfile -t mining-rights-daily-agent-agent-api .
docker build -f apps/web-dashboard/Dockerfile -t mining-rights-daily-agent-web-dashboard .
docker compose up --no-build
```

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
python -m mcp_servers.mining_news.server
python -m mcp_servers.mineral_pdf.server
python -m mcp_servers.lme_price.server
```

For Claude Desktop or Cursor, copy the server entries from `mcp-config.json`.

The Agent API also uses these MCP stdio server entries by default when generating reports.

## Verify

```bash
python -m pytest
pnpm --recursive test
pnpm --recursive build
docker compose config
```
