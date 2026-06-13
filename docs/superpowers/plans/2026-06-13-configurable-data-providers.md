# Configurable Data Providers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the three MCP servers so real/configured data providers are first-class and fixture data is only an explicit or disclosed fallback.

**Architecture:** Each MCP domain gets a focused `providers.py` that owns external I/O and fixture loading. Existing `tools.py` files keep the public MCP tool contracts, validate inputs, call providers in priority order, and normalize responses into shared Pydantic models. The Agent API, CLI, and Web Dashboard pass user-provided PDF sources through the stack instead of silently binding fixed sample data.

**Tech Stack:** Python 3.11, FastMCP, Pydantic v2, httpx, feedparser, beautifulsoup4, pypdf, pytest, TypeScript, React, Vite, pnpm.

---

## Execution Notes

The current worktree may already contain partial changes in MCP tools, CLI, Web, docs, and tests. Execution must read the current diff first, preserve any user or earlier agent changes, and evolve them toward this plan. Do not use destructive reset or checkout commands.

Commit only files intentionally changed for each task. If a file already has related uncommitted work, review the whole file and include the coherent final version in that task commit.

## File Responsibility Map

- `packages/shared/mining_agent_shared/config.py`: environment-backed settings for provider behavior.
- `.env.example`: documents configurable source environment variables.
- `mcp_servers/mining_news/providers.py`: RSS and fixture news providers.
- `mcp_servers/mining_news/tools.py`: `search` and `fetch_article` public tool orchestration.
- `mcp_servers/mining_news/tests/test_tools.py`: news provider and fallback behavior tests.
- `mcp_servers/mineral_pdf/providers.py`: PDF resource and fixture resource providers.
- `mcp_servers/mineral_pdf/parser.py`: page-text resource parsing only.
- `mcp_servers/mineral_pdf/tools.py`: `extract_resources` public tool orchestration.
- `mcp_servers/mineral_pdf/server.py`: FastMCP wrapper with optional `pdf_url`.
- `mcp_servers/mineral_pdf/tests/test_tools.py`: PDF provider, abstain, and fixture behavior tests.
- `mcp_servers/lme_price/providers.py`: configured file/URL and fixture price providers.
- `mcp_servers/lme_price/tools.py`: `get_price` and `get_trend` public tool orchestration.
- `mcp_servers/lme_price/server.py`: FastMCP wrappers returning dict JSON payloads.
- `mcp_servers/lme_price/tests/test_tools.py`: configured price, fallback, and no-fallback tests.
- `apps/agent-api/app/orchestrator.py`: passes optional PDF source and cites actual provider source.
- `apps/agent-api/app/main.py`: passes request `pdf_url` into orchestration.
- `packages/shared/mining_agent_shared/models.py`: keeps `ReportRequest.pdf_url`.
- `apps/agent-api/tests/test_orchestrator.py`: Agent source propagation and no hardcoded PDF tests.
- `apps/agent-cli/src/*`: CLI `--pdf` request wiring and output tests.
- `apps/web-dashboard/src/*`: PDF input request wiring and API tests.
- `README.md`, `RUN.md`, `DATA_NOTES.md`: provider configuration and fallback semantics.

---

### Task 1: Shared Provider Configuration

**Files:**
- Modify: `packages/shared/mining_agent_shared/config.py`
- Modify: `.env.example`
- Test: `packages/shared/tests/test_config.py`

- [ ] **Step 1: Write the failing config test**

Create `packages/shared/tests/test_config.py`:

```python
from mining_agent_shared.config import Settings


def test_settings_include_provider_source_configuration():
    settings = Settings(
        mining_news_rss_feeds="https://example.com/mining.xml, https://example.com/metals.xml",
        mineral_pdf_default_url="https://example.com/report.pdf",
        price_data_file="data/prices/live.json",
        price_data_url="https://example.com/prices.json",
        use_fixtures_on_failure=False,
    )

    assert settings.mining_news_rss_feeds == "https://example.com/mining.xml, https://example.com/metals.xml"
    assert settings.mineral_pdf_default_url == "https://example.com/report.pdf"
    assert settings.price_data_file == "data/prices/live.json"
    assert settings.price_data_url == "https://example.com/prices.json"
    assert settings.use_fixtures_on_failure is False
```

- [ ] **Step 2: Verify red**

Run:

```bash
python -m pytest packages/shared/tests/test_config.py -v
```

Expected before implementation:

```text
FAILED ... extra inputs are not permitted
```

- [ ] **Step 3: Implement settings fields**

