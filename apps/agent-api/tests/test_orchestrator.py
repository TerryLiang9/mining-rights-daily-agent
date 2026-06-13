from fastapi.testclient import TestClient

from app.main import app
from app.orchestrator import generate_report
from mcp_servers.lme_price.tools import get_price, get_trend
from mcp_servers.mineral_pdf.tools import extract_resources
from mcp_servers.mining_news.tools import fetch_article, search


class RecordingToolAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.arguments: list[tuple[str, str, dict]] = []

    def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> dict:
        self.calls.append((server_name, tool_name))
        self.arguments.append((server_name, tool_name, arguments))
        if (server_name, tool_name) == ("mining-news-mcp", "search"):
            return search(**arguments).model_dump()
        if (server_name, tool_name) == ("mining-news-mcp", "fetch_article"):
            return fetch_article(**arguments).model_dump()
        if (server_name, tool_name) == ("mineral-pdf-mcp", "extract_resources"):
            return extract_resources(**arguments).model_dump()
        if (server_name, tool_name) == ("lme-price-mcp", "get_price"):
            return get_price(**arguments)
        if (server_name, tool_name) == ("lme-price-mcp", "get_trend"):
            return get_trend(**arguments).model_dump()
        raise AssertionError(f"Unexpected tool call: {server_name}.{tool_name}")


def test_generate_report_contains_required_sections():
    response = generate_report("给我生成一份关于 Pilbara 锂矿的今日简报", days=7, llm_provider="mock")

    assert "Executive Summary" in response.markdown
    assert "风险提示" in response.markdown
    assert "数据质量说明" in response.markdown
    assert "Sources" in response.markdown
    assert "当前价格" in response.markdown
    assert "12850" in response.markdown
    assert response.citations
    assert response.tool_trace
    assert response.fallback_used is True
    assert isinstance(response.warnings, list)


def test_generate_report_uses_tool_adapter_for_required_mcp_calls():
    adapter = RecordingToolAdapter()

    response = generate_report(
        "给我生成一份关于 Pilbara 锂矿的今日简报",
        days=7,
        llm_provider="mock",
        tool_adapter=adapter,
    )

    assert response.markdown
    assert ("mining-news-mcp", "search") in adapter.calls
    assert ("mining-news-mcp", "fetch_article") in adapter.calls
    assert ("mineral-pdf-mcp", "extract_resources") in adapter.calls
    assert ("lme-price-mcp", "get_price") in adapter.calls
    assert ("lme-price-mcp", "get_trend") in adapter.calls
    assert "lme-price-mcp.get_price" in {trace.tool for trace in response.tool_trace}


def test_generate_report_uses_pdf_path_for_resource_extraction():
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
    assert pdf_arguments[0]["pdf_url"].endswith(".pdf")


def test_api_exposes_health_and_report_routes():
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    response = client.post(
        "/reports",
        json={"query": "给我生成一份关于 Pilbara 锂矿的今日简报", "days": 7},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["markdown"]
    assert payload["citations"]
    assert payload["tool_trace"]
    assert payload["fallback_used"] is True
    assert isinstance(payload["warnings"], list)
