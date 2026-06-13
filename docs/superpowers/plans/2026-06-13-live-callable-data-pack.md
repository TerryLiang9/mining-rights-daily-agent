# Live Callable Data Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure the local project to call non-fixture news, PDF, and price data by default.

**Architecture:** Reuse the existing Provider boundaries. Add a local `data/live` price snapshot and source manifest, point `.env` at public RSS/PDF sources plus the CSV, and add tests proving the configured provider path is callable with `fallback_used=false`.

**Tech Stack:** Python 3.11, pytest, existing MCP servers, CSV/JSON data files, pydantic settings, pnpm/Vite for verification.

---

### Task 1: Add Live Data Pack Files

**Files:**
- Create: `data/live/prices.csv`
- Create: `data/live/sources.json`

- [ ] **Step 1: Research public source URLs**

Use web/search and direct HTTP checks to choose:

```text
news_rss: public mining RSS feed URLs
mineral_pdf: public NI 43-101 or technical report PDF URL
prices: public market snapshot pages or downloadable CSV/JSON source pages
```

Expected: Every data row in `prices.csv` can be explained in `sources.json`.

- [ ] **Step 2: Create `data/live/prices.csv`**

Use the existing supported schema:

```csv
commodity,date,price,currency,unit
lithium,2026-06-13,12850,USD,t
copper,2026-06-13,9580,USD,t
nickel,2026-06-13,18350,USD,t
zinc,2026-06-13,2890,USD,t
```

Replace the example numbers with researched public values or documented market proxies. Include at least five dates per commodity where public data supports trend calls.

- [ ] **Step 3: Create `data/live/sources.json`**

Use this exact structure:

```json
{
  "retrieved_at": "2026-06-13",
  "news_feeds": [
    {
      "name": "Mining.com",
      "url": "https://www.mining.com/feed/",
      "notes": "Public RSS feed used by mining-news-mcp."
    }
  ],
  "pdf_reports": [
    {
      "name": "Public technical report",
      "url": "https://example.com/report.pdf",
      "notes": "Configured as MINERAL_PDF_DEFAULT_URL."
    }
  ],
  "price_sources": [
    {
      "commodity": "copper",
      "source_url": "https://example.com/source",
      "source_type": "public market snapshot",
      "notes": "Values are a local snapshot, not licensed real-time LME data."
    }
  ]
}
```

- [ ] **Step 4: Verify price provider loads the CSV**

Run:

```bash
python -c "from mcp_servers.lme_price.providers import ConfiguredPriceProvider; d=ConfiguredPriceProvider('data/live/prices.csv').load(); print(d.source, sorted(d.data.keys()))"
```

Expected: prints a path ending in `data\live\prices.csv` and commodities including `lithium`, `copper`, `nickel`, `zinc`.

- [ ] **Step 5: Commit**

```bash
git add data/live/prices.csv data/live/sources.json
git commit -m "data: add live callable data pack"
```

### Task 2: Configure Local Runtime

**Files:**
- Modify: `.env`
- Modify: `.env.example`

- [ ] **Step 1: Update `.env`**

Set:

```env
USE_FIXTURES_ON_FAILURE=false
MINING_NEWS_RSS_FEEDS=https://www.mining.com/feed/
MINERAL_PDF_DEFAULT_URL=<chosen public PDF URL or local path>
PRICE_DATA_FILE=data/live/prices.csv
PRICE_DATA_URL=
```

- [ ] **Step 2: Update `.env.example`**

Keep safe defaults, but document live examples:

```env
MINING_NEWS_RSS_FEEDS=
MINERAL_PDF_DEFAULT_URL=
PRICE_DATA_FILE=data/live/prices.csv
PRICE_DATA_URL=
```

- [ ] **Step 3: Verify settings**

Run:

```bash
python -c "from mining_agent_shared.config import get_settings; s=get_settings(); print(s.use_fixtures_on_failure, s.price_data_file, s.mining_news_rss_feeds, s.mineral_pdf_default_url)"
```

