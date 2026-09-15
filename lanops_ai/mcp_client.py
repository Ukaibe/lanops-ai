"""Small MCP client used by the agent to discover and invoke tools."""

from dataclasses import dataclass
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


@dataclass(frozen=True)
class MCPToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


class MCPToolClient:
    """Use a fresh stateless Streamable HTTP session for each MCP operation."""

    def __init__(self, url: str) -> None:
        self._url = url

    async def list_tools(self) -> list[MCPToolDefinition]:
        async with (
            streamable_http_client(self._url) as streams,
            ClientSession(streams[0], streams[1]) as session,
        ):
            await session.initialize()
            result = await session.list_tools()
        return [
            MCPToolDefinition(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema,
            )
            for tool in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        async with (
            streamable_http_client(self._url) as streams,
            ClientSession(streams[0], streams[1]) as session,
        ):
            await session.initialize()
            result = await session.call_tool(name, arguments)

        text = "\n".join(
            block.text for block in result.content if hasattr(block, "text")
        )
        if result.isError:
            raise RuntimeError(text or f"MCP tool {name!r} failed")
        if text:
            return text
        if result.structuredContent is not None:
            return str(result.structuredContent)
        return "MCP tool completed without textual output"
