from fastapi.testclient import TestClient

from app.main import app
from app.api.v1 import registry
from app.api.deps import get_db


client = TestClient(app)


class _FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeHttpxClient:
    def __init__(self, timeout: float):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url: str):
        if url.endswith("/health"):
            return _FakeResponse(200, {"status": "ok"})
        if url.endswith("/tools"):
            return _FakeResponse(200, {"tools": [{"name": "ping"}, {"name": "echo"}]})
        return _FakeResponse(404, {})


def test_mcp_probe_success(monkeypatch) -> None:
    app.dependency_overrides[get_db] = lambda: None
    monkeypatch.setattr(registry.store, "assert_project_member", lambda db, project_id, user_id: None)
    monkeypatch.setattr(registry.httpx, "Client", _FakeHttpxClient)

    response = client.post(
        "/api/v1/registry/mcp/probe",
        json={
            "project_id": "p1",
            "config": {
                "transport": "streamable_http",
                "endpoint_url": "http://127.0.0.1:8099",
                "timeout_seconds": 5,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["health_ok"] is True
    assert data["tools_ok"] is True
    assert data["tools"] == ["ping", "echo"]

    app.dependency_overrides.clear()


def test_mcp_probe_rejects_stdio(monkeypatch) -> None:
    app.dependency_overrides[get_db] = lambda: None
    monkeypatch.setattr(registry.store, "assert_project_member", lambda db, project_id, user_id: None)

    response = client.post(
        "/api/v1/registry/mcp/probe",
        json={
            "project_id": "p1",
            "config": {
                "transport": "stdio",
                "command": "python",
                "args": ["mock.py"],
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "streamable_http" in (data["error"] or "")

    app.dependency_overrides.clear()