Update `packages/shared/mining_agent_shared/config.py`:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_api_host: str = "0.0.0.0"
    agent_api_port: int = 8000
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma"
    use_fixtures_on_failure: bool = True
    mining_news_rss_feeds: str = ""
    mineral_pdf_default_url: str = ""
    price_data_file: str = ""
    price_data_url: str = ""
```

Update `.env.example` so it contains exactly these provider variables:

```env
MINING_NEWS_RSS_FEEDS=
MINERAL_PDF_DEFAULT_URL=
PRICE_DATA_FILE=
PRICE_DATA_URL=
USE_FIXTURES_ON_FAILURE=true
```

- [ ] **Step 4: Verify green**

Run:

```bash
python -m pytest packages/shared/tests/test_config.py -v
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```bash
git add packages/shared/mining_agent_shared/config.py packages/shared/tests/test_config.py .env.example
git commit -m "feat: add configurable provider settings"
```

---

### Task 2: Mining News Providers

**Files:**
- Create: `mcp_servers/mining_news/providers.py`
- Modify: `mcp_servers/mining_news/tools.py`
- Test: `mcp_servers/mining_news/tests/test_tools.py`

- [ ] **Step 1: Write failing provider tests**

Append to `mcp_servers/mining_news/tests/test_tools.py`:

```python
from types import SimpleNamespace

from mining_agent_shared.config import Settings
from mcp_servers.mining_news import tools
from mcp_servers.mining_news.tools import search


def test_search_uses_configured_rss_provider_before_fixture(monkeypatch):
    class FakeResponse:
        text = """
        <rss><channel>
          <item>
            <title>Pilbara lithium project advances</title>
            <link>https://news.example.com/pilbara-live</link>
            <description>Live RSS item about Pilbara lithium.</description>
            <pubDate>Sat, 13 Jun 2026 00:00:00 GMT</pubDate>
          </item>
        </channel></rss>
        """

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(mining_news_rss_feeds="https://feeds.example.com/mining.xml"),
    )
    monkeypatch.setattr(tools, "_http_get", lambda url: FakeResponse(), raising=False)

    result = search("Pilbara lithium", days=7, limit=3)

    assert result.fallback_used is False
    assert [item.url for item in result.items] == ["https://news.example.com/pilbara-live"]
    assert result.items[0].source == "feeds.example.com"


def test_search_does_not_use_fixture_when_fallback_disabled(monkeypatch):
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(
            mining_news_rss_feeds="https://feeds.example.com/broken.xml",
            use_fixtures_on_failure=False,
        ),
    )
    monkeypatch.setattr(
        tools,
        "_http_get",
        lambda url: (_ for _ in ()).throw(RuntimeError("rss unavailable")),
        raising=False,
    )

    result = search("Pilbara lithium", days=7, limit=3)

    assert result.items == []
    assert result.fallback_used is False
    assert any("rss unavailable" in warning.lower() for warning in result.warnings)
```

- [ ] **Step 2: Verify red**

Run:

```bash
python -m pytest mcp_servers/mining_news/tests/test_tools.py -v
```

Expected before implementation:

```text
FAILED ... attribute get_settings does not exist
```

or:

```text
FAILED ... fallback_used is True
```

- [ ] **Step 3: Create `providers.py`**

Create `mcp_servers/mining_news/providers.py`:

