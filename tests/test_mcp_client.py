from types import SimpleNamespace

from lanops_ai.mcp_client import MCPToolClient


async def test_mcp_client_discovers_and_calls_tools(monkeypatch):
    class _Transport:
        async def __aenter__(self):
            return (object(), object(), None)

        async def __aexit__(self, *args):
            return None

    class _Session:
        def __init__(self, *args):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def initialize(self):
            pass

        async def list_tools(self):
            return SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="ping",
                        description="Ping a host",
                        inputSchema={"type": "object"},
                    )
                ]
            )

        async def call_tool(self, name, arguments):
            assert name == "ping"
            assert arguments == {"host": "127.0.0.1"}
            return SimpleNamespace(
                content=[SimpleNamespace(text="reachable")],
                isError=False,
                structuredContent=None,
            )

    monkeypatch.setattr("lanops_ai.mcp_client.streamable_http_client", lambda url: _Transport())
    monkeypatch.setattr("lanops_ai.mcp_client.ClientSession", _Session)
    client = MCPToolClient("http://mcp.test/mcp/")

    definitions = await client.list_tools()
    result = await client.call_tool("ping", {"host": "127.0.0.1"})

    assert definitions[0].name == "ping"
    assert result == "reachable"
