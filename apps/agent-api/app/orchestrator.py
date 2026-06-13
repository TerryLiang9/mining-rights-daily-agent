from __future__ import annotations

from time import perf_counter
from typing import Any, Protocol

from app.adapters.mcp_stdio import MCPStdioToolAdapter
from app.llm.mock import MockLLMProvider
from app.llm.ollama import OllamaProvider
from mining_agent_shared.citations import make_citation
from mining_agent_shared.config import get_settings
from mining_agent_shared.models import (
    Article,
    EvidencePack,
    NewsSearchResult,
    PriceQuote,
    PriceTrend,
    ReportResponse,
    ResourceExtractionResult,
    ToolTrace,
    Topic,
)


class ToolAdapter(Protocol):
    def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        ...

REQUIRED_REPORT_SECTIONS = ("Executive Summary", "风险提示", "数据质量说明", "Sources")
SAMPLE_RESOURCE_PDF = "data/fixtures/pilbara-resource-sample.pdf"


def parse_topic(query: str, days: int) -> Topic:
    lowered = query.lower()
    region = "Pilbara" if "pilbara" in lowered else "global"
    if "锂" in query or "lithium" in lowered:
        commodity = "lithium"
    elif "铜" in query or "copper" in lowered:
        commodity = "copper"
    elif "镍" in query or "nickel" in lowered:
        commodity = "nickel"
    elif "锌" in query or "zinc" in lowered:
        commodity = "zinc"
    else:
        commodity = "lithium"
    return Topic(raw_query=query, region=region, commodity=commodity, days=days)


def _trace(
    tool: str,
    input_payload: dict,
    status: str,
    start: float,
    fallback_used: bool,
    message: str | None = None,
) -> ToolTrace:
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


def _report_has_required_sections(markdown: str) -> bool:
    return all(section in markdown for section in REQUIRED_REPORT_SECTIONS)


def generate_report(
    query: str,
    days: int = 7,
    pdf_url: str | None = None,
    llm_provider: str | None = None,
    tool_adapter: ToolAdapter | None = None,
) -> ReportResponse:
    settings = get_settings()
    topic = parse_topic(query, days)
    adapter = tool_adapter or MCPStdioToolAdapter()
    traces: list[ToolTrace] = []
    warnings: list[str] = []
    resource_pdf_url = pdf_url.strip() if pdf_url and pdf_url.strip() else SAMPLE_RESOURCE_PDF

    start = perf_counter()
    news_query = f"{topic.region} {topic.commodity} mining"
    news_result = NewsSearchResult(
        **adapter.call_tool(
            "mining-news-mcp",
            "search",
            {"query": news_query, "days": days, "limit": 3},
        )
    )
    traces.append(
        _trace(
            "mining-news-mcp.search",
            {"query": news_query, "days": days, "limit": 3},
            "fallback" if news_result.fallback_used else "success",
            start,
            news_result.fallback_used,
        )
    )
    warnings.extend(news_result.warnings)

    articles = []
    for item in news_result.items[:2]:
        start = perf_counter()
        article = Article(
            **adapter.call_tool("mining-news-mcp", "fetch_article", {"url": item.url})
        )
        articles.append(article)
        traces.append(
            _trace(
                "mining-news-mcp.fetch_article",
                {"url": item.url},
                "fallback" if article.fallback_used else "success",
                start,
                article.fallback_used,
            )
        )
        warnings.extend(article.warnings)

    start = perf_counter()
    resources = ResourceExtractionResult(
        **adapter.call_tool(
            "mineral-pdf-mcp",
            "extract_resources",
            {"pdf_url": resource_pdf_url, "project_name": topic.region},
        )
    )
    traces.append(
        _trace(
            "mineral-pdf-mcp.extract_resources",
            {"pdf_url": resource_pdf_url, "project_name": topic.region},
            "fallback" if resources.fallback_used else "success",
            start,
            resources.fallback_used,
        )
    )
    warnings.extend(resources.warnings)

    start = perf_counter()
    price_trend = PriceTrend(
        **adapter.call_tool(
            "lme-price-mcp",
            "get_trend",
            {"commodity": topic.commodity, "days": 30},
        )
    )
    traces.append(
        _trace(
            "lme-price-mcp.get_trend",
            {"commodity": topic.commodity, "days": 30},
            "fallback" if price_trend.fallback_used else "success",
            start,
            price_trend.fallback_used,
        )
    )
    warnings.extend(price_trend.warnings)

    start = perf_counter()
    price_quote = PriceQuote(
        **adapter.call_tool(
            "lme-price-mcp",
            "get_price",
            {
                "commodity": topic.commodity,
                "date": price_trend.points[-1].date if price_trend.points else None,
            },
        )
    )
    traces.append(
        _trace(
            "lme-price-mcp.get_price",
            {"commodity": topic.commodity, "date": price_quote.date},
            "fallback" if price_quote.fallback_used else "success",
            start,
            price_quote.fallback_used,
        )
    )
    warnings.extend(price_quote.warnings)

    citations = [
        *[make_citation(item.title, item.url, "news") for item in news_result.items],
        make_citation(resources.report_title, resources.source_url, "pdf"),
        make_citation(f"{topic.commodity} price data", "data/fixtures/prices.json", "price"),
    ]
    fallback_used = any(trace.fallback_used for trace in traces)
    evidence = EvidencePack(
        topic=topic,
        news=news_result.items,
        articles=articles,
        resources=resources.resources,
        prices=price_trend.points,
        current_price=price_quote,
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

    if not _report_has_required_sections(markdown):
        warnings.append("Generated report missed required sections; mock provider normalized the output.")
        markdown = MockLLMProvider().generate_report(evidence)

    return ReportResponse(
        markdown=markdown,
        citations=citations,
        tool_trace=traces,
        fallback_used=fallback_used,
        warnings=warnings,
    )
