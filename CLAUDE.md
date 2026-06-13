# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mining Rights Daily Agent — an evidence-first MCP Agent that generates cited Chinese-language mining rights daily briefs. It runs a **deterministic tool pipeline** (news search → article fetch → PDF resource extraction → price trend → price quote), builds a structured `EvidencePack`, then asks an LLM (Ollama Gemma by default) to write a Markdown report **only from that evidence**. A mock LLM provider and fixture data ensure the system runs without live sources.

## Build / Test / Run

```bash
# Install dependencies
python -m pip install -e ".[dev]"
pnpm install

# Run all tests (Python + TypeScript)
python -m pytest
pnpm --recursive test

# Build all TypeScript packages
pnpm --recursive build

# Start API server (port 8000)
python -m uvicorn app.main:app --app-dir apps/agent-api --reload --port 8000

# CLI — generate a report
pnpm cli report "给我生成一份关于 Pilbara 锂矿的今日简报"
pnpm cli report "<query>" --pdf data/pdfs/your-report.pdf

# Web Dashboard (port 5173)
pnpm --filter web-dashboard dev

# Docker (API on 8000, Web on 5173)
docker compose up --build
```

**Run a single Python test file:**
```bash
python -m pytest mcp_servers/mining_news/tests/test_tools.py
python -m pytest apps/agent-api/tests/test_orchestrator.py
```

**Run MCP servers standalone** (for debugging or Claude Desktop/Cursor):
```bash
python -m mcp_servers.mining_news.server
python -m mcp_servers.mineral_pdf.server
python -m mcp_servers.lme_price.server
```

## Architecture

### Deterministic Workflow (not ReAct)

The orchestrator (`apps/agent-api/app/orchestrator.py`) calls five tools in fixed order. This is deliberate — local Gemma handles summarization well but not open-ended tool planning. The tool order is code, not LLM reasoning.

### Tool Pipeline (orchestrator.py `generate_report`)

1. `mining-news-mcp.search` → 2. `mining-news-mcp.fetch_article` (per item) → 3. `mineral-pdf-mcp.extract_resources` → 4. `lme-price-mcp.get_trend` → 5. `lme-price-mcp.get_price`

Each result is unpacked into Pydantic models (`NewsSearchResult`, `Article`, `ResourceExtractionResult`, `PriceTrend`, `PriceQuote`). Traces, warnings, and fallback flags are collected per step. The final `EvidencePack` is the **only** input to the LLM.

### Three MCP Servers (`mcp_servers/`)

Each is a FastMCP stdio server with `tools.py` (logic), `providers.py` (data sources), and `server.py` (FastMCP entrypoint):

- **mining-news-mcp** — `search` (RSS or fixture, scored/filtered) and `fetch_article` (HTTP fetch + HTML extraction, blocked for localhost/local schemes)
- **mineral-pdf-mcp** — `extract_resources` (pypdf text extraction + regex parser for Measured/Indicated/Inferred resource lines). Returns `abstain=true` when no PDF is provided (does NOT fall back to fixture automatically)
- **lme-price-mcp** — `get_trend` and `get_price` (JSON, CSV, or fixture; nearest-prior-close for missing exact dates; commodity aliases)

### Agent API (`apps/agent-api/`)

- `app/main.py` — FastAPI app, single POST `/reports` endpoint + GET `/health`
- `app/orchestrator.py` — the deterministic pipeline; builds `EvidencePack`, selects LLM, validates required report sections
- `app/adapters/mcp_stdio.py` — `MCPStdioToolAdapter`: spawns Python MCP stdio subprocesses per tool call (reads `mcp-config.json`)
- `app/llm/ollama.py` — calls Ollama `/api/generate` with strict prompt (Chinese, evidence-only, no invention)
- `app/llm/mock.py` — deterministic mock provider, generates all required sections; used as fallback when Ollama fails or output is malformed

### Shared Package (`packages/shared/`)

- `mining_agent_shared/models.py` — all Pydantic models: `Topic`, `NewsItem`, `ResourceItem`, `PricePoint`, `PriceQuote`, `PriceTrend`, `EvidencePack`, `ReportRequest`, `ReportResponse`, `ToolTrace`, `Citation`
- `mining_agent_shared/config.py` — `Settings` via pydantic-settings, reads `.env`
- `mining_agent_shared/citations.py` — citation factory

### TypeScript Apps

- **agent-cli** (`apps/agent-cli/src/index.ts`) — CLI that calls the API, formats output
- **web-dashboard** (`apps/web-dashboard/src/App.tsx`) — React + Vite dashboard with query input, PDF URL field, Markdown render, tool trace panel, sources panel, data quality panel

### Monorepo Layout

- Python: single `pyproject.toml` at root with `packages/shared` as the only setuptools package
- Node: pnpm workspace with `apps/web-dashboard` and `apps/agent-cli`

## Data & Fixture Strategy

Fixture data lives in `data/fixtures/` (news.json, resources.json, prices.json, pilbara-resource-sample.pdf). Every fallback is **explicitly disclosed** in the tool response (`fallback_used: true`), warning list, API response, CLI output, Web Dashboard, and generated report.

Key rules:
- **News**: blank query → empty result (no fixture noise). RSS failure + `USE_FIXTURES_ON_FAILURE=true` → fixture. `USE_FIXTURES_ON_FAILURE=false` → empty with warning.
- **PDF**: only uses fixture when explicitly requested (`fixture://` or path ending in `resources.json`). Otherwise, missing PDF → `abstain=true`.
- **Price**: configured file/URL first; fixture fallback controlled by `USE_FIXTURES_ON_FAILURE`. Unsupported commodities → structured warning.

Configure live sources via `.env`: `MINING_NEWS_RSS_FEEDS`, `MINERAL_PDF_DEFAULT_URL`, `PRICE_DATA_FILE`, `PRICE_DATA_URL`.

## Required Report Sections

The orchestrator validates that generated reports contain all of: `Executive Summary`, `风险提示`, `数据质量说明`, `Sources`. If Ollama output misses any, the mock provider regenerates.

## Key Design Constraints

- The LLM prompt explicitly forbids inventing numbers, dates, URLs, or project names
- Article fetching rejects localhost/127.0.0.1/::1/.local URLs
- PDF extraction has a 30 MB size limit
- News `query` must be non-blank; `days` clamped to [1,90], `limit` to [1,20]
- Price `days` clamped to [1,365]; exact date misses use nearest prior close
- The tool adapter spawns a new stdio subprocess per call (not a persistent session)
