"""Example backend: three voice agents (support bot, language tutor, receptionist with a booking tool).

    pip install voxwire
    VOXWIRE_URL=http://localhost:8000 VOXWIRE_API_KEY=... python app.py
    open http://localhost:5050

It does the two jobs your own backend would do:
  1. POST /start  -> creates a Voxwire session with the API key (never sent to the browser)
  2. POST /tools  -> the tool webhook the receptionist's `book_appointment` calls, signature-checked
"""
import hashlib
import hmac
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from voxwire import VoxwireClient

VOXWIRE_URL = os.getenv("VOXWIRE_URL", "http://localhost:8000")
# The tool webhook URL must be reachable from the Voxwire server (inside docker: host.docker.internal).
PUBLIC_URL = os.getenv("EXAMPLE_PUBLIC_URL", "http://host.docker.internal:5050")
SECRET = os.getenv("VOXWIRE_SECRET", "")  # same value as the server's, to verify webhook signatures
vx = VoxwireClient(VOXWIRE_URL, api_key=os.getenv("VOXWIRE_API_KEY"))
HERE, SDK = Path(__file__).parent, Path(__file__).parents[2] / "js" / "src"

AGENTS = {
    "support": {"system_prompt": "You are a friendly support agent for Acme Cloud. Keep answers to two sentences."},
    "tutor": {"system_prompt": "You are a patient Spanish tutor. Speak simple Spanish, then repeat in English. "
                               "Correct the learner's mistakes gently."},
    "receptionist": {
        "system_prompt": "You are the receptionist at Bright Dental. Help callers book an appointment. "
                         "Ask for their name and preferred day, then call book_appointment.",
        "tools": [{
            "name": "book_appointment",
            "description": "Book a dental appointment",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"}, "day": {"type": "string", "description": "e.g. Monday"}},
                "required": ["name", "day"]},
        }],
        "tool_webhook_url": f"{PUBLIC_URL}/tools",
    },
}
BOOKINGS = []


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path.startswith("/sdk/"):  # serve the SDK from the repo so this works before `npm i voxwire`
            return str(SDK / path.removeprefix("/sdk/"))
        return str(HERE / "index.html")

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/start":
            agent = AGENTS.get(json.loads(raw or b"{}").get("agent"), AGENTS["support"])
            s = vx.create_session(**agent, ttl_seconds=120)
            return self._json(200, {"signaling_url": s["signaling_url"], "ice_servers": s["ice_servers"]})
        if self.path == "/tools":
            expected = "sha256=" + hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
            if SECRET and not hmac.compare_digest(expected, self.headers.get("X-Voxwire-Signature", "")):
                return self._json(401, {"error": "bad signature"})
            call = json.loads(raw)
            if call["tool"] == "book_appointment":
                BOOKINGS.append(call["arguments"])
                print("booked:", call["arguments"])
                return self._json(200, {"confirmed": True, "time": "10:00", **call["arguments"]})
            return self._json(200, {"error": "unknown tool"})
        self._json(404, {"error": "not found"})


if __name__ == "__main__":
    print("Example running on http://localhost:5050")
    ThreadingHTTPServer(("0.0.0.0", 5050), Handler).serve_forever()