```python
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import feedparser
from bs4 import BeautifulSoup

from mining_agent_shared.models import Article, NewsItem, NewsSearchResult

ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT_DIR / "data" / "fixtures" / "news.json"
GENERIC_QUERY_TERMS = {"mining", "mine", "minerals", "mineral", "global", "news"}


def retrieved_at() -> str:
    return datetime.now(UTC).isoformat()


def scoring_terms(query: str) -> list[str]:
    terms = [term.lower() for term in query.split() if term.strip()]
    meaningful = [term for term in terms if term not in GENERIC_QUERY_TERMS]
    return meaningful or terms


def parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def filter_recent(items: list[NewsItem], days: int) -> list[NewsItem]:
    dated_items = [(item, parse_iso_date(item.published_at)) for item in items]
    valid_dates = [published for _, published in dated_items if published is not None]
    if not valid_dates:
        return items
    cutoff = max(valid_dates) - timedelta(days=days - 1)
    return [item for item, published in dated_items if published is None or published >= cutoff]


def score_items(items: list[NewsItem], terms: list[str]) -> list[NewsItem]:
    scored: list[NewsItem] = []
    for item in items:
        haystack = f"{item.title} {item.summary} {item.source}".lower()
        matched = sum(1 for term in terms if term in haystack)
        if terms and matched == 0:
            continue
        scored.append(item.model_copy(update={"score": round(min(1.0, max(item.score, 0.45 + matched * 0.2)), 3)}))
    return sorted(scored, key=lambda item: (item.score, item.published_at), reverse=True)


class RssNewsProvider:
    def __init__(self, feed_urls: list[str], http_get) -> None:
        self.feed_urls = feed_urls
        self.http_get = http_get

    def search(self, query: str, days: int, limit: int) -> NewsSearchResult:
        warnings: list[str] = []
        items: list[NewsItem] = []
        for feed_url in self.feed_urls:
            try:
                response = self.http_get(feed_url)
                response.raise_for_status()
                feed = feedparser.parse(response.text)
            except Exception as exc:
                warnings.append(f"RSS feed failed for {feed_url}: {exc}")
                continue
            source = urlparse(feed_url).netloc or "rss"
            for entry in feed.entries:
                parsed_time = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
                published_at = (
                    datetime(*parsed_time[:6], tzinfo=UTC).date().isoformat()
                    if parsed_time
                    else datetime.now(UTC).date().isoformat()
                )
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                items.append(
                    NewsItem(
                        title=(getattr(entry, "title", "") or "Untitled mining news").strip(),
                        url=(getattr(entry, "link", "") or feed_url).strip(),
                        source=source,
                        published_at=published_at,
                        summary=BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)[:600],
                        score=0.5,
                    )
                )
        return NewsSearchResult(
            items=score_items(filter_recent(items, days), scoring_terms(query))[:limit],
            fallback_used=False,
            retrieved_at=retrieved_at(),
            warnings=warnings,
        )


class FixtureNewsProvider:
    def _items(self) -> list[NewsItem]:
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        return [NewsItem(**item) for item in raw]

    def search(self, query: str, days: int, limit: int, warnings: list[str] | None = None) -> NewsSearchResult:
        return NewsSearchResult(
            items=score_items(filter_recent(self._items(), days), scoring_terms(query))[:limit],
            fallback_used=True,
            retrieved_at=retrieved_at(),
            warnings=[*(warnings or []), "Using fixture mining news for reproducible interview demo."],
        )

    def fetch_article(self, url: str) -> Article | None:
        for item in self._items():
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
        return None
```

- [ ] **Step 4: Refactor `tools.py`**

Update `mcp_servers/mining_news/tools.py` to import settings and providers:

```python
from mining_agent_shared.config import get_settings
from mcp_servers.mining_news.providers import FixtureNewsProvider, RssNewsProvider, retrieved_at
```

Use this provider selection in `search`:

```python
settings = get_settings()
feed_urls = [url.strip() for url in settings.mining_news_rss_feeds.split(",") if url.strip()]
if feed_urls:
    live_result = RssNewsProvider(feed_urls, _http_get).search(normalized_query, days, limit)
    if live_result.items or not settings.use_fixtures_on_failure:
        return live_result
    warnings.extend(live_result.warnings)

return FixtureNewsProvider().search(normalized_query, days, limit, warnings)
```

Use this fixture lookup in `fetch_article`:

```python
fixture_article = FixtureNewsProvider().fetch_article(url)
if fixture_article is not None:
    return fixture_article
```

- [ ] **Step 5: Verify green**

Run:

```bash
python -m pytest mcp_servers/mining_news/tests/test_tools.py -v
```

Expected:

```text
all tests passed
```

- [ ] **Step 6: Commit**

```bash
git add mcp_servers/mining_news/providers.py mcp_servers/mining_news/tools.py mcp_servers/mining_news/tests/test_tools.py
git commit -m "feat: split mining news data providers"
```

---

### Task 3: Mineral PDF Providers

**Files:**
- Create: `mcp_servers/mineral_pdf/providers.py`
- Modify: `mcp_servers/mineral_pdf/tools.py`
- Modify: `mcp_servers/mineral_pdf/server.py`
- Modify: `apps/agent-api/app/orchestrator.py`
- Test: `mcp_servers/mineral_pdf/tests/test_tools.py`
- Test: `apps/agent-api/tests/test_orchestrator.py`

- [ ] **Step 1: Write failing PDF no-source test**

Append to `mcp_servers/mineral_pdf/tests/test_tools.py`:

