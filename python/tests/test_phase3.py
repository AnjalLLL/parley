import asyncio
import base64
import hashlib
import hmac
import json
import threading
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace as NS
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from voxwire.app import app
from voxwire.core import auth
from voxwire.core.config import SECRET, settings
from voxwire.core.session_manager import Session, sessions
from voxwire.services import webhooks
from voxwire.services.audio_pipeline import AudioPipeline
from voxwire.services.gemini_client import EchoClient, GeminiLiveClient
from voxwire.services.openai_client import OpenAIRealtimeClient
from voxwire.services.providers import resolve_provider
from voxwire.services.twilio_bridge import TwilioBridge, stream_twiml, valid_signature

H = {"Authorization": "Bearer k1"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "VOXWIRE_API_KEYS", "k1")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    auth._hits.clear()
    return TestClient(app)


# --- providers -------------------------------------------------------------

def test_resolve_provider(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk")
    monkeypatch.setattr(settings, "DEFAULT_PROVIDER", None)
    assert resolve_provider() == "openai"
    assert resolve_provider("gemini") == "openai"  # no gemini key -> fallback
    assert resolve_provider("echo") == "echo"
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    assert resolve_provider() == "echo"


def test_session_validation(client):
    assert client.post("/api/session", json={"provider": "openai"}, headers=H).status_code == 422
    tools = [{"name": "book", "description": "Book a slot", "parameters": {"type": "object"}}]
    assert client.post("/api/session", json={"tools": tools}, headers=H).status_code == 422
    r = client.post("/api/session", json={"tools": tools, "tool_webhook_url": "http://x"}, headers=H).json()
    assert r["provider"] == "echo"
    assert sessions.get(r["session_id"]).tools[0]["name"] == "book"
    assert client.post("/api/session", json={"record": True}, headers=H).status_code == 422  # no RECORDINGS_DIR


def test_transcript_merges_fragments(client):
    sid = client.post("/api/session", json={}, headers=H).json()["session_id"]
    s = sessions.get(sid)
    for role, text in [("user", "Hel"), ("user", "lo"), ("ai", "Hi!")]:
        sessions.add_transcript(s, role, text)
    t = client.get(f"/api/session/{sid}/transcript", headers=H).json()["transcript"]
    assert [(x["role"], x["text"]) for x in t] == [("user", "Hello"), ("ai", "Hi!")]


# --- webhooks --------------------------------------------------------------

class _Hook(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        _Hook.received.append((self.headers["X-Voxwire-Signature"], body))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"booked": True}).encode())

    def log_message(self, *a):
        pass


@pytest.fixture
def hook_url():
    _Hook.received = []
    srv = HTTPServer(("127.0.0.1", 0), _Hook)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_tool_call_is_signed_and_returns_result(hook_url):
    result = asyncio.run(webhooks.call_tool(hook_url, "s1", "book", {"day": "mon"}))
    assert result == {"booked": True}
    sig, body = _Hook.received[0]
    assert sig == "sha256=" + hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    assert json.loads(body) == {"session_id": "s1", "tool": "book", "arguments": {"day": "mon"}}


def test_tool_call_failure_goes_back_to_model():
    assert "error" in asyncio.run(webhooks.call_tool("http://127.0.0.1:1", "s1", "x", {}))


def test_call_events(hook_url):
    async def run():
        s = sessions.create(webhook_url=hook_url)
        sessions.start(s, ws=None)
        sessions.add_transcript(s, "user", "hi")
        sessions.finish(s, "hangup")
        await asyncio.gather(*webhooks._pending)
    asyncio.run(run())
    events = [json.loads(b)["event"] for _, b in _Hook.received]
    assert sorted(events) == ["call.ended", "call.started", "transcript.ready"]


# --- provider message handling --------------------------------------------

def test_gemini_handles_transcripts_and_tools():
    got, sent = [], []

    async def on_tool(name, args):
        return {"ok": name}

    async def run():
        c = GeminiLiveClient.__new__(GeminiLiveClient)
        c._response_queue, c.on_transcript, c.on_tool_call = asyncio.Queue(), lambda r, t: got.append((r, t)), on_tool
        async def _record(function_responses):
            sent.extend(function_responses)

        c.session = NS(send_tool_response=_record)
        sc = NS(interrupted=False, input_transcription=NS(text="hi"), output_transcription=NS(text="hello"))
        await c._handle(NS(data=b"\x00\x01", server_content=sc, tool_call=None))
        call = NS(id="c1", name="book", args={"a": 1})
        await c._handle(NS(data=None, server_content=None, tool_call=NS(function_calls=[call])))
        await asyncio.sleep(0.05)
        return await c._response_queue.get()

    audio = asyncio.run(run())
    assert audio == b"\x00\x01" and got == [("user", "hi"), ("ai", "hello")]
    assert sent[0].id == "c1" and sent[0].response == {"ok": "book"}


