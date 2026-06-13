from mcp_servers.mineral_pdf.tools import extract_resources


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
