from fastapi.testclient import TestClient

from lanops_ai.api import app


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
