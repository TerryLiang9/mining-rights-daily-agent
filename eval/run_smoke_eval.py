from app.orchestrator import generate_report

REQUIRED_SECTIONS = ["Executive Summary", "风险提示", "数据质量说明", "Sources"]


def test_smoke_report_sections(monkeypatch):
    monkeypatch.setenv("USE_FIXTURES_ON_FAILURE", "true")
    monkeypatch.setenv("MINING_NEWS_RSS_FEEDS", "")
    monkeypatch.setenv("MINERAL_PDF_DEFAULT_URL", "")
    monkeypatch.setenv("PRICE_DATA_FILE", "")
    monkeypatch.setenv("PRICE_DATA_URL", "")

    response = generate_report("给我生成一份关于 Pilbara 锂矿的今日简报", days=7, llm_provider="mock")
    for section in REQUIRED_SECTIONS:
        assert section in response.markdown
    assert response.citations
    assert response.tool_trace
    assert response.fallback_used is True