def test_openai_handles_events():
    got, sent = [], []

    async def on_tool(name, args):
        return {"slot": args["day"]}

    async def run():
        c = OpenAIRealtimeClient(on_tool_call=on_tool, on_transcript=lambda r, t: got.append((r, t)))

        class WS:
            async def send(self, m):
                sent.append(json.loads(m))

        c.ws = WS()
        await c.handle({"type": "response.output_audio.delta", "delta": base64.b64encode(b"ab").decode()})
        await c.handle({"type": "conversation.item.input_audio_transcription.completed", "transcript": "yo"})
        await c.handle({"type": "response.output_audio_transcript.done", "transcript": "hey"})
        await c.handle({"type": "response.function_call_arguments.done", "name": "book",
                        "call_id": "c9", "arguments": '{"day": "tue"}'})
        await asyncio.sleep(0.05)
        return await c._queue.get()

    assert asyncio.run(run()) == b"ab"
    assert got == [("user", "yo"), ("ai", "hey")]
    assert sent[0]["item"] == {"type": "function_call_output", "call_id": "c9", "output": '{"slot": "tue"}'}
    assert sent[1] == {"type": "response.create"}


def test_openai_session_config_includes_tools():
    c = OpenAIRealtimeClient(tools=[{"name": "t", "description": "d", "parameters": {}}])
    cfg = c.session_config("be nice")["session"]
    assert cfg["instructions"] == "be nice" and cfg["tools"][0] == {"type": "function", "name": "t",
                                                                    "description": "d", "parameters": {}}


# --- recording -------------------------------------------------------------

class _Pion:
    async def stream_audio_from_pion(self, sid):
        yield b"\x01\x00" * 160
        await asyncio.sleep(3600)

    async def stream_audio_to_pion(self, sid, stream, rate):
        async for _ in stream:
            pass


def test_recording_writes_both_sides(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "RECORDINGS_DIR", str(tmp_path))

    async def run():
        p = AudioPipeline(Session("rec1", 0, record=True), _Pion(), ws=None, ai=EchoClient())
        task = asyncio.create_task(p.run())
        await asyncio.sleep(0.1)
        await p.stop()
        task.cancel()

    asyncio.run(run())
    for side in ("user", "ai"):
        with wave.open(str(tmp_path / f"rec1-{side}.wav")) as w:
            assert w.getnframes() == 160 and w.getframerate() == 16000


# --- Twilio ------------------------------------------------------------------

def test_twiml_escapes_and_signature(monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_URL", "https://v.example.com")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "tok")
    xml = stream_twiml("abc", 'a"b')
    assert 'url="wss://v.example.com/twilio/stream/abc"' in xml and "value='a\"b'" in xml  # quoteattr picks safe quotes
    params = {"From": "+1555", "CallSid": "CA1"}
    sig = base64.b64encode(hmac.new(b"tok", b"https://v.example.com/x" + b"CallSidCA1From+1555", hashlib.sha1).digest())
    assert valid_signature("https://v.example.com/x", params, sig.decode())
    assert not valid_signature("https://v.example.com/x", params, "bad")


def test_twilio_inbound_and_media_echo(client, monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_URL", "https://v.example.com")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "tok")
    params = {"From": "+15550001", "To": "+15550002", "CallSid": "CA1"}
    data = "https://v.example.com/twilio/voice" + "".join(k + params[k] for k in sorted(params))
    sig = base64.b64encode(hmac.new(b"tok", data.encode(), hashlib.sha1).digest()).decode()
    body = urlencode(params)
    ctype = {"Content-Type": "application/x-www-form-urlencoded"}
    assert client.post("/twilio/voice", content=body, headers={**ctype, "X-Twilio-Signature": "x"}).status_code == 403
    r = client.post("/twilio/voice", content=body, headers={**ctype, "X-Twilio-Signature": sig})
    assert r.status_code == 200 and "<Stream" in r.text
    sid = r.text.split("/twilio/stream/")[1].split('"')[0]
    token = r.text.split('name="token" value="')[1].split('"')[0]

    with client.websocket_connect(f"/twilio/stream/{sid}") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(json.dumps({"event": "start", "start": {"streamSid": "MZ1", "customParameters": {"token": token}}}))
        ws.send_text(json.dumps({"event": "media", "media": {"payload": base64.b64encode(b"\xff" * 160).decode()}}))
        out = ws.receive_json()  # echo mode plays the caller back
        assert out["event"] == "media" and out["streamSid"] == "MZ1"
        assert len(base64.b64decode(out["media"]["payload"])) == 160
        ws.send_text(json.dumps({"event": "stop"}))
    s = sessions.get(sid)
    assert s.channel == "phone" and s.metadata["from"] == "+15550001"


def test_bridge_converts_rates():
    async def run():
        b = TwilioBridge(ws=None)
        b.feed(base64.b64encode(b"\xff" * 160).decode())
        b.close()
        return [c async for c in b.stream_audio_from_pion("s")]

    chunks = asyncio.run(run())
    assert len(chunks) == 1 and len(chunks[0]) == 160 * 2 * 2  # 8k ulaw -> 16k pcm16


def test_phone_endpoints_need_config(client, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "")
    assert client.post("/twilio/voice").status_code == 503
    assert client.post("/api/call", json={"to": "+15550001"}, headers=H).status_code == 503
