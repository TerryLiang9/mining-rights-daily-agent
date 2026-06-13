from mcp.server.fastmcp import FastMCP

from mcp_servers.mineral_pdf.tools import extract_resources as extract_resources_tool

mcp = FastMCP("mineral-pdf-mcp")


@mcp.tool()
def extract_resources(pdf_url: str, project_name: str | None = None) -> dict:
    """Extract Indicated and Inferred resources from a mineral technical report."""
    return extract_resources_tool(pdf_url=pdf_url, project_name=project_name).model_dump()


if __name__ == "__main__":
    mcp.run()
