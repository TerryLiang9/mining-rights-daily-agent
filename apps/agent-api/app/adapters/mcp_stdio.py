from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT_DIR = Path(__file__).resolve().parents[4]
DEFAULT_CONFIG_PATH = ROOT_DIR / "mcp-config.json"


class MCPStdioToolAdapter:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_PATH

    def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return asyncio.run(self._call_tool(server_name, tool_name, arguments))

    async def _call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        params = self._server_params(server_name)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)

        if result.isError:
            text = result.content[0].text if result.content else "MCP tool returned an error."
            raise RuntimeError(f"{server_name}.{tool_name} failed: {text}")
        if not result.content:
            return {}

        text = result.content[0].text
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise TypeError(f"{server_name}.{tool_name} returned non-object JSON.")
        return payload

    def _server_params(self, server_name: str) -> StdioServerParameters:
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        server = config["mcpServers"][server_name]
        return StdioServerParameters(
            command=server["command"],
            args=server.get("args", []),
            cwd=ROOT_DIR,
        )
