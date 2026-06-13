# Live Callable Data Pack Design

## Goal

Make the local demo call non-fixture data by default while keeping the project stable for interviews and local runs.

The selected approach is a hybrid data pack:

- Mining news uses configured public RSS feeds through `MINING_NEWS_RSS_FEEDS`.
- Mineral PDF extraction uses a configured real public PDF or local PDF through `MINERAL_PDF_DEFAULT_URL`.
- Price data uses a local `data/live/prices.csv` snapshot through `PRICE_DATA_FILE`.
- `USE_FIXTURES_ON_FAILURE=false` remains the local default so missing sources produce warnings instead of demo data.

## Non-Goals

- Do not claim licensed real-time LME market data unless a licensed feed is configured.
- Do not scrape pages that prohibit automated access.
- Do not fabricate prices, resources, article titles, URLs, or source names.
- Do not replace the existing MCP tool interface.

## Data Files

Create `data/live/` with:

- `prices.csv`: rows in the existing supported format `commodity,date,price,currency,unit`.
- `sources.json`: source metadata for each configured source, including source URL, retrieval date, data type, and caveats.

The CSV should include enough rows to make trend calls useful for common demo commodities such as lithium, copper, nickel, and zinc. Values must come from public source pages or documented market snapshots, and the metadata must disclose whether the value is spot, contract, index, or another market proxy.

## Configuration

Update local `.env` to point at callable sources:

```env
USE_FIXTURES_ON_FAILURE=false
MINING_NEWS_RSS_FEEDS=<comma-separated public mining RSS feeds>
MINERAL_PDF_DEFAULT_URL=<public report PDF URL or local PDF path>
PRICE_DATA_FILE=data/live/prices.csv
PRICE_DATA_URL=
```

Update `.env.example` with commented guidance instead of machine-specific local choices.

## Runtime Behavior

The Agent API should call the same three MCP servers as today. Success criteria:

- `mining-news-mcp.search` returns RSS-backed results when feeds are reachable.
- `mineral-pdf-mcp.extract_resources` parses the configured report or returns `abstain=true` if the PDF cannot be parsed.
- `lme-price-mcp.get_price` and `get_trend` read `data/live/prices.csv` with `fallback_used=false`.
- The Web Dashboard no longer shows `fallback` for price data when the CSV is configured.
- Warnings clearly describe missing or unreachable live sources.

## Testing

Add or update focused tests for:

- `data/live/prices.csv` can be loaded by the configured price provider.
- `.env.example` documents live provider fields.
- Agent report citations use `data/live/prices.csv` when configured.

Run:

```bash
python -m pytest
pnpm --recursive test
pnpm --recursive build
docker compose config
git diff --check
```

## Risks

Public RSS feeds and PDFs can change or disappear. Price snapshots are not licensed real-time LME data. The UI and generated report must keep disclosing source type and warnings so users can tell the difference between live, configured snapshot, abstain, and fallback states.