```python
from mining_agent_shared.config import Settings
from mcp_servers.mineral_pdf import tools


def test_extract_resources_abstains_without_pdf_source(monkeypatch):
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(mineral_pdf_default_url=""),
    )

    result = extract_resources(None, project_name="Pilbara")

    assert result.abstain is True
    assert result.resources == []
    assert result.fallback_used is False
    assert any("pdf" in warning.lower() and "not provided" in warning.lower() for warning in result.warnings)


def test_extract_resources_uses_default_pdf_url_from_settings(monkeypatch, tmp_path):
    pdf_path = tmp_path / "configured-report.pdf"
    pdf_path.write_bytes(
        _minimal_pdf_with_text(["Indicated 42 Mt 1.10% Li2O 0.5 Mt LCE"])
    )
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(mineral_pdf_default_url=str(pdf_path)),
    )

    result = extract_resources(None, project_name="Configured")

    assert result.abstain is False
    assert result.source_url == str(pdf_path)
    assert result.resources[0].category == "Indicated"
```

- [ ] **Step 2: Write failing Agent no-hardcoded-PDF test**

Append to `apps/agent-api/tests/test_orchestrator.py`:

```python
def test_generate_report_does_not_default_to_sample_pdf_when_pdf_url_missing():
    adapter = RecordingToolAdapter()

    generate_report(
        "给我生成一份关于 Pilbara 锂矿的今日简报",
        days=7,
        llm_provider="mock",
        tool_adapter=adapter,
    )

    pdf_arguments = [
        arguments
        for server_name, tool_name, arguments in adapter.arguments
        if (server_name, tool_name) == ("mineral-pdf-mcp", "extract_resources")
    ]

    assert pdf_arguments
    assert pdf_arguments[0].get("pdf_url") in {None, ""}
```

- [ ] **Step 3: Verify red**

Run:

```bash
python -m pytest mcp_servers/mineral_pdf/tests/test_tools.py apps/agent-api/tests/test_orchestrator.py -v
```

Expected before implementation:

```text
FAILED ... source_url == data/fixtures/pilbara-resource-sample.pdf
```

or:

```text
FAILED ... extract_resources expected str
```

- [ ] **Step 4: Create `providers.py`**

Create `mcp_servers/mineral_pdf/providers.py`:

```python
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader

from mining_agent_shared.models import ResourceExtractionResult, ResourceItem
from mcp_servers.mineral_pdf.parser import parse_resource_pages

ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT_DIR / "data" / "fixtures" / "resources.json"
MAX_PDF_BYTES = 30 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 30


class PdfResourceProvider:
    def read_pdf_bytes(self, pdf_url: str) -> bytes:
        parsed = urlparse(pdf_url)
        if parsed.scheme in {"http", "https"}:
            response = httpx.get(pdf_url, timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if content_type and "pdf" not in content_type and "octet-stream" not in content_type:
                raise ValueError(f"URL did not return a PDF content type: {content_type}")
            if len(response.content) > MAX_PDF_BYTES:
                raise ValueError("PDF is larger than the configured maximum size.")
            return response.content
        path = Path(pdf_url)
        if parsed.scheme and not path.is_absolute():
            raise ValueError(f"Unsupported PDF URL scheme: {parsed.scheme}")
        if not path.is_absolute():
            path = ROOT_DIR / path
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"PDF path does not exist: {path}")
        if path.stat().st_size > MAX_PDF_BYTES:
            raise ValueError("PDF is larger than the configured maximum size.")
        return path.read_bytes()

    def extract(self, pdf_url: str, project_name: str | None) -> ResourceExtractionResult:
        reader = PdfReader(BytesIO(self.read_pdf_bytes(pdf_url)))
        pages = [(index, page.extract_text() or "") for index, page in enumerate(reader.pages, start=1)]
        resources = parse_resource_pages(pages)
        if not resources:
            return ResourceExtractionResult(
                project_name=project_name or "unknown",
                report_title="Unavailable NI 43-101 report",
                source_url=pdf_url,
                resources=[],
                abstain=True,
                fallback_used=False,
                warnings=["PDF extraction abstained because no Indicated/Inferred resource lines were found."],
            )
        return ResourceExtractionResult(
            project_name=project_name or "unknown",
            report_title=Path(urlparse(pdf_url).path).name or "Extracted NI 43-101 report",
            source_url=pdf_url,
            resources=resources,
            abstain=False,
            fallback_used=False,
            warnings=[],
        )


class FixtureResourceProvider:
    def extract(self) -> ResourceExtractionResult:
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        return ResourceExtractionResult(
            project_name=raw["project_name"],
            report_title=raw["report_title"],
            source_url=raw["source_url"],
            resources=[ResourceItem(**item) for item in raw["resources"]],
            fallback_used=True,
            warnings=["Using fixture NI 43-101-like resource data for reproducible demo."],
        )
```

- [ ] **Step 5: Refactor PDF `tools.py` and `server.py`**

Update `mcp_servers/mineral_pdf/tools.py`:

