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


def test_ws_closes_fast_when_sfu_is_down(client, monkeypatch):
    monkeypatch.setattr(settings, "PION_GRPC_URL", "127.0.0.1:1")  # nothing listens here
    monkeypatch.setattr(settings, "SFU_TIMEOUT_SECONDS", 1.0)
    s = client.post("/api/session", json={}, headers=H).json()
    start = time.time()
    assert _ws_close_code(client, f"/ws/signaling/{s['session_id']}?token={s['token']}") == 1011
    assert time.time() - start < 5
    assert sessions.get(s["session_id"]).status == "ended"


def test_lifespan_runs_startup_and_shutdown(monkeypatch, caplog):
    monkeypatch.setattr(settings, "VOXWIRE_API_KEYS", "")
    monkeypatch.setattr(settings, "VOXWIRE_SECRET", "")
    with caplog.at_level("INFO", logger="voxwire.app"):
        with TestClient(app) as c:
            # startup has run once the client context is entered
            assert any("Starting Voxwire" in m for m in caplog.messages)
            assert any("API is OPEN" in m for m in caplog.messages)
            assert any("VOXWIRE_SECRET is empty" in m for m in caplog.messages)
            assert c.get("/api/health").status_code == 200
    # leaving the context runs the shutdown half of the lifespan without error


def test_lifespan_is_quiet_when_configured(monkeypatch, caplog):
    monkeypatch.setattr(settings, "VOXWIRE_API_KEYS", "k1")
    monkeypatch.setattr(settings, "VOXWIRE_SECRET", "s3cret")
    with caplog.at_level("INFO", logger="voxwire.app"):
        with TestClient(app):
            pass
    assert any("Starting Voxwire" in m for m in caplog.messages)
    assert not [r for r in caplog.records if r.levelname == "WARNING"]


def test_no_deprecated_on_event_handlers():
    assert app.router.on_startup == []
    assert app.router.on_shutdown == []

