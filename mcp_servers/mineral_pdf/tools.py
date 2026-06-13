from __future__ import annotations

from mining_agent_shared.config import get_settings
from mining_agent_shared.models import ResourceExtractionResult
from mcp_servers.mineral_pdf.providers import FixtureResourceProvider, PdfResourceProvider


def extract_resources(pdf_url: str | None = None, project_name: str | None = None) -> ResourceExtractionResult:
    settings = get_settings()
    normalized_pdf_url = pdf_url.strip() if isinstance(pdf_url, str) and pdf_url.strip() else ""
    if not normalized_pdf_url:
        normalized_pdf_url = settings.mineral_pdf_default_url.strip()

    if not normalized_pdf_url:
        return ResourceExtractionResult(
            project_name=project_name or "unknown",
            report_title="No NI 43-101 report provided",
            source_url="",
            resources=[],
            abstain=True,
            fallback_used=False,
            warnings=["PDF source was not provided; set pdf_url or MINERAL_PDF_DEFAULT_URL."],
        )

    if normalized_pdf_url.startswith("fixture://") or normalized_pdf_url.endswith("resources.json"):
        return FixtureResourceProvider().extract()

    try:
        return PdfResourceProvider().extract(normalized_pdf_url, project_name)
    except Exception as exc:
        return ResourceExtractionResult(
            project_name=project_name or "unknown",
            report_title="Unreadable NI 43-101 report",
            source_url=normalized_pdf_url,
            resources=[],
            abstain=True,
            fallback_used=False,
            warnings=[f"PDF extraction failed: {exc}"],
        )
