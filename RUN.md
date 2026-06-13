# 5-Minute Run Guide

## Prerequisites

- Python 3.11
- Node.js 24+
- pnpm 10+
- Ollama running locally with Gemma available

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
