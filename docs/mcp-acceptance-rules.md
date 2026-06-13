# MCP Acceptance Rules

This document defines the strict delivery rules for interview task #2: build a mining rights daily Agent with MCP.

## Required MCP Servers

The repository must expose these MCP servers through `mcp-config.json`:

- `mining-news-mcp`
- `mineral-pdf-mcp`
- `lme-price-mcp`

The configured names should match the task statement so Claude Desktop, Cursor, and reviewers can inspect the same server names without translation.

## Required Tools

Each server must expose and pass MCP stdio calls for its required tools:

- `mining-news-mcp.search(query, days)`
- `mining-news-mcp.fetch_article(url)`
- `mineral-pdf-mcp.extract_resources(pdf_url)`
- `lme-price-mcp.get_price(commodity, date)`
- `lme-price-mcp.get_trend(commodity, days)`

Tests must verify both `list_tools` and `call_tool` for every required tool, not only the existence of tool names.

## Agent Workflow Rules

For the input `给我生成一份关于 Pilbara 锂矿的今日简报`, the Agent client must:

1. Call `mining-news-mcp.search`.
2. Call `mining-news-mcp.fetch_article` for selected news URLs.
3. Call `mineral-pdf-mcp.extract_resources` with a PDF URL or local PDF path.
4. Call `lme-price-mcp.get_price`.
5. Call `lme-price-mcp.get_trend`.
6. Build an evidence pack from tool outputs.
7. Return a Markdown report with news summary, resource data, current price, price trend, risk notes, data quality notes, and cited source links.

The Agent must route these calls through the MCP stdio adapter by default.

## PDF Evidence Rules

The PDF server may use deterministic sample data for reproducible demos, but the Agent flow must demonstrate the `extract_resources(pdf_url)` path with a real local PDF fixture or HTTP PDF URL.

If PDF parsing fails or no Indicated/Inferred resource rows are found, the tool must return `abstain=true` and explain the issue in `warnings`.

## Price Evidence Rules

The report must include both:

- the current or requested-date price from `get_price`
- the multi-day trend from `get_trend`

Tool trace must show both price calls.

## Delivery Rules

The project must keep:

- `mcp-config.json` for Claude Desktop / Cursor verification.
- `RUN.md` with a 5-minute run path and one `docker compose up --build` command.
- Python and TypeScript tests for the Agent, MCP servers, CLI, and dashboard API client.

Before claiming completion, run:

```bash
python -m pytest
pnpm --recursive test
pnpm --recursive build
docker compose config
```

If Docker Desktop is unavailable, report that `docker compose config` passed but image build/runtime was not verified.
