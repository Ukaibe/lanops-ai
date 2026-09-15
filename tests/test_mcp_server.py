from lanops_ai.mcp_server import mcp


async def test_mcp_server_exposes_all_lan_tools():
    tools = await mcp.list_tools()
    tools_by_name = {tool.name: tool for tool in tools}

    assert set(tools_by_name) == {
        "dns_lookup",
        "ping",
        "powershell_winrm",
        "recent_syslog",
        "search_runbooks",
        "snmp_get",
        "ssh_command",
    }
    assert tools_by_name["ping"].inputSchema["required"] == ["host"]