```python
from mining_agent_shared.config import get_settings
from mining_agent_shared.models import ResourceExtractionResult
from mcp_servers.mineral_pdf.providers import FixtureResourceProvider, PdfResourceProvider


def extract_resources(pdf_url: str | None = None, project_name: str | None = None) -> ResourceExtractionResult:
    settings = get_settings()
    normalized_pdf_url = pdf_url.strip() if isinstance(pdf_url, str) and pdf_url.strip() else settings.mineral_pdf_default_url.strip()

    if not normalized_pdf_url:
        return ResourceExtractionResult(
            project_name=project_name or "unknown",
            report_title="No NI 43-101 report provided",
            source_url="",
            resources=[],
            abstain=True,
            fallback_used=False,
            warnings=["PDF source was not provided; set pdf_url or MINERAL_PDF_DEFAULT_URL."],
        )

    if normalized_pdf_url.startswith("fixture://") or normalized_pdf_url.endswith("resources.json"):
        return FixtureResourceProvider().extract()

    try:
        return PdfResourceProvider().extract(normalized_pdf_url, project_name)
    except Exception as exc:
        return ResourceExtractionResult(
            project_name=project_name or "unknown",
            report_title="Unreadable NI 43-101 report",
            source_url=normalized_pdf_url,
            resources=[],
            abstain=True,
            fallback_used=False,
            warnings=[f"PDF extraction failed: {exc}"],
        )
```

Update `mcp_servers/mineral_pdf/server.py`:

```python
@mcp.tool()
def extract_resources(pdf_url: str | None = None, project_name: str | None = None) -> dict:
    """Extract Indicated and Inferred resources from a mineral technical report."""
    return extract_resources_tool(pdf_url=pdf_url, project_name=project_name).model_dump()
```

- [ ] **Step 6: Remove Agent hardcoded sample PDF default**

Update `apps/agent-api/app/orchestrator.py` so the PDF call sends the provided URL or `None`:

```python
resource_pdf_url = pdf_url.strip() if pdf_url and pdf_url.strip() else None
resource_arguments = {"pdf_url": resource_pdf_url, "project_name": topic.region}
resources = ResourceExtractionResult(
    **adapter.call_tool("mineral-pdf-mcp", "extract_resources", resource_arguments)
)
```

Delete the `SAMPLE_RESOURCE_PDF` constant if it is unused.

- [ ] **Step 7: Verify green**

Run:

```bash
python -m pytest mcp_servers/mineral_pdf/tests/test_tools.py apps/agent-api/tests/test_orchestrator.py -v
```

Expected:

```text
all tests passed
```

- [ ] **Step 8: Commit**

```bash
git add mcp_servers/mineral_pdf/providers.py mcp_servers/mineral_pdf/tools.py mcp_servers/mineral_pdf/server.py mcp_servers/mineral_pdf/tests/test_tools.py apps/agent-api/app/orchestrator.py apps/agent-api/tests/test_orchestrator.py
git commit -m "feat: split mineral PDF providers"
```

---

### Task 4: LME Price Providers

**Files:**
- Create: `mcp_servers/lme_price/providers.py`
- Modify: `mcp_servers/lme_price/tools.py`
- Modify: `mcp_servers/lme_price/server.py`
- Test: `mcp_servers/lme_price/tests/test_tools.py`

- [ ] **Step 1: Write failing configured JSON and no-fallback tests**

Append to `mcp_servers/lme_price/tests/test_tools.py`:

```python
import json

from mining_agent_shared.config import Settings
from mcp_servers.lme_price import tools


def test_get_price_uses_configured_json_file_before_fixture(monkeypatch, tmp_path):
    price_file = tmp_path / "prices.json"
    price_file.write_text(
        json.dumps(
            {
                "lithium": {
                    "currency": "USD",
                    "unit": "t",
                    "points": [{"date": "2026-06-13", "price": 22222}],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(price_data_file=str(price_file)),
    )

    price = get_price("lithium")

    assert price.price == 22222
    assert price.source == str(price_file)
    assert price.fallback_used is False


def test_get_trend_does_not_fallback_when_disabled(monkeypatch):
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(price_data_file="missing-prices.json", use_fixtures_on_failure=False),
    )

    trend = get_trend("lithium", days=30)

    assert trend.points == []
    assert trend.trend == "insufficient_data"
    assert trend.fallback_used is False
    assert any("missing-prices.json" in warning for warning in trend.warnings)
```

- [ ] **Step 2: Write failing configured CSV test**

Append to `mcp_servers/lme_price/tests/test_tools.py`:

