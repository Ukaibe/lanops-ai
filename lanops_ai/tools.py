import asyncio
import json
import platform

import dns.resolver
import paramiko
import winrm
from langchain_core.tools import tool
from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    get_cmd,
)

from lanops_ai.config import get_settings
from lanops_ai.rag import knowledge_base
from lanops_ai.security import require_remote_commands, resolve_allowed_host
from lanops_ai.syslog import RECENT_MESSAGES


def _clip(value: str, size: int = 12000) -> str:
    return value[:size]


@tool
async def ping(host: str, count: int = 3) -> str:
    """Ping an allowlisted LAN host and return packet statistics."""
    address = await asyncio.to_thread(resolve_allowed_host, host)
    flag = "-n" if platform.system() == "Windows" else "-c"
    process = await asyncio.create_subprocess_exec(
        "ping",
        flag,
        str(max(1, min(count, 5))),
        address,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output, _ = await asyncio.wait_for(process.communicate(), timeout=20)
    return _clip(output.decode(errors="replace"))


@tool
async def dns_lookup(name: str, record_type: str = "A") -> str:
    """Resolve A, AAAA, CNAME, MX, NS, PTR, or TXT DNS records."""
    kind = record_type.upper()
    if kind not in {"A", "AAAA", "CNAME", "MX", "NS", "PTR", "TXT"}:
        raise ValueError("Unsupported DNS record type")
    answers = await asyncio.to_thread(dns.resolver.resolve, name, kind, lifetime=5)
    return json.dumps([answer.to_text() for answer in answers])


@tool
async def snmp_get(host: str, oid: str = "1.3.6.1.2.1.1.1.0") -> str:
    """Read one SNMP v2c OID from an allowlisted device."""
    address = await asyncio.to_thread(resolve_allowed_host, host)
    settings = get_settings()
    error, status, index, bindings = await get_cmd(
        SnmpEngine(),
        CommunityData(settings.snmp_community),
        await UdpTransportTarget.create((address, 161), timeout=3, retries=1),
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
    )
    if error or status:
        return f"SNMP error: {error or status.prettyPrint()} at index {index}"
    return "\n".join(
        f"{key.prettyPrint()} = {value.prettyPrint()}" for key, value in bindings
    )


@tool
async def ssh_command(host: str, command: str) -> str:
    """Run a command over SSH when remote commands are explicitly enabled."""
    require_remote_commands()
    address = await asyncio.to_thread(resolve_allowed_host, host)
    settings = get_settings()
    if not settings.ssh_username:
        raise ValueError("LANOPS_SSH_USERNAME is required")

    def run() -> str:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.connect(
            address,
            username=settings.ssh_username,
            password=settings.ssh_password,
            key_filename=settings.ssh_key_file,
            timeout=8,
        )
        _, stdout, stderr = client.exec_command(command, timeout=15)
        result = stdout.read().decode(errors="replace") + stderr.read().decode(errors="replace")
        client.close()
        return _clip(result)

    return await asyncio.to_thread(run)


@tool
async def powershell_winrm(host: str, script: str) -> str:
    """Run PowerShell through WinRM when remote commands are explicitly enabled."""
    require_remote_commands()
    address = await asyncio.to_thread(resolve_allowed_host, host)
    settings = get_settings()
    if not settings.winrm_username or not settings.winrm_password:
        raise ValueError("WinRM credentials are required")

    def run() -> str:
        session = winrm.Session(
            f"http://{address}:5985/wsman",
            auth=(settings.winrm_username, settings.winrm_password),
            transport=settings.winrm_transport,
            read_timeout_sec=20,
            operation_timeout_sec=15,
        )
        result = session.run_ps(script)
        stdout = result.std_out.decode(errors="replace")
        stderr = result.std_err.decode(errors="replace")
        return _clip(f"status={result.status_code}\n{stdout}\n{stderr}")

    return await asyncio.to_thread(run)


@tool
async def search_runbooks(query: str) -> str:
    """Search indexed runbooks and network documentation."""
    return json.dumps(await asyncio.to_thread(knowledge_base.search, query), indent=2)


@tool
def recent_syslog(limit: int = 50, contains: str = "") -> str:
    """Return recent received syslog records, optionally filtered by text."""
    rows = list(RECENT_MESSAGES)
    if contains:
        rows = [row for row in rows if contains.lower() in row["message"].lower()]
    return json.dumps(rows[-max(1, min(limit, 100)) :], indent=2)


TOOLS = [
    ping,
    dns_lookup,
    snmp_get,
    ssh_command,
    powershell_winrm,
    search_runbooks,
    recent_syslog,
]
