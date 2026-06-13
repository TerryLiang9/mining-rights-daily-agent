from fastapi.testclient import TestClient

from app.main import app
from app.orchestrator import generate_report


def test_generate_report_contains_required_sections():
    response = generate_report("给我生成一份关于 Pilbara 锂矿的今日简报", days=7, llm_provider="mock")

    assert "Executive Summary" in response.markdown
    assert "风险提示" in response.markdown
    assert "数据质量说明" in response.markdown
    assert "Sources" in response.markdown
    assert response.citations
    assert response.tool_trace
    assert response.fallback_used is True
    assert isinstance(response.warnings, list)


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