```python
def test_get_trend_uses_configured_csv_file(monkeypatch, tmp_path):
    price_file = tmp_path / "prices.csv"
    price_file.write_text(
        "commodity,date,price,currency,unit\n"
        "lithium,2026-06-01,100,USD,t\n"
        "lithium,2026-06-13,110,USD,t\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(price_data_file=str(price_file)),
    )

    trend = get_trend("lithium", days=30)

    assert [point.price for point in trend.points] == [100, 110]
    assert trend.change_pct == 10.0
    assert trend.source == str(price_file)
    assert trend.fallback_used is False
```

- [ ] **Step 3: Verify red**

Run:

```bash
python -m pytest mcp_servers/lme_price/tests/test_tools.py -v
```

Expected before implementation:

```text
FAILED ... price == 12850
```

or:

```text
FAILED ... fallback_used is True
```

- [ ] **Step 4: Create `providers.py`**

Create `mcp_servers/lme_price/providers.py`:

```python
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import httpx

ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT_DIR / "data" / "fixtures" / "prices.json"
REQUEST_TIMEOUT_SECONDS = 15


class PriceProviderError(RuntimeError):
    pass


def _normalize_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT_DIR / candidate


def _load_json_payload(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise PriceProviderError("Price JSON must be an object keyed by commodity.")
    return payload


def _load_csv_payload(raw: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    reader = csv.DictReader(raw.splitlines())
    for row in reader:
        commodity = (row.get("commodity") or "").strip().lower()
        if not commodity:
            continue
        entry = payload.setdefault(
            commodity,
            {"currency": row.get("currency") or "USD", "unit": row.get("unit") or "t", "points": []},
        )
        entry["points"].append({"date": row["date"], "price": float(row["price"])})
    return payload


class ConfiguredPriceProvider:
    def __init__(self, price_data_file: str = "", price_data_url: str = "") -> None:
        self.price_data_file = price_data_file.strip()
        self.price_data_url = price_data_url.strip()

    def load(self) -> tuple[dict[str, Any], str]:
        if self.price_data_file:
            path = _normalize_path(self.price_data_file)
            raw = path.read_text(encoding="utf-8")
            if path.suffix.lower() == ".csv":
                return _load_csv_payload(raw), str(path if Path(self.price_data_file).is_absolute() else self.price_data_file)
            return _load_json_payload(raw), str(path if Path(self.price_data_file).is_absolute() else self.price_data_file)
        if self.price_data_url:
            response = httpx.get(self.price_data_url, timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=True)
            response.raise_for_status()
            return _load_json_payload(response.text), self.price_data_url
        raise PriceProviderError("No configured price source; set PRICE_DATA_FILE or PRICE_DATA_URL.")


class FixturePriceProvider:
    def load(self) -> tuple[dict[str, Any], str]:
        return _load_json_payload(FIXTURE_PATH.read_text(encoding="utf-8")), "data/fixtures/prices.json"
```

- [ ] **Step 5: Refactor `tools.py`**

Update `mcp_servers/lme_price/tools.py` to load provider data:

```python
from mining_agent_shared.config import get_settings
from mcp_servers.lme_price.providers import ConfiguredPriceProvider, FixturePriceProvider


def _load_price_data() -> tuple[dict, str, bool, list[str]]:
    settings = get_settings()
    warnings: list[str] = []
    try:
        data, source = ConfiguredPriceProvider(settings.price_data_file, settings.price_data_url).load()
        return data, source, False, warnings
    except Exception as exc:
        warnings.append(f"Configured price provider failed: {exc}")
        if not settings.use_fixtures_on_failure:
            return {}, "configured", False, warnings
        fixture_data, fixture_source = FixturePriceProvider().load()
        return fixture_data, fixture_source, True, [*warnings, "Using fixture price data for reproducible demo."]
```

Update `get_price` and `get_trend` to use:

```python
data, source, fallback_used, provider_warnings = _load_price_data()
```

Then set `source=source`, `fallback_used=fallback_used`, and `warnings=provider_warnings` in returned `PriceQuote` and `PriceTrend`.

- [ ] **Step 6: Verify green**

Run:

```bash
python -m pytest mcp_servers/lme_price/tests/test_tools.py -v
```

Expected:

```text
all tests passed
```

- [ ] **Step 7: Commit**

```bash
git add mcp_servers/lme_price/providers.py mcp_servers/lme_price/tools.py mcp_servers/lme_price/server.py mcp_servers/lme_price/tests/test_tools.py
git commit -m "feat: split price data providers"
```

---

### Task 5: Agent Evidence Source Propagation

**Files:**
- Modify: `apps/agent-api/app/orchestrator.py`
- Modify: `apps/agent-api/tests/test_orchestrator.py`

