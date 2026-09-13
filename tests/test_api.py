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
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