Expected: fallback is `False`, `price_data_file` is `data/live/prices.csv`, and feed/PDF fields are non-empty in local `.env`.

- [ ] **Step 4: Commit**

```bash
git add .env.example
git commit -m "docs: document live data provider defaults"
```

Do not commit `.env` if it is ignored by git.

### Task 3: Add Regression Tests

**Files:**
- Modify: `mcp_servers/lme_price/tests/test_tools.py`
- Modify: `apps/agent-api/tests/test_orchestrator.py`

- [ ] **Step 1: Add price CSV test**

Add:

```python
def test_live_price_csv_fixture_file_is_callable(monkeypatch):
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(
            use_fixtures_on_failure=False,
            price_data_file="data/live/prices.csv",
            price_data_url="",
        ),
    )

    price = get_price("copper")
    trend = get_trend("copper", days=30)

    assert price.price is not None
    assert price.source.endswith("data\\live\\prices.csv") or price.source.endswith("data/live/prices.csv")
    assert price.fallback_used is False
    assert trend.points
    assert trend.fallback_used is False
```

- [ ] **Step 2: Add Agent citation test**

Add:

```python
def test_generate_report_can_cite_live_price_csv(monkeypatch):
    monkeypatch.setenv("USE_FIXTURES_ON_FAILURE", "false")
    monkeypatch.setenv("PRICE_DATA_FILE", "data/live/prices.csv")
    response = generate_report(
        "给我生成一份关于 copper mining 的矿权日报",
        days=7,
        llm_provider="mock",
        tool_adapter=RecordingToolAdapter(),
    )
    price_citations = [citation for citation in response.citations if citation.source_type == "price"]
    assert price_citations
    assert "data/live/prices.csv" in price_citations[0].url.replace("\\", "/")
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
python -m pytest mcp_servers/lme_price/tests/test_tools.py apps/agent-api/tests/test_orchestrator.py -v
```

Expected: all focused tests pass.

- [ ] **Step 4: Commit**

```bash
git add mcp_servers/lme_price/tests/test_tools.py apps/agent-api/tests/test_orchestrator.py
git commit -m "test: cover live callable data pack"
```

### Task 4: Runtime Verification

**Files:**
- No code files unless verification exposes a defect.

- [ ] **Step 1: Run full verification**

Run:

```bash
python -m pytest
pnpm --recursive test
pnpm --recursive build
docker compose config
git diff --check
```

Expected: all commands pass.

- [ ] **Step 2: Restart local services**

Stop the existing API/Web processes and start:

```bash
python -m uvicorn app.main:app --app-dir apps/agent-api --reload --host 127.0.0.1 --port 8000
pnpm --filter web-dashboard dev -- --host 0.0.0.0
```

- [ ] **Step 3: Call the API**

Run:

```bash
curl -X POST http://127.0.0.1:8000/reports -H "Content-Type: application/json" -d "{\"query\":\"给我生成一份关于 copper mining 的矿权日报\",\"days\":7}"
```

Expected: `fallback_used` is false for price data and the price citation points to `data/live/prices.csv`. News/PDF behavior depends on public source reachability and parser success, but must not use fixture data with fallback disabled.

- [ ] **Step 4: Final status**

Report:

```text
Local URL: http://127.0.0.1:5173
API URL: http://127.0.0.1:8000
Configured news RSS:
Configured PDF:
Configured price CSV:
Verification commands:
Remaining caveats:
```

## Self-Review

- Spec coverage: the plan covers live news RSS, configured PDF, local live price CSV, source metadata, `.env`, `.env.example`, tests, verification, and restart.
- Placeholder scan: the only angle-bracket value is intentionally resolved in Task 1 before `.env` is modified; no implementation step can be executed without choosing the public PDF URL first.
- Type consistency: test code uses existing `Settings`, `get_price`, `get_trend`, `generate_report`, and `RecordingToolAdapter` names.
