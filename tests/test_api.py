from fastapi.testclient import TestClient
from starlette.requests import Request

from lanops_ai.api import _request_client_ip, app


class _Transport:
    def close(self):
        pass


async def _fake_syslog():
    return _Transport()


def test_health(monkeypatch):
    monkeypatch.setattr("lanops_ai.api.start_syslog_server", _fake_syslog)
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        response = client.get("/api/health")
        mcp_response = client.post(
            "/mcp/",
            headers={"Accept": "application/json, text/event-stream"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert mcp_response.status_code == 200
    assert mcp_response.json()["result"]["serverInfo"]["name"] == "LAN Ops Tools"


def test_request_client_ip_uses_proxy_observed_address():
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/chat",
            "headers": [(b"x-forwarded-for", b"192.168.1.77")],
            "scheme": "http",
            "server": ("lanops.example", 8080),
            "client": ("172.18.0.4", 12345),
            "query_string": b"",
        }
    )

    assert _request_client_ip(request) == "192.168.1.77"


def test_request_client_ip_replaces_docker_gateway_with_host_address(monkeypatch):
    monkeypatch.setenv("LANOPS_HOST_IPV4_ADDRESS", "192.168.1.228")
    from lanops_ai.config import get_settings

    get_settings.cache_clear()
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/chat",
            "headers": [(b"x-forwarded-for", b"172.18.0.1")],
            "scheme": "http",
            "server": ("lanops.example", 8080),
            "client": ("172.18.0.4", 12345),
            "query_string": b"",
        }
    )

    assert _request_client_ip(request) == "192.168.1.228"
    get_settings.cache_clear()