- [ ] **Step 1: Write failing price citation source test**

Append to `apps/agent-api/tests/test_orchestrator.py`:

```python
class ConfiguredPriceRecordingToolAdapter(RecordingToolAdapter):
    def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> dict:
        payload = super().call_tool(server_name, tool_name, arguments)
        if (server_name, tool_name) in {
            ("lme-price-mcp", "get_price"),
            ("lme-price-mcp", "get_trend"),
        }:
            payload["source"] = "data/live/prices.json"
            payload["fallback_used"] = False
            payload["warnings"] = []
        return payload


def test_generate_report_cites_actual_price_source():
    adapter = ConfiguredPriceRecordingToolAdapter()

    response = generate_report(
        "给我生成一份关于 Pilbara 锂矿的今日简报",
        days=7,
        pdf_url="fixture://pilbara-lithium",
        llm_provider="mock",
        tool_adapter=adapter,
    )

    price_citations = [citation for citation in response.citations if citation.source_type == "price"]
    assert price_citations
    assert price_citations[0].url == "data/live/prices.json"
```

- [ ] **Step 2: Verify red**

Run:

```bash
python -m pytest apps/agent-api/tests/test_orchestrator.py -v
```

Expected before implementation:

```text
FAILED ... data/fixtures/prices.json
```

- [ ] **Step 3: Implement citation source propagation**

Update citation creation in `apps/agent-api/app/orchestrator.py`:

```python
price_source_url = price_quote.source or price_trend.source or "unknown"
citations = [
    *[make_citation(item.title, item.url, "news") for item in news_result.items],
    make_citation(resources.report_title, resources.source_url or "no-pdf-source", "pdf"),
    make_citation(f"{topic.commodity} price data", price_source_url, "price"),
]
```

- [ ] **Step 4: Verify green**

Run:

```bash
python -m pytest apps/agent-api/tests/test_orchestrator.py -v
```

Expected:

```text
all tests passed
```

- [ ] **Step 5: Commit**

```bash
git add apps/agent-api/app/orchestrator.py apps/agent-api/tests/test_orchestrator.py
git commit -m "fix: cite actual price provider source"
```

---

### Task 6: CLI, Web, and Documentation

**Files:**
- Modify: `apps/agent-cli/src/agent-api.ts`
- Modify: `apps/agent-cli/src/format.ts`
- Modify: `apps/agent-cli/src/index.ts`
- Modify: `apps/agent-cli/src/agent-api.test.ts`
- Modify: `apps/agent-cli/src/format.test.ts`
- Modify: `apps/web-dashboard/src/App.tsx`
- Modify: `apps/web-dashboard/src/api.ts`
- Modify: `apps/web-dashboard/src/api.test.ts`
- Modify: `README.md`
- Modify: `RUN.md`
- Modify: `DATA_NOTES.md`

- [ ] **Step 1: Verify CLI/Web tests already express `pdf_url` behavior**

Ensure `apps/agent-cli/src/agent-api.test.ts` contains exactly one test with this body:

```typescript
test("createReport posts pdf_url when provided", async () => {
  let requestBody: unknown;
  await createReport("Pilbara lithium", {
    pdfUrl: "data/pdfs/custom-report.pdf",
    fetchImpl: async (_url, init) => {
      requestBody = JSON.parse(init.body);
      return {
        ok: true,
        status: 200,
        text: async () => "",
        json: async () => ({
          markdown: "report",
          citations: [],
          tool_trace: [],
          fallback_used: false,
          warnings: [],
        }),
      };
    },
  });

  assert.deepEqual(requestBody, {
    query: "Pilbara lithium",
    days: 7,
    pdf_url: "data/pdfs/custom-report.pdf",
  });
});
```

Ensure `apps/web-dashboard/src/api.test.ts` contains exactly one test with this body:

```typescript
test("createReport includes pdf_url when a PDF path is provided", async () => {
  let requestBody: unknown;
  await createReport("Pilbara lithium", {
    pdfUrl: "data/pdfs/custom-report.pdf",
    fetchImpl: async (_url, init) => {
      requestBody = JSON.parse(init.body);
      return {
        ok: true,
        status: 200,
        text: async () => "",
        json: async () => ({
          markdown: "report",
          citations: [],
          tool_trace: [],
          fallback_used: false,
          warnings: [],
        }),
      };
    },
  });

  assert.deepEqual(requestBody, {
    query: "Pilbara lithium",
    days: 7,
    pdf_url: "data/pdfs/custom-report.pdf",
  });
});
```

Run:

```bash
pnpm --recursive test
```

Expected before implementation:

