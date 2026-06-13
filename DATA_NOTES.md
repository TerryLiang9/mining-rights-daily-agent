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

## Fixture Strategy

The interview task asks for mining news, mineral PDF extraction, and price trend tools. Some real-world sources have login walls, rate limits, inconsistent PDF table layouts, or anti-scraping rules. This project therefore keeps fixture data in `data/fixtures` and marks every fallback in:

- the tool response,
- the Agent API response,
- the CLI output,
- the Web Dashboard,
- and the generated Markdown report.

This keeps the demo reproducible while preserving clear replacement points for production sources.

## Replacement Points

- `mcp_servers/mining_news/tools.py`: replace fixture search with RSS or public web search.
- `mcp_servers/mineral_pdf/tools.py`: replace fixture extraction with PDF download and parser/model extraction.
- `mcp_servers/lme_price/tools.py`: replace fixture prices with licensed LME/SHFE/market-data connectors.
