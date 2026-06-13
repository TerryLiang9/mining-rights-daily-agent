from mcp_servers.mineral_pdf.parser import parse_resource_pages
import mcp_servers.mineral_pdf.tools as tools
from mcp_servers.mineral_pdf.tools import extract_resources
from mining_agent_shared.config import Settings


def _minimal_pdf_with_text(lines: list[str]) -> bytes:
    stream = "BT /F1 12 Tf 72 720 Td " + " T* ".join(f"({line}) Tj" for line in lines) + " ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream".encode("latin-1"),
    ]
    parts = [b"%PDF-1.4\n"]
    offsets: list[int] = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in parts))
        parts.append(f"{index} 0 obj\n".encode("ascii"))
        parts.append(obj)
        parts.append(b"\nendobj\n")
    xref_offset = sum(len(part) for part in parts)
    parts.append(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    parts.append(b"0000000000 65535 f \n")
    for offset in offsets:
        parts.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    parts.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return b"".join(parts)


def test_extract_resources_falls_back_to_fixture():
    result = extract_resources("fixture://pilbara-lithium", project_name="Pilbara")
    assert result.project_name == "Pilbara lithium sample"
    assert result.resources
    assert result.resources[0].category == "Indicated"
    assert result.fallback_used is True
    assert result.abstain is False


def test_extract_resources_reads_local_pdf(tmp_path):
    pdf_path = tmp_path / "pilbara-resource.pdf"
    pdf_path.write_bytes(
        _minimal_pdf_with_text(
            [
                "Indicated 120.5 Mt 1.25% Li2O 1.5 Mt LCE",
                "Inferred 80.2 Mt 1.05% Li2O 0.9 Mt LCE",
            ]
        )
    )

    result = extract_resources(str(pdf_path), project_name="Pilbara")

    assert result.project_name == "Pilbara"
    assert result.abstain is False
    assert result.fallback_used is False
    assert [resource.category for resource in result.resources] == ["Indicated", "Inferred"]
    assert {resource.page for resource in result.resources} == {1}


def test_extract_resources_abstains_without_pdf_source(monkeypatch):
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(mineral_pdf_default_url="", use_fixtures_on_failure=True),
    )

    result = extract_resources(None, project_name="Pilbara")

    assert result.project_name == "Pilbara"
    assert result.source_url == ""
    assert result.resources == []
    assert result.abstain is True
    assert result.fallback_used is False
    assert any("PDF source" in warning for warning in result.warnings)


def test_extract_resources_uses_default_pdf_url_from_settings(tmp_path, monkeypatch):
    pdf_path = tmp_path / "configured-resource.pdf"
    pdf_path.write_bytes(
        _minimal_pdf_with_text(["Indicated 12.5 Mt 1.10% Li2O 0.15 Mt LCE"])
    )
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: Settings(mineral_pdf_default_url=str(pdf_path)),
    )

    result = extract_resources(None, project_name="Configured")

    assert result.project_name == "Configured"
    assert result.source_url == str(pdf_path)
    assert result.abstain is False
    assert result.fallback_used is False
    assert [resource.category for resource in result.resources] == ["Indicated"]


def test_parser_handles_common_ni_43101_resource_wording_with_pages():
    resources = parse_resource_pages(
        [
            (
                12,
                """
                Mineral Resource Estimate
                Indicated Resources 120.5 million tonnes at 1.25% Li2O containing 1.50 Mt LCE
                Inferred Resources 80.2 Mt at 1.05% Li2O containing 0.90 Mt LCE
                """,
            )
        ]
    )

    assert [resource.category for resource in resources] == ["Indicated", "Inferred"]
    assert resources[0].ore_tonnage == 120.5
    assert resources[0].ore_tonnage_unit == "Mt"
    assert resources[0].page == 12
    assert resources[1].contained_metal == 0.9
