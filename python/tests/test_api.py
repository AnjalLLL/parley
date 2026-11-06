import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from voxwire.app import app
from voxwire.core import auth
from voxwire.core.config import settings
from voxwire.core.session_manager import make_token, sessions, verify_token


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "VOXWIRE_API_KEYS", "k1,k2")
    auth._hits.clear()
    return TestClient(app)


H = {"Authorization": "Bearer k1"}


def test_requires_api_key(client):
    assert client.post("/api/session", json={}).status_code == 401
    assert client.post("/api/session", json={}, headers={"Authorization": "Bearer nope"}).status_code == 401


def test_session_lifecycle(client):
    r = client.post("/api/session", json={"system_prompt": "be brief", "metadata": {"user": 7}}, headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "waiting" and body["metadata"] == {"user": 7} and body["token"]
    assert sessions.get(body["session_id"]).system_prompt == "be brief"

    got = client.get(f"/api/session/{body['session_id']}", headers=H).json()
    assert got["status"] == "waiting"

    assert client.delete(f"/api/session/{body['session_id']}", headers=H).json() == {"ok": True}
    assert client.get(f"/api/session/{body['session_id']}", headers=H).json()["status"] == "ended"
    assert client.get("/api/session/missing", headers=H).status_code == 404


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "SESSION_CREATE_PER_MINUTE", 2)
    codes = [client.post("/api/session", json={}, headers=H).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_concurrent_call_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_CONCURRENT_CALLS", 0)
    assert client.post("/api/session", json={}, headers=H).status_code == 429


def test_dev_mode_without_keys(monkeypatch):
    monkeypatch.setattr(settings, "VOXWIRE_API_KEYS", "")
    assert TestClient(app).post("/api/session", json={}).status_code == 200


def _ws_close_code(client, url):
    with pytest.raises(WebSocketDisconnect) as e:
        with client.websocket_connect(url) as ws:
            ws.receive_text()
    return e.value.code


def test_ws_rejects_unknown_session_and_bad_token(client):
    assert _ws_close_code(client, "/ws/signaling/nope?token=x") == 4404
    sid = client.post("/api/session", json={}, headers=H).json()["session_id"]
    assert _ws_close_code(client, f"/ws/signaling/{sid}?token=bad") == 4401
    assert _ws_close_code(client, f"/ws/signaling/{sid}") == 4401


def test_tokens():
    exp = time.time() + 60
    tok = make_token("s1", exp)
    assert verify_token("s1", tok)
    assert not verify_token("s2", tok)
    assert not verify_token("s1", make_token("s1", time.time() - 1))
    assert not verify_token("s1", None) and not verify_token("s1", "garbage")


def test_health_and_metrics(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and "active_calls" in h and "pion_url" not in h
    assert "voxwire_calls_total" in client.get("/metrics").text
