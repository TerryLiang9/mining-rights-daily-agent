from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.server.fastmcp import FastMCP

from mcp_servers.lme_price.tools import get_price as get_price_tool
from mcp_servers.lme_price.tools import get_trend as get_trend_tool

mcp = FastMCP("lme-price-mcp")


@mcp.tool()
def get_price(commodity: str, date: str | None = None) -> dict:
    """Get latest or date-specific commodity price."""
    return get_price_tool(commodity=commodity, date=date).model_dump()


@mcp.tool()
def get_trend(commodity: str, days: int = 30) -> dict:
    """Get commodity price trend."""
    return get_trend_tool(commodity=commodity, days=days).model_dump()


if __name__ == "__main__":
    mcp.run()
