# Mining Rights Daily Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable MCP-based mining rights daily brief Agent with three MCP servers, a FastAPI orchestration API, Ollama Gemma generation, a TypeScript CLI, a TypeScript Web Dashboard, Docker Compose, tests, and delivery docs.

**Architecture:** The project uses an evidence-first workflow. Python MCP tools collect structured news, resource, and price evidence; FastAPI orchestrates those tools and calls Ollama Gemma or a mock LLM; TypeScript CLI and Web Dashboard call only the Agent API. MCP protocol entrypoints and HTTP demo paths reuse the same Python tool functions to avoid duplicate business logic.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, official MCP Python SDK `mcp>=1.27,<2`, httpx, pytest, Ollama Gemma, TypeScript, React, Vite, npm/pnpm workspaces, Docker Compose.

---

## Scope Check

This is one integrated implementation plan because the interview deliverable must run as one product. The tasks are still split by independently testable boundaries: foundation, shared schemas, three MCP servers, Agent API, CLI, Web Dashboard, Docker/docs, and final verification.

The MCP Python SDK plan uses the official `FastMCP` direct execution style:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My App")

@mcp.tool()
def hello(name: str = "World") -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
```

The dependency range must keep the v1 upper bound:

```toml
mcp[cli]>=1.27,<2
```

## File Responsibility Map

### Root

- `README.md`: first-screen overview, demo screenshots note, quick start, architecture, commands.
- `RUN.md`: 5-minute run path for interviewer.
- `DATA_NOTES.md`: schema, fixture, fallback, deduplication and data quality notes.
- `.env.example`: documented local config.
- `.gitignore`: Python, Node, env, output and cache ignores.
- `pyproject.toml`: Python dependencies, pytest config and package discovery.
- `package.json`: root workspace scripts.
- `pnpm-workspace.yaml`: TypeScript workspace package map.
- `docker-compose.yml`: `agent-api` and `web-dashboard` services.
- `mcp-config.json`: Claude Desktop / Cursor MCP server config.

### Python Shared Package

- `packages/shared/mining_agent_shared/models.py`: Pydantic schemas for all tool and report payloads.
- `packages/shared/mining_agent_shared/config.py`: environment config.
- `packages/shared/mining_agent_shared/logging.py`: JSON-ish logging helper.
- `packages/shared/mining_agent_shared/citations.py`: citation creation helpers.

### MCP Servers

- `mcp_servers/mining_news/tools.py`: news search and article fetch functions.
- `mcp_servers/mining_news/server.py`: FastMCP wrapper for news tools.
- `mcp_servers/mineral_pdf/tools.py`: resource extraction entrypoint.
- `mcp_servers/mineral_pdf/parser.py`: PDF text/table extraction helpers.
- `mcp_servers/mineral_pdf/server.py`: FastMCP wrapper for PDF tools.
- `mcp_servers/lme_price/tools.py`: price lookup and trend functions.
- `mcp_servers/lme_price/server.py`: FastMCP wrapper for price tools.

### Agent API

- `apps/agent-api/app/main.py`: FastAPI routes and app lifecycle.
- `apps/agent-api/app/schemas.py`: HTTP request/response aliases.
- `apps/agent-api/app/orchestrator.py`: deterministic Agent workflow.
- `apps/agent-api/app/llm/base.py`: LLM provider protocol.
- `apps/agent-api/app/llm/ollama.py`: Ollama HTTP provider.
- `apps/agent-api/app/llm/mock.py`: deterministic mock provider.
- `apps/agent-api/app/adapters/local_tools.py`: local adapter to reuse tool functions.

### TypeScript

- `apps/agent-cli/src/index.ts`: CLI that calls `POST /reports`.
- `apps/web-dashboard/src/App.tsx`: React UI shell.
- `apps/web-dashboard/src/api.ts`: Agent API client.
- `apps/web-dashboard/src/components/*.tsx`: focused display components.

### Data and Evaluation

- `data/fixtures/news.json`: deterministic sample news.
- `data/fixtures/resources.json`: deterministic sample NI 43-101-like resource data.
- `data/fixtures/prices.json`: deterministic sample commodity prices.
- `eval/sample_prompts.json`: smoke prompts.
- `eval/run_smoke_eval.py`: checks output sections and fallback disclosure.

---

## Task 1: Repository Foundation

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `pyproject.toml`
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `README.md`
- Create: `RUN.md`
- Create: `DATA_NOTES.md`

- [ ] **Step 1: Create root config files**

Create `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
node_modules/
dist/
build/
coverage/
outputs/
*.log
.DS_Store
```

Create `.env.example`:

```env
AGENT_API_HOST=0.0.0.0
AGENT_API_PORT=8000
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma
USE_FIXTURES_ON_FAILURE=true
```

Create `pyproject.toml`:

```toml
[project]
name = "mining-rights-daily-agent"
version = "0.1.0"
description = "MCP mining rights daily brief agent"
requires-python = ">=3.11"
dependencies = [
  "beautifulsoup4>=4.12,<5",
  "fastapi>=0.116,<1",
  "feedparser>=6.0,<7",
  "httpx>=0.28,<1",
  "mcp[cli]>=1.27,<2",
  "pydantic>=2.11,<3",
  "pydantic-settings>=2.10,<3",
  "pypdf>=5,<7",
  "python-dotenv>=1.0,<2",
  "uvicorn[standard]>=0.35,<1"
]

[project.optional-dependencies]
dev = [
  "pytest>=8,<9",
  "pytest-asyncio>=1,<2"
]

[tool.pytest.ini_options]
pythonpath = [
  ".",
  "packages/shared",
  "apps/agent-api"
]
testpaths = [
  "mcp_servers",
  "apps/agent-api",
  "eval"
]
```

Create `package.json`:

```json
{
  "name": "mining-rights-daily-agent",
  "private": true,
  "packageManager": "pnpm@10.33.0",
  "scripts": {
    "build": "pnpm --recursive build",
    "cli": "pnpm --filter agent-cli start --",
    "dev:web": "pnpm --filter web-dashboard dev",
    "test:python": "python -m pytest",
    "verify": "python -m pytest && pnpm --recursive build && docker compose config"
  },
  "devDependencies": {
    "@types/node": "^24.0.0",
    "typescript": "^5.8.0"
  }
}
```

Create `pnpm-workspace.yaml`:

```yaml
packages:
  - "apps/web-dashboard"
  - "apps/agent-cli"
```

- [ ] **Step 2: Create minimal docs**

Create `README.md`:

```markdown
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
```

Create `RUN.md`:

```markdown
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
```

Create `DATA_NOTES.md`:

```markdown
# Data Notes

The project uses fixture data when external mining news, PDF, or price sources are unavailable. Fallback use is explicit in the API response, CLI output, Web Dashboard, and generated report.

## Core Schemas

- News item: title, url, source, published_at, summary, score.
- Resource item: category, ore tonnage, grade, contained metal, units, page, confidence.
- Price point: commodity, date, price, currency, unit.
- Evidence pack: topic, news, resources, prices, citations, tool trace, data_quality.

## Data Quality Rules

- Missing PDF evidence returns abstain or fixture data.
- Unsupported commodity returns a structured warning.
- Generated reports must disclose fallback data.
```

- [ ] **Step 3: Verify foundation**

Run:

```bash
python --version
node --version
pnpm --version
```

Expected:

```text
Python 3.11.x
v24.x.x
10.x.x
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore .env.example pyproject.toml package.json pnpm-workspace.yaml README.md RUN.md DATA_NOTES.md
git commit -m "chore: initialize project foundation"
```

---

## Task 2: Shared Schemas and Fixture Data

**Files:**
- Create: `packages/shared/mining_agent_shared/__init__.py`
- Create: `packages/shared/mining_agent_shared/models.py`
- Create: `packages/shared/mining_agent_shared/config.py`
- Create: `packages/shared/mining_agent_shared/citations.py`
- Create: `data/fixtures/news.json`
- Create: `data/fixtures/resources.json`
- Create: `data/fixtures/prices.json`
- Test: `packages/shared/tests/test_models.py`

- [ ] **Step 1: Write schema tests**

Create `packages/shared/tests/test_models.py`:

```python
from mining_agent_shared.models import (
    Citation,
    EvidencePack,
    NewsItem,
    PricePoint,
    ResourceItem,
    Topic,
)


def test_evidence_pack_tracks_fallback():
    pack = EvidencePack(
        topic=Topic(raw_query="Pilbara lithium", region="Pilbara", commodity="lithium"),
        news=[
            NewsItem(
                title="Pilbara lithium update",
                url="https://example.com/news",
                source="fixture",
                published_at="2026-06-13",
                summary="Sample update",
                score=0.9,
            )
        ],
        resources=[
            ResourceItem(
                category="Indicated",
                ore_tonnage=120.5,
                ore_tonnage_unit="Mt",
                grade=1.25,
                grade_unit="% Li2O",
                contained_metal=1.5,
                contained_metal_unit="Mt LCE",
                page=42,
                confidence=0.8,
            )
        ],
        prices=[PricePoint(date="2026-06-13", price=12850.0)],
        citations=[Citation(label="fixture news", url="https://example.com/news", source_type="news")],
        fallback_used=True,
        warnings=["Using fixture data"],
    )

    assert pack.fallback_used is True
    assert pack.topic.commodity == "lithium"
    assert pack.citations[0].source_type == "news"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest packages/shared/tests/test_models.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'mining_agent_shared'
```

- [ ] **Step 3: Implement shared models**

Create `packages/shared/mining_agent_shared/__init__.py`:

```python
"""Shared schemas and helpers for the mining rights daily agent."""
```

Create `packages/shared/mining_agent_shared/models.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Topic(BaseModel):
    raw_query: str
    region: str = "global"
    commodity: str = "lithium"
    days: int = Field(default=7, ge=1, le=90)
    language: str = "zh"
    report_type: str = "daily_brief"


class Citation(BaseModel):
    label: str
    url: str
    source_type: Literal["news", "pdf", "price", "fixture"]
    retrieved_at: str | None = None


class ToolTrace(BaseModel):
    tool: str
    input: dict
    status: Literal["success", "partial", "fallback", "error"]
    duration_ms: int
    fallback_used: bool = False
    message: str | None = None


class NewsItem(BaseModel):
    title: str
    url: str
    source: str
    published_at: str
    summary: str
    score: float = Field(ge=0, le=1)


class NewsSearchResult(BaseModel):
    items: list[NewsItem]
    fallback_used: bool = False
    retrieved_at: str
    warnings: list[str] = []


class Article(BaseModel):
    url: str
    title: str
    text: str
    published_at: str | None = None
    source: str
    fallback_used: bool = False
    warnings: list[str] = []


class ResourceItem(BaseModel):
    category: Literal["Measured", "Indicated", "Inferred", "Other"]
    ore_tonnage: float | None = None
    ore_tonnage_unit: str | None = None
    grade: float | None = None
    grade_unit: str | None = None
    contained_metal: float | None = None
    contained_metal_unit: str | None = None
    page: int | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)


class ResourceExtractionResult(BaseModel):
    project_name: str
    report_title: str
    resources: list[ResourceItem]
    abstain: bool = False
    fallback_used: bool = False
    source_url: str
    warnings: list[str] = []


class PricePoint(BaseModel):
    date: str
    price: float


class PriceTrend(BaseModel):
    commodity: str
    days: int
    points: list[PricePoint]
    change_pct: float | None = None
    trend: Literal["up", "down", "flat", "insufficient_data"]
    currency: str = "USD"
    unit: str = "t"
    source: str
    fallback_used: bool = False
    warnings: list[str] = []


class EvidencePack(BaseModel):
    topic: Topic
    news: list[NewsItem] = []
    articles: list[Article] = []
    resources: list[ResourceItem] = []
    prices: list[PricePoint] = []
    price_trend: PriceTrend | None = None
    citations: list[Citation] = []
    tool_trace: list[ToolTrace] = []
    fallback_used: bool = False
    warnings: list[str] = []


class ReportRequest(BaseModel):
    query: str
    days: int = Field(default=7, ge=1, le=90)


class ReportResponse(BaseModel):
    markdown: str
    citations: list[Citation]
    tool_trace: list[ToolTrace]
    fallback_used: bool
    warnings: list[str] = []
```

Create `packages/shared/mining_agent_shared/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_api_host: str = "0.0.0.0"
    agent_api_port: int = 8000
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma"
    use_fixtures_on_failure: bool = True


def get_settings() -> Settings:
    return Settings()
```

Create `packages/shared/mining_agent_shared/citations.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime

from mining_agent_shared.models import Citation


def make_citation(label: str, url: str, source_type: str) -> Citation:
    return Citation(
        label=label,
        url=url,
        source_type=source_type,
        retrieved_at=datetime.now(UTC).isoformat(),
    )
```

- [ ] **Step 4: Add fixture data**

Create `data/fixtures/news.json`:

```json
[
  {
    "title": "Pilbara lithium developers monitor export and processing policy signals",
    "url": "https://example.com/pilbara-lithium-policy",
    "source": "fixture-mining-news",
    "published_at": "2026-06-12",
    "summary": "Sample mining news item about Pilbara lithium policy and project execution.",
    "score": 0.91
  },
  {
    "title": "Australian critical minerals projects focus on downstream partnerships",
    "url": "https://example.com/australia-critical-minerals",
    "source": "fixture-mining-news",
    "published_at": "2026-06-11",
    "summary": "Sample item covering critical minerals partnerships and financing signals.",
    "score": 0.84
  }
]
```

Create `data/fixtures/resources.json`:

```json
{
  "project_name": "Pilbara lithium sample",
  "report_title": "Sample NI 43-101 Technical Report",
  "source_url": "data/fixtures/resources.json",
  "resources": [
    {
      "category": "Indicated",
      "ore_tonnage": 120.5,
      "ore_tonnage_unit": "Mt",
      "grade": 1.25,
      "grade_unit": "% Li2O",
      "contained_metal": 1.5,
      "contained_metal_unit": "Mt LCE",
      "page": 42,
      "confidence": 0.78
    },
    {
      "category": "Inferred",
      "ore_tonnage": 80.2,
      "ore_tonnage_unit": "Mt",
      "grade": 1.05,
      "grade_unit": "% Li2O",
      "contained_metal": 0.9,
      "contained_metal_unit": "Mt LCE",
      "page": 43,
      "confidence": 0.72
    }
  ]
}
```

Create `data/fixtures/prices.json`:

```json
{
  "lithium": {
    "currency": "USD",
    "unit": "t",
    "points": [
      { "date": "2026-05-15", "price": 12100 },
      { "date": "2026-05-22", "price": 12340 },
      { "date": "2026-05-29", "price": 12620 },
      { "date": "2026-06-05", "price": 12740 },
      { "date": "2026-06-13", "price": 12850 }
    ]
  },
  "copper": {
    "currency": "USD",
    "unit": "t",
    "points": [
      { "date": "2026-05-15", "price": 9450 },
      { "date": "2026-06-13", "price": 9580 }
    ]
  }
}
```

- [ ] **Step 5: Run shared tests**

Run:

```bash
python -m pytest packages/shared/tests/test_models.py -v
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit**

```bash
git add packages/shared data/fixtures pyproject.toml
git commit -m "feat: add shared schemas and fixtures"
```

---

## Task 3: Mining News MCP Server

**Files:**
- Create: `mcp_servers/__init__.py`
- Create: `mcp_servers/mining_news/__init__.py`
- Create: `mcp_servers/mining_news/tools.py`
- Create: `mcp_servers/mining_news/server.py`
- Test: `mcp_servers/mining_news/tests/test_tools.py`

- [ ] **Step 1: Write failing tests**

Create `mcp_servers/mining_news/tests/test_tools.py`:

```python
from mcp_servers.mining_news.tools import fetch_article, search


def test_search_uses_fixture_news():
    result = search("Pilbara lithium", days=7, limit=2)
    assert result.items
    assert result.items[0].title
    assert result.fallback_used is True


def test_fetch_article_returns_text_for_fixture_url():
    result = fetch_article("https://example.com/pilbara-lithium-policy")
    assert result.url == "https://example.com/pilbara-lithium-policy"
    assert "Pilbara" in result.text
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest mcp_servers/mining_news/tests/test_tools.py -v
```

Expected:

```text
ModuleNotFoundError
```

- [ ] **Step 3: Implement news tools**

Create `mcp_servers/__init__.py`:

```python
"""MCP server packages."""
```

Create `mcp_servers/mining_news/__init__.py`:

```python
"""Mining news MCP tools."""
```

Create `mcp_servers/mining_news/tools.py`:

```python
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from mining_agent_shared.models import Article, NewsItem, NewsSearchResult

FIXTURE_PATH = Path("data/fixtures/news.json")


def _load_fixture_items() -> list[NewsItem]:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [NewsItem(**item) for item in raw]


def search(query: str, days: int = 7, limit: int = 5) -> NewsSearchResult:
    terms = [term.lower() for term in query.split() if term.strip()]
    items = _load_fixture_items()
    scored = []
    for item in items:
        haystack = f"{item.title} {item.summary}".lower()
        matched = sum(1 for term in terms if term in haystack)
        score = max(item.score, min(1.0, 0.5 + matched * 0.2))
        scored.append(item.model_copy(update={"score": score}))
    scored.sort(key=lambda item: item.score, reverse=True)
    return NewsSearchResult(
        items=scored[:limit],
        fallback_used=True,
        retrieved_at=datetime.now(UTC).isoformat(),
        warnings=["Using fixture mining news for reproducible interview demo."],
    )


def fetch_article(url: str) -> Article:
    for item in _load_fixture_items():
        if item.url == url:
            return Article(
                url=item.url,
                title=item.title,
                text=f"{item.title}\n\n{item.summary}\n\nThis fixture article discusses Pilbara lithium project signals, policy context, and execution risks.",
                published_at=item.published_at,
                source=item.source,
                fallback_used=True,
                warnings=["Article body generated from fixture summary."],
            )
    return Article(
        url=url,
        title="Unavailable article",
        text="Article body unavailable. The Agent should disclose this partial evidence.",
        source="unknown",
        fallback_used=True,
        warnings=["Requested article URL was not found in fixture data."],
    )
```

- [ ] **Step 4: Implement FastMCP wrapper**

Create `mcp_servers/mining_news/server.py`:

```python
from mcp.server.fastmcp import FastMCP

from mcp_servers.mining_news.tools import fetch_article as fetch_article_tool
from mcp_servers.mining_news.tools import search as search_tool

mcp = FastMCP("mining-news-mcp")


@mcp.tool()
def search(query: str, days: int = 7, limit: int = 5) -> dict:
    """Search mining news for a topic."""
    return search_tool(query=query, days=days, limit=limit).model_dump()


@mcp.tool()
def fetch_article(url: str) -> dict:
    """Fetch article text by URL."""
    return fetch_article_tool(url=url).model_dump()


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m pytest mcp_servers/mining_news/tests/test_tools.py -v
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Smoke check MCP server import**

Run:

```bash
python -c "from mcp_servers.mining_news.server import mcp; print(mcp.name)"
```

Expected:

```text
mining-news-mcp
```

- [ ] **Step 7: Commit**

```bash
git add mcp_servers/mining_news mcp_servers/__init__.py
git commit -m "feat: add mining news MCP server"
```

---

## Task 4: Mineral PDF MCP Server

**Files:**
- Create: `mcp_servers/mineral_pdf/__init__.py`
- Create: `mcp_servers/mineral_pdf/parser.py`
- Create: `mcp_servers/mineral_pdf/tools.py`
- Create: `mcp_servers/mineral_pdf/server.py`
- Test: `mcp_servers/mineral_pdf/tests/test_tools.py`

- [ ] **Step 1: Write failing tests**

Create `mcp_servers/mineral_pdf/tests/test_tools.py`:

```python
from mcp_servers.mineral_pdf.tools import extract_resources


def test_extract_resources_falls_back_to_fixture():
    result = extract_resources("fixture://pilbara-lithium", project_name="Pilbara")
    assert result.project_name == "Pilbara lithium sample"
    assert result.resources
    assert result.resources[0].category == "Indicated"
    assert result.fallback_used is True
    assert result.abstain is False
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest mcp_servers/mineral_pdf/tests/test_tools.py -v
```

Expected:

```text
ModuleNotFoundError
```

- [ ] **Step 3: Implement parser and tools**

Create `mcp_servers/mineral_pdf/__init__.py`:

```python
"""Mineral PDF MCP tools."""
```

Create `mcp_servers/mineral_pdf/parser.py`:

```python
from __future__ import annotations

import re

from mining_agent_shared.models import ResourceItem


RESOURCE_PATTERN = re.compile(
    r"(?P<category>Indicated|Inferred)\s+"
    r"(?P<tonnage>\d+(?:\.\d+)?)\s*Mt\s+"
    r"(?P<grade>\d+(?:\.\d+)?)\s*%\s*Li2O\s+"
    r"(?P<metal>\d+(?:\.\d+)?)\s*Mt\s*LCE",
    re.IGNORECASE,
)


def parse_resource_lines(text: str) -> list[ResourceItem]:
    resources: list[ResourceItem] = []
    for match in RESOURCE_PATTERN.finditer(text):
        category = match.group("category").title()
        resources.append(
            ResourceItem(
                category=category,
                ore_tonnage=float(match.group("tonnage")),
                ore_tonnage_unit="Mt",
                grade=float(match.group("grade")),
                grade_unit="% Li2O",
                contained_metal=float(match.group("metal")),
                contained_metal_unit="Mt LCE",
                confidence=0.7,
            )
        )
    return resources
```

Create `mcp_servers/mineral_pdf/tools.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from mining_agent_shared.models import ResourceExtractionResult, ResourceItem

FIXTURE_PATH = Path("data/fixtures/resources.json")


def _load_fixture() -> ResourceExtractionResult:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return ResourceExtractionResult(
        project_name=raw["project_name"],
        report_title=raw["report_title"],
        source_url=raw["source_url"],
        resources=[ResourceItem(**item) for item in raw["resources"]],
        fallback_used=True,
        warnings=["Using fixture NI 43-101-like resource data for reproducible demo."],
    )


def extract_resources(pdf_url: str, project_name: str | None = None) -> ResourceExtractionResult:
    if pdf_url.startswith("fixture://") or pdf_url.startswith("data/"):
        return _load_fixture()
    return ResourceExtractionResult(
        project_name=project_name or "unknown",
        report_title="Unavailable NI 43-101 report",
        source_url=pdf_url,
        resources=[],
        abstain=True,
        fallback_used=False,
        warnings=["PDF extraction abstained because no supported report fixture matched the URL."],
    )
```

- [ ] **Step 4: Implement FastMCP wrapper**

Create `mcp_servers/mineral_pdf/server.py`:

```python
from mcp.server.fastmcp import FastMCP

from mcp_servers.mineral_pdf.tools import extract_resources as extract_resources_tool

mcp = FastMCP("mineral-pdf-mcp")


@mcp.tool()
def extract_resources(pdf_url: str, project_name: str | None = None) -> dict:
    """Extract Indicated and Inferred resources from a mineral technical report."""
    return extract_resources_tool(pdf_url=pdf_url, project_name=project_name).model_dump()


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
python -m pytest mcp_servers/mineral_pdf/tests/test_tools.py -v
```

Expected:

```text
1 passed
```

Commit:

```bash
git add mcp_servers/mineral_pdf
git commit -m "feat: add mineral PDF MCP server"
```

---

## Task 5: LME Price MCP Server

**Files:**
- Create: `mcp_servers/lme_price/__init__.py`
- Create: `mcp_servers/lme_price/tools.py`
- Create: `mcp_servers/lme_price/server.py`
- Test: `mcp_servers/lme_price/tests/test_tools.py`

- [ ] **Step 1: Write failing tests**

Create `mcp_servers/lme_price/tests/test_tools.py`:

```python
from mcp_servers.lme_price.tools import get_price, get_trend


def test_get_trend_returns_fixture_change():
    trend = get_trend("lithium", days=30)
    assert trend.commodity == "lithium"
    assert trend.points
    assert trend.trend == "up"
    assert trend.fallback_used is True


def test_get_price_returns_latest_point():
    price = get_price("lithium")
    assert price["commodity"] == "lithium"
    assert price["price"] == 12850
```

- [ ] **Step 2: Implement price tools**

Create `mcp_servers/lme_price/__init__.py`:

```python
"""LME price MCP tools."""
```

Create `mcp_servers/lme_price/tools.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from mining_agent_shared.models import PricePoint, PriceTrend

FIXTURE_PATH = Path("data/fixtures/prices.json")


def _load_prices() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def get_trend(commodity: str, days: int = 30) -> PriceTrend:
    data = _load_prices()
    key = commodity.lower()
    if key not in data:
        return PriceTrend(
            commodity=key,
            days=days,
            points=[],
            trend="insufficient_data",
            source="fixture",
            fallback_used=True,
            warnings=[f"Unsupported commodity: {commodity}"],
        )
    payload = data[key]
    points = [PricePoint(**point) for point in payload["points"]]
    if len(points) < 2:
        change_pct = None
        trend = "insufficient_data"
    else:
        first = points[0].price
        last = points[-1].price
        change_pct = round(((last - first) / first) * 100, 2)
        trend = "up" if change_pct > 1 else "down" if change_pct < -1 else "flat"
    return PriceTrend(
        commodity=key,
        days=days,
        points=points,
        change_pct=change_pct,
        trend=trend,
        currency=payload.get("currency", "USD"),
        unit=payload.get("unit", "t"),
        source="fixture",
        fallback_used=True,
        warnings=["Using fixture price data for reproducible demo."],
    )


def get_price(commodity: str, date: str | None = None) -> dict:
    trend = get_trend(commodity, days=30)
    if not trend.points:
        return {
            "commodity": commodity.lower(),
            "date": date,
            "price": None,
            "source": "fixture",
            "fallback_used": True,
            "warnings": trend.warnings,
        }
    point = trend.points[-1]
    return {
        "commodity": trend.commodity,
        "date": point.date,
        "price": point.price,
        "currency": trend.currency,
        "unit": trend.unit,
        "source": trend.source,
        "fallback_used": trend.fallback_used,
    }
```

- [ ] **Step 3: Implement FastMCP wrapper**

Create `mcp_servers/lme_price/server.py`:

```python
from mcp.server.fastmcp import FastMCP

from mcp_servers.lme_price.tools import get_price as get_price_tool
from mcp_servers.lme_price.tools import get_trend as get_trend_tool

mcp = FastMCP("lme-price-mcp")


@mcp.tool()
def get_price(commodity: str, date: str | None = None) -> dict:
    """Get latest or date-specific commodity price."""
    return get_price_tool(commodity=commodity, date=date)


@mcp.tool()
def get_trend(commodity: str, days: int = 30) -> dict:
    """Get commodity price trend."""
    return get_trend_tool(commodity=commodity, days=days).model_dump()


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
python -m pytest mcp_servers/lme_price/tests/test_tools.py -v
```

Expected:

```text
2 passed
```

Commit:

```bash
git add mcp_servers/lme_price
git commit -m "feat: add price MCP server"
```

---

## Task 6: Agent API and LLM Providers

**Files:**
- Create: `apps/agent-api/app/__init__.py`
- Create: `apps/agent-api/app/main.py`
- Create: `apps/agent-api/app/orchestrator.py`
- Create: `apps/agent-api/app/llm/__init__.py`
- Create: `apps/agent-api/app/llm/base.py`
- Create: `apps/agent-api/app/llm/mock.py`
- Create: `apps/agent-api/app/llm/ollama.py`
- Create: `apps/agent-api/app/adapters/__init__.py`
- Create: `apps/agent-api/app/adapters/local_tools.py`
- Test: `apps/agent-api/tests/test_orchestrator.py`

- [ ] **Step 1: Write failing orchestrator test**

Create `apps/agent-api/tests/test_orchestrator.py`:

```python
from app.orchestrator import generate_report


def test_generate_report_contains_required_sections():
    response = generate_report("给我生成一份关于 Pilbara 锂矿的今日简报", days=7, llm_provider="mock")
    assert "Executive Summary" in response.markdown
    assert "风险提示" in response.markdown
    assert "数据质量说明" in response.markdown
    assert response.citations
    assert response.fallback_used is True
```

- [ ] **Step 2: Implement local tools adapter**

Create `apps/agent-api/app/adapters/__init__.py`:

```python
"""Agent API adapters."""
```

Create `apps/agent-api/app/adapters/local_tools.py`:

```python
from mcp_servers.lme_price.tools import get_trend
from mcp_servers.mineral_pdf.tools import extract_resources
from mcp_servers.mining_news.tools import fetch_article, search

__all__ = ["search", "fetch_article", "extract_resources", "get_trend"]
```

- [ ] **Step 3: Implement LLM providers**

Create `apps/agent-api/app/llm/__init__.py`:

```python
"""LLM providers."""
```

Create `apps/agent-api/app/llm/base.py`:

```python
from __future__ import annotations

from typing import Protocol

from mining_agent_shared.models import EvidencePack


class LLMProvider(Protocol):
    def generate_report(self, evidence: EvidencePack) -> str:
        """Generate a Markdown report from an evidence pack."""
```

Create `apps/agent-api/app/llm/mock.py`:

```python
from mining_agent_shared.models import EvidencePack


class MockLLMProvider:
    def generate_report(self, evidence: EvidencePack) -> str:
        commodity = evidence.topic.commodity
        region = evidence.topic.region
        fallback_note = "本报告使用了样例数据/fallback 数据。" if evidence.fallback_used else "本报告未使用 fallback 数据。"
        sources = "\n".join(f"- {citation.label}: {citation.url}" for citation in evidence.citations)
        return f"""# {region} {commodity} 矿权日报

## Executive Summary
- 当前简报基于新闻、资源量和价格三个工具的结构化证据生成。
- 价格趋势为 {evidence.price_trend.trend if evidence.price_trend else "insufficient_data"}。
- 数据质量需要结合 fallback 标记判断。

## 新闻动态
{chr(10).join(f"- {item.title}: {item.summary}" for item in evidence.news)}

## 储量/资源量快照
{chr(10).join(f"- {item.category}: {item.ore_tonnage} {item.ore_tonnage_unit}, grade {item.grade} {item.grade_unit}" for item in evidence.resources)}

## 价格趋势
- 近 30 天趋势：{evidence.price_trend.trend if evidence.price_trend else "insufficient_data"}。

## 风险提示
- 外部数据源不可用时会使用样例数据。
- PDF 抽取证据不足时应进入人工复核。

## 数据质量说明
{fallback_note}

## Sources
{sources}
"""
```

Create `apps/agent-api/app/llm/ollama.py`:

```python
import httpx

from mining_agent_shared.models import EvidencePack


class OllamaProvider:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate_report(self, evidence: EvidencePack) -> str:
        prompt = self._build_prompt(evidence)
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["response"]

    def _build_prompt(self, evidence: EvidencePack) -> str:
        return (
            "You are a mining intelligence analyst. Write a concise Markdown daily brief in Chinese. "
            "Use only the evidence below. Do not invent numbers, dates, URLs, or project names. "
            "Required sections: Executive Summary, 新闻动态, 储量/资源量快照, 价格趋势, 风险提示, 数据质量说明, Sources.\n\n"
            f"<evidence>{evidence.model_dump_json()}</evidence>"
        )
```

- [ ] **Step 4: Implement orchestrator and API**

Create `apps/agent-api/app/__init__.py`:

```python
"""FastAPI Agent API."""
```

Create `apps/agent-api/app/orchestrator.py`:

```python
from __future__ import annotations

from time import perf_counter

from app.adapters.local_tools import extract_resources, fetch_article, get_trend, search
from app.llm.mock import MockLLMProvider
from app.llm.ollama import OllamaProvider
from mining_agent_shared.citations import make_citation
from mining_agent_shared.config import get_settings
from mining_agent_shared.models import EvidencePack, ReportResponse, ToolTrace, Topic


def parse_topic(query: str, days: int) -> Topic:
    lowered = query.lower()
    region = "Pilbara" if "pilbara" in lowered else "global"
    commodity = "lithium" if ("锂" in query or "lithium" in lowered) else "copper" if ("铜" in query or "copper" in lowered) else "lithium"
    return Topic(raw_query=query, region=region, commodity=commodity, days=days)


def _trace(tool: str, input_payload: dict, status: str, start: float, fallback_used: bool, message: str | None = None) -> ToolTrace:
    return ToolTrace(
        tool=tool,
        input=input_payload,
        status=status,
        duration_ms=int((perf_counter() - start) * 1000),
        fallback_used=fallback_used,
        message=message,
    )


def _select_llm(provider_name: str):
    settings = get_settings()
    if provider_name == "mock":
        return MockLLMProvider()
    if provider_name == "ollama":
        return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
    return MockLLMProvider()


def generate_report(query: str, days: int = 7, llm_provider: str | None = None) -> ReportResponse:
    settings = get_settings()
    topic = parse_topic(query, days)
    traces: list[ToolTrace] = []
    warnings: list[str] = []

    start = perf_counter()
    news_result = search(f"{topic.region} {topic.commodity} mining", days=days, limit=3)
    traces.append(_trace("mining-news-mcp.search", {"query": query, "days": days}, "fallback" if news_result.fallback_used else "success", start, news_result.fallback_used))
    warnings.extend(news_result.warnings)

    articles = []
    for item in news_result.items[:2]:
        start = perf_counter()
        article = fetch_article(item.url)
        articles.append(article)
        traces.append(_trace("mining-news-mcp.fetch_article", {"url": item.url}, "fallback" if article.fallback_used else "success", start, article.fallback_used))
        warnings.extend(article.warnings)

    start = perf_counter()
    resources = extract_resources("fixture://pilbara-lithium", project_name=topic.region)
    traces.append(_trace("mineral-pdf-mcp.extract_resources", {"pdf_url": "fixture://pilbara-lithium"}, "fallback" if resources.fallback_used else "success", start, resources.fallback_used))
    warnings.extend(resources.warnings)

    start = perf_counter()
    price_trend = get_trend(topic.commodity, days=30)
    traces.append(_trace("lme-price-mcp.get_trend", {"commodity": topic.commodity, "days": 30}, "fallback" if price_trend.fallback_used else "success", start, price_trend.fallback_used))
    warnings.extend(price_trend.warnings)

    citations = [
        *[make_citation(item.title, item.url, "news") for item in news_result.items],
        make_citation(resources.report_title, resources.source_url, "pdf"),
        make_citation(f"{topic.commodity} price fixture", "data/fixtures/prices.json", "price"),
    ]
    fallback_used = any(trace.fallback_used for trace in traces)
    evidence = EvidencePack(
        topic=topic,
        news=news_result.items,
        articles=articles,
        resources=resources.resources,
        prices=price_trend.points,
        price_trend=price_trend,
        citations=citations,
        tool_trace=traces,
        fallback_used=fallback_used,
        warnings=warnings,
    )

    provider = _select_llm(llm_provider or settings.llm_provider)
    try:
        markdown = provider.generate_report(evidence)
    except Exception as exc:
        warnings.append(f"Ollama failed; mock provider used: {exc}")
        markdown = MockLLMProvider().generate_report(evidence)

    if "Sources" not in markdown or "风险提示" not in markdown or "数据质量说明" not in markdown:
        warnings.append("Generated report missed required sections; mock provider normalized the output.")
        markdown = MockLLMProvider().generate_report(evidence)

    return ReportResponse(
        markdown=markdown,
        citations=citations,
        tool_trace=traces,
        fallback_used=fallback_used,
        warnings=warnings,
    )
```

Create `apps/agent-api/app/main.py`:

```python
from fastapi import FastAPI

from app.orchestrator import generate_report
from mining_agent_shared.models import ReportRequest, ReportResponse

app = FastAPI(title="Mining Rights Daily Agent")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/reports", response_model=ReportResponse)
def create_report(request: ReportRequest) -> ReportResponse:
    return generate_report(request.query, days=request.days)
```

- [ ] **Step 5: Run API tests**

Run:

```bash
python -m pytest apps/agent-api/tests/test_orchestrator.py -v
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Run API manually**

Run:

```bash
python -m uvicorn app.main:app --app-dir apps/agent-api --port 8000
```

In another terminal:

```bash
curl -X POST http://localhost:8000/reports -H "Content-Type: application/json" -d "{\"query\":\"给我生成一份关于 Pilbara 锂矿的今日简报\"}"
```

Expected:

```text
Response contains markdown, citations, tool_trace, fallback_used.
```

- [ ] **Step 7: Commit**

```bash
git add apps/agent-api
git commit -m "feat: add agent API orchestration"
```

---

## Task 7: TypeScript Agent CLI

**Files:**
- Create: `apps/agent-cli/package.json`
- Create: `apps/agent-cli/tsconfig.json`
- Create: `apps/agent-cli/src/index.ts`

- [ ] **Step 1: Create CLI package**

Create `apps/agent-cli/package.json`:

```json
{
  "name": "agent-cli",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "tsc",
    "start": "tsx src/index.ts"
  },
  "dependencies": {
    "tsx": "^4.20.0"
  },
  "devDependencies": {
    "typescript": "^5.8.0"
  }
}
```

Create `apps/agent-cli/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "outDir": "dist",
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

Create `apps/agent-cli/src/index.ts`:

```typescript
const [, , command, ...args] = process.argv;

async function runReport(query: string) {
  const response = await fetch("http://localhost:8000/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, days: 7 }),
  });

  if (!response.ok) {
    throw new Error(`Agent API failed: ${response.status} ${await response.text()}`);
  }

  const payload = await response.json();
  console.log(payload.markdown);
  console.log("\nTool Trace:");
  for (const trace of payload.tool_trace) {
    console.log(`- ${trace.tool}: ${trace.status}, ${trace.duration_ms}ms, fallback=${trace.fallback_used}`);
  }
  console.log("\nSources:");
  for (const citation of payload.citations) {
    console.log(`- ${citation.label}: ${citation.url}`);
  }
}

if (command !== "report") {
  console.error('Usage: pnpm cli report "给我生成一份关于 Pilbara 锂矿的今日简报"');
  process.exit(1);
}

const query = args.join(" ").trim();
if (!query) {
  console.error("Missing report query.");
  process.exit(1);
}

runReport(query).catch((error) => {
  console.error(error);
  process.exit(1);
});
```

- [ ] **Step 2: Build CLI**

Run:

```bash
pnpm install
pnpm --filter agent-cli build
```

Expected:

```text
No TypeScript errors.
```

- [ ] **Step 3: Commit**

```bash
git add apps/agent-cli package.json pnpm-workspace.yaml
git commit -m "feat: add TypeScript agent CLI"
```

---

## Task 8: TypeScript Web Dashboard

**Files:**
- Create: `apps/web-dashboard/package.json`
- Create: `apps/web-dashboard/index.html`
- Create: `apps/web-dashboard/tsconfig.json`
- Create: `apps/web-dashboard/vite.config.ts`
- Create: `apps/web-dashboard/src/main.tsx`
- Create: `apps/web-dashboard/src/App.tsx`
- Create: `apps/web-dashboard/src/api.ts`
- Create: `apps/web-dashboard/src/styles.css`

- [ ] **Step 1: Create Vite React package**

Create `apps/web-dashboard/package.json`:

```json
{
  "name": "web-dashboard",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "tsc && vite build",
    "dev": "vite --host 0.0.0.0"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.6.0",
    "vite": "^7.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "typescript": "^5.8.0"
  }
}
```

Create `apps/web-dashboard/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Mining Rights Daily Agent</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `apps/web-dashboard/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

Create `apps/web-dashboard/vite.config.ts`:

```typescript
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
```

- [ ] **Step 2: Create API client and UI**

Create `apps/web-dashboard/src/api.ts`:

```typescript
export type ReportResponse = {
  markdown: string;
  citations: Array<{ label: string; url: string; source_type: string }>;
  tool_trace: Array<{ tool: string; status: string; duration_ms: number; fallback_used: boolean }>;
  fallback_used: boolean;
  warnings: string[];
};

export async function createReport(query: string): Promise<ReportResponse> {
  const response = await fetch("http://localhost:8000/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, days: 7 }),
  });
  if (!response.ok) {
    throw new Error(`Agent API failed: ${response.status}`);
  }
  return response.json();
}
```

Create `apps/web-dashboard/src/main.tsx`:

```typescript
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

Create `apps/web-dashboard/src/App.tsx`:

```typescript
import { useState } from "react";
import { createReport, type ReportResponse } from "./api";

export default function App() {
  const [query, setQuery] = useState("给我生成一份关于 Pilbara 锂矿的今日简报");
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onGenerate() {
    setLoading(true);
    setError(null);
    try {
      setReport(await createReport(query));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="sidebar">
        <h1>Mining Rights Daily Agent</h1>
        <label htmlFor="query">Brief topic</label>
        <textarea id="query" value={query} onChange={(event) => setQuery(event.target.value)} />
        <button onClick={onGenerate} disabled={loading}>
          {loading ? "Generating..." : "Generate Report"}
        </button>
        {error && <p className="error">{error}</p>}
        {report?.fallback_used && <p className="warning">Fallback data used for reproducible demo.</p>}
      </section>

      <section className="content">
        <article className="report">
          <h2>Markdown Report</h2>
          <pre>{report?.markdown ?? "No report generated yet."}</pre>
        </article>
        <article>
          <h2>Tool Trace</h2>
          <ul>
            {report?.tool_trace.map((trace) => (
              <li key={`${trace.tool}-${trace.duration_ms}`}>
                {trace.tool}: {trace.status}, {trace.duration_ms}ms, fallback={String(trace.fallback_used)}
              </li>
            ))}
          </ul>
        </article>
        <article>
          <h2>Sources</h2>
          <ul>
            {report?.citations.map((citation) => (
              <li key={citation.url}>
                <a href={citation.url}>{citation.label}</a> <span>{citation.source_type}</span>
              </li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
```

Create `apps/web-dashboard/src/styles.css`:

```css
:root {
  color: #17201c;
  background: #f6f7f5;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

body {
  margin: 0;
}

.shell {
  display: grid;
  grid-template-columns: minmax(280px, 360px) 1fr;
  min-height: 100vh;
}

.sidebar {
  background: #ffffff;
  border-right: 1px solid #d9ded8;
  padding: 24px;
}

.content {
  display: grid;
  gap: 16px;
  padding: 24px;
}

textarea {
  box-sizing: border-box;
  width: 100%;
  min-height: 140px;
  resize: vertical;
}

button {
  margin-top: 12px;
  width: 100%;
  padding: 10px 12px;
}

article {
  background: #ffffff;
  border: 1px solid #d9ded8;
  border-radius: 8px;
  padding: 16px;
}

pre {
  white-space: pre-wrap;
  word-break: break-word;
}

.warning {
  color: #875a00;
}

.error {
  color: #a12727;
}

@media (max-width: 800px) {
  .shell {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 3: Build Web**

Run:

```bash
pnpm --filter web-dashboard build
```

Expected:

```text
vite build completes without errors.
```

- [ ] **Step 4: Commit**

```bash
git add apps/web-dashboard
git commit -m "feat: add web dashboard"
```

---

## Task 9: MCP Config, Docker, Docs, and Smoke Eval

**Files:**
- Create: `mcp-config.json`
- Create: `docker-compose.yml`
- Create: `apps/agent-api/Dockerfile`
- Create: `apps/web-dashboard/Dockerfile`
- Create: `eval/sample_prompts.json`
- Create: `eval/run_smoke_eval.py`
- Modify: `README.md`
- Modify: `RUN.md`
- Modify: `DATA_NOTES.md`

- [ ] **Step 1: Add MCP config**

Create `mcp-config.json`:

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

- [ ] **Step 2: Add Docker files**

Create `apps/agent-api/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY mcp_servers ./mcp_servers
COPY apps/agent-api ./apps/agent-api
COPY data ./data
RUN pip install --no-cache-dir -e ".[dev]"
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "apps/agent-api", "--host", "0.0.0.0", "--port", "8000"]
```

Create `apps/web-dashboard/Dockerfile`:

```dockerfile
FROM node:24-alpine

WORKDIR /app
COPY package.json pnpm-workspace.yaml ./
COPY apps/web-dashboard ./apps/web-dashboard
RUN corepack enable && pnpm install --filter web-dashboard --prod=false
EXPOSE 5173
CMD ["pnpm", "--filter", "web-dashboard", "dev"]
```

Create `docker-compose.yml`:

```yaml
services:
  agent-api:
    build:
      context: .
      dockerfile: apps/agent-api/Dockerfile
    env_file:
      - .env
    ports:
      - "8000:8000"

  web-dashboard:
    build:
      context: .
      dockerfile: apps/web-dashboard/Dockerfile
    depends_on:
      - agent-api
    ports:
      - "5173:5173"
```

- [ ] **Step 3: Add smoke eval**

Create `eval/sample_prompts.json`:

```json
[
  "给我生成一份关于 Pilbara 锂矿的今日简报",
  "生成一份关于 copper mining 的矿权日报"
]
```

Create `eval/run_smoke_eval.py`:

```python
from app.orchestrator import generate_report

REQUIRED_SECTIONS = ["Executive Summary", "风险提示", "数据质量说明", "Sources"]


def test_smoke_report_sections():
    response = generate_report("给我生成一份关于 Pilbara 锂矿的今日简报", days=7, llm_provider="mock")
    for section in REQUIRED_SECTIONS:
        assert section in response.markdown
    assert response.citations
    assert response.tool_trace
```

- [ ] **Step 4: Expand docs**

Update `README.md`, `RUN.md`, and `DATA_NOTES.md` so they include:

```markdown
## Verification

```bash
python -m pytest
pnpm --recursive build
docker compose config
```

## MCP Servers

The MCP servers are defined in `mcp-config.json`. They can be connected to Claude Desktop or Cursor using stdio commands from the repository root.
```

- [ ] **Step 5: Verify and commit**

Run:

```bash
python -m pytest
pnpm --recursive build
docker compose config
```

Expected:

```text
All Python tests pass.
Both TypeScript packages build.
Docker Compose configuration is valid.
```

Commit:

```bash
git add mcp-config.json docker-compose.yml apps/agent-api/Dockerfile apps/web-dashboard/Dockerfile eval README.md RUN.md DATA_NOTES.md
git commit -m "chore: add deployment docs and smoke eval"
```

---

## Task 10: Final Verification and GitHub Delivery

**Files:**
- Modify: `README.md`
- Create: `docs/interview-notes.md`

- [ ] **Step 1: Add interview notes**

Create `docs/interview-notes.md`:

```markdown
# Interview Notes

## Project Summary

This project implements an evidence-first MCP Agent for mining rights daily briefs. It separates tool execution from report generation: three MCP servers collect structured evidence, then the Agent API builds an evidence pack and asks Ollama Gemma to generate a cited Markdown brief.

## Why Deterministic Workflow

Local Gemma is useful for summarization, but not ideal for unrestricted tool planning. The workflow keeps tool order in code so the system is testable, auditable, and stable within a 24-hour interview task.

## Risk Controls

- Evidence pack is the only input to the LLM.
- Fallback data is disclosed.
- Missing PDF evidence can abstain.
- Tool trace records status, duration, and fallback flags.
```

- [ ] **Step 2: Run final verification**

Run:

```bash
python -m pytest
pnpm --recursive build
docker compose config
git status --short
```

Expected:

```text
Python tests pass.
TypeScript builds pass.
Docker Compose config passes.
Only intentional doc changes are uncommitted before final commit.
```

- [ ] **Step 3: Commit final docs**

```bash
git add README.md docs/interview-notes.md
git commit -m "docs: add interview delivery notes"
```

- [ ] **Step 4: Create GitHub repository and push**

Run this command after confirming GitHub CLI is authenticated:

```bash
git branch -M main
gh repo create mining-rights-daily-agent --private --source . --remote origin --push
```

Expected:

```text
Repository is visible on GitHub and contains source code, README, RUN.md, DATA_NOTES.md, mcp-config.json, and tests.
```

---

## Self-Review Checklist

- Spec coverage: The plan covers three MCP servers, Agent API, Ollama/mock LLM, TS CLI, Web Dashboard, Docker, docs, eval, and GitHub delivery.
- File consistency: Python imports use `mcp_servers.*`, `mining_agent_shared.*`, and `app.*` consistently with `pyproject.toml` pytest `pythonpath`.
- Protocol consistency: MCP wrappers use `FastMCP` and `mcp.run()` for direct stdio execution.
- Runtime consistency: CLI and Web call only `POST /reports` and do not duplicate Agent logic.
- Data quality consistency: All three tool paths disclose fixture/fallback use.
- Verification coverage: The final verification command includes Python tests, TypeScript builds, and Docker Compose config validation.
