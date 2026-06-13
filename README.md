# Mining Rights Daily Agent

MCP-based mining rights daily brief Agent for the Lingyun Zhikuang interview task.

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

## What It Demonstrates

- Three MCP servers: mining news, mineral PDF resources, and metal prices.
- Evidence-first Agent orchestration.
- Ollama Gemma local LLM generation with mock fallback.
- TypeScript CLI and Web Dashboard.
- Explicit citations, tool trace, fallback flags, and data quality warnings.
