from __future__ import annotations

import json
from pathlib import Path

from mining_agent_shared.models import ResourceExtractionResult, ResourceItem

FIXTURE_PATH = Path("data/fixtures/resources.json")


def _load_fixture() -> ResourceExtractionResult:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return ResourceExtractionResult(
        project_name=raw["project_name"],
        report_title=raw["report_title"],
        source_url=raw["source_url"],
        resources=[ResourceItem(**item) for item in raw["resources"]],
        fallback_used=True,
        warnings=["Using fixture NI 43-101-like resource data for reproducible demo."],
    )


def extract_resources(pdf_url: str, project_name: str | None = None) -> ResourceExtractionResult:
    if pdf_url.startswith("fixture://") or pdf_url.startswith("data/"):
        return _load_fixture()

    return ResourceExtractionResult(
        project_name=project_name or "unknown",
        report_title="Unavailable NI 43-101 report",
        source_url=pdf_url,
        resources=[],
        abstain=True,
        fallback_used=False,
        warnings=["PDF extraction abstained because no supported report fixture matched the URL."],
    )
