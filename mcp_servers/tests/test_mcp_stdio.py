from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]


def _server_params(server_name: str) -> StdioServerParameters:
    config = json.loads((ROOT / "mcp-config.json").read_text(encoding="utf-8"))
    server = config["mcpServers"][server_name]
    return StdioServerParameters(
        command=server["command"],
        args=server.get("args", []),
        cwd=ROOT,
    )


def test_mcp_config_uses_required_server_names():
    config = json.loads((ROOT / "mcp-config.json").read_text(encoding="utf-8"))
    assert set(config["mcpServers"]) == {
        "mining-news-mcp",
        "mineral-pdf-mcp",
        "lme-price-mcp",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("server_name", "expected_tools", "tool_name", "arguments"),
    [
        (
            "mining-news-mcp",
            {"search", "fetch_article"},
            "search",
            {"query": "Pilbara lithium", "days": 7, "limit": 2},
        ),
        (
            "mining-news-mcp",
            {"search", "fetch_article"},
            "fetch_article",
            {"url": "https://example.com/pilbara-lithium-policy"},
        ),
        (
            "mineral-pdf-mcp",
            {"extract_resources"},
            "extract_resources",
            {"pdf_url": "data/fixtures/pilbara-resource-sample.pdf", "project_name": "Pilbara"},
        ),
        (
            "lme-price-mcp",
            {"get_price", "get_trend"},
            "get_price",
            {"commodity": "lithium", "date": "2026-06-13"},
        ),
        (
            "lme-price-mcp",
            {"get_price", "get_trend"},
            "get_trend",
            {"commodity": "lithium", "days": 30},
        ),
    ],
)
async def test_mcp_config_servers_start_and_call_tools(
    server_name: str,
    expected_tools: set[str],
    tool_name: str,
    arguments: dict,
):
    async with stdio_client(_server_params(server_name)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == expected_tools

            result = await session.call_tool(tool_name, arguments)
            assert result.content
            assert result.isError is not True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("script_path", "expected_tools"),
    [
        ("mcp_servers/mining_news/server.py", {"search", "fetch_article"}),
        ("mcp_servers/mineral_pdf/server.py", {"extract_resources"}),
        ("mcp_servers/lme_price/server.py", {"get_price", "get_trend"}),
    ],
)
async def test_mcp_servers_can_start_from_script_paths(script_path: str, expected_tools: set[str]):
    params = StdioServerParameters(command="python", args=[script_path], cwd=ROOT)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == expected_tools
