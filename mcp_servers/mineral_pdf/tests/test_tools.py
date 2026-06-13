from mcp_servers.mineral_pdf.tools import extract_resources


def test_extract_resources_falls_back_to_fixture():
    result = extract_resources("fixture://pilbara-lithium", project_name="Pilbara")
    assert result.project_name == "Pilbara lithium sample"
    assert result.resources
    assert result.resources[0].category == "Indicated"
    assert result.fallback_used is True
    assert result.abstain is False
