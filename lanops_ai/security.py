import ipaddress
import socket

from lanops_ai.config import get_settings


def resolve_allowed_host(host: str) -> str:
    """Resolve a hostname and reject addresses outside configured networks."""
    networks = [
        ipaddress.ip_network(item.strip())
        for item in get_settings().allowed_networks.split(",")
        if item.strip()
    ]
    addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
    if not addresses:
        raise ValueError("Host did not resolve")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not any(ip in network for network in networks):
            raise ValueError(f"Target {address} is outside LANOPS_ALLOWED_NETWORKS")
    return min(addresses)


def require_remote_commands() -> None:
    if not get_settings().enable_remote_commands:
        raise PermissionError("Remote commands are disabled; set LANOPS_ENABLE_REMOTE_COMMANDS=true")
