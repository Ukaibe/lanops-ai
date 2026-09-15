"""MCP protocol boundary for LAN operations tools."""

from mcp.server.fastmcp import FastMCP

from lanops_ai import tools

mcp = FastMCP(
    "LAN Ops Tools",
    instructions=(
        "Read-only diagnostics are preferred. Remote command tools enforce the "
        "application's network allowlist and explicit enablement setting."
    ),
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
)

# Registration lives here so tool implementations remain transport-independent
# and can be unit tested without an MCP session.
mcp.tool()(tools.ping)
mcp.tool()(tools.dns_lookup)
mcp.tool()(tools.snmp_get)
mcp.tool()(tools.ssh_command)
mcp.tool()(tools.powershell_winrm)
mcp.tool()(tools.search_runbooks)
mcp.tool()(tools.recent_syslog)

mcp_app = mcp.streamable_http_app()

__all__ = ["mcp", "mcp_app"]
