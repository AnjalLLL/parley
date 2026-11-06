import base64
import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient

from voxwire.app import app
from voxwire.core import auth
from voxwire.core.config import settings
from voxwire.core.ice_config import get_ice_config
from voxwire.core.session_manager import sessions

A, B = {"Authorization": "Bearer ka"}, {"Authorization": "Bearer kb"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "VOXWIRE_API_KEYS", "ka,kb")
    auth._hits.clear()
    return TestClient(app)


def _ended_call(client, headers):
    sid = client.post("/api/session", json={"metadata": {"n": 1}}, headers=headers).json()["session_id"]
    s = sessions.get(sid)
    sessions.start(s, ws=None)
    sessions.add_transcript(s, "user", "hello")
    sessions.finish(s, "hangup")
    sessions._sessions.pop(sid)  # simulate a restart: only the call log remains
    return sid


def test_ended_calls_come_from_call_log(client):
    sid = _ended_call(client, A)
    got = client.get(f"/api/session/{sid}", headers=A).json()
    assert got["status"] == "ended" and got["end_reason"] == "hangup" and got["metadata"] == {"n": 1}
    assert client.get(f"/api/session/{sid}/transcript", headers=A).json()["transcript"][0]["text"] == "hello"
    assert sid in [c["session_id"] for c in client.get("/api/sessions", headers=A).json()["recent"]]


def test_keys_cannot_see_each_others_calls(client):
    sid = _ended_call(client, A)
    assert client.get(f"/api/session/{sid}", headers=B).status_code == 404
    assert sid not in [c["session_id"] for c in client.get("/api/sessions", headers=B).json()["recent"]]
    live = client.post("/api/session", json={}, headers=A).json()["session_id"]
    assert client.delete(f"/api/session/{live}", headers=B).status_code == 404
    assert client.delete(f"/api/session/{live}", headers=A).status_code == 200


def test_usage_counts_calls(client):
    before = client.get("/api/usage", headers=B).json()["calls"]
    _ended_call(client, B)
    u = client.get("/api/usage", headers=B).json()
    assert u["calls"] == before + 1 and u["per_day"] and "active_calls" in u


def test_session_returns_ice_servers(client):
    r = client.post("/api/session", json={}, headers=A).json()
    assert r["ice_servers"][0]["urls"].startswith("stun:")


def test_turn_rest_credentials(monkeypatch):
    monkeypatch.setattr(settings, "TURN_ENABLED", True)
    monkeypatch.setattr(settings, "TURN_URL", "turn:t.example.com:3478")
    monkeypatch.setattr(settings, "TURN_SECRET", "s3cret")
    turn = get_ice_config()["iceServers"][1]
    expected = base64.b64encode(hmac.new(b"s3cret", turn["username"].encode(), hashlib.sha1).digest()).decode()
    assert turn["credential"] == expected and turn["username"].endswith(":voxwire")
