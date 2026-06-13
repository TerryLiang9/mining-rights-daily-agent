from fastapi.testclient import TestClient
import pytest

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
            return get_price(**arguments).model_dump()
        if (server_name, tool_name) == ("lme-price-mcp", "get_trend"):
            return get_trend(**arguments).model_dump()
        raise AssertionError(f"Unexpected tool call: {server_name}.{tool_name}")


@pytest.fixture(autouse=True)
def fixture_provider_environment(monkeypatch):
    monkeypatch.setenv("USE_FIXTURES_ON_FAILURE", "true")
    monkeypatch.setenv("MINING_NEWS_RSS_FEEDS", "")
    monkeypatch.setenv("MINERAL_PDF_DEFAULT_URL", "")
    monkeypatch.setenv("PRICE_DATA_FILE", "")
    monkeypatch.setenv("PRICE_DATA_URL", "")


class ConfiguredPriceRecordingToolAdapter(RecordingToolAdapter):
    def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> dict:
        result = super().call_tool(server_name, tool_name, arguments)
        if server_name == "lme-price-mcp":
            result["source"] = "data/live/prices.json"
            result["fallback_used"] = False
            result["warnings"] = []
        return result


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
    assert pdf_arguments[0]["pdf_url"] is None


def test_generate_report_uses_request_pdf_url_when_provided():
    adapter = RecordingToolAdapter()
    requested_pdf = "data/pdfs/custom-report.pdf"

    generate_report(
        "给我生成一份关于 Pilbara 锂矿的今日简报",
        days=7,
        pdf_url=requested_pdf,
        llm_provider="mock",
        tool_adapter=adapter,
    )

    pdf_arguments = [
        arguments
        for server_name, tool_name, arguments in adapter.arguments
        if (server_name, tool_name) == ("mineral-pdf-mcp", "extract_resources")
    ]
    assert pdf_arguments[0]["pdf_url"] == requested_pdf


def test_generate_report_uses_price_tool_source_in_citations():
    adapter = ConfiguredPriceRecordingToolAdapter()

    response = generate_report(
        "给我生成一份关于 Pilbara 锂矿的今日简报",
        days=7,
        llm_provider="mock",
        tool_adapter=adapter,
    )

    price_citations = [
        citation for citation in response.citations if citation.source_type == "price"
    ]
    assert price_citations
    assert price_citations[0].url == "data/live/prices.json"


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


def test_api_accepts_pdf_url_in_report_request():
    client = TestClient(app)

    response = client.post(
        "/reports",
        json={
            "query": "给我生成一份关于 Pilbara 锂矿的今日简报",
            "days": 7,
            "pdf_url": "data/fixtures/pilbara-resource-sample.pdf",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["markdown"]
    assert any(
        trace["tool"] == "mineral-pdf-mcp.extract_resources"
        and trace["input"]["pdf_url"] == "data/fixtures/pilbara-resource-sample.pdf"
        for trace in payload["tool_trace"]
    )
