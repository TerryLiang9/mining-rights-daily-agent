from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader

from mcp_servers.mineral_pdf.parser import parse_resource_lines
from mining_agent_shared.models import ResourceExtractionResult, ResourceItem

ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT_DIR / "data" / "fixtures" / "resources.json"


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


def _read_pdf_bytes(pdf_url: str) -> bytes:
    parsed = urlparse(pdf_url)
    if parsed.scheme in {"http", "https"}:
        response = httpx.get(pdf_url, timeout=30)
        response.raise_for_status()
        return response.content

    path = Path(pdf_url)
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path.read_bytes()


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    page_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(page_text)


def extract_resources(pdf_url: str, project_name: str | None = None) -> ResourceExtractionResult:
    if pdf_url.startswith("fixture://") or pdf_url.endswith("resources.json"):
        return _load_fixture()

    try:
        text = _extract_pdf_text(_read_pdf_bytes(pdf_url))
    except Exception as exc:
        return ResourceExtractionResult(
            project_name=project_name or "unknown",
            report_title="Unreadable NI 43-101 report",
            source_url=pdf_url,
            resources=[],
            abstain=True,
            fallback_used=False,
            warnings=[f"PDF extraction failed: {exc}"],
        )

    resources = parse_resource_lines(text)
    if resources:
        return ResourceExtractionResult(
            project_name=project_name or "unknown",
            report_title=Path(urlparse(pdf_url).path).name or "Extracted NI 43-101 report",
            source_url=pdf_url,
            resources=resources,
            abstain=False,
            fallback_used=False,
            warnings=[],
        )

    return ResourceExtractionResult(
        project_name=project_name or "unknown",
        report_title="Unavailable NI 43-101 report",
        source_url=pdf_url,
        resources=[],
        abstain=True,
        fallback_used=False,
        warnings=["PDF extraction abstained because no Indicated/Inferred resource lines were found."],
    )