```text
agent-cli or web-dashboard tests fail because pdf_url is not sent
```

- [ ] **Step 2: Implement CLI PDF wiring**

Update `apps/agent-cli/src/format.ts` so `parseCommand` parses both forms:

```typescript
if (value === "--pdf") {
  pdfUrl = rest[index + 1];
  index += 2;
  continue;
}
if (value.startsWith("--pdf=")) {
  pdfUrl = value.slice("--pdf=".length);
  index += 1;
  continue;
}
```

Ensure `apps/agent-cli/src/agent-api.ts` sends:

```typescript
const body: Record<string, unknown> = { query, days };
if (options.pdfUrl?.trim()) {
  body.pdf_url = options.pdfUrl.trim();
}
```

- [ ] **Step 3: Implement Web PDF wiring**

Update `apps/web-dashboard/src/App.tsx` to contain:

```tsx
const [pdfUrl, setPdfUrl] = useState("");
```

and renders:

```tsx
<div className="field">
  <label htmlFor="pdf-url">PDF 路径或 URL</label>
  <input
    id="pdf-url"
    value={pdfUrl}
    onChange={(event) => setPdfUrl(event.target.value)}
    placeholder="data/pdfs/report.pdf 或 https://example.com/report.pdf"
    spellCheck={false}
  />
</div>
```

and calls:

```typescript
setReport(await createReport(trimmedQuery, { days, pdfUrl }));
```

- [ ] **Step 4: Update docs**

Update `README.md`, `RUN.md`, and `DATA_NOTES.md` with these concrete examples:

```bash
$env:MINING_NEWS_RSS_FEEDS="https://example.com/mining.xml"
$env:MINERAL_PDF_DEFAULT_URL="data/pdfs/report.pdf"
$env:PRICE_DATA_FILE="data/prices/live.json"
```

Add an explicit note:

```markdown
Fixture data is retained for reproducible fallback tests. It is not the primary data source when `MINING_NEWS_RSS_FEEDS`, `MINERAL_PDF_DEFAULT_URL`, `PRICE_DATA_FILE`, or `PRICE_DATA_URL` are configured.
```

- [ ] **Step 5: Verify TS and docs-adjacent behavior**

Run:

```bash
pnpm --recursive test
pnpm --recursive build
```

Expected:

```text
all TypeScript tests and builds pass
```

- [ ] **Step 6: Commit**

```bash
git add apps/agent-cli/src apps/web-dashboard/src README.md RUN.md DATA_NOTES.md
git commit -m "feat: expose configurable data sources in clients and docs"
```

---

### Task 7: Final Verification

**Files:**
- No expected code changes unless verification exposes a bug.

- [ ] **Step 1: Run Python tests**

Run:

```bash
python -m pytest
```

Expected:

```text
all Python tests pass
```

- [ ] **Step 2: Run TypeScript tests**

Run:

```bash
pnpm --recursive test
```

Expected:

```text
all TypeScript tests pass
```

- [ ] **Step 3: Run TypeScript builds**

Run:

```bash
pnpm --recursive build
```

Expected:

```text
agent-cli tsc passes; web-dashboard tsc and vite build pass
```

- [ ] **Step 4: Validate Docker Compose config**

Run:

```bash
docker compose config
```

Expected:

```text
Compose renders agent-api and web-dashboard services without errors
```

- [ ] **Step 5: Run focused MCP stdio test**

Run:

```bash
python -m pytest mcp_servers/tests/test_mcp_stdio.py -v
```

Expected:

```text
all MCP stdio list_tools and call_tool tests pass
```

- [ ] **Step 6: Inspect final diff**

Run:

```bash
git diff --check
git status --short
```

Expected:

```text
git diff --check has no whitespace errors
git status shows only intentional uncommitted changes, or a clean tree after final commits
```

- [ ] **Step 7: Route verification failures back to the owning task**

When a verification command fails, do not create a catch-all commit. Return to the task that owns the failing files, make the smallest fix there, rerun that task's focused test command, then rerun the full verification sequence from Task 7 Step 1.

---

## Self-Review

- Spec coverage: Tasks cover provider files for all three MCP domains, settings, no-hardcoded PDF behavior, price source propagation, CLI/Web request wiring, docs, and final verification.
- Placeholder scan: The plan contains no placeholder markers or undefined future work.
- Type consistency: Provider names are consistent with the spec: `RssNewsProvider`, `FixtureNewsProvider`, `PdfResourceProvider`, `FixtureResourceProvider`, `ConfiguredPriceProvider`, and `FixturePriceProvider`.
- Scope check: The plan stays within configurable data providers and does not introduce database, auth, or new Agent framework work.
