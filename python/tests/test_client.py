import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from voxwire import VoxwireClient, VoxwireError


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert self.headers["Authorization"] == "Bearer k"
        self._send(200, {"session_id": "abc", "token": "t1", "prompt": body["system_prompt"]})

    def do_GET(self):
        self._send(500, {"detail": "boom"})

    def _send(self, code, obj):
        self.send_response(code)
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_create_session_adds_signaling_url(server):
    s = VoxwireClient(server, api_key="k").create_session("be nice")
    assert s["session_id"] == "abc" and s["prompt"] == "be nice"
    assert s["signaling_url"] == server.replace("http://", "ws://") + "/ws/signaling/abc?token=t1"


def test_errors_raise(server):
    with pytest.raises(VoxwireError, match="500"):
        VoxwireClient(server).health()


def test_https_maps_to_wss():
    assert VoxwireClient("https://x.io/").signaling_url("1") == "wss://x.io/ws/signaling/1"
