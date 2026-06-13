# Data Notes

The project uses fixture data when external mining news, PDF, or price sources are unavailable. Fallback use is explicit in the API response, CLI output, Web Dashboard, and generated report.

## Core Schemas

- News item: title, url, source, published_at, summary, score.
- Resource item: category, ore tonnage, grade, contained metal, units, page, confidence.
- Price point: commodity, date, price, currency, unit.
- Evidence pack: topic, news, resources, prices, citations, tool trace, data_quality.

## Data Quality Rules

- Blank news queries return no items instead of fixture noise.
- News search can read comma-separated RSS URLs from `MINING_NEWS_RSS_FEEDS`; if no live item is available, it falls back to fixture news and discloses that fallback.
- Article fetching only accepts HTTP(S) URLs and rejects unsafe local schemes.
- Missing or unreadable PDF evidence returns `abstain=true`; fixture resource data is used only for explicit `fixture://` or fixture JSON requests.
- PDF resource extraction records page numbers for text-based PDFs when `pypdf` can extract them.
- Unsupported commodities and missing exact price dates return structured warnings; date-specific prices use the nearest prior close when available.
- Generated reports must disclose fallback data.

## Fixture Strategy

The interview task asks for mining news, mineral PDF extraction, and price trend tools. Some real-world sources have login walls, rate limits, inconsistent PDF table layouts, or anti-scraping rules. This project therefore keeps fixture data in `data/fixtures` and marks every fallback in:

- the tool response,
- the Agent API response,
- the CLI output,
- the Web Dashboard,
- and the generated Markdown report.

This keeps the demo reproducible while preserving clear replacement points for production sources. The included price data is still fixture data, not a licensed live LME feed.

## Replacement Points

- `mcp_servers/mining_news/tools.py`: configure RSS feeds with `MINING_NEWS_RSS_FEEDS` or replace the provider with a licensed/news-search connector.
- `mcp_servers/mineral_pdf/tools.py`: improve parser/model extraction for scanned PDFs and complex NI 43-101 tables.
- `mcp_servers/lme_price/tools.py`: replace fixture prices with licensed LME/SHFE/market-data connectors.
